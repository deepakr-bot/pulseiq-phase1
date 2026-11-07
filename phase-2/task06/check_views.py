import duckdb, os
print("DB file:", os.path.abspath("pulseiq.duckdb"))
con = duckdb.connect("pulseiq.duckdb", read_only=True)
print(con.sql("""
    SELECT table_schema, table_name, table_type
    FROM information_schema.tables
    WHERE table_name ILIKE '%attend%' OR table_name ILIKE '%leave%'
       OR table_name ILIKE '%dim_date%' OR table_name ILIKE '%dim_depart%'
    ORDER BY 1, 2
""").df())