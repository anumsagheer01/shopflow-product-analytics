USE DATABASE SHOPFLOW_DB;
USE WAREHOUSE SHOPFLOW_WH;


-- STAGING LAYER
-- Clean types, rename columns, handle nulls, join translations


-- STAGING: ORDERS
CREATE OR REPLACE TABLE STAGING.STG_ORDERS AS
SELECT
    order_id,
    customer_id,
    order_status,
    TRY_TO_TIMESTAMP(order_purchase_timestamp)      AS order_purchased_at,
    TRY_TO_TIMESTAMP(order_approved_at)             AS order_approved_at,
    TRY_TO_TIMESTAMP(order_delivered_carrier_date)  AS delivered_to_carrier_at,
    TRY_TO_TIMESTAMP(order_delivered_customer_date) AS delivered_to_customer_at,
    TRY_TO_TIMESTAMP(order_estimated_delivery_date) AS estimated_delivery_at,
    -- Derived fields
    DATEDIFF('day',
        TRY_TO_TIMESTAMP(order_purchase_timestamp),
        TRY_TO_TIMESTAMP(order_delivered_customer_date)
    ) AS actual_delivery_days,
    DATEDIFF('day',
        TRY_TO_TIMESTAMP(order_purchase_timestamp),
        TRY_TO_TIMESTAMP(order_estimated_delivery_date)
    ) AS estimated_delivery_days,
    CASE
        WHEN TRY_TO_TIMESTAMP(order_delivered_customer_date)
           > TRY_TO_TIMESTAMP(order_estimated_delivery_date)
        THEN TRUE ELSE FALSE
    END AS is_late_delivery
FROM RAW.ORDERS
WHERE order_id IS NOT NULL;


-- STAGING: ORDER ITEMS
CREATE OR REPLACE TABLE STAGING.STG_ORDER_ITEMS AS
SELECT
    order_id,
    order_item_id,
    product_id,
    seller_id,
    TRY_TO_TIMESTAMP(shipping_limit_date) AS shipping_limit_at,
    price::FLOAT                          AS item_price,
    freight_value::FLOAT                  AS freight_value,
    (price + freight_value)::FLOAT        AS total_item_value
FROM RAW.ORDER_ITEMS
WHERE order_id IS NOT NULL;


-- STAGING: ORDER PAYMENTS
CREATE OR REPLACE TABLE STAGING.STG_ORDER_PAYMENTS AS
SELECT
    order_id,
    payment_sequential,
    payment_type,
    payment_installments::NUMBER  AS payment_installments,
    payment_value::FLOAT          AS payment_value
FROM RAW.ORDER_PAYMENTS
WHERE order_id IS NOT NULL;


-- STAGING: ORDER REVIEWS
CREATE OR REPLACE TABLE STAGING.STG_ORDER_REVIEWS AS
SELECT
    review_id,
    order_id,
    review_score::NUMBER                            AS review_score,
    review_comment_title,
    review_comment_message,
    TRY_TO_TIMESTAMP(review_creation_date)          AS review_created_at,
    TRY_TO_TIMESTAMP(review_answer_timestamp)       AS review_answered_at,
    CASE
        WHEN review_score >= 4 THEN 'positive'
        WHEN review_score = 3  THEN 'neutral'
        ELSE 'negative'
    END AS sentiment
FROM RAW.ORDER_REVIEWS
WHERE review_id IS NOT NULL;


-- STAGING: CUSTOMERS
CREATE OR REPLACE TABLE STAGING.STG_CUSTOMERS AS
SELECT
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix AS zip_code,
    INITCAP(customer_city)   AS city,
    UPPER(customer_state)    AS state
FROM RAW.CUSTOMERS
WHERE customer_id IS NOT NULL;


-- STAGING: PRODUCTS (with English translation joined)
CREATE OR REPLACE TABLE STAGING.STG_PRODUCTS AS
SELECT
    p.product_id,
    COALESCE(t.product_category_name_english,
             p.product_category_name,
             'unknown')      AS category_english,
    p.product_name_length,
    p.product_description_length,
    p.product_photos_qty,
    p.product_weight_g::FLOAT   AS weight_g,
    p.product_length_cm::FLOAT  AS length_cm,
    p.product_height_cm::FLOAT  AS height_cm,
    p.product_width_cm::FLOAT   AS width_cm,

    (p.product_length_cm * p.product_height_cm * p.product_width_cm)::FLOAT AS volume_cm3
FROM RAW.PRODUCTS p
LEFT JOIN RAW.CATEGORY_TRANSLATION t
    ON p.product_category_name = t.product_category_name
WHERE p.product_id IS NOT NULL;


-- STAGING: SELLERS
CREATE OR REPLACE TABLE STAGING.STG_SELLERS AS
SELECT
    seller_id,
    seller_zip_code_prefix AS zip_code,
    INITCAP(seller_city)   AS city,
    UPPER(seller_state)    AS state
FROM RAW.SELLERS
WHERE seller_id IS NOT NULL;