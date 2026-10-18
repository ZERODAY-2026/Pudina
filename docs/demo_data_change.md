# Reversible Snowflake data-change demo

This demo shows that the same aggregate answer changes after a controlled data
change and returns to its original value after revert. It edits a disposable
Snowflake clone of `BANK_MARKETING`, never the source table. The clone and its
tagged synthetic row are removed when the script finishes successfully.

The fixed question is: **How many clients have the student occupation?** The
pipeline and direct SQL checks run as `DATAMIND_READER`. Only the isolated
clone/create/insert/delete/drop operations run as `DATAMIND_LOADER`.

## Automated demo

Run from the repository root after configuring both Snowflake roles, the Gemma
backend, and loading the source dataset:

```powershell
Push-Location backend
python -m scripts.demo_data_change --dry-run
python -m scripts.demo_data_change
Pop-Location
```

The dry run sends the aggregate question through the reader pipeline and checks
it with direct read-only SQL. It does not connect with the loader role, create a
clone, or write data.

The real run asks you to type `DEMO` before any Snowflake write. It then:

1. Creates or refreshes the reserved `BANK_MARKETING_DEMO_CHANGE` table as a
   Snowflake clone of `BANK_MARKETING`.
2. Records the `BEFORE` answer and query ID, and checks the count with direct
   SQL using the reader role.
3. Inserts one clearly tagged synthetic row using the loader role. The `job`
   value is `student`; `marital` is set to `__DATAMIND_B4_DEMO__` as the tag.
4. Records the `AFTER` answer and a new query ID, and verifies the direct SQL
   count increased by exactly one.
5. Deletes only the tagged row using the loader role, verifies the tag is gone,
   and records the `REVERTED` answer and another new query ID. The reverted
   value must equal `BEFORE`.
6. Drops the clone. `BANK_MARKETING` itself is never changed.

Each pipeline answer and its corresponding direct SQL count must agree or the
script fails. The reserved clone is replaced on a confirmed rerun, so an
interrupted previous demo cannot cause duplicate demo rows in the source. If
the script cannot drop the clone, it reports the failure; remove
`BANK_MARKETING_DEMO_CHANGE` manually with the loader role before considering
the demo complete.

The loader must be able to read the source table to create a clone. The
committed setup template grants that read access. If the roles were set up
before this grant was added, run these statements as a Snowflake administrator
or the schema owner:

```sql
GRANT SELECT ON ALL TABLES IN SCHEMA DATAMIND_DB.PUBLIC_DATA
    TO ROLE DATAMIND_LOADER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA DATAMIND_DB.PUBLIC_DATA
    TO ROLE DATAMIND_LOADER;
```

The loader also needs the schema-level `CREATE TABLE` privilege shown in
[`setup.sql.example`](../scripts/setup.sql.example). The reader role needs
`SELECT` on future tables so it can query the new clone.

## Manual video variant: Snowsight and React UI

This variant demonstrates the same lifecycle in Snowsight while asking the
question from the React frontend. It still changes only a Snowflake copy.

1. Confirm the `.env` database and schema, and make sure `DATAMIND_READER` can
   select from future tables and `DATAMIND_LOADER` can select from the source
   and create tables.
2. Copy `backend/config/dataset_a.yaml` to a temporary
   `backend/config/dataset_demo_change.yaml`. In that copy, set
   `dataset_name: UCI Bank Marketing Demo Copy` and change the sole table name
   from `BANK_MARKETING` to `BANK_MARKETING_DEMO_CHANGE`. Do not change the
   committed source config.
3. In Snowsight, switch to `DATAMIND_LOADER`, then create the disposable clone
   and insert the single tagged row. Replace the database/schema identifiers
   below only if your `.env` uses different values:

   ```sql
   CREATE OR REPLACE TABLE DATAMIND_DB.PUBLIC_DATA.BANK_MARKETING_DEMO_CHANGE
       CLONE DATAMIND_DB.PUBLIC_DATA.BANK_MARKETING;

   INSERT INTO DATAMIND_DB.PUBLIC_DATA.BANK_MARKETING_DEMO_CHANGE
       ("age", "job", "marital", "education", "default", "balance",
        "housing", "loan", "contact", "day", "month", "duration",
        "campaign", "pdays", "previous", "poutcome", "y")
   VALUES
       (42, 'student', '__DATAMIND_B4_DEMO__', 'tertiary', 'no', 0,
        'no', 'no', 'cellular', 1, 'may', 1, 1, -1, 0, 'unknown', 'no');
   ```

4. Start the backend from the backend directory with
   `uvicorn src.api:app --reload --port 8000`, and start your React client using
   its normal development command. The backend discovers YAML files in
   `backend/config/`; select the additional **UCI Bank Marketing Demo Copy**
   dataset in the UI. Its API dataset ID is `bank-marketing-demo-copy`. If the
   React app runs on a different origin than `http://localhost:5173`, add that
   origin to `CORS_ORIGINS` in `.env` and restart the backend.
5. Ask **How many clients have the student occupation?** and record the
   answer and `query_id`. In Snowsight, verify the count as the reader role:

   ```sql
   SELECT COUNT(*) AS student_count
   FROM DATAMIND_DB.PUBLIC_DATA.BANK_MARKETING_DEMO_CHANGE
   WHERE "job" = 'student';
   ```

6. After the UI answer has been recorded, revert the clone and ask the same
   question again:

   ```sql
   DELETE FROM DATAMIND_DB.PUBLIC_DATA.BANK_MARKETING_DEMO_CHANGE
   WHERE "marital" = '__DATAMIND_B4_DEMO__';
   ```

   Verify the direct count now equals the original count. The UI should return
   the same original answer with a new `query_id`.
7. Drop the disposable copy and remove the temporary YAML file:

   ```sql
   DROP TABLE DATAMIND_DB.PUBLIC_DATA.BANK_MARKETING_DEMO_CHANGE;
   ```

   ```powershell
   Remove-Item .\backend\config\dataset_demo_change.yaml
   ```

The source `BANK_MARKETING` table remains unchanged throughout. Do not run the
insert or delete against the source table.
