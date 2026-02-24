import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (classification_report, 
                             confusion_matrix, 
                             roc_auc_score,
                             RocCurveDisplay)
from sklearn.preprocessing import StandardScaler
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

print("Loading data...")
df = pd.read_sql("""
    SELECT
        CUSTOMER_ID,
        AVG(REVIEW_SCORE)                    AS avg_review_score,
        AVG(ACTUAL_DELIVERY_DAYS)            AS avg_delivery_days,
        SUM(ITEM_PRICE)                      AS total_spent,
        COUNT(DISTINCT ORDER_ID)             AS total_orders,
        AVG(ITEM_PRICE)                      AS avg_order_value,
        SUM(CASE WHEN IS_LATE_DELIVERY 
            THEN 1 ELSE 0 END)               AS late_deliveries,
        MAX(PAYMENT_INSTALLMENTS)            AS max_installments,
        COUNT(DISTINCT PRODUCT_CATEGORY)     AS unique_categories,
        MIN(ORDER_PURCHASED_AT)              AS first_order_date,
        MAX(ORDER_PURCHASED_AT)              AS last_order_date
    FROM ANALYTICS.FACT_ORDER_ITEMS
    WHERE ORDER_STATUS = 'delivered'
      AND CUSTOMER_ID IS NOT NULL
    GROUP BY CUSTOMER_ID
""", conn)
conn.close()

print(f"Loaded {len(df):,} customers\n")

# ── FEATURE ENGINEERING ─────────────────────────────────
print("Engineering features...")

df['first_order_date'] = pd.to_datetime(df['FIRST_ORDER_DATE'])
df['last_order_date'] = pd.to_datetime(df['LAST_ORDER_DATE'])

# Days since last order (recency)
reference_date = df['last_order_date'].max()
df['days_since_last_order'] = (
    reference_date - df['last_order_date']
).dt.days

# Customer lifespan
df['customer_lifespan_days'] = (
    df['last_order_date'] - df['first_order_date']
).dt.days

# Late delivery rate
df['late_delivery_rate'] = (
    df['LATE_DELIVERIES'] / df['TOTAL_ORDERS']
)

# CHURN LABEL
# A customer is "churned" if they haven't ordered 
# in the last 180 days of the dataset
df['is_churned'] = (
    df['days_since_last_order'] > 180
).astype(int)

print(f"Churn rate: {df['is_churned'].mean()*100:.1f}%")
print(f"Churned customers: {df['is_churned'].sum():,}")
print(f"Active customers: {(df['is_churned']==0).sum():,}")

# ── PREPARE FEATURES ────────────────────────────────────
features = [
    'AVG_REVIEW_SCORE',
    'AVG_DELIVERY_DAYS', 
    'TOTAL_SPENT',
    'TOTAL_ORDERS',
    'AVG_ORDER_VALUE',
    'late_delivery_rate',
    'MAX_INSTALLMENTS',
    'UNIQUE_CATEGORIES',
    'customer_lifespan_days'
]

X = df[features].fillna(0)
y = df['is_churned']

# ── TRAIN/TEST SPLIT ────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\nTraining set: {len(X_train):,} customers")
print(f"Test set: {len(X_test):,} customers")

# ── SCALE FEATURES ──────────────────────────────────────
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ── MODEL 1: LOGISTIC REGRESSION ────────────────────────
print("\nLOGISTIC REGRESSION")
lr = LogisticRegression(random_state=42, max_iter=1000)
lr.fit(X_train_scaled, y_train)
lr_pred = lr.predict(X_test_scaled)
lr_auc = roc_auc_score(y_test, 
                        lr.predict_proba(X_test_scaled)[:,1])
print(f"ROC-AUC: {lr_auc:.4f}")
print(classification_report(y_test, lr_pred))

# ── MODEL 2: RANDOM FOREST ───────────────────────────────
print("\nRANDOM FOREST")
rf = RandomForestClassifier(
    n_estimators=100, 
    random_state=42,
    max_depth=10
)
rf.fit(X_train, y_train)
rf_pred = rf.predict(X_test)
rf_auc = roc_auc_score(y_test,
                        rf.predict_proba(X_test)[:,1])
print(f"ROC-AUC: {rf_auc:.4f}")
print(classification_report(y_test, rf_pred))

# ── FEATURE IMPORTANCE ──────────────────────────────────
print("\nTOP FEATURES (Random Forest)")
importance_df = pd.DataFrame({
    'feature': features,
    'importance': rf.feature_importances_
}).sort_values('importance', ascending=False)
print(importance_df.round(4))

# ── VISUALIZATIONS ──────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('ShopFlow Churn Prediction Model', 
             fontsize=18, fontweight='bold')

# Plot 1 - Feature Importance
importance_df.plot(
    kind='barh', x='feature', y='importance',
    ax=axes[0,0], color='steelblue', legend=False
)
axes[0,0].set_title('Feature Importance (Random Forest)')
axes[0,0].set_xlabel('Importance Score')
axes[0,0].invert_yaxis()

# Plot 2 - Confusion Matrix
cm = confusion_matrix(y_test, rf_pred)
sns.heatmap(cm, annot=True, fmt='d', 
            cmap='Blues', ax=axes[0,1])
axes[0,1].set_title('Confusion Matrix (Random Forest)')
axes[0,1].set_xlabel('Predicted')
axes[0,1].set_ylabel('Actual')
axes[0,1].set_xticklabels(['Active', 'Churned'])
axes[0,1].set_yticklabels(['Active', 'Churned'])

# Plot 3 - ROC Curves
RocCurveDisplay.from_estimator(
    lr, X_test_scaled, y_test, 
    ax=axes[1,0], name=f'Logistic Regression'
)
RocCurveDisplay.from_estimator(
    rf, X_test, y_test,
    ax=axes[1,0], name=f'Random Forest'
)
axes[1,0].set_title('ROC Curves- Model Comparison')

# Plot 4 - Churn Distribution
churn_counts = df['is_churned'].value_counts()
axes[1,1].pie(
    churn_counts,
    labels=['Churned', 'Active'],
    colors=['#ff6b6b', '#51cf66'],
    autopct='%1.1f%%',
    startangle=90
)
axes[1,1].set_title('Customer Churn Distribution')

plt.tight_layout()
plt.savefig('docs/churn_model.png', 
            dpi=150, bbox_inches='tight')
plt.show()
print("\nChurn model complete!")
print(f"Best model: Random Forest (AUC={rf_auc:.4f})")