"""
Tek kaynak: pilot (SRC/STG/DWH/DM/LKP/TMP) + domain sentetik tablolar.
Çıktılar (pipeline Adım 0):
  - ddl/generated/schema.sql          — tüm CREATE TABLE'lar
  - lineage/lineage.json              — kolon lineage (pilot + domain)
  - glossary/glossary.json            — çekirdek + domain kolonları
  - docs/etl_flow.md, docs/toa.md     — sentetik modele göre güncellenir
"""

from __future__ import annotations

import json
import os
import random

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
SCHEMA_OUT = os.path.join(BASE_DIR, "ddl", "generated", "schema.sql")
LINEAGE_PATH = os.path.join(BASE_DIR, "lineage", "lineage.json")
GLOSSARY_PATH = os.path.join(BASE_DIR, "glossary", "glossary.json")
DOCS_ETL = os.path.join(BASE_DIR, "docs", "etl_flow.md")
DOCS_TOA = os.path.join(BASE_DIR, "docs", "toa.md")

# ── Pilot çekirdek DDL (önceden ayrı .sql dosyalarındaydı; tek dosyada toplandı) ──
CORE_PILOT_SQL = """
-- ═══════════════════════════════════════════════════════════
-- PILOT: Source / Staging / DWH / Data Mart / Lookup / Temp
-- (generate_synthetic_corpus.py ile üretilir; kök ddl/*.sql kullanılmaz)
-- ═══════════════════════════════════════════════════════════

-- TABLE_DESC: Core Banking kaynak ham müşteri ve kredi yüklemesi
CREATE TABLE SRC_MUSTERI (
    MUSTERI_ID INT, -- Dahili müşteri anahtarı (kaynak sistem)
    TC_KIMLIK_NO VARCHAR(11), -- 11 haneli TCKN
    AD VARCHAR(50), -- Ad (stagingde birleştirilecek)
    SOYAD VARCHAR(50), -- Soyad
    DOGUM_TARIHI DATE, -- Doğum tarihi
    MUSTERI_TIP INT, -- Ham kod; DWHde LKP ile eşlenir
    CREATED_DATE DATE -- Kaynak kayıt tarihi
);

CREATE TABLE SRC_KREDI (
    KREDI_ID INT,
    MUSTERI_ID INT,
    KREDI_AMT DECIMAL(18,2), -- Anapara (kaynak adı İngilizce)
    KREDI_TIP INT,
    VADE_AY INT,
    BASLANGIC_TARIHI DATE,
    BITIS_TARIHI DATE
);

-- TABLE_DESC: Temizleme ve standardizasyon katmanı
CREATE TABLE STG_MUSTERI (
    MUSTERI_ID INT,
    TC_KIMLIK_NO VARCHAR(11),
    AD_SOYAD VARCHAR(100), -- AD + SOYAD birleşimi
    DOGUM_TARIHI DATE,
    MUSTERI_TIP_ID INT, -- LKP_MUSTERI_TIP referansı
    LOAD_DATE DATE -- Partisyon / yükleme damgası
);

CREATE TABLE STG_KREDI (
    KREDI_ID INT,
    MUSTERI_ID INT,
    KREDI_TUTAR DECIMAL(18,2),
    KREDI_TIP_ID INT,
    VADE_AY INT,
    LOAD_DATE DATE
);

-- TABLE_DESC: İş ana veri ve işlem hub tabloları
CREATE TABLE DWH_MUSTERI (
    MUSTERI_ID INT PRIMARY KEY,
    TC_KIMLIK_NO VARCHAR(11),
    AD_SOYAD VARCHAR(100),
    DOGUM_TARIHI DATE,
    MUSTERI_TIP_ID INT,
    AKTIF_FLAG INT
);

CREATE TABLE DWH_KREDI (
    KREDI_ID INT PRIMARY KEY,
    MUSTERI_ID INT,
    KREDI_TUTAR DECIMAL(18,2),
    KREDI_TIP_ID INT,
    VADE_AY INT,
    AKTIF_FLAG INT,
    FOREIGN KEY (MUSTERI_ID) REFERENCES DWH_MUSTERI(MUSTERI_ID)
);

CREATE TABLE DWH_ISLEM (
    ISLEM_ID INT PRIMARY KEY,
    MUSTERI_ID INT,
    KREDI_ID INT,
    ISLEM_TUTAR DECIMAL(18,2),
    ISLEM_TARIHI DATE,
    ISLEM_TIP VARCHAR(50),
    FOREIGN KEY (MUSTERI_ID) REFERENCES DWH_MUSTERI(MUSTERI_ID),
    FOREIGN KEY (KREDI_ID) REFERENCES DWH_KREDI(KREDI_ID)
);

CREATE TABLE DM1_KREDI_RAPOR (
    RAPOR_ID INT PRIMARY KEY,
    MUSTERI_ID INT,
    TOPLAM_KREDI_TUTAR DECIMAL(18,2),
    AKTIF_KREDI_SAYISI INT,
    RAPOR_TARIHI DATE
);

CREATE TABLE DM2_SEGMENT_ANALIZ (
    SEGMENT_ID INT,
    TOPLAM_MUSTERI INT,
    ORT_KREDI_TUTAR DECIMAL(18,2),
    ANALIZ_TARIHI DATE
);

CREATE TABLE LKP_MUSTERI_TIP (
    ID INT PRIMARY KEY,
    ACIKLAMA VARCHAR(100)
);

INSERT INTO LKP_MUSTERI_TIP VALUES
(1, 'Bireysel Müşteri'),
(2, 'Ticari Müşteri');

CREATE TABLE LKP_KREDI_TIP (
    ID INT PRIMARY KEY,
    ACIKLAMA VARCHAR(100)
);

INSERT INTO LKP_KREDI_TIP VALUES
(1, 'İhtiyaç Kredisi'),
(2, 'Konut Kredisi'),
(3, 'Taşıt Kredisi');

CREATE TABLE TMP_RAPOR_DENEME (
    ID INT,
    AD INT,
    DOGUM INT,
    KREDI VARCHAR(20)
);
""".strip()

DOMAINS = [
    "KART",
    "ODEME",
    "SUBE",
    "LIMIT",
    "POS",
    "ATM",
    "KMH",
    "TAHSILAT",
    "MEVDUAT",
    "KIRILIM",
    "RISK",
    "MUHASEBE",
    "KANAL",
    "KAMPANYA",
    "FATURA",
    "TEMINAT",
    "KONTRAT",
    "CRM",
    "EKSTRE",
]

# Pilot kolon lineage (elle tutulan harita + domain üretimi ile birleşir)
PILOT_LINEAGE: dict[str, dict[str, str]] = {
    "DWH_MUSTERI.MUSTERI_ID": {
        "source": "STG_MUSTERI.MUSTERI_ID",
        "original_source": "SRC_MUSTERI.MUSTERI_ID",
        "transformation": "Direct mapping",
    },
    "DWH_MUSTERI.TC_KIMLIK_NO": {
        "source": "STG_MUSTERI.TC_KIMLIK_NO",
        "original_source": "SRC_MUSTERI.TC_KIMLIK_NO",
        "transformation": "Direct mapping",
    },
    "DWH_MUSTERI.AD_SOYAD": {
        "source": "STG_MUSTERI.AD_SOYAD",
        "original_source": "SRC_MUSTERI.AD + SRC_MUSTERI.SOYAD",
        "transformation": "Concatenation",
    },
    "DWH_MUSTERI.DOGUM_TARIHI": {
        "source": "STG_MUSTERI.DOGUM_TARIHI",
        "original_source": "SRC_MUSTERI.DOGUM_TARIHI",
        "transformation": "Direct mapping",
    },
    "DWH_MUSTERI.MUSTERI_TIP_ID": {
        "source": "STG_MUSTERI.MUSTERI_TIP_ID",
        "original_source": "SRC_MUSTERI.MUSTERI_TIP",
        "transformation": "Lookup normalization → LKP_MUSTERI_TIP",
    },
    "DWH_MUSTERI.AKTIF_FLAG": {
        "source": "Derived in DWH load",
        "original_source": "Business rule from staging",
        "transformation": "Default 1 / soft-delete flag",
    },
    "DWH_KREDI.KREDI_ID": {
        "source": "STG_KREDI.KREDI_ID",
        "original_source": "SRC_KREDI.KREDI_ID",
        "transformation": "Direct mapping",
    },
    "DWH_KREDI.MUSTERI_ID": {
        "source": "STG_KREDI.MUSTERI_ID",
        "original_source": "SRC_KREDI.MUSTERI_ID",
        "transformation": "Direct mapping",
    },
    "DWH_KREDI.KREDI_TUTAR": {
        "source": "STG_KREDI.KREDI_TUTAR",
        "original_source": "SRC_KREDI.KREDI_AMT",
        "transformation": "Rename + DECIMAL cast",
    },
    "DWH_KREDI.KREDI_TIP_ID": {
        "source": "STG_KREDI.KREDI_TIP_ID",
        "original_source": "SRC_KREDI.KREDI_TIP",
        "transformation": "Lookup normalization → LKP_KREDI_TIP",
    },
    "DWH_KREDI.VADE_AY": {
        "source": "STG_KREDI.VADE_AY",
        "original_source": "SRC_KREDI.VADE_AY",
        "transformation": "Direct mapping",
    },
    "DWH_KREDI.AKTIF_FLAG": {
        "source": "Derived in DWH load",
        "original_source": "N/A",
        "transformation": "Business flag",
    },
    "DWH_ISLEM.ISLEM_ID": {
        "source": "Core Banking feed",
        "original_source": "Transaction engine",
        "transformation": "Surrogate / load",
    },
    "DWH_ISLEM.MUSTERI_ID": {
        "source": "Core Banking feed",
        "original_source": "SRC_MUSTERI.MUSTERI_ID",
        "transformation": "FK resolution",
    },
    "DWH_ISLEM.KREDI_ID": {
        "source": "Core Banking feed",
        "original_source": "SRC_KREDI.KREDI_ID",
        "transformation": "FK resolution",
    },
    "DWH_ISLEM.ISLEM_TUTAR": {
        "source": "Transaction system feed",
        "original_source": "External transaction service",
        "transformation": "Loaded as-is",
    },
    "DWH_ISLEM.ISLEM_TARIHI": {
        "source": "Transaction system feed",
        "original_source": "External transaction service",
        "transformation": "Date normalization",
    },
    "DWH_ISLEM.ISLEM_TIP": {
        "source": "Transaction system feed",
        "original_source": "External transaction service",
        "transformation": "Free text category",
    },
    "DM1_KREDI_RAPOR.RAPOR_ID": {
        "source": "Mart surrogate",
        "original_source": "Derived",
        "transformation": "Identity / sequence in mart",
    },
    "DM1_KREDI_RAPOR.MUSTERI_ID": {
        "source": "DWH_MUSTERI.MUSTERI_ID",
        "original_source": "SRC_MUSTERI.MUSTERI_ID",
        "transformation": "Grain = customer",
    },
    "DM1_KREDI_RAPOR.TOPLAM_KREDI_TUTAR": {
        "source": "DWH_KREDI.KREDI_TUTAR",
        "original_source": "SRC_KREDI.KREDI_AMT",
        "transformation": "SUM(KREDI_TUTAR) per MUSTERI_ID",
    },
    "DM1_KREDI_RAPOR.AKTIF_KREDI_SAYISI": {
        "source": "DWH_KREDI.AKTIF_FLAG",
        "original_source": "Derived field",
        "transformation": "COUNT where AKTIF_FLAG = 1",
    },
    "DM1_KREDI_RAPOR.RAPOR_TARIHI": {
        "source": "ETL batch date",
        "original_source": "Control table",
        "transformation": "As-of reporting date",
    },
    "DM2_SEGMENT_ANALIZ.SEGMENT_ID": {
        "source": "Segmentation model",
        "original_source": "Derived",
        "transformation": "Cluster id",
    },
    "DM2_SEGMENT_ANALIZ.TOPLAM_MUSTERI": {
        "source": "DWH_MUSTERI",
        "original_source": "SRC_MUSTERI",
        "transformation": "COUNT distinct MUSTERI_ID",
    },
    "DM2_SEGMENT_ANALIZ.ORT_KREDI_TUTAR": {
        "source": "DWH_KREDI.KREDI_TUTAR",
        "original_source": "SRC_KREDI.KREDI_AMT",
        "transformation": "AVG grouped by segment",
    },
    "DM2_SEGMENT_ANALIZ.ANALIZ_TARIHI": {
        "source": "ETL batch date",
        "original_source": "Control table",
        "transformation": "Snapshot date",
    },
}


def _pick_table_desc(rng: random.Random) -> str:
    kind = rng.choices(
        ["empty", "short", "good"],
        weights=[0.22, 0.18, 0.60],
        k=1,
    )[0]
    if kind == "empty":
        return ""
    if kind == "short":
        return "Rapor tablosu."
    return (
        "Bankacılık operasyonel veri ambarı kapsamında üretilen "
        "sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir."
    )


def _pick_col_desc(
    rng: random.Random,
    col: str,
    table: str,
    semantic: str,
) -> str:
    kind = rng.choices(
        ["empty", "short", "good_tr", "good_en", "wrong", "typo", "mediocre"],
        weights=[0.11, 0.11, 0.34, 0.07, 0.06, 0.07, 0.24],
        k=1,
    )[0]
    if kind == "empty":
        return ""
    if kind == "short":
        return "Alandır."
    if kind == "good_en":
        return (
            f"Business attribute `{col}` in `{table}`; sourced from staging "
            "and validated against operational rules."
        )
    if kind == "wrong":
        wrong_map = {
            "tutar": "Müşteri segment kodunu tutar; risk skoru ile ilişkilidir.",
            "tarih": "Kredi vadesini gün sayısı olarak tutar (ay değil).",
            "tip_id": "POS terminal seri numarasıdır; şube kodu ile aynıdır.",
            "musteri": "Kredi ana para tutarıdır; döviz cinsinden saklanır.",
            "pk": "Rapor satırı açıklama metnidir.",
            "diger": "Kanal kodu müşteri telefon numarasıdır.",
        }
        return wrong_map.get(semantic, wrong_map["diger"])
    if kind == "typo":
        return f"{semantic} alanı: iş kuralına göre doldurulur (typo testi: tutr, trh)."
    if kind == "mediocre":
        return f"{col} kolonu {table} tablosunda yer alır."
    good_map = {
        "tutar": (
            "İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; "
            "kur dönüşümü uygulanmamıştır."
        ),
        "tarih": (
            "İşlemin veya kaydın geçerli olduğu takvim tarihidir; "
            "operasyonel gün sonu ile uyumludur."
        ),
        "tip_id": (
            "İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; "
            "iş anlamı kod listesi ile çözülür."
        ),
        "musteri": (
            "Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder."
        ),
        "pk": "Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).",
        "diger": (
            "Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır."
        ),
    }
    return good_map.get(semantic, good_map["diger"])


def _write_lkp(rng: random.Random, domain: str, lines: list[str]) -> None:
    t = f"LKP_{domain}_TIP"
    td = _pick_table_desc(rng)
    lines.append(f"-- TABLE_DESC: {td}")
    lines.append(f"CREATE TABLE {t} (")
    lines.append(f"    ID INT PRIMARY KEY, -- {_pick_col_desc(rng, 'ID', t, 'pk')}")
    lines.append(f"    ACIKLAMA VARCHAR(200) -- {_pick_col_desc(rng, 'ACIKLAMA', t, 'diger')}")
    lines.append(");")
    lines.append("")


def _write_fact(
    rng: random.Random,
    layer: str,
    domain: str,
    lines: list[str],
) -> list[str]:
    prefix = {"SRC": "SRC", "STG": "STG", "DWH": "DWH"}[layer]
    tname = f"{prefix}_{domain}_FACT"
    td = _pick_table_desc(rng)
    lines.append(f"-- TABLE_DESC: {td}")
    lines.append(f"CREATE TABLE {tname} (")
    spec: list[tuple[str, str, str]] = [
        (f"{domain}_FACT_ID", "INT", "pk"),
        ("MUSTERI_ID", "INT", "musteri"),
        (f"{domain}_TUTAR", "DECIMAL(18,2)", "tutar"),
        (f"{domain}_TIP_ID", "INT", "tip_id"),
        ("ISLEM_TARIHI", "DATE", "tarih"),
        ("KANAL_KOD", "VARCHAR(30)", "diger"),
    ]
    cols: list[str] = []
    for i, (name, typ, sem) in enumerate(spec):
        desc = _pick_col_desc(rng, name, tname, sem)
        is_last = i == len(spec) - 1
        comma = "" if is_last else ","
        tail = f" -- {desc}" if desc else ""
        lines.append(f"    {name} {typ}{comma}{tail}")
        cols.append(name)
    lines.append(");")
    lines.append("")
    return cols


def _write_dm(
    rng: random.Random,
    domain: str,
    lines: list[str],
) -> list[str]:
    tname = f"DM_{domain}_RAPOR"
    td = _pick_table_desc(rng)
    lines.append(f"-- TABLE_DESC: {td}")
    lines.append(f"CREATE TABLE {tname} (")
    spec: list[tuple[str, str, str]] = [
        ("RAPOR_ID", "INT", "pk"),
        ("MUSTERI_ID", "INT", "musteri"),
        (f"TOPLAM_{domain}_TUTAR", "DECIMAL(18,2)", "tutar"),
        ("RAPOR_TARIHI", "DATE", "tarih"),
    ]
    cols: list[str] = []
    for i, (name, typ, sem) in enumerate(spec):
        desc = _pick_col_desc(rng, name, tname, sem)
        is_last = i == len(spec) - 1
        comma = "" if is_last else ","
        tail = f" -- {desc}" if desc else ""
        lines.append(f"    {name} {typ}{comma}{tail}")
        cols.append(name)
    lines.append(");")
    lines.append("")
    return cols


def build_domain_lineage(domain: str, dwh_cols: list[str], dm_cols: list[str]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    dwh = f"DWH_{domain}_FACT"
    stg = f"STG_{domain}_FACT"
    src = f"SRC_{domain}_FACT"
    dm = f"DM_{domain}_RAPOR"
    for c in dwh_cols:
        out[f"{dwh}.{c}"] = {
            "source": f"{stg}.{c}",
            "original_source": f"{src}.{c}",
            "transformation": "SCD Type 1 load / direct map",
        }
    tutar = f"{domain}_TUTAR"
    if f"TOPLAM_{domain}_TUTAR" in dm_cols and tutar in dwh_cols:
        out[f"{dm}.TOPLAM_{domain}_TUTAR"] = {
            "source": f"{dwh}.{tutar}",
            "original_source": f"{src}.{tutar}",
            "transformation": f"SUM({tutar}) grouped by MUSTERI_ID, RAPOR_TARIHI",
        }
    if "MUSTERI_ID" in dm_cols and "MUSTERI_ID" in dwh_cols:
        out[f"{dm}.MUSTERI_ID"] = {
            "source": f"{dwh}.MUSTERI_ID",
            "original_source": f"{src}.MUSTERI_ID",
            "transformation": "Surrogate preserved in mart",
        }
    if "RAPOR_ID" in dm_cols:
        out[f"{dm}.RAPOR_ID"] = {
            "source": "Sequence / surrogate generator",
            "original_source": "Derived in mart ETL",
            "transformation": "ROW_NUMBER / identity in reporting layer",
        }
    if "RAPOR_TARIHI" in dm_cols:
        out[f"{dm}.RAPOR_TARIHI"] = {
            "source": "ETL batch date",
            "original_source": "Control table",
            "transformation": "Business report as-of date",
        }
    return out


def generate_domain_sql_and_lineage(
    seed: int = 42,
    domains: list[str] | None = None,
) -> tuple[str, dict[str, dict[str, str]]]:
    rng = random.Random(seed)
    domains = domains or DOMAINS
    lines: list[str] = [
        "",
        "-- ═══════════════════════════════════════════════════════════",
        "-- DOMAIN FACT / MART (sentetik genişletme)",
        "-- ═══════════════════════════════════════════════════════════",
        "",
    ]
    lineage: dict[str, dict[str, str]] = {}
    for domain in domains:
        d = domain.upper().replace(" ", "_")
        _write_lkp(rng, d, lines)
        _write_fact(rng, "SRC", d, lines)
        _write_fact(rng, "STG", d, lines)
        dwh_cols = _write_fact(rng, "DWH", d, lines)
        dm_cols = _write_dm(rng, d, lines)
        lineage.update(build_domain_lineage(d, dwh_cols, dm_cols))
    return "\n".join(lines), lineage


def build_glossary(domains: list[str]) -> dict[str, dict[str, str]]:
    """Çekirdek sözlük + domain kolonları (pipeline glossary_checker ile uyumlu)."""
    core: dict[str, dict[str, str]] = {
        "TC_KIMLIK_NO": {
            "definition": "Türkiye Cumhuriyeti vatandaşlarına verilen 11 haneli benzersiz kimlik numarası.",
            "source": "Nüfus / Core Banking",
            "data_type": "VARCHAR(11)",
            "example": "12345678901",
        },
        "MUSTERI_ID": {
            "definition": "Müşteriyi tekil tanımlayan dahili sayısal kimlik.",
            "source": "Core Banking",
            "data_type": "INT",
            "example": "100001",
        },
        "AD": {"definition": "Müşteri adı (kaynakta ayrı alan).", "source": "Core Banking", "data_type": "VARCHAR(50)", "example": "Ahmet"},
        "SOYAD": {"definition": "Müşteri soyadı (kaynakta ayrı alan).", "source": "Core Banking", "data_type": "VARCHAR(50)", "example": "Yılmaz"},
        "AD_SOYAD": {
            "definition": "Ad ve soyadın stagingde birleştirilmiş hali.",
            "source": "STG dönüşümü",
            "data_type": "VARCHAR(100)",
            "example": "Ahmet Yılmaz",
        },
        "DOGUM_TARIHI": {
            "definition": "Doğum tarihi (YYYY-MM-DD).",
            "source": "Core Banking",
            "data_type": "DATE",
            "example": "1985-06-15",
        },
        "MUSTERI_TIP": {
            "definition": "Kaynak sistemdeki ham müşteri tip kodu (lookup öncesi).",
            "source": "Core Banking",
            "data_type": "INT",
            "example": "1",
        },
        "CREATED_DATE": {
            "definition": "Kaynak kaydın oluşturulma tarihi.",
            "source": "Core Banking",
            "data_type": "DATE",
            "example": "2024-01-10",
        },
        "MUSTERI_TIP_ID": {
            "definition": "LKP_MUSTERI_TIP ile eşlenen müşteri segment kodu.",
            "source": "LKP_MUSTERI_TIP",
            "data_type": "INT",
            "example": "1",
        },
        "AKTIF_FLAG": {
            "definition": "1=Aktif kayıt, 0=Pasif (soft-delete).",
            "source": "DWH iş kuralı",
            "data_type": "INT",
            "example": "1",
        },
        "KREDI_ID": {
            "definition": "Kredi sözleşmesini tekil tanımlayan anahtar.",
            "source": "Core Banking",
            "data_type": "INT",
            "example": "200001",
        },
        "KREDI_AMT": {
            "definition": "Kaynak sistemdeki anapara alanı (İngilizce ad).",
            "source": "Core Banking",
            "data_type": "DECIMAL(18,2)",
            "example": "50000.00",
        },
        "KREDI_TUTAR": {
            "definition": "Kredi anapara tutarı (TL).",
            "source": "Core Banking / STG",
            "data_type": "DECIMAL(18,2)",
            "example": "50000.00",
        },
        "KREDI_TIP": {
            "definition": "Kaynakta ham kredi tip kodu.",
            "source": "Core Banking",
            "data_type": "INT",
            "example": "2",
        },
        "KREDI_TIP_ID": {
            "definition": "LKP_KREDI_TIP ile eşlenen ürün kodu.",
            "source": "LKP_KREDI_TIP",
            "data_type": "INT",
            "example": "2",
        },
        "VADE_AY": {
            "definition": "Vade süresi (ay).",
            "source": "Core Banking",
            "data_type": "INT",
            "example": "36",
        },
        "BASLANGIC_TARIHI": {
            "definition": "Kredi başlangıç tarihi.",
            "source": "Core Banking",
            "data_type": "DATE",
            "example": "2023-01-01",
        },
        "BITIS_TARIHI": {
            "definition": "Kredi bitiş tarihi.",
            "source": "Core Banking",
            "data_type": "DATE",
            "example": "2026-01-01",
        },
        "LOAD_DATE": {
            "definition": "Staging yükleme / partisyon tarihi.",
            "source": "ETL",
            "data_type": "DATE",
            "example": "2024-03-01",
        },
        "ISLEM_ID": {
            "definition": "İşlem tekil anahtarı.",
            "source": "Core Banking",
            "data_type": "INT",
            "example": "300001",
        },
        "ISLEM_TUTAR": {
            "definition": "İşlem tutarı (TL).",
            "source": "Core Banking",
            "data_type": "DECIMAL(18,2)",
            "example": "1500.00",
        },
        "ISLEM_TARIHI": {
            "definition": "İşlem tarihi.",
            "source": "Core Banking",
            "data_type": "DATE",
            "example": "2024-03-01",
        },
        "ISLEM_TIP": {
            "definition": "İşlem kategorisi (serbest metin).",
            "source": "Core Banking",
            "data_type": "VARCHAR(50)",
            "example": "ODEME",
        },
        "RAPOR_ID": {
            "definition": "Data mart rapor satırı kimliği.",
            "source": "Data Mart",
            "data_type": "INT",
            "example": "400001",
        },
        "TOPLAM_KREDI_TUTAR": {
            "definition": "Müşteri bazında toplam kredi anaparası.",
            "source": "DWH_KREDI agregasyonu",
            "data_type": "DECIMAL(18,2)",
            "example": "125000.00",
        },
        "AKTIF_KREDI_SAYISI": {
            "definition": "Aktif kredi adedi.",
            "source": "DWH_KREDI agregasyonu",
            "data_type": "INT",
            "example": "3",
        },
        "RAPOR_TARIHI": {
            "definition": "Rapor üretim tarihi.",
            "source": "Data Mart",
            "data_type": "DATE",
            "example": "2024-02-29",
        },
        "SEGMENT_ID": {
            "definition": "Segment kimliği.",
            "source": "Analitik model",
            "data_type": "INT",
            "example": "10",
        },
        "TOPLAM_MUSTERI": {
            "definition": "Segmentteki toplam müşteri sayısı.",
            "source": "DWH agregasyonu",
            "data_type": "INT",
            "example": "5420",
        },
        "ORT_KREDI_TUTAR": {
            "definition": "Segment ortalama kredi tutarı.",
            "source": "DWH_KREDI agregasyonu",
            "data_type": "DECIMAL(18,2)",
            "example": "38500.00",
        },
        "ANALIZ_TARIHI": {
            "definition": "Analiz snapshot tarihi.",
            "source": "Data Mart",
            "data_type": "DATE",
            "example": "2024-02-29",
        },
        "ACIKLAMA": {
            "definition": "Lookup tablosunda kod açıklaması.",
            "source": "LKP",
            "data_type": "VARCHAR(200)",
            "example": "Bireysel",
        },
        "ID": {
            "definition": "Lookup tekil kod değeri.",
            "source": "LKP",
            "data_type": "INT",
            "example": "1",
        },
        "KANAL_KOD": {
            "definition": "İşlem kanalı kodu (şube, mobil, internet vb.).",
            "source": "Operasyonel sistem",
            "data_type": "VARCHAR(30)",
            "example": "MOBIL",
        },
    }
    for d in domains:
        du = d.upper()
        core[f"{du}_FACT_ID"] = {
            "definition": f"{du} işlem fact tablosu satır kimliği.",
            "source": "ETL",
            "data_type": "INT",
            "example": "900001",
        }
        core[f"{du}_TUTAR"] = {
            "definition": f"{du} ürün/işlem tutarı (TL).",
            "source": f"DWH_{du}_FACT",
            "data_type": "DECIMAL(18,2)",
            "example": "1200.00",
        }
        core[f"{du}_TIP_ID"] = {
            "definition": f"LKP_{du}_TIP ile eşlenen tip kodu.",
            "source": f"LKP_{du}_TIP",
            "data_type": "INT",
            "example": "1",
        }
        core[f"TOPLAM_{du}_TUTAR"] = {
            "definition": f"{du} için mart katmanında toplam tutar.",
            "source": f"DM_{du}_RAPOR",
            "data_type": "DECIMAL(18,2)",
            "example": "50000.00",
        }
    return dict(sorted(core.items()))


def write_etl_flow(domains: list[str]) -> None:
    dom_list = ", ".join(f"`{d}`" for d in domains)
    text = f"""# ETL Akışı (otomatik üretim)

Bu dosya `scripts/generate_synthetic_corpus.py` tarafından güncellenir.

## Mimari

```
[Core Banking]
     ▼
[SOURCE — SRC_*]     Ham müşteri/kredi + domain fact tabloları
     ▼
[STAGING — STG_*]    Temizlik, tip, LKP eşleme, LOAD_DATE
     ▼
[DATA WAREHOUSE — DWH_*]  İş ana veri + DWH_*_FACT domain tabloları
     ▼
[DATA MART — DM_*]   Özet raporlar (DM1/DM2 pilot + DM_*_RAPOR domain)
[LOOKUP — LKP_*]     Kod listeleri (pilot + domain başına LKP_*_TIP)
```

## Pilot tablolar

| Katman | Örnek |
|--------|--------|
| Source | `SRC_MUSTERI`, `SRC_KREDI` |
| Staging | `STG_MUSTERI`, `STG_KREDI` |
| DWH | `DWH_MUSTERI`, `DWH_KREDI`, `DWH_ISLEM` |
| Data Mart | `DM1_KREDI_RAPOR`, `DM2_SEGMENT_ANALIZ` |
| Lookup | `LKP_MUSTERI_TIP`, `LKP_KREDI_TIP` |

## Sentetik domain katmanı ({len(domains)} domain)

Her domain için: `LKP_<DOMAIN>_TIP`, `SRC_<DOMAIN>_FACT`, `STG_<DOMAIN>_FACT`, `DWH_<DOMAIN>_FACT`, `DM_<DOMAIN>_RAPOR`.

**Domain listesi:** {dom_list}

## Lineage

Kolon bazlı kaynak eşlemesi `lineage/lineage.json` içindedir; Excel için `output/lineage_export.xlsx` (pipeline Adım 8).
"""
    os.makedirs(os.path.dirname(DOCS_ETL), exist_ok=True)
    with open(DOCS_ETL, "w", encoding="utf-8") as f:
        f.write(text.strip() + "\n")


def write_toa(domains: list[str]) -> None:
    rows = "\n".join(
        f"| {d} | LKP + SRC/STG/DWH FACT + DM RAPOR |"
        for d in domains
    )
    text = f"""# TOA — Tablo / Obje / Alan (otomatik üretim)

Bu envanter `generate_synthetic_corpus.py` ile şemaya göre güncellenir.

## Pilot çekirdek (örnek DWH)

| Tablo | Obje (iş bağlamı) |
|-------|---------------------|
| DWH_MUSTERI | Müşteri master |
| DWH_KREDI | Kredi sözleşmesi |
| DWH_ISLEM | Finansal işlem |
| DM1_KREDI_RAPOR | Müşteri kredi özet raporu |
| DM2_SEGMENT_ANALIZ | Segment analizi |

## Domain genişlemesi

| Domain kodu | Üretilen tablo ailesi |
|-------------|------------------------|
{rows}

**Alan:** Kolon açıklamaları DDL içinde `--` yorumları ve `glossary/glossary.json` ile hizalanır.
"""
    with open(DOCS_TOA, "w", encoding="utf-8") as f:
        f.write(text.strip() + "\n")


def run(
    seed: int = 42,
    write_ddl: bool = True,
    write_lineage: bool = True,
    write_glossary: bool = True,
    write_docs: bool = True,
) -> None:
    domains = DOMAINS
    domain_sql, domain_lineage = generate_domain_sql_and_lineage(seed=seed, domains=domains)
    full_sql = CORE_PILOT_SQL.strip() + "\n" + domain_sql

    os.makedirs(os.path.dirname(SCHEMA_OUT), exist_ok=True)
    if write_ddl:
        with open(SCHEMA_OUT, "w", encoding="utf-8") as f:
            f.write(full_sql)
        print(f"  → Şema: {SCHEMA_OUT}")

    final_lineage = {**PILOT_LINEAGE, **domain_lineage}
    if write_lineage:
        os.makedirs(os.path.dirname(LINEAGE_PATH), exist_ok=True)
        with open(LINEAGE_PATH, "w", encoding="utf-8") as f:
            json.dump(dict(sorted(final_lineage.items())), f, ensure_ascii=False, indent=2)
        print(f"  → Lineage: {LINEAGE_PATH} ({len(final_lineage)} kolon)")

    if write_glossary:
        gloss = build_glossary(domains)
        os.makedirs(os.path.dirname(GLOSSARY_PATH), exist_ok=True)
        with open(GLOSSARY_PATH, "w", encoding="utf-8") as f:
            json.dump(gloss, f, ensure_ascii=False, indent=2)
        print(f"  → Glossary: {GLOSSARY_PATH} ({len(gloss)} terim)")

    if write_docs:
        write_etl_flow(domains)
        write_toa(domains)
        print(f"  → docs: {DOCS_ETL}, {DOCS_TOA}")


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    run()
