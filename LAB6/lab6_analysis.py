import matplotlib
matplotlib.use("Agg")

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def find_input_files():
    """
    Szuka plikow z danymi w katalogu LAB6/data.
    Podstawowo wystarczy Online_Retail.csv.
    Jesli istnieje Online_Retail_II.csv albo Online_Retail_II.xlsx, skrypt tez go wczyta.
    """
    possible_files = [
        DATA_DIR / "Online_Retail.csv",
        DATA_DIR / "online_retail.csv",
        DATA_DIR / "Online_Retail_II.csv",
        DATA_DIR / "online_retail_II.csv",
        DATA_DIR / "Online_Retail_II.xlsx",
        DATA_DIR / "online_retail_II.xlsx",
    ]

    existing_files = []
    seen = set()
    for file_path in possible_files:
        if file_path.exists() and file_path.resolve() not in seen:
            existing_files.append(file_path)
            seen.add(file_path.resolve())

    if not existing_files:
        raise FileNotFoundError(
            "Nie znaleziono danych. Umiesc plik Online_Retail.csv w folderze LAB6/data."
        )

    return existing_files


def read_retail_file(file_path: Path) -> pd.DataFrame:
    print(f"Wczytywanie pliku: {file_path}")

    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path, encoding="ISO-8859-1")
    elif file_path.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(file_path)
    else:
        raise ValueError(f"Nieobslugiwany format pliku: {file_path}")

    df["SourceFile"] = file_path.name
    return df


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ujednolicenie nazw kolumn na wypadek, gdyby rozne zrodla mialy drobne roznice.
    """
    rename_map = {
        "Invoice": "InvoiceNo",
        "InvoiceNo.": "InvoiceNo",
        "StockCode ": "StockCode",
        "Description ": "Description",
        "Price": "UnitPrice",
        "Customer ID": "CustomerID",
        "Customer Id": "CustomerID",
        "Invoice Date": "InvoiceDate",
    }

    return df.rename(columns=rename_map)


def load_data() -> pd.DataFrame:
    input_files = find_input_files()
    frames = []

    for file_path in input_files:
        df_part = read_retail_file(file_path)
        df_part = normalize_columns(df_part)
        frames.append(df_part)

    return pd.concat(frames, ignore_index=True)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Przygotowanie danych do analizy:
    - usuniecie brakujacych CustomerID,
    - usuniecie anulowanych faktur,
    - usuniecie zwrotow i blednych ilosci,
    - usuniecie blednych cen,
    - konwersja daty,
    - dodanie Revenue, Year i Month.
    """
    report = []
    report.append(f"Liczba rekordow przed czyszczeniem: {len(df)}")

    required_columns = [
        "InvoiceNo",
        "StockCode",
        "Description",
        "Quantity",
        "InvoiceDate",
        "UnitPrice",
        "CustomerID",
        "Country",
    ]

    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Brakuje wymaganych kolumn: {missing_columns}")

    df = df.copy()

    df["InvoiceNo"] = df["InvoiceNo"].astype(str)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
    df["CustomerID"] = pd.to_numeric(df["CustomerID"], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["CustomerID", "InvoiceDate", "Quantity", "UnitPrice", "Country"])
    report.append(f"Usunieto rekordy z brakami kluczowych danych: {before - len(df)}")

    before = len(df)
    df = df[~df["InvoiceNo"].str.startswith("C")]
    report.append(f"Usunieto anulowane faktury: {before - len(df)}")

    before = len(df)
    df = df[df["Quantity"] > 0]
    report.append(f"Usunieto rekordy z Quantity <= 0: {before - len(df)}")

    before = len(df)
    df = df[df["UnitPrice"] > 0]
    report.append(f"Usunieto rekordy z UnitPrice <= 0: {before - len(df)}")

    before = len(df)
    df = df.drop_duplicates()
    report.append(f"Usunieto duplikaty: {before - len(df)}")

    df["CustomerID"] = df["CustomerID"].astype(int)
    df["Revenue"] = df["Quantity"] * df["UnitPrice"]
    df["Year"] = df["InvoiceDate"].dt.year
    df["Month"] = df["InvoiceDate"].dt.month
    df["MonthName"] = df["InvoiceDate"].dt.strftime("%Y-%m")

    report.append(f"Liczba rekordow po czyszczeniu: {len(df)}")
    report.append(f"Laczny przychod po czyszczeniu: {df['Revenue'].sum():.2f}")

    with open(OUTPUT_DIR / "data_cleaning_report.txt", "w", encoding="utf-8") as file:
        file.write("\n".join(report))

    return df


def task_1_pivot(df: pd.DataFrame):
    pivot_country_month = pd.pivot_table(
        df,
        values="Revenue",
        index="Country",
        columns="Month",
        aggfunc="sum",
        fill_value=0,
    )
    pivot_country_month.to_csv(OUTPUT_DIR / "task1_pivot_country_month.csv")

    month_sales = (
        df.groupby("Month")["Revenue"]
        .sum()
        .reset_index()
        .sort_values("Revenue", ascending=False)
    )
    month_sales.to_csv(OUTPUT_DIR / "task1_month_sales_ranking.csv", index=False)
    month_sales.head(1).to_csv(OUTPUT_DIR / "task1_best_month.csv", index=False)

    print("\nZadanie 1 - pivot wykonane.")
    print("Najlepszy miesiac wg sprzedazy:")
    print(month_sales.head(1))

    return pivot_country_month, month_sales


def task_2_country_ranking(df: pd.DataFrame):
    country_ranking = (
        df.groupby("Country")["Revenue"]
        .sum()
        .reset_index()
        .sort_values("Revenue", ascending=False)
    )
    top10_countries = country_ranking.head(10)

    country_ranking.to_csv(OUTPUT_DIR / "task2_country_revenue_ranking.csv", index=False)
    top10_countries.to_csv(OUTPUT_DIR / "task2_top10_countries.csv", index=False)

    print("\nZadanie 2 - TOP 10 krajow:")
    print(top10_countries)

    return country_ranking, top10_countries


def task_3_customer_analysis(df: pd.DataFrame):
    customer_revenue = (
        df.groupby("CustomerID")["Revenue"]
        .sum()
        .reset_index()
        .sort_values("Revenue", ascending=False)
    )
    top10_customers = customer_revenue.head(10)
    avg_revenue = customer_revenue["Revenue"].mean()

    customer_summary = pd.DataFrame(
        {
            "metric": [
                "number_of_customers",
                "average_revenue_per_customer",
                "max_customer_revenue",
                "min_customer_revenue",
            ],
            "value": [
                len(customer_revenue),
                avg_revenue,
                customer_revenue["Revenue"].max(),
                customer_revenue["Revenue"].min(),
            ],
        }
    )

    customer_revenue.to_csv(OUTPUT_DIR / "task3_customer_revenue.csv", index=False)
    top10_customers.to_csv(OUTPUT_DIR / "task3_top10_customers.csv", index=False)
    customer_summary.to_csv(OUTPUT_DIR / "task3_customer_summary.csv", index=False)

    print("\nZadanie 3 - TOP 10 klientow:")
    print(top10_customers)
    print(f"\nSredni przychod na klienta: {avg_revenue:.2f}")

    return customer_revenue, top10_customers, avg_revenue


def task_4_country_segmentation(country_ranking: pd.DataFrame):
    segmented = country_ranking.copy()
    q25 = segmented["Revenue"].quantile(0.25)
    q75 = segmented["Revenue"].quantile(0.75)

    def assign_segment(revenue):
        if revenue >= q75:
            return "Top 25% - wysoki przychod"
        if revenue <= q25:
            return "Dolne 25% - niski przychod"
        return "Srodkowe 50% - sredni przychod"

    segmented["Segment"] = segmented["Revenue"].apply(assign_segment)
    segmented.to_csv(OUTPUT_DIR / "task4_country_segments.csv", index=False)

    segment_summary = (
        segmented.groupby("Segment")
        .agg(
            country_count=("Country", "count"),
            total_revenue=("Revenue", "sum"),
            avg_revenue=("Revenue", "mean"),
        )
        .reset_index()
        .sort_values("total_revenue", ascending=False)
    )
    segment_summary.to_csv(OUTPUT_DIR / "task4_segment_summary.csv", index=False)

    print("\nZadanie 4 - segmentacja krajow:")
    print(segmented)

    return segmented, segment_summary


def create_visualizations(country_ranking: pd.DataFrame, month_sales: pd.DataFrame, segmented: pd.DataFrame):
    top10 = country_ranking.head(10).sort_values("Revenue", ascending=True)

    plt.figure(figsize=(10, 6))
    plt.barh(top10["Country"], top10["Revenue"])
    plt.title("TOP 10 krajow wedlug przychodu")
    plt.xlabel("Revenue")
    plt.ylabel("Country")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "chart_top10_countries.png")
    plt.close()

    month_sales_sorted = month_sales.sort_values("Month")
    plt.figure(figsize=(10, 6))
    plt.plot(month_sales_sorted["Month"], month_sales_sorted["Revenue"], marker="o")
    plt.title("Sprzedaz wedlug miesiecy")
    plt.xlabel("Month")
    plt.ylabel("Revenue")
    plt.xticks(month_sales_sorted["Month"])
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "chart_monthly_revenue.png")
    plt.close()

    segment_summary_for_chart = (
        segmented.groupby("Segment")["Revenue"]
        .sum()
        .reset_index()
        .sort_values("Revenue", ascending=True)
    )
    plt.figure(figsize=(10, 6))
    plt.barh(segment_summary_for_chart["Segment"], segment_summary_for_chart["Revenue"])
    plt.title("Przychod wedlug segmentow krajow")
    plt.xlabel("Revenue")
    plt.ylabel("Segment")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "chart_segment_revenue.png")
    plt.close()


def task_5_conclusions(top10_countries, month_sales, segmented, avg_revenue):
    best_country = top10_countries.iloc[0]
    best_month = month_sales.iloc[0]
    top_segment = segmented[segmented["Segment"] == "Top 25% - wysoki przychod"]
    top_segment_revenue_share = top_segment["Revenue"].sum() / segmented["Revenue"].sum() * 100

    monthly_max = month_sales["Revenue"].max()
    monthly_min = month_sales["Revenue"].min()
    seasonality_ratio = monthly_max / monthly_min if monthly_min != 0 else 0

    conclusions = f"""
LAB6 - Wnioski z analizy danych

1. Ktore kraje sa kluczowe?

Najwazniejszym krajem pod wzgledem przychodu jest: {best_country['Country']}.
Przychod tego kraju wynosi: {best_country['Revenue']:.2f}.
W grupie kluczowych krajow znajduja sie kraje z segmentu "Top 25% - wysoki przychod".

2. Czy sprzedaz jest rownomierna miedzy krajami?

Sprzedaz nie jest rownomierna miedzy krajami.
Kraje z segmentu Top 25% odpowiadaja za okolo {top_segment_revenue_share:.2f}% calkowitego przychodu.
Oznacza to koncentracje sprzedazy w ograniczonej liczbie krajow.

3. Czy widac sezonowosc?

Najwyzsza sprzedaz odnotowano w miesiacu: {int(best_month['Month'])}.
Wartosc sprzedazy w tym miesiacu wynosi: {best_month['Revenue']:.2f}.
Relacja najlepszego miesiaca do najslabszego miesiaca wynosi okolo {seasonality_ratio:.2f}, co wskazuje,
ze sprzedaz zmienia sie w czasie i mozna analizowac ja sezonowo.

4. Analiza klientow

Sredni przychod na klienta wynosi: {avg_revenue:.2f}.
TOP 10 klientow ma duzo wieksze wartosci przychodu niz przecietny klient, dlatego analiza klientow
moze byc przydatna do segmentacji i identyfikacji najbardziej wartosciowych odbiorcow.

Podsumowanie:
Analiza pokazuje, ze dane sprzedazowe mozna skutecznie analizowac przy uzyciu tabel pivot,
rankingow i prostej segmentacji. Najwieksze znaczenie biznesowe maja kraje i klienci generujacy
najwiekszy przychod, a wymiar czasu pozwala wykrywac zmiennosc sprzedazy miedzy miesiacami.
"""
    with open(OUTPUT_DIR / "task5_conclusions.txt", "w", encoding="utf-8") as file:
        file.write(conclusions)

    print("\nZadanie 5 - zapisano wnioski do task5_conclusions.txt")


def main():
    print("LAB6 - Analiza danych")
    print("====================")

    df_raw = load_data()

    print("\nDane surowe:")
    print(df_raw.head())
    print(df_raw.shape)

    df = clean_data(df_raw)

    print("\nDane po czyszczeniu:")
    print(df.head())
    print(df.shape)

    df.head(1000).to_csv(OUTPUT_DIR / "prepared_sales_data_sample.csv", index=False)

    pivot_country_month, month_sales = task_1_pivot(df)
    country_ranking, top10_countries = task_2_country_ranking(df)
    customer_revenue, top10_customers, avg_revenue = task_3_customer_analysis(df)
    segmented, segment_summary = task_4_country_segmentation(country_ranking)
    create_visualizations(country_ranking, month_sales, segmented)
    task_5_conclusions(top10_countries, month_sales, segmented, avg_revenue)

    print("\nLAB6 zakonczone.")
    print(f"Wyniki zapisano w folderze: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
