"""
quality_engine.py
Kişi 2 — Metadata Quality & Rule Engine
quality_rules.py'deki kuralları her tabloya/kolona uygular.
Çıktı: output/quality_report.json
"""

import json
import os
import sys

# Aynı dizinden import
sys.path.insert(0, os.path.dirname(__file__))
from quality_rules import (
    COLUMN_RULES, TABLE_RULES,
    rule_has_description, rule_description_min_length,
    rule_data_type_valid, rule_no_reserved_words,
    rule_lookup_valid,
    rule_table_has_description, rule_table_has_columns,
)

BASE_DIR   = os.path.join(os.path.dirname(__file__), "..")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

AVAILABLE_LOOKUPS = ["LKP_MUSTERI_TIP", "LKP_KREDI_TIP"]

GOOD_THRESHOLD = 0.75  # >= 0.75 → GOOD


# ─── Kolon Değerlendirme ────────────────────────────────────────────────────

def evaluate_column(column: dict) -> dict:
    """Bir kolona tüm kolon kurallarını uygular, skor döner."""
    rule_results = []
    total_weight = 0.0
    passed_weight = 0.0

    for rule_id, (fn, weight) in COLUMN_RULES.items():
        if rule_id == "LOOKUP_VALID":
            applies, passed = rule_lookup_valid(column, AVAILABLE_LOOKUPS)
            if not applies:
                continue  # Bu kolona uygulanmaz, atla
        else:
            passed = fn(column)

        total_weight   += weight
        passed_weight  += weight if passed else 0.0
        rule_results.append({
            "rule": rule_id,
            "passed": passed,
            "weight": weight
        })

    score = round(passed_weight / total_weight, 3) if total_weight > 0 else 0.0
    return {
        "column_name": column["column_name"],
        "score": score,
        "classification": "GOOD" if score >= GOOD_THRESHOLD else "BAD",
        "needs_enrichment": score < GOOD_THRESHOLD,
        "failed_rules": [r["rule"] for r in rule_results if not r["passed"]],
        "rule_details": rule_results
    }


# ─── Tablo Değerlendirme ─────────────────────────────────────────────────────

def evaluate_table(table: dict) -> dict:
    """Bir tabloya tüm tablo + kolon kurallarını uygular."""
    # Tablo seviyesi kurallar
    tbl_results = []
    tbl_total_w  = 0.0
    tbl_passed_w = 0.0
    for rule_id, (fn, weight) in TABLE_RULES.items():
        passed = fn(table)
        tbl_total_w   += weight
        tbl_passed_w  += weight if passed else 0.0
        tbl_results.append({"rule": rule_id, "passed": passed, "weight": weight})

    tbl_score = round(tbl_passed_w / tbl_total_w, 3) if tbl_total_w > 0 else 0.0

    # Kolon seviyesi değerlendirme
    col_evals = [evaluate_column(col) for col in table.get("columns", [])]
    avg_col_score = (
        sum(c["score"] for c in col_evals) / len(col_evals)
        if col_evals else 0.0
    )

    # Genel skor: %40 tablo + %60 kolon ortalaması
    overall = round(0.4 * tbl_score + 0.6 * avg_col_score, 3)

    return {
        "table_name": table["table_name"],
        "layer": table.get("layer", "UNKNOWN"),
        "overall_score": overall,
        "table_score": tbl_score,
        "avg_column_score": round(avg_col_score, 3),
        "classification": "GOOD" if overall >= GOOD_THRESHOLD else "BAD",
        "table_rule_details": tbl_results,
        "columns": col_evals
    }


# ─── Ana Çalıştırıcı ─────────────────────────────────────────────────────────

def run_engine():
    metadata_path = os.path.join(OUTPUT_DIR, "metadata.json")
    if not os.path.exists(metadata_path):
        print("❌ output/metadata.json bulunamadı. Önce metadata_extractor.py çalıştırın.")
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print("📊 Kalite değerlendirmesi başlıyor...\n")
    report = []
    good_count = 0
    bad_count  = 0

    for table in metadata:
        result = evaluate_table(table)
        report.append(result)
        icon = "✅" if result["classification"] == "GOOD" else "❌"
        print(f"  {icon} [{result['layer']:15s}] {result['table_name']:30s} | Skor: {result['overall_score']:.2f}")
        if result["classification"] == "GOOD":
            good_count += 1
        else:
            bad_count += 1

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(OUTPUT_DIR, "quality_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ GOOD: {good_count} | ❌ BAD: {bad_count}")
    print(f"📄 Rapor → {report_path}")


if __name__ == "__main__":
    run_engine()
