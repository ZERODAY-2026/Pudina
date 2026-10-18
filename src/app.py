"""Accessible Streamlit chat interface for the DataMind question pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.config_loader import DatasetConfig, DatasetConfigError, load_dataset_config
from src.pipeline import AnswerResult, Pipeline


def available_configs(config_dir: str | Path = "config") -> list[Path]:
    """Return sorted dataset YAML files from the selected config directory."""
    return sorted(Path(config_dir).glob("*.yaml"))


def dataframe_for_result(result: AnswerResult) -> pd.DataFrame:
    """Convert an answer's result rows into a display-ready dataframe."""
    return pd.DataFrame(result.rows, columns=result.columns)


def render_answer_details(st: Any, result: AnswerResult) -> None:
    """Render answer evidence in labeled, collapsible sections."""
    with st.expander("How I got this"):
        st.write(result.explanation)
        st.markdown("**Assumptions**")
        if result.assumptions:
            for assumption in result.assumptions:
                st.markdown(f"- {assumption}")
        else:
            st.write("No additional assumptions.")
        for warning in result.warnings:
            st.warning(warning)

    with st.expander("SQL executed"):
        if result.sql:
            st.code(result.sql, language="sql")
        else:
            st.write("No SQL was executed.")

    with st.expander("Result rows"):
        if result.rows:
            st.dataframe(
                dataframe_for_result(result),
                use_container_width=True,
                hide_index=True,
            )
        elif result.status == "answerable":
            st.info("No rows matched the requested criteria.")
        else:
            st.write("No result rows are available.")

    with st.expander("Snowflake query ID"):
        if result.query_id:
            st.code(result.query_id)
        else:
            st.write("No Snowflake query was run.")


def render_assistant_message(st: Any, result: AnswerResult) -> None:
    """Display an answer or friendly status message and its evidence."""
    st.markdown(result.answer)
    if result.status == "unsupported":
        st.info("Try asking a read-only question about the configured dataset.")
    elif result.status == "ambiguous" and result.clarifying_question:
        st.info(result.clarifying_question)
    elif result.status == "error":
        st.warning(
            "I couldn't complete that data query. Please try rephrasing your "
            "question or check the service configuration."
        )
    render_answer_details(st, result)


def main() -> None:
    """Run the interactive chat app."""
    import streamlit as st

    st.set_page_config(page_title="DataMind", page_icon="📊", layout="wide")
    st.title("DataMind")
    st.caption("Ask questions about your data in plain English.")

    configs = available_configs()
    if not configs:
        st.error("No dataset configurations were found in the config folder.")
        return

    config_by_label = {path.stem: path for path in configs}
    labels = list(config_by_label)
    default_index = labels.index("dataset_a") if "dataset_a" in labels else 0
    selected_label = st.sidebar.selectbox(
        "Dataset configuration",
        labels,
        index=default_index,
        help="Select the dataset schema to use for questions.",
    )
    config_path = config_by_label[selected_label]

    try:
        config = load_dataset_config(config_path)
    except DatasetConfigError as exc:
        st.sidebar.error(f"Could not load dataset configuration: {exc}")
        return

    st.sidebar.subheader("Dataset")
    st.sidebar.write(config.dataset_name)
    st.sidebar.caption(config.description)
    st.sidebar.subheader("Example questions")
    examples = config.example_questions or _default_examples(config)
    selected_example: str | None = None
    for index, example in enumerate(examples):
        if st.sidebar.button(
            example,
            key=f"example_{selected_label}_{index}",
            use_container_width=True,
        ):
            selected_example = example

    state_config_key = "datamind_config_path"
    chat_messages_key = "datamind_chat_messages"
    history_key = "datamind_conversation_history"
    config_identity = str(config_path.resolve())
    if st.session_state.get(state_config_key) != config_identity:
        st.session_state[state_config_key] = config_identity
        st.session_state[chat_messages_key] = []
        st.session_state[history_key] = []

    for message in st.session_state[chat_messages_key]:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown(message["content"])
            else:
                render_assistant_message(st, message["result"])

    question = st.chat_input("Ask a question about this dataset")
    if selected_example:
        question = selected_example
    if not question:
        return

    st.session_state[chat_messages_key].append(
        {"role": "user", "content": question}
    )
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Checking the dataset and preparing an answer..."):
                result = Pipeline(config_path=config_path).ask(
                    question,
                    history=st.session_state[history_key],
                )
            render_assistant_message(st, result)
        except Exception as exc:
            result = AnswerResult(
                status="error",
                answer=(
                    "I couldn't complete that request. Check the Gemma and "
                    "Snowflake configuration, then try again."
                ),
                explanation="The request failed before a verified result was available.",
                warnings=[f"{type(exc).__name__}: {exc}"],
            )
            render_assistant_message(st, result)
            st.session_state[chat_messages_key].append(
                {
                    "role": "assistant",
                    "content": result.answer,
                    "result": result,
                }
            )
            return

    st.session_state[chat_messages_key].append(
        {"role": "assistant", "content": result.answer, "result": result}
    )
    st.session_state[history_key].append(
        {"question": question, "answer": result.answer}
    )
    st.session_state[history_key] = st.session_state[history_key][-6:]


def _default_examples(config: DatasetConfig) -> list[str]:
    """Offer schema-derived examples if a config has none yet."""
    examples: list[str] = []
    for table in config.tables:
        examples.append(f"How many rows are in {table.name}?")
        if len(examples) >= 5:
            break
    return examples


if __name__ == "__main__":
    main()
