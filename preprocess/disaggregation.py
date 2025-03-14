import pandas as pd
import matplotlib.pyplot as plt

# CSV dosyasını yükleme
file_path = "/Users/ceylin/Desktop/indr491/indr491/mmkBelgeler/KU003 Siparişler.xlsx"
df = pd.read_excel(file_path, header=1)  # 2. satırı sütun isimleri olarak al
print(df.columns.tolist())  # Sütun isimlerini liste olarak yazdır
print(df.head()) 

# Genislik sütununu sayısal formata dönüştürme
df["PlnHmdde Gnşlk"] = df["PlnHmdde Gnşlk"].astype(str).str.replace(",", ".").astype(float)

# Teslimat tarihi sütununu datetime formatına çevirme
df["Teslimat tarihi"] = pd.to_datetime(df["Teslimat tarihi"], dayfirst=True, errors='coerce')

# Ay bilgisini içeren yeni bir sütun oluşturma
df["Ay"] = df["Teslimat tarihi"].dt.to_period("M")

# Genislik gruplarının belirlenmesi (örneğin 100 birim aralıklarla gruplama)
bins = list(range(int(df["PlnHmdde Gnşlk"].min()), int(df["PlnHmdde Gnşlk"].max()) + 100, 100))
df["Genislik Grubu"] = pd.cut(df["PlnHmdde Gnşlk"], bins)

# Her ay için yüzdelik dağılımı hesaplama
genislik_distribution = df.groupby(["Ay", "Genislik Grubu"]).size().unstack().apply(lambda x: x / x.sum(), axis=1)

# Grafik oluşturma
plt.figure(figsize=(12, 6))
genislik_distribution.plot(kind="bar", stacked=True, colormap="viridis", figsize=(12, 6))
plt.xlabel("Ay")
plt.ylabel("Yüzdelik Dağılım")
plt.title("Genislik Gruplarının Aylık Yüzdelik Dağılımı")
plt.legend(title="Genislik Grubu", bbox_to_anchor=(1.05, 1), loc='upper left')
plt.xticks(rotation=45)
plt.tight_layout()

# Grafiği gösterme
plt.show()
