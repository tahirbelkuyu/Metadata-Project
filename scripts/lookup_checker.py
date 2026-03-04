"""
lookup_checker.py
Kişi 2 — Metadata Quality & Rule Engine
_ID veya _TIP ile biten kolonların gerçek lookup tablosuna bağlı olup olmadığını doğrular.
Çıktı: output/lookup_check.json
"""

import json
import os

BASE_DIR   = os.path.join(os.path.dirname(__file__), "..")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Bilinen kolon → lookup eşlemesi (Faz 0'da ekiple genişletilmeli)
KNOWN_LOOKUP_MAP: dict[str, str | None] = {
    "MUSTERI_TIP_ID": "LKP_MUSTERI_TIP",
    "KREDI_TIP_ID":   "LKP_KREDI_TIP",
    "AKTIF_FLAG":     None,   # Lookup yok — sadece 0/1 flag
    "ISLEM_TIP":      None,   # Serbest metin, lookup yok
}

AVAILABLE_LOOKUPS = list(set(v for v in KNOWN_LOOKUP_MAP.values() if v))

TRIGGER_SUFFIXES = ("_ID", "_TIP", "_FLAG")


def should_have_lookup(col_name: str) -> bool:
    """Kolon adı lookup gerektirir mi?"""
    upper = col_name.upper()
    return any(upper.endswith(s) for s in TRIGGER_SUFFIXES)


def check_lookups(metadata_path: str | None = None) -> list[dict]:
    metadata_path = metadata_path or os.path.join(OUTPUT_DIR, "metadata.json")

    if not os.path.exists(metadata_path):
        print("❌ output/metadata.json bulunamadı.")
        return []

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    findings = []
    issues   = 0

    print("🔗 Lookup bağlantıları kontrol ediliyor...\n")
    for table in metadata:
        for col in table.get("columns", []):
            col_name = col["column_name"]
            if not should_have_lookup(col_name):
                continue

            expected = KNOWN_LOOKUP_MAP.get(col_name, "UNKNOWN")
            actual   = col.get("lookup_table")

            if expected == "UNKNOWN":
                status = "⚠️  TANIM_YOK"   # Haritada tanımlı değil
            elif expected is None and actual is None:
                status = "✅ LOOKUP_YOK"    # Beklenen bu
            elif expected == actual:
                status = "✅ GEÇERLI"
            else:
                status = "❌ EŞLEŞMİYOR"
                issues += 1

            valid = status.startswith("✅")
            print(f"  {status} | {table['table_name']}.{col_name}"
                  f" → beklenen: {expected} | gerçek: {actual}")

            findings.append({
                "table_name":      table["table_name"],
                "column_name":     col_name,
                "expected_lookup": expected,
                "actual_lookup":   actual,
                "valid":           valid,
                "status":          status.split()[1]
            })

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "lookup_check.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(findings, f, ensure_ascii=False, indent=2)

    print(f"\n🔗 Toplam {len(findings)} kolon kontrol edildi | ❌ Sorunlu: {issues}")
    print(f"📄 → {out_path}")
    return findings


if __name__ == "__main__":
    check_lookups()
