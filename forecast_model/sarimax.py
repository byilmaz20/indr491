import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX

# Generate a sample time series dataset
np.random.seed(42)
dates = pd.date_range(start="2020-01-01", periods=100, freq="M")
data = 10 + np.sin(np.linspace(0, 20, 100)) + np.random.normal(0, 0.5, 100)  # Seasonal pattern + noise
df = pd.DataFrame({"Date": dates, "Value": data})
df.set_index("Date", inplace=True)

print(df.head())



file_path = "/Users/ceylin/Desktop/indr491/indr491/mmkBelgeler/KU003 Siparişler.xlsx"
df = pd.read_excel(file_path, header=1)
sarimax_df = df[["Teslimat tarihi", "Açık Mik.(TON)"]]





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
