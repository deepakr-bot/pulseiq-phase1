import subprocess, sys, os

subprocess.run([sys.executable, "load_to_duckdb.py"], cwd="05_Starter", check=True)
os.replace("05_Starter/pulseiq.duckdb", "pulseiq.duckdb")
subprocess.run([sys.executable, "etl.py"], check=True)