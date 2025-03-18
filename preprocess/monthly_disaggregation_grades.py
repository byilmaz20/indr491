import pandas as pd
import matplotlib.pyplot as plt

# Dosyayı oku
file_path = "/Users/ceylin/Desktop/indr491/indr491/preprocessedBelgeler/forecastData_altLimit100_son3_byGrade.xlsx"
df = pd.read_excel(file_path)

# Yıl ve ay verisini ayırarak düzenle
df["Year"] = df["Month"].astype(str).str.split(".").str[1]  # Yıl bilgisini al
df["Month"] = df["Month"].astype(str).str.split(".").str[0].str.zfill(2)  # Ay bilgisini al ve iki haneli yap

# Eğer Year sütunu 3 haneli ise, başına "0" ekleyerek düzelt (Örneğin: "202" → "2020")
df.loc[df["Year"].str.len() == 3, "Year"] = df["Year"] + "0"

# Yeni "YearMonth" sütununu oluştur
df["YearMonth"] = df["Year"] + "-" + df["Month"]

# Datetime çevirimi (artık hata almayacağız)
df["YearMonth"] = pd.to_datetime(df["YearMonth"], format="%Y-%m")

# Toplam sipariş miktarını hesapla
df['Total_Grade_Month'] = df.groupby(['YearMonth'])['Sipariş Mik. (TON)'].transform('sum')

# Yüzde hesaplama
df['Percentage'] = (df['Sipariş Mik. (TON)'] / df['Total_Grade_Month']) * 100

# Her Grade ve SpecGroupId için grafikleri çiz
unique_grades = df['Grade'].unique()

for grade in unique_grades:
    grade_data = df[df['Grade'] == grade]


    plt.figure(figsize=(12, 6))
    spec_group_data = grade_data.sort_values(by="YearMonth")  # Tarihe göre sıralama
    plot.title(f'Percentage Distribution within {grade}')
    
    plt.plot(spec_group_data['YearMonth'], spec_group_data['Percentage'], marker='o', linestyle='-')
    plt.xlabel('Year-Month')
    plt.ylabel('Percentage Share within Grade')
    plt.xticks(rotation=90)
    plt.grid(True)
    plt.show()
