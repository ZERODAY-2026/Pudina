"""Compute independent TPC-H targets with hand-written Snowflake SQL."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable

from src.snowflake_client import SnowflakeClient


TPCH_GROUND_TRUTH_SQL: dict[str, str] = {
    "tpch_customer_count": (
        "SELECT COUNT(*) AS CUSTOMER_COUNT "
        "FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER"
    ),
    "tpch_order_count": (
        "SELECT COUNT(*) AS ORDER_COUNT "
        "FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS"
    ),
    "tpch_average_order_value": (
        "SELECT AVG(O_TOTALPRICE) AS AVERAGE_ORDER_VALUE "
        "FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS"
    ),
    "tpch_total_order_value": (
        "SELECT SUM(O_TOTALPRICE) AS TOTAL_ORDER_VALUE "
        "FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS"
    ),
    "tpch_building_orders": (
        "SELECT COUNT(*) AS BUILDING_ORDER_COUNT "
        "FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS AS O "
        "JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER AS C "
        "ON O.O_CUSTKEY = C.C_CUSTKEY "
        "WHERE C.C_MKTSEGMENT = 'BUILDING'"
    ),
    "tpch_top_order_nations": (
        "SELECT N.N_NAME, COUNT(*) AS ORDER_COUNT "
        "FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS AS O "
        "JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER AS C "
        "ON O.O_CUSTKEY = C.C_CUSTKEY "
        "JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.NATION AS N "
        "ON C.C_NATIONKEY = N.N_NATIONKEY "
        "GROUP BY N.N_NAME "
        "ORDER BY ORDER_COUNT DESC, N.N_NAME "
        "LIMIT 3"
    ),
    "tpch_air_line_average": (
        "SELECT AVG(L_EXTENDEDPRICE) AS AVERAGE_AIR_LINE_PRICE "
        "FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.LINEITEM "
        "WHERE L_SHIPMODE = 'AIR'"
    ),
    "tpch_suppliers_by_region": (
        "SELECT R.R_NAME, COUNT(*) AS SUPPLIER_COUNT "
        "FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.SUPPLIER AS S "
        "JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.NATION AS N "
        "ON S.S_NATIONKEY = N.N_NATIONKEY "
        "JOIN SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.REGION AS R "
        "ON N.N_REGIONKEY = R.R_REGIONKEY "
        "GROUP BY R.R_NAME "
        "ORDER BY R.R_NAME"
    ),
}

_LIST_TARGETS = {"tpch_top_order_nations", "tpch_suppliers_by_region"}
ClientFactory = Callable[[], SnowflakeClient]


def compute_tpch_ground_truth(
    client_factory: ClientFactory = SnowflakeClient,
) -> tuple[dict[str, int | float | list[str]], list[dict[str, Any]]]:
    """Run the independent SQL targets as the read-only role and retain evidence."""
    ground_truth: dict[str, int | float | list[str]] = {}
    evidence: list[dict[str, Any]] = []
    with client_factory() as client:
        for key, sql in TPCH_GROUND_TRUTH_SQL.items():
            result = client.run_query(sql)
            rows = result["rows"]
            if not rows:
                raise RuntimeError(
                    f"Ground-truth SQL for {key} returned no result rows."
                )
            if key in _LIST_TARGETS:
                value: int | float | list[str] = [str(row[0]) for row in rows]
            else:
                raw_value = rows[0][0]
                if raw_value is None:
                    raise RuntimeError(
                        f"Ground-truth SQL for {key} returned NULL."
                    )
                if isinstance(raw_value, Decimal):
                    value = float(raw_value)
                else:
                    value = int(raw_value) if isinstance(raw_value, int) else float(raw_value)
            ground_truth[key] = value
            evidence.append(
                {
                    "id": key,
                    "sql": sql,
                    "rows": rows,
                    "query_id": result["query_id"],
                }
            )
    return ground_truth, evidence
