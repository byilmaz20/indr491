# Load the data from Sheet1 of the orders file
import datetime
import os
import pandas as pd
print(os.getcwd())

sonXyil = 3

finalOrdersDF = pd.DataFrame()

for file in os.listdir("mmkBelgeler/siparisler"):
    orders_df = pd.read_excel(os.path.join("mmkBelgeler/siparisler",file), header=0)
    #print(orders_df.head())
    #print(file)

    # Convert "Teslimat tarihi" to datetime format
    orders_df["Teslimat tarihi"] = pd.to_datetime(orders_df["Teslimat tarihi"], errors='coerce')

    # Extract Month-Year format (MM.YYYY) for grouping
    finalOrdersDF = pd.concat([finalOrdersDF, orders_df])


#TODO son 3 yıldır siparisi yoksa sil
finalOrdersDF = finalOrdersDF[finalOrdersDF["Teslimat tarihi"].dt.year >= 2025 - sonXyil]

# Group by Spec, summing up the order quantity
result_df = finalOrdersDF.groupby(["Müşteri malzeme numarası"])["Sipariş Mik. (TON)"].sum().reset_index()

#rename columns
result_df.rename(columns={"Müşteri malzeme numarası": "SPEC", "Sipariş Mik. (TON)": "Son 3 yıl Sipariş Mik. (TON) Toplam"}, inplace=True)

# Save to a new Excel file without renaming columns
output_orders_file = "preprocessedBelgeler/preprocessedDemandBySpecTam.xlsx"
result_df.to_excel(output_orders_file, index=False)



print("done")