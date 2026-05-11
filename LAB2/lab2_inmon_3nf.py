import matplotlib
matplotlib.use("Agg")

from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
INMON_DIR = OUTPUT_DIR / "inmon_3nf"

INMON_DIR.mkdir(parents=True, exist_ok=True)

INPUT_FILE = DATA_DIR / "Online_Retail.csv"


def normalize_customer_id(row):
    if pd.isna(row["CustomerID"]):
        return f"UNKNOWN_{row['Country']}"
    return str(int(row["CustomerID"]))


def main():
    # Zadanie 1: wczytanie danych - staging
    df = pd.read_csv(INPUT_FILE, encoding="ISO-8859-1")

    print("=== STAGING: Online_Retail.csv ===")
    print("Liczba rekordów i kolumn:")
    print(df.shape)

    print("\nPierwsze 5 rekordów:")
    print(df.head())

    print("\nNazwy kolumn:")
    print(df.columns)

    print("\nTypy danych:")
    print(df.dtypes)

    # Podstawowe przygotowanie danych
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df["Description"] = df["Description"].fillna("Unknown product")
    df["Country"] = df["Country"].fillna("Unknown country")
    df["CustomerBusinessKey"] = df.apply(normalize_customer_id, axis=1)

    df["IsCancelled"] = df["InvoiceNo"].astype(str).str.startswith("C")
    df["IsReturn"] = df["Quantity"] < 0

    # Zadanie 2: identyfikacja encji
    entity_description = """
LAB2 - Identyfikacja encji biznesowych

1. Country
   Klucz główny: country_id
   Atrybuty: country_name

2. Customer
   Klucz główny: customer_key
   Klucz biznesowy: CustomerBusinessKey / CustomerID
   Atrybuty: customer_id_source, country_id

3. Product
   Klucz główny: product_key
   Klucz biznesowy: StockCode
   Atrybuty: description

4. Invoice
   Klucz główny: invoice_no
   Atrybuty: invoice_date, customer_key, country_id, is_cancelled

5. InvoiceLine
   Klucz główny: invoice_line_id
   Klucze obce: invoice_no, product_key
   Atrybuty: quantity, unit_price, is_return

Komentarz:
Dane źródłowe są w jednym dużym pliku CSV. W modelu 3NF rozdzielamy je
na encje, aby ograniczyć redundancję i zachować relacje przez klucze.
"""

    with open(INMON_DIR / "entity_description.txt", "w", encoding="utf-8") as file:
        file.write(entity_description)

    # Zadanie 3: model 3NF

    # COUNTRY
    countries = (
        df[["Country"]]
        .drop_duplicates()
        .sort_values("Country")
        .reset_index(drop=True)
    )
    countries.insert(0, "country_id", range(1, len(countries) + 1))
    countries = countries.rename(columns={"Country": "country_name"})

    df = df.merge(
        countries,
        left_on="Country",
        right_on="country_name",
        how="left"
    )

    # CUSTOMER
    customers = (
        df[["CustomerBusinessKey", "CustomerID", "country_id"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    customers.insert(0, "customer_key", range(1, len(customers) + 1))
    customers = customers.rename(
        columns={
            "CustomerBusinessKey": "customer_business_key",
            "CustomerID": "customer_id_source"
        }
    )

    df = df.merge(
        customers[["customer_key", "customer_business_key"]],
        left_on="CustomerBusinessKey",
        right_on="customer_business_key",
        how="left"
    )

    # PRODUCT
    products = (
        df.groupby("StockCode", as_index=False)
        .agg(description=("Description", lambda x: x.dropna().mode().iloc[0] if not x.dropna().empty else "Unknown product"))
        .sort_values("StockCode")
        .reset_index(drop=True)
    )
    products.insert(0, "product_key", range(1, len(products) + 1))
    products = products.rename(columns={"StockCode": "stock_code"})

    df = df.merge(
        products[["product_key", "stock_code"]],
        left_on="StockCode",
        right_on="stock_code",
        how="left"
    )

    # INVOICE
    invoices = (
        df[["InvoiceNo", "InvoiceDate", "customer_key", "country_id", "IsCancelled"]]
        .drop_duplicates(subset=["InvoiceNo"])
        .sort_values("InvoiceNo")
        .reset_index(drop=True)
    )
    invoices = invoices.rename(
        columns={
            "InvoiceNo": "invoice_no",
            "InvoiceDate": "invoice_date",
            "IsCancelled": "is_cancelled"
        }
    )

    # INVOICE LINE
    invoice_lines = df[
        [
            "InvoiceNo",
            "product_key",
            "Quantity",
            "UnitPrice",
            "IsReturn"
        ]
    ].copy()

    invoice_lines.insert(0, "invoice_line_id", range(1, len(invoice_lines) + 1))
    invoice_lines = invoice_lines.rename(
        columns={
            "InvoiceNo": "invoice_no",
            "Quantity": "quantity",
            "UnitPrice": "unit_price",
            "IsReturn": "is_return"
        }
    )

    # Zapis tabel 3NF
    countries.to_csv(INMON_DIR / "country_3nf.csv", index=False)
    customers.to_csv(INMON_DIR / "customer_3nf.csv", index=False)
    products.to_csv(INMON_DIR / "product_3nf.csv", index=False)
    invoices.to_csv(INMON_DIR / "invoice_3nf.csv", index=False)
    invoice_lines.to_csv(INMON_DIR / "invoice_line_3nf.csv", index=False)

    # Zadanie 4: refleksja
    reflection = """
LAB2 - Refleksja

Dlaczego model 3NF nie jest wygodny do analiz OLAP?

Model 3NF dobrze ogranicza redundancję i nadaje się do integracji danych,
ale nie jest wygodny do szybkich analiz OLAP, ponieważ dane są rozbite na
wiele tabel. Aby policzyć np. sprzedaż według kraju, produktu i miesiąca,
trzeba łączyć kilka tabel: invoice_line, invoice, customer, country oraz product.

Co wymagałoby wielu JOIN-ów?

Przykład: analiza sprzedaży według kraju i produktu wymaga połączenia:
invoice_line -> invoice -> country oraz invoice_line -> product.
Analiza sprzedaży według klienta, kraju i produktu wymagałaby jeszcze
dołączenia tabeli customer. Dlatego w analizach częściej stosuje się model
gwiazdy Kimbala, gdzie tabela faktów jest bezpośrednio połączona z wymiarami.
"""

    with open(INMON_DIR / "reflection.txt", "w", encoding="utf-8") as file:
        file.write(reflection)

    print("\nZapisano tabele modelu 3NF do folderu:")
    print(INMON_DIR)

    print("\nUtworzone pliki:")
    print("- country_3nf.csv")
    print("- customer_3nf.csv")
    print("- product_3nf.csv")
    print("- invoice_3nf.csv")
    print("- invoice_line_3nf.csv")
    print("- entity_description.txt")
    print("- reflection.txt")


if __name__ == "__main__":
    main()