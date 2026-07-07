from parsers import DKB

df1 = DKB.load("../data/07-07-2026_Umsatzliste_Girokonto_DE60120300001200204400 (3).csv")
print(df1.head())