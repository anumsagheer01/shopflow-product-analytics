import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import snowflake.connector
import os
from dotenv import load_dotenv

load_dotenv()

# ── Connect + Load ──────────────────────────────────────
conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    warehouse="SHOPFLOW_WH",
    database="SHOPFLOW_DB",
    schema="ANALYTICS"
)

df = pd.read_sql("SELECT * FROM ANALYTICS.FACT_ORDER_ITEMS WHERE ORDER_PURCHASED_AT IS NOT NULL LIMIT 50000", conn)
conn.close()
print(f"Loaded {len(df):,} rows\n")

# ── 1. Basic Info ───────────────────────────────────────
print("=== SHAPE ===")
print(df.shape)

print("\n=== MISSING VALUES ===")
missing = df.isnull().sum()
missing = missing[missing > 0]
print(missing)

print("\nORDER STATUS DISTRIBUTION")
print(df['ORDER_STATUS'].value_counts())

print("\nBASIC STATS")
print(df[['ITEM_PRICE','FREIGHT_VALUE','REVIEW_SCORE','ACTUAL_DELIVERY_DAYS']].describe().round(2))

# ── 2. Revenue by Category ──────────────────────────────
print("\nTOP 10 CATEGORIES BY REVENUE")
cat_revenue = df.groupby('PRODUCT_CATEGORY')['ITEM_PRICE'].sum().sort_values(ascending=False).head(10)
print(cat_revenue.round(2))

# ── 3. Late Delivery Analysis ───────────────────────────
print("\nLATE DELIVERY RATE")
late_rate = df['IS_LATE_DELIVERY'].mean() * 100
print(f"Overall late delivery rate: {late_rate:.2f}%")

print("\nLATE DELIVERY vs REVIEW SCORE")
late_review = df.groupby('IS_LATE_DELIVERY')['REVIEW_SCORE'].mean().round(2)
print(late_review)

# ── 4. Monthly Revenue Trend ────────────────────────────
print("\nMONTHLY REVENUE")
df['ORDER_MONTH'] = pd.to_datetime(df['ORDER_MONTH'])
monthly = df.groupby('ORDER_MONTH')['ITEM_PRICE'].sum().round(2)
print(monthly)

# ── 5. Customer Segments ────────────────────────────────
print("\nPAYMENT TYPE DISTRIBUTION")
print(df['PAYMENT_TYPE'].value_counts())

print("\SENTIMENT DISTRIBUTION")
print(df['SENTIMENT'].value_counts())

print("\nEDA Complete!")

# ── VISUALIZATIONS ──────────────────────────────────────
sns.set_theme(style="whitegrid")
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('ShopFlow EDA Dashboard', fontsize=18, fontweight='bold')

# Plot 1 — Top 10 Categories by Revenue
cat_revenue.plot(kind='barh', ax=axes[0,0], color='steelblue')
axes[0,0].set_title('Top 10 Categories by Revenue')
axes[0,0].set_xlabel('Total Revenue (BRL)')
axes[0,0].invert_yaxis()

# Plot 2 — Monthly Revenue Trend
monthly.plot(kind='line', ax=axes[0,1], color='green', marker='o')
axes[0,1].set_title('Monthly Revenue Trend')
axes[0,1].set_xlabel('Month')
axes[0,1].set_ylabel('Revenue (BRL)')

# Plot 3 — Late Delivery vs Review Score
late_review.plot(kind='bar', ax=axes[1,0], color=['steelblue','red'])
axes[1,0].set_title('Avg Review Score: On Time vs Late')
axes[1,0].set_xlabel('Is Late Delivery')
axes[1,0].set_ylabel('Average Review Score')
axes[1,0].set_xticklabels(['On Time', 'Late'], rotation=0)

# Plot 4 — Payment Type Distribution
df['PAYMENT_TYPE'].value_counts().plot(kind='bar', ax=axes[1,1], color='purple')
axes[1,1].set_title('Payment Type Distribution')
axes[1,1].set_xlabel('Payment Type')
axes[1,1].set_ylabel('Count')
axes[1,1].tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig('docs/eda_dashboard.png', dpi=150, bbox_inches='tight')
plt.show()
print("Charts saved to docs/eda_dashboard.png")

# ── COHORT ANALYSIS ─────────────────────────────────────
cohort_df = df[df['ORDER_STATUS'] == 'delivered'].copy()
cohort_df['ORDER_MONTH'] = pd.to_datetime(cohort_df['ORDER_MONTH'])

cohort_df['COHORT_MONTH'] = cohort_df.groupby('CUSTOMER_ID')['ORDER_MONTH'].transform('min')
cohort_df['COHORT_INDEX'] = (
    (cohort_df['ORDER_MONTH'].dt.year - cohort_df['COHORT_MONTH'].dt.year) * 12 +
    (cohort_df['ORDER_MONTH'].dt.month - cohort_df['COHORT_MONTH'].dt.month)
)

cohort_counts = cohort_df.groupby(
    ['COHORT_MONTH', 'COHORT_INDEX'])['CUSTOMER_ID'].nunique().reset_index()
cohort_pivot = cohort_counts.pivot(
    index='COHORT_MONTH', columns='COHORT_INDEX', values='CUSTOMER_ID')
cohort_retention = cohort_pivot.divide(cohort_pivot[0], axis=0).round(3) * 100

# ── Key Insight Print ───────────────────────────────────
total_customers = cohort_df['CUSTOMER_ID'].nunique()
repeat_customers = cohort_df[cohort_df['COHORT_INDEX'] > 0]['CUSTOMER_ID'].nunique()
repeat_rate = repeat_customers / total_customers * 100
print(f"\nTotal unique customers: {total_customers:,}")
print(f"Repeat customers: {repeat_customers:,}")
print(f"Repeat purchase rate: {repeat_rate:.2f}%")
print("\nKEY INSIGHT: ShopFlow has very low repeat purchase rate")
print("This is the core business problem to solve!")

# ── Plot: Repeat vs One-time customers ─────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('ShopFlow Customer Retention Analysis', fontsize=16, fontweight='bold')

# Pie chart
labels = ['One-time buyers', 'Repeat buyers']
sizes = [total_customers - repeat_customers, repeat_customers]
colors = ['#ff6b6b', '#51cf66']
axes[0].pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
axes[0].set_title('Customer Purchase Frequency')

# Monthly new vs repeat customers
monthly_cohort = cohort_df.groupby(['ORDER_MONTH', 'COHORT_INDEX'])['CUSTOMER_ID'].nunique().reset_index()
new_customers = monthly_cohort[monthly_cohort['COHORT_INDEX'] == 0].set_index('ORDER_MONTH')['CUSTOMER_ID']
repeat_monthly = monthly_cohort[monthly_cohort['COHORT_INDEX'] > 0].groupby('ORDER_MONTH')['CUSTOMER_ID'].sum()

new_customers.plot(ax=axes[1], label='New Customers', color='steelblue', marker='o')
repeat_monthly.plot(ax=axes[1], label='Repeat Customers', color='orange', marker='s')
axes[1].set_title('New vs Repeat Customers Over Time')
axes[1].set_xlabel('Month')
axes[1].set_ylabel('Customer Count')
axes[1].legend()

plt.tight_layout()
plt.savefig('docs/cohort_analysis.png', dpi=150, bbox_inches='tight')
plt.show()
print("Cohort analysis saved!")