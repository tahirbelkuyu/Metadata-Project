# Metadata-Project

Metadata kalite pipeline’ı: DDL’den tablo/kolon metadata’sı, kurallar, glossary, lookup, SMOTE, lineage → Excel.

## Çalıştırma

```bash
pip install -r requirements.txt
python scripts/run_pipeline.py
```

- **Tek şema kaynağı:** `ddl/generated/schema.sql` (Adım 0’da üretilir; pilot + sentetik domain tabloları).
- **Adım 0** ayrıca yazar: `lineage/lineage.json`, `glossary/glossary.json`, `docs/etl_flow.md`, `docs/toa.md`.

Şema veya domain listesini değiştirmek için: `scripts/generate_synthetic_corpus.py` içindeki `DOMAINS` ve `CORE_PILOT_SQL`.

## Klasörler

| Klasör | İçerik |
|--------|--------|
| `ddl/generated/` | `schema.sql` (yalnızca generator çıktısı) |
| `scripts/` | Pipeline ve yardımcı modüller |
| `config/` | `rules.yaml` |
| `glossary/` | `glossary.json` (Adım 0 ile güncellenir) |
| `lineage/` | `lineage.json` |
| `docs/` | ETL ve TOA (Adım 0 ile güncellenir) |
| `output/` | Pipeline çıktıları (yerel; `.gitignore`) |
