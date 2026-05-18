import json
import pandas as pd

QUALITY_PATH = "../output/quality_report.json"
BENCHMARK_PATH = "benchmark_quality.csv"

with open(QUALITY_PATH, "r", encoding="utf-8") as f:
    quality = json.load(f)

# Excel'den gelen CSV bazen tab-separated oluyor, bu yüzden sep=None kullanýyoruz
benchmark = pd.read_csv(BENCHMARK_PATH, sep=None, engine="python")

rows = []

for table in quality:
    table_name = table["table_name"]
    for col in table["columns"]:
        rows.append({
            "table_name": table_name,
            "column_name": col["column_name"],
            "predicted": col["classification"]
        })

pred_df = pd.DataFrame(rows)

df = benchmark.merge(pred_df, on=["table_name", "column_name"], how="left")

correct = (df["true_label"] == df["predicted"]).sum()
total = len(df)
accuracy = correct / total

print("Accuracy:", round(accuracy, 3))

print("\nYanlis tahminler:")
print(df[df["true_label"] != df["predicted"]])