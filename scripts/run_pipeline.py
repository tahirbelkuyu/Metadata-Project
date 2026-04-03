"""
run_pipeline.py
Kişi 2 — Metadata Quality & Rule Engine
Tüm pipeline adımlarını sırayla çalıştıran ana script.
Kullanım: python scripts/run_pipeline.py
"""

import os
import sys
import time

# scripts/ dizinini path'e ekle (modülleri bulabilmek için)
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR    = os.path.join(SCRIPTS_DIR, "..")
sys.path.insert(0, SCRIPTS_DIR)

def separator(title: str):
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")


def step(n: int, title: str, fn):
    separator(f"ADIM {n}: {title}")
    t0 = time.time()
    fn()
    elapsed = time.time() - t0
    print(f"  ⏱  {elapsed:.2f}s")


if __name__ == "__main__":
    os.chdir(BASE_DIR)  # Proje kök dizinine geç

    print("=" * 55)
    print("  🚀 Akbank Metadata Quality Pipeline")
    print("=" * 55)

    from metadata_extractor import extract_all_metadata
    from quality_engine     import run_engine
    from classifier         import classify_and_flag
    from lookup_checker     import check_lookups
    from glossary_checker   import check_glossary
    from llm_enricher       import enrich
    import json

    # ── Adım 0: Sentetik DDL + lineage (çok tablo/kolon) ─────
    def step0():
        from generate_synthetic_corpus import run as generate_synthetic_corpus
        generate_synthetic_corpus()

    # ── Adım 1: Metadata Çıkar ──────────────────────────────
    def step1():
        metadata = extract_all_metadata()
        os.makedirs("output", exist_ok=True)
        with open("output/metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"  → {len(metadata)} tablo → output/metadata.json")

    # ── Adım 2: Kalite Değerlendirme ────────────────────────
    def step2():
        run_engine()

    # ── Adım 3: Sınıflandır ─────────────────────────────────
    def step3():
        items = classify_and_flag()
        print(f"  → {len(items)} öğe zenginleştirmeye ihtiyaç duyuyor")

    # ── Adım 4: Lookup Kontrol ──────────────────────────────
    def step4():
        findings = check_lookups()
        bad = [f for f in findings if not f.get("valid")]
        print(f"  → {len(bad)} lookup sorunu bulundu")

    # ── Adım 5: Glossary Kontrol ────────────────────────────
    def step5():
        found, needs_llm = check_glossary()
        print(f"  → Glossary'de: {len(found)} | LLM'e gidecek: {len(needs_llm)}")
    # ── Adım 6: Metadata Enrichment ─────────────────────────
    def step6():
        enriched = enrich()
        print(f"  → {len(enriched)} öğe için otomatik açıklama üretildi")

    # ── Adım 7: SMOTE ile dengeli özellik örnekleri ─────────
    def step7():
        try:
            from smote_metadata import run_smote_and_export
            run_smote_and_export()
        except ImportError as e:
            print("  ⚠️  imbalanced-learn yok: pip install -r requirements.txt")
            print(f"     ({e})")

    # ── Adım 8: Lineage → Excel ─────────────────────────────
    def step8():
        try:
            from export_lineage_excel import export_excel
            export_excel()
        except ImportError as e:
            print("  ⚠️  pandas/openpyxl yok: pip install -r requirements.txt")
            print(f"     ({e})")

    step(0, "Şema + lineage + glossary + ETL/TOA dok.", step0)
    step(1, "Metadata Extraction (DDL → JSON)",      step1)
    step(2, "Quality Rule Engine",                    step2)
    step(3, "Classifier (GOOD / BAD İşaretleme)",    step3)
    step(4, "Lookup Bağlantı Kontrolü",              step4)
    step(5, "Glossary Kontrolü",                     step5)
    step(6, "Metadata Enrichment",                   step6)
    step(7, "SMOTE (dengeli sentetik kolon örnekleri)", step7)
    step(8, "Lineage → Excel export",                 step8)

    separator("✅ Pipeline Tamamlandı")
    print()
    print("  📁 Çıktı dosyaları (output/):")
    output_files = [
        ("metadata.json",         "Ham metadata"),
        ("quality_report.json",   "Kalite raporu"),
        ("needs_enrichment.json", "Zenginleştirme listesi"),
        ("lookup_check.json",     "Lookup kontrolü"),
        ("glossary_found.json",   "Glossary'den çekilenler"),
        ("needs_llm.json",        "LLM'e gidecekler (Kişi 1)"),
        ("enriched_metadata.json", "Otomatik üretilen metadata açıklamaları"),
        ("smote_features.csv",    "SMOTE dengeli özellik matrisi"),
        ("smote_balanced_samples.json", "SMOTE örnek listesi"),
        ("lineage_export.xlsx",   "Lineage Excel export"),
    ]
    for fname, desc in output_files:
        path = os.path.join("output", fname)
        exists = "✅" if os.path.exists(path) else "❌"
        print(f"  {exists}  {fname:30s}  ← {desc}")
    print()
