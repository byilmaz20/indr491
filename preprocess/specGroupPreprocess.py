#800ün altındakiler gruplanabilir
import os
import pandas as pd
#geçmiş siparişlerde o genişliğe/spece en çok hangi hammadde genişliği atandı diye bakabiliriz

# Load the data from Sheet1
specDF = pd.read_csv("mmkBelgeler/KU002 Mamul SPEC Bilgileri - Tam.csv", encoding="ISO-8859-1", delimiter=";")
last3YearsSiparisDF = pd.read_excel("preprocessedBelgeler/preprocessedDemandBySpecTam.xlsx")


specDF["Genislik"] = specDF["Genislik"].astype(str).str.replace(",", ".").astype(float)

specDF["Genislik_Grouped"] = specDF["Genislik"].apply(lambda x: "0-800" if x < 800 else str(x))

# Group by the specified columns and assign a unique SpecGroupId
specDF['SpecGroupId'] = specDF.groupby(['Kalinlik', 'Genislik_Grouped', 'Grade']).ngroup() + 1


mergedDF = specDF.merge(last3YearsSiparisDF, left_on="SPEC", right_on="SPEC", how="left")
mergedDF["Son 3 yıl Sipariş Mik. (TON) Toplam"] = mergedDF["Son 3 yıl Sipariş Mik. (TON) Toplam"].fillna(0)
#if sum of last 3 years orders is 0, delete the SpecGroupId
sum_df = mergedDF.groupby(["SpecGroupId"])["Son 3 yıl Sipariş Mik. (TON) Toplam"].sum().reset_index()

output_file_path = "preprocessedBelgeler/specGroups_last3.xlsx"
sum_df.to_excel(output_file_path, index=False)

print(len(sum_df))
sum_df = sum_df[sum_df["Son 3 yıl Sipariş Mik. (TON) Toplam"] > 0]
print(len(sum_df))
specDF = mergedDF[mergedDF["SpecGroupId"].isin(sum_df["SpecGroupId"])]
specDF['SpecGroupId'] = specDF.groupby(['Kalinlik', 'Genislik_Grouped', 'Grade']).ngroup() + 1


# Select only the required columns for output
output_df = specDF[['SpecGroupId', 'SPEC', 'Kalinlik', 'Genislik', 'Genislik_Grouped', 'Grade']].sort_values(by='SpecGroupId')
# Save to a new Excel file
output_file_path = "preprocessedBelgeler/specGroupsTam_0-800_x_last3.xlsx"
output_df.to_excel(output_file_path, index=False)



