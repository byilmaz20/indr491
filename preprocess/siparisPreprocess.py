# Load the data from Sheet1 of the orders file
import os
import pandas as pd
print(os.getcwd())

spec_groups_df = pd.read_excel("preprocessedBelgeler/specGroupsTam_0-800_x_last3.xlsx")
finalOrdersDF = pd.DataFrame()


for file in os.listdir("mmkBelgeler/siparisler"):
    orders_df = pd.read_excel(os.path.join("mmkBelgeler/siparisler",file), header=0)

    # Convert "Teslimat tarihi" to datetime format
    orders_df["Teslimat tarihi"] = pd.to_datetime(orders_df["Teslimat tarihi"], errors='coerce')

    # Extract Month-Year format (MM.YYYY) for grouping
    orders_df["Month"] = orders_df["Teslimat tarihi"].dt.strftime("%m.%Y")
    finalOrdersDF = pd.concat([finalOrdersDF, orders_df])

# Merge to find the corresponding SpecGroup for each order based on "Müşteri malzeme numarası" (SPEC)
merged_df = finalOrdersDF.merge(spec_groups_df, left_on="Müşteri malzeme numarası", right_on="SPEC", how="left")
# Assign unmatched SPECs to SpecGroupId 0
merged_df["SpecGroupId"] = merged_df["SpecGroupId"].fillna(0)

# Group by Month and SpecGroup, summing up the order quantity
result_df = merged_df.groupby(["Month", "SpecGroupId"])["Sipariş Mik. (TON)"].sum().reset_index()


# Save to a new Excel file without renaming columns
output_orders_file = "preprocessedBelgeler/preprocessedDemandTam_0-800_x_last3.xlsx"
result_df.to_excel(output_orders_file, index=False)
