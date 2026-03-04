# TOA (Tablolar / Objeler / Alanlar) — Akbank Metadata Pilot

## TOA Nedir?

Metadata yönetiminde kullanılan üç seviyeli bir veri varlığı hiyerarşisidir:

| Seviye | Karşılık | Örnek |
|--------|----------|-------|
| **T**ablo | Veritabanındaki fiziksel tablo | `DWH_MUSTERI` |
| **O**bje | Tablonun iş bağlamı + meta tanımı | "Akbank müşteri master tablosu" |
| **A**lan | Tablodaki tek bir kolon | `TC_KIMLIK_NO` |

---

## Proje TOA Envanteri

### DWH_MUSTERI

| Alan | Tip | Açıklama (Hedef) |
|------|-----|-----------------|
| MUSTERI_ID | INT | Müşteri tekil tanımlayıcı (PK) |
| TC_KIMLIK_NO | VARCHAR(11) | 11 haneli TC Kimlik numarası |
| AD_SOYAD | VARCHAR(100) | Müşterinin tam adı |
| DOGUM_TARIHI | DATE | Doğum tarihi |
| MUSTERI_TIP_ID | INT | LKP_MUSTERI_TIP → Bireysel / Ticari |
| AKTIF_FLAG | INT | 1=aktif, 0=pasif (soft-delete) |

### DWH_KREDI

| Alan | Tip | Açıklama (Hedef) |
|------|-----|-----------------|
| KREDI_ID | INT | Kredi tekil tanımlayıcı (PK) |
| MUSTERI_ID | INT | FK → DWH_MUSTERI |
| KREDI_TUTAR | DECIMAL(18,2) | Kredi anapara tutarı (TL) |
| KREDI_TIP_ID | INT | LKP_KREDI_TIP → İhtiyaç / Konut / Taşıt |
| VADE_AY | INT | Kredi vade süresi (ay cinsinden) |
| AKTIF_FLAG | INT | 1=aktif kredi, 0=kapalı kredi |

### DWH_ISLEM

| Alan | Tip | Açıklama (Hedef) |
|------|-----|-----------------|
| ISLEM_ID | INT | İşlem tekil tanımlayıcı (PK) |
| MUSTERI_ID | INT | FK → DWH_MUSTERI |
| KREDI_ID | INT | FK → DWH_KREDI |
| ISLEM_TUTAR | DECIMAL(18,2) | İşlem miktarı (TL) |
| ISLEM_TARIHI | DATE | İşlem gerçekleşme tarihi |
| ISLEM_TIP | VARCHAR(50) | İşlem kategorisi (ödeme, tahsilat vb.) |

---

## Metadata Kalite Senaryosu

Bu projedeki kasıtlı bozukluk planı:

| # | Tablo | Senaryo |
|---|-------|---------|
| 1-8 | Genel tablolar | İyi metadata (açıklamalar tam) |
| 3-4 arası | Seçili tablolar | Bazı kolon açıklamaları ≤ 10 karakter |
| 9 | Kötü tablo 1 | Tablo açıklaması yok, neredeyse tüm kolonlar boş |
| 10 | Kötü tablo 2 | Lookup bağlantıları kırık, açıklamalar yetersiz |
