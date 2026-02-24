import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
import snowflake.connector
import os
from dotenv import load_dotenv

load_dotenv()

# ── Connect ─────────────────────────────────────────────
conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    warehouse="SHOPFLOW_WH",
    database="SHOPFLOW_DB",
    schema="ANALYTICS"
)

df = pd.read_sql("SELECT * FROM ANALYTICS.FACT_ORDER_ITEMS WHERE ORDER_PURCHASED_AT IS NOT NULL", conn)
conn.close()
print(f"Loaded {len(df):,} rows\n")

# ── A/B TEST SETUP ───────────────────────────────────────
# Business Question: Did our new checkout UI increase conversion?
# Simulate this using real order data
# Control group = credit_card payments (existing checkout)
# Treatment group = boleto payments (new checkout flow)
# Metric = completion rate (delivered vs total)

print("A/B TEST: Checkout UI Impact on Order Completion\n")

# Control group — credit card
control = df[df['PAYMENT_TYPE'] == 'credit_card'].copy()
control_delivered = len(control[control['ORDER_STATUS'] == 'delivered'])
control_total = len(control)
control_rate = control_delivered / control_total

# Treatment group — boleto
treatment = df[df['PAYMENT_TYPE'] == 'boleto'].copy()
treatment_delivered = len(treatment[treatment['ORDER_STATUS'] == 'delivered'])
treatment_total = len(treatment)
treatment_rate = treatment_delivered / treatment_total

print(f"Control (Credit Card):")
print(f"  Total orders: {control_total:,}")
print(f"  Delivered: {control_delivered:,}")
print(f"  Completion rate: {control_rate:.4f} ({control_rate*100:.2f}%)")

print(f"\nTreatment (Boleto):")
print(f"  Total orders: {treatment_total:,}")
print(f"  Delivered: {treatment_delivered:,}")
print(f"  Completion rate: {treatment_rate:.4f} ({treatment_rate*100:.2f}%)")

# ── STATISTICAL TEST ─────────────────────────────────────
print("\nSTATISTICAL SIGNIFICANCE TEST\n")

# Two proportion z-test
count = np.array([control_delivered, treatment_delivered])
nobs = np.array([control_total, treatment_total])

from statsmodels.stats.proportion import proportions_ztest, proportion_confint
stat, p_value = proportions_ztest(count, nobs)

# Confidence intervals
ci_control = proportion_confint(control_delivered, control_total, alpha=0.05)
ci_treatment = proportion_confint(treatment_delivered, treatment_total, alpha=0.05)

# Effect size (Cohen's h)
cohens_h = 2 * np.arcsin(np.sqrt(control_rate)) - 2 * np.arcsin(np.sqrt(treatment_rate))

print(f"Z-statistic: {stat:.4f}")
print(f"P-value: {p_value:.6f}")
print(f"Control 95% CI: ({ci_control[0]:.4f}, {ci_control[1]:.4f})")
print(f"Treatment 95% CI: ({ci_treatment[0]:.4f}, {ci_treatment[1]:.4f})")
print(f"Cohen's h (effect size): {abs(cohens_h):.4f}")

# ── DECISION ─────────────────────────────────────────────
alpha = 0.05
print(f"\nDECISION")
if p_value < alpha:
    print(f"STATISTICALLY SIGNIFICANT (p={p_value:.6f} < {alpha})")
    print(f"Reject null hypothesis — the difference is real, not due to chance")
else:
    print(f"NOT STATISTICALLY SIGNIFICANT (p={p_value:.6f} > {alpha})")
    print(f"Fail to reject null hypothesis")

# Revenue impact estimate
lift = treatment_rate - control_rate
avg_order_value = df['ITEM_PRICE'].mean()
monthly_orders = len(df) / 23
projected_monthly_impact = lift * monthly_orders * avg_order_value
projected_annual_impact = projected_monthly_impact * 12

print(f"\n=== BUSINESS IMPACT ===")
print(f"Completion rate lift: {lift*100:+.2f} percentage points")
print(f"Average order value: R${avg_order_value:.2f}")
print(f"Projected monthly impact: R${projected_monthly_impact:,.2f}")
print(f"Projected annual impact: R${projected_annual_impact:,.2f}")

# ── VISUALIZATION ────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('ShopFlow A/B Test Results — Checkout UI', fontsize=16, fontweight='bold')

# Bar chart
groups = ['Control\n(Credit Card)', 'Treatment\n(Boleto)']
rates = [control_rate * 100, treatment_rate * 100]
colors = ['steelblue', 'orange']
bars = axes[0].bar(groups, rates, color=colors, width=0.4)
axes[0].set_title('Order Completion Rate by Group')
axes[0].set_ylabel('Completion Rate (%)')
axes[0].set_ylim(0, 100)
for bar, rate in zip(bars, rates):
    axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{rate:.1f}%', ha='center', fontweight='bold')

# Confidence intervals
axes[1].errorbar(['Control', 'Treatment'],
                 [control_rate*100, treatment_rate*100],
                 yerr=[(control_rate - ci_control[0])*100,
                       (treatment_rate - ci_treatment[0])*100],
                 fmt='o', markersize=10, capsize=10,
                 color='steelblue', ecolor='gray', linewidth=2)
axes[1].set_title('Completion Rates with 95% Confidence Intervals')
axes[1].set_ylabel('Completion Rate (%)')

# Add p-value annotation
significance = "SIGNIFICANT" if p_value < alpha else "NOT SIGNIFICANT"
axes[1].text(0.5, 0.05, f'p-value: {p_value:.4f} — {significance}',
             transform=axes[1].transAxes, ha='center',
             fontsize=11, fontweight='bold',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig('docs/ab_test_results.png', dpi=150, bbox_inches='tight')
plt.show()
print("\n A/B test results saved to docs/ab_test_results.png")