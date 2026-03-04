"""
glossary_checker.py
Kişi 2 — Metadata Quality & Rule Engine
zenginleştirme ihtiyaçlarını glossary'e karşı kontrol eder.
    - Glossary'de varsa → glossary_found.json
    - Yoksa             → needs_llm.json  (Kişi 1'e gider)
"""

import json
import os

BASE_DIR      = os.path.join(os.path.dirname(__file__), "..")
OUTPUT_DIR    = os.path.join(BASE_DIR, "output")
GLOSSARY_PATH = os.path.join(BASE_DIR, "glossary", "glossary.json")


def _load_glossary() -> dict:
    """Glossary dosyasını yükler; yoksa veya boşsa boş dict döner."""
    try:
        with open(GLOSSARY_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def check_glossary(needs_path: str | None = None) -> tuple[list, list]:
    needs_path = needs_path or os.path.join(OUTPUT_DIR, "needs_enrichment.json")

    if not os.path.exists(needs_path):
        print("❌ needs_enrichment.json bulunamadı. Önce classifier.py çalıştırın.")
        return [], []

    with open(needs_path, "r", encoding="utf-8") as f:
        needs = json.load(f)

    glossary = _load_glossary()
    if not glossary:
        print("⚠️  Glossary boş veya bulunamadı — tüm öğeler LLM'e gidecek.\n")

    found_in_glossary = []
    needs_llm         = []

    print(f"📖 Glossary kontrolü ({len(needs)} öğe)...\n")
    for item in needs:
        if item["type"] == "column":
            col = item["column_name"]
            if col in glossary:
                enriched = {
                    **item,
                    "glossary_definition": glossary[col].get("definition", ""),
                    "glossary_source":     glossary[col].get("source", "")
                }
                found_in_glossary.append(enriched)
                print(f"  📖 {item['table_name']}.{col} → Glossary'de BULUNDU")
            else:
                needs_llm.append(item)
                print(f"  ❓ {item['table_name']}.{col} → Glossary'de YOK, LLM gerekli")

        elif item["type"] == "table":
            # Tablo açıklamaları için de glossary'ye bak
            tbl = item["table_name"]
            if tbl in glossary:
                found_in_glossary.append({
                    **item,
                    "glossary_definition": glossary[tbl].get("definition", "")
                })
                print(f"  📖 Tablo {tbl} → Glossary'de BULUNDU")
            else:
                needs_llm.append(item)
                print(f"  ❓ Tablo {tbl} → Glossary'de YOK, LLM gerekli")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    found_path = os.path.join(OUTPUT_DIR, "glossary_found.json")
    with open(found_path, "w", encoding="utf-8") as f:
        json.dump(found_in_glossary, f, ensure_ascii=False, indent=2)

    llm_path = os.path.join(OUTPUT_DIR, "needs_llm.json")
    with open(llm_path, "w", encoding="utf-8") as f:
        json.dump(needs_llm, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Glossary'de bulundu : {len(found_in_glossary)}")
    print(f"🤖 LLM zenginleştirme : {len(needs_llm)}")
    print(f"📄 → {found_path}")
    print(f"📄 → {llm_path}  (Kişi 1'e ilet)")

    return found_in_glossary, needs_llm


if __name__ == "__main__":
    check_glossary()
