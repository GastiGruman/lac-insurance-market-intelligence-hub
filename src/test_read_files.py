from pathlib import Path
import pandas as pd

# Carpeta donde están los archivos descargados de Fasecolda
folder = Path("data/raw/fasecolda/2015-2024")

# Buscar archivos de Excel dentro de esa carpeta
excel_files = list(folder.glob("*.xls*"))

print("Cantidad de archivos encontrados:", len(excel_files))

print("\nPrimeros 10 archivos encontrados:")
for file in excel_files[:10]:
    print("-", file.name)

# Leer el primer archivo para revisar su estructura
if excel_files:
    first_file = excel_files[0]
    print("\nLeyendo archivo:", first_file.name)

    df = pd.read_excel(first_file)

    print("\nTamaño del archivo leído:")
    print(df.shape)

    print("\nPrimeras filas:")
    print(df.head())

    print("\nColumnas:")
    print(df.columns.tolist())
else:
    print("No se encontraron archivos de Excel en la carpeta.")