import os
import pandas as pd
import datetime
import itertools

def getSpecDF():
    specDF = pd.read_csv("mmkBelgeler/KU002 Mamul SPEC Bilgileri - Tam.csv", encoding="ISO-8859-1", delimiter=";", dtype={"LevhaBoyu": str})
    specDF["Genislik"] = specDF["Genislik"].astype(str).str.replace(",", ".").astype(float)
    specDF["LevhaBoyu"] = specDF["Genislik"].astype(str).str.replace(",", ".").astype(float)
    return specDF

def getConcatOrdersDF():
    finalOrdersDF = pd.DataFrame()
    for file in os.listdir("mmkBelgeler/siparisler"):
        orders_df = pd.read_excel(os.path.join("mmkBelgeler/siparisler",file), header=0)
        orders_df["Teslimat tarihi"] = pd.to_datetime(orders_df["Teslimat tarihi"], errors='coerce')
        finalOrdersDF = pd.concat([finalOrdersDF, orders_df])
    return finalOrdersDF

def getSiparisBySpec(lastXyear = 8, finalOrdersDF = getConcatOrdersDF()):
    finalOrdersDF = finalOrdersDF[finalOrdersDF["Teslimat tarihi"].dt.year >= 2025 - lastXyear]
    resultDF = finalOrdersDF.groupby(["Müşteri malzeme numarası"])["Sipariş Mik. (TON)"].sum().reset_index()
    resultDF.rename(columns={"Müşteri malzeme numarası": "SPEC", "Sipariş Mik. (TON)": f"Son {lastXyear} yıl Sipariş Mik. (TON) Toplam"}, inplace=True)
    return resultDF

def getSpecGroups(siparisAltLimit = 0, lastXyear = 8):
    specDF = getSpecDF()
    specDF["Genislik_Grouped"] = specDF["Genislik"].apply(lambda x: "0-800" if x < 800 else str(x)) #Bu simdilik kesin bi kabul
    specDF['SpecGroupId'] = specDF.groupby(['Kalinlik', 'Genislik_Grouped', 'Grade']).ngroup() + 1
    lastXyearSiparisDF = getSiparisBySpec(lastXyear)
    mergedDF = specDF.merge(lastXyearSiparisDF, left_on="SPEC", right_on="SPEC", how="left")
    mergedDF[f"Son {lastXyear} yıl Sipariş Mik. (TON) Toplam"] = mergedDF[f"Son {lastXyear} yıl Sipariş Mik. (TON) Toplam"].fillna(0)
    sumDF = mergedDF.groupby(["SpecGroupId"])[f"Son {lastXyear} yıl Sipariş Mik. (TON) Toplam"].sum().reset_index()
    sumDF = sumDF[sumDF[f"Son {lastXyear} yıl Sipariş Mik. (TON) Toplam"] > siparisAltLimit]
    specDF = mergedDF[mergedDF["SpecGroupId"].isin(sumDF["SpecGroupId"])]
    specDF = specDF.copy()
    specDF['SpecGroupId'] = specDF.groupby(['Kalinlik', 'Genislik_Grouped', 'Grade']).ngroup() + 1
    specDF = specDF[["SPEC", "SpecGroupId", 'Kalinlik', 'Genislik_Grouped', 'Grade']]
    specDF = specDF.sort_values(by='SpecGroupId')
    return specDF

def getForecastData(siparisAltLimit = 0, lastXyear = 8, groupByGrade = False, finalOrdersDF = getConcatOrdersDF()):
    specGroupsDF = getSpecGroups(siparisAltLimit, lastXyear) 

    finalOrdersDF["Teslimat tarihi"] = pd.to_datetime(finalOrdersDF["Teslimat tarihi"], errors="coerce")
    finalOrdersDF["Month"] = finalOrdersDF["Teslimat tarihi"].dt.strftime("%m.%Y")

    mergedDF = finalOrdersDF.merge(specGroupsDF, left_on="Müşteri malzeme numarası", right_on="SPEC", how="left")
    mergedDF["SpecGroupId"] = mergedDF["SpecGroupId"].fillna(0)

    """mergedDF["Month"] = pd.to_datetime(mergedDF["Month"], format="%m.%Y")
    minMonth = mergedDF["Month"].min()
    maxMonth = mergedDF["Month"].max()
    months = pd.date_range(start=minMonth, end=maxMonth, freq="MS").strftime("%m.%Y")"""


    if not groupByGrade:
        resultDF = mergedDF.groupby(["Month", "SpecGroupId", "Grade"])["Sipariş Mik. (TON)"].sum().reset_index()
        """
        unique_spec_groups = resultDF["SpecGroupId"].unique()
        full_index = pd.MultiIndex.from_product([months, unique_spec_groups], names=["Month", "SpecGroupId"])
        df_full = resultDF.set_index(["Month", "SpecGroupId"]).reindex(full_index, fill_value=0).reset_index()
        """


    else:
        resultDF = mergedDF.groupby(["Month", "Grade"])["Sipariş Mik. (TON)"].sum().reset_index()
        """
        unique_grades = resultDF["Grade"].unique()
        full_index = pd.MultiIndex.from_product([months, unique_grades], names=["Month", "Grade"])
        df_full = resultDF.set_index(["Month", "Grade"]).reindex(full_index, fill_value=0).reset_index()
        """
    
    return resultDF
"""
start = datetime.datetime.now()
finalOrdersDF = getConcatOrdersDF()

now = datetime.datetime.now()
print(now - start)
start = now

siparisBySpecDF = getSiparisBySpec(3, finalOrdersDF)
siparisBySpecFile = "preprocessedBelgeler/preprocessedDemandBySpecTamSon3.xlsx"
siparisBySpecDF.to_excel(siparisBySpecFile, index=False)

specGroups0DF = getSpecGroups(0, 3)
specGroups0File = "preprocessedBelgeler/specGroupsTam_last3_altLimit0.xlsx"
specGroups0DF.to_excel(specGroups0File, index=False)

specGroups100DF = getSpecGroups(100, 3)
specGroups100File = "preprocessedBelgeler/specGroupsTam_last3_altLimit100.xlsx"
specGroups100DF.to_excel(specGroups100File, index=False)

forecastData0DF = getForecastData(0, 3)
forecastData0File = "preprocessedBelgeler/forecastData_altLimit0_son3_byGrup.xlsx"
forecastData0DF.to_excel(forecastData0File, index=False)

now = datetime.datetime.now()
print(now - start)
start = now
forecastData100DF = getForecastData(100, 3, False, finalOrdersDF)
forecastData100File = "preprocessedBelgeler/forecastData_altLimit100_son3_byGrup.xlsx"
forecastData100DF.to_excel(forecastData100File, index=False)

now = datetime.datetime.now()
print(now - start)
start = now

forecastData100_3_gradeDF = getForecastData(100, 3, True, finalOrdersDF)
forecastData100_3_gradeFile = "preprocessedBelgeler/forecastData_altLimit100_son3_byGrade.xlsx"
forecastData100_3_gradeDF.to_excel(forecastData100_3_gradeFile, index=False)

now = datetime.datetime.now()
print(now - start)
start = now"""