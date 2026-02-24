import snowflake.connector
import os
from dotenv import load_dotenv

load_dotenv()

# ── Connection ──────────────────────────────────────────────
conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    warehouse="SHOPFLOW_WH",
    database="SHOPFLOW_DB",
    schema="RAW"
)

cursor = conn.cursor()

# ── File to Table mapping ────────────────────────────────────
tables = {
    "ORDERS":              "olist_orders_dataset.csv",
    "ORDER_ITEMS":         "olist_order_items_dataset.csv",
    "ORDER_PAYMENTS":      "olist_order_payments_dataset.csv",
    "ORDER_REVIEWS":       "olist_order_reviews_dataset.csv",
    "CUSTOMERS":           "olist_customers_dataset.csv",
    "PRODUCTS":            "olist_products_dataset.csv",
    "SELLERS":             "olist_sellers_dataset.csv",
    "GEOLOCATION":         "olist_geolocation_dataset.csv",
    "CATEGORY_TRANSLATION":"product_category_name_translation.csv"
}

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw")

# ── Stage + Load each file ──────────────────────────────────
for table, filename in tables.items():
    filepath = os.path.abspath(os.path.join(DATA_PATH, filename))
    filepath_escaped = filepath.replace("\\", "/")  # Snowflake needs forward slashes

    print(f"Loading {filename} → RAW.{table}...")

    # Create a named file format
    cursor.execute("""
        CREATE OR REPLACE FILE FORMAT shopflow_csv_format
            TYPE = 'CSV'
            FIELD_OPTIONALLY_ENCLOSED_BY = '"'
            SKIP_HEADER = 1
            NULL_IF = ('NULL', 'null', '')
            EMPTY_FIELD_AS_NULL = TRUE;
    """)

    # Create internal stage
    cursor.execute(f"CREATE OR REPLACE STAGE {table}_stage FILE_FORMAT = shopflow_csv_format;")

    # Upload file to stage
    cursor.execute(f"PUT file://{filepath_escaped} @{table}_stage AUTO_COMPRESS=TRUE;")

    # Copy from stage into table
    cursor.execute(f"""
        COPY INTO RAW.{table}
        FROM @{table}_stage
        ON_ERROR = 'CONTINUE';
    """)

    print(f"{table} loaded successfully")

cursor.close()
conn.close()
print("\n🎉 All tables loaded into Snowflake RAW schema.")