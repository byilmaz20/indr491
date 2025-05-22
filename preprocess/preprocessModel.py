import pandas as pd

def preprocessModel():
    specGroupsDF = pd.read_excel("preprocessedBelgeler/NEWspecGroupsTam_last3_altLimit100.xlsx")
    orders_df = pd.read_excel("preprocessedBelgeler/NewpreprocessedFinalOrders2025.xlsx")

    list= ["31 HR",	"31 PHR",	"31 CRF",	"31 GCR",	"31 GHR",	"31 PPG",	"41 HR",	"41 PHR",	"41 CRF",	"41 GCR",	"41 GHR",	"41 PPG"]
    orders_df["Açık Mik.(TON)"] = orders_df["Açık Mik.(TON)"] - sum(orders_df[i] for i in list) / 1000

    gecmisEslemelerDF = pd.read_excel("mmkBelgeler/KU004 Sipariş bazında eşlenen HR tarihçesi.xlsx")
    gecmisEslemelerDF = gecmisEslemelerDF.merge(specGroupsDF, left_on="Müşteri malzeme numarası", right_on="SPEC", how="left")
    gecmisEslemelerDF.rename(columns={"Müşteri malzeme numarası" : "SPEC"}, inplace=True)
    gecmisEslemelerDF = gecmisEslemelerDF[["Malzeme", "SpecGroupId"]].drop_duplicates()

    specGroupsDF = specGroupsDF[["SpecGroupId",	"Kalinlik",	"Genislik",	"Genislik_Grouped",	"Grade"]].drop_duplicates().set_index("SpecGroupId")

    hammaddeDF = pd.read_excel("mmkBelgeler/KU005 Hammadde listesi.xlsx")
    hammaddeDF = hammaddeDF[["Malzeme", "Kalınlık",	"Genişlik",	"Grade", "Stok Kg"]][hammaddeDF["Stok Kg"] > 0].set_index("Malzeme")

    kesmePayiDF = pd.read_excel("mmkBelgeler/KU008 CPL Kenar Kesme payları.xlsx")
    kesmePayiDF["HR Min Kalınlık"] = pd.to_numeric(kesmePayiDF["HR Min Kalınlık"], errors="coerce")
    kesmePayiDF["HR Max Kalınlık"] = pd.to_numeric(kesmePayiDF["HR Max Kalınlık"], errors="coerce")

    ezmeTablosuDF = pd.read_excel("mmkBelgeler/KU009 CRM ezme tablosu.xlsx")

    setI = set(hammaddeDF.index.unique())
    setJ = set(specGroupsDF.index.unique())
    setU = set([1, 2, 3])

    H_i = {i:hammaddeDF.loc[i, "Stok Kg"] / 1000 for i in setI}

    gecmisEslemelerDF = gecmisEslemelerDF[gecmisEslemelerDF["Malzeme"].isin(setI) & gecmisEslemelerDF["SpecGroupId"].isin(setJ)]

    gradeMatchingDF = pd.read_excel("mmkBelgeler/KU010 Grade Eşlemesi.xlsx")

    setGrade = specGroupsDF["Grade"].unique()

    dictGrade = {g:[g] for g in setGrade}

    matched = True
    while matched:
        matched = False
        for i, row in gradeMatchingDF.iterrows():
            if row["Malzeme Grade"] in setGrade and row["Bileşen Grade"] not in dictGrade[row["Malzeme Grade"]]:
                dictGrade[row["Malzeme Grade"]].append(row["Bileşen Grade"])
                matched = True
            for g in dictGrade:
                if row["Malzeme Grade"] in dictGrade[g] and row["Bileşen Grade"] not in dictGrade[g]:
                    dictGrade[g].append(row["Bileşen Grade"])
                    matched = True
                    
    for g in setGrade:
        print(f"{g}: {dictGrade[g]}")

    grade_i = {i:hammaddeDF.loc[i, "Grade"] for i in setI}
    grade_j = {j:specGroupsDF.loc[j, "Grade"] for j in setJ}
    kalinlik_i = {i:float(hammaddeDF.loc[i, "Kalınlık"]) for i in setI}
    kalinlik_j = {j:float(specGroupsDF.loc[j, "Kalinlik"].replace(",",".")) for j in setJ}
    genislik_i = {i:float(hammaddeDF.loc[i, "Genişlik"]) for i in setI}
    genislik_j = {j:float(specGroupsDF.loc[j, "Genislik_Grouped"]) for j in setJ}

    kesmePayi_i = {}

    for i in setI:
        grade = grade_i[i]
        kalinlik = kalinlik_i[i]

        matched_rows = kesmePayiDF[
            (kesmePayiDF["Grade"] == grade) &
            (kesmePayiDF["HR Min Kalınlık"] <= kalinlik) &
            (kesmePayiDF["HR Max Kalınlık"] >= kalinlik)
        ]

        if not matched_rows.empty:
            # If multiple matches, pick the first (or you can define logic to choose)
            kesmePayi_i[i] = matched_rows.iloc[0]["Kenar Kesme Payı mm"]
            #print(f"Match found for {i} with grade {grade} and kalinlik {kalinlik}: {kesmePayi_i[i]}")
        else:
            #print(f"No match found for {i} with grade {grade} and kalinlik {kalinlik}")
            kesmePayi_i[i] = None  # or np.nan / 0


    setIJ = set()
    for i in setI:
        gradeI = grade_i[i]
        kalinlikI = kalinlik_i[i]
        genislikI = genislik_i[i]
        for j in setJ:
            gradeJ = grade_j[j]
            kalinlikJ = kalinlik_j[j]
            genislikJ = genislik_j[j]
            #print(gradeI, gradeJ)
            #print(kalinlikI, kalinlikJ)
            #print(genislikI, genislikJ)
            if gradeI == gradeJ and kalinlikI == kalinlikJ and genislikI == genislikJ:
                    setIJ.add((i,j))
                    #print("Same")

            elif gradeI in dictGrade[gradeJ]:
                #Kalinlik check
                #if genislik_i == genislik_j: #TODO!!! buraya KU008 eklenecek
                if True:
                    matched_rows = ezmeTablosuDF[
                        (ezmeTablosuDF["HR_Grade"] == gradeI) &
                        (ezmeTablosuDF["Mamul_Gns_Min"] <= genislikJ) &
                        (ezmeTablosuDF["Mamul_Gns_Max"] >= genislikJ) &
                        (ezmeTablosuDF["Mamul_Kln_Min"] <= kalinlikJ) &
                        (ezmeTablosuDF["Mamul_Kln_Max"] >= kalinlikJ) &
                        (ezmeTablosuDF["Giris_Kalinlik"] == kalinlikI)
                    ]

                    if not matched_rows.empty:
                        setIJ.add((i,j))
                        #print(f"✔ Match Found for i={i} and j={j}")
                        
                

    for index, row in gecmisEslemelerDF.iterrows():
        i = row["Malzeme"]
        j = row["SpecGroupId"]
        if i in setI and j in setJ:
            setIJ.add((i,j))


    orders_df["Yaratma tarihi"] = pd.to_datetime(orders_df["Yaratma tarihi"], errors="coerce")
    orders_df["Teslimat tarihi"] = pd.to_datetime(orders_df["Teslimat tarihi"], errors="coerce")
    referans_tarih = pd.to_datetime("2025-03-01")

    # filter orders by date
    orders_df = orders_df[(referans_tarih >= orders_df["Yaratma tarihi"]) & (orders_df["Teslimat tarihi"] >= referans_tarih)]
    spec_to_group = pd.read_excel("preprocessedBelgeler/NEWspecGroupsTam_last3_altLimit100.xlsx")[["SPEC", "SpecGroupId"]]

    # dju is a dataframe first column j second u third dju 
    dju = {}
    for j in setJ:
        for u in setU:
            dju[(j,u)] = 0

    # read excel /Users/ceylin/Desktop/indr491/indr491/results/SARIMAX_forecast.xlsx
    forecast_df = pd.read_excel("results/SARIMAX_forecast.xlsx")

    for j in setJ:
        specs = spec_to_group[spec_to_group["SpecGroupId"] == j]["SPEC"].unique()
        orders = orders_df[orders_df["Müşteri malzeme numarası"].isin(specs)]
        high_urgency_orders = orders[orders["Öncelik Tanımı"] == 'Acil sipariş kalemi']
        normal_orders = orders[
            (orders["Öncelik Tanımı"] == 'Normal öncellikli sipariş kalemi') |
            (orders["Öncelik Tanımı"] == 'Termininden önce üretilmesin')
        ]        
        d1 = high_urgency_orders["Açık Mik.(TON)"].sum()
        d2 = normal_orders["Açık Mik.(TON)"].sum()
        d3 = forecast_df[forecast_df["SpecGroupId"] == j]["Forecast_TON"].sum()
        dju[(j, 1)] = d1 if d1 > 10 ** -3 else 0
        dju[(j, 2)] = d2 if d2 > 10 ** -3 else 0
        dju[(j, 3)] = d3 if d3 > 10 ** -3 else 0

    #dju should be a dataframe
    """dju_df = pd.DataFrame(
        [(j, u, val) for (j, u), val in dju.items()],
        columns=["SpecGroupId", "Urgency", "Siparis_TON"]
    )
    dju_df.to_excel("preprocessedBelgeler/dju_df.xlsx", index=False)"""
    
    #print("dju_df: ", dju_df.head())

    """#log these to a txt
    with open("preprocessedBelgeler/setIJ.txt", "w") as f:
        for j in setJ:
            if sum(dju[(j,u)] for u in [1,2]) > 0:
                f.write(f"SpecGroupId: {j} ({genislik_j[j]}x{kalinlik_j[j]}x{grade_j[j]}) Demand: {dju[(j, 1)]} {dju[(j, 2)]} {dju[(j, 3)]}\n")
                for i in setI:
                    if H_i[i] > 0 and (i,j) in setIJ:
                        f.write(f"Hammadde: ({genislik_i[i]}x{kalinlik_i[i]}x{grade_i[i]}) Stok: {H_i[i]} \n")
    """

    

    """for j in setJ:
        if sum(dju[(j,u)] for u in setU) > 0:
            print(f"SpecGroupId: {j} ({genislik_j[j]}x{kalinlik_j[j]}x{grade_j[j]}) Demand: {dju[(j, 1)]} {dju[(j, 2)]} {dju[(j, 3)]}")
            for i in setI:
                if H_i[i] > 0 and (i,j) in setIJ:
                    print(f"Hammadde: ({genislik_i[i]}x{kalinlik_i[i]}x{grade_i[i]}) Stok: {H_i[i]} ")
    """
    dictTanimI = {i: f"({genislik_i[i]}x{kalinlik_i[i]}x{grade_i[i]})" for i in setI}
    dictTanimJ = {j: f"({genislik_j[j]}x{kalinlik_j[j]}x{grade_j[j]})" for j in setJ}
    return setI, setJ, setU, setIJ, H_i, dju, dictTanimI, dictTanimJ



setI, setJ, setU, setIJ, H_i, dju, dictTanimI, dictTanimJ = preprocessModel()

"""
#to pickle
import pickle
with open("preprocessedBelgeler/preprocessedModel.pkl", "wb") as f:
    pickle.dump((setI, setJ, setU, setIJ, H_i, dju), f)
"""

"""
#to read from pickle
with open("preprocessedBelgeler/preprocessedModel.pkl", "rb") as f:
    setI, setJ, setU, setIJ, H_i, dju = pickle.load(f)
    print(setI, setJ, setU, setIJ, H_i, dju)
"""