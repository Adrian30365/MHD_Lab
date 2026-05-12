import matplotlib
matplotlib.use("Agg")

from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
INTEGRATION_DIR = OUTPUT_DIR / "integrated_etl"

ONLINE_RETAIL_CSV = DATA_DIR / "Online_Retail.csv"

POSSIBLE_ONLINE_RETAIL_II_FILES = [
    DATA_DIR / "Online_Retail_II.xlsx",
    DATA_DIR / "online_retail_II.xlsx",
    DATA_DIR / "online_retail_ii.xlsx",
    DATA_DIR / "Online Retail II.xlsx",
]

TARGET_COLUMNS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]


def ensure_directories() -> None:
    INTEGRATION_DIR.mkdir(parents=True, exist_ok=True)


def find_online_retail_ii_file() -> Path:
    for file_path in POSSIBLE_ONLINE_RETAIL_II_FILES:
        if file_path.exists():
            return file_path

    expected_names = "\n".join(f"- {path.name}" for path in POSSIBLE_ONLINE_RETAIL_II_FILES)
    raise FileNotFoundError(
        "Nie znaleziono pliku Online Retail II w folderze LAB4/data/.\n"
        "Umieść tam jeden z plików:\n"
        f"{expected_names}\n\n"
        "Zadanie dodatkowe wymaga drugiego zbioru Online Retail II."
    )


def read_online_retail_csv() -> pd.DataFrame:
    if not ONLINE_RETAIL_CSV.exists():
        raise FileNotFoundError(
            f"Brak pliku {ONLINE_RETAIL_CSV}. Skopiuj Online_Retail.csv do LAB4/data/."
        )

    df = pd.read_csv(ONLINE_RETAIL_CSV, encoding="ISO-8859-1")
    df["SourceSystem"] = "Online_Retail_csv"
    df["SourceSheet"] = "csv"
    return df


def read_online_retail_ii_excel() -> pd.DataFrame:
    excel_file = find_online_retail_ii_file()

    sheets = pd.read_excel(excel_file, sheet_name=None)

    frames = []
    for sheet_name, sheet_df in sheets.items():
        sheet_df = sheet_df.copy()
        sheet_df["SourceSystem"] = "Online_Retail_II_xlsx"
        sheet_df["SourceSheet"] = str(sheet_name)
        frames.append(sheet_df)

    df = pd.concat(frames, ignore_index=True)
    return df


def normalize_schema(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    df = df.copy()

    rename_map = {
        "Invoice": "InvoiceNo",
        "InvoiceNo": "InvoiceNo",
        "StockCode": "StockCode",
        "Description": "Description",
        "Quantity": "Quantity",
        "InvoiceDate": "InvoiceDate",
        "Price": "UnitPrice",
        "UnitPrice": "UnitPrice",
        "Customer ID": "CustomerID",
        "CustomerID": "CustomerID",
        "Country": "Country",
    }

    df = df.rename(columns=rename_map)

    for column in TARGET_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA

    keep_columns = TARGET_COLUMNS + ["SourceSystem", "SourceSheet"]
    df = df[keep_columns]
    df["SourceName"] = source_name

    return df


def profile_dataset(df: pd.DataFrame, dataset_name: str) -> None:
    profile = pd.DataFrame(
        {
            "column": df.columns,
            "dtype": [str(dtype) for dtype in df.dtypes],
            "missing_values": [int(df[column].isna().sum()) for column in df.columns],
            "missing_percent": [
                round(float(df[column].isna().mean() * 100), 2) for column in df.columns
            ],
        }
    )

    safe_name = dataset_name.lower().replace(" ", "_")
    profile.to_csv(INTEGRATION_DIR / f"profile_{safe_name}.csv", index=False)

    with open(INTEGRATION_DIR / f"profile_{safe_name}.txt", "w", encoding="utf-8") as file:
        file.write(f"Profil danych: {dataset_name}\n")
        file.write("=" * 60 + "\n\n")
        file.write(f"Liczba rekordów: {df.shape[0]}\n")
        file.write(f"Liczba kolumn: {df.shape[1]}\n\n")
        file.write("Kolumny:\n")
        file.write(", ".join(df.columns.astype(str)))
        file.write("\n\nTypy danych:\n")
        file.write(df.dtypes.to_string())
        file.write("\n\nBrakujące wartości:\n")
        file.write(df.isna().sum().to_string())


def clean_for_fact(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["InvoiceNo"] = df["InvoiceNo"].astype(str).str.strip()
    df["StockCode"] = df["StockCode"].astype(str).str.strip()
    df["Description"] = df["Description"].fillna("Unknown product").astype(str).str.strip()
    df["Country"] = df["Country"].fillna("Unknown country").astype(str).str.strip()

    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
    df["CustomerID"] = pd.to_numeric(df["CustomerID"], errors="coerce")

    quality_before = {
        "rows_before": int(len(df)),
        "missing_customer_id": int(df["CustomerID"].isna().sum()),
        "cancelled_invoice_no_starts_with_C": int(df["InvoiceNo"].str.upper().str.startswith("C").sum()),
        "quantity_less_or_equal_zero": int((df["Quantity"] <= 0).sum()),
        "unit_price_less_than_zero": int((df["UnitPrice"] < 0).sum()),
        "missing_invoice_date": int(df["InvoiceDate"].isna().sum()),
        "duplicates_before_cleaning": int(df.duplicated().sum()),
    }

    df = df.dropna(subset=["CustomerID"])
    df = df[~df["InvoiceNo"].str.upper().str.startswith("C")]
    df = df[df["Quantity"] > 0]
    df = df[df["UnitPrice"] >= 0]
    df = df.dropna(subset=["InvoiceDate"])
    df["CustomerID"] = df["CustomerID"].astype(int)

    business_columns = [
        "InvoiceNo",
        "StockCode",
        "Description",
        "Quantity",
        "InvoiceDate",
        "UnitPrice",
        "CustomerID",
        "Country",
    ]

    df["DuplicateBusinessKey"] = df[business_columns].astype(str).agg("|".join, axis=1)

    duplicates_between_sources = (
        df[df.duplicated(subset=["DuplicateBusinessKey"], keep=False)]
        .sort_values(["DuplicateBusinessKey", "SourceSystem"])
    )
    duplicates_between_sources.to_csv(
        INTEGRATION_DIR / "duplicates_between_sources.csv",
        index=False,
    )

    df = df.drop_duplicates(subset=["DuplicateBusinessKey"], keep="first")

    df["Year"] = df["InvoiceDate"].dt.year
    df["Month"] = df["InvoiceDate"].dt.month
    df["Day"] = df["InvoiceDate"].dt.day
    df["Revenue"] = df["Quantity"] * df["UnitPrice"]
    df["LineCount"] = 1

    conflict_key = ["InvoiceNo", "StockCode", "CustomerID", "InvoiceDate"]
    price_conflicts = (
        df.groupby(conflict_key)
        .agg(
            min_unit_price=("UnitPrice", "min"),
            max_unit_price=("UnitPrice", "max"),
            unique_prices=("UnitPrice", "nunique"),
            rows_count=("UnitPrice", "size"),
        )
        .reset_index()
    )
    price_conflicts = price_conflicts[price_conflicts["unique_prices"] > 1]
    price_conflicts.to_csv(INTEGRATION_DIR / "price_conflicts.csv", index=False)

    quality_before["rows_after_cleaning_and_deduplication"] = int(len(df))
    pd.DataFrame([quality_before]).to_csv(
        INTEGRATION_DIR / "integrated_quality_report.csv",
        index=False,
    )

    return df


def build_fact_sales(df: pd.DataFrame) -> pd.DataFrame:
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
            "Country",
            "SourceSystem",
            "SourceSheet",
            "SourceName",
        ]
    ].copy()

    fact_sales.insert(0, "fact_sales_id", range(1, len(fact_sales) + 1))

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
            "Country": "country",
            "SourceSystem": "source_system",
            "SourceSheet": "source_sheet",
            "SourceName": "source_name",
        }
    )

    return fact_sales


def save_reports(fact_sales: pd.DataFrame) -> None:
    fact_sales.to_csv(INTEGRATION_DIR / "fact_sales_integrated.csv", index=False)

    sales_by_country = (
        fact_sales.groupby("country")
        .agg(
            revenue=("revenue", "sum"),
            quantity=("quantity", "sum"),
            transaction_lines=("line_count", "sum"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    sales_by_country.to_csv(INTEGRATION_DIR / "integrated_sales_by_country.csv", index=False)

    sales_by_month = (
        fact_sales.groupby(["year", "month"])
        .agg(
            revenue=("revenue", "sum"),
            quantity=("quantity", "sum"),
            transaction_lines=("line_count", "sum"),
        )
        .reset_index()
        .sort_values(["year", "month"])
    )
    sales_by_month.to_csv(INTEGRATION_DIR / "integrated_sales_by_month.csv", index=False)

    source_counts = (
        fact_sales.groupby(["source_system", "source_sheet"])
        .size()
        .reset_index(name="rows_count")
        .sort_values(["source_system", "source_sheet"])
    )
    source_counts.to_csv(INTEGRATION_DIR / "source_rows_count.csv", index=False)

    notes = """
LAB4 - Zadanie dodatkowe - integracja danych z wielu źródeł

Cel:
Połączyć Online_Retail.csv oraz Online_Retail_II.xlsx w jedną spójną tabelę faktów.

Decyzje projektowe:
1. Przyjęto schemat docelowy z kolumnami:
   InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country.

2. W Online Retail II nazwy kolumn mogą różnić się od Online_Retail.csv:
   Invoice -> InvoiceNo,
   Price -> UnitPrice,
   Customer ID -> CustomerID.
   Dlatego wykonano mapowanie nazw kolumn.

3. Do połączenia użyto concat, a nie merge.
   Uzasadnienie: zbiory reprezentują rekordy transakcyjne o podobnej strukturze,
   więc należy je dopisać jeden pod drugim, a nie łączyć kolumnami.

4. Duplikat rozpoznawany jest po kluczu biznesowym:
   InvoiceNo + StockCode + Description + Quantity + InvoiceDate + UnitPrice + CustomerID + Country.

5. Konflikt ceny wykrywany jest, gdy dla tego samego InvoiceNo, StockCode, CustomerID
   oraz InvoiceDate występuje więcej niż jedna cena UnitPrice.

6. Wynikiem końcowym jest fact_sales_integrated.csv.
"""
    with open(INTEGRATION_DIR / "integration_notes.txt", "w", encoding="utf-8") as file:
        file.write(notes.strip())


def main() -> None:
    ensure_directories()

    print("=== LAB4 - ZADANIE 2 - INTEGRACJA WIELU ŹRÓDEŁ ===")

    df1_raw = read_online_retail_csv()
    df2_raw = read_online_retail_ii_excel()

    profile_dataset(df1_raw, "Online Retail CSV przed normalizacja")
    profile_dataset(df2_raw, "Online Retail II Excel przed normalizacja")

    df1 = normalize_schema(df1_raw, "Online_Retail.csv")
    df2 = normalize_schema(df2_raw, "Online_Retail_II.xlsx")

    profile_dataset(df1, "Online Retail CSV po normalizacji")
    profile_dataset(df2, "Online Retail II Excel po normalizacji")

    df_all = pd.concat([df1, df2], ignore_index=True)

    print("Połączono źródła przez concat.")
    print(f"Liczba rekordów przed czyszczeniem: {len(df_all)}")

    df_clean = clean_for_fact(df_all)
    fact_sales = build_fact_sales(df_clean)
    save_reports(fact_sales)

    print("Integracja zakończona.")
    print(f"Liczba rekordów w fact_sales_integrated.csv: {len(fact_sales)}")
    print("Wyniki zapisano w folderze:")
    print(INTEGRATION_DIR)


if __name__ == "__main__":
    main()
