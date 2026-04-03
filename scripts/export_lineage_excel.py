"""
export_lineage_excel.py
lineage/lineage.json → Excel (kolon bazlı lineage raporu)

SSIS tarafında aynı sütun düzenini kullanarak Execute SQL + Excel hedefi
veya bu scripti Execute Process Task ile çalıştırabilirsiniz.
"""

from __future__ import annotations

import json
import os

import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
LINEAGE_JSON = os.path.join(BASE_DIR, "lineage", "lineage.json")
OUTPUT_XLSX = os.path.join(BASE_DIR, "output", "lineage_export.xlsx")


def load_lineage(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def lineage_to_rows(data: dict) -> list[dict]:
    rows = []
    for target_key, meta in data.items():
        tbl = target_key.split(".")[0] if "." in target_key else target_key
        layer = ""
        u = tbl.upper()
        if u.startswith("SRC_"):
            layer = "SOURCE"
        elif u.startswith("STG_"):
            layer = "STAGING"
        elif u.startswith("DWH_"):
            layer = "DATA_WAREHOUSE"
        elif u.startswith("DM"):
            layer = "DATA_MART"
        elif u.startswith("LKP_"):
            layer = "LOOKUP"
        rows.append(
            {
                "target_object": target_key,
                "target_table": tbl,
                "layer": layer,
                "source": meta.get("source", ""),
                "original_source": meta.get("original_source", ""),
                "transformation": meta.get("transformation", ""),
            }
        )
    return rows


def export_excel(
    lineage_path: str | None = None,
    out_path: str | None = None,
) -> str:
    lineage_path = lineage_path or LINEAGE_JSON
    out_path = out_path or OUTPUT_XLSX

    if not os.path.isfile(lineage_path):
        raise FileNotFoundError(f"Lineage dosyası yok: {lineage_path}")

    data = load_lineage(lineage_path)
    rows = lineage_to_rows(data)
    df = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    def _write_xlsx(target: str) -> None:
        with pd.ExcelWriter(target, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="ColumnLineage", index=False)
            summary = pd.DataFrame(
                [
                    {"metric": "kayit_sayisi", "deger": len(df)},
                    {"metric": "kaynak_json", "deger": os.path.normpath(lineage_path)},
                ]
            )
            summary.to_excel(writer, sheet_name="Ozet", index=False)
            if "layer" in df.columns and len(df):
                oz = (
                    df.groupby("layer", dropna=False)
                    .size()
                    .reset_index(name="kolon_sayisi")
                    .sort_values("kolon_sayisi", ascending=False)
                )
                oz.to_excel(writer, sheet_name="KatmanaGore", index=False)

    try:
        _write_xlsx(out_path)
    except PermissionError:
        alt = out_path.replace(".xlsx", "_new.xlsx")
        print(f"  ⚠️  Çıktı dosyası kilitli; yazıldı: {alt}")
        _write_xlsx(alt)
        out_path = alt

    print(f"  → Excel lineage: {out_path} ({len(df)} satır)")
    return out_path


def main() -> None:
    os.chdir(BASE_DIR)
    export_excel()


if __name__ == "__main__":
    main()
