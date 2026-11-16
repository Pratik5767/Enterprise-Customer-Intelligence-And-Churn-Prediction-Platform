import pandas as pd



df = pd.read_csv("data/raw/telco_churn.csv", dtype=str)

df.loc[0, "tenure"] = "-5"                                          # impossible tenure
df.loc[1, "MonthlyCharges"] = "abc"                                 # wrong data type
df.loc[2, "Contract"] = "Weekly"                                    # invalid category
df.loc[3, "customerID"] = None                                      # missing ID
df.loc[4, ["InternetService", "OnlineSecurity"]] = ["No", "Yes"]    # inconsistent services

df = pd.concat([df, df.iloc[[10]]])                                 # duplicate record
df.to_csv("data/raw/telco_dirty.csv", index=False)

