"""
Metadata Enrichment Module

Purpose:
Pipeline'da eksik metadata aciklamalarini otomatik uretmek.

Why:
Mevcut sistem sadece eksikleri tespit ediyor (detect),
ama tamamlamiyor. Bu modul enrichment ekler.
"""

import json
import os

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")


def generate_description(item: dict) -> str:
    """
    Eksik metadata icin otomatik aciklama uretir.
    Ileride bu kisim LLM ile degistirilebilir.
    """
    item_type = item.get("type", "column")

    if item_type == "table":
        table_name = item.get("table_name", "UNKNOWN_TABLE")
        layer = item.get("layer", "UNKNOWN_LAYER")
        return (
            f"{table_name} tablosu, {layer.lower()} katmaninda "
            f"metadata ile ilgili verileri tutar."
        )

    table_name = item.get("table_name", "UNKNOWN_TABLE")
    column_name = item.get("column_name", "UNKNOWN_COLUMN")
    readable_name = column_name.lower().replace("_", " ")

    return (
        f"{table_name} tablosundaki {readable_name} kolonu, "
        f"bankacilik sisteminde ilgili bilgiyi temsil eder."
    )


def enrich(needs_llm_path: str | None = None) -> list[dict]:
    """
    needs_llm.json dosyasini okuyup aciklama uretir
    ve enriched_metadata.json olarak kaydeder.
    """
    needs_llm_path = needs_llm_path or os.path.join(OUTPUT_DIR, "needs_llm.json")

    if not os.path.exists(needs_llm_path):
        print("needs_llm.json bulunamadi. Once pipeline calistirilmali.")
        return []

    with open(needs_llm_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    enriched_items = []

    for item in items:
        enriched_item = {
            **item,
            "generated_description": generate_description(item),
            "enrichment_method": "template_based",
        }
        enriched_items.append(enriched_item)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "enriched_metadata.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(enriched_items, f, ensure_ascii=False, indent=2)

    print(f"{len(enriched_items)} kayit icin aciklama uretildi.")
    print(f"Cikti dosyasi: {out_path}")

    return enriched_items