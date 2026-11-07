import duckdb
con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("\nTables and views about headcount, attrition, employees")
print(con.sql("""
    SELECT table_schema, table_name, table_type
    FROM information_schema.tables
    WHERE table_name ILIKE '%headcount%' OR table_name ILIKE '%attrition%'
       OR table_name ILIKE '%dim_employee%' OR table_name ILIKE '%exit%'
       OR table_name ILIKE 'm%attrition%' OR table_name ILIKE '%separation%'
    ORDER BY 1, 2""").df().to_string())

print("\nAll metric views in main")
print(con.sql("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'main' AND table_type = 'VIEW' ORDER BY 1""").df().to_string())

for t in ["dw.fact_headcount_monthly", "dw.fact_attrition_risk",
          "clean.fact_attrition_risk", "raw.fact_attrition_risk", "dw.dim_employee"]:
    try:
        print("\n==", t)
        print(con.sql(f"DESCRIBE {t}").df()[["column_name", "column_type"]].to_string(index=False))
        print(con.sql(f"SELECT * FROM {t} LIMIT 3").df().to_string())
    except Exception:
        print("not found")