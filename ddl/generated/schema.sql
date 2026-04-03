-- ═══════════════════════════════════════════════════════════
-- PILOT: Source / Staging / DWH / Data Mart / Lookup / Temp
-- (generate_synthetic_corpus.py ile üretilir; kök ddl/*.sql kullanılmaz)
-- ═══════════════════════════════════════════════════════════
/*
Kaynak (Source): CREATE TABLE SRC_ veya SRC_MUSTERI, SRC_KREDI, SRC_KART_FACT vb.
Staging: STG_
DWH: DWH_MUSTERI, DWH_KREDI, DWH_*_FACT vb.
Data Mart: DM1_, DM2_, DM_KART_RAPOR vb.
Lookup: LKP_MUSTERI_TIP, LKP_KREDI_TIP, LKP_KART_TIP vb.
*/
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

-- ═══════════════════════════════════════════════════════════
-- DOMAIN FACT / MART (sentetik genişletme)
-- ═══════════════════════════════════════════════════════════

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE LKP_KART_TIP (
    ID INT PRIMARY KEY, -- 
    ACIKLAMA VARCHAR(200) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE SRC_KART_FACT (
    KART_FACT_ID INT, -- pk alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    MUSTERI_ID INT, -- Kredi ana para tutarıdır; döviz cinsinden saklanır.
    KART_TUTAR DECIMAL(18,2), -- KART_TUTAR kolonu SRC_KART_FACT tablosunda yer alır.
    KART_TIP_ID INT,
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30)
);

-- TABLE_DESC: 
CREATE TABLE STG_KART_FACT (
    KART_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT,
    KART_TUTAR DECIMAL(18,2), -- Alandır.
    KART_TIP_ID INT, -- POS terminal seri numarasıdır; şube kodu ile aynıdır.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DWH_KART_FACT (
    KART_FACT_ID INT, -- KART_FACT_ID kolonu DWH_KART_FACT tablosunda yer alır.
    MUSTERI_ID INT,
    KART_TUTAR DECIMAL(18,2), -- KART_TUTAR kolonu DWH_KART_FACT tablosunda yer alır.
    KART_TIP_ID INT, -- tip_id alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- Alandır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DM_KART_RAPOR (
    RAPOR_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT,
    TOPLAM_KART_TUTAR DECIMAL(18,2),
    RAPOR_TARIHI DATE -- RAPOR_TARIHI kolonu DM_KART_RAPOR tablosunda yer alır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE LKP_ODEME_TIP (
    ID INT PRIMARY KEY, -- ID kolonu LKP_ODEME_TIP tablosunda yer alır.
    ACIKLAMA VARCHAR(200) -- diger alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE SRC_ODEME_FACT (
    ODEME_FACT_ID INT, -- ODEME_FACT_ID kolonu SRC_ODEME_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    ODEME_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    ODEME_TIP_ID INT, -- ODEME_TIP_ID kolonu SRC_ODEME_FACT tablosunda yer alır.
    ISLEM_TARIHI DATE, -- Business attribute `ISLEM_TARIHI` in `SRC_ODEME_FACT`; sourced from staging and validated against operational rules.
    KANAL_KOD VARCHAR(30) -- KANAL_KOD kolonu SRC_ODEME_FACT tablosunda yer alır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE STG_ODEME_FACT (
    ODEME_FACT_ID INT, -- pk alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    MUSTERI_ID INT,
    ODEME_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    ODEME_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE,
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: 
CREATE TABLE DWH_ODEME_FACT (
    ODEME_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- Kredi ana para tutarıdır; döviz cinsinden saklanır.
    ODEME_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    ODEME_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE, -- Alandır.
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DM_ODEME_RAPOR (
    RAPOR_ID INT, -- Rapor satırı açıklama metnidir.
    MUSTERI_ID INT, -- Business attribute `MUSTERI_ID` in `DM_ODEME_RAPOR`; sourced from staging and validated against operational rules.
    TOPLAM_ODEME_TUTAR DECIMAL(18,2), -- Alandır.
    RAPOR_TARIHI DATE -- tarih alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
);

-- TABLE_DESC: 
CREATE TABLE LKP_SUBE_TIP (
    ID INT PRIMARY KEY, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    ACIKLAMA VARCHAR(200) -- ACIKLAMA kolonu LKP_SUBE_TIP tablosunda yer alır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE SRC_SUBE_FACT (
    SUBE_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- Kredi ana para tutarıdır; döviz cinsinden saklanır.
    SUBE_TUTAR DECIMAL(18,2), -- SUBE_TUTAR kolonu SRC_SUBE_FACT tablosunda yer alır.
    SUBE_TIP_ID INT, -- SUBE_TIP_ID kolonu SRC_SUBE_FACT tablosunda yer alır.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30)
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE STG_SUBE_FACT (
    SUBE_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- Alandır.
    SUBE_TUTAR DECIMAL(18,2), -- SUBE_TUTAR kolonu STG_SUBE_FACT tablosunda yer alır.
    SUBE_TIP_ID INT, -- SUBE_TIP_ID kolonu STG_SUBE_FACT tablosunda yer alır.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- Kanal kodu müşteri telefon numarasıdır.
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE DWH_SUBE_FACT (
    SUBE_FACT_ID INT, -- SUBE_FACT_ID kolonu DWH_SUBE_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    SUBE_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    SUBE_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE, -- Business attribute `ISLEM_TARIHI` in `DWH_SUBE_FACT`; sourced from staging and validated against operational rules.
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DM_SUBE_RAPOR (
    RAPOR_ID INT, -- RAPOR_ID kolonu DM_SUBE_RAPOR tablosunda yer alır.
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    TOPLAM_SUBE_TUTAR DECIMAL(18,2), -- Alandır.
    RAPOR_TARIHI DATE -- RAPOR_TARIHI kolonu DM_SUBE_RAPOR tablosunda yer alır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE LKP_LIMIT_TIP (
    ID INT PRIMARY KEY, -- 
    ACIKLAMA VARCHAR(200) -- 
);

-- TABLE_DESC: 
CREATE TABLE SRC_LIMIT_FACT (
    LIMIT_FACT_ID INT, -- Business attribute `LIMIT_FACT_ID` in `SRC_LIMIT_FACT`; sourced from staging and validated against operational rules.
    MUSTERI_ID INT, -- MUSTERI_ID kolonu SRC_LIMIT_FACT tablosunda yer alır.
    LIMIT_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    LIMIT_TIP_ID INT,
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- KANAL_KOD kolonu SRC_LIMIT_FACT tablosunda yer alır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE STG_LIMIT_FACT (
    LIMIT_FACT_ID INT, -- LIMIT_FACT_ID kolonu STG_LIMIT_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- MUSTERI_ID kolonu STG_LIMIT_FACT tablosunda yer alır.
    LIMIT_TUTAR DECIMAL(18,2),
    LIMIT_TIP_ID INT, -- tip_id alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    ISLEM_TARIHI DATE, -- Kredi vadesini gün sayısı olarak tutar (ay değil).
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE DWH_LIMIT_FACT (
    LIMIT_FACT_ID INT, -- Rapor satırı açıklama metnidir.
    MUSTERI_ID INT, -- Alandır.
    LIMIT_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    LIMIT_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE, -- ISLEM_TARIHI kolonu DWH_LIMIT_FACT tablosunda yer alır.
    KANAL_KOD VARCHAR(30) -- KANAL_KOD kolonu DWH_LIMIT_FACT tablosunda yer alır.
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE DM_LIMIT_RAPOR (
    RAPOR_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- Alandır.
    TOPLAM_LIMIT_TUTAR DECIMAL(18,2), -- TOPLAM_LIMIT_TUTAR kolonu DM_LIMIT_RAPOR tablosunda yer alır.
    RAPOR_TARIHI DATE -- RAPOR_TARIHI kolonu DM_LIMIT_RAPOR tablosunda yer alır.
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE LKP_POS_TIP (
    ID INT PRIMARY KEY, -- Rapor satırı açıklama metnidir.
    ACIKLAMA VARCHAR(200) -- Business attribute `ACIKLAMA` in `LKP_POS_TIP`; sourced from staging and validated against operational rules.
);

-- TABLE_DESC: 
CREATE TABLE SRC_POS_FACT (
    POS_FACT_ID INT, -- POS_FACT_ID kolonu SRC_POS_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    POS_TUTAR DECIMAL(18,2), -- POS_TUTAR kolonu SRC_POS_FACT tablosunda yer alır.
    POS_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE,
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: 
CREATE TABLE STG_POS_FACT (
    POS_FACT_ID INT, -- POS_FACT_ID kolonu STG_POS_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- MUSTERI_ID kolonu STG_POS_FACT tablosunda yer alır.
    POS_TUTAR DECIMAL(18,2), -- POS_TUTAR kolonu STG_POS_FACT tablosunda yer alır.
    POS_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE,
    KANAL_KOD VARCHAR(30) -- KANAL_KOD kolonu STG_POS_FACT tablosunda yer alır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DWH_POS_FACT (
    POS_FACT_ID INT,
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    POS_TUTAR DECIMAL(18,2),
    POS_TIP_ID INT, -- POS_TIP_ID kolonu DWH_POS_FACT tablosunda yer alır.
    ISLEM_TARIHI DATE, -- ISLEM_TARIHI kolonu DWH_POS_FACT tablosunda yer alır.
    KANAL_KOD VARCHAR(30) -- Alandır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DM_POS_RAPOR (
    RAPOR_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    TOPLAM_POS_TUTAR DECIMAL(18,2), -- TOPLAM_POS_TUTAR kolonu DM_POS_RAPOR tablosunda yer alır.
    RAPOR_TARIHI DATE -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
);

-- TABLE_DESC: 
CREATE TABLE LKP_ATM_TIP (
    ID INT PRIMARY KEY, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    ACIKLAMA VARCHAR(200) -- diger alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
);

-- TABLE_DESC: 
CREATE TABLE SRC_ATM_FACT (
    ATM_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- MUSTERI_ID kolonu SRC_ATM_FACT tablosunda yer alır.
    ATM_TUTAR DECIMAL(18,2), -- Müşteri segment kodunu tutar; risk skoru ile ilişkilidir.
    ATM_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- Alandır.
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE STG_ATM_FACT (
    ATM_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- Business attribute `MUSTERI_ID` in `STG_ATM_FACT`; sourced from staging and validated against operational rules.
    ATM_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    ATM_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE,
    KANAL_KOD VARCHAR(30) -- Kanal kodu müşteri telefon numarasıdır.
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE DWH_ATM_FACT (
    ATM_FACT_ID INT, -- ATM_FACT_ID kolonu DWH_ATM_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- MUSTERI_ID kolonu DWH_ATM_FACT tablosunda yer alır.
    ATM_TUTAR DECIMAL(18,2),
    ATM_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE, -- Kredi vadesini gün sayısı olarak tutar (ay değil).
    KANAL_KOD VARCHAR(30) -- Alandır.
);

-- TABLE_DESC: 
CREATE TABLE DM_ATM_RAPOR (
    RAPOR_ID INT, -- RAPOR_ID kolonu DM_ATM_RAPOR tablosunda yer alır.
    MUSTERI_ID INT, -- Business attribute `MUSTERI_ID` in `DM_ATM_RAPOR`; sourced from staging and validated against operational rules.
    TOPLAM_ATM_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    RAPOR_TARIHI DATE -- RAPOR_TARIHI kolonu DM_ATM_RAPOR tablosunda yer alır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE LKP_KMH_TIP (
    ID INT PRIMARY KEY, -- Alandır.
    ACIKLAMA VARCHAR(200) -- 
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE SRC_KMH_FACT (
    KMH_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    KMH_TUTAR DECIMAL(18,2), -- tutar alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    KMH_TIP_ID INT, -- POS terminal seri numarasıdır; şube kodu ile aynıdır.
    ISLEM_TARIHI DATE, -- ISLEM_TARIHI kolonu SRC_KMH_FACT tablosunda yer alır.
    KANAL_KOD VARCHAR(30)
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE STG_KMH_FACT (
    KMH_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- MUSTERI_ID kolonu STG_KMH_FACT tablosunda yer alır.
    KMH_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    KMH_TIP_ID INT, -- Alandır.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE DWH_KMH_FACT (
    KMH_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- MUSTERI_ID kolonu DWH_KMH_FACT tablosunda yer alır.
    KMH_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    KMH_TIP_ID INT, -- KMH_TIP_ID kolonu DWH_KMH_FACT tablosunda yer alır.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30)
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DM_KMH_RAPOR (
    RAPOR_ID INT, -- RAPOR_ID kolonu DM_KMH_RAPOR tablosunda yer alır.
    MUSTERI_ID INT, -- MUSTERI_ID kolonu DM_KMH_RAPOR tablosunda yer alır.
    TOPLAM_KMH_TUTAR DECIMAL(18,2), -- TOPLAM_KMH_TUTAR kolonu DM_KMH_RAPOR tablosunda yer alır.
    RAPOR_TARIHI DATE -- RAPOR_TARIHI kolonu DM_KMH_RAPOR tablosunda yer alır.
);

-- TABLE_DESC: 
CREATE TABLE LKP_TAHSILAT_TIP (
    ID INT PRIMARY KEY, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    ACIKLAMA VARCHAR(200) -- Alandır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE SRC_TAHSILAT_FACT (
    TAHSILAT_FACT_ID INT,
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    TAHSILAT_TUTAR DECIMAL(18,2), -- TAHSILAT_TUTAR kolonu SRC_TAHSILAT_FACT tablosunda yer alır.
    TAHSILAT_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE, -- ISLEM_TARIHI kolonu SRC_TAHSILAT_FACT tablosunda yer alır.
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE STG_TAHSILAT_FACT (
    TAHSILAT_FACT_ID INT, -- TAHSILAT_FACT_ID kolonu STG_TAHSILAT_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- MUSTERI_ID kolonu STG_TAHSILAT_FACT tablosunda yer alır.
    TAHSILAT_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    TAHSILAT_TIP_ID INT, -- tip_id alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    ISLEM_TARIHI DATE, -- Alandır.
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DWH_TAHSILAT_FACT (
    TAHSILAT_FACT_ID INT, -- Business attribute `TAHSILAT_FACT_ID` in `DWH_TAHSILAT_FACT`; sourced from staging and validated against operational rules.
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    TAHSILAT_TUTAR DECIMAL(18,2), -- tutar alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    TAHSILAT_TIP_ID INT,
    ISLEM_TARIHI DATE, -- Business attribute `ISLEM_TARIHI` in `DWH_TAHSILAT_FACT`; sourced from staging and validated against operational rules.
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DM_TAHSILAT_RAPOR (
    RAPOR_ID INT, -- Alandır.
    MUSTERI_ID INT, -- MUSTERI_ID kolonu DM_TAHSILAT_RAPOR tablosunda yer alır.
    TOPLAM_TAHSILAT_TUTAR DECIMAL(18,2),
    RAPOR_TARIHI DATE -- Alandır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE LKP_MEVDUAT_TIP (
    ID INT PRIMARY KEY, -- Rapor satırı açıklama metnidir.
    ACIKLAMA VARCHAR(200) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: 
CREATE TABLE SRC_MEVDUAT_FACT (
    MEVDUAT_FACT_ID INT, -- MEVDUAT_FACT_ID kolonu SRC_MEVDUAT_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    MEVDUAT_TUTAR DECIMAL(18,2), -- Business attribute `MEVDUAT_TUTAR` in `SRC_MEVDUAT_FACT`; sourced from staging and validated against operational rules.
    MEVDUAT_TIP_ID INT, -- Business attribute `MEVDUAT_TIP_ID` in `SRC_MEVDUAT_FACT`; sourced from staging and validated against operational rules.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- Business attribute `KANAL_KOD` in `SRC_MEVDUAT_FACT`; sourced from staging and validated against operational rules.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE STG_MEVDUAT_FACT (
    MEVDUAT_FACT_ID INT, -- MEVDUAT_FACT_ID kolonu STG_MEVDUAT_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- Alandır.
    MEVDUAT_TUTAR DECIMAL(18,2), -- tutar alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    MEVDUAT_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- Kanal kodu müşteri telefon numarasıdır.
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE DWH_MEVDUAT_FACT (
    MEVDUAT_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- musteri alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    MEVDUAT_TUTAR DECIMAL(18,2),
    MEVDUAT_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE, -- ISLEM_TARIHI kolonu DWH_MEVDUAT_FACT tablosunda yer alır.
    KANAL_KOD VARCHAR(30) -- KANAL_KOD kolonu DWH_MEVDUAT_FACT tablosunda yer alır.
);

-- TABLE_DESC: 
CREATE TABLE DM_MEVDUAT_RAPOR (
    RAPOR_ID INT, -- Alandır.
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    TOPLAM_MEVDUAT_TUTAR DECIMAL(18,2), -- TOPLAM_MEVDUAT_TUTAR kolonu DM_MEVDUAT_RAPOR tablosunda yer alır.
    RAPOR_TARIHI DATE -- RAPOR_TARIHI kolonu DM_MEVDUAT_RAPOR tablosunda yer alır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE LKP_KIRILIM_TIP (
    ID INT PRIMARY KEY, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    ACIKLAMA VARCHAR(200) -- Alandır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE SRC_KIRILIM_FACT (
    KIRILIM_FACT_ID INT, -- pk alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    MUSTERI_ID INT, -- Business attribute `MUSTERI_ID` in `SRC_KIRILIM_FACT`; sourced from staging and validated against operational rules.
    KIRILIM_TUTAR DECIMAL(18,2), -- KIRILIM_TUTAR kolonu SRC_KIRILIM_FACT tablosunda yer alır.
    KIRILIM_TIP_ID INT, -- POS terminal seri numarasıdır; şube kodu ile aynıdır.
    ISLEM_TARIHI DATE,
    KANAL_KOD VARCHAR(30) -- KANAL_KOD kolonu SRC_KIRILIM_FACT tablosunda yer alır.
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE STG_KIRILIM_FACT (
    KIRILIM_FACT_ID INT, -- Rapor satırı açıklama metnidir.
    MUSTERI_ID INT, -- MUSTERI_ID kolonu STG_KIRILIM_FACT tablosunda yer alır.
    KIRILIM_TUTAR DECIMAL(18,2), -- Alandır.
    KIRILIM_TIP_ID INT, -- Alandır.
    ISLEM_TARIHI DATE,
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE DWH_KIRILIM_FACT (
    KIRILIM_FACT_ID INT, -- Business attribute `KIRILIM_FACT_ID` in `DWH_KIRILIM_FACT`; sourced from staging and validated against operational rules.
    MUSTERI_ID INT, -- musteri alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    KIRILIM_TUTAR DECIMAL(18,2), -- Alandır.
    KIRILIM_TIP_ID INT, -- POS terminal seri numarasıdır; şube kodu ile aynıdır.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DM_KIRILIM_RAPOR (
    RAPOR_ID INT, -- RAPOR_ID kolonu DM_KIRILIM_RAPOR tablosunda yer alır.
    MUSTERI_ID INT,
    TOPLAM_KIRILIM_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    RAPOR_TARIHI DATE -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
);

-- TABLE_DESC: 
CREATE TABLE LKP_RISK_TIP (
    ID INT PRIMARY KEY, -- ID kolonu LKP_RISK_TIP tablosunda yer alır.
    ACIKLAMA VARCHAR(200) -- Kanal kodu müşteri telefon numarasıdır.
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE SRC_RISK_FACT (
    RISK_FACT_ID INT, -- pk alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    RISK_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    RISK_TIP_ID INT,
    ISLEM_TARIHI DATE,
    KANAL_KOD VARCHAR(30) -- KANAL_KOD kolonu SRC_RISK_FACT tablosunda yer alır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE STG_RISK_FACT (
    RISK_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- MUSTERI_ID kolonu STG_RISK_FACT tablosunda yer alır.
    RISK_TUTAR DECIMAL(18,2), -- Business attribute `RISK_TUTAR` in `STG_RISK_FACT`; sourced from staging and validated against operational rules.
    RISK_TIP_ID INT, -- Alandır.
    ISLEM_TARIHI DATE, -- Alandır.
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DWH_RISK_FACT (
    RISK_FACT_ID INT, -- RISK_FACT_ID kolonu DWH_RISK_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- MUSTERI_ID kolonu DWH_RISK_FACT tablosunda yer alır.
    RISK_TUTAR DECIMAL(18,2), -- RISK_TUTAR kolonu DWH_RISK_FACT tablosunda yer alır.
    RISK_TIP_ID INT, -- Alandır.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30)
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DM_RISK_RAPOR (
    RAPOR_ID INT, -- RAPOR_ID kolonu DM_RISK_RAPOR tablosunda yer alır.
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    TOPLAM_RISK_TUTAR DECIMAL(18,2), -- Business attribute `TOPLAM_RISK_TUTAR` in `DM_RISK_RAPOR`; sourced from staging and validated against operational rules.
    RAPOR_TARIHI DATE -- Alandır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE LKP_MUHASEBE_TIP (
    ID INT PRIMARY KEY, -- ID kolonu LKP_MUHASEBE_TIP tablosunda yer alır.
    ACIKLAMA VARCHAR(200) -- ACIKLAMA kolonu LKP_MUHASEBE_TIP tablosunda yer alır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE SRC_MUHASEBE_FACT (
    MUHASEBE_FACT_ID INT, -- MUHASEBE_FACT_ID kolonu SRC_MUHASEBE_FACT tablosunda yer alır.
    MUSTERI_ID INT,
    MUHASEBE_TUTAR DECIMAL(18,2), -- tutar alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    MUHASEBE_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE, -- ISLEM_TARIHI kolonu SRC_MUHASEBE_FACT tablosunda yer alır.
    KANAL_KOD VARCHAR(30) -- KANAL_KOD kolonu SRC_MUHASEBE_FACT tablosunda yer alır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE STG_MUHASEBE_FACT (
    MUHASEBE_FACT_ID INT, -- MUHASEBE_FACT_ID kolonu STG_MUHASEBE_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    MUHASEBE_TUTAR DECIMAL(18,2), -- MUHASEBE_TUTAR kolonu STG_MUHASEBE_FACT tablosunda yer alır.
    MUHASEBE_TIP_ID INT,
    ISLEM_TARIHI DATE, -- ISLEM_TARIHI kolonu STG_MUHASEBE_FACT tablosunda yer alır.
    KANAL_KOD VARCHAR(30) -- KANAL_KOD kolonu STG_MUHASEBE_FACT tablosunda yer alır.
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE DWH_MUHASEBE_FACT (
    MUHASEBE_FACT_ID INT, -- MUHASEBE_FACT_ID kolonu DWH_MUHASEBE_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    MUHASEBE_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    MUHASEBE_TIP_ID INT, -- MUHASEBE_TIP_ID kolonu DWH_MUHASEBE_FACT tablosunda yer alır.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30)
);

-- TABLE_DESC: 
CREATE TABLE DM_MUHASEBE_RAPOR (
    RAPOR_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- MUSTERI_ID kolonu DM_MUHASEBE_RAPOR tablosunda yer alır.
    TOPLAM_MUHASEBE_TUTAR DECIMAL(18,2), -- TOPLAM_MUHASEBE_TUTAR kolonu DM_MUHASEBE_RAPOR tablosunda yer alır.
    RAPOR_TARIHI DATE -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE LKP_KANAL_TIP (
    ID INT PRIMARY KEY, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    ACIKLAMA VARCHAR(200) -- ACIKLAMA kolonu LKP_KANAL_TIP tablosunda yer alır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE SRC_KANAL_FACT (
    KANAL_FACT_ID INT, -- KANAL_FACT_ID kolonu SRC_KANAL_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- Alandır.
    KANAL_TUTAR DECIMAL(18,2), -- KANAL_TUTAR kolonu SRC_KANAL_FACT tablosunda yer alır.
    KANAL_TIP_ID INT, -- Alandır.
    ISLEM_TARIHI DATE, -- ISLEM_TARIHI kolonu SRC_KANAL_FACT tablosunda yer alır.
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: 
CREATE TABLE STG_KANAL_FACT (
    KANAL_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- musteri alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    KANAL_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    KANAL_TIP_ID INT, -- Business attribute `KANAL_TIP_ID` in `STG_KANAL_FACT`; sourced from staging and validated against operational rules.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DWH_KANAL_FACT (
    KANAL_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- musteri alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    KANAL_TUTAR DECIMAL(18,2),
    KANAL_TIP_ID INT, -- KANAL_TIP_ID kolonu DWH_KANAL_FACT tablosunda yer alır.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- diger alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DM_KANAL_RAPOR (
    RAPOR_ID INT, -- Rapor satırı açıklama metnidir.
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    TOPLAM_KANAL_TUTAR DECIMAL(18,2),
    RAPOR_TARIHI DATE -- Kredi vadesini gün sayısı olarak tutar (ay değil).
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE LKP_KAMPANYA_TIP (
    ID INT PRIMARY KEY, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    ACIKLAMA VARCHAR(200) -- ACIKLAMA kolonu LKP_KAMPANYA_TIP tablosunda yer alır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE SRC_KAMPANYA_FACT (
    KAMPANYA_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    KAMPANYA_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    KAMPANYA_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- Alandır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE STG_KAMPANYA_FACT (
    KAMPANYA_FACT_ID INT, -- KAMPANYA_FACT_ID kolonu STG_KAMPANYA_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- Kredi ana para tutarıdır; döviz cinsinden saklanır.
    KAMPANYA_TUTAR DECIMAL(18,2), -- KAMPANYA_TUTAR kolonu STG_KAMPANYA_FACT tablosunda yer alır.
    KAMPANYA_TIP_ID INT, -- Business attribute `KAMPANYA_TIP_ID` in `STG_KAMPANYA_FACT`; sourced from staging and validated against operational rules.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: 
CREATE TABLE DWH_KAMPANYA_FACT (
    KAMPANYA_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    KAMPANYA_TUTAR DECIMAL(18,2), -- Business attribute `KAMPANYA_TUTAR` in `DWH_KAMPANYA_FACT`; sourced from staging and validated against operational rules.
    KAMPANYA_TIP_ID INT, -- POS terminal seri numarasıdır; şube kodu ile aynıdır.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: 
CREATE TABLE DM_KAMPANYA_RAPOR (
    RAPOR_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- MUSTERI_ID kolonu DM_KAMPANYA_RAPOR tablosunda yer alır.
    TOPLAM_KAMPANYA_TUTAR DECIMAL(18,2), -- TOPLAM_KAMPANYA_TUTAR kolonu DM_KAMPANYA_RAPOR tablosunda yer alır.
    RAPOR_TARIHI DATE -- Alandır.
);

-- TABLE_DESC: 
CREATE TABLE LKP_FATURA_TIP (
    ID INT PRIMARY KEY, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    ACIKLAMA VARCHAR(200) -- Kanal kodu müşteri telefon numarasıdır.
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE SRC_FATURA_FACT (
    FATURA_FACT_ID INT, -- FATURA_FACT_ID kolonu SRC_FATURA_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- musteri alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    FATURA_TUTAR DECIMAL(18,2), -- Müşteri segment kodunu tutar; risk skoru ile ilişkilidir.
    FATURA_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE, -- Alandır.
    KANAL_KOD VARCHAR(30)
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE STG_FATURA_FACT (
    FATURA_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- MUSTERI_ID kolonu STG_FATURA_FACT tablosunda yer alır.
    FATURA_TUTAR DECIMAL(18,2),
    FATURA_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE, -- Business attribute `ISLEM_TARIHI` in `STG_FATURA_FACT`; sourced from staging and validated against operational rules.
    KANAL_KOD VARCHAR(30) -- Alandır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DWH_FATURA_FACT (
    FATURA_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    FATURA_TUTAR DECIMAL(18,2), -- Müşteri segment kodunu tutar; risk skoru ile ilişkilidir.
    FATURA_TIP_ID INT,
    ISLEM_TARIHI DATE, -- tarih alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    KANAL_KOD VARCHAR(30) -- KANAL_KOD kolonu DWH_FATURA_FACT tablosunda yer alır.
);

-- TABLE_DESC: 
CREATE TABLE DM_FATURA_RAPOR (
    RAPOR_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- Alandır.
    TOPLAM_FATURA_TUTAR DECIMAL(18,2), -- TOPLAM_FATURA_TUTAR kolonu DM_FATURA_RAPOR tablosunda yer alır.
    RAPOR_TARIHI DATE -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
);

-- TABLE_DESC: 
CREATE TABLE LKP_TEMINAT_TIP (
    ID INT PRIMARY KEY, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    ACIKLAMA VARCHAR(200) -- ACIKLAMA kolonu LKP_TEMINAT_TIP tablosunda yer alır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE SRC_TEMINAT_FACT (
    TEMINAT_FACT_ID INT, -- TEMINAT_FACT_ID kolonu SRC_TEMINAT_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- Kredi ana para tutarıdır; döviz cinsinden saklanır.
    TEMINAT_TUTAR DECIMAL(18,2), -- TEMINAT_TUTAR kolonu SRC_TEMINAT_FACT tablosunda yer alır.
    TEMINAT_TIP_ID INT, -- Business attribute `TEMINAT_TIP_ID` in `SRC_TEMINAT_FACT`; sourced from staging and validated against operational rules.
    ISLEM_TARIHI DATE, -- ISLEM_TARIHI kolonu SRC_TEMINAT_FACT tablosunda yer alır.
    KANAL_KOD VARCHAR(30) -- KANAL_KOD kolonu SRC_TEMINAT_FACT tablosunda yer alır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE STG_TEMINAT_FACT (
    TEMINAT_FACT_ID INT, -- pk alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    TEMINAT_TUTAR DECIMAL(18,2), -- TEMINAT_TUTAR kolonu STG_TEMINAT_FACT tablosunda yer alır.
    TEMINAT_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE, -- ISLEM_TARIHI kolonu STG_TEMINAT_FACT tablosunda yer alır.
    KANAL_KOD VARCHAR(30) -- diger alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DWH_TEMINAT_FACT (
    TEMINAT_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    TEMINAT_TUTAR DECIMAL(18,2), -- Müşteri segment kodunu tutar; risk skoru ile ilişkilidir.
    TEMINAT_TIP_ID INT, -- TEMINAT_TIP_ID kolonu DWH_TEMINAT_FACT tablosunda yer alır.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- Business attribute `KANAL_KOD` in `DWH_TEMINAT_FACT`; sourced from staging and validated against operational rules.
);

-- TABLE_DESC: Rapor tablosu.
CREATE TABLE DM_TEMINAT_RAPOR (
    RAPOR_ID INT,
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    TOPLAM_TEMINAT_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    RAPOR_TARIHI DATE -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE LKP_KONTRAT_TIP (
    ID INT PRIMARY KEY, -- Alandır.
    ACIKLAMA VARCHAR(200) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE SRC_KONTRAT_FACT (
    KONTRAT_FACT_ID INT, -- pk alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    MUSTERI_ID INT,
    KONTRAT_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    KONTRAT_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- Alandır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE STG_KONTRAT_FACT (
    KONTRAT_FACT_ID INT, -- KONTRAT_FACT_ID kolonu STG_KONTRAT_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- Business attribute `MUSTERI_ID` in `STG_KONTRAT_FACT`; sourced from staging and validated against operational rules.
    KONTRAT_TUTAR DECIMAL(18,2), -- tutar alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    KONTRAT_TIP_ID INT, -- KONTRAT_TIP_ID kolonu STG_KONTRAT_FACT tablosunda yer alır.
    ISLEM_TARIHI DATE, -- ISLEM_TARIHI kolonu STG_KONTRAT_FACT tablosunda yer alır.
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: 
CREATE TABLE DWH_KONTRAT_FACT (
    KONTRAT_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- musteri alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    KONTRAT_TUTAR DECIMAL(18,2), -- KONTRAT_TUTAR kolonu DWH_KONTRAT_FACT tablosunda yer alır.
    KONTRAT_TIP_ID INT, -- KONTRAT_TIP_ID kolonu DWH_KONTRAT_FACT tablosunda yer alır.
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- diger alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DM_KONTRAT_RAPOR (
    RAPOR_ID INT, -- Business attribute `RAPOR_ID` in `DM_KONTRAT_RAPOR`; sourced from staging and validated against operational rules.
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    TOPLAM_KONTRAT_TUTAR DECIMAL(18,2), -- Alandır.
    RAPOR_TARIHI DATE -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
);

-- TABLE_DESC: 
CREATE TABLE LKP_CRM_TIP (
    ID INT PRIMARY KEY, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    ACIKLAMA VARCHAR(200) -- Kanal kodu müşteri telefon numarasıdır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE SRC_CRM_FACT (
    CRM_FACT_ID INT, -- Alandır.
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    CRM_TUTAR DECIMAL(18,2), -- Alandır.
    CRM_TIP_ID INT, -- Business attribute `CRM_TIP_ID` in `SRC_CRM_FACT`; sourced from staging and validated against operational rules.
    ISLEM_TARIHI DATE,
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE STG_CRM_FACT (
    CRM_FACT_ID INT,
    MUSTERI_ID INT, -- Kredi ana para tutarıdır; döviz cinsinden saklanır.
    CRM_TUTAR DECIMAL(18,2), -- Alandır.
    CRM_TIP_ID INT, -- İlgili sözlük tablosuna (LKP) referans veren tip tanımlayıcıdır; iş anlamı kod listesi ile çözülür.
    ISLEM_TARIHI DATE,
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: 
CREATE TABLE DWH_CRM_FACT (
    CRM_FACT_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- MUSTERI_ID kolonu DWH_CRM_FACT tablosunda yer alır.
    CRM_TUTAR DECIMAL(18,2), -- İlgili işlem veya ürün için TL cinsinden tutarı ifade eder; kur dönüşümü uygulanmamıştır.
    CRM_TIP_ID INT, -- tip_id alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    ISLEM_TARIHI DATE, -- ISLEM_TARIHI kolonu DWH_CRM_FACT tablosunda yer alır.
    KANAL_KOD VARCHAR(30) -- Operasyonel kanal veya statü bilgisini tutar; raporlama filtrelerinde kullanılır.
);

-- TABLE_DESC: 
CREATE TABLE DM_CRM_RAPOR (
    RAPOR_ID INT,
    MUSTERI_ID INT, -- Müşteri ana veri tablosundaki tekil müşteri anahtarına (FK) işaret eder.
    TOPLAM_CRM_TUTAR DECIMAL(18,2), -- TOPLAM_CRM_TUTAR kolonu DM_CRM_RAPOR tablosunda yer alır.
    RAPOR_TARIHI DATE -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE LKP_EKSTRE_TIP (
    ID INT PRIMARY KEY, -- ID kolonu LKP_EKSTRE_TIP tablosunda yer alır.
    ACIKLAMA VARCHAR(200) -- Kanal kodu müşteri telefon numarasıdır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE SRC_EKSTRE_FACT (
    EKSTRE_FACT_ID INT, -- EKSTRE_FACT_ID kolonu SRC_EKSTRE_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- Alandır.
    EKSTRE_TUTAR DECIMAL(18,2),
    EKSTRE_TIP_ID INT, -- Alandır.
    ISLEM_TARIHI DATE, -- Alandır.
    KANAL_KOD VARCHAR(30) -- Kanal kodu müşteri telefon numarasıdır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE STG_EKSTRE_FACT (
    EKSTRE_FACT_ID INT, -- Alandır.
    MUSTERI_ID INT, -- musteri alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    EKSTRE_TUTAR DECIMAL(18,2), -- EKSTRE_TUTAR kolonu STG_EKSTRE_FACT tablosunda yer alır.
    EKSTRE_TIP_ID INT, -- Alandır.
    ISLEM_TARIHI DATE, -- Business attribute `ISLEM_TARIHI` in `STG_EKSTRE_FACT`; sourced from staging and validated against operational rules.
    KANAL_KOD VARCHAR(30) -- diger alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
);

-- TABLE_DESC: 
CREATE TABLE DWH_EKSTRE_FACT (
    EKSTRE_FACT_ID INT, -- EKSTRE_FACT_ID kolonu DWH_EKSTRE_FACT tablosunda yer alır.
    MUSTERI_ID INT, -- MUSTERI_ID kolonu DWH_EKSTRE_FACT tablosunda yer alır.
    EKSTRE_TUTAR DECIMAL(18,2),
    EKSTRE_TIP_ID INT,
    ISLEM_TARIHI DATE, -- İşlemin veya kaydın geçerli olduğu takvim tarihidir; operasyonel gün sonu ile uyumludur.
    KANAL_KOD VARCHAR(30) -- Kanal kodu müşteri telefon numarasıdır.
);

-- TABLE_DESC: Bankacılık operasyonel veri ambarı kapsamında üretilen sentetik tablo; ETL ile beslenir ve veri kalitesi kurallarına tabidir.
CREATE TABLE DM_EKSTRE_RAPOR (
    RAPOR_ID INT, -- Tablo içinde satırı benzersiz tanımlayan teknik anahtar (surrogate PK).
    MUSTERI_ID INT, -- musteri alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
    TOPLAM_EKSTRE_TUTAR DECIMAL(18,2),
    RAPOR_TARIHI DATE -- tarih alanı: iş kuralına göre doldurulur (typo testi: tutr, trh).
);
