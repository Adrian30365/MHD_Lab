import matplotlib
matplotlib.use("Agg")

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
KIMBALL_DIR = OUTPUT_DIR / "kimball_star"

KIMBALL_DIR.mkdir(parents=True, exist_ok=True)

INPUT_FILE = DATA_DIR / "Online_Retail.csv"


def normalize_customer_id(row):
    if pd.isna(row["CustomerID"]):
        return f"UNKNOWN_{row['Country']}"
    return str(int(row["CustomerID"]))


def main():
    df = pd.read_csv(INPUT_FILE, encoding="ISO-8859-1")

    print("=== LAB2 DODATKOWE - MODEL GWIAZDY ===")
    print("Dane wejściowe:")
    print(df.shape)
    print(df.head())

    # Przygotowanie danych
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df["Description"] = df["Description"].fillna("Unknown product")
    df["Country"] = df["Country"].fillna("Unknown country")
    df["CustomerBusinessKey"] = df.apply(normalize_customer_id, axis=1)

    df["IsCancelled"] = df["InvoiceNo"].astype(str).str.startswith("C")
    df["IsReturn"] = df["Quantity"] < 0

    # Miara wymagana w zadaniu
    df["SalesAmount"] = df["Quantity"] * df["UnitPrice"]

    # Dodatkowo rozdzielamy sprzedaż dodatnią i zwroty
    df["GrossSalesAmount"] = df["SalesAmount"].where(df["SalesAmount"] > 0, 0)
    df["ReturnAmount"] = df["SalesAmount"].where(df["SalesAmount"] < 0, 0)

    # Data bez godziny do wymiaru czasu
    df["Date"] = df["InvoiceDate"].dt.date
    df["Year"] = df["InvoiceDate"].dt.year
    df["Quarter"] = df["InvoiceDate"].dt.quarter
    df["Month"] = df["InvoiceDate"].dt.month
    df["Day"] = df["InvoiceDate"].dt.day

    # Wymiar kraju
    dim_country = (
        df[["Country"]]
        .drop_duplicates()
        .sort_values("Country")
        .reset_index(drop=True)
    )
    dim_country.insert(0, "country_key", range(1, len(dim_country) + 1))
    dim_country = dim_country.rename(columns={"Country": "country_name"})

    df = df.merge(
        dim_country,
        left_on="Country",
        right_on="country_name",
        how="left"
    )

    # Wymiar klienta
    dim_customer = (
        df[["CustomerBusinessKey", "CustomerID", "country_key"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    dim_customer.insert(0, "customer_key", range(1, len(dim_customer) + 1))
    dim_customer = dim_customer.rename(
        columns={
            "CustomerBusinessKey": "customer_business_key",
            "CustomerID": "customer_id_source"
        }
    )

    df = df.merge(
        dim_customer[["customer_key", "customer_business_key"]],
        left_on="CustomerBusinessKey",
        right_on="customer_business_key",
        how="left"
    )

    # Wymiar produktu
    dim_product = (
        df.groupby("StockCode", as_index=False)
        .agg(product_name=("Description", lambda x: x.dropna().mode().iloc[0] if not x.dropna().empty else "Unknown product"))
        .sort_values("StockCode")
        .reset_index(drop=True)
    )
    dim_product.insert(0, "product_key", range(1, len(dim_product) + 1))
    dim_product = dim_product.rename(columns={"StockCode": "stock_code"})

    df = df.merge(
        dim_product[["product_key", "stock_code"]],
        left_on="StockCode",
        right_on="stock_code",
        how="left"
    )

    # Wymiar czasu
    dim_date = (
        df[["Date", "Year", "Quarter", "Month", "Day"]]
        .dropna()
        .drop_duplicates()
        .sort_values("Date")
        .reset_index(drop=True)
    )
    dim_date.insert(0, "date_key", range(1, len(dim_date) + 1))
    dim_date = dim_date.rename(
        columns={
            "Date": "date",
            "Year": "year",
            "Quarter": "quarter",
            "Month": "month",
            "Day": "day"
        }
    )

    df = df.merge(
        dim_date[["date_key", "date"]],
        left_on="Date",
        right_on="date",
        how="left"
    )

    # Tabela faktów
    fact_sales = df[
        [
            "InvoiceNo",
            "customer_key",
            "product_key",
            "country_key",
            "date_key",
            "Quantity",
            "UnitPrice",
            "SalesAmount",
            "GrossSalesAmount",
            "ReturnAmount",
            "IsReturn",
            "IsCancelled"
        ]
    ].copy()

    fact_sales.insert(0, "sales_fact_id", range(1, len(fact_sales) + 1))

    fact_sales = fact_sales.rename(
        columns={
            "InvoiceNo": "invoice_no",
            "Quantity": "quantity",
            "UnitPrice": "unit_price",
            "SalesAmount": "sales_amount",
            "GrossSalesAmount": "gross_sales_amount",
            "ReturnAmount": "return_amount",
            "IsReturn": "is_return",
            "IsCancelled": "is_cancelled"
        }
    )

    # Analiza biznesowa: sprzedaż wg krajów
    sales_by_country = (
        fact_sales
        .merge(dim_country, on="country_key", how="left")
        .groupby("country_name")
        .agg(
            net_sales=("sales_amount", "sum"),
            gross_sales=("gross_sales_amount", "sum"),
            returns=("return_amount", "sum"),
            transaction_lines=("sales_fact_id", "count")
        )
        .reset_index()
        .sort_values("net_sales", ascending=False)
    )

    # Analiza biznesowa: trend sprzedaży w czasie
    sales_trend_monthly = (
        fact_sales
        .merge(dim_date, on="date_key", how="left")
        .groupby(["year", "month"])
        .agg(
            net_sales=("sales_amount", "sum"),
            gross_sales=("gross_sales_amount", "sum"),
            returns=("return_amount", "sum"),
            transaction_lines=("sales_fact_id", "count")
        )
        .reset_index()
        .sort_values(["year", "month"])
    )

    # Wykres trendu sprzedaży
    sales_trend_monthly["period"] = (
        sales_trend_monthly["year"].astype(int).astype(str)
        + "-"
        + sales_trend_monthly["month"].astype(int).astype(str).str.zfill(2)
    )

    plt.figure(figsize=(12, 6))
    plt.plot(
        sales_trend_monthly["period"],
        sales_trend_monthly["net_sales"],
        marker="o"
    )
    plt.title("Trend sprzedaży netto w czasie")
    plt.xlabel("Miesiąc")
    plt.ylabel("Sprzedaż netto")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(KIMBALL_DIR / "sales_trend_monthly.png")
    plt.close()

    # Zapis wymiarów i faktów
    dim_country.to_csv(KIMBALL_DIR / "dim_country.csv", index=False)
    dim_customer.to_csv(KIMBALL_DIR / "dim_customer.csv", index=False)
    dim_product.to_csv(KIMBALL_DIR / "dim_product.csv", index=False)
    dim_date.to_csv(KIMBALL_DIR / "dim_date.csv", index=False)
    fact_sales.to_csv(KIMBALL_DIR / "fact_sales.csv", index=False)

    sales_by_country.to_csv(KIMBALL_DIR / "sales_by_country.csv", index=False)
    sales_trend_monthly.to_csv(KIMBALL_DIR / "sales_trend_monthly.csv", index=False)

    # Uzasadnienie projektowe i pytanie kontrolne
    design_notes = """
LAB2 dodatkowe - uzasadnienie decyzji projektowych

1. Model logiczny

Zaprojektowano prosty model gwiazdy:
- tabela faktów: fact_sales
- wymiary: dim_customer, dim_product, dim_date, dim_country

Ziarnistość danych:
Jeden rekord w tabeli fact_sales odpowiada jednej pozycji faktury,
czyli jednej linii sprzedażowej z pliku Online_Retail.csv.

2. Przygotowanie danych

Obsługa brakujących danych:
- brakujący opis produktu zastąpiono wartością "Unknown product",
- brakujący kraj zastąpiono wartością "Unknown country",
- brakujący CustomerID otrzymał techniczny klucz typu UNKNOWN_kraj.

Obsługa zwrotów:
- Quantity < 0 oznacza zwrot,
- utworzono flagę is_return,
- SalesAmount = Quantity * UnitPrice,
- zwroty zmniejszają sprzedaż netto,
- dodatkowo zapisano GrossSalesAmount i ReturnAmount.

3. Pytania biznesowe

Przygotowano:
- sprzedaż wg krajów: sales_by_country.csv,
- trend sprzedaży w czasie: sales_trend_monthly.csv,
- wykres trendu: sales_trend_monthly.png.

4. Pytanie kontrolne

To zadanie jest realizowane w podejściu Kimbala.

Uzasadnienie:
Zaczynamy od pytania analitycznego i procesu biznesowego sprzedaży,
a następnie projektujemy tabelę faktów oraz wymiary. Powstaje model
gwiazdy, który jest wygodny do analiz OLAP.

W podejściu Inmona najpierw projektowalibyśmy centralną, znormalizowaną
hurtownię danych w 3NF, a dopiero później wyprowadzali struktury
analityczne lub data marty.
"""

    with open(KIMBALL_DIR / "design_notes.txt", "w", encoding="utf-8") as file:
        file.write(design_notes)

    print("\nZapisano model gwiazdy do folderu:")
    print(KIMBALL_DIR)

    print("\nUtworzone pliki:")
    print("- dim_country.csv")
    print("- dim_customer.csv")
    print("- dim_product.csv")
    print("- dim_date.csv")
    print("- fact_sales.csv")
    print("- sales_by_country.csv")
    print("- sales_trend_monthly.csv")
    print("- sales_trend_monthly.png")
    print("- design_notes.txt")


if __name__ == "__main__":
    main()