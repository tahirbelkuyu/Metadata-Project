# TOA — Tablo / Obje / Alan (otomatik üretim)

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
| KART | LKP + SRC/STG/DWH FACT + DM RAPOR |
| ODEME | LKP + SRC/STG/DWH FACT + DM RAPOR |
| SUBE | LKP + SRC/STG/DWH FACT + DM RAPOR |
| LIMIT | LKP + SRC/STG/DWH FACT + DM RAPOR |
| POS | LKP + SRC/STG/DWH FACT + DM RAPOR |
| ATM | LKP + SRC/STG/DWH FACT + DM RAPOR |
| KMH | LKP + SRC/STG/DWH FACT + DM RAPOR |
| TAHSILAT | LKP + SRC/STG/DWH FACT + DM RAPOR |
| MEVDUAT | LKP + SRC/STG/DWH FACT + DM RAPOR |
| KIRILIM | LKP + SRC/STG/DWH FACT + DM RAPOR |
| RISK | LKP + SRC/STG/DWH FACT + DM RAPOR |
| MUHASEBE | LKP + SRC/STG/DWH FACT + DM RAPOR |
| KANAL | LKP + SRC/STG/DWH FACT + DM RAPOR |
| KAMPANYA | LKP + SRC/STG/DWH FACT + DM RAPOR |
| FATURA | LKP + SRC/STG/DWH FACT + DM RAPOR |
| TEMINAT | LKP + SRC/STG/DWH FACT + DM RAPOR |
| KONTRAT | LKP + SRC/STG/DWH FACT + DM RAPOR |
| CRM | LKP + SRC/STG/DWH FACT + DM RAPOR |
| EKSTRE | LKP + SRC/STG/DWH FACT + DM RAPOR |

**Alan:** Kolon açıklamaları DDL içinde `--` yorumları ve `glossary/glossary.json` ile hizalanır.
