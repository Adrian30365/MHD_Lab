# LAB3 - Modelowanie danych w hurtowni

## Cel

Celem laboratorium jest zaprojektowanie hurtowni danych w schemacie gwiazdy dla danych `Online_Retail.csv`.

## Pliki

- `online_retail_dw_lab3_completed.ipynb` - notebook z opisem, kodem i miejscem na wyniki.
- `lab3_dw_model.py` - wersja skryptowa tego samego rozwiązania, wygodna do uruchomienia w terminalu.
- `data/Online_Retail.csv` - plik wejściowy z danymi.
- `output/` - katalog z wynikami generowanymi przez notebook lub skrypt.

## Model

Ziarno tabeli faktów: pojedyncza pozycja faktury.

Tabela faktów:

- `FactSales`

Wymiary:

- `DimCustomer_SCD2`
- `DimProduct`
- `DimDate`
- `DimCountry`
- `DimInvoice`

## SCD

Dla wymiaru klienta zastosowano SCD typu 2. Śledzoną zmianą jest zmiana kraju klienta.

## Wyniki

Po uruchomieniu powstaną między innymi:

- `FactSales.csv`
- `DimCustomer_SCD2.csv`
- `DimProduct.csv`
- `DimDate.csv`
- `DimCountry.csv`
- `DimInvoice.csv`
- `sales_by_country.csv`
- `sales_trend_monthly.csv`
- `sales_by_product.csv`
- `sales_trend_monthly.png`
- `design_notes.txt`
