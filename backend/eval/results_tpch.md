# DataMind Evaluation Results

- Overall accuracy: **4/10 (40.0%)**
- Held-out accuracy: **N/A (no held-out questions)**
- Numeric tolerance: `0.01` (relative and absolute)

## Accuracy by category

| Category | Passed | Total | Accuracy |
|---|---:|---:|---:|
| ambiguous | 1 | 1 | 100.0% |
| filter | 0 | 1 | 0.0% |
| join | 1 | 3 | 33.3% |
| simple_aggregate | 1 | 4 | 25.0% |
| unsupported | 1 | 1 | 100.0% |

## Held-out accuracy by category

| Category | Passed | Total | Accuracy |
|---|---:|---:|---:|

## Per-question results

| Result | ID | Category | Split | Question | Expected | Actual | Query ID | SQL |
|---|---|---|---|---|---|---|---|---|
| FAIL | tpch_customer_count | simple_aggregate | development | How many customer records are in this sample? | numeric=150000 | status=error, answer="I couldn't complete that query right now. Please try again or rephrase your question." | — | `—` |
| FAIL | tpch_order_count | simple_aggregate | development | How many orders are recorded? | numeric=1500000 | status=error, answer="I couldn't complete that query right now. Please try again or rephrase your question." | — | `—` |
| FAIL | tpch_average_order_value | simple_aggregate | development | What is the average total price per order? | numeric=151219.53763164 | status=error, answer="I couldn't complete that query right now. Please try again or rephrase your question." | — | `—` |
| PASS | tpch_total_order_value | simple_aggregate | development | What is the combined total price of all orders? | numeric=226829306447.46 | answer='226829306447.46', rows=[('226829306447.46',)] | 01c7cf6b-0007-82d8-0002-10620002738e | `SELECT SUM("O_TOTALPRICE") AS total_price FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS LIMIT 500` |
| FAIL | tpch_building_orders | join | development | How many orders were placed by customers in the BUILDING market segment? | numeric=303959 | status=error, answer="I couldn't complete that query right now. Please try again or rephrase your question." | — | `—` |
| FAIL | tpch_top_order_nations | join | development | Which three nations account for the most orders? | string_list=['FRANCE', 'RUSSIA', 'INDONESIA'] | status=error, answer="I couldn't complete that query right now. Please try again or rephrase your question." | — | `—` |
| FAIL | tpch_air_line_average | filter | development | What is the average extended price of line items shipped by air? | numeric=38299.98169647 | status=error, answer="I couldn't complete that query right now. Please try again or rephrase your question." | — | `—` |
| PASS | tpch_suppliers_by_region | join | development | How many suppliers belong to each geographic region? | string_list=['AFRICA', 'AMERICA', 'ASIA', 'EUROPE', 'MIDDLE EAST'] | answer='Here is the count of suppliers by geographic region:\nAFRICA: 420\nMIDDLE EAST: 415\nAMERICA: 413\nEUROPE: 412\nASIA: 397', rows=[('AFRICA', 420), ('MIDDLE EAST', 415), ('AMERICA', 413), ('EUROPE', 412), ('ASIA', 397)] | 01c7cf6c-0007-82d8-0002-1062000273be | `SELECT R.R_NAME, COUNT(DISTINCT S.S_SUPPKEY) AS supplier_count FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.REGION AS R JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.SUPPLIER AS S ON R."R_REGIONKEY" = S."S_NATIONKEY" GROUP BY R.R_NAME ORDER BY supplier_count DESC LIMIT 5` |
| PASS | tpch_ambiguous_best_region | ambiguous | development | Which region is best? | status=ambiguous, response contains 'metric' | status=ambiguous, answer='', row_count=0 | — | `—` |
| PASS | tpch_unsupported_future_orders | unsupported | development | Predict which customers will place an order next year. | status=unsupported, response contains 'read-only' | status=unsupported, answer="I can't help with that request. I can answer read-only questions about TPC-H SF1, including data in SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER, SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS, SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.LINEITEM, SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.NATION, SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.REGION, SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.PART, SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.SUPPLIER, SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.PARTSUPP and fields such as C_CUSTKEY, C_NAME, C_ADDRESS, C_NATIONKEY, C_PHONE, C_ACCTBAL, C_MKTSEGMENT, C_COMMENT, O_ORDERKEY, O_CUSTKEY, O_ORDERSTATUS, O_TOTALPRICE, O_ORDERDATE, O_ORDERPRIORITY, O_CLERK, O_SHIPPRIORITY, O_COMMENT, L_ORDERKEY, L_PARTKEY, L_SUPPKEY, L_LINENUMBER, L_QUANTITY, L_EXTENDEDPRICE, L_DISCOUNT, L_TAX, L_RETURNFLAG, L_LINESTATUS, L_SHIPDATE, L_COMMITDATE, L_RECEIPTDATE, L_SHIPINSTRUCT, L_SHIPMODE, L_COMMENT, N_NATIONKEY, N_NAME, N_REGIONKEY, N_COMMENT, R_REGIONKEY, R_NAME, R_COMMENT, P_PARTKEY, P_NAME, P_MFGR, P_BRAND, P_TYPE, P_SIZE, P_CONTAINER, P_RETAILPRICE, P_COMMENT, S_SUPPKEY, S_NAME, S_ADDRESS, S_NATIONKEY, S_PHONE, S_ACCTBAL, S_COMMENT, PS_PARTKEY, PS_SUPPKEY, PS_AVAILQTY, PS_SUPPLYCOST, PS_COMMENT.", row_count=0 | — | `—` |

## Failure analysis

- **tpch_customer_count (simple_aggregate)**: Expected an answerable result. Expected numeric=150000; observed status=error, answer="I couldn't complete that query right now. Please try again or rephrase your question.".
- **tpch_order_count (simple_aggregate)**: Expected an answerable result. Expected numeric=1500000; observed status=error, answer="I couldn't complete that query right now. Please try again or rephrase your question.".
- **tpch_average_order_value (simple_aggregate)**: Expected an answerable result. Expected numeric=151219.53763164; observed status=error, answer="I couldn't complete that query right now. Please try again or rephrase your question.".
- **tpch_building_orders (join)**: Expected an answerable result. Expected numeric=303959; observed status=error, answer="I couldn't complete that query right now. Please try again or rephrase your question.".
- **tpch_top_order_nations (join)**: Expected an answerable result. Expected string_list=['FRANCE', 'RUSSIA', 'INDONESIA']; observed status=error, answer="I couldn't complete that query right now. Please try again or rephrase your question.".
- **tpch_air_line_average (filter)**: Expected an answerable result. Expected numeric=38299.98169647; observed status=error, answer="I couldn't complete that query right now. Please try again or rephrase your question.".

## Independent SQL ground truth

These expected values were queried directly through the reader client, not through the NL pipeline.

| ID | Expected rows | Query ID | Hand-written SQL |
|---|---|---|---|
| tpch_customer_count | [(150000,)] | 01c7cf6a-0007-82d8-0002-106200027366 | `SELECT COUNT(*) AS CUSTOMER_COUNT FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER` |
| tpch_order_count | [(1500000,)] | 01c7cf6a-0007-82d8-0002-10620002736a | `SELECT COUNT(*) AS ORDER_COUNT FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS` |
| tpch_average_order_value | [(Decimal('151219.53763164'),)] | 01c7cf6a-0007-82d8-0002-10620002736e | `SELECT AVG(O_TOTALPRICE) AS AVERAGE_ORDER_VALUE FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS` |
| tpch_total_order_value | [(Decimal('226829306447.46'),)] | 01c7cf6a-0007-82d8-0002-106200027372 | `SELECT SUM(O_TOTALPRICE) AS TOTAL_ORDER_VALUE FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS` |
| tpch_building_orders | [(303959,)] | 01c7cf6a-0007-82d8-0002-106200027376 | `SELECT COUNT(*) AS BUILDING_ORDER_COUNT FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS AS O JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER AS C ON O.O_CUSTKEY = C.C_CUSTKEY WHERE C.C_MKTSEGMENT = 'BUILDING'` |
| tpch_top_order_nations | [('FRANCE', 61600), ('RUSSIA', 61495), ('INDONESIA', 61377)] | 01c7cf6a-0007-82d8-0002-10620002737a | `SELECT N.N_NAME, COUNT(*) AS ORDER_COUNT FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS AS O JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER AS C ON O.O_CUSTKEY = C.C_CUSTKEY JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.NATION AS N ON C.C_NATIONKEY = N.N_NATIONKEY GROUP BY N.N_NAME ORDER BY ORDER_COUNT DESC, N.N_NAME LIMIT 3` |
| tpch_air_line_average | [(Decimal('38299.98169647'),)] | 01c7cf6a-0007-82d8-0002-10620002737e | `SELECT AVG(L_EXTENDEDPRICE) AS AVERAGE_AIR_LINE_PRICE FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.LINEITEM WHERE L_SHIPMODE = 'AIR'` |
| tpch_suppliers_by_region | [('AFRICA', 1955), ('AMERICA', 2036), ('ASIA', 2003), ('EUROPE', 1987), ('MIDDLE EAST', 2019)] | 01c7cf6a-0007-82d8-0002-106200027382 | `SELECT R.R_NAME, COUNT(*) AS SUPPLIER_COUNT FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.SUPPLIER AS S JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.NATION AS N ON S.S_NATIONKEY = N.N_NATIONKEY JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.REGION AS R ON N.N_REGIONKEY = R.R_REGIONKEY GROUP BY R.R_NAME ORDER BY R.R_NAME` |
