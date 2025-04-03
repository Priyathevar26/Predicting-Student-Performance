import pandas as pd

data_path = "uploads/Students_Grading_Dataset.csv"  # Correct path
try:
    df = pd.read_csv(data_path)
    print("✅ Dataset loaded successfully!")
    print("📌 Available columns:", df.columns.tolist())
except FileNotFoundError:
    print(f"❌ ERROR: {data_path} not found!")

