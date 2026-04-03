"""
metadata_extractor.py
Kişi 2 — Metadata Quality & Rule Engine
DDL dosyalarından tablo ve kolon metadata'sını çıkarır.
Çıktı: output/metadata.json

Desteklenen DDL notasyonu:
  -- TABLE_DESC: Tablo açıklaması (CREATE TABLE'dan hemen önce)
  KOLON_ADI TIP, -- Kolon açıklaması (satır sonu yorum)
"""

import re
import json
import os

DDL_DIR = os.path.join(os.path.dirname(__file__), "..", "ddl")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")

# Eski sabit eşleme (infer başarısız olursa)
LOOKUP_MAPPING = {
    "MUSTERI_TIP_ID": "LKP_MUSTERI_TIP",
    "KREDI_TIP_ID": "LKP_KREDI_TIP",
}


def _infer_lookup_table(col_name: str) -> str | None:
    """Kolon adından LKP tablosu türetir (sentetik şema ile uyumlu)."""
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
    return LOOKUP_MAPPING.get(col_name)


def _iter_sql_files(ddl_path: str) -> list[str]:
    """ddl/ altındaki tüm .sql dosyaları (alt klasörler dahil)."""
    paths: list[str] = []
    for dirpath, _, filenames in os.walk(ddl_path):
        for f in sorted(filenames):
            if f.endswith(".sql"):
                paths.append(os.path.join(dirpath, f))
    return sorted(paths)


def _parse_columns_block(columns_block: str) -> list[dict]:
    columns: list[dict] = []
    for line in columns_block.strip().split("\n"):
        raw = line.strip()
        if not raw or raw.upper().startswith(
            ("FOREIGN", "PRIMARY", "UNIQUE", "CHECK", "--")
        ):
            continue
        inline_comment = ""
        if "--" in raw:
            raw, inline_comment = raw.split("--", 1)
            inline_comment = inline_comment.strip()
        raw = raw.strip().rstrip(",")
        if not raw:
            continue
        parts = raw.split()
        if len(parts) >= 2:
            col_name = parts[0]
            col_type = parts[1]
            lookup_ref = _infer_lookup_table(col_name)
            columns.append(
                {
                    "column_name": col_name,
                    "data_type": col_type,
                    "description": inline_comment,
                    "lookup_table": lookup_ref,
                    "nullable": True,
                }
            )
    return columns


def parse_ddl_file(filepath: str) -> list[dict]:
    """Bir SQL DDL dosyasından CREATE TABLE bloklarını parse eder (parantez dengeli)."""
    tables = []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    i = 0
    while True:
        m = re.search(r"CREATE TABLE (\w+)\s*\(", content[i:], re.IGNORECASE)
        if not m:
            break
        table_name = m.group(1)
        create_start = i + m.start()
        paren_open = i + m.end() - 1
        depth = 1
        j = paren_open + 1
        cols_end = -1
        while j < len(content):
            ch = content[j]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    cols_end = j
                    break
            j += 1
        if cols_end < 0:
            break
        j = cols_end + 1
        while j < len(content) and content[j] in " \t\r\n":
            j += 1
        if j < len(content) and content[j] == ";":
            j += 1

        columns_block = content[paren_open + 1 : cols_end]
        chunk_before = content[max(0, create_start - 800) : create_start]
        tds = re.findall(
            r"--\s*TABLE_DESC:\s*(.+?)(?:\r\n|\n)", chunk_before, re.IGNORECASE
        )
        table_description = tds[-1].strip() if tds else ""

        columns = _parse_columns_block(columns_block)
        if columns:
            tables.append(
                {
                    "table_name": table_name,
                    "source_file": os.path.basename(filepath),
                    "table_description": table_description,
                    "layer": _detect_layer(table_name),
                    "columns": columns,
                }
            )
        i = j

    return tables


def _detect_layer(table_name: str) -> str:
    """Tablo adı prefix'inden ETL katmanını tespit eder."""
    prefixes = {
        "SRC_": "SOURCE",
        "STG_": "STAGING",
        "DWH_": "DATA_WAREHOUSE",
        "DM": "DATA_MART",
        "LKP_": "LOOKUP",
        "TMP_": "TEMP",
    }
    for prefix, layer in prefixes.items():
        if table_name.upper().startswith(prefix):
            return layer
    return "UNKNOWN"


def extract_all_metadata() -> list[dict]:
    """ddl/ dizinindeki tüm .sql dosyalarından metadata çıkarır."""
    all_tables = []
    ddl_path = os.path.abspath(DDL_DIR)
    for filepath in _iter_sql_files(ddl_path):
        tables = parse_ddl_file(filepath)
        all_tables.extend(tables)
        print(f"  📄 {os.path.relpath(filepath, ddl_path)}: {len(tables)} tablo bulundu")
    return all_tables


if __name__ == "__main__":
    print("🔍 Metadata çıkarılıyor...\n")
    metadata = extract_all_metadata()

    os.makedirs(os.path.abspath(OUTPUT_DIR), exist_ok=True)
    output_path = os.path.join(os.path.abspath(OUTPUT_DIR), "metadata.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Toplam {len(metadata)} tablo → {output_path}")
