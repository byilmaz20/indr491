import pandas as pd
import numpy as np
from xgboost import XGBRegressor
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.metrics import r2_score

#specgroupid'ler özelinde tahminle
#sonra gradegroup olarak topla sonuçları

# === Load and clean data ===
df = pd.read_excel("/Users/samet/INDR491CodeBase/preprocessedBelgeler/NewforecastData_altLimit100_son3_byGrup.xlsx")
df["Sipariş Mik. (TON)"] = (
    df["Sipariş Mik. (TON)"]
    .astype(str)
    .str.replace(",", ".", regex=False)
    .astype(float)
)
df["Month"] = pd.to_datetime(df["Month"], errors='coerce')
df["month"] = df["Month"].dt.month
df["year"] = df["Month"].dt.year
df = df.dropna(subset=["Month"])
#df["Grade"] = df["Grade"].astype(str)
df["GradeGroup"] = df["GradeGroup"].astype(str)

# === Feature Engineering ===
df = df.sort_values(by=["SpecGroupId", "Month"]).reset_index(drop=True)
lags = [1,2,3,6]
for lag in lags:
    df[f"lag_{lag}"] = df.groupby("SpecGroupId")["Sipariş Mik. (TON)"].shift(lag)
df["prev_year_same_month"] = df.groupby("SpecGroupId")["Sipariş Mik. (TON)"].shift(12)
df["rolling_mean_3"] = df.groupby("SpecGroupId")["Sipariş Mik. (TON)"].transform(lambda x: x.shift(1).rolling(3).mean())
df["rolling_mean_6"] = df.groupby("SpecGroupId")["Sipariş Mik. (TON)"].transform(lambda x: x.shift(1).rolling(6).mean())
df["rolling_std_3"] = df.groupby("SpecGroupId")["Sipariş Mik. (TON)"].transform(lambda x: x.shift(1).rolling(3).std())
df["quarter"] = df["Month"].dt.quarter
df["is_start_of_year"] = (df["Month"].dt.month == 1).astype(int)

df_model = df.dropna().copy()
df_model = df_model[df_model["Month"].dt.year >= 2022].copy()

# === Define features ===
features = [
    "SpecGroupId", "month", "year", "quarter", "is_start_of_year",
    "lag_1", "lag_2", "lag_3", "lag_6", "rolling_mean_3",
    "rolling_mean_6", "rolling_std_3", "prev_year_same_month"
]
target = "Sipariş Mik. (TON)"

# === Correct Train-Test Split ===
train_df = df_model[df_model["Month"] <= pd.Timestamp("2024-05-31")]
test_df = df_model[(df_model["Month"] >= pd.Timestamp("2024-06-01")) & (df_model["Month"] <= pd.Timestamp("2024-12-31"))]

X_train = train_df[features]
y_train = train_df[target]
X_test = test_df[features]
y_test = test_df[target]

# === Train Model ===
model = XGBRegressor(
    objective="reg:squarederror",
    n_estimators=100,
    learning_rate=0.1,
    max_depth=6,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42
)
model.fit(X_train, y_train)


# === Predict ===
test_df = test_df.copy()
test_df["y_pred"] = model.predict(X_test)

# 1. R^2 skorunu hesaplayıp yazdıralım
r2 = r2_score(y_test, test_df["y_pred"])
print(f"\nTest set R² score: {r2:.4f}")

# 2. Feature importance’ı alıp, pandas Series olarak sıralayalım
importances = model.feature_importances_
feat_imp = pd.Series(importances, index=features).sort_values(ascending=False)
print("\nFeature Importance (azalan sırada):")
print(feat_imp)

# 3. Bar chart ile görselleştirme
plt.figure(figsize=(8, 5))
feat_imp.plot(kind='bar')
plt.title("XGBoost Feature Importances\n On Test Set")
plt.xlabel("Feature")
plt.ylabel("Gain-based Feature Importance")
plt.grid(True)
plt.tight_layout()

# Eğer Jupyter/Notebook değil, pencerede görmek için:
plt.show()

# === Helper Metrics ===
def mean_absolute_percentage_error(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    nonzero = y_true != 0
    return np.mean(np.abs((y_true[nonzero] - y_pred[nonzero]) / y_true[nonzero])) * 100

def smape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2
    nonzero = denominator != 0
    return np.mean(np.abs(y_pred[nonzero] - y_true[nonzero]) / denominator[nonzero]) * 100

def wmape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return np.sum(np.abs(y_true - y_pred)) / np.sum(np.abs(y_true)) * 100

# 1. GradeGroup + Month Bazlı Aggregate Performans
grade_month = test_df.groupby(["GradeGroup", "year", "month"]).agg(
    actual_sum=("Sipariş Mik. (TON)", "sum"),
    pred_sum=("y_pred", "sum")
).reset_index()

overall_mae = mean_absolute_error(grade_month["actual_sum"], grade_month["pred_sum"])
overall_mape = mean_absolute_percentage_error(grade_month["actual_sum"], grade_month["pred_sum"])
overall_smape = smape(grade_month["actual_sum"], grade_month["pred_sum"])
overall_wmape = wmape(grade_month["actual_sum"], grade_month["pred_sum"])
overall_rmse = np.sqrt(mean_squared_error(grade_month["actual_sum"], grade_month["pred_sum"]))

print("\n(Grade + Ay Bazlı) Toplam Performans:")
print(f"MAE   : {overall_mae:.4f}")
print(f"MAPE  : {overall_mape:.2f}%")
print(f"sMAPE : {overall_smape:.2f}%")
print(f"wMAPE : {overall_wmape:.2f}%")
print(f"RMSE  : {overall_rmse:.4f}")

# === 2. Son 7 Ay Performansı ===
last_months = test_df["Month"].sort_values().unique()

monthly_performance = []
for month in last_months:
    temp = test_df[test_df["Month"] == month]
    if len(temp) > 0:
        mae = mean_absolute_error(temp["Sipariş Mik. (TON)"], temp["y_pred"])
        mape = mean_absolute_percentage_error(temp["Sipariş Mik. (TON)"], temp["y_pred"])
        monthly_performance.append((month, mae, mape))

monthly_perf_df = pd.DataFrame(monthly_performance, columns=["Month", "MAE", "MAPE"])
print("\nSon 7 Ay Performansı:\n", monthly_perf_df)

# === 3. Özel SpecGroup Performansı ve Grafik ===
special_ids = [670, 847, 478, 492]
special_perf = []

for gid in special_ids:
    temp = test_df[test_df["SpecGroupId"] == gid]
    if len(temp) > 0:
        mae = mean_absolute_error(temp["Sipariş Mik. (TON)"], temp["y_pred"])
        mape = mean_absolute_percentage_error(temp["Sipariş Mik. (TON)"], temp["y_pred"])
        smape_val = smape(temp["Sipariş Mik. (TON)"], temp["y_pred"])
        wmape_val = wmape(temp["Sipariş Mik. (TON)"], temp["y_pred"])
        special_perf.append((gid, mae, mape, smape_val, wmape_val))

special_perf_df = pd.DataFrame(special_perf, columns=["GroupId", "MAE", "MAPE (%)", "sMAPE (%)", "wMAPE (%)"])
print("\nÖzel SpecGroup Performansı:\n", special_perf_df)

# === 4. Line Graphs (corrected style) ===
fig, axes = plt.subplots(2, 2, figsize=(15, 10))
axes = axes.flatten()

for idx, gid in enumerate(special_ids):
    temp_full = df_model[df_model["SpecGroupId"] == gid].copy()
    temp_pred = test_df[test_df["SpecGroupId"] == gid].copy()
    
    axes[idx].plot(temp_full["Month"], temp_full["Sipariş Mik. (TON)"], label="Gerçek", marker="o", color="blue")
    axes[idx].plot(temp_pred["Month"], temp_pred["y_pred"], label="Tahmin", marker="x", linestyle="--", color="orange")
    
    axes[idx].set_title(f"SpecGroupId {gid} – Gerçek Sipariş vs Tahmin")
    axes[idx].set_xlabel("Ay")
    axes[idx].set_ylabel("Sipariş Miktarı (TON)")
    axes[idx].legend()
    axes[idx].grid(True)

plt.tight_layout()
plt.show()

# === 5. 2024 Haziran ve Temmuz Grade Bazlı Bar Chart ===
months_to_plot = [(2024,6), (2024,7)]
for year, month in months_to_plot:
    temp = test_df[(test_df["year"] == year) & (test_df["month"] == month)]
    if len(temp) > 0:
        grouped = temp.groupby("GradeGroup").agg(
            actual_sum=("Sipariş Mik. (TON)", "sum"),
            pred_sum=("y_pred", "sum")
        ).reset_index()

        grouped.plot(kind="bar", x="GradeGroup", y=["actual_sum", "pred_sum"], figsize=(10,6))
        plt.title(f"{year}-{month:02d} Grade Bazlı Tahmin vs Gerçek Sipariş")
        plt.ylabel("Sipariş Miktarı (TON)")
        plt.grid(True)
        plt.show()
