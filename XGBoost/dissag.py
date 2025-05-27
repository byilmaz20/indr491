import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import matplotlib.pyplot as plt


#gradegroup özelinde tahminle
#sonra specgroup'lara böl sonuçları

# --- Helper metrics ---
def mape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    nonzero = y_true != 0
    return np.mean(np.abs((y_true[nonzero] - y_pred[nonzero]) / y_true[nonzero])) * 100

def smape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2
    nonzero = denom != 0
    return np.mean(np.abs(y_pred[nonzero] - y_true[nonzero]) / denom[nonzero]) * 100

def wmape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return np.sum(np.abs(y_true - y_pred)) / np.sum(np.abs(y_true)) * 100

def main():
    # --- 1) Load and preprocess spec-level data ---
    df = pd.read_excel("/Users/samet/INDR491CodeBase/preprocessedBelgeler/NewforecastData_altLimit100_son3_byGrup.xlsx")
    df["Sipariş Mik. (TON)"] = (
        df["Sipariş Mik. (TON)"]
        .astype(str)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )
    df["Month"] = pd.to_datetime(df["Month"], errors="coerce")
    df = df.dropna(subset=["Month"]).copy()
    df["GradeGroup"] = df["GradeGroup"].astype(str)
    df["MonthNum"] = df["Month"].dt.month

    # Define train/test cutoff date
    last_train = pd.Timestamp("2024-05-31")

    # --- 2) Aggregate to GradeGroup level ---
    grade_df = (
        df.groupby(["GradeGroup", "Month"], as_index=False)
          .agg({"Sipariş Mik. (TON)": "sum"})
          .sort_values(["GradeGroup", "Month"])
    )
    grade_df["MonthNum"] = grade_df["Month"].dt.month

    # --- 3) Feature engineering at GradeGroup ---
    for lag in [1, 2, 3, 6]:
        grade_df[f"lag_{lag}"] = (
            grade_df.groupby("GradeGroup")["Sipariş Mik. (TON)"]
                    .shift(lag)
        )
    grade_df["prev_year_same_month"] = (
        grade_df.groupby("GradeGroup")["Sipariş Mik. (TON)"].shift(12)
    )
    grade_df["rolling_mean_3"] = (
        grade_df.groupby("GradeGroup")["Sipariş Mik. (TON)"]
                .transform(lambda x: x.shift(1).rolling(3).mean())
    )
    grade_df["rolling_mean_6"] = (
        grade_df.groupby("GradeGroup")["Sipariş Mik. (TON)"]
                .transform(lambda x: x.shift(1).rolling(6).mean())
    )
    grade_df["rolling_std_3"] = (
        grade_df.groupby("GradeGroup")["Sipariş Mik. (TON)"]
                .transform(lambda x: x.shift(1).rolling(3).std())
    )
    grade_df["Year"] = grade_df["Month"].dt.year
    grade_df["Quarter"] = grade_df["Month"].dt.quarter
    grade_df["is_start_of_year"] = (grade_df["MonthNum"] == 1).astype(int)

    # Filter 2022+ and drop incomplete rows
    grade_model = grade_df.dropna()
    grade_model = grade_model[grade_model["Year"] >= 2022]

    # Specify features and target
    g_feats = [
        "MonthNum", "Year", "Quarter", "is_start_of_year",
        "lag_1", "lag_2", "lag_3", "lag_6",
        "rolling_mean_3", "rolling_mean_6", "rolling_std_3",
        "prev_year_same_month"
    ]
    g_target = "Sipariş Mik. (TON)"

    # --- 4) Train/test split by date ---
    g_train = grade_model[grade_model["Month"] <= last_train]
    g_test  = grade_model[grade_model["Month"] > last_train]
    if g_test.empty:
        print("No grade-level forecast period found. Check your cutoff date.")
        return

    Xg_train = g_train[g_feats]
    yg_train = g_train[g_target]
    Xg_test  = g_test[g_feats]

    # --- 5) Train XGBoost model on GradeGroup ---
    g_model = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=100,
        learning_rate=0.1,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    g_model.fit(Xg_train, yg_train)

    # Grade-level predictions
    g_test = g_test.copy()
    g_test["grade_pred"] = g_model.predict(Xg_test)

    # --- 6) Compute dynamic historical shares per GradeGroup & MonthNum ---
    hist = (
        df[df["Month"] <= last_train]
        .groupby(["GradeGroup", "MonthNum", "SpecGroupId"], as_index=False)
        .agg({"Sipariş Mik. (TON)": "sum"})
    )
    # Use transform for share to align indices
    hist["share"] = hist.groupby(["GradeGroup", "MonthNum"])["Sipariş Mik. (TON)"].transform(lambda x: x / x.sum())
    shares = hist[["GradeGroup", "MonthNum", "SpecGroupId", "share"]]

    # --- 7) Disaggregate grade forecasts to SpecGroupId ---
    disagg = (
        g_test[["GradeGroup", "MonthNum", "Month", "grade_pred"]]
        .merge(shares, on=["GradeGroup", "MonthNum"], how="left")
    )
    disagg = disagg.dropna(subset=["share"])
    if disagg.empty:
        print("Disaggregation failed: no matching historical shares.")
        return
    disagg["spec_pred"] = disagg["grade_pred"] * disagg["share"]

    # --- 8) Merge with actual spec-levels and evaluate ---
    actuals = df[["SpecGroupId", "Month", "Sipariş Mik. (TON)"]].rename(
        columns={"Sipariş Mik. (TON)": "actual"}
    )
    result = (
        disagg.merge(actuals, on=["SpecGroupId", "Month"], how="inner")
        .dropna(subset=["actual", "spec_pred"])
    )
    if result.empty:
        print("No spec-level records matched for evaluation.")
        return

    mae_val  = mean_absolute_error(result["actual"], result["spec_pred"])
    rmse_val = np.sqrt(mean_squared_error(result["actual"], result["spec_pred"]))
    mape_val = mape(result["actual"], result["spec_pred"])
    smape_val= smape(result["actual"], result["spec_pred"])
    wmape_val= wmape(result["actual"], result["spec_pred"])

    print("\nSpec-level disaggregated performance:")
    print(f"MAE   : {mae_val:.2f}")
    print(f"RMSE  : {rmse_val:.2f}")
    print(f"MAPE  : {mape_val:.2f}%")
    print(f"sMAPE : {smape_val:.2f}%")
    print(f"wMAPE : {wmape_val:.2f}%\n")
    
    grade_actual = g_test[g_target]
    grade_pred   = g_test["grade_pred"]
    grade_wmape  = wmape(grade_actual, grade_pred)
    print(f"Grade-level WMAPE: {grade_wmape:.2f}%")
    
 
    # Grade-level MAE
    #grade_mae = mean_absolute_error(grade_actual, grade_pred)
    #print(f"Grade-level MAE: {grade_mae:.2f}")

    # Grade-level RMSE (manuel)
    #mse = mean_squared_error(grade_actual, grade_pred)
    #grade_rmse = np.sqrt(mse)
    #print(f"Grade-level RMSE: {grade_rmse:.2f}")

    # --- 9) Plot example SpecGroupId forecast ---
    example_ids = result["SpecGroupId"].unique()
    if example_ids.size > 0:
        ex = example_ids[0]
        ex_df = result[result["SpecGroupId"] == ex]
        plt.figure(figsize=(8,4))
        plt.plot(ex_df["Month"], ex_df["actual"], label="Actual", marker="o")
        plt.plot(ex_df["Month"], ex_df["spec_pred"], label="Predicted", linestyle="--", marker="x")
        plt.title(f"SpecGroupId {ex}: Actual vs Disaggregated Forecast")
        plt.xlabel("Month")
        plt.ylabel("Sipariş Mik. (TON)")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    main()
