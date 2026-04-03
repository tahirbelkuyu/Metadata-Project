"""
smote_metadata.py
Kalite raporu + ham metadata üzerinden sayısal özellik vektörleri oluşturur,
azınlık sınıfı SMOTE ile dengeler, sentetik kolon örnekleri üretir.

Önkoşul: output/metadata.json ve output/quality_report.json (run_pipeline önce çalışsın)
Çıktı: output/smote_balanced_samples.json, output/smote_features.csv
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

LAYER_CODE = {
    "SOURCE": 0,
    "STAGING": 1,
    "DATA_WAREHOUSE": 2,
    "DATA_MART": 3,
    "LOOKUP": 4,
    "TEMP": 5,
    "UNKNOWN": 6,
}


def _desc_map(metadata: list) -> dict[tuple[str, str], str]:
    m: dict[tuple[str, str], str] = {}
    for t in metadata:
        tn = t.get("table_name", "")
        for c in t.get("columns", []):
            m[(tn, c.get("column_name", ""))] = (c.get("description") or "").strip()
    return m


def _lookup_rule_passed(rule_details: list, rule_id: str) -> float:
    for r in rule_details or []:
        if r.get("rule") == rule_id:
            return 1.0 if r.get("passed") else 0.0
    return 0.5


def build_frame(metadata: list, report: list) -> pd.DataFrame:
    dm = _desc_map(metadata)
    rows = []
    for tbl in report:
        tn = tbl["table_name"]
        layer = tbl.get("layer") or "UNKNOWN"
        for col in tbl.get("columns", []):
            cn = col["column_name"]
            desc = dm.get((tn, cn), "")
            rd = col.get("rule_details") or []
            rows.append(
                {
                    "table_name": tn,
                    "column_name": cn,
                    "layer_code": LAYER_CODE.get(layer, 6),
                    "desc_len": float(len(desc)),
                    "score": float(col.get("score", 0.0)),
                    "failed_rules_n": float(len(col.get("failed_rules") or [])),
                    "has_description": 1.0 if col.get("score", 0) > 0.2 else 0.0,
                    "lookup_ok": _lookup_rule_passed(rd, "LOOKUP_VALID"),
                    "dtype_ok": _lookup_rule_passed(rd, "DATA_TYPE_VALID"),
                    "label": 1 if col.get("classification") == "GOOD" else 0,
                }
            )
    return pd.DataFrame(rows)


FEATURE_COLS = [
    "layer_code",
    "desc_len",
    "score",
    "failed_rules_n",
    "has_description",
    "lookup_ok",
    "dtype_ok",
]


def _resample(Xs: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    from imblearn.over_sampling import RandomOverSampler, SMOTE

    n0 = int((y == 0).sum())
    n1 = int((y == 1).sum())
    minority = min(n0, n1)
    if minority < 2:
        return RandomOverSampler(random_state=42).fit_resample(Xs, y)
    k = min(5, minority - 1)
    if k < 1:
        return RandomOverSampler(random_state=42).fit_resample(Xs, y)
    return SMOTE(random_state=42, k_neighbors=k).fit_resample(Xs, y)


def run_smote_and_export(
    metadata_path: str | None = None,
    report_path: str | None = None,
) -> tuple[int, int]:
    metadata_path = metadata_path or os.path.join(OUTPUT_DIR, "metadata.json")
    report_path = report_path or os.path.join(OUTPUT_DIR, "quality_report.json")

    if not os.path.isfile(metadata_path) or not os.path.isfile(report_path):
        raise FileNotFoundError(
            "metadata.json ve quality_report.json gerekli. Önce pipeline çalıştırın."
        )

    with open(metadata_path, encoding="utf-8") as f:
        metadata = json.load(f)
    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)

    df = build_frame(metadata, report)
    if df.empty:
        raise ValueError("Öğe yok; quality_report boş olabilir.")

    X = df[FEATURE_COLS].values.astype(np.float64)
    y = df["label"].values.astype(np.int64)

    # Kalite motoru tüm kolonları BAD işaretleyebilir → tek sınıf. SMOTE için skor medyanı veya sıra ile ikinci sınıf türetilir.
    if np.unique(y).size < 2:
        scores = df["score"].values
        med = float(np.median(scores))
        y = (scores >= med).astype(np.int64)
        if np.unique(y).size < 2:
            n = len(df)
            order = np.argsort(scores)
            y = np.zeros(n, dtype=np.int64)
            y[order[n // 2:]] = 1
            print("  ℹ️  Skorlar eşit dağılımdı; SMOTE için üst/alt yarı ayrımı kullanıldı.")
        else:
            print(
                f"  ℹ️  GOOD/BAD tek sınıftı; SMOTE için skor ≥ medyan ({med:.3f}) → üst grup etiket 1."
            )

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    Xr, yr = _resample(Xs, y)
    X_inv = scaler.inverse_transform(Xr)

    csv_df = pd.DataFrame(X_inv, columns=FEATURE_COLS)
    csv_df["label"] = yr
    csv_df["classification"] = np.where(yr == 1, "GOOD", "BAD")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    csv_path = os.path.join(OUTPUT_DIR, "smote_features.csv")
    csv_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # Sentetik mi: ölçekli uzayda en yakın orijinale uzaklık
    nn = NearestNeighbors(n_neighbors=1, algorithm="auto").fit(Xs)
    dist, nn_idx = nn.kneighbors(Xr)
    dist = dist.ravel()
    nn_idx = nn_idx.ravel()
    tol = 1e-5

    records: list[dict] = []
    synth_counter = 0
    for i in range(len(Xr)):
        base = df.iloc[int(nn_idx[i])]
        is_synthetic = dist[i] > tol
        if is_synthetic:
            synth_counter += 1
            col_name = f"{base['column_name']}_SMOTE_{synth_counter}"
        else:
            col_name = base["column_name"]

        records.append(
            {
                "synthetic": bool(is_synthetic),
                "table_name": base["table_name"],
                "column_name": col_name,
                "nearest_original_column": base["column_name"],
                "label": int(yr[i]),
                "classification": "GOOD" if yr[i] == 1 else "BAD",
                "features": {c: float(X_inv[i, j]) for j, c in enumerate(FEATURE_COLS)},
            }
        )

    json_path = os.path.join(OUTPUT_DIR, "smote_balanced_samples.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    added = len(Xr) - len(df)
    print(f"  → Orijinal kolon satırı: {len(df)}")
    print(f"  → SMOTE sonrası toplam: {len(csv_df)} (çoğaltılan/üretilen satır: {added})")
    print(f"  → Uzaklık eşiğiyle 'sentetik' işaretlenen: {synth_counter}")
    print(f"  → {csv_path}")
    print(f"  → {json_path}")

    return len(df), len(csv_df)


def main() -> None:
    os.chdir(BASE_DIR)
    try:
        run_smote_and_export()
    except ImportError as e:
        print("imbalanced-learn eksik. Kurulum: pip install -r requirements.txt")
        print(e)
        sys.exit(1)
    except Exception as e:
        print(f"SMOTE hatası: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
