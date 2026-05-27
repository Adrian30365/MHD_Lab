import os
import time
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output" / "aggregation_performance"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LARGE_MULTIPLIER = int(os.getenv("LAB8_MULTIPLIER", "5"))


def find_data_file() -> Path:
    possible_files = [
        DATA_DIR / "Online_Retail_II.csv",
        DATA_DIR / "online_retail_II.csv",
        DATA_DIR / "Online_Retail_II.xlsx",
        DATA_DIR / "online_retail_II.xlsx",
        BASE_DIR.parent / "LAB5" / "data" / "Online_Retail_II.csv",
        BASE_DIR.parent / "LAB5" / "data" / "Online_Retail_II.xlsx",
        BASE_DIR.parent / "LAB4" / "data" / "Online_Retail_II.xlsx",
        BASE_DIR.parent / "LAB2" / "data" / "Online_Retail.csv",
    ]
    for file_path in possible_files:
        if file_path.exists():
            return file_path
    raise FileNotFoundError(
        "Nie znaleziono danych. Wrzuc plik do LAB8/data jako Online_Retail_II.csv albo Online_Retail_II.xlsx."
    )


def read_source_file(file_path: Path):
    start = time.perf_counter()
    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path, encoding="ISO-8859-1")
    elif file_path.suffix.lower() in [".xlsx", ".xls"]:
        sheets = pd.read_excel(file_path, sheet_name=None)
        df = pd.concat(sheets.values(), ignore_index=True)
    else:
        raise ValueError(f"Nieobslugiwany format pliku: {file_path.suffix}")
    load_time = time.perf_counter() - start
    return df, load_time


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "Invoice": "InvoiceNo",
        "Customer ID": "CustomerID",
        "Price": "UnitPrice",
    }
    df = df.rename(columns=rename_map)
    required_columns = [
        "InvoiceNo", "StockCode", "Description", "Quantity",
        "InvoiceDate", "UnitPrice", "CustomerID", "Country",
    ]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Brak wymaganych kolumn: {missing}")
    return df


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_columns(df)
    start_rows = len(df)
    df = df.dropna(subset=["CustomerID"]).copy()
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df = df.dropna(subset=["Quantity", "UnitPrice", "InvoiceDate"])
    df = df[df["Quantity"] > 0]
    df = df[df["UnitPrice"] > 0]
    df["TotalPrice"] = df["Quantity"] * df["UnitPrice"]
    df["Month"] = df["InvoiceDate"].dt.to_period("M").astype(str)
    df["CustomerID"] = df["CustomerID"].astype(int).astype(str)
    df["InvoiceNo"] = df["InvoiceNo"].astype(str)
    df["Country"] = df["Country"].astype(str)
    df["StockCode"] = df["StockCode"].astype(str)
    report = {
        "rows_before_cleaning": start_rows,
        "rows_after_cleaning": len(df),
        "removed_rows": start_rows - len(df),
    }
    pd.DataFrame([report]).to_csv(OUTPUT_DIR / "data_preparation_report.csv", index=False)
    return df


def save_initial_profile(raw_df: pd.DataFrame, load_time: float, file_path: Path):
    missing = raw_df.isna().sum().reset_index()
    missing.columns = ["column", "missing_values"]
    missing.to_csv(OUTPUT_DIR / "missing_values.csv", index=False)
    dtypes = raw_df.dtypes.astype(str).reset_index()
    dtypes.columns = ["column", "dtype"]
    dtypes.to_csv(OUTPUT_DIR / "dtypes.csv", index=False)
    memory_mb = raw_df.memory_usage(deep=True).sum() / 1024 / 1024
    with open(OUTPUT_DIR / "extract_report.txt", "w", encoding="utf-8") as file:
        file.write("LAB8 - Etap 1: wczytanie i analiza danych\n\n")
        file.write(f"Plik zrodlowy: {file_path}\n")
        file.write(f"Czas wczytywania: {load_time:.6f} s\n")
        file.write(f"Liczba rekordow: {len(raw_df)}\n")
        file.write(f"Liczba kolumn: {raw_df.shape[1]}\n")
        file.write(f"Zuzycie pamieci: {memory_mb:.2f} MB\n\n")
        file.write("Typy danych:\n")
        file.write(raw_df.dtypes.astype(str).to_string())
        file.write("\n\nBrakujace wartosci:\n")
        file.write(raw_df.isna().sum().to_string())


def measure(operation_name: str, method_name: str, dataset_name: str, func):
    start = time.perf_counter()
    result = func()
    elapsed = time.perf_counter() - start
    if isinstance(result, pd.Series):
        rows = len(result)
        result_to_save = result.reset_index()
    else:
        rows = len(result)
        result_to_save = result.copy()
    return {
        "dataset": dataset_name,
        "operation": operation_name,
        "method": method_name,
        "time_seconds": elapsed,
        "result_rows": rows,
        "result": result_to_save,
    }


def run_aggregations(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    df_country_index = df.set_index("Country")
    df_month_index = df.set_index("Month")
    df_customer_index = df.set_index("CustomerID")
    tests = [
        ("sales_by_country", "groupby", lambda: df.groupby("Country")["TotalPrice"].sum().sort_values(ascending=False)),
        ("sales_by_country", "pivot_table", lambda: pd.pivot_table(df, values="TotalPrice", index="Country", aggfunc="sum").sort_values("TotalPrice", ascending=False)),
        ("sales_by_country", "set_index_groupby", lambda: df_country_index.groupby(level=0)["TotalPrice"].sum().sort_values(ascending=False)),
        ("sales_by_month", "groupby", lambda: df.groupby("Month")["TotalPrice"].sum().sort_index()),
        ("sales_by_month", "pivot_table", lambda: pd.pivot_table(df, values="TotalPrice", index="Month", aggfunc="sum").sort_index()),
        ("sales_by_month", "set_index_groupby", lambda: df_month_index.groupby(level=0)["TotalPrice"].sum().sort_index()),
        ("transactions_by_customer", "groupby", lambda: df.groupby("CustomerID")["InvoiceNo"].nunique().sort_values(ascending=False)),
        ("transactions_by_customer", "pivot_table", lambda: pd.pivot_table(df, values="InvoiceNo", index="CustomerID", aggfunc=pd.Series.nunique).sort_values("InvoiceNo", ascending=False)),
        ("transactions_by_customer", "set_index_groupby", lambda: df_customer_index.groupby(level=0)["InvoiceNo"].nunique().sort_values(ascending=False)),
    ]
    timing_rows = []
    for operation_name, method_name, func in tests:
        measured = measure(operation_name, method_name, dataset_name, func)
        file_name = f"{dataset_name}_{operation_name}_{method_name}.csv"
        measured["result"].to_csv(OUTPUT_DIR / file_name, index=False)
        timing_rows.append({
            "dataset": measured["dataset"],
            "operation": measured["operation"],
            "method": measured["method"],
            "time_seconds": measured["time_seconds"],
            "result_rows": measured["result_rows"],
            "output_file": file_name,
        })
    return pd.DataFrame(timing_rows)


def create_large_dataset(df: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([df] * LARGE_MULTIPLIER, ignore_index=True)


def build_report(timings: pd.DataFrame, normal_rows: int, large_rows: int):
    fastest = timings.sort_values("time_seconds").groupby(["dataset", "operation"]).first().reset_index()
    fastest.to_csv(OUTPUT_DIR / "fastest_methods.csv", index=False)
    avg_by_method = timings.groupby(["dataset", "method"])["time_seconds"].mean().reset_index().sort_values(["dataset", "time_seconds"])
    avg_by_method.to_csv(OUTPUT_DIR / "average_time_by_method.csv", index=False)
    normal_fastest_method = avg_by_method[avg_by_method["dataset"] == "normal"].head(1)["method"].iloc[0]
    large_fastest_method = avg_by_method[avg_by_method["dataset"] == "large"].head(1)["method"].iloc[0]
    with open(OUTPUT_DIR / "final_report.txt", "w", encoding="utf-8") as file:
        file.write("LAB8 - raport koncowy\n\n")
        file.write("Cel: porownanie metod agregacji danych hurtownianych w Pandas.\n\n")
        file.write(f"Liczba rekordow po czyszczeniu: {normal_rows}\n")
        file.write(f"Liczba rekordow w zbiorze powiekszonym: {large_rows}\n")
        file.write(f"Mnoznik powiekszenia danych: {LARGE_MULTIPLIER}\n\n")
        file.write("Najbardziej wydajna metoda srednio dla zbioru podstawowego:\n")
        file.write(f"{normal_fastest_method}\n\n")
        file.write("Najbardziej wydajna metoda srednio dla zbioru powiekszonego:\n")
        file.write(f"{large_fastest_method}\n\n")
        file.write("Wnioski:\n")
        file.write("1. groupby() jest najczesciej najprostsza i bardzo wydajna metoda agregacji danych w Pandas.\n")
        file.write("2. pivot_table() jest czytelna przy budowie tabel analitycznych, ale moze miec wiekszy narzut.\n")
        file.write("3. set_index() bywa przydatny, gdy wielokrotnie analizujemy dane wedlug tej samej kolumny.\n")
        file.write("4. Przy bardzo duzych hurtowniach danych problemem staje sie zuzycie pamieci i czas operacji.\n")


def main():
    file_path = find_data_file()
    raw_df, load_time = read_source_file(file_path)
    save_initial_profile(raw_df, load_time, file_path)
    df = prepare_data(raw_df)
    normal_rows = len(df)
    normal_timings = run_aggregations(df, "normal")
    large_df = create_large_dataset(df)
    large_rows = len(large_df)
    large_timings = run_aggregations(large_df, "large")
    timings = pd.concat([normal_timings, large_timings], ignore_index=True)
    timings.to_csv(OUTPUT_DIR / "aggregation_times.csv", index=False)
    build_report(timings, normal_rows, large_rows)
    print("LAB8 zakonczone.")
    print(f"Plik danych: {file_path}")
    print(f"Rekordy po czyszczeniu: {normal_rows}")
    print(f"Rekordy w zbiorze powiekszonym: {large_rows}")
    print(f"Wyniki zapisano w: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
