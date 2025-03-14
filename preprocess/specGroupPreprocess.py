#800ün altındakiler gruplanabilir mi?
import os
import pandas as pd
#rint(os.getcwd())
#geçmiş siparişlerde o genişliğe/spece en çok hangi hammadde genişliği atandı diye bakabiliriz

# Load the data from Sheet1
"""
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
file_path = os.path.join(project_root, "mmkBelgeler", "KU002 Mamul SPEC Bilgileri - Örnek.xlsx")"""
#df = pd.read_excel("../mmkBelgeler/KU002 Mamul SPEC Bilgileri - Örnek.xlsx", sheet_name="Sheet1")
df = pd.read_csv("mmkBelgeler/KU002 Mamul SPEC Bilgileri - Tam.csv", encoding="ISO-8859-1", delimiter=";")
print(df.head())

df["Genislik"] = df["Genislik"].astype(str).str.replace(",", ".").astype(float)

df["Genislik_Grouped"] = df["Genislik"].apply(lambda x: "0-800" if x < 800 else "800+")

# Group by the specified columns and assign a unique SpecGroupId
df['SpecGroupId'] = df.groupby(['UrunTipi', 'Kalinlik', 'Genislik_Grouped', 'Grade']).ngroup() + 1

# Select only the required columns for output
output_df = df[['SpecGroupId', 'SPEC', 'UrunTipi', 'Kalinlik', 'Genislik', 'Genislik_Grouped', 'Grade']].sort_values(by='SpecGroupId')
# Save to a new Excel file
output_file_path = "mmkBelgeler/specGroupsTam800.xlsx"
output_df.to_excel(output_file_path, index=False)

