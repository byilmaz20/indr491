import os
import pandas as pd
import datetime

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

def getSiparisBySpec(lastXyear = 8):
    finalOrdersDF = getConcatOrdersDF()
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
    return specDF

def getForecastData(siparisAltLimit = 0, lastXyear = 8, groupByGrade = False):
    specGroupsDF = getSpecGroups(siparisAltLimit, lastXyear) 
    finalOrdersDF = getConcatOrdersDF()
    finalOrdersDF["Month"] = finalOrdersDF["Teslimat tarihi"].dt.strftime("%m.%Y")
    mergedDF = finalOrdersDF.merge(specGroupsDF, left_on="Müşteri malzeme numarası", right_on="SPEC", how="left")
    mergedDF["SpecGroupId"] = mergedDF["SpecGroupId"].fillna(0)

    if not groupByGrade:
        resultDF = mergedDF.groupby(["Month", "SpecGroupId", "Grade"])["Sipariş Mik. (TON)"].sum().reset_index()
    if groupByGrade:
        resultDF = resultDF.groupby(["Month", "Grade"])["Sipariş Mik. (TON)"].sum().reset_index()

    #if siparis doesn't exist for a month, it should be 0
    resultDF["Month"] = pd.to_datetime(resultDF["Month"], format="%m.%Y")
    startingMonth = resultDF["Month"].min()
    endingMonth = resultDF["Month"].max()
    allMonths = pd.date_range(start=startingMonth, end=endingMonth, freq='MS').strftime("%m.%Y")

    allMonthsDF = pd.DataFrame(allMonths, columns=["Month"])
    resultDF = allMonthsDF.merge(resultDF, on="Month", how="left")
    resultDF["Sipariş Mik. (TON)"] = resultDF["Sipariş Mik. (TON)"].fillna(0)
    return resultDF



"""siparisBySpecDF = getSiparisBySpec(3)
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
"""
forecastData100DF = getForecastData(100, 3)
forecastData100File = "preprocessedBelgeler/forecastData_altLimit100_son3_byGrup.xlsx"
forecastData100DF.to_excel(forecastData100File, index=False)

forecastData100_3_gradeDF = getForecastData(100, 3, True)
forecastData100_3_gradeFile = "preprocessedBelgeler/forecastData_altLimit100_son3_byGrade.xlsx"
forecastData100_3_gradeDF.to_excel(forecastData100_3_gradeFile, index=False)
