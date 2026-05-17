from pathlib import Path
import pandas as pd

# Carpeta donde están los archivos originales de Fasecolda
input_folder = Path("data/raw/fasecolda/2015-2024")

# Carpeta donde guardaremos el archivo procesado
output_folder = Path("data/processed")
output_folder.mkdir(parents=True, exist_ok=True)

# Buscar todos los archivos Excel
excel_files = list(input_folder.glob("*.xls*"))

print("Cantidad de archivos encontrados:", len(excel_files))

all_data = []

for file in excel_files:
    print("Leyendo:", file.name)

    df = pd.read_excel(file)

    # Agregar columna con el nombre del archivo fuente
    df["ARCHIVO_FUENTE"] = file.name

    all_data.append(df)

# Unir todos los archivos en una sola tabla
combined_df = pd.concat(all_data, ignore_index=True)

print("\nTamaño final de la tabla combinada:")
print(combined_df.shape)

print("\nPrimeras filas:")
print(combined_df.head())

print("\nColumnas:")
print(combined_df.columns.tolist())

# Guardar como CSV
output_file = output_folder / "fasecolda_2015_2024_combined.csv"
combined_df.to_csv(output_file, index=False, encoding="utf-8-sig")

print("\nArchivo guardado en:")
print(output_file)