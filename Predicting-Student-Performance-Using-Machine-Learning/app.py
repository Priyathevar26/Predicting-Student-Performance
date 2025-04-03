from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import joblib

app = Flask(__name__)

# Database Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "users.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "d0fcf28f55e4f6c736362c3a2fc7b71c"
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB file limit

# Ensure necessary folders exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

# Home Page
@app.route("/")
def home():
    return render_template("index.html")

# User Registration
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("❌ Username already taken! Try another.", "danger")
            return redirect(url_for("register"))

        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("✅ Account created successfully! Please log in.", "success")
        return redirect(url_for("login"))
    
    return render_template("register.html")

# User Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            flash("✅ Login Successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("❌ Invalid Username or Password!", "danger")
    return render_template("login.html")

# User Dashboard
@app.route("/dashboard")
def dashboard():
    if "user_id" in session:
        return render_template("dashboard.html")
    else:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("login"))

# Logout
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("✅ You have been logged out.", "info")
    return redirect(url_for("login"))

# File Upload Route
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"csv", "xlsx"}

@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            flash("⚠️ No file part!", "danger")
            return redirect(request.url)

        file = request.files["file"]

        if file.filename == "":
            flash("⚠️ No selected file!", "danger")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(filepath)
            flash("✅ File uploaded successfully!", "success")
            return redirect(url_for("upload_file"))

        else:
            flash("⚠️ Invalid file format. Only CSV and XLSX allowed.", "danger")
            return redirect(request.url)

    return render_template("upload.html")

# Student Performance Prediction
@app.route("/predict", methods=["GET", "POST"])
def predict():
    if request.method == "POST":
        try:
            data = request.form

            # Extracting all required features
            midterm_score = float(data.get("midterm_score", 0))
            attendance = float(data.get("attendance", 0))
            test_prep = data.get("test_prep", "").strip().lower()

            # Validate Test Preparation Course input
            if test_prep not in ["completed", "none"]:
                flash("⚠️ Invalid Test Preparation Course! Choose 'Completed' or 'None'.", "danger")
                return redirect(url_for("predict"))

            # Convert 'Completed' and 'None' to numerical values
            test_prep_value = 1 if test_prep == "completed" else 0

            # Add the missing feature (e.g., Assignments_Avg)
            assignments_avg = float(data.get("assignments_avg", 0))  # Change this to the correct feature

            # Ensure we pass exactly 4 features as expected by the model
            features = [midterm_score, attendance, test_prep_value, assignments_avg]

            # Load Model
            model_path = "model.pkl"
            if not os.path.exists(model_path):
                flash("⚠️ Model file not found!", "danger")
                return redirect(url_for("predict"))

            model = joblib.load(model_path)
            prediction = model.predict([features])

            return jsonify({"predicted_score": round(prediction[0], 2)})

        except ValueError:
            flash("⚠️ Invalid input! Please enter valid numbers.", "danger")
            return redirect(url_for("predict"))

        except Exception as e:
            flash(f"⚠️ Error in prediction: {str(e)}", "danger")
            return redirect(url_for("predict"))

    return render_template("predict.html")

# Run Flask App
if __name__ == "__main__":
    app.run(debug=True)
