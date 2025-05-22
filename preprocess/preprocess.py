import math
import os
import pandas as pd
import datetime
import itertools



def getSpecDF():
    specDF = pd.read_csv("mmkBelgeler/KU002 Mamul SPEC Bilgileri - Tam.csv", encoding="ISO-8859-1", delimiter=";", dtype={"LevhaBoyu": str})
    specDF["Genislik"] = specDF["Genislik"].astype(str).str.replace(",", ".").astype(float)
    specDF["LevhaBoyu"] = specDF["Genislik"].astype(str).str.replace(",", ".").astype(float)
    specDF["SPEC"] = specDF["SPEC"].astype(int)
    return specDF

def getConcatOrdersDF():
    finalOrdersDF = pd.DataFrame()
    for file in os.listdir("mmkBelgeler/siparisler"):
        orders_df = pd.read_excel(os.path.join("mmkBelgeler/siparisler",file), header=0, engine='openpyxl')
        orders_df["Yaratma tarihi"] = pd.to_datetime(orders_df["Yaratma tarihi"], errors='coerce')
        finalOrdersDF = pd.concat([finalOrdersDF, orders_df])
    print(f"Final Orders DF shape: {finalOrdersDF.shape}")
    print(finalOrdersDF.head())
    finalOrdersDF = finalOrdersDF[finalOrdersDF["Müşteri malzeme numarası"].notna()]
    print(finalOrdersDF.head())

    finalOrdersDF["Müşteri malzeme numarası"] = finalOrdersDF["Müşteri malzeme numarası"].astype(int)
    print(finalOrdersDF.head())

    return finalOrdersDF

def getSiparisBySpec(lastXyear = 3, finalOrdersDF = getConcatOrdersDF()):
    finalOrdersDF = finalOrdersDF[finalOrdersDF["Yaratma tarihi"].dt.year >= 2025 - lastXyear]
    resultDF = finalOrdersDF.groupby(["Müşteri malzeme numarası"])["Sipariş Mik. (TON)"].sum().reset_index()
    resultDF.rename(columns={"Müşteri malzeme numarası": "SPEC", "Sipariş Mik. (TON)": f"Son {lastXyear} yıl Sipariş Mik. (TON) Toplam"}, inplace=True)
    #add genislik grade kalınlık from specDF
    specDF = getSpecDF()
    resultDF = resultDF.merge(specDF, left_on="SPEC", right_on="SPEC", how="left")
    resultDF = resultDF[["SPEC", f"Son {lastXyear} yıl Sipariş Mik. (TON) Toplam", "Kalinlik", "Genislik", "Grade"]]
    resultDF = resultDF[resultDF[f"Son {lastXyear} yıl Sipariş Mik. (TON) Toplam"] > 10]
    resultDF["SPEC"] = resultDF["SPEC"].astype(int)
    return resultDF

def assign_genislik_group(row):
    genislik = row['Genislik']
    planlanan = row['Planlanan']

    if genislik >= 800:
        return genislik
    elif planlanan >= 800:
        return planlanan
    else:
        # Find the first multiple of genislik that is >= 800
        if genislik == 0:
            return 800  # avoid division by zero
        multiple = ((800 + genislik - 1) // genislik) * genislik
        #print(f'Matched multiple: {multiple} (genislik: {genislik}, planlanan: {planlanan})')
        return multiple

def getSpecGroups(planlanan, siparisAltLimit = 100, lastXyear = 8):
    specDF = getSpecDF()
    specDF["Genislik"] = specDF["Genislik"].astype(str).str.replace(",", ".").astype(float)
    #specDF.to_excel("preprocessedBelgeler/DENEMEspecDF.xlsx", index=False)

    planlananDF = pd.DataFrame(list(planlanan.items()), columns=["SPEC", "Planlanan"])
    planlananDF["Planlanan"] = planlananDF["Planlanan"].astype(int)
    #planlananDF.to_excel("preprocessedBelgeler/DENEMEplanlananDF.xlsx", index=False)

    specDF = specDF.merge(planlananDF, left_on="SPEC", right_on="SPEC", how="left")
    #.fillna(0)
    specDF["Planlanan"] = specDF["Planlanan"].fillna(0)
    #fill genislik group with genişlik if >=800, else use planlanan if planlanan >=800 else use first multiply of genişlik that is >=800
    specDF["Genislik_Grouped"] = specDF.apply(assign_genislik_group, axis=1)
    specDF['SpecGroupId'] = specDF.groupby(['Kalinlik', 'Genislik_Grouped', 'Grade']).ngroup() + 1
    lastXyearSiparisDF = getSiparisBySpec(lastXyear)
    
    mergedDF = specDF.merge(lastXyearSiparisDF, left_on="SPEC", right_on="SPEC", how="left")
    mergedDF[f"Son {lastXyear} yıl Sipariş Mik. (TON) Toplam"] = mergedDF[f"Son {lastXyear} yıl Sipariş Mik. (TON) Toplam"].fillna(0)
    sumDF = mergedDF.groupby(["SpecGroupId"])[f"Son {lastXyear} yıl Sipariş Mik. (TON) Toplam"].sum().reset_index()

    
    sumDF = sumDF[sumDF[f"Son {lastXyear} yıl Sipariş Mik. (TON) Toplam"] > siparisAltLimit]
    filteredGroupIds = sumDF["SpecGroupId"].unique()
    cleanSpecDF = specDF[specDF["SpecGroupId"].isin(filteredGroupIds)].copy()
    cleanSpecDF['SpecGroupId'] = cleanSpecDF.groupby(['Kalinlik', 'Genislik_Grouped', 'Grade']).ngroup() + 1

    specDF = cleanSpecDF[["SPEC", "SpecGroupId", "Kalinlik", "Genislik", "Genislik_Grouped", "Grade"]].sort_values("SpecGroupId")
    gradeGroupsDF = pd.read_excel("mmkBelgeler/KU015 Grade Grupları.xlsx", index_col=0)
    grade_map = gradeGroupsDF["Grup"].to_dict()
    #print(grade_map)
    specDF["GradeGroup"] = specDF["Grade"].apply(lambda g: grade_map.get(g, g))   
     
    return specDF


def getForecastData(planlanan, siparisAltLimit = 0, lastXyear = 8, finalOrdersDF = getConcatOrdersDF()):
    # print sizes of dataframes


    specGroupsDF = getSpecGroups(planlanan, siparisAltLimit, lastXyear) 
    finalOrdersDF["Yaratma tarihi"] = pd.to_datetime(finalOrdersDF["Yaratma tarihi"], errors="coerce")
    finalOrdersDF["Month"] = finalOrdersDF["Yaratma tarihi"].dt.strftime("%m.%Y")


    mergedDF = finalOrdersDF.merge(specGroupsDF, left_on="Müşteri malzeme numarası", right_on="SPEC", how="left")
    mergedDF["SpecGroupId"] = mergedDF["SpecGroupId"].fillna(0)

    resultDF = mergedDF.groupby(["Month", "SpecGroupId", "Grade"])["Sipariş Mik. (TON)"].sum().reset_index()
    

    #Zero filling
    resultDF["Month"] = pd.to_datetime(resultDF["Month"], format="%m.%Y")

    all_months = pd.date_range(start=resultDF["Month"].min(), end=resultDF["Month"].max(), freq='MS')
    new_rows = []

    for uid in resultDF["SpecGroupId"].unique():
        existing_months = resultDF[resultDF["SpecGroupId"] == uid]["Month"].unique()
        missing_months = [m for m in all_months if m not in existing_months]
        grade = resultDF.loc[resultDF["SpecGroupId"] == uid, "Grade"].unique()[0]
        for month in missing_months:
            new_rows.append({"SpecGroupId": uid, "Month": month,"Grade": grade ,"Sipariş Mik. (TON)": 0})  

    resultDF = pd.concat([resultDF, pd.DataFrame(new_rows)], ignore_index=True)
    gradeGroupsDF = pd.read_excel("mmkBelgeler/KU015 Grade Grupları.xlsx", index_col=0)
    grade_map = gradeGroupsDF["Grup"].to_dict()
    #print(grade_map)
    resultDF["GradeGroup"] = resultDF["Grade"].apply(lambda g: grade_map.get(g, g))
    
    return resultDF


def getPlanlanan(finalOrdersDF):
    filtered_df = finalOrdersDF[["Müşteri malzeme numarası", "PlnHmdde Gnşlk"]].dropna()
    filtered_df["PlnHmdde Gnşlk"] = pd.to_numeric(filtered_df["PlnHmdde Gnşlk"], errors="coerce")
    filtered_df = filtered_df[filtered_df["PlnHmdde Gnşlk"] > 0]
    min_valid = filtered_df.groupby("Müşteri malzeme numarası")["PlnHmdde Gnşlk"].min().reset_index()
    planlanan = dict(zip(min_valid["Müşteri malzeme numarası"], min_valid["PlnHmdde Gnşlk"]))
    return(planlanan)





finalOrdersDF = getConcatOrdersDF() # get all orders
# save to excel
finalOrdersFile = "preprocessedBelgeler/NewpreprocessedFinalOrders.xlsx"
#finalOrdersDF.to_excel(finalOrdersFile, index=False)
siparisBySpecDF = getSiparisBySpec(3, finalOrdersDF)
siparisBySpecFile = "preprocessedBelgeler/NewpreprocessedDemandBySpecTamSon3.xlsx"
siparisBySpecDF.to_excel(siparisBySpecFile, index=False)

planlanan = getPlanlanan(finalOrdersDF)
# save to excel
planlananFile = "preprocessedBelgeler/NewpreprocessedPlanlanan.xlsx"
planlananDF = pd.DataFrame(list(planlanan.items()), columns=["SPEC", "Planlanan"])
planlananDF["Planlanan"] = planlananDF["Planlanan"].astype(int)

planlananDF.to_excel(planlananFile, index=False)

specGroups100DF = getSpecGroups(planlanan, 100, 3)
specGroups100File = "preprocessedBelgeler/NEWspecGroupsTam_last3_altLimit100.xlsx"
specGroups100DF.to_excel(specGroups100File, index=False)

forecastData100DF = getForecastData(planlanan, 100, 3, finalOrdersDF)
forecastData100File = "preprocessedBelgeler/NewforecastData_altLimit100_son3_byGrup.xlsx"
forecastData100DF.to_excel(forecastData100File, index=False)
print("done")