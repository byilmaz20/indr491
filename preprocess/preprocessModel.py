import pandas as pd

specGroupsDF = pd.read_excel("preprocessedBelgeler/NEWspecGroupsTam_last3_altLimit100.xlsx")

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
            if row["Bileşen Grade"] in dictGrade[g] and row["Malzeme Grade"] not in dictGrade[g]:
                dictGrade[g].append(row["Malzeme Grade"])
                matched = True

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


#print(grade_j, kalinlik_j, genislik_j)
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
                    
            
"""
for row in gecmisEslemelerDF.iterrows():
    print(row)
    i = row["Malzeme"]
    j = row["SpecGroupId"]
    if i in setI and j in setJ:
        print("here")
        setIJ.add((i,j))"""

