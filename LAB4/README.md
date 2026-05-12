# LAB4 - ETL w hurtowniach danych

## Cel

Laboratorium pokazuje proces ETL:

- Extract - wczytanie danych,
- Transform - czyszczenie, ujednolicenie i przygotowanie miar,
- Load - zapis danych do tabeli faktów.

Pracujemy na zbiorze `Online_Retail.csv`.

## Struktura

```text
LAB4
├── data
│   ├── Online_Retail.csv
│   └── Online_Retail_II.xlsx          # potrzebne tylko do zadania dodatkowego
├── output
├── lab4_etl_basic.py
├── lab4_etl_integration.py
├── README.md
└── requirements.txt
```

## Zadanie podstawowe

Plik:

```text
lab4_etl_basic.py
```

Uruchomienie:

```powershell
python LAB4\lab4_etl_basic.py
```

Wyniki:

```text
LAB4/output/basic_etl/
```

Najważniejszy plik wynikowy:

```text
fact_sales.csv
```

## Zadanie dodatkowe

Plik:

```text
lab4_etl_integration.py
```

Wymaga drugiego pliku:

```text
LAB4/data/Online_Retail_II.xlsx
```

Uruchomienie:

```powershell
python LAB4\lab4_etl_integration.py
```

Wyniki:

```text
LAB4/output/integrated_etl/
```

Najważniejszy plik wynikowy:

```text
fact_sales_integrated.csv
```

## Założenia projektowe

W zadaniu podstawowym usuwane są:

- rekordy bez `CustomerID`,
- anulowane faktury zaczynające się od `C`,
- rekordy z `Quantity <= 0`,
- rekordy z `UnitPrice < 0`,
- brakujące daty,
- duplikaty.

Dodane są:

- `Year`,
- `Month`,
- `Day`,
- `Revenue = Quantity * UnitPrice`.

W zadaniu dodatkowym użyto `concat`, ponieważ dane z dwóch źródeł mają reprezentować kolejne rekordy transakcyjne w jednej tabeli faktów.
