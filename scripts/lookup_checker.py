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

# Bilinen kolon → lookup eşlemesi (sabit örnekler; sentetik kolonlar isimden türetilir)
KNOWN_LOOKUP_MAP: dict[str, str | None] = {
    "MUSTERI_TIP_ID": "LKP_MUSTERI_TIP",
    "KREDI_TIP_ID": "LKP_KREDI_TIP",
    "AKTIF_FLAG": None,
    "ISLEM_TIP": None,
}

TRIGGER_SUFFIXES = ("_TIP_ID", "_KOD_ID", "_REF_ID")


def _expected_lookup_from_name(col_name: str) -> str | None:
    """Kolon adından beklenen LKP tablosu (sentetik şema ile uyumlu)."""
    if col_name in KNOWN_LOOKUP_MAP:
        v = KNOWN_LOOKUP_MAP[col_name]
        return v
    u = col_name.upper()
    if u.endswith("_TIP_ID"):
        stem = col_name[: -len("_TIP_ID")].upper()
        return f"LKP_{stem}_TIP"
    if u.endswith("_KOD_ID"):
        stem = col_name[: -len("_KOD_ID")].upper()
        return f"LKP_{stem}_KOD"
    if u.endswith("_REF_ID"):
        stem = col_name[: -len("_REF_ID")].upper()
        return f"LKP_{stem}_REF"
    return None


def should_have_lookup(col_name: str) -> bool:
    """Lookup doğrulaması gereken kolon adı mı?"""
    return _expected_lookup_from_name(col_name) is not None


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

            expected = _expected_lookup_from_name(col_name)
            actual = col.get("lookup_table")

            if expected is None:
                status = "⚠️  TANIM_YOK"
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
