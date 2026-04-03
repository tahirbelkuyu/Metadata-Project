# ETL Akışı (otomatik üretim)

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

## Sentetik domain katmanı (19 domain)

Her domain için: `LKP_<DOMAIN>_TIP`, `SRC_<DOMAIN>_FACT`, `STG_<DOMAIN>_FACT`, `DWH_<DOMAIN>_FACT`, `DM_<DOMAIN>_RAPOR`.

**Domain listesi:** `KART`, `ODEME`, `SUBE`, `LIMIT`, `POS`, `ATM`, `KMH`, `TAHSILAT`, `MEVDUAT`, `KIRILIM`, `RISK`, `MUHASEBE`, `KANAL`, `KAMPANYA`, `FATURA`, `TEMINAT`, `KONTRAT`, `CRM`, `EKSTRE`

## Lineage

Kolon bazlı kaynak eşlemesi `lineage/lineage.json` içindedir; Excel için `output/lineage_export.xlsx` (pipeline Adım 8).
