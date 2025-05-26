import pandas as pd
import numpy as np
from pmdarima import acf
from statsmodels.tsa.statespace.sarimax import SARIMAX
import matplotlib.pyplot as plt
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
import os
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
from statsmodels.tsa.stattools import adfuller

def find_best_sarimax_order(ts, train_end_date, full_series):
    best_mape = np.inf
    best_order = None
    best_seasonal_order = None

    ts = ts.dropna()

    # ADF testi
    try:
        adf_pvalue = adfuller(ts)[1]
        d = 0 if adf_pvalue < 0.05 else 1
    except:
        d = 0

    # ACF testi
    try:
        acf_values = acf(ts, nlags=24)
        if len(acf_values) > 12 and acf_values[12] > 0.3:
            seasonal = True
            s = 12
        else:
            seasonal = False
            s = 0
    except:
        seasonal = False
        s = 0

    for p in range(0, 3):
        for q in range(0, 3):
            try:
                if seasonal:
                    seasonal_order = (1,0,1,s)
                else:
                    seasonal_order = (0,0,0,0)

                model = SARIMAX(ts, order=(p,d,q), seasonal_order=seasonal_order,
                                enforce_stationarity=False, enforce_invertibility=False)
                results = model.fit(disp=False)

                forecast = results.get_forecast(steps=7)
                forecast_mean = forecast.predicted_mean

                test_data = full_series.loc[train_end_date:]
                common_months = test_data.index.intersection(forecast_mean.index)

                if len(common_months) == 0:
                    continue

                actual = test_data.loc[common_months]
                predicted = forecast_mean.loc[common_months]

                mape = mean_absolute_percentage_error(actual, predicted) * 100

                if mape < best_mape:
                    best_mape = mape
                    best_order = (p,d,q)
                    best_seasonal_order = seasonal_order

            except:
                continue

    if best_order is None:
        best_order = (1,0,1)
        best_seasonal_order = (0,0,0,0)
        best_mape = np.nan

    return best_order, best_seasonal_order, best_mape


# %%



np.set_printoptions(suppress=True)
pd.options.display.float_format = '{:,.2f}'.format

# 1. Veri yükleme
base_dir = os.path.dirname(__file__)  # bulunduğun dosyanın konumu
excel_path = os.path.join(base_dir, '..', 'preprocessedBelgeler', 'NewforecastData_altLimit100_son3_byGrup.xlsx')
df = pd.read_excel(excel_path)
#df = pd.read_excel('../preprocessedBelgeler/NewforecastData_altLimit100_son3_byGrup.xlsx')  # Dosya adını değiştir
df.columns = ['Month', 'SpecGroupId', 'Grade', 'Sipariş Mik. (TON)', 'GradeGroup']
df['Month'] = pd.to_datetime(df['Month'])
df['SpecGroupId'] = df['SpecGroupId'].astype(str)

# 2. Aylık grade bazlı toplam sipariş
monthly_grade = df.groupby(['Month', 'GradeGroup'])['Sipariş Mik. (TON)'].sum().reset_index()
grade_list = monthly_grade['GradeGroup'].unique()

# Tahminler ve dağıtılmış sonuçlar için boş dataframe
forecast_df = pd.DataFrame()
train_forecast_df = pd.DataFrame()
disaggregated_df = pd.DataFrame()
disaggregated_forecast_df = pd.DataFrame()


mae_list = []
mape_list = []

sarimax_param_log = []

# 3. Her grade için SARIMAX modeli ile tahmin
for grade in grade_list:
    # 1. Grade'e ait zaman serisini hazırla
    grade_data = monthly_grade[monthly_grade['GradeGroup'] == grade].set_index('Month')
    
    # 🔒 Model verisini 2018-01 ile 2024-12 arasında sınırla
    grade_data = grade_data.loc['2022-01':'2024-06']

    grade_ts = grade_data['Sipariş Mik. (TON)'].asfreq('MS').fillna(0)
    
    # 2. ❗ Sabit ya da boş seri kontrolü
    if grade_ts.std() < 1e-3 or grade_ts.sum() == 0:
        print(f"'{grade}' atlandı çünkü zaman serisi sabit veya boş.")
        continue  # bu grade'i atla

   

    # 3. SARIMAX Modeli
    try:
        # 🔥 Grade'e özel en iyi order'ı, seasonal order'ı ve best_mape'i bul
        full_grade_data = monthly_grade[monthly_grade['GradeGroup'] == grade].set_index('Month')  # full series data çekiyoruz
        full_grade_data = full_grade_data.loc['2022-01':'2025-02']  # geçmiş+gelecek tüm veri

        best_order, best_seasonal_order, best_mape = find_best_sarimax_order(
            grade_ts, 
            train_end_date='2024-07-01', 
            full_series=full_grade_data['Sipariş Mik. (TON)'].asfreq('MS').fillna(0)
        )

        print(f"Grade '{grade}' için seçilen SARIMAX order (MAPE bazlı): {best_order}, seasonal_order: {best_seasonal_order}, MAPE: {best_mape:.2f}%")

        # 🔥 SARIMAX Modeli kur
        model = SARIMAX(grade_ts, order=best_order, seasonal_order=best_seasonal_order)
        results = model.fit(disp=False)
        print(results.summary())
        # 🔥 Logla
        sarimax_param_log.append({
            'GradeGroup': grade,
            'Order': best_order,
            'Seasonal_Order': best_seasonal_order,
            'MAPE (%)': round(best_mape, 2)
        })



    except Exception as e:
        print(f"{grade} için model kurulamadı: {e}")
        continue

    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    plot_acf(grade_ts, lags=12, ax=ax[0])
    ax[0].set_title(f"{grade} - ACF (Sipariş Mik.)")
    
    plot_pacf(grade_ts, lags=12, ax=ax[1], method='ywm')  # 'ywm' daha stabil PACF için
    ax[1].set_title(f"{grade} - PACF (Sipariş Mik.)")

    plt.tight_layout()
    plt.show()
    
    # 4. Tahmin (örnek: 7 ay ileri)
    forecast = results.get_forecast(steps=8)
    forecast_values = forecast.predicted_mean
    forecast_index = forecast_values.index
    
    train_forecast = results.predict(start=grade_ts.index[0], end=grade_ts.index[-1])
    train_forecast_index = train_forecast.index
    
    # 🔍 Gerçek 2025 verisini al
    full_grade_data = monthly_grade[monthly_grade['GradeGroup'] == grade].set_index('Month')
    test_data = full_grade_data.loc['2024-07':'2025-02']['Sipariş Mik. (TON)'].asfreq('MS').fillna(0)
    common_months = test_data.index.intersection(forecast_index)

    print(common_months)
    if len(common_months) > 0:
        actual = test_data.loc[common_months]
        predicted = forecast_values.loc[common_months]

        mae = mean_absolute_error(actual, predicted)
        mape = mean_absolute_percentage_error(actual, predicted)

        mae_list.append({'GradeGroup': grade, 'MAE_Model': mae})
        mape_list.append({'GradeGroup': grade, 'MAPE_Model': mape})

        print(f"\n📈 GradeGroup '{grade}' için MODEL tahmini:")
        print(f"Gerçek: {actual.values}, Tahmin: {predicted.values}")
        print(f"MAE: {mae:.2f}, MAPE: {mape:.2%}")

    # 5. Forecast DataFrame'e ekle
    temp_forecast = pd.DataFrame({
        'Month': forecast_index,
        'GradeGroup': grade,
        'Forecast_TON': forecast_values.values
    })
    forecast_df = pd.concat([forecast_df, temp_forecast], ignore_index=True)
    
    temp_forecast_train = pd.DataFrame({
        'Month': train_forecast_index,
        'GradeGroup': grade,
        'Forecast_TON': train_forecast.values
    })
    train_forecast_df = pd.concat([train_forecast_df, temp_forecast_train], ignore_index=True)
    
    # 6. Disaggregation (her tahmin edilen ayı specGroupId'lere dağıt)
    for month in forecast_index:
        # Önce o grade'in geçmiş aynı aya ait oranlarını bul
        past_months = df[(df['GradeGroup'] == grade) & (df['Month'].dt.month == month.month)]
        past_months_total = past_months.groupby('SpecGroupId')['Sipariş Mik. (TON)'].sum()
        total = past_months_total.sum()
        

        # Eğer ay bazlı veri yoksa: tüm geçmişi fallback olarak kullan
        if total == 0:
            print(f"{grade} için {month.strftime('%Y-%m')} ayında geçmiş ay bazlı oran bulunamadı. Tüm geçmişten alınacak.")
            past_months = df[df['GradeGroup'] == grade]
            past_months_total = past_months.groupby('SpecGroupId')['Sipariş Mik. (TON)'].sum()
            total = past_months_total.sum()

        # Hâlâ yoksa atla
        if total == 0:
            print(f"{grade} için {month.strftime('%Y-%m')} ayında hiçbir geçmiş veri bulunamadı.")
            continue

        proportions = past_months_total / total
        disagg = proportions * forecast_values[month]

        for spec_id, miktar in disagg.items():
            disaggregated_df = pd.concat([disaggregated_df, pd.DataFrame({
                'Month': [month],
                'GradeGroup': [grade],
                'SpecGroupId': [spec_id],
                'Forecast_TON': [miktar]
            })])
        
        

        # 💡 SpecGroupId bazlı gerçek değerlerle kıyasla
        actual_df = df[(df['Month'] == month) & (df['GradeGroup'] == grade)]
        actual_agg = actual_df.groupby('SpecGroupId')['Sipariş Mik. (TON)'].sum()

        forecast_agg = disaggregated_df[
            (disaggregated_df['Month'] == month) &
            (disaggregated_df['GradeGroup'] == grade)
        ].groupby('SpecGroupId')['Forecast_TON'].sum()

        common_index = actual_agg.index.intersection(forecast_agg.index)

        if len(common_index) > 0:
            actual_vals = actual_agg.loc[common_index]
            pred_vals = forecast_agg.loc[common_index]

            mae_spec = mean_absolute_error(actual_vals, pred_vals)
            mape_spec = mean_absolute_percentage_error(actual_vals, pred_vals)

            # 🔁 Sonuçları listeye ekle
            for spec_id in common_index:
                disagg_metrics = {
                    'GradeGroup': grade,
                    'Month': month,
                    'SpecGroupId': spec_id,
                    'MAE_Disagg': abs(actual_vals[spec_id] - pred_vals[spec_id]),
                    'MAPE_Disagg': abs((actual_vals[spec_id] - pred_vals[spec_id]) / actual_vals[spec_id]) if actual_vals[spec_id] != 0 else np.nan
                }
                mae_list.append(disagg_metrics)


# %%
"""
import pandas as pd
import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX
import matplotlib.pyplot as plt
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

np.set_printoptions(suppress=True)
pd.options.display.float_format = '{:,.2f}'.format

# 1. Veri yükleme
df = pd.read_excel('../preprocessedBelgeler/NewforecastData_altLimit100_son3_byGrup.xlsx')  # Dosya adını değiştir
df.columns = ['Month', 'SpecGroupId', 'Grade', 'Sipariş Mik. (TON)', 'GradeGroup']
df['Month'] = pd.to_datetime(df['Month'])
df['SpecGroupId'] = df['SpecGroupId'].astype(str)

# 2. Aylık grade bazlı toplam sipariş
monthly_grade = df.groupby(['Month', 'GradeGroup'])['Sipariş Mik. (TON)'].sum().reset_index()
grade_list = monthly_grade['GradeGroup'].unique()

# Tahminler ve dağıtılmış sonuçlar için boş dataframe
forecast_df = pd.DataFrame()
train_forecast_df = pd.DataFrame()
disaggregated_df = pd.DataFrame()
disaggregated_forecast_df = pd.DataFrame()


mae_list = []
mape_list = []

sarimax_param_log = []

# 3. Her grade için SARIMAX modeli ile tahmin
for grade in grade_list:
    # 1. Grade'e ait zaman serisini hazırla
    grade_data = monthly_grade[monthly_grade['GradeGroup'] == grade].set_index('Month')
    
    # 🔒 Model verisini 2018-01 ile 2024-12 arasında sınırla
    grade_data = grade_data.loc['2022-01':'2025-02']

    grade_ts = grade_data['Sipariş Mik. (TON)'].asfreq('MS').fillna(0)
    
    # 2. ❗ Sabit ya da boş seri kontrolü
    if grade_ts.std() < 1e-3 or grade_ts.sum() == 0:
        print(f"'{grade}' atlandı çünkü zaman serisi sabit veya boş.")
        continue  # bu grade'i atla

   

    # 3. SARIMAX Modeli
    try:
        # 🔥 Grade'e özel en iyi order'ı, seasonal order'ı ve best_mape'i bul
        full_grade_data = monthly_grade[monthly_grade['GradeGroup'] == grade].set_index('Month')  # full series data çekiyoruz
        full_grade_data = full_grade_data.loc['2022-01':'2025-02']  # geçmiş+gelecek tüm veri

        best_order, best_seasonal_order, best_mape = find_best_sarimax_order(
            grade_ts, 
            train_end_date='2025-03-01', 
            full_series=full_grade_data['Sipariş Mik. (TON)'].asfreq('MS').fillna(0)
        )

        print(f"Grade '{grade}' için seçilen SARIMAX order (MAPE bazlı): {best_order}, seasonal_order: {best_seasonal_order}, MAPE: {best_mape:.2f}%")

        # 🔥 SARIMAX Modeli kur
        model = SARIMAX(grade_ts, order=best_order, seasonal_order=best_seasonal_order)
        results = model.fit(disp=False)
        print(results.summary())
        # 🔥 Logla
        sarimax_param_log.append({
            'GradeGroup': grade,
            'Order': best_order,
            'Seasonal_Order': best_seasonal_order,
            'MAPE (%)': round(best_mape, 2)
        })



    except Exception as e:
        print(f"{grade} için model kurulamadı: {e}")
        continue

    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    plot_acf(grade_ts, lags=12, ax=ax[0])
    ax[0].set_title(f"{grade} - ACF (Sipariş Mik.)")
    
    plot_pacf(grade_ts, lags=12, ax=ax[1], method='ywm')  
    ax[1].set_title(f"{grade} - PACF (Sipariş Mik.)")

    plt.tight_layout()
    plt.show()
    
    # 4. Tahmin (örnek: 7 ay ileri)
    forecast = results.get_forecast(steps=3)
    forecast_values = forecast.predicted_mean
    forecast_index = forecast_values.index
    
    train_forecast = results.predict(start=grade_ts.index[0], end=grade_ts.index[-1])
    train_forecast_index = train_forecast.index
    
    
    
    # 6. Disaggregation (her tahmin edilen ayı specGroupId'lere dağıt)
    for month in forecast_index:
        # Önce o grade'in geçmiş aynı aya ait oranlarını bul
        past_months = df[(df['GradeGroup'] == grade) & (df['Month'].dt.month == month.month)]
        past_months_total = past_months.groupby('SpecGroupId')['Sipariş Mik. (TON)'].sum()
        total = past_months_total.sum()
        

        # Eğer ay bazlı veri yoksa: tüm geçmişi fallback olarak kullan
        if total == 0:
            print(f"{grade} için {month.strftime('%Y-%m')} ayında geçmiş ay bazlı oran bulunamadı. Tüm geçmişten alınacak.")
            past_months = df[df['GradeGroup'] == grade]
            past_months_total = past_months.groupby('SpecGroupId')['Sipariş Mik. (TON)'].sum()
            total = past_months_total.sum()

        # Hâlâ yoksa atla
        if total == 0:
            print(f"{grade} için {month.strftime('%Y-%m')} ayında hiçbir geçmiş veri bulunamadı.")
            continue

        proportions = past_months_total / total
        disagg = proportions * forecast_values[month]

        for spec_id, miktar in disagg.items():
            disaggregated_df = pd.concat([disaggregated_df, pd.DataFrame({
                'Month': [month],
                'GradeGroup': [grade],
                'SpecGroupId': [spec_id],
                'Forecast_TON': [miktar]
            })])
        
disaggregated_df.to_excel('../results/SARIMAX_forecast.xlsx', index=False)
       """


# %%


# %%
params_df = pd.DataFrame(sarimax_param_log)
print("\n📋 Grade Bazlı SARIMAX Parametreleri ve MAPE Skorları:")
print(params_df.sort_values(by='MAPE (%)').reset_index(drop=True))

# (İstersen Excel'e aktar)
# params_df.to_excel("sarimax_parametreleri_mape.xlsx", index=False)



# %%
from sklearn.metrics import mean_squared_error

# 🎯 Grade bazlı performans metriklerini hesapla
grade_metrics = []

# forecast_df: grade bazlı 3 aylık tahminlerin olduğu dataframe
# monthly_grade: gerçek değerlerin olduğu dataframe

for grade in forecast_df['GradeGroup'].unique():
    # Tahmin edilen veriler
    pred_series = forecast_df[forecast_df['GradeGroup'] == grade].set_index('Month')['Forecast_TON']
    
    # Gerçek veriler
    actual_series = monthly_grade[monthly_grade['GradeGroup'] == grade].set_index('Month')['Sipariş Mik. (TON)']
    
    # Ortak aylar
    common_months = pred_series.index.intersection(actual_series.index)
    
    if len(common_months) == 0:
        continue

    y_true = actual_series.loc[common_months]
    y_pred = pred_series.loc[common_months]

    mae = mean_absolute_error(y_true, y_pred)
    mape = mean_absolute_percentage_error(y_true, y_pred) * 100
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    smape = 100 * np.mean(2 * np.abs(y_pred - y_true) / (np.abs(y_true) + np.abs(y_pred)))
    wmape = 100 * np.sum(np.abs(y_pred - y_true)) / np.sum(np.abs(y_true))

    grade_metrics.append({
        'GradeGroup': grade,
        'MAE': mae,
        'MAPE (%)': mape,
        'sMAPE (%)': smape,
        'wMAPE (%)': wmape,
        'RMSE': rmse
    })

# 🎉 Sonuçları tablo olarak göster
grade_metrics_df = pd.DataFrame(grade_metrics)
print("\n📊 GradeGroup Bazlı Tahmin Performansı:")
print(grade_metrics_df)

# Excel'e kaydetmek istersen:
# grade_metrics_df.to_excel("grade_metrics_summary.xlsx", index=False)


# %%
from sklearn.metrics import mean_squared_error, mean_absolute_error, mean_absolute_percentage_error

# 🎯 Tüm Grade'ler için genel hata metrikleri
# forecast_df: tahminler (2025-01 ~ 2025-03)
# monthly_grade: gerçek değerler

# Gerçek veriyi 2025-01 ile 2025-03 arasından alalım
actual_all = monthly_grade[
    (monthly_grade['Month'] >= '2024-07') & 
    (monthly_grade['Month'] <= '2025-02')
]

# Tahmin edilen veriler zaten forecast_df içinde (her Grade için)
merged_all = pd.merge(
    actual_all, 
    forecast_df, 
    on=['Month', 'GradeGroup'], 
    how='inner'
)

# Boş varsa at
merged_all.dropna(subset=['Sipariş Mik. (TON)', 'Forecast_TON'], inplace=True)
print(merged_all)
# Gerçek ve tahmin serileri
y_true_all = merged_all['Sipariş Mik. (TON)']
y_pred_all = merged_all['Forecast_TON']

# Hata metrikleri
mae_all = mean_absolute_error(y_true_all, y_pred_all)
mape_all = mean_absolute_percentage_error(y_true_all, y_pred_all) * 100
rmse_all = np.sqrt(mean_squared_error(y_true_all, y_pred_all))
smape_all = 100 * np.mean(2 * np.abs(y_pred_all - y_true_all) / (np.abs(y_true_all) + np.abs(y_pred_all)))
wmape_all = 100 * np.sum(np.abs(y_pred_all - y_true_all)) / np.sum(np.abs(y_true_all))

# 📢 Sonuçları yazdır
print("\n📦 Tüm GradeGroup'lar için TOPLAM tahmin performansı:")
print(f"MAE   : {mae_all:.2f}")
print(f"MAPE  : {mape_all:.2f}%")
print(f"sMAPE : {smape_all:.2f}%")
print(f"wMAPE : {wmape_all:.2f}%")
print(f"RMSE  : {rmse_all:.2f}")


# %%
import matplotlib.pyplot as plt

# 🎯 Hedef aylar
target_months = ['2024-07','2024-08', '2024-09', '2024-10','2024-11','2024-12','2025-01','2025-02']

for month in target_months:
    print(f"⏳ {month} ayı için grafik hazırlanıyor...")

    forecast_m = forecast_df[forecast_df['Month'] == month]
    actual_m = monthly_grade[monthly_grade['Month'] == month]

    # Verileri aynı forma sok
    forecast_m = forecast_m[['GradeGroup', 'Forecast_TON']].set_index('GradeGroup')
    actual_m = actual_m[['GradeGroup', 'Sipariş Mik. (TON)']].set_index('GradeGroup')

    # Ortak grade'leri al
    common_grades = forecast_m.index.intersection(actual_m.index)

    if len(common_grades) == 0:
        print(f"⚠️ {month} için hem tahmin hem gerçek veri yok.")
        continue

    compare_df = pd.DataFrame({
        'Forecast': forecast_m.loc[common_grades]['Forecast_TON'],
        'Actual': actual_m.loc[common_grades]['Sipariş Mik. (TON)']
    }).sort_index()

    # Bar chart
    # colors
    compare_df.plot(kind='bar', figsize=(12,6))
    plt.title(f"{month} - Forecast vs Actual Orders by Grade Group")
    plt.ylabel("Ordered Amount (Tons)")
    plt.xlabel("GradeGroup")
    plt.xticks(rotation=45)
    plt.legend(["Forecasted", "Actual"])
    plt.tight_layout()
    plt.show()



# %%
import matplotlib.pyplot as plt

# 🎯 Seçmek istediğin SpecGroupId’leri belirle
selected_spec_ids = [ '166', '845', '669','656','825' ]  # buraya ilgilendiğin ID'leri yaz

for spec_id in selected_spec_ids:
    # 🔹 Gerçek veriler (geçmiş)
    actual_series = df[df['SpecGroupId'] == spec_id][['Month', 'Sipariş Mik. (TON)']].copy()
    actual_series = actual_series.groupby('Month').sum().sort_index()
    actual_series.rename(columns={'Sipariş Mik. (TON)': 'Actual'}, inplace=True)

    # 🔹 Tahmin verileri (disaggregated)
    forecast_series = disaggregated_df[disaggregated_df['SpecGroupId'] == spec_id][['Month', 'Forecast_TON']].copy()
    forecast_series = forecast_series.groupby('Month').sum().sort_index()
    forecast_series.rename(columns={'Forecast_TON': 'Forecast'}, inplace=True)

    
    # 🔗 İki veri setini birleştir
    merged = pd.concat([actual_series, forecast_series], axis=1)
    # colors are grey for actual and red for forecast
    
    # 📈 Grafik
    plt.figure(figsize=(12, 5))

    plt.plot(merged.index, merged['Actual'], label='Actual', marker='o', color='grey')
    plt.plot(merged.index, merged['Forecast'], label='Forecast', linestyle='--', marker='x', color='red')
    plt.title(f"SpecGroupId {spec_id} – Forecasted vs Actual Orders")
    plt.xlabel("Month")
    plt.ylabel("Ordered Amount (Tons)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error

# 🎯 Seçmek istediğin SpecGroupId’leri belirle
selected_spec_ids = ['166', '845', '669','656','825']

# Sonuçları saklamak için boş DataFrame oluştur
metrics_df = pd.DataFrame(columns=['SpecGroupId', 'MAE', 'MAPE (%)', 'sMAPE (%)', 'wMAPE (%)', 'RMSE'])

for spec_id in selected_spec_ids:
    # 🔹 Gerçek veriler (geçmiş)
    actual_series = df[df['SpecGroupId'] == spec_id][['Month', 'Sipariş Mik. (TON)']].copy()
    actual_series = actual_series.groupby('Month').sum().sort_index()
    actual_series.rename(columns={'Sipariş Mik. (TON)': 'Actual'}, inplace=True)

    # 🔹 Tahmin verileri (disaggregated)
    forecast_series = disaggregated_df[disaggregated_df['SpecGroupId'] == spec_id][['Month', 'Forecast_TON']].copy()
    forecast_series = forecast_series.groupby('Month').sum().sort_index()
    forecast_series.rename(columns={'Forecast_TON': 'Forecast'}, inplace=True)

    # 🔗 İki veri setini birleştir ve NaN değerleri kaldır
    merged = pd.concat([actual_series, forecast_series], axis=1).dropna()

    # 📌 Hata metriklerini hesapla
    mae = mean_absolute_error(merged['Actual'], merged['Forecast'])
    mape = mean_absolute_percentage_error(merged['Actual'], merged['Forecast']) * 100
    rmse = np.sqrt(mean_squared_error(merged['Actual'], merged['Forecast']))

    # sMAPE hesapla
    smape = 100 * np.mean(2 * np.abs(merged['Forecast'] - merged['Actual']) / (np.abs(merged['Actual']) + np.abs(merged['Forecast'])))

    # wMAPE hesapla
    wmape = 100 * np.sum(np.abs(merged['Forecast'] - merged['Actual'])) / np.sum(np.abs(merged['Actual']))

    # Sonuçları DataFrame'e ekle
    metrics_df = metrics_df.append({'SpecGroupId': spec_id,
                                    'MAE': mae,
                                    'MAPE (%)': mape,
                                    'sMAPE (%)': smape,
                                    'wMAPE (%)': wmape,
                                    'RMSE': rmse}, ignore_index=True)

# 📊 Sonuçları göster
print(metrics_df)



# %%
# 🔁 Eğer tüm SpecGroupId'ler için metrik hesaplanmadıysa onları da hesaplayalım
if len(metrics_df) < df['SpecGroupId'].nunique():
    all_spec_ids = df['SpecGroupId'].astype(str).unique()
    for spec_id in all_spec_ids:
        if spec_id in metrics_df['SpecGroupId'].astype(str).values:
            continue  # zaten hesaplandıysa atla

        actual_series = df[df['SpecGroupId'].astype(str) == spec_id][['Month', 'Sipariş Mik. (TON)']].copy()
        actual_series = actual_series.groupby('Month').sum().sort_index()
        actual_series.rename(columns={'Sipariş Mik. (TON)': 'Actual'}, inplace=True)

        forecast_series = disaggregated_df[disaggregated_df['SpecGroupId'].astype(str) == spec_id][['Month', 'Forecast_TON']].copy()
        forecast_series = forecast_series.groupby('Month').sum().sort_index()
        forecast_series.rename(columns={'Forecast_TON': 'Forecast'}, inplace=True)

        merged = pd.concat([actual_series, forecast_series], axis=1).dropna()

        if len(merged) == 0 or merged['Actual'].sum() == 0:
            continue

        mae = mean_absolute_error(merged['Actual'], merged['Forecast'])
        mape = mean_absolute_percentage_error(merged['Actual'], merged['Forecast']) * 100
        rmse = np.sqrt(mean_squared_error(merged['Actual'], merged['Forecast']))
        smape = 100 * np.mean(2 * np.abs(merged['Forecast'] - merged['Actual']) / (np.abs(merged['Actual']) + np.abs(merged['Forecast'])))
        wmape = 100 * np.sum(np.abs(merged['Forecast'] - merged['Actual'])) / np.sum(np.abs(merged['Actual']))

        metrics_df = metrics_df.append({'SpecGroupId': spec_id,
                                        'MAE': mae,
                                        'MAPE (%)': mape,
                                        'sMAPE (%)': smape,
                                        'wMAPE (%)': wmape,
                                        'RMSE': rmse}, ignore_index=True)

# 🔝 En düşük wMAPE’ye sahip 10 SpecGroupId’yi yazdır
top_10_spec = metrics_df.sort_values(by='wMAPE (%)').head(1321)

print("\n🔝 En iyi 10 SpecGroupId (wMAPE bazlı):")
print(top_10_spec[['SpecGroupId', 'wMAPE (%)']])


# %%
# Gerekli kütüphaneler
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error

# Tüm SpecGroupId'ler için gerçek verileri hazırla
actual_series_all = df[['Month', 'SpecGroupId', 'Sipariş Mik. (TON)']].groupby(['Month', 'SpecGroupId']).sum().sort_index()
actual_series_all.rename(columns={'Sipariş Mik. (TON)': 'Actual'}, inplace=True)

# Tüm SpecGroupId'ler için tahmin verilerini hazırla
forecast_series_all = disaggregated_df[['Month', 'SpecGroupId', 'Forecast_TON']].groupby(['Month', 'SpecGroupId']).sum().sort_index()
forecast_series_all.rename(columns={'Forecast_TON': 'Forecast'}, inplace=True)

# 🔗 Verileri birleştir
merged_all = pd.concat([actual_series_all, forecast_series_all], axis=1).dropna()

# Gerçek değeri 0.1'den büyük olanları filtrele
filtered_merged = merged_all[merged_all['Actual'] > 0.1]

print("total_count", len(merged_all))
print("filtered_count", len(filtered_merged))

# 🎯 Metrikleri hesapla
mae = mean_absolute_error(filtered_merged['Actual'], filtered_merged['Forecast'])
rmse = np.sqrt(mean_squared_error(filtered_merged['Actual'], filtered_merged['Forecast']))
mape = mean_absolute_percentage_error(filtered_merged['Actual'], filtered_merged['Forecast']) * 100
smape = 100 * np.mean(2 * np.abs(filtered_merged['Forecast'] - filtered_merged['Actual']) / 
                      (np.abs(filtered_merged['Forecast']) + np.abs(filtered_merged['Actual'])))
wmape = 100 * np.sum(np.abs(filtered_merged['Forecast'] - filtered_merged['Actual'])) / np.sum(np.abs(filtered_merged['Actual']))

# Sonuçları yazdır
print(f"Gerçek değeri 0.1'den büyük olanlar için:\n"
      f"MAE   : {mae:.2f}\n"
      f"RMSE  : {rmse:.2f}\n"
      f"MAPE  : {mape:.2f}%\n"
      f"sMAPE : {smape:.2f}%\n"
      f"wMAPE : {wmape:.2f}%")



# %%
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error, r2_score
from statsmodels.tsa.statespace.sarimax import SARIMAX

# Tüm SpecGroupId'ler için gerçek verileri hazırla
actual_series_all = df[['Month', 'SpecGroupId', 'Sipariş Mik. (TON)']].groupby(['Month', 'SpecGroupId']).sum().sort_index()
actual_series_all.rename(columns={'Sipariş Mik. (TON)': 'Actual'}, inplace=True)

# Tüm SpecGroupId'ler için tahmin verilerini hazırla
forecast_series_all = disaggregated_df[['Month', 'SpecGroupId', 'Forecast_TON']].groupby(['Month', 'SpecGroupId']).sum().sort_index()
forecast_series_all.rename(columns={'Forecast_TON': 'Forecast'}, inplace=True)

# Verileri birleştir
merged_all = pd.concat([actual_series_all, forecast_series_all], axis=1).dropna()

# Gerçek değeri 0.1'den yüksek olanları filtrele
filtered_merged = merged_all[merged_all['Actual'] > 0.1]

print("total_count", len(merged_all))
print("filtered_count", len(filtered_merged))

# SARIMAX Modelini çalıştır
model = SARIMAX(filtered_merged['Actual'], order=(1,0,0))
result = model.fit()

# R² Hesapla
predictions = result.fittedvalues
r2 = r2_score(filtered_merged['Actual'], predictions)

# Parametrelerin anlamlılık tablosunu hazırla
params_summary = pd.DataFrame({
    'Coefficient': result.params,
    'Std_Error': result.bse,
    'p-value': result.pvalues,
    'Significant': result.pvalues < 0.05
})

# Sonuçları yazdır
print(f"R²: {r2:.4f}")
print("\nParametrelerin Anlamlılık Tablosu:\n", params_summary)

# %%
import pandas as pd

# Gerçek verileri hazırla
actual_series_all = df[['Month', 'SpecGroupId', 'GradeGroup', 'Sipariş Mik. (TON)']]\
    .groupby(['Month', 'SpecGroupId', 'GradeGroup'])\
    .sum().reset_index()

actual_series_all.rename(columns={'Sipariş Mik. (TON)': 'Actual'}, inplace=True)

# Tahmin verilerini hazırla
forecast_series_all = disaggregated_df[['Month', 'SpecGroupId', 'Forecast_TON']]\
    .groupby(['Month', 'SpecGroupId'])\
    .sum().reset_index()

forecast_series_all.rename(columns={'Forecast_TON': 'Forecast'}, inplace=True)

# Gerçek ve Tahmin verilerini birleştir
merged_all = pd.merge(actual_series_all, forecast_series_all, 
                      on=['Month', 'SpecGroupId'], 
                      how='left').dropna()

# Sonucu Excel'e kaydet
#merged_all.to_excel('actual_forecast_with_grade_month_specgroup.xlsx', index=False)



# %%


# %%


# %%


# %%


# %%


# %%


# %%


# %%



