import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

# 🔹 Load dataset
data_path = "Students_Grading_Dataset.csv"
try:
    df = pd.read_csv(data_path)
    print("✅ Dataset loaded successfully!")
except FileNotFoundError:
    print(f"❌ ERROR: {data_path} not found!")
    exit()

# 🔹 Define Features & Target Variable (Updated Column Names)
features = ["Attendance (%)", "Assignments_Avg", "Quizzes_Avg", "Participation_Score"]
target = "Final_Score"

# 🔹 Check if required columns exist
missing_cols = [col for col in features + [target] if col not in df.columns]
if missing_cols:
    print(f"❌ ERROR: Missing columns in dataset: {missing_cols}")
    exit()

X = df[features]
y = df[target]

# 🔹 Split Data (80% Train, 20% Test)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 🔹 Train Model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 🔹 Evaluate Model
y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
print(f"✅ Model Trained Successfully! MAE: {mae:.2f}")

# 🔹 Save Model
model_path = "model.pkl"
joblib.dump(model, model_path)
print(f"✅ Model saved as {model_path}")
