import joblib
import pandas as pd

model = joblib.load("model.pkl")  # Load trained model

# Example new student data (Modify as needed)
new_data = pd.DataFrame([{
    "Attendance (%)": 85,
    "Assignments_Avg": 90,
    "Quizzes_Avg": 88,
    "Participation_Score": 80
}])

prediction = model.predict(new_data)
print(f"📌 Predicted Final Score: {prediction[0]:.2f}")
