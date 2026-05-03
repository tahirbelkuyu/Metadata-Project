import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

METADATA_PATH = BASE_DIR / "output" / "metadata.json"
BENCHMARK_PATH = Path(__file__).resolve().parent / "benchmark_quality.csv"
OUTPUT_PATH = Path(__file__).resolve().parent / "ablation_quality_results.csv"

GOOD_THRESHOLD = 0.75
AVAILABLE_LOOKUPS = ["LKP_MUSTERI_TIP", "LKP_KREDI_TIP"]


def load_metadata():
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_benchmark():
    return pd.read_csv(BENCHMARK_PATH, sep=None, engine="python")


def has_description(col):
    return bool(col.get("description", "").strip())


def description_min_length(col, min_len=15):
    return len(col.get("description", "").strip()) >= min_len


def data_type_valid(col):
    valid_types = {
        "INT", "INTEGER", "BIGINT", "SMALLINT",
        "VARCHAR", "CHAR", "TEXT", "NVARCHAR",
        "DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL",
        "DATE", "DATETIME", "TIMESTAMP",
        "BOOLEAN", "BIT"
    }
    dtype = col.get("data_type", "").upper().split("(")[0].strip()
    return dtype in valid_types


def no_reserved_words(col):
    reserved = {"SELECT", "FROM", "WHERE", "TABLE", "INDEX", "ORDER", "GROUP", "KEY"}
    return col.get("column_name", "").upper() not in reserved


def lookup_valid(col):
    name = col.get("column_name", "").upper()
    applies = name.endswith("_ID") or name.endswith("_TIP")
    if not applies:
        return None
    return col.get("lookup_table") in AVAILABLE_LOOKUPS


def evaluate_column(col, table, active_rules):
    # Intentionally bad / temporary test table
    if table.get("layer") == "TEMP" or table.get("table_name", "").startswith("TMP_"):
        return "BAD"

    # Missing metadata should be separated from low-quality metadata
    if not has_description(col):
        return "UNKNOWN"

    rule_functions = {
        "HAS_DESCRIPTION": has_description,
        "DESCRIPTION_MIN_LENGTH": description_min_length,
        "DATA_TYPE_VALID": data_type_valid,
        "NO_RESERVED_WORDS": no_reserved_words,
        "LOOKUP_VALID": lookup_valid,
    }

    weights = {
        "HAS_DESCRIPTION": 0.20,
        "DESCRIPTION_MIN_LENGTH": 0.10,
        "DATA_TYPE_VALID": 0.20,
        "NO_RESERVED_WORDS": 0.10,
        "LOOKUP_VALID": 0.40,
    }

    total_weight = 0.0
    passed_weight = 0.0

    for rule in active_rules:
        result = rule_functions[rule](col)

        # LOOKUP_VALID may not apply to every column
        if result is None:
            continue

        total_weight += weights[rule]
        if result:
            passed_weight += weights[rule]

    if total_weight == 0:
        return "UNKNOWN"

    score = passed_weight / total_weight
    return "GOOD" if score >= GOOD_THRESHOLD else "BAD"


def run_model(metadata, active_rules, model_name):
    rows = []

    for table in metadata:
        for col in table.get("columns", []):
            pred = evaluate_column(col, table, active_rules)
            rows.append({
                "model": model_name,
                "table_name": table["table_name"],
                "column_name": col["column_name"],
                "predicted": pred
            })

    return pd.DataFrame(rows)


def calculate_accuracy(pred_df, benchmark):
    merged = benchmark.merge(
        pred_df,
        on=["table_name", "column_name"],
        how="left"
    )

    correct = (merged["true_label"] == merged["predicted"]).sum()
    total = len(merged)

    return correct / total if total > 0 else 0


def main():
    metadata = load_metadata()
    benchmark = load_benchmark()

    models = {
        "full_model": [
            "HAS_DESCRIPTION",
            "DESCRIPTION_MIN_LENGTH",
            "DATA_TYPE_VALID",
            "NO_RESERVED_WORDS",
            "LOOKUP_VALID",
        ],
        "without_lookup": [
            "HAS_DESCRIPTION",
            "DESCRIPTION_MIN_LENGTH",
            "DATA_TYPE_VALID",
            "NO_RESERVED_WORDS",
        ],
        "without_description_length": [
            "HAS_DESCRIPTION",
            "DATA_TYPE_VALID",
            "NO_RESERVED_WORDS",
            "LOOKUP_VALID",
        ],
        "structural_only": [
            "DATA_TYPE_VALID",
            "NO_RESERVED_WORDS",
            "LOOKUP_VALID",
        ],
    }

    results = []

    for model_name, active_rules in models.items():
        pred_df = run_model(metadata, active_rules, model_name)
        accuracy = calculate_accuracy(pred_df, benchmark)

        results.append({
            "model": model_name,
            "active_rules": ", ".join(active_rules),
            "accuracy": round(accuracy, 3)
        })

    result_df = pd.DataFrame(results)
    result_df.to_csv(OUTPUT_PATH, index=False)

    print("\nAblation Study Results")
    print(result_df)
    print(f"\nSaved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()