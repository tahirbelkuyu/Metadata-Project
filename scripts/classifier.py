"""
classifier.py
Kişi 2 — Metadata Quality & Rule Engine
Quality report'u okur; zenginleştirme gereken kolon/tabloları işaretler.
Çıktı: output/needs_enrichment.json
"""

import json
import os

BASE_DIR   = os.path.join(os.path.dirname(__file__), "..")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

GOOD_THRESHOLD = 0.75


def classify_and_flag(report_path: str | None = None) -> list[dict]:
    report_path = report_path or os.path.join(OUTPUT_DIR, "quality_report.json")

    if not os.path.exists(report_path):
        print("❌ quality_report.json bulunamadı. Önce quality_engine.py çalıştırın.")
        return []

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    needs_enrichment = []

    for table in report:
        # Tablo açıklaması eksikse kaydet
        tbl_desc_rule = next(
            (r for r in table.get("table_rule_details", [])
             if r["rule"] == "HAS_TABLE_DESCRIPTION"),
            None
        )
        if tbl_desc_rule and not tbl_desc_rule["passed"]:
            needs_enrichment.append({
                "type": "table",
                "table_name": table["table_name"],
                "layer": table.get("layer"),
                "overall_score": table["overall_score"],
                "reason": "table_description_missing"
            })

        # Kötü skora sahip kolonları kaydet
        for col in table.get("columns", []):
            if col.get("needs_enrichment"):
                needs_enrichment.append({
                    "type": "column",
                    "table_name": table["table_name"],
                    "column_name": col["column_name"],
                    "score": col["score"],
                    "classification": col["classification"],
                    "failed_rules": col.get("failed_rules", [])
                })

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "needs_enrichment.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(needs_enrichment, f, ensure_ascii=False, indent=2)

    # Özet yazdır
    tables_flagged  = sum(1 for x in needs_enrichment if x["type"] == "table")
    columns_flagged = sum(1 for x in needs_enrichment if x["type"] == "column")
    print(f"🔍 Zenginleştirmeye ihtiyaç duyulan:")
    print(f"   📋 Tablo açıklaması: {tables_flagged}")
    print(f"   🏷️  Kolon açıklaması: {columns_flagged}")
    print(f"📄 → {out_path}")

    return needs_enrichment


if __name__ == "__main__":
    classify_and_flag()
