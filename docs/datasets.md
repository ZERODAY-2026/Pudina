# Dataset sources and attribution

DataMind stores dataset schemas and relationship metadata in
`backend/config/*.yaml`.
The YAML does not contain a copy of either dataset's rows.

## Dataset A — UCI Bank Marketing

- **Source:** [UCI Bank Marketing](https://archive.ics.uci.edu/dataset/222/bank+marketing)
- **License:** Creative Commons Attribution 4.0 International (CC BY 4.0),
  as stated on the UCI dataset page.
- **Attribution (UCI Cite button):** Moro, S., Rita, P., & Cortez, P. (2014).
  *Bank Marketing* [Dataset]. UCI Machine Learning Repository.
  https://doi.org/10.24432/C5K306.
- **Changes:** None to the source dataset. The CSV is downloaded locally for
  loading/evaluation and is not committed to this repository.
- **Configuration:** [`dataset_a.yaml`](../backend/config/dataset_a.yaml). The table
  used by the backend is `BANK_MARKETING`; the source CSV is semicolon-delimited.

## Dataset B — Snowflake TPC-H SF1 sample data

- **Source:** Snowflake's in-account `SNOWFLAKE_SAMPLE_DATA.TPCH_SF1` sample
  database.
- **License:** No open-data license is stated in this project for this sample
  data; this documentation does not claim or grant one.
- **Changes:** None. The backend queries the sample tables in the Snowflake
  account using fully qualified names. No TPC-H rows are copied into the
  repository.
- **Configuration:** [`dataset_b.yaml`](../backend/config/dataset_b.yaml) describes
  `CUSTOMER`, `ORDERS`, `LINEITEM`, `NATION`, `REGION`, `PART`, `SUPPLIER`, and
  `PARTSUPP`, with configured join keys.
- **Access:** The reader role must have the required database/schema usage and
  SELECT privileges in the account. The app does not create a local copy.

## Data-change demonstration

The reversible demo creates a Snowflake copy of the Bank Marketing table,
adds and removes one tagged synthetic row on that copy, verifies the changed
answer, and drops the copy. It never writes to the original table. See
[`demo_data_change.md`](./demo_data_change.md) for safety steps and manual
cleanup guidance.
