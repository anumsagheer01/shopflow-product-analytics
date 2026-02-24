import pandas as pd
import snowflake.connector
import os
from dotenv import load_dotenv
load_dotenv()

conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    warehouse="SHOPFLOW_WH",
    database="SHOPFLOW_DB",
    schema="ANALYTICS"
)

print("Exporting...")
pd.read_sql("SELECT * FROM ANALYTICS.MONTHLY_KPIS", conn).to_csv("data/processed/monthly_kpis.csv", index=False)
pd.read_sql("SELECT * FROM ANALYTICS.DIM_CUSTOMERS", conn).to_csv("data/processed/dim_customers.csv", index=False)
pd.read_sql("SELECT * FROM ANALYTICS.FACT_ORDER_ITEMS LIMIT 50000", conn).to_csv("data/processed/fact_order_items.csv", index=False)
conn.close()
print("Done!")