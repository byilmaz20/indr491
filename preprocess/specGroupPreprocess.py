#800ün altındakiler gruplanabilir mi?
import os
import pandas as pd
print(os.getcwd())
#geçmiş siparişlerde o genişliğe/spece en çok hangi hammadde genişliği atandı diye bakabiliriz

# Load the data from Sheet1
"""
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
file_path = os.path.join(project_root, "mmkBelgeler", "KU002 Mamul SPEC Bilgileri - Örnek.xlsx")"""
df = pd.read_excel("../mmkBelgeler/KU002 Mamul SPEC Bilgileri - Örnek.xlsx", sheet_name="Sheet1")

# Group by the specified columns and assign a unique SpecGroupId
df['SpecGroupId'] = df.groupby(['ÜrünTipi', 'Kalınlık', 'Genişlik', 'Grade']).ngroup() + 1

# Select only the required columns for output
output_df = df[['SpecGroupId', 'SPEC']].sort_values(by='SpecGroupId')

# Save to a new Excel file
output_file_path = "../mmkBelgeler/specGroups.xlsx"
output_df.to_excel(output_file_path, index=False)

