import matplotlib
matplotlib.use("Agg")

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
OLAP_DIR = OUTPUT_DIR / "olap"

OLAP_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLUMNS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]


def find_file(possible_paths):
    for path in possible_paths:
        if path.exists():
            return path
    return None


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ujednolica nazwy kolumn z Online Retail oraz Online Retail II."""
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]

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

    df = df.rename(columns={col: rename_map.get(col, col) for col in df.columns})

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Brak wymaganych kolumn po ujednoliceniu: {missing_columns}")

    return df[REQUIRED_COLUMNS]


def read_online_retail_csv(path: Path, source_name: str) -> pd.DataFrame:
    print(f"Wczytywanie CSV: {path}")
    df = pd.read_csv(path, encoding="ISO-8859-1")
    df = normalize_columns(df)
    df["Source"] = source_name
    return df


def read_online_retail_ii_excel(path: Path, source_name: str) -> pd.DataFrame:
    print(f"Wczytywanie XLSX: {path}")
    workbook = pd.ExcelFile(path)
    frames = []

    for sheet_name in workbook.sheet_names:
        print(f"  Arkusz: {sheet_name}")
        sheet_df = pd.read_excel(workbook, sheet_name=sheet_name)
        sheet_df = normalize_columns(sheet_df)
        sheet_df["Source"] = f"{source_name}_{sheet_name}"
        frames.append(sheet_df)

    return pd.concat(frames, ignore_index=True)


def extract_data() -> pd.DataFrame:
    """Extract: wczytanie Online_Retail.csv oraz drugiego zbioru, jeśli istnieje."""
    online_retail_path = find_file([
        DATA_DIR / "Online_Retail.csv",
        BASE_DIR.parent / "LAB2" / "data" / "Online_Retail.csv",
        BASE_DIR.parent / "LAB4" / "data" / "Online_Retail.csv",
    ])

    if online_retail_path is None:
        raise FileNotFoundError(
            "Nie znaleziono Online_Retail.csv. Umieść plik w LAB5/data/ albo skopiuj go z LAB2/data/."
        )

    frames = [read_online_retail_csv(online_retail_path, "Online_Retail")]

    # Drugi zbiór zgodnie z poleceniem może występować jako CSV albo XLSX.
    online_retail_ii_csv = find_file([
        DATA_DIR / "Online_Retail_II.csv",
        DATA_DIR / "online_retail_II.csv",
        DATA_DIR / "online_retail_ii.csv",
        BASE_DIR.parent / "LAB4" / "data" / "Online_Retail_II.csv",
        BASE_DIR.parent / "LAB4" / "data" / "online_retail_II.csv",
    ])

    online_retail_ii_xlsx = find_file([
        DATA_DIR / "Online_Retail_II.xlsx",
        DATA_DIR / "online_retail_II.xlsx",
        DATA_DIR / "online_retail_ii.xlsx",
        BASE_DIR.parent / "LAB4" / "data" / "Online_Retail_II.xlsx",
        BASE_DIR.parent / "LAB4" / "data" / "online_retail_II.xlsx",
    ])

    if online_retail_ii_csv is not None:
        frames.append(read_online_retail_csv(online_retail_ii_csv, "Online_Retail_II"))
    elif online_retail_ii_xlsx is not None:
        frames.append(read_online_retail_ii_excel(online_retail_ii_xlsx, "Online_Retail_II"))
    else:
        print("UWAGA: Nie znaleziono drugiego zbioru Online_Retail_II. Analiza zostanie wykonana tylko na Online_Retail.csv.")

    df = pd.concat(frames, ignore_index=True)

    extract_report = []
    extract_report.append("LAB5 - EXTRACT REPORT")
    extract_report.append(f"Liczba rekordów po wczytaniu: {len(df)}")
    extract_report.append(f"Liczba kolumn po wczytaniu: {len(df.columns)}")
    extract_report.append("Kolumny: " + ", ".join(df.columns))
    extract_report.append("\nBraki danych przed czyszczeniem:")
    extract_report.append(str(df.isna().sum()))

    (OLAP_DIR / "extract_report.txt").write_text("\n".join(extract_report), encoding="utf-8")

    source_counts = df.groupby("Source").size().reset_index(name="row_count")
    source_counts.to_csv(OLAP_DIR / "source_row_counts.csv", index=False)

    print("\nPierwsze 5 rekordów:")
    print(df.head())
    print("\nStruktura danych:")
    print(df.info())
    print("\nStatystyki opisowe:")
    print(df.describe(include="all"))

    return df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Transform: czyszczenie, konwersja typów oraz przygotowanie wymiarów czasu i miary TotalPrice."""
    before_rows = len(df)
    before_duplicates = df.duplicated().sum()

    df = df.copy()
    df = df.drop_duplicates()

    df["InvoiceNo"] = df["InvoiceNo"].astype(str)
    df["StockCode"] = df["StockCode"].astype(str)
    df["Description"] = df["Description"].fillna("Unknown product").astype(str)
    df["Country"] = df["Country"].fillna("Unknown country").astype(str)

    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
    df["CustomerID"] = pd.to_numeric(df["CustomerID"], errors="coerce")
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")

    rows_after_type_conversion = len(df)

    # Czyszczenie zgodne z poleceniem: brakujące CustomerID, Quantity <= 0, dodatkowo błędne daty i ceny.
    df = df.dropna(subset=["CustomerID", "InvoiceDate", "Quantity", "UnitPrice"])
    df = df[~df["InvoiceNo"].str.startswith("C", na=False)]
    df = df[df["Quantity"] > 0]
    df = df[df["UnitPrice"] > 0]

    df["CustomerID"] = df["CustomerID"].astype(int)
    df["Year"] = df["InvoiceDate"].dt.year
    df["Month"] = df["InvoiceDate"].dt.month
    df["Day"] = df["InvoiceDate"].dt.day
    df["YearMonth"] = df["InvoiceDate"].dt.to_period("M").astype(str)

    # Miara faktu wymagana w OLAP.
    df["TotalPrice"] = df["Quantity"] * df["UnitPrice"]

    quality_report = []
    quality_report.append("LAB5 - TRANSFORM / DATA QUALITY REPORT")
    quality_report.append(f"Rekordy przed czyszczeniem: {before_rows}")
    quality_report.append(f"Duplikaty przed czyszczeniem: {before_duplicates}")
    quality_report.append(f"Rekordy po konwersji typów: {rows_after_type_conversion}")
    quality_report.append(f"Rekordy po czyszczeniu: {len(df)}")
    quality_report.append(f"Usunięte rekordy: {before_rows - len(df)}")
    quality_report.append("\nBraki danych po czyszczeniu:")
    quality_report.append(str(df.isna().sum()))

    (OLAP_DIR / "transform_quality_report.txt").write_text("\n".join(quality_report), encoding="utf-8")

    return df


def olap_operations(df: pd.DataFrame) -> None:
    """Operacje OLAP: roll-up, drill-down, slice, dice, pivot/cube oraz zadania 1-5."""

    # Roll-up: sprzedaż na poziomie roku.
    rollup_year = (
        df.groupby("Year", as_index=False)
        .agg(TotalPrice=("TotalPrice", "sum"), Quantity=("Quantity", "sum"))
        .sort_values("Year")
    )
    rollup_year.to_csv(OLAP_DIR / "rollup_sales_by_year.csv", index=False)

    # Drill-down: większa szczegółowość rok + miesiąc.
    drilldown_year_month = (
        df.groupby(["Year", "Month"], as_index=False)
        .agg(TotalPrice=("TotalPrice", "sum"), Quantity=("Quantity", "sum"))
        .sort_values(["Year", "Month"])
    )
    drilldown_year_month.to_csv(OLAP_DIR / "drilldown_sales_by_year_month.csv", index=False)

    # Slice: wybór jednego kraju.
    slice_uk = df[df["Country"] == "United Kingdom"]
    slice_uk_summary = (
        slice_uk.groupby(["Year", "Month"], as_index=False)
        .agg(TotalPrice=("TotalPrice", "sum"), Quantity=("Quantity", "sum"))
        .sort_values(["Year", "Month"])
    )
    slice_uk_summary.to_csv(OLAP_DIR / "slice_united_kingdom_monthly.csv", index=False)

    # Dice: kraj + rok.
    dice_uk_2011 = df[(df["Country"] == "United Kingdom") & (df["Year"] == 2011)]
    dice_uk_2011_summary = (
        dice_uk_2011.groupby("Month", as_index=False)
        .agg(TotalPrice=("TotalPrice", "sum"), Quantity=("Quantity", "sum"))
        .sort_values("Month")
    )
    dice_uk_2011_summary.to_csv(OLAP_DIR / "dice_united_kingdom_2011_monthly.csv", index=False)

    # Pivot: kraj x rok.
    pivot_country_year = pd.pivot_table(
        df,
        values="TotalPrice",
        index="Country",
        columns="Year",
        aggfunc="sum",
        fill_value=0,
    )
    pivot_country_year.to_csv(OLAP_DIR / "pivot_country_year.csv")

    # Zadanie 1: Top 10 krajów pod względem sprzedaży.
    top_10_countries = (
        df.groupby("Country", as_index=False)
        .agg(TotalPrice=("TotalPrice", "sum"), Quantity=("Quantity", "sum"))
        .sort_values("TotalPrice", ascending=False)
        .head(10)
    )
    top_10_countries.to_csv(OLAP_DIR / "task1_top_10_countries.csv", index=False)

    # Zadanie 2: miesiąc o największej sprzedaży.
    monthly_sales = (
        df.groupby(["Year", "Month", "YearMonth"], as_index=False)
        .agg(TotalPrice=("TotalPrice", "sum"), Quantity=("Quantity", "sum"))
        .sort_values("TotalPrice", ascending=False)
    )
    monthly_sales.to_csv(OLAP_DIR / "monthly_sales_ranking.csv", index=False)
    best_month = monthly_sales.head(1)
    best_month.to_csv(OLAP_DIR / "task2_best_sales_month.csv", index=False)

    # Zadanie 3: kostka kraj x miesiąc, wartość sprzedaży.
    cube_country_month = pd.pivot_table(
        df,
        values="TotalPrice",
        index="Country",
        columns="Month",
        aggfunc="sum",
        fill_value=0,
    )
    cube_country_month.to_csv(OLAP_DIR / "task3_cube_country_month.csv")

    # Zadanie 4: dla każdego kraju rok z najwyższą sprzedażą.
    country_year_sales = (
        df.groupby(["Country", "Year"], as_index=False)
        .agg(TotalPrice=("TotalPrice", "sum"), Quantity=("Quantity", "sum"))
        .sort_values(["Country", "TotalPrice"], ascending=[True, False])
    )
    best_year_by_country = country_year_sales.groupby("Country", as_index=False).head(1)
    best_year_by_country.to_csv(OLAP_DIR / "task4_best_year_by_country.csv", index=False)

    # Zadanie 5 challenge: Top 5 produktów w każdym kraju.
    product_country_sales = (
        df.groupby(["Country", "StockCode", "Description"], as_index=False)
        .agg(TotalPrice=("TotalPrice", "sum"), Quantity=("Quantity", "sum"))
        .sort_values(["Country", "TotalPrice"], ascending=[True, False])
    )
    top_5_products_by_country = product_country_sales.groupby("Country", as_index=False).head(5)
    top_5_products_by_country.to_csv(OLAP_DIR / "task5_top_5_products_by_country.csv", index=False)

    # Bonus: heatmap. Dla czytelności pokazujemy Top 15 krajów.
    top_countries = top_10_countries["Country"].tolist()
    extra_countries = (
        df.groupby("Country")["TotalPrice"].sum().sort_values(ascending=False).head(15).index.tolist()
    )
    selected_countries = list(dict.fromkeys(top_countries + extra_countries))[:15]

    heatmap_data = cube_country_month.loc[cube_country_month.index.isin(selected_countries)]

    plt.figure(figsize=(12, 8))
    plt.imshow(heatmap_data.values, aspect="auto")
    plt.colorbar(label="TotalPrice")
    plt.xticks(range(len(heatmap_data.columns)), heatmap_data.columns)
    plt.yticks(range(len(heatmap_data.index)), heatmap_data.index)
    plt.xlabel("Month")
    plt.ylabel("Country")
    plt.title("Heatmap sprzedaży: kraj x miesiąc")
    plt.tight_layout()
    plt.savefig(OLAP_DIR / "bonus_heatmap_country_month.png")
    plt.close()

    # Krótki opis decyzji i wyników.
    notes = f"""
LAB5 - mechanizmy OLAP i analiza danych

Model OLAP:
- Fakty / miary: TotalPrice oraz Quantity.
- Wymiary: Country, Year, Month, StockCode.

Wykonane operacje:
1. Roll-up - agregacja sprzedaży do poziomu roku.
2. Drill-down - zejście do poziomu roku i miesiąca.
3. Slice - wybór jednego kraju: United Kingdom.
4. Dice - wybór kraju United Kingdom oraz roku 2011.
5. Pivot / kostka danych - Country x Year oraz Country x Month.

Wyniki zadań:
- Top 10 krajów zapisano w task1_top_10_countries.csv.
- Miesiąc o największej sprzedaży zapisano w task2_best_sales_month.csv.
- Kostkę kraj x miesiąc zapisano w task3_cube_country_month.csv.
- Najlepszy rok dla każdego kraju zapisano w task4_best_year_by_country.csv.
- Top 5 produktów w każdym kraju zapisano w task5_top_5_products_by_country.csv.
- Heatmapę zapisano w bonus_heatmap_country_month.png.

Założenia ETL:
Usunięto brakujące CustomerID, anulowane faktury, Quantity <= 0, UnitPrice <= 0,
błędne daty oraz duplikaty. Miara TotalPrice została policzona jako Quantity * UnitPrice.
""".strip()

    (OLAP_DIR / "olap_notes.txt").write_text(notes, encoding="utf-8")

    print("\n=== WYNIKI GŁÓWNE ===")
    print("\nTop 10 krajów:")
    print(top_10_countries)

    print("\nMiesiąc o największej sprzedaży:")
    print(best_month)

    print("\nZapisano wyniki OLAP do folderu:")
    print(OLAP_DIR)


def main():
    df_raw = extract_data()
    df_clean = transform_data(df_raw)
    olap_operations(df_clean)

    print("\nLAB5 zakończone poprawnie.")


if __name__ == "__main__":
    main()
