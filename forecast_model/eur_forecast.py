import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX

eur_path = "/Users/ceylin/Desktop/indr491/indr491/doviz_rates/EUR_to_TR .xlsx"
eur_df = pd.read_excel(eur_path, header=1)

eur_df = eur_df[["Tarih", "Şimdi"]]  # Gerekli sütunları al
# rename columns
eur_df.columns = ["Date", "Euro"]
eur_df["Date"] = pd.to_datetime(eur_df["Date"], format="%d.%m.%Y")  # Tarih formatını düzelt
eur_df["Euro"] = eur_df["Euro"].astype(str).str.replace(",", ".").astype(float)  # Virgülleri noktaya çevir

eur_df = eur_df.set_index("Date").sort_index()


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
            model = SARIMAX(eur_df["Euro"], 
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
forecast_steps = 3  # 3 ay tahmin edilecek

forecast = best_model.get_forecast(steps=forecast_steps)

forecast_index = pd.date_range(start=eur_df.index[-1] + pd.DateOffset(months=1), periods=forecast_steps, freq="M")
forecast_values = forecast.predicted_mean
conf_int = forecast.conf_int()

# ----- 5. Sonuçları Görselleştirme -----
plt.figure(figsize=(10, 5))
plt.plot(eur_df.index, eur_df["Euro"], label="Observed")
plt.plot(forecast_index, forecast_values, label="Best Model Forecast", color="red")
plt.fill_between(forecast_index, conf_int.iloc[:, 0], conf_int.iloc[:, 1], color="pink", alpha=0.3)
plt.legend()
plt.title(f"Optimized SARIMAX Forecast (Best AIC: {best_aic:.2f})")
plt.show()


