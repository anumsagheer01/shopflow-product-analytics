USE DATABASE SHOPFLOW_DB;
USE WAREHOUSE SHOPFLOW_WH;

-- ANALYTICS LAYER
-- Denormalized, business-ready, KPI-friendly tables

CREATE OR REPLACE TABLE ANALYTICS.FACT_ORDER_ITEMS AS
SELECT
    -- Keys
    oi.order_id,
    oi.order_item_id,
    oi.product_id,
    oi.seller_id,
    o.customer_id,

    -- Timestamps
    o.order_purchased_at,
    o.order_approved_at,
    o.delivered_to_customer_at,
    o.estimated_delivery_at,

    -- Order attributes
    o.order_status,
    o.actual_delivery_days,
    o.estimated_delivery_days,
    o.is_late_delivery,

    -- Financial
    oi.item_price,
    oi.freight_value,
    oi.total_item_value,
    p.payment_value,
    p.payment_type,
    p.payment_installments,

    -- Product
    pr.category_english  AS product_category,
    pr.weight_g,
    pr.volume_cm3,

    -- Review
    r.review_score,
    r.sentiment,

    -- Seller location
    s.city   AS seller_city,
    s.state  AS seller_state,

    -- Customer location
    c.city   AS customer_city,
    c.state  AS customer_state,

    -- Time dimensions 
    DATE_TRUNC('month', o.order_purchased_at) AS order_month,
    DATE_TRUNC('quarter', o.order_purchased_at) AS order_quarter,
    YEAR(o.order_purchased_at)  AS order_year

FROM STAGING.STG_ORDER_ITEMS oi
LEFT JOIN STAGING.STG_ORDERS o
    ON oi.order_id = o.order_id
LEFT JOIN STAGING.STG_ORDER_PAYMENTS p
    ON oi.order_id = p.order_id
   AND p.payment_sequential = 1
LEFT JOIN STAGING.STG_PRODUCTS pr
    ON oi.product_id = pr.product_id
LEFT JOIN STAGING.STG_ORDER_REVIEWS r
    ON oi.order_id = r.order_id
LEFT JOIN STAGING.STG_SELLERS s
    ON oi.seller_id = s.seller_id
LEFT JOIN STAGING.STG_CUSTOMERS c
    ON o.customer_id = c.customer_id;


-- DIMENSION TABLE: Customers with lifetime value metrics
CREATE OR REPLACE TABLE ANALYTICS.DIM_CUSTOMERS AS
WITH customer_orders AS (
    SELECT
        c.customer_unique_id,
        c.city,
        c.state,
        COUNT(DISTINCT o.order_id)          AS total_orders,
        SUM(p.payment_value)                AS total_spent,
        AVG(p.payment_value)                AS avg_order_value,
        MIN(o.order_purchased_at)           AS first_order_at,
        MAX(o.order_purchased_at)           AS last_order_at,
        DATEDIFF('day',
            MIN(o.order_purchased_at),
            MAX(o.order_purchased_at))      AS customer_lifespan_days
    FROM STAGING.STG_CUSTOMERS c
    LEFT JOIN STAGING.STG_ORDERS o
        ON c.customer_id = o.customer_id
    LEFT JOIN STAGING.STG_ORDER_PAYMENTS p
        ON o.order_id = p.order_id
       AND p.payment_sequential = 1
    GROUP BY 1,2,3
)
SELECT
    *,
    CASE
        WHEN total_orders >= 3  THEN 'high_value'
        WHEN total_orders = 2   THEN 'returning'
        ELSE 'one_time'
    END AS customer_segment,
    CASE
        WHEN total_spent >= 500 THEN 'whale'
        WHEN total_spent >= 200 THEN 'mid_tier'
        ELSE 'low_tier'
    END AS spend_tier
FROM customer_orders;


-- SUMMARY TABLE: Monthly KPIs 
CREATE OR REPLACE TABLE ANALYTICS.MONTHLY_KPIS AS
SELECT
    order_month,
    COUNT(DISTINCT order_id)                              AS total_orders,
    COUNT(DISTINCT customer_id)                           AS unique_customers,
    SUM(item_price)                                       AS gross_merchandise_value,
    AVG(item_price)                                       AS avg_order_value,
    SUM(freight_value)                                    AS total_freight_revenue,
    ROUND(AVG(review_score), 2)                           AS avg_review_score,
    SUM(CASE WHEN is_late_delivery THEN 1 ELSE 0 END)     AS late_deliveries,
    COUNT(DISTINCT order_id)                              AS total_delivered,
    ROUND(
        SUM(CASE WHEN is_late_delivery THEN 1 ELSE 0 END)
        / NULLIF(COUNT(DISTINCT order_id), 0) * 100
    , 2)                                                  AS late_delivery_rate_pct
FROM ANALYTICS.FACT_ORDER_ITEMS
WHERE order_status = 'delivered'
  AND order_month IS NOT NULL
GROUP BY 1
ORDER BY 1;