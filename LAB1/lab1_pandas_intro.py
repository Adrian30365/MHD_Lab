import matplotlib
matplotlib.use("Agg")

from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

INPUT_FILE = DATA_DIR / "sales_raw.csv"


def main():
    df = pd.read_csv(INPUT_FILE)

    print("Pierwsze 5 rekordów:")
    print(df.head())

    print("\nLiczba wierszy i kolumn:")
    print(df.shape)

    print("\nNazwy kolumn:")
    print(df.columns)

    print("\nTypy danych:")
    print(df.dtypes)

    # Transformacje danych
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["total_value"] = df["quantity"] * df["unit_price"]
    df["year"] = df["order_date"].dt.year

    print("\nDane po transformacji:")
    print(df.head())

    # Agregacje
    total_sales = df["total_value"].sum()
    sales_by_country = df.groupby("country")["total_value"].sum().sort_values(ascending=False)
    sales_by_year = df.groupby("year")["total_value"].sum().sort_index()

    print("\nŁączna wartość sprzedaży:")
    print(total_sales)

    print("\nSprzedaż według kraju:")
    print(sales_by_country)

    print("\nSprzedaż według roku:")
    print(sales_by_year)

    # Przygotowanie danych analitycznych
    df_agg = (
        df.groupby(["country", "year"])["total_value"]
        .sum()
        .reset_index()
        .sort_values(["country", "year"])
    )

    output_file = OUTPUT_DIR / "sales_aggregated.csv"
    df_agg.to_csv(output_file, index=False)

    print(f"\nZapisano plik: {output_file}")


if __name__ == "__main__":
    main()