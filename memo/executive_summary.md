## Product Analytics: Executive Summary
**Date:** February 2026  
**About the data:** This analysis uses 113,000+ real 
transactions from a Brazilian e-commerce marketplace 
(2016–2018), rebranded as ShopFlow for portfolio purposes.

### What this analysis Is About
This project analyzes customer orders, delivery performance, 
and satisfaction scores to answer three questions:

1. What is driving low customer satisfaction scores?
2. Are customers coming back for repeat purchases?
3. Can statistical testing reveal differences between 
   customer groups?

### Finding 1: Late Deliveries are the biggest problem

- Compared review scores between orders that arrived 
on time versus orders that arrived late.

- Orders delivered on time: **4.1 out of 5 stars**
- Orders delivered late: **2.6 out of 5 stars**

That is a significant drop in satisfaction caused purely 
by late delivery. Customers who wait longer than expected 
are far more likely to leave a negative review.

The slowest product categories by average delivery time:
- Office furniture: 20+ days on average
- Security products: 19+ days on average
- Mattresses: 15+ days on average

**What this means for the business:**
Improving delivery speed, especially for slow categories,
is the single most direct way to improve customer 
satisfaction scores.

**Suggested next step:**
Set a target delivery time for each product category. 
Monitor sellers who consistently miss those targets and 
work with them to improve.

### Finding 2: Customers are not coming back

In this dataset, virtually every customer made only one 
purchase. The platform is growing by attracting new 
customers each month, but it is not successfully bringing 
existing customers back.

Monthly new customer acquisition grew steadily from 
late 2016 through mid-2018, which is positive. However, 
without repeat purchases, every month the business must 
find entirely new customers just to maintain revenue.

The average order value across all transactions 
is **R$112.89** (Brazilian Reais, the local currency).

**What this means for the business:**
Retention is a major untapped opportunity. Even a small 
improvement in repeat purchase rate would significantly 
reduce the cost of growing revenue.

**Suggested next step:**
Introduce simple post-purchase follow-ups such as 
a thank you email, a product recommendation, or a 
small incentive to return. These are low-cost actions 
with potentially high impact.

### Finding 3: Statistical Testing Demonstration

**What this section is:**
Designed a simulated comparison 
between two customer groups, those who paid by credit 
card versus those who paid by boleto (a Brazilian payment 
method). This was not a real experiment, no changes were 
made to the platform. It is a methodology demonstration.

**What was tested:**
Whether the two payment groups had meaningfully different 
order completion rates.

**Resutls:**
- Credit card group completion rate: 97.8%
- Boleto group completion rate: 97.8%
- P-value: 0.55

A p-value of 0.55 means there is a 55% chance this 
difference is just random variation. In statistical 
terms this is not significant, the two groups performed 
essentially the same.

**What this means:**
Payment method alone does not appear to affect whether 
an order gets completed. In a real business setting, 
this result would mean: do not invest engineering 
resources in changing the checkout flow based on 
this data alone.

**Note:**
A properly designed experiment would randomly assign 
users to different checkout experiences and measure 
the impact over time. This simulation demonstrates 
the analytical framework used in real A/B testing.

### Three Things To Focus On

| Priority | What To Do |
|---|---|
| 1 | Identify sellers with the longest delivery times and set improvement targets |
| 2 | Launch simple post-purchase emails to encourage repeat buying |
| 3 | If checkout testing is a future priority, design a proper controlled experiment |


### Data Notes
- Source: Real Brazilian e-commerce marketplace, 2016–2018
- Orders analyzed: 113,000+
- All prices in Brazilian Reais (R$)
- Analysis conducted in SQL, Python, and Power BI
- Statistical test used: Two-proportion z-test
- All figures calculated directly from the dataset