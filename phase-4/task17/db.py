import os
import duckdb

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pulseiq.duckdb")

def q(sql):
    con = duckdb.connect(DB, read_only=True)
    try:
        return con.sql(sql).df()
    finally:
        con.close()