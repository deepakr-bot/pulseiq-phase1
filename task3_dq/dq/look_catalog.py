import duckdb
con = duckdb.connect("pulseiq.duckdb")
df = con.sql("""SELECT table_schema AS s, table_name AS t, string_agg(column_name, ', ') AS cols
FROM information_schema.columns
WHERE table_schema IN ('dw','clean','main')
GROUP BY 1,2 ORDER BY 1,2""").df()
open("dq/tables.txt", "w").write(df.to_string())
print(df.to_string())