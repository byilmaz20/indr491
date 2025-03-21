import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX

# ----- 1. Veriyi Hazırlama -----
df_path = "/Users/ceylin/Desktop/indr491/indr491/preprocessedBelgeler/forecastData_altLimit100_son3_byGrade.xlsx"
df = pd.read_excel(df_path)
df = df.groupby("Month")["Sipariş Mik. (TON)"].sum().reset_index()

# Yıl ve ay düzenleme
df["Year"] = df["Month"].astype(str).str.split(".").str[1]  # Yıl
df["Month"] = df["Month"].astype(str).str.split(".").str[0].str.zfill(2)  # Ay

df.loc[df["Year"].str.len() == 3, "Year"] = df["Year"] + "0"  # Yıl düzeltme
df["YearMonth"] = df["Year"] + "-" + df["Month"]
df["YearMonth"] = pd.to_datetime(df["YearMonth"], format="%Y-%m")

df = pd.DataFrame({"Date": df["YearMonth"], "Value": df["Sipariş Mik. (TON)"]})
df.set_index("Date", inplace=True)
df = df.sort_values(by="Date")
df = df[df.index >= "2023-01-01"] 

# Euro kuru verisini yükleme
eur_path = "/Users/ceylin/Desktop/indr491/indr491/doviz_rates/EUR_to_TR .xlsx"
eur_df = pd.read_excel(eur_path, header=1)
eur_df = eur_df[["Tarih", "Şimdi"]]

eur_df["Tarih"] = pd.to_datetime(eur_df["Tarih"], format="%d.%m.%Y")  # Tarih formatı düzeltme
eur_df["Şimdi"] = eur_df["Şimdi"].astype(str).str.replace(",", ".").astype(float)  # Sayısal hale getirme
eur_df = eur_df.set_index("Tarih").sort_index()

# df içindeki tarihleri euro_df ile kesiştirerek ortak tarihleri al
df = df[df.index.isin(eur_df.index)]
eur_df = eur_df.loc[df.index]  # Euro kuru tarihleri de eşleşmeli

# ----- 2. Grid Search için Parametre Aralığını Belirleme -----
p = d = q = range(0, 3)  # ARIMA (p, d, q) için olası değerler
P = D = Q = range(0, 2)  # Mevsimsel (P, D, Q) için olası değerler
S = [12]  # 12 aylık sezonluk yapı

# Tüm kombinasyonları oluştur
pdq = list(itertools.product(p, d, q))
seasonal_pdq = list(itertools.product(P, D, Q, S))

# En iyi modeli bulmak için boş değişken
best_aic = np.inf  # Başlangıçta sonsuz
best_order = None
best_seasonal_order = None
best_model = None

# ----- 3. Tüm Parametre Kombinasyonlarını Deneme -----
for order in pdq:
    for seasonal_order in seasonal_pdq:
        try:
            # SARIMAX modeli kur
            model = SARIMAX(df["Value"], exog=eur_df["Şimdi"], 
                            order=order, seasonal_order=seasonal_order)
            results = model.fit(disp=False)

            # AIC değerine göre en iyisini bul
            if results.aic < best_aic:
                best_aic = results.aic
                best_order = order
                best_seasonal_order = seasonal_order
                best_model = results

            print(f"SARIMAX{order}x{seasonal_order} - AIC:{results.aic:.2f}")

        except Exception as e:
            print(f"Model SARIMAX{order}x{seasonal_order} başarısız: {e}")

# En iyi modelin detaylarını yazdır
print(f"\nEn iyi model: SARIMAX{best_order}x{best_seasonal_order} - AIC:{best_aic:.2f}")

# ----- 4. En İyi Model ile Tahmin Yapma -----
forecast_steps = 3  # 12 ay tahmin edilecek
exog_forecast = np.full(forecast_steps, eur_df["Şimdi"].iloc[-1])  # Exogenous değişkenin son değerini kullan

forecast = best_model.get_forecast(steps=forecast_steps, exog=exog_forecast)

forecast_index = pd.date_range(start=df.index[-1] + pd.DateOffset(months=1), periods=forecast_steps, freq="M")
forecast_values = forecast.predicted_mean
conf_int = forecast.conf_int()

# ----- 5. Sonuçları Görselleştirme -----
plt.figure(figsize=(10, 5))
plt.plot(df.index, df["Value"], label="Observed")
plt.plot(forecast_index, forecast_values, label="Best Model Forecast", color="red")
plt.fill_between(forecast_index, conf_int.iloc[:, 0], conf_int.iloc[:, 1], color="pink", alpha=0.3)
plt.legend()
plt.title(f"Optimized SARIMAX Forecast (Best AIC: {best_aic:.2f})")
plt.show()
