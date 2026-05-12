import matplotlib
matplotlib.use("Agg")

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

INPUT_FILE = DATA_DIR / "Online_Retail.csv"


def load_data() -> pd.DataFrame:
    """Wczytanie danych źródłowych do strefy staging."""
    df = pd.read_csv(INPUT_FILE, encoding="ISO-8859-1")
    print("Dane źródłowe:")
    print(df.shape)
    print(df.head())
    print(df.dtypes)
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Czyszczenie zgodnie z wymaganiami LAB3."""
    df_clean = df.copy()

    df_clean = df_clean.dropna(subset=["CustomerID"])
    df_clean = df_clean[~df_clean["InvoiceNo"].astype(str).str.startswith("C")]
    df_clean = df_clean[df_clean["Quantity"] > 0]
    df_clean = df_clean[df_clean["UnitPrice"] > 0]

    df_clean["InvoiceDate"] = pd.to_datetime(df_clean["InvoiceDate"], errors="coerce")
    df_clean = df_clean.dropna(subset=["InvoiceDate"])

    df_clean = df_clean.drop_duplicates()

    df_clean["CustomerID"] = df_clean["CustomerID"].astype(int)
    df_clean["StockCode"] = df_clean["StockCode"].astype(str)
    df_clean["Description"] = df_clean["Description"].fillna("Unknown product")
    df_clean["Country"] = df_clean["Country"].fillna("Unknown country")

    df_clean["Revenue"] = df_clean["Quantity"] * df_clean["UnitPrice"]
    df_clean["InvoiceDateOnly"] = df_clean["InvoiceDate"].dt.date

    print("\nDane po czyszczeniu:")
    print(df_clean.shape)
    print(df_clean.head())

    return df_clean


def build_dim_country(df: pd.DataFrame) -> pd.DataFrame:
    dim_country = (
        df[["Country"]]
        .drop_duplicates()
        .sort_values("Country")
        .reset_index(drop=True)
    )
    dim_country.insert(0, "country_key", range(1, len(dim_country) + 1))
    dim_country = dim_country.rename(columns={"Country": "country_name"})
    return dim_country


def build_dim_product(df: pd.DataFrame) -> pd.DataFrame:
    dim_product = (
        df.groupby("StockCode", as_index=False)
        .agg(product_name=("Description", lambda x: x.mode().iloc[0] if not x.mode().empty else "Unknown product"))
        .sort_values("StockCode")
        .reset_index(drop=True)
    )
    dim_product.insert(0, "product_key", range(1, len(dim_product) + 1))
    dim_product = dim_product.rename(columns={"StockCode": "stock_code"})
    return dim_product


def build_dim_date(df: pd.DataFrame) -> pd.DataFrame:
    dim_date = (
        df[["InvoiceDateOnly"]]
        .drop_duplicates()
        .sort_values("InvoiceDateOnly")
        .reset_index(drop=True)
    )
    dim_date.insert(0, "date_key", range(1, len(dim_date) + 1))
    dim_date = dim_date.rename(columns={"InvoiceDateOnly": "date"})
    dim_date["date"] = pd.to_datetime(dim_date["date"])
    dim_date["year"] = dim_date["date"].dt.year
    dim_date["quarter"] = dim_date["date"].dt.quarter
    dim_date["month"] = dim_date["date"].dt.month
    dim_date["day"] = dim_date["date"].dt.day
    dim_date["weekday"] = dim_date["date"].dt.day_name()
    return dim_date


def build_dim_invoice(df: pd.DataFrame) -> pd.DataFrame:
    dim_invoice = (
        df[["InvoiceNo", "InvoiceDate"]]
        .drop_duplicates(subset=["InvoiceNo"])
        .sort_values("InvoiceNo")
        .reset_index(drop=True)
    )
    dim_invoice.insert(0, "invoice_key", range(1, len(dim_invoice) + 1))
    dim_invoice = dim_invoice.rename(
        columns={"InvoiceNo": "invoice_no", "InvoiceDate": "invoice_datetime"}
    )
    dim_invoice["invoice_date"] = dim_invoice["invoice_datetime"].dt.date
    dim_invoice["invoice_hour"] = dim_invoice["invoice_datetime"].dt.hour
    return dim_invoice


def build_dim_customer_scd2(df: pd.DataFrame, dim_country: pd.DataFrame) -> pd.DataFrame:
    customer_country_history = (
        df[["CustomerID", "Country", "InvoiceDate"]]
        .drop_duplicates()
        .sort_values(["CustomerID", "InvoiceDate"])
        .reset_index(drop=True)
    )

    scd_records = []

    for customer_id, customer_rows in customer_country_history.groupby("CustomerID"):
        customer_rows = customer_rows.sort_values("InvoiceDate")
        current_country = None
        valid_from = None

        for _, row in customer_rows.iterrows():
            row_country = row["Country"]
            row_date = row["InvoiceDate"]

            if current_country is None:
                current_country = row_country
                valid_from = row_date
            elif row_country != current_country:
                scd_records.append(
                    {
                        "customer_id": int(customer_id),
                        "country_name": current_country,
                        "valid_from": valid_from,
                        "valid_to": row_date,
                        "current_flag": False,
                    }
                )
                current_country = row_country
                valid_from = row_date

        scd_records.append(
            {
                "customer_id": int(customer_id),
                "country_name": current_country,
                "valid_from": valid_from,
                "valid_to": pd.NaT,
                "current_flag": True,
            }
        )

    dim_customer = pd.DataFrame(scd_records)
    dim_customer = dim_customer.merge(dim_country, on="country_name", how="left")
    dim_customer.insert(0, "customer_key", range(1, len(dim_customer) + 1))
    dim_customer = dim_customer[
        [
            "customer_key",
            "customer_id",
            "country_key",
            "country_name",
            "valid_from",
            "valid_to",
            "current_flag",
        ]
    ]
    return dim_customer


def add_customer_key(df: pd.DataFrame, dim_customer: pd.DataFrame) -> pd.DataFrame:
    df_with_customer_key = df.merge(
        dim_customer[
            ["customer_key", "customer_id", "country_name", "valid_from", "valid_to"]
        ],
        left_on=["CustomerID", "Country"],
        right_on=["customer_id", "country_name"],
        how="left",
    )

    in_valid_period = (
        (df_with_customer_key["InvoiceDate"] >= df_with_customer_key["valid_from"])
        & (
            df_with_customer_key["valid_to"].isna()
            | (df_with_customer_key["InvoiceDate"] < df_with_customer_key["valid_to"])
        )
    )

    df_with_customer_key = df_with_customer_key[in_valid_period].copy()
    return df_with_customer_key


def build_fact_sales(
    df: pd.DataFrame,
    dim_customer: pd.DataFrame,
    dim_product: pd.DataFrame,
    dim_date: pd.DataFrame,
    dim_country: pd.DataFrame,
    dim_invoice: pd.DataFrame,
) -> pd.DataFrame:
    fact = add_customer_key(df, dim_customer)

    fact = fact.merge(
        dim_product[["product_key", "stock_code"]],
        left_on="StockCode",
        right_on="stock_code",
        how="left",
    )

    fact = fact.merge(
        dim_country[["country_key", "country_name"]],
        left_on="Country",
        right_on="country_name",
        how="left",
    )

    dim_date_for_merge = dim_date.copy()
    dim_date_for_merge["date_only"] = dim_date_for_merge["date"].dt.date
    fact = fact.merge(
        dim_date_for_merge[["date_key", "date_only"]],
        left_on="InvoiceDateOnly",
        right_on="date_only",
        how="left",
    )

    fact = fact.merge(
        dim_invoice[["invoice_key", "invoice_no"]],
        left_on="InvoiceNo",
        right_on="invoice_no",
        how="left",
    )

    fact_sales = fact[
        [
            "invoice_key",
            "customer_key",
            "product_key",
            "date_key",
            "country_key",
            "Quantity",
            "UnitPrice",
            "Revenue",
        ]
    ].copy()

    fact_sales.insert(0, "sales_key", range(1, len(fact_sales) + 1))
    fact_sales["line_count"] = 1

    fact_sales = fact_sales.rename(
        columns={
            "Quantity": "quantity",
            "UnitPrice": "unit_price",
            "Revenue": "revenue",
        }
    )

    return fact_sales


def create_analysis_outputs(
    fact_sales: pd.DataFrame,
    dim_country: pd.DataFrame,
    dim_date: pd.DataFrame,
    dim_product: pd.DataFrame,
) -> None:
    sales_by_country = (
        fact_sales.merge(dim_country, on="country_key", how="left")
        .groupby("country_name")
        .agg(
            revenue=("revenue", "sum"),
            quantity=("quantity", "sum"),
            lines=("line_count", "sum"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
    )

    sales_trend = (
        fact_sales.merge(dim_date, on="date_key", how="left")
        .groupby(["year", "month"])
        .agg(
            revenue=("revenue", "sum"),
            quantity=("quantity", "sum"),
            lines=("line_count", "sum"),
        )
        .reset_index()
        .sort_values(["year", "month"])
    )

    sales_by_product = (
        fact_sales.merge(dim_product, on="product_key", how="left")
        .groupby(["stock_code", "product_name"])
        .agg(revenue=("revenue", "sum"), quantity=("quantity", "sum"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )

    sales_by_country.to_csv(OUTPUT_DIR / "sales_by_country.csv", index=False)
    sales_trend.to_csv(OUTPUT_DIR / "sales_trend_monthly.csv", index=False)
    sales_by_product.to_csv(OUTPUT_DIR / "sales_by_product.csv", index=False)

    sales_trend["period"] = (
        sales_trend["year"].astype(str)
        + "-"
        + sales_trend["month"].astype(str).str.zfill(2)
    )

    plt.figure(figsize=(12, 6))
    plt.plot(sales_trend["period"], sales_trend["revenue"], marker="o")
    plt.title("Trend sprzedaży w czasie")
    plt.xlabel("Miesiąc")
    plt.ylabel("Revenue")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "sales_trend_monthly.png")
    plt.close()


def save_design_notes() -> None:
    notes = """LAB3 - Modelowanie danych w hurtowni

1. Grain
Wybrano grain na poziomie pojedynczej pozycji faktury. Jeden rekord w FactSales odpowiada jednej linii sprzedażowej z faktury, czyli sprzedaży konkretnego produktu w konkretnej fakturze. Taki poziom szczegółowości pozwala analizować sprzedaż według produktu, klienta, kraju oraz czasu, a w razie potrzeby agregować dane do poziomu faktury, dnia lub miesiąca.

Przykład analizy: sprzedaż produktów według kraju i miesiąca.

2. Model gwiazdy
Tabela faktów: FactSales.
Wymiary: DimCustomer, DimProduct, DimDate, DimCountry, DimInvoice.
Minimalne wymagania spełniają DimCustomer, DimProduct i DimDate, a w ramach rozszerzenia dodano DimCountry oraz DimInvoice.

3. Klucze
Klucze naturalne:
- CustomerID dla klienta,
- StockCode dla produktu,
- InvoiceNo dla faktury,
- data z InvoiceDate dla czasu,
- Country dla kraju.

Klucze sztuczne:
- customer_key,
- product_key,
- date_key,
- country_key,
- invoice_key.

Tabela faktów używa wyłącznie kluczy sztucznych do połączenia z wymiarami.

4. SCD2
Dla DimCustomer zastosowano SCD typu 2. Zmianę wykrywa się na podstawie zmiany kraju klienta. Wymiar zawiera kolumny valid_from, valid_to oraz current_flag, dzięki czemu można zachować historię zmian.

5. Kompromisy projektowe
Model gwiazdy jest mniej znormalizowany niż 3NF, ale jest wygodniejszy dla analiz OLAP. Dane opisowe znajdują się w wymiarach, a miary w tabeli faktów. Dzięki temu analizy sprzedaży według czasu, produktu, klienta i kraju wymagają prostych połączeń tabeli faktów z wymiarami.

6. Jak model wspiera analizy biznesowe
Model umożliwia analizę przychodów, ilości sprzedanych sztuk i liczby linii sprzedaży według kraju, produktu, klienta i czasu. Dodatkowe pliki sales_by_country.csv i sales_trend_monthly.csv pokazują przykładowe odpowiedzi na pytania biznesowe.
"""
    with open(OUTPUT_DIR / "design_notes.txt", "w", encoding="utf-8") as file:
        file.write(notes)


def main() -> None:
    df_raw = load_data()
    df_clean = clean_data(df_raw)

    dim_country = build_dim_country(df_clean)
    dim_product = build_dim_product(df_clean)
    dim_date = build_dim_date(df_clean)
    dim_invoice = build_dim_invoice(df_clean)
    dim_customer = build_dim_customer_scd2(df_clean, dim_country)

    fact_sales = build_fact_sales(
        df_clean,
        dim_customer,
        dim_product,
        dim_date,
        dim_country,
        dim_invoice,
    )

    dim_customer.to_csv(OUTPUT_DIR / "DimCustomer_SCD2.csv", index=False)
    dim_product.to_csv(OUTPUT_DIR / "DimProduct.csv", index=False)
    dim_date.to_csv(OUTPUT_DIR / "DimDate.csv", index=False)
    dim_country.to_csv(OUTPUT_DIR / "DimCountry.csv", index=False)
    dim_invoice.to_csv(OUTPUT_DIR / "DimInvoice.csv", index=False)
    fact_sales.to_csv(OUTPUT_DIR / "FactSales.csv", index=False)

    create_analysis_outputs(fact_sales, dim_country, dim_date, dim_product)
    save_design_notes()

    print("\nZapisano wyniki do folderu:")
    print(OUTPUT_DIR)
    print("\nUtworzone główne pliki:")
    print("- DimCustomer_SCD2.csv")
    print("- DimProduct.csv")
    print("- DimDate.csv")
    print("- DimCountry.csv")
    print("- DimInvoice.csv")
    print("- FactSales.csv")
    print("- sales_by_country.csv")
    print("- sales_trend_monthly.csv")
    print("- sales_trend_monthly.png")
    print("- design_notes.txt")


if __name__ == "__main__":
    main()
