# LAB7 - Optymalizacja zapytań analitycznych w Pandas

## Cel

Laboratorium dotyczy analizy wpływu sposobu przetwarzania danych na wydajność operacji analitycznych.

Wykonywane są:

- wczytanie i analiza danych,
- optymalizacja pamięci,
- pomiar czasu operacji analitycznych,
- porównanie wyników przed i po optymalizacji,
- zapis wniosków.

## Dane

Wymagany plik wejściowy:

```text
data/Online_Retail.csv
```

Plik można skopiować z wcześniejszego laboratorium:

```powershell
copy .\LAB2\data\Online_Retail.csv .\LAB7\data\Online_Retail.csv
```

## Uruchomienie

Na Windows:

```powershell
python LAB7\lab7_optimization.py
```

Na PythonAnywhere:

```bash
cd ~/MHD_Lab
source ~/.virtualenvs/MHD_Lab/bin/activate
python LAB7/lab7_optimization.py
```

## Wyniki

Wyniki zapisują się do:

```text
output/optimization/
```

Najważniejsze pliki:

- `extract_analysis.txt` - podstawowa analiza danych i czas wczytywania,
- `missing_values.csv` - liczba brakujących wartości,
- `dtypes_before_optimization.csv` - typy danych przed optymalizacją,
- `dtypes_after_optimization.csv` - typy danych po optymalizacji,
- `memory_comparison.csv` - porównanie zużycia pamięci,
- `operation_times_comparison.csv` - porównanie czasów operacji,
- `conclusions.txt` - wnioski końcowe.

## Operacje mierzone czasowo

- suma sprzedaży według kraju,
- suma sprzedaży według miesiąca,
- TOP 10 klientów według wartości zakupów,
- filtrowanie produktów sprzedanych w Wielkiej Brytanii,
- filtrowanie rekordów o wartości sprzedaży większej niż 1000.
