import numpy as np
import pandas as pd
import xgboost as xgb
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error


# Simulated historical demand dataset
np.random.seed(42)
months = pd.date_range(start="2015-01", periods=100, freq='M')

data = pd.DataFrame({
  "Month": months,
  "Past_Demand": np.random.randint(800, 1500, size=len(months)),  # Historical demand
  "Steel_Price_Index": np.random.uniform(50, 120, size=len(months)),  # Steel price index
  "Energy_Cost": np.random.uniform(30, 100, size=len(months)),  # Energy costs
  "GDP_Growth": np.random.uniform(0.5, 3.5, size=len(months)),  # GDP growth percentage
  "Production_Capacity": np.random.randint(500, 2000, size=len(months))  # Plant capacity
})

# Target Variable: Future Demand (shifted forward)
data["Future_Demand"] = data["Past_Demand"].shift(-1)  # Next month's demand

# Drop last row since it has NaN Future_Demand
data = data.dropna()

# Convert Month to numerical values
data["Month"] = data["Month"].astype("int64") // 10**9  # Convert to timestamp for modeling


# Features (X) and Target (y)
X = data.drop(columns=["Future_Demand"])
y = data["Future_Demand"]

# Train-test split (80% train, 20% test)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)


# Define the XGBoost model
xgb_model = xgb.XGBRegressor(
  objective="reg:squarederror",
  n_estimators=100,
  learning_rate=0.1,
  max_depth=5,
  subsample=0.8,
  colsample_bytree=0.8,
  random_state=42
)

# Train the model
xgb_model.fit(X_train, y_train)


# Predict future demand
y_pred = xgb_model.predict(X_test)

# Evaluate the model
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))

print(f"Mean Absolute Error (MAE): {mae:.2f}")
print(f"Root Mean Squared Error (RMSE): {rmse:.2f}")


plt.figure(figsize=(10,5))
plt.plot(y_test.values, label="Actual Demand", marker='o')
plt.plot(y_pred, label="Predicted Demand", marker='x', linestyle='dashed')
plt.xlabel("Test Samples")
plt.ylabel("Demand")
plt.title("XGBoost Metal Demand Forecasting")
plt.legend()
plt.show()


# Get the most recent row of data
latest_data = data.iloc[-1:].drop(columns=["Future_Demand"])

# Generate future timestamps
future_months = [latest_data["Month"].values[0] + i * 2629800 for i in range(1, 7)]  # Approx. 1 month in seconds

future_forecasts = []
for month in future_months:
  new_data = latest_data.copy()
  new_data["Month"] = month  # Update with future month
  forecast = xgb_model.predict(new_data)[0]
  future_forecasts.append(forecast)

# Convert to DataFrame
future_df = pd.DataFrame({"Month": pd.to_datetime(future_months, unit='s'),
                        "Predicted_Demand": future_forecasts})

# Display the results
# Display the DataFrame nicely
print(future_df.to_string(index=False))
