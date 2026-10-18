# DataMind Evaluation Results

- Overall accuracy: **14/20 (70.0%)**
- Held-out accuracy: **4/5 (80.0%)**
- Numeric tolerance: `0.01` (relative and absolute)

## Accuracy by category

| Category | Passed | Total | Accuracy |
|---|---:|---:|---:|
| ambiguous | 2 | 2 | 100.0% |
| empty_result | 1 | 2 | 50.0% |
| filter | 3 | 5 | 60.0% |
| join | 0 | 2 | 0.0% |
| multi_step | 2 | 3 | 66.7% |
| simple_aggregate | 4 | 4 | 100.0% |
| unsupported | 2 | 2 | 100.0% |

## Held-out accuracy by category

| Category | Passed | Total | Accuracy |
|---|---:|---:|---:|
| empty_result | 1 | 1 | 100.0% |
| filter | 0 | 1 | 0.0% |
| multi_step | 1 | 1 | 100.0% |
| simple_aggregate | 1 | 1 | 100.0% |
| unsupported | 1 | 1 | 100.0% |

## Per-question results

| Result | ID | Category | Split | Question | Expected | Actual | Query ID | SQL |
|---|---|---|---|---|---|---|---|---|
| PASS | agg_total_rows | simple_aggregate | development | How many client contacts are in the dataset? | numeric=45211 | answer='45211', rows=[(45211,)] | 01c7cf0d-0007-82d8-0002-106200026b1a | `SELECT COUNT(*) AS row_count FROM BANK_MARKETING LIMIT 500` |
| PASS | agg_mean_age | simple_aggregate | development | What is the average age of contacted clients? | numeric=40.93621021432837 | answer='The average age of contacted clients is 40.936210.', rows=[(Decimal('40.936210'),)] | 01c7cf0e-0007-82d8-0002-106200026b22 | `SELECT AVG("age") AS average_age FROM BANK_MARKETING LIMIT 500` |
| PASS | agg_subscribers | simple_aggregate | development | How many clients subscribed to a term deposit? | numeric=5289 | answer='5289 clients subscribed to a term deposit.', rows=[(5289,)] | 01c7cf0e-0007-82d8-0002-106200026b2e | `SELECT COUNT(*) AS subscribed_clients FROM BANK_MARKETING WHERE "y" = 'yes' LIMIT 500` |
| PASS | agg_mean_duration | simple_aggregate | held-out | What was the average duration of the last contact in seconds? | numeric=258.1630797814691 | answer='258.163080', rows=[(Decimal('258.163080'),)] | 01c7cf0e-0007-82d8-0002-106200026b36 | `SELECT AVG("duration") AS average_duration FROM BANK_MARKETING LIMIT 500` |
| PASS | filter_housing | filter | development | How many clients had a housing loan? | numeric=25130 | answer='25130', rows=[(25130,)] | 01c7cf0e-0007-82d8-0002-106200026b3e | `SELECT COUNT(*) AS client_count FROM BANK_MARKETING WHERE "housing" = 'yes' LIMIT 500` |
| PASS | filter_admin | filter | development | How many clients had an admin job? | numeric=5171 | answer='5171', rows=[(5171,)] | 01c7cf0f-0007-82d8-0002-106200026b4a | `SELECT COUNT(*) AS client_count FROM BANK_MARKETING WHERE "job" = 'admin.' LIMIT 500` |
| FAIL | filter_campaign | filter | held-out | How many clients were contacted at least three times in this campaign? | numeric=15162 | answer='48', rows=[(48,)] | 01c7cf0f-0007-82d8-0002-106200026b52 | `SELECT COUNT(DISTINCT "campaign") FROM BANK_MARKETING WHERE "campaign" > 0 LIMIT 500` |
| PASS | filter_cellular | filter | development | How many clients were contacted by cellular phone? | numeric=29285 | answer='29285', rows=[(29285,)] | 01c7cf0f-0007-82d8-0002-106200026b5a | `SELECT COUNT(*) FROM BANK_MARKETING WHERE "contact" = 'cellular' LIMIT 500` |
| FAIL | filter_not_previously_contacted | filter | development | How many clients had not been contacted in a previous campaign? | numeric=0 | answer='36954', rows=[(36954,)] | 01c7cf0f-0007-82d8-0002-106200026b66 | `SELECT COUNT(*) AS num_clients FROM BANK_MARKETING WHERE "pdays" = -1 LIMIT 500` |
| FAIL | join_account_details | join | development | Join each marketing contact to the client's account profile details. | status=unsupported, response contains 'read-only questions' | status=ambiguous, answer="The question 'Join each marketing contact to the client's account profile details' is ambiguous. It does not specify which fields from the BANK_MARKETING table should be joined with which fields from a hypothetical 'client's account profile details' table. Clarification is needed regarding the desired join conditions and the target table.", row_count=0 | — | `—` |
| FAIL | join_product_details | join | development | Join the campaign contacts to product purchase details. | status=unsupported, response contains 'bank_marketing' | status=ambiguous, answer="The question 'Join the campaign contacts to product purchase details' is ambiguous. It does not specify which product details or how the join should be performed.", row_count=0 | — | `—` |
| PASS | multi_housing_subscribers | multi_step | development | How many clients with a housing loan subscribed to a term deposit? | numeric=1935 | answer='1935 clients with a housing loan subscribed to a term deposit.', rows=[(1935,)] | 01c7cf10-0007-82d8-0002-106200026b6e | `SELECT COUNT(CASE WHEN "housing" = 'yes' AND "y" = 'yes' THEN 1 ELSE NULL END) FROM BANK_MARKETING LIMIT 500` |
| FAIL | multi_senior_subscribers | multi_step | development | How many clients over age 40 subscribed to a term deposit? | numeric=2332 | answer='20494', rows=[(20494,)] | 01c7cf10-0007-82d8-0002-106200026b76 | `SELECT COUNT(CASE WHEN "age" > 40 THEN "y" ELSE NULL END) AS subscribed_over_40 FROM BANK_MARKETING LIMIT 500` |
| PASS | multi_best_month | multi_step | held-out | Which month had the most term-deposit subscriptions? | string=may | answer='may', rows=[('may',)] | 01c7cf10-0007-82d8-0002-106200026b82 | `SELECT "month" FROM BANK_MARKETING GROUP BY "month" ORDER BY COUNT(*) DESC LIMIT 1` |
| PASS | ambiguous_best_job | ambiguous | development | What is the best job? | status=ambiguous, response contains 'metric' | status=ambiguous, answer='“Best” or “top” needs a metric to rank by.', row_count=0 | — | `—` |
| PASS | ambiguous_top_clients | ambiguous | development | Show the top clients. | status=ambiguous, response contains 'metric' | status=ambiguous, answer='“Best” or “top” needs a metric to rank by.', row_count=0 | — | `—` |
| PASS | empty_impossible_age | empty_result | held-out | Find clients older than 200 years. | status=answerable, no rows | status=answerable, answer='No rows matched the requested criteria.', row_count=0 | 01c7cf11-0007-82d8-0002-106200026b8a | `SELECT * FROM BANK_MARKETING WHERE "age" > 200 LIMIT 5` |
| FAIL | empty_unknown_job | empty_result | development | Show clients whose job category is astronaut. | status=answerable, no rows | status=answerable, answer='The clients whose job category is unknown are: 33, 47, 59, 37, and 29.', row_count=5 | 01c7cf11-0007-82d8-0002-106200026b92 | `SELECT * FROM BANK_MARKETING WHERE "job" = 'unknown' LIMIT 5` |
| PASS | unsupported_prediction | unsupported | development | Predict which clients will subscribe next year. | status=unsupported, response contains 'read-only questions' | status=unsupported, answer="I can't help with that request. I can answer read-only questions about UCI Bank Marketing, including data in BANK_MARKETING and fields such as age, job, marital, education, default, balance, housing, loan, contact, day, month, duration, campaign, pdays, previous, poutcome, y.", row_count=0 | — | `—` |
| PASS | unsupported_delete | unsupported | held-out | Delete all client records from Snowflake. | status=unsupported, response contains 'bank_marketing' | status=unsupported, answer="I can't help with that request. I can answer read-only questions about UCI Bank Marketing, including data in BANK_MARKETING and fields such as age, job, marital, education, default, balance, housing, loan, contact, day, month, duration, campaign, pdays, previous, poutcome, y.", row_count=0 | — | `—` |

## Failure analysis

- **filter_campaign (filter)**: Answer did not contain the CSV-derived numeric target within tolerance 0.01. Expected numeric=15162; observed answer='48', rows=[(48,)].
- **filter_not_previously_contacted (filter)**: Answer did not contain the CSV-derived numeric target within tolerance 0.01. Expected numeric=0; observed answer='36954', rows=[(36954,)].
- **join_account_details (join)**: Expected behavior/status was not met. Expected status=unsupported, response contains 'read-only questions'; observed status=ambiguous, answer="The question 'Join each marketing contact to the client's account profile details' is ambiguous. It does not specify which fields from the BANK_MARKETING table should be joined with which fields from a hypothetical 'client's account profile details' table. Clarification is needed regarding the desired join conditions and the target table.", row_count=0.
- **join_product_details (join)**: Expected behavior/status was not met. Expected status=unsupported, response contains 'bank_marketing'; observed status=ambiguous, answer="The question 'Join the campaign contacts to product purchase details' is ambiguous. It does not specify which product details or how the join should be performed.", row_count=0.
- **multi_senior_subscribers (multi_step)**: Answer did not contain the CSV-derived numeric target within tolerance 0.01. Expected numeric=2332; observed answer='20494', rows=[(20494,)].
- **empty_unknown_job (empty_result)**: Expected behavior/status was not met. Expected status=answerable, no rows; observed status=answerable, answer='The clients whose job category is unknown are: 33, 47, 59, 37, and 29.', row_count=5.
