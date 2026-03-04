# ETL Akış Dökümanı — Akbank Metadata Pilot

## Genel Bakış

Bu projede **5 katmanlı bir ETL mimarisi** kullanılmaktadır:

```
[Core Banking]
     │  ← Ham veri (olduğu gibi)
     ▼
[SOURCE — SRC_*]
     │  ← Temizleme, tip dönüşümü, lookup join
     ▼
[STAGING — STG_*]
     │  ← İş kuralları, doğrulama, birleştirme
     ▼
[DATA WAREHOUSE — DWH_*]
     │  ← Raporlama için özetleme, agregasyon
     ▼
[DATA MART — DM_*]

[LOOKUP — LKP_*] → Tüm katmanlarda referans olarak kullanılır
```

---

## Katmanlar

### Source (SRC_*)
- **Kaynak:** Core Banking sistemi
- **İçerik:** Ham, dönüşüm uygulanmamış veri
- **Tablolar:** `SRC_MUSTERI`, `SRC_KREDI`
- **Not:** Alan adları kaynak sistemin kendi adlandırmasını taşır (`AD`, `SOYAD` ayrı; `KREDI_AMT` İngilizce)

### Staging (STG_*)
- **Görev:** Temizleme + Dönüştürme
- **Dönüşümler:**
  - `AD + SOYAD` → `AD_SOYAD` (birleştirme)
  - `MUSTERI_TIP` → `MUSTERI_TIP_ID` (lookup normalizasyonu)
  - `KREDI_AMT` → `KREDI_TUTAR` (Türkçe isim standardı)
  - `LOAD_DATE` eklenir (yükleme zamanı damgası)
- **Tablolar:** `STG_MUSTERI`, `STG_KREDI`

### Data Warehouse (DWH_*)
- **Görev:** İş kuralları, foreign key ilişkileri, kalıcı depo
- **Özellikler:** Primary key tanımlı, `AKTIF_FLAG` ile soft-delete
- **Tablolar:** `DWH_MUSTERI`, `DWH_KREDI`, `DWH_ISLEM`

### Data Mart (DM_*)
- **Görev:** Raporlamaya hazır özet tablolar
- **Tablolar:** `DM1_KREDI_RAPOR`, `DM2_SEGMENT_ANALIZ`

### Lookup (LKP_*)
- **Görev:** Kod ↔ Açıklama eşleştirme
- **Tablolar:** `LKP_MUSTERI_TIP`, `LKP_KREDI_TIP`

---

## Alan Dönüşüm Haritası (SRC → DWH)

| Source Alanı | DWH Alanı | Dönüşüm |
|---|---|---|
| `SRC_MUSTERI.AD` + `.SOYAD` | `DWH_MUSTERI.AD_SOYAD` | Birleştirme |
| `SRC_MUSTERI.MUSTERI_TIP` | `DWH_MUSTERI.MUSTERI_TIP_ID` | LKP_MUSTERI_TIP join |
| `SRC_KREDI.KREDI_AMT` | `DWH_KREDI.KREDI_TUTAR` | Yeniden adlandırma |
| `SRC_KREDI.KREDI_TIP` | `DWH_KREDI.KREDI_TIP_ID` | LKP_KREDI_TIP join |
