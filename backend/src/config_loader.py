"""Load, validate, and format dataset schemas for language-model prompts."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class DatasetConfigError(ValueError):
    """Raised when a dataset YAML file cannot be loaded or validated."""


class SchemaModel(BaseModel):
    """Base class that rejects unexpected schema configuration fields."""

    model_config = ConfigDict(extra="forbid")


class ColumnConfig(SchemaModel):
    """Configuration for one column in a dataset table."""

    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    sample_values: list[str | int | float | bool | None] = Field(
        default_factory=list, max_length=5
    )
    nullable: bool


class TableConfig(SchemaModel):
    """Configuration for one dataset table."""

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    columns: list[ColumnConfig] = Field(min_length=1)


class JoinConfig(SchemaModel):
    """A join relationship between two configured table columns."""

    left_table: str = Field(min_length=1)
    left_column: str = Field(min_length=1)
    right_table: str = Field(min_length=1)
    right_column: str = Field(min_length=1)


class DatasetConfig(SchemaModel):
    """Validated dataset schema and domain notes."""

    dataset_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    tables: list[TableConfig] = Field(min_length=1)
    joins: list[JoinConfig] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    example_questions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_table_references(self) -> DatasetConfig:
        """Ensure table and column names are unique and every join is resolvable."""
        tables_by_name = {table.name: table for table in self.tables}
        if len(tables_by_name) != len(self.tables):
            raise ValueError("Table names must be unique.")

        for table in self.tables:
            column_names = [column.name for column in table.columns]
            if len(set(column_names)) != len(column_names):
                raise ValueError(f"Column names must be unique in table '{table.name}'.")

        for join in self.joins:
            left_table = tables_by_name.get(join.left_table)
            right_table = tables_by_name.get(join.right_table)
            if left_table is None or right_table is None:
                raise ValueError(
                    "Join references an unknown table: "
                    f"{join.left_table}.{join.left_column} = "
                    f"{join.right_table}.{join.right_column}."
                )
            left_columns = {column.name for column in left_table.columns}
            right_columns = {column.name for column in right_table.columns}
            if (
                join.left_column not in left_columns
                or join.right_column not in right_columns
            ):
                raise ValueError(
                    "Join references an unknown column: "
                    f"{join.left_table}.{join.left_column} = "
                    f"{join.right_table}.{join.right_column}."
                )
        return self


def load_dataset_config(config_path: str | Path) -> DatasetConfig:
    """Load and validate a dataset YAML file."""
    path = Path(config_path)
    try:
        with path.open(encoding="utf-8") as config_file:
            raw_config = yaml.safe_load(config_file)
    except OSError as exc:
        raise DatasetConfigError(f"Could not read dataset config '{path}': {exc}") from exc
    except yaml.YAMLError as exc:
        raise DatasetConfigError(f"Invalid YAML in dataset config '{path}': {exc}") from exc

    try:
        return DatasetConfig.model_validate(raw_config)
    except ValidationError as exc:
        raise DatasetConfigError(
            f"Invalid dataset config '{path}': {exc}"
        ) from exc


def build_schema_prompt(config_path: str | Path) -> str:
    """Build a compact prompt description from a dataset YAML path."""
    config = load_dataset_config(config_path)
    lines = [
        f"Dataset: {config.dataset_name}",
        f"Description: {config.description}",
        "Use the exact configured table names below, including database and "
        "schema qualifiers when present.",
        "Tables:",
    ]
    for table in config.tables:
        lines.append(f"- {table.name}: {table.description}")
        for column in table.columns:
            samples = ", ".join(
                _format_sample(value) for value in column.sample_values
            )
            details = [
                f"type={column.type}",
                f"nullable={'yes' if column.nullable else 'no'}",
                f"description={column.description}",
            ]
            if samples:
                details.append(f"examples=[{samples}]")
            lines.append(f"  - {column.name} ({'; '.join(details)})")

    lines.append("Join keys:")
    if config.joins:
        for join in config.joins:
            lines.append(
                f"- {join.left_table}.{join.left_column} = "
                f"{join.right_table}.{join.right_column}"
            )
    else:
        lines.append("- None")

    if config.notes:
        lines.append("Known quirks and notes:")
        lines.extend(f"- {note}" for note in config.notes)

    return "\n".join(lines)


def _format_sample(value: str | int | float | bool | None) -> str:
    """Format a sample value unambiguously for the schema prompt."""
    if value is None:
        return "null"
    if isinstance(value, str):
        return repr(value)
    return str(value)
