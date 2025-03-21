import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX

# ----- 1. Veri Hazırlama -----
# Ana veri kümesini yükle
df_path = "/Users/ceylin/Desktop/indr491/indr491/preprocessedBelgeler/forecastData_altLimit100_son3_byGrade.xlsx"
df = pd.read_excel(df_path)
df = df.groupby("Month")["Sipariş Mik. (TON)"].sum().reset_index()
print(df.head())

#df = df[df["Grade"] == 'DX51D+Z']  # Grade filtresi

# Yıl ve ay verisini düzenle
df["Year"] = df["Month"].astype(str).str.split(".").str[1]  # Yıl
df["Month"] = df["Month"].astype(str).str.split(".").str[0].str.zfill(2)  # Ay

df.loc[df["Year"].str.len() == 3, "Year"] = df["Year"] + "0"  # Yıl düzeltme
df["YearMonth"] = df["Year"] + "-" + df["Month"]
df["YearMonth"] = pd.to_datetime(df["YearMonth"], format="%Y-%m")

df = pd.DataFrame({"Date": df["YearMonth"], "Value": df["Sipariş Mik. (TON)"]})
df.set_index("Date", inplace=True)
df = df.sort_values(by="Date")

df = df[df.index >= "2023-01-01"]  # 2019 yılından itibaren veri al

# ----- 2. Euro Kurunu (Exogenous Variable) Hazırlama -----
eur_path = "/Users/ceylin/Desktop/indr491/indr491/doviz_rates/EUR_to_TR .xlsx"
eur_df = pd.read_excel(eur_path, header=1)

eur_df = eur_df[["Tarih", "Şimdi"]]  # Gerekli sütunları al
# rename columns
eur_df.columns = ["Date", "Euro"]
eur_df["Date"] = pd.to_datetime(eur_df["Date"], format="%d.%m.%Y")  # Tarih formatını düzelt
eur_df["Euro"] = eur_df["Euro"].astype(str).str.replace(",", ".").astype(float)  # Virgülleri noktaya çevir

eur_df = eur_df.set_index("Date").sort_index()

df = df[df.index.isin(eur_df.index)]

# df'in tarihleriyle eşleşen Euro kurlarını al
eur_df = eur_df.loc[df.index]
print(eur_df.head())


print(df.head())
print(eur_df.head())

# ----- 3. SARIMAX Modelini Exogenous Değişken ile Eğitme -----
order = (2, 2, 2)  # ARIMA(p, d, q)
seasonal_order = (1, 1, 0, 12)  # Seasonal (P, D, Q, S) 12 aylık sezonluk yapı

train_size = int(len(df) * 0.8)
train, test = df.iloc[:train_size], df.iloc[train_size:]
train_exog, test_exog = eur_df.iloc[:train_size], eur_df.iloc[train_size:]

# Modeli euro kuru ile eğit
model = SARIMAX(train["Value"], train_exog=eur_df["Euro"], order=order, seasonal_order=seasonal_order)
results = model.fit()

# ----- 4. Tahmin Yapma -----
forecast_steps = 3  # 12 ay tahmin edilecek

# Exogenous değişkenin gelecek değerlerini belirleme 
# exog_forecast = np.full(forecast_steps, eur_df["Euro"].iloc[-1]) (Burada son değeri tekrar ederek koyduk)

eur_order = (2, 1, 2)  # ARIMA(p, d, q)
eur_seasonal_order = (1, 1, 1, 12)  # Seasonal yapı

eur_model = SARIMAX(eur_df["Euro"], order=eur_order, seasonal_order=eur_seasonal_order)
eur_results = eur_model.fit()

# Euro kuru için tahmin yap
eur_forecast = eur_results.get_forecast(steps=forecast_steps)

# Euro forecast değerlerini al
exog_forecast = eur_forecast.predicted_mean

# Model ile tahmin yap
forecast = results.get_forecast(steps=forecast_steps, exog=exog_forecast)

forecast_index = pd.date_range(start=df.index[-1] + pd.DateOffset(months=1), periods=forecast_steps, freq="M")
forecast_values = forecast.predicted_mean
conf_int = forecast.conf_int()

# MAPE hesaplama fonksiyonu
def mean_absolute_percentage_error(y_true, y_pred):
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

# Test MAPE'sini hesaplama
test_mape = mean_absolute_percentage_error(test["Value"], forecast_values)

# ----- 5. Sonuçları Görselleştirme -----
plt.figure(figsize=(10, 5))
plt.plot(df.index, df["Value"], label="Observed")
plt.plot(forecast_index, forecast_values, label="Forecast", color="red")
plt.fill_between(forecast_index, conf_int.iloc[:, 0], conf_int.iloc[:, 1], color="pink", alpha=0.3)
plt.legend()
plt.title("SARIMAX Forecast with Euro Exchange Rate")
plt.show()

# Modelin özetini yazdır
print(results.summary())
