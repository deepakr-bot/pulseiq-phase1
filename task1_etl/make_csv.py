import pandas as pd, os

os.makedirs("03_Data/csv", exist_ok=True)
sheets = pd.read_excel("03_Data/PulseIQ_Dataset.xlsx", sheet_name=None)
for name, df in sheets.items():
    print(name, len(df))
    df.to_csv(f"03_Data/csv/{name}.csv", index=False)