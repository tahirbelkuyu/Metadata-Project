"""
quality_rules.py
Kişi 2 — Metadata Quality & Rule Engine
Kalite kurallarının saf fonksiyon implementasyonları.
Her fonksiyon True (geçti) / False (geçmedi) döner.
"""


# ─── Kolon Seviyesi Kurallar ────────────────────────────────────────────────

def rule_has_description(column: dict) -> bool:
    """Açıklama alanı dolu mu?"""
    desc = column.get("description", "")
    return bool(desc and desc.strip())


def rule_description_min_length(column: dict, min_len: int = 15) -> bool:
    """Açıklama en az min_len karakter mi?"""
    desc = column.get("description", "")
    return len(desc.strip()) >= min_len


def rule_data_type_valid(column: dict) -> bool:
    """Geçerli bir SQL veri tipi var mı?"""
    VALID_TYPES = {
        "INT", "INTEGER", "BIGINT", "SMALLINT",
        "VARCHAR", "CHAR", "TEXT", "NVARCHAR",
        "DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL",
        "DATE", "DATETIME", "TIMESTAMP",
        "BOOLEAN", "BIT"
    }
    dtype = column.get("data_type", "").upper().split("(")[0].strip()
    return dtype in VALID_TYPES


def rule_lookup_valid(column: dict, available_lookups: list[str]) -> tuple[bool, bool]:
    """
    Lookup beklenen kolonlar: *_TIP_ID, *_KOD_ID, *_REF_ID (PK/FK *_ID hariç).
    Bu kolonların metadata.lookup_table değeri mevcut LKP tablolarından biri olmalı.
    Returns: (applies: bool, passed: bool)
    """
    col_name = column.get("column_name", "")
    u = col_name.upper()
    applies = (
        u.endswith("_TIP_ID")
        or u.endswith("_KOD_ID")
        or u.endswith("_REF_ID")
    )
    if not applies:
        return False, True  # Kural uygulanmaz, geçti sayılır
    passed = column.get("lookup_table") in available_lookups
    return True, passed


def rule_no_reserved_words(column: dict) -> bool:
    """Kolon adı SQL reserved word mu?"""
    RESERVED = {"SELECT", "FROM", "WHERE", "TABLE", "INDEX", "ORDER", "GROUP", "KEY"}
    return column.get("column_name", "").upper() not in RESERVED


# ─── Tablo Seviyesi Kurallar ─────────────────────────────────────────────────

def rule_table_has_description(table: dict) -> bool:
    """Tablo açıklaması var mı?"""
    desc = table.get("table_description", "")
    return bool(desc and desc.strip())


def rule_table_has_columns(table: dict) -> bool:
    """Tablonun en az bir kolonu var mı?"""
    return len(table.get("columns", [])) > 0


# ─── Rule Registry ───────────────────────────────────────────────────────────
# quality_engine.py bu sözlüğü okur.

COLUMN_RULES = {
    "HAS_DESCRIPTION":       (rule_has_description,       0.30),
    "DESCRIPTION_MIN_LENGTH": (rule_description_min_length, 0.20),
    "DATA_TYPE_VALID":        (rule_data_type_valid,         0.15),
    "NO_RESERVED_WORDS":      (rule_no_reserved_words,       0.05),
    # LOOKUP_VALID özel mantık içerdiğinden engine içinde ayrıca işlenir
    "LOOKUP_VALID":           (None,                         0.30),
}

TABLE_RULES = {
    "HAS_TABLE_DESCRIPTION":  (rule_table_has_description,  0.50),
    "HAS_COLUMNS":            (rule_table_has_columns,       0.50),
}
