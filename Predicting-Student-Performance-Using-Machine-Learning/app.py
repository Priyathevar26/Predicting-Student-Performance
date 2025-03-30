from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)

# 🔹 Database Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'users.db')  
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'd0fcf28f55e4f6c736362c3a2fc7b71c'  # Change this to a secure secret key

db = SQLAlchemy(app)

# 🔹 User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# 🔹 Create Database Tables
with app.app_context():
    try:
        db.create_all()
        print("✅ users.db database created successfully!")
    except Exception as e:
        print(f"❌ Database Error: {e}")


# 🔹 Home Route
@app.route("/")
def home():
    return render_template("index.html")


# 🔹 Register Route (Signup)
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        print(f"Received: {username}, {email}, {password}")  # Debugging Step

        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already taken! Try another.", "danger")
            print("Username already exists.")  # Debugging Step
            return redirect(url_for("register"))

        # Create new user
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        print("User registered successfully!")  # Debugging Step
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")
# Ensure register.html exists in /templates




# 🔹 Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        print(f"Received login request: Username={username}, Password={password}")  # Debugging Step

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            flash("✅ Login Successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("❌ Invalid Username or Password!", "danger")

    return render_template("login.html")


# 🔹 Dashboard (Protected Page)
@app.route("/dashboard")
def dashboard():
    if "user_id" in session:
        return render_template("home.html")
    else:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("login"))


# 🔹 Logout Route
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("✅ You have been logged out.", "info")
    return redirect(url_for("login"))


# 🔹 Fix: Predict Route (to prevent BuildError)
@app.route("/predict")
def predict():
    return render_template("predict.html")  # Ensure you create predict.html in the templates folder
# Add this new route to match your template calls
@app.route("/predict_datapoint")
def predict_datapoint():
    return redirect(url_for('predict'))  # Redirects to your existing predict route

if __name__ == "__main__":
    app.run(debug=True)
