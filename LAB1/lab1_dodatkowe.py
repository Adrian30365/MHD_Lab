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

    print("Wczytane dane:")
    print(df.head())

    # Konwersja daty
    df["order_date"] = pd.to_datetime(df["order_date"])

    # Kolumna wymagana w zadaniu
    df["total_value"] = df["quantity"] * df["unit_price"]

    # Dodatkowe kolumny czasu
    df["year"] = df["order_date"].dt.year
    df["month"] = df["order_date"].dt.month
    df["day"] = df["order_date"].dt.day

    # 1. Łączna wartość sprzedaży dla każdego kraju
    sales_by_country = (
        df.groupby("country")["total_value"]
        .sum()
        .reset_index()
        .sort_values("total_value", ascending=False)
    )

    print("\nSprzedaż według kraju:")
    print(sales_by_country)

    sales_by_country.to_csv(
        OUTPUT_DIR / "sales_by_country.csv",
        index=False
    )

    # 2. Łączna wartość sprzedaży dla każdego produktu
    sales_by_product = (
        df.groupby("product_name")["total_value"]
        .sum()
        .reset_index()
        .sort_values("total_value", ascending=False)
    )

    print("\nSprzedaż według produktu:")
    print(sales_by_product)

    sales_by_product.to_csv(
        OUTPUT_DIR / "sales_by_product.csv",
        index=False
    )

    # 3. Transakcje o wartości większej niż 1000
    df_high_value = df[df["total_value"] > 1000].copy()

    print("\nTransakcje o wartości większej niż 1000:")
    print(df_high_value)

    df_high_value.to_csv(
        OUTPUT_DIR / "high_value_sales.csv",
        index=False
    )

    # 4. Liczba transakcji w każdym kraju w wybranym zbiorze
    high_value_count_by_country = (
        df_high_value.groupby("country")
        .size()
        .reset_index(name="transaction_count")
        .sort_values("transaction_count", ascending=False)
    )

    print("\nLiczba transakcji high_value w każdym kraju:")
    print(high_value_count_by_country)

    high_value_count_by_country.to_csv(
        OUTPUT_DIR / "high_value_count_by_country.csv",
        index=False
    )

    print("\nZadanie dodatkowe wykonane.")
    print("Zapisane pliki:")
    print("- sales_by_country.csv")
    print("- sales_by_product.csv")
    print("- high_value_sales.csv")
    print("- high_value_count_by_country.csv")


if __name__ == "__main__":
    main()