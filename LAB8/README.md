# LAB8 - Analiza wpływu różnych metod agregacji na wydajność

Laboratorium porównuje trzy metody agregacji danych w Pandas:

- `groupby()`
- `pivot_table()`
- agregacja po wcześniejszym `set_index()`

## Dane

Zadanie przewiduje plik:

```text
Online_Retail_II.csv
```

Skrypt obsługuje również plik Excel:

```text
Online_Retail_II.xlsx
```

Plik danych należy umieścić w:

```text
LAB8/data/
```

Skrypt potrafi też skorzystać z danych z wcześniejszych laboratoriów, jeżeli znajdują się w `LAB4` lub `LAB5`.

## Uruchomienie

```bash
python LAB8/lab8_aggregation_performance.py
```

## Powiększony zbiór danych

Domyślnie dane są powiększane 5 razy. Na PythonAnywhere można zmienić mnożnik, np.:

```bash
LAB8_MULTIPLIER=10 python LAB8/lab8_aggregation_performance.py
```

## Wyniki

Wyniki zapisują się w:

```text
LAB8/output/aggregation_performance/
```

Najważniejsze pliki:

- `extract_report.txt`
- `missing_values.csv`
- `data_preparation_report.csv`
- `aggregation_times.csv`
- `fastest_methods.csv`
- `average_time_by_method.csv`
- `final_report.txt`

## Zakres realizacji

Skrypt wykonuje wczytanie danych, przygotowanie `TotalPrice`, trzy rodzaje agregacji, test na powiększonym zbiorze danych i raport końcowy.
