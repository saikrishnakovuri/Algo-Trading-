import pandas as pd

try:
    df_inv = pd.read_csv("data/extended/inventory.csv")
    summary = "\nEXTENDED DATA INVENTORY\n=======================\n"
    summary += df_inv.to_string()
    with open("recovery_results.md", "a", encoding="utf-8") as f:
        f.write("\n\n=== PART 1.2: MAXIMUM DATA INGESTION ===\n")
        f.write(summary)
    print("Summary appended to recovery_results.md")
    print(summary)
except Exception as e:
    print(f"Error: {e}")
