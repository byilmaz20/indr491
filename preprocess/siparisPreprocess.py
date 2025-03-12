# Load the data from Sheet1 of the orders file
import pandas as pd

orders_df = pd.read_excel("../mmkBelgeler/KU003 Siparişler.xlsx", sheet_name="Sheet1", header=1)
spec_groups_df = pd.read_excel("../mmkBelgeler/specGroups.xlsx")

# Convert "Teslimat tarihi" to datetime format
orders_df["Teslimat tarihi"] = pd.to_datetime(orders_df["Teslimat tarihi"], errors='coerce')

# Extract Month-Year format (MM.YYYY) for grouping
orders_df["Month"] = orders_df["Teslimat tarihi"].dt.strftime("%m.%Y")

# Merge to find the corresponding SpecGroup for each order based on "Müşteri malzeme numarası" (SPEC)
merged_df = orders_df.merge(spec_groups_df, left_on="Müşteri malzeme numarası", right_on="SPEC", how="left")
# Assign unmatched SPECs to SpecGroupId 0
merged_df["SpecGroupId"] = merged_df["SpecGroupId"].fillna(0)

# Group by Month and SpecGroup, summing up the order quantity
result_df = merged_df.groupby(["Month", "SpecGroupId"])["Sipariş Mik. (TON)"].sum().reset_index()

# Save to a new Excel file without renaming columns
output_orders_file = "../mmkBelgeler/preprocessedDemand.xlsx"
result_df.to_excel(output_orders_file, index=False)
