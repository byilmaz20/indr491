import pandas as pd
import matplotlib.pyplot as plt

# Dosyanın yolu
file_path = "/Users/ceylin/Desktop/indr491/indr491/preprocessedBelgeler/preprocessedDemandTam_last3_altLimit100.xlsx"
df = pd.read_excel(file_path)

# Yıl ve ayı ayrıştır
df["Year"] = df["Month"].astype(str).str.split(".").str[1].astype(str)
df["Month"] = df["Month"].astype(str).str.split(".").str[0].astype(str)

# Yıl ve ayları birleştirirken metin formatına çevir
df["YearMonth"] = df["Year"] + "-" + df["Month"]

# Aylık bazda SpecGroupId'ye göre toplam sipariş miktarı
filtered_demand_distribution = df.groupby(["YearMonth", "SpecGroupId"])["Sipariş Mik. (TON)"].sum().unstack()

# Yüzdesel dağılım hesapla
filtered_percentage_distribution = filtered_demand_distribution.div(filtered_demand_distribution.sum(axis=1), axis=0) * 100

# Her SpecGroupId için grafik çiz
for spec_group in filtered_percentage_distribution.columns:
    plt.figure(figsize=(12, 6))
    plt.plot(filtered_percentage_distribution.index, filtered_percentage_distribution[spec_group], marker='o', linestyle='-')
    plt.xlabel("Yıl-Ay")
    plt.ylabel("Yüzdesel Talep Dağılımı")
    plt.title(f"SpecGroupId {spec_group} için Yıl-Ay Bazında Yüzdesel Talep Dağılımı")
    plt.xticks(rotation=90)
    plt.grid(True)
    plt.show()
