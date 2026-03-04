"""
metadata_extractor.py
Kişi 2 — Metadata Quality & Rule Engine
DDL dosyalarından tablo ve kolon metadata'sını çıkarır.
Çıktı: output/metadata.json
"""

import re
import json
import os

DDL_DIR = os.path.join(os.path.dirname(__file__), "..", "ddl")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")

# Lookup tablosu → ilgili olabilecek kolon adı suffix eşleştirmesi
LOOKUP_MAPPING = {
    "MUSTERI_TIP_ID": "LKP_MUSTERI_TIP",
    "KREDI_TIP_ID":   "LKP_KREDI_TIP",
}


def parse_ddl_file(filepath: str) -> list[dict]:
    """Bir SQL DDL dosyasından CREATE TABLE bloklarını parse eder."""
    tables = []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # CREATE TABLE bloklarını yakala (iç içe parantez desteği yok — basit DDL varsayımı)
    pattern = r"CREATE TABLE (\w+)\s*\((.+?)\);"
    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)

    for table_name, columns_block in matches:
        columns = []
        for line in columns_block.strip().split("\n"):
            line = line.strip().rstrip(",")
            # Kısıtlamaları atla
            if not line or line.upper().startswith(("FOREIGN", "PRIMARY", "UNIQUE", "CHECK", "--")):
                continue
            parts = line.split()
            if len(parts) >= 2:
                col_name = parts[0]
                col_type = parts[1]
                # Otomatik lookup bağlantısı
                lookup_ref = LOOKUP_MAPPING.get(col_name, None)
                columns.append({
                    "column_name": col_name,
                    "data_type": col_type,
                    "description": "",          # Sentetik aşamada eklenecek
                    "lookup_table": lookup_ref,
                    "nullable": True
                })

        if columns:
            tables.append({
                "table_name": table_name,
                "source_file": os.path.basename(filepath),
                "table_description": "",       # Sentetik aşamada eklenecek
                "layer": _detect_layer(table_name),
                "columns": columns
            })

    return tables


def _detect_layer(table_name: str) -> str:
    """Tablo adı prefix'inden ETL katmanını tespit eder."""
    prefixes = {
        "SRC_":  "SOURCE",
        "STG_":  "STAGING",
        "DWH_":  "DATA_WAREHOUSE",
        "DM":    "DATA_MART",
        "LKP_":  "LOOKUP",
        "TMP_":  "TEMP",
    }
    for prefix, layer in prefixes.items():
        if table_name.upper().startswith(prefix):
            return layer
    return "UNKNOWN"


def extract_all_metadata() -> list[dict]:
    """ddl/ dizinindeki tüm .sql dosyalarından metadata çıkarır."""
    all_tables = []
    ddl_path = os.path.abspath(DDL_DIR)
    for filename in sorted(os.listdir(ddl_path)):
        if filename.endswith(".sql"):
            filepath = os.path.join(ddl_path, filename)
            tables = parse_ddl_file(filepath)
            all_tables.extend(tables)
            print(f"  📄 {filename}: {len(tables)} tablo bulundu")
    return all_tables


if __name__ == "__main__":
    print("🔍 Metadata çıkarılıyor...\n")
    metadata = extract_all_metadata()

    os.makedirs(os.path.abspath(OUTPUT_DIR), exist_ok=True)
    output_path = os.path.join(os.path.abspath(OUTPUT_DIR), "metadata.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Toplam {len(metadata)} tablo → {output_path}")
