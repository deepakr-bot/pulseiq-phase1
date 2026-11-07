import duckdb
con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("\nTables and views about payroll")
print(con.sql("""SELECT table_schema, table_name, table_type FROM information_schema.tables
    WHERE table_name ILIKE '%payroll%' OR table_name ILIKE '%dim_department%'
       OR table_name IN ('m07_gross_pay','m08_net_pay','m09_payroll_cost','m10_cost_per_head')
    ORDER BY 1, 2""").df().to_string())

print("\n== dw.fact_payroll")
print(con.sql("SELECT COUNT(*) AS rows FROM dw.fact_payroll").df().to_string(index=False))
print(con.sql("DESCRIBE dw.fact_payroll").df()[["column_name", "column_type"]].to_string(index=False))

for v in ["m07_gross_pay", "m08_net_pay", "m09_payroll_cost", "m10_cost_per_head"]:
    print("\n==", v)
    print(con.sql(f"SELECT * FROM main.{v} LIMIT 4").df().to_string())