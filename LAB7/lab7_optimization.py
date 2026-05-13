import time
from pathlib import Path
from typing import Callable, Dict, Tuple

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
OPT_DIR = OUTPUT_DIR / "optimization"

OPT_DIR.mkdir(parents=True, exist_ok=True)

INPUT_FILE = DATA_DIR / "Online_Retail.csv"


def measure_time(function: Callable[[], object], repeats: int = 5) -> Tuple[object, float, float]:
    """Mierzy czas wykonania operacji kilka razy i zwraca wynik, najlepszy czas oraz średni czas."""
    times = []
    result = None

    for _ in range(repeats):
        start = time.perf_counter()
        result = function()
        end = time.perf_counter()
        times.append(end - start)

    return result, min(times), sum(times) / len(times)


def memory_mb(df: pd.DataFrame) -> float:
    """Zwraca zużycie pamięci DataFrame w MB."""
    return df.memory_usage(deep=True).sum() / (1024 ** 2)


def load_data() -> Tuple[pd.DataFrame, float]:
    """Etap 1: wczytanie danych i pomiar czasu."""
    start = time.perf_counter()
    df = pd.read_csv(INPUT_FILE, encoding="ISO-8859-1")
    end = time.perf_counter()
    return df, end - start


def prepare_for_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Przygotowanie kolumn analitycznych.
    To nie jest jeszcze optymalizacja pamięci, tylko ujednolicenie danych,
    aby dało się wykonać te same operacje przed i po optymalizacji.
    """
    df = df.copy()

    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
    df["CustomerID"] = pd.to_numeric(df["CustomerID"], errors="coerce")

    df["Revenue"] = df["Quantity"] * df["UnitPrice"]
    df["Month"] = df["InvoiceDate"].dt.month
    df["Year"] = df["InvoiceDate"].dt.year

    return df


def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Etap 2: optymalizacja pamięci.
    - kolumny tekstowe zmieniamy na category,
    - liczby całkowite i zmiennoprzecinkowe downcastujemy.
    """
    df_opt = df.copy()

    text_columns = ["InvoiceNo", "StockCode", "Description", "Country"]
    for column in text_columns:
        if column in df_opt.columns:
            df_opt[column] = df_opt[column].astype("category")

    if "Quantity" in df_opt.columns:
        df_opt["Quantity"] = pd.to_numeric(df_opt["Quantity"], downcast="integer")

    if "UnitPrice" in df_opt.columns:
        df_opt["UnitPrice"] = pd.to_numeric(df_opt["UnitPrice"], downcast="float")

    if "CustomerID" in df_opt.columns:
        df_opt["CustomerID"] = pd.to_numeric(df_opt["CustomerID"], errors="coerce").astype("Int32")

    if "Revenue" in df_opt.columns:
        df_opt["Revenue"] = pd.to_numeric(df_opt["Revenue"], downcast="float")

    if "Month" in df_opt.columns:
        df_opt["Month"] = pd.to_numeric(df_opt["Month"], downcast="integer")

    if "Year" in df_opt.columns:
        df_opt["Year"] = pd.to_numeric(df_opt["Year"], downcast="integer")

    return df_opt


def run_analytic_operations(df: pd.DataFrame, label: str) -> Dict[str, Dict[str, float]]:
    """Etap 3: pomiar wydajności operacji analitycznych."""
    timings = {}

    result, best, avg = measure_time(
        lambda: df.groupby("Country", observed=True)["Revenue"].sum().sort_values(ascending=False)
    )
    result.to_csv(OPT_DIR / f"{label}_sales_by_country.csv")
    timings["sum_sales_by_country"] = {"best_time_sec": best, "avg_time_sec": avg}

    result, best, avg = measure_time(
        lambda: df.groupby("Month", observed=True)["Revenue"].sum().sort_index()
    )
    result.to_csv(OPT_DIR / f"{label}_sales_by_month.csv")
    timings["sum_sales_by_month"] = {"best_time_sec": best, "avg_time_sec": avg}

    result, best, avg = measure_time(
        lambda: df.groupby("CustomerID", observed=True)["Revenue"].sum().sort_values(ascending=False).head(10)
    )
    result.to_csv(OPT_DIR / f"{label}_top10_customers.csv")
    timings["top10_customers_by_revenue"] = {"best_time_sec": best, "avg_time_sec": avg}

    result, best, avg = measure_time(
        lambda: df[df["Country"].astype(str) == "United Kingdom"]
    )
    result.head(1000).to_csv(OPT_DIR / f"{label}_uk_products_sample.csv", index=False)
    timings["filter_united_kingdom"] = {"best_time_sec": best, "avg_time_sec": avg, "rows": len(result)}

    result, best, avg = measure_time(
        lambda: df[df["Revenue"] > 1000]
    )
    result.head(1000).to_csv(OPT_DIR / f"{label}_sales_over_1000_sample.csv", index=False)
    timings["filter_sales_over_1000"] = {"best_time_sec": best, "avg_time_sec": avg, "rows": len(result)}

    return timings


def save_basic_analysis(df_raw: pd.DataFrame, load_time: float) -> None:
    """Zapis informacji z etapu 1."""
    df_raw.isna().sum().reset_index().rename(
        columns={"index": "column", 0: "missing_values"}
    ).to_csv(OPT_DIR / "missing_values.csv", index=False)

    df_raw.dtypes.astype(str).reset_index().rename(
        columns={"index": "column", 0: "dtype"}
    ).to_csv(OPT_DIR / "dtypes_before_preparation.csv", index=False)

    with open(OPT_DIR / "extract_analysis.txt", "w", encoding="utf-8") as file:
        file.write("LAB7 - Etap 1: Wczytanie i analiza danych\n\n")
        file.write(f"Czas wczytywania danych: {load_time:.6f} s\n")
        file.write(f"Liczba rekordów: {len(df_raw)}\n")
        file.write(f"Liczba kolumn: {len(df_raw.columns)}\n")
        file.write(f"Zużycie pamięci przed przygotowaniem: {memory_mb(df_raw):.4f} MB\n\n")
        file.write("Kolumny:\n")
        for column in df_raw.columns:
            file.write(f"- {column}: {df_raw[column].dtype}\n")
        file.write("\nPierwsze 5 rekordów:\n")
        file.write(df_raw.head().to_string())


def build_conclusions(memory_before: float, memory_after: float, comparison: pd.DataFrame) -> str:
    memory_reduction = memory_before - memory_after
    memory_reduction_percent = (memory_reduction / memory_before * 100) if memory_before else 0

    faster_ops = comparison[comparison["speedup_ratio"] > 1]["operation"].tolist()
    slower_ops = comparison[comparison["speedup_ratio"] < 1]["operation"].tolist()

    return f"""LAB7 - Wnioski

1. Wpływ optymalizacji pamięci

Przed optymalizacją DataFrame zajmował około {memory_before:.2f} MB.
Po optymalizacji DataFrame zajmował około {memory_after:.2f} MB.
Oznacza to zmniejszenie zużycia pamięci o około {memory_reduction:.2f} MB,
czyli o około {memory_reduction_percent:.2f}%.

Największy wpływ miała konwersja kolumn tekstowych, takich jak Country,
StockCode, Description i InvoiceNo, do typu category. W danych sprzedażowych
wiele wartości powtarza się, więc typ category pozwala przechowywać je
bardziej oszczędnie.

2. Które operacje przyspieszyły?

Operacje, które w tym uruchomieniu były szybsze po optymalizacji:
{", ".join(faster_ops) if faster_ops else "brak jednoznacznego przyspieszenia"}.

Operacje, które w tym uruchomieniu były wolniejsze po optymalizacji:
{", ".join(slower_ops) if slower_ops else "brak jednoznacznego spowolnienia"}.

3. Jaki był wpływ optymalizacji typów danych?

Optymalizacja typów danych zmniejszyła zużycie pamięci i może przyspieszyć
część operacji grupowania, sortowania lub filtrowania. Mniejsze typy liczbowe
oraz category ograniczają ilość danych, które Pandas musi przetwarzać w pamięci.

4. Czy zmniejszenie pamięci zawsze oznacza wzrost wydajności?

Nie zawsze. Zmniejszenie pamięci zwykle pomaga, ale nie gwarantuje
przyspieszenia każdej operacji. Niektóre operacje na typie category albo na
typach nullable mogą mieć dodatkowy koszt przetwarzania. Dlatego w ETL i BI
nie wystarczy tylko zmienić typy danych - trzeba również mierzyć czas działania
konkretnych operacji analitycznych.
"""


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Brak pliku: {INPUT_FILE}. Umieść Online_Retail.csv w folderze LAB7/data/."
        )

    df_raw, load_time = load_data()
    save_basic_analysis(df_raw, load_time)

    print("=== LAB7: Optymalizacja zapytań analitycznych w Pandas ===")
    print(f"Wczytano dane: {df_raw.shape}")
    print(f"Czas wczytywania: {load_time:.6f} s")

    df_before = prepare_for_analysis(df_raw)

    memory_before = memory_mb(df_before)
    dtypes_before = df_before.dtypes.astype(str).reset_index()
    dtypes_before.columns = ["column", "dtype_before"]
    dtypes_before.to_csv(OPT_DIR / "dtypes_before_optimization.csv", index=False)

    df_after = optimize_dataframe(df_before)
    memory_after = memory_mb(df_after)

    dtypes_after = df_after.dtypes.astype(str).reset_index()
    dtypes_after.columns = ["column", "dtype_after"]
    dtypes_after.to_csv(OPT_DIR / "dtypes_after_optimization.csv", index=False)

    memory_comparison = pd.DataFrame(
        {
            "version": ["before_optimization", "after_optimization"],
            "memory_mb": [memory_before, memory_after],
        }
    )
    memory_comparison["difference_vs_before_mb"] = memory_comparison["memory_mb"] - memory_before
    memory_comparison.to_csv(OPT_DIR / "memory_comparison.csv", index=False)

    print(f"Pamięć przed optymalizacją: {memory_before:.4f} MB")
    print(f"Pamięć po optymalizacji: {memory_after:.4f} MB")

    timings_before = run_analytic_operations(df_before, "before")
    timings_after = run_analytic_operations(df_after, "after")

    rows = []
    for operation in timings_before:
        before_best = timings_before[operation]["best_time_sec"]
        after_best = timings_after[operation]["best_time_sec"]

        rows.append(
            {
                "operation": operation,
                "before_best_time_sec": before_best,
                "after_best_time_sec": after_best,
                "before_avg_time_sec": timings_before[operation]["avg_time_sec"],
                "after_avg_time_sec": timings_after[operation]["avg_time_sec"],
                "speedup_ratio": before_best / after_best if after_best else None,
                "rows_before": timings_before[operation].get("rows", ""),
                "rows_after": timings_after[operation].get("rows", ""),
            }
        )

    comparison = pd.DataFrame(rows)
    comparison.to_csv(OPT_DIR / "operation_times_comparison.csv", index=False)

    filter_summary = comparison[comparison["operation"].str.startswith("filter_")][
        ["operation", "rows_before", "rows_after"]
    ]
    filter_summary.to_csv(OPT_DIR / "filter_summary.csv", index=False)

    conclusions = build_conclusions(memory_before, memory_after, comparison)
    with open(OPT_DIR / "conclusions.txt", "w", encoding="utf-8") as file:
        file.write(conclusions)

    print("\nZapisano wyniki do folderu:")
    print(OPT_DIR)
    print("\nNajważniejsze pliki:")
    print("- extract_analysis.txt")
    print("- missing_values.csv")
    print("- memory_comparison.csv")
    print("- operation_times_comparison.csv")
    print("- conclusions.txt")


if __name__ == "__main__":
    main()
