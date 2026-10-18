# Five-minute DataMind demo

Use a configured Snowflake account and working Gemma backend. Keep the source
data unchanged. The manual data-change segment is optional unless the
disposable-copy demo has already been prepared and verified.

| Time | Walkthrough |
|---|---|
| 0:00–0:30 | **Introduce the system.** Show the React UI, health indicators, and the selected UCI Bank Marketing dataset. Explain that Gemma interprets questions, while Snowflake executes queries and supplies the answer evidence. |
| 0:30–1:00 | **Simple aggregate.** Ask “How many clients subscribed to a term deposit?” Open the evidence panel and point out the answer, executed SQL, returned row, and Snowflake query ID. |
| 1:00–1:35 | **Join question.** Select TPC-H SF1 and ask “Which three nations have the most orders?” Show the configured `ORDERS -> CUSTOMER -> NATION` path and all three result rows. |
| 1:35–2:05 | **Clarification.** Ask “Which region is best?” Show the clarification and explain that a ranking needs a metric; the system does not silently choose one. |
| 2:05–2:30 | **Empty result.** Ask “Show clients older than 200 years.” Show the valid query and the empty result message rather than fabricated rows. |
| 2:30–2:55 | **Refusal.** Ask “Predict which customers will place an order next year.” Show that unsupported predictions are refused, while read-only questions remain supported. |
| 2:55–3:30 | **Evidence and safety.** Reopen an evidence panel to show SQL, rows, query ID, explanation, and assumptions. Mention that the API guard and the `DATAMIND_READER` role both enforce read-only access. |
| 3:30–4:20 | **Data-change demonstration.** If already prepared, follow [the manual clone demo](demo_data_change.md): show the same aggregate against a disposable Snowflake clone before and after a tagged synthetic row is inserted, then after it is deleted. Point out the three fresh query IDs and direct SQL checks. Do not improvise writes during the presentation; the source table must not be modified. If the demo is not prepared, show the written procedure and state that it remains a manual step. |
| 4:20–4:40 | **Dataset B.** Re-select TPC-H SF1, show its examples, and explain that its sample tables are queried in-account and are not copied into the repository. |
| 4:40–5:00 | **Limitations.** Be explicit that live language-model output varies. The recorded Bank Marketing scores are 14/20 (70%, held-out 4/5), unseen 15/20 (75%), and TPC-H 4/10 (40%). The TPC-H grouped-label grader does not fully verify metric-to-label pairing; consult [testing limitations](testing.md). These figures are recorded runs, not guarantees. |

If a live query fails, do not hide or replace the error with a prepared answer.
Show the failure and its evidence, or move to another documented example and
identify the skipped step honestly.
