import duckdb, re, os

con = duckdb.connect("pulseiq.duckdb")
df = con.execute("SELECT * FROM raw.data_contracts").df()
df["table"] = df["feed"].str.extract(r"\((\w+)\)\s*$")

# 1) Contract notes for 3 tables (evidence for your report)
os.makedirs("reports", exist_ok=True)
with open("reports/contract_notes.md", "w", encoding="utf-8") as f:
    for t in ["fact_task", "fact_anomaly", "fact_attrition_risk"]:
        f.write(f"## {t}\n\n| column | type | can be empty? | allowed values / rule |\n|---|---|---|---|\n")
        for _, r in df[df["table"] == t].iterrows():
            f.write(f"| {r.column_name} | {r.data_type} | {'yes' if r.nullable else 'no'} | {r.rule_or_allowed_values} |\n")
        f.write("\n")
print("Wrote reports/contract_notes.md\n")

# 2) Which tables have contracts, and every distinct rule text
print("Tables with contracts:", sorted(df["table"].dropna().unique()), "\n")
print("Distinct data types:", sorted(df["data_type"].dropna().unique()), "\n")
print("Distinct rules:")
for r in sorted(df["rule_or_allowed_values"].dropna().unique()):
    print(" -", r)