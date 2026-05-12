# LAB6 - Analiza danych

Laboratorium 6 dotyczy analizy danych sprzedażowych przy użyciu Pandas.

## Zakres

Zrealizowane zadania:

1. Tabela pivot:
   - wiersze: `Country`
   - kolumny: `Month`
   - wartości: suma `Revenue`

2. Ranking krajów:
   - całkowity przychód dla każdego kraju
   - sortowanie malejące
   - TOP 10 krajów

3. Analiza klientów:
   - przychód dla każdego klienta
   - TOP 10 klientów
   - średni przychód na klienta

4. Segmentacja krajów:
   - Top 25% - wysoki przychód
   - Środkowe 50% - średni przychód
   - Dolne 25% - niski przychód

5. Wnioski:
   - kluczowe kraje
   - równomierność sprzedaży między krajami
   - sezonowość

## Dane wejściowe

W folderze `data` powinien znajdować się plik:

```text
Online_Retail.csv
```

Opcjonalnie można dodać także:

```text
Online_Retail_II.csv
```

albo:

```text
Online_Retail_II.xlsx
```

Skrypt obsługuje oba warianty.

## Uruchomienie

Z głównego folderu repozytorium:

```powershell
python LAB6\lab6_analysis.py
```

albo z folderu LAB6:

```powershell
python lab6_analysis.py
```

## Wyniki

Wyniki zapisują się do folderu:

```text
LAB6/output/
```

Najważniejsze pliki:

```text
task1_pivot_country_month.csv
task1_month_sales_ranking.csv
task1_best_month.csv
task2_country_revenue_ranking.csv
task2_top10_countries.csv
task3_customer_revenue.csv
task3_top10_customers.csv
task3_customer_summary.csv
task4_country_segments.csv
task4_segment_summary.csv
task5_conclusions.txt
chart_top10_countries.png
chart_monthly_revenue.png
chart_segment_revenue.png
```
