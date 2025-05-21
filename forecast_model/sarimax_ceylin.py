import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX

path = "/Users/ceylin/Desktop/indr491/indr491/preprocessedBelgeler/forecastData_altLimit100_son3_byGrade.xlsx"
df = pd.read_excel(path)

mask = df["Grade"] == 'DD11'  
df = df[mask]  # Seçilen verileri filtrele

# Yıl ve ay verisini ayırarak düzenle
df["Year"] = df["Month"].astype(str).str.split(".").str[1]  # Yıl bilgisini al
df["Month"] = df["Month"].astype(str).str.split(".").str[0].str.zfill(2)  # Ay bilgisini al ve iki haneli yap

# Eğer Year sütunu 3 haneli ise, başına "0" ekleyerek düzelt (Örneğin: "202" → "2020")
df.loc[df["Year"].str.len() == 3, "Year"] = df["Year"] + "0"

# Yeni "YearMonth" sütununu oluştur
df["YearMonth"] = df["Year"] + "-" + df["Month"]

# Datetime çevirimi (artık hata almayacağız)
df["YearMonth"] = pd.to_datetime(df["YearMonth"], format="%Y-%m")

df = pd.DataFrame({"Date": df["YearMonth"], "Value": df["Sipariş Mik. (TON)"]})
df.set_index("Date", inplace=True)
df = df.sort_values(by="Date") 

print(df.head())



# Plot the data
df.plot(title="Time Series Data", figsize=(10, 5))
plt.show()

# Define SARIMAX model parameters
order = (1, 1, 1)  # ARIMA(p, d, q)
seasonal_order = (1, 1, 1, 12)  # Seasonal (P, D, Q, S) with seasonality of 12 months

# Fit SARIMAX model
model = SARIMAX(df["Value"], order=order, seasonal_order=seasonal_order)
results = model.fit()

# Forecast the next 12 months
forecast = results.get_forecast(steps=12)
forecast_index = pd.date_range(start=df.index[-1] + pd.DateOffset(months=1), periods=12, freq="M")
forecast_values = forecast.predicted_mean
conf_int = forecast.conf_int()

# Plot forecast
plt.figure(figsize=(10, 5))
plt.plot(df.index, df["Value"], label="Observed")
plt.plot(forecast_index, forecast_values, label="Forecast", color="red")
plt.fill_between(forecast_index, conf_int.iloc[:, 0], conf_int.iloc[:, 1], color="pink", alpha=0.3)
plt.legend()
plt.title("SARIMAX Forecast")
plt.show()

# Print model summary
print(results.summary())
