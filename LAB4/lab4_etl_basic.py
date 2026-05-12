import matplotlib
matplotlib.use("Agg")

from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
BASIC_DIR = OUTPUT_DIR / "basic_etl"

INPUT_FILE = DATA_DIR / "Online_Retail.csv"


def ensure_directories() -> None:
    BASIC_DIR.mkdir(parents=True, exist_ok=True)


def extract() -> pd.DataFrame:
    """Extract - wczytanie danych źródłowych do strefy staging."""
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Brak pliku: {INPUT_FILE}\n"
            "Skopiuj Online_Retail.csv do folderu LAB4/data/."
        )

    df = pd.read_csv(INPUT_FILE, encoding="ISO-8859-1")

    schema_report = pd.DataFrame(
        {
            "column": df.columns,
            "dtype": [str(dtype) for dtype in df.dtypes],
            "missing_values": [int(df[column].isna().sum()) for column in df.columns],
            "missing_percent": [
                round(float(df[column].isna().mean() * 100), 2) for column in df.columns
            ],
        }
    )
    schema_report.to_csv(BASIC_DIR / "extract_schema_report.csv", index=False)

    with open(BASIC_DIR / "extract_summary.txt", "w", encoding="utf-8") as file:
        file.write("LAB4 - ETL podstawowy - etap Extract\n")
        file.write("=" * 50 + "\n\n")
        file.write(f"Liczba rekordów: {df.shape[0]}\n")
        file.write(f"Liczba kolumn: {df.shape[1]}\n\n")
        file.write("Pierwsze 5 rekordów:\n")
        file.write(df.head().to_string())
        file.write("\n\nOpis statystyczny:\n")
        file.write(df.describe(include="all").to_string())

    print("EXTRACT zakończony.")
    print(f"Wczytano rekordów: {df.shape[0]}")
    print(f"Wczytano kolumn: {df.shape[1]}")

    return df


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Transform - czyszczenie danych i przygotowanie miar."""
    before_rows = len(df)

    df = df.copy()

    df["InvoiceNo"] = df["InvoiceNo"].astype(str).str.strip()
    df["StockCode"] = df["StockCode"].astype(str).str.strip()
    df["Description"] = df["Description"].fillna("Unknown product").astype(str).str.strip()
    df["Country"] = df["Country"].fillna("Unknown country").astype(str).str.strip()

    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
    df["CustomerID"] = pd.to_numeric(df["CustomerID"], errors="coerce")

    quality_stats = {
        "rows_before": before_rows,
        "missing_customer_id": int(df["CustomerID"].isna().sum()),
        "cancelled_invoice_no_starts_with_C": int(df["InvoiceNo"].str.startswith("C").sum()),
        "quantity_less_or_equal_zero": int((df["Quantity"] <= 0).sum()),
        "unit_price_less_than_zero": int((df["UnitPrice"] < 0).sum()),
        "missing_invoice_date": int(df["InvoiceDate"].isna().sum()),
        "duplicates_before_cleaning": int(df.duplicated().sum()),
    }

    df = df.dropna(subset=["CustomerID"])
    df = df[~df["InvoiceNo"].str.startswith("C")]
    df = df[df["Quantity"] > 0]
    df = df[df["UnitPrice"] >= 0]
    df = df.dropna(subset=["InvoiceDate"])
    df = df.drop_duplicates()

    df["CustomerID"] = df["CustomerID"].astype(int)

    df["Year"] = df["InvoiceDate"].dt.year
    df["Month"] = df["InvoiceDate"].dt.month
    df["Day"] = df["InvoiceDate"].dt.day

    df["Revenue"] = df["Quantity"] * df["UnitPrice"]
    df["LineCount"] = 1

    quality_stats["rows_after"] = int(len(df))
    quality_stats["rows_removed"] = int(before_rows - len(df))

    pd.DataFrame([quality_stats]).to_csv(BASIC_DIR / "transform_quality_report.csv", index=False)

    print("TRANSFORM zakończony.")
    print(f"Rekordy przed czyszczeniem: {before_rows}")
    print(f"Rekordy po czyszczeniu: {len(df)}")
    print(f"Usunięto rekordów: {before_rows - len(df)}")

    return df


def load(df: pd.DataFrame) -> None:
    """Load - zapis przygotowanej tabeli faktów i prostych wyników kontroli."""
    fact_sales = df[
        [
            "InvoiceNo",
            "StockCode",
            "CustomerID",
            "InvoiceDate",
            "Year",
            "Month",
            "Day",
            "Quantity",
            "UnitPrice",
            "Revenue",
            "LineCount",
        ]
    ].copy()

    fact_sales = fact_sales.rename(
        columns={
            "InvoiceNo": "invoice_no",
            "StockCode": "stock_code",
            "CustomerID": "customer_id",
            "InvoiceDate": "invoice_date",
            "Year": "year",
            "Month": "month",
            "Day": "day",
            "Quantity": "quantity",
            "UnitPrice": "unit_price",
            "Revenue": "revenue",
            "LineCount": "line_count",
        }
    )

    fact_sales.to_csv(BASIC_DIR / "fact_sales.csv", index=False)

    sales_by_country = (
        df.groupby("Country")
        .agg(
            revenue=("Revenue", "sum"),
            quantity=("Quantity", "sum"),
            transaction_lines=("LineCount", "sum"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    sales_by_country.to_csv(BASIC_DIR / "sales_by_country_check.csv", index=False)

    sales_by_month = (
        df.groupby(["Year", "Month"])
        .agg(
            revenue=("Revenue", "sum"),
            quantity=("Quantity", "sum"),
            transaction_lines=("LineCount", "sum"),
        )
        .reset_index()
        .sort_values(["Year", "Month"])
    )
    sales_by_month.to_csv(BASIC_DIR / "sales_by_month_check.csv", index=False)

    notes = """
LAB4 - ETL podstawowy - decyzje projektowe

Extract:
Wczytano plik Online_Retail.csv do Pandas z kodowaniem ISO-8859-1.

Transform:
Usunięto rekordy bez CustomerID, anulowane transakcje, rekordy z Quantity <= 0,
rekordy z UnitPrice < 0, brakujące daty oraz duplikaty.
Ujednolicono typy danych i rozbito InvoiceDate na Year, Month, Day.

Load:
Wynikiem jest tabela fact_sales.csv. Jeden rekord odpowiada jednej pozycji faktury.
Dodano miarę Revenue = Quantity * UnitPrice, ponieważ ułatwia analizę wartości sprzedaży
i przychodu bez ponownego liczenia tej wartości w raportach.
"""
    with open(BASIC_DIR / "etl_notes.txt", "w", encoding="utf-8") as file:
        file.write(notes.strip())

    print("LOAD zakończony.")
    print(f"Zapisano: {BASIC_DIR / 'fact_sales.csv'}")


def main() -> None:
    ensure_directories()

    print("=== LAB4 - ZADANIE 1 - PIPELINE ETL ===")
    staged_df = extract()
    transformed_df = transform(staged_df)
    load(transformed_df)

    print("\nGotowe. Wyniki zapisano w folderze:")
    print(BASIC_DIR)


if __name__ == "__main__":
    main()
