import pandas as pd
import matplotlib.pyplot as plt

# CSV dosyasını yükleme
file_path = "/Users/ceylin/Desktop/indr491/indr491/mmkBelgeler/KU003 Siparişler 012018.csv"

# Try different encodings if needed: 'latin1', 'ISO-8859-1', 'utf-8'
df = pd.read_csv(file_path, encoding="ISO-8859-1", delimiter=";")
df.columns = [
    "Satış belgesi", "Kalem", "Üretim yeri", "Müşteri malzeme numarası",
    "Satış belgesi türü", "Malzeme", "Malzeme Tanımı", "Plan Hammaddesi",
    "PlnHmdde Gnşlk", "Sipariş Mik. (TON)", "Sevk Edilen Mik. (TON)",
    "Açık Mik. (TON)", "Tedariksiz Mamul", "Yaratma tarihi", "Teslimat tarihi",
    "Planlanan Termin Tarihi", "Öncelik Tanımı", "31 HR", "31 PHR", "31 CRF",
    "31 GCR", "31 GHR", "31 PPG", "41 HR", "41 PHR", "41 CRF", "41 GCR",
    "41 GHR", "41 PPG", "Ticari kalite", "Sektör Tanımı", "Baz Fiyat",
    "Nihai Fiyat", "Siparişi Veren", "Müşteri grubu 2", "Max Tonaj", "Min Tonaj"
]
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
