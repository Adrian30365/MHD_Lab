# LAB5 - Mechanizmy OLAP i analiza danych

Celem laboratorium jest wykonanie podstawowych operacji OLAP w bibliotece pandas oraz przygotowanie kostek danych na podstawie zbiorów Online Retail.

## Dane wejściowe

Pliki danych należy umieścić w katalogu:

```text
LAB5/data/
```

Wymagany plik:

```text
Online_Retail.csv
```

Opcjonalny/drugi zbiór danych zgodnie z instrukcją:

```text
Online_Retail_II.csv
```

albo:

```text
Online_Retail_II.xlsx
```

Skrypt obsługuje również sytuację, w której dane znajdują się w `LAB2/data` albo `LAB4/data`.

## Uruchomienie

Z głównego katalogu repozytorium:

```powershell
cd C:\Users\Ja\Desktop\MHD_Lab
.\venv\Scripts\Activate.ps1
python LAB5\lab5_olap_analysis.py
```

## Wykonane elementy

Skrypt realizuje:

- wczytanie danych,
- połączenie zbiorów,
- czyszczenie danych,
- dodanie miary `TotalPrice`,
- ekstrakcję wymiarów czasu: `Year`, `Month`, `Day`,
- roll-up,
- drill-down,
- slice,
- dice,
- pivot table jako kostkę danych,
- Top 10 krajów pod względem sprzedaży,
- miesiąc o największej sprzedaży,
- kostkę kraj x miesiąc,
- najlepszy rok sprzedaży dla każdego kraju,
- Top 5 produktów w każdym kraju,
- heatmapę sprzedaży.

## Wyniki

Wyniki zapisują się do:

```text
LAB5/output/olap/
```

Najważniejsze pliki:

```text
task1_top_10_countries.csv
task2_best_sales_month.csv
task3_cube_country_month.csv
task4_best_year_by_country.csv
task5_top_5_products_by_country.csv
bonus_heatmap_country_month.png
olap_notes.txt
```

## Założenia czyszczenia danych

W procesie transformacji usunięto:

- rekordy z brakującym `CustomerID`,
- anulowane faktury,
- rekordy z `Quantity <= 0`,
- rekordy z `UnitPrice <= 0`,
- rekordy z błędną datą,
- duplikaty.

Miara sprzedaży została obliczona jako:

```text
TotalPrice = Quantity * UnitPrice
```
