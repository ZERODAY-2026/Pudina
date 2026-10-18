"""Validate model-generated SQL against read-only and dataset-scope rules."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping

from sqlglot import exp, parse, parse_one
from sqlglot.errors import ParseError


class SQLValidationError(ValueError):
    """Raised when SQL is invalid, unsafe, or outside the dataset scope."""


def repair_unconfigured_columns(
    sql: str,
    column_allowlist: Mapping[str, Iterable[str]],
) -> str:
    """Correct a uniquely identifiable schema-column suffix hallucination."""
    try:
        statement = parse_one(sql, read="snowflake")
    except ParseError as exc:
        raise SQLValidationError(f"Invalid Snowflake SQL: {exc}") from exc
    if not isinstance(statement, exp.Query):
        return sql

    columns_by_table = {
        _normalize_identifier(table): {column.casefold(): column for column in columns}
        for table, columns in column_allowlist.items()
    }
    tables_by_alias = {
        table.alias_or_name.casefold(): _table_name(table)
        for table in statement.find_all(exp.Table)
    }

    for column in statement.find_all(exp.Column):
        table_name = tables_by_alias.get(column.table.casefold())
        configured_columns = columns_by_table.get(table_name or "")
        if configured_columns is None or column.name.casefold() in configured_columns:
            continue
        invalid_suffix = column.name.casefold().rsplit("_", maxsplit=1)[-1]
        candidates = [
            configured_name
            for configured_name in configured_columns
            if len(configured_name.rsplit("_", maxsplit=1)[-1]) >= 4
            and invalid_suffix.endswith(
                configured_name.rsplit("_", maxsplit=1)[-1]
            )
        ]
        if len(candidates) == 1:
            column.set(
                "this",
                exp.to_identifier(
                    configured_columns[candidates[0]],
                    quoted=bool(column.this.args.get("quoted")),
                ),
            )

    return statement.sql(dialect="snowflake")


def repair_unconfigured_join_paths(
    sql: str,
    join_relationships: Iterable[tuple[str, str, str, str]],
) -> str:
    """Replace a guessed direct join with its configured relationship path."""
    relationships = tuple(join_relationships)
    try:
        statement = parse_one(sql, read="snowflake")
    except ParseError as exc:
        raise SQLValidationError(f"Invalid Snowflake SQL: {exc}") from exc
    if not isinstance(statement, exp.Query):
        return sql

    for _ in range(len(relationships) + 1):
        from_clause = statement.args.get("from")
        base_table = from_clause.this if from_clause is not None else None
        if not isinstance(base_table, exp.Table):
            break
        joins = list(statement.args.get("joins") or [])
        table_by_alias = {
            base_table.alias_or_name.casefold(): _table_name(base_table)
        }
        changed = False

        for index, join in enumerate(joins):
            target = join.this
            on_clause = join.args.get("on")
            if not isinstance(target, exp.Table) or on_clause is None:
                if isinstance(target, exp.Table):
                    table_by_alias[target.alias_or_name.casefold()] = _table_name(target)
                continue

            equalities = list(on_clause.find_all(exp.EQ))
            if len(equalities) != 1:
                table_by_alias[target.alias_or_name.casefold()] = _table_name(target)
                continue
            columns = list(equalities[0].find_all(exp.Column))
            if len(columns) != 2:
                table_by_alias[target.alias_or_name.casefold()] = _table_name(target)
                continue

            target_alias = target.alias_or_name.casefold()
            if columns[0].table.casefold() == target_alias:
                start_column, target_column = columns[1], columns[0]
            elif columns[1].table.casefold() == target_alias:
                start_column, target_column = columns[0], columns[1]
            else:
                table_by_alias[target_alias] = _table_name(target)
                continue
            start_alias = start_column.table.casefold()
            start_table = table_by_alias.get(start_alias)
            target_table = _table_name(target)
            if start_table is None:
                table_by_alias[target_alias] = target_table
                continue
            if join.args.get("side") or join.args.get("kind"):
                table_by_alias[target_alias] = target_table
                continue

            path = _relationship_path(start_table, target_table, relationships)
            if not path or _relationship_matches(
                start_table,
                start_column.name,
                target_table,
                target_column.name,
                relationships,
            ):
                table_by_alias[target_alias] = target_table
                continue
            if any(
                _normalize_identifier(step[2]) in table_by_alias.values()
                for step in path[:-1]
            ):
                table_by_alias[target_alias] = target_table
                continue

            used_aliases = {
                table.alias_or_name.casefold()
                for table in statement.find_all(exp.Table)
            }
            current_alias = start_alias
            replacement_joins: list[exp.Join] = []
            for path_index, (_, current_column, next_table, next_column) in enumerate(path):
                is_final = path_index == len(path) - 1
                next_alias = (
                    target_alias
                    if is_final
                    else _new_join_alias(used_aliases, path_index + 1)
                )
                if is_final:
                    next_table_node = target.copy()
                else:
                    next_table_node = _configured_table(next_table, relationships)
                    next_table_node.set(
                        "alias",
                        exp.TableAlias(this=exp.to_identifier(next_alias)),
                    )
                on = exp.EQ(
                    this=exp.column(current_column, table=current_alias),
                    expression=exp.column(next_column, table=next_alias),
                )
                if is_final:
                    replacement = join.copy()
                    replacement.set("on", on)
                else:
                    replacement = exp.Join(this=next_table_node, on=on)
                replacement_joins.append(replacement)
                current_alias = next_alias

            statement.set(
                "joins",
                joins[:index] + replacement_joins + joins[index + 1 :],
            )
            changed = True
            break

        if not changed:
            break

    return statement.sql(dialect="snowflake")


def validate_read_only_sql(
    sql: str,
    table_allowlist: Iterable[str] | None = None,
    max_limit: int | None = 500,
    join_allowlist: Iterable[tuple[str, str, str, str]] | None = None,
) -> str:
    """Validate exactly one SELECT, enforce table scope, and cap result rows."""
    if not sql.strip():
        raise SQLValidationError("SQL query must not be empty.")
    if max_limit is not None and max_limit < 1:
        raise ValueError("max_limit must be a positive integer or None.")

    try:
        statements = [
            statement
            for statement in parse(sql, read="snowflake")
            if statement is not None
        ]
    except ParseError as exc:
        raise SQLValidationError(f"Invalid Snowflake SQL: {exc}") from exc

    if len(statements) != 1:
        raise SQLValidationError("Exactly one SQL statement is allowed.")
    statement = statements[0]
    if not isinstance(statement, exp.Query) or not statement.find(exp.Select):
        raise SQLValidationError("Only a SELECT or WITH...SELECT query is allowed.")
    if statement.find(exp.Into):
        raise SQLValidationError("SELECT INTO is not allowed.")

    if table_allowlist is not None:
        _validate_tables(statement, table_allowlist)
    if join_allowlist is not None:
        _validate_joins(statement, join_allowlist)

    if max_limit is not None:
        _apply_limit(statement, max_limit)
    return statement.sql(dialect="snowflake")


def configured_max_limit() -> int:
    """Read the positive SQL row cap from SQL_GUARD_MAX_LIMIT (default 500)."""
    raw_limit = os.getenv("SQL_GUARD_MAX_LIMIT", "500").strip()
    try:
        limit = int(raw_limit)
    except ValueError as exc:
        raise ValueError("SQL_GUARD_MAX_LIMIT must be a positive integer.") from exc
    if limit < 1:
        raise ValueError("SQL_GUARD_MAX_LIMIT must be a positive integer.")
    return limit


def _validate_tables(statement: exp.Query, table_allowlist: Iterable[str]) -> None:
    """Reject table references not explicitly present in the allowlist."""
    allowed = {_normalize_identifier(name) for name in table_allowlist}
    if not allowed:
        raise SQLValidationError("The configured table allowlist is empty.")

    cte_names = {
        cte.alias_or_name.casefold()
        for cte in statement.find_all(exp.CTE)
        if cte.alias_or_name
    }
    for table in statement.find_all(exp.Table):
        if not any((table.catalog, table.db)) and table.name.casefold() in cte_names:
            continue
        qualified_name = ".".join(
            part.casefold()
            for part in (table.catalog, table.db, table.name)
            if part
        )
        if qualified_name not in allowed:
            raise SQLValidationError(
                f"Table '{qualified_name}' is not in the configured dataset allowlist."
            )


def _normalize_identifier(identifier: str) -> str:
    """Normalize a Snowflake identifier for case-insensitive allowlist matching."""
    return ".".join(
        part.strip().strip('"').casefold() for part in identifier.split(".")
    )


def _table_name(table: exp.Table) -> str:
    """Return a normalized fully qualified name for a parsed SQL table."""
    return _normalize_identifier(
        ".".join(part for part in (table.catalog, table.db, table.name) if part)
    )


def _relationship_matches(
    left_table: str,
    left_column: str,
    right_table: str,
    right_column: str,
    relationships: tuple[tuple[str, str, str, str], ...],
) -> bool:
    """Check a column equality against either orientation of configured keys."""
    for configured_left, configured_left_column, configured_right, configured_right_column in relationships:
        direct = (
            _normalize_identifier(configured_left),
            configured_left_column.casefold(),
            _normalize_identifier(configured_right),
            configured_right_column.casefold(),
        )
        if (
            direct
            == (left_table, left_column.casefold(), right_table, right_column.casefold())
            or direct
            == (right_table, right_column.casefold(), left_table, left_column.casefold())
        ):
            return True
    return False


def _relationship_path(
    start_table: str,
    target_table: str,
    relationships: tuple[tuple[str, str, str, str], ...],
) -> list[tuple[str, str, str, str]] | None:
    """Find a shortest configured path between two normalized table names."""
    original_names: dict[str, str] = {}
    adjacency: dict[str, list[tuple[str, str, str]]] = {}
    for left_table, left_column, right_table, right_column in relationships:
        left = _normalize_identifier(left_table)
        right = _normalize_identifier(right_table)
        original_names[left] = left_table
        original_names[right] = right_table
        adjacency.setdefault(left, []).append((right, left_column, right_column))
        adjacency.setdefault(right, []).append((left, right_column, left_column))

    queue: list[tuple[str, list[tuple[str, str, str, str]]]] = [(start_table, [])]
    visited = {start_table}
    for current, path in queue:
        if current == target_table:
            return path
        for neighbor, current_column, neighbor_column in adjacency.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(
                    (
                        neighbor,
                        path
                        + [
                            (
                                original_names[current],
                                current_column,
                                original_names[neighbor],
                                neighbor_column,
                            )
                        ],
                    )
                )
    return None


def _configured_table(
    normalized_name: str,
    relationships: tuple[tuple[str, str, str, str], ...],
) -> exp.Table:
    """Create a fully qualified SQL table node from configured metadata."""
    normalized_name = _normalize_identifier(normalized_name)
    table_name = next(
        table
        for relationship in relationships
        for table in (relationship[0], relationship[2])
        if _normalize_identifier(table) == normalized_name
    )
    parts = table_name.split(".")
    return exp.Table(
        this=exp.to_identifier(parts[-1]),
        db=exp.to_identifier(parts[-2]) if len(parts) >= 2 else None,
        catalog=exp.to_identifier(parts[-3]) if len(parts) >= 3 else None,
    )


def _new_join_alias(used_aliases: set[str], index: int) -> str:
    """Choose a deterministic alias not used by the generated SQL."""
    alias = f"_DM_JOIN_{index}"
    while alias.casefold() in used_aliases:
        index += 1
        alias = f"_DM_JOIN_{index}"
    used_aliases.add(alias.casefold())
    return alias


def _validate_joins(
    statement: exp.Query,
    join_allowlist: Iterable[tuple[str, str, str, str]],
) -> None:
    """Reject cross-table equality joins not declared in dataset metadata."""
    relationships = tuple(join_allowlist)
    allowed = {
        frozenset(
            (
                (_normalize_identifier(left_table), left_column.casefold()),
                (_normalize_identifier(right_table), right_column.casefold()),
            )
        )
        for left_table, left_column, right_table, right_column in relationships
    }
    table_names = {
        table.alias_or_name.casefold(): _normalize_identifier(
            ".".join(part for part in (table.catalog, table.db, table.name) if part)
        )
        for table in statement.find_all(exp.Table)
        if table.name
    }

    for join in statement.find_all(exp.Join):
        on_clause = join.args.get("on")
        if on_clause is None:
            continue
        for equality in on_clause.find_all(exp.EQ):
            columns = [
                column
                for column in equality.find_all(exp.Column)
                if column.table.casefold() in table_names
            ]
            if len(columns) != 2 or columns[0].table.casefold() == columns[1].table.casefold():
                continue
            left = (
                table_names[columns[0].table.casefold()],
                columns[0].name.casefold(),
            )
            right = (
                table_names[columns[1].table.casefold()],
                columns[1].name.casefold(),
            )
            if frozenset((left, right)) not in allowed:
                left_table, right_table = left[0], right[0]
                matching_relationships = [
                    f"{configured_left_table}.{configured_left_column} = "
                    f"{configured_right_table}.{configured_right_column}"
                    for (
                        configured_left_table,
                        configured_left_column,
                        configured_right_table,
                        configured_right_column,
                    ) in relationships
                    if {
                        _normalize_identifier(configured_left_table),
                        _normalize_identifier(configured_right_table),
                    }
                    == {left_table, right_table}
                ]
                allowed_text = (
                    "; configured relationship(s): "
                    + ", ".join(matching_relationships)
                    if matching_relationships
                    else "; no configured relationship directly connects these tables"
                )
                raise SQLValidationError(
                    f"Join condition '{equality.sql(dialect='snowflake')}' is not "
                    f"a configured relationship{allowed_text}."
                )


def _apply_limit(statement: exp.Query, max_limit: int) -> None:
    """Add LIMIT or reduce a larger/non-literal LIMIT to the configured cap."""
    if isinstance(statement, exp.Select) and statement.args.get("group") is None:
        for projection in statement.expressions:
            if (
                projection.find(exp.AggFunc) is not None
                and projection.find(exp.Subquery) is None
                and projection.find(exp.Window) is None
            ):
                statement.set("limit", None)
                return

    limit_node = statement.args.get("limit")
    if limit_node is None:
        statement.set("limit", exp.Limit(expression=exp.Literal.number(max_limit)))
        return

    limit_value = limit_node.args.get("expression")
    if not isinstance(limit_value, exp.Literal) or not limit_value.is_int:
        limit_node.set("expression", exp.Literal.number(max_limit))
        return

    if int(limit_value.this) > max_limit:
        limit_node.set("expression", exp.Literal.number(max_limit))
