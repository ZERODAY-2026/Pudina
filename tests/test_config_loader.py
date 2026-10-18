"""Tests for dataset configuration loading and schema prompt rendering."""

from pathlib import Path

import yaml

from src.config_loader import build_schema_prompt, load_dataset_config


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DATASET_CONFIG = REPOSITORY_ROOT / "config" / "dataset_a.yaml"


def test_dataset_config_loads_and_validates() -> None:
    """Load the Bank Marketing config and check dataset/table metadata."""
    config = load_dataset_config(DATASET_CONFIG)

    assert config.dataset_name == "UCI Bank Marketing"
    assert len(config.tables) == 1
    assert config.tables[0].name == "BANK_MARKETING"
    assert len(config.tables[0].columns) == 17
    assert all(3 <= len(column.sample_values) <= 5 for column in config.tables[0].columns)


def test_schema_prompt_contains_every_table_and_column() -> None:
    """Include all configured tables, columns, sample values, and notes."""
    config = load_dataset_config(DATASET_CONFIG)
    prompt = build_schema_prompt(DATASET_CONFIG)

    for table in config.tables:
        assert table.name in prompt
        for column in table.columns:
            assert column.name in prompt
            assert column.description in prompt
            for sample in column.sample_values:
                formatted_sample = repr(sample) if isinstance(sample, str) else str(sample)
                assert formatted_sample in prompt
    assert "pdays uses 999" in prompt


def test_switching_config_path_changes_schema_text(tmp_path: Path) -> None:
    """Render another schema by changing only the supplied config path."""
    alternate_config = {
        "dataset_name": "Alternate dataset",
        "description": "A separate schema used to verify config-driven prompts.",
        "tables": [
            {
                "name": "ALT_TABLE",
                "description": "Alternate table description.",
                "columns": [
                    {
                        "name": "alt_value",
                        "type": "VARCHAR",
                        "description": "An alternate value.",
                        "sample_values": ["example"],
                        "nullable": True,
                    }
                ],
            }
        ],
        "joins": [],
        "notes": [],
    }
    alternate_path = tmp_path / "alternate.yaml"
    alternate_path.write_text(
        yaml.safe_dump(alternate_config, sort_keys=False), encoding="utf-8"
    )

    prompt = build_schema_prompt(alternate_path)

    assert "Alternate dataset" in prompt
    assert "ALT_TABLE" in prompt
    assert "alt_value" in prompt
    assert "BANK_MARKETING" not in prompt
