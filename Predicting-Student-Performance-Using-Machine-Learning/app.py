# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime
from pathlib import Path
from io import StringIO

app = Flask(__name__)

# Database Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'd0fcf28f55e4f6c736362c3a2fc7b71c'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB file limit

db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# DataFile Model for storing uploaded datasets
class DataFile(db.Model):
    id = db.Column(db.String(36), primary_key=True)  # UUID
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    filename = db.Column(db.String(120))
    data = db.Column(db.Text)  # JSON data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create database tables
with app.app_context():
    try:
        db.create_all()
        print("✅ users.db database created successfully!")
    except Exception as e:
        print(f"❌ Database Error: {e}")

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv', 'xlsx'}

def clean_data(df):
    """Clean and standardize the dataframe"""
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('(%)', 'percent')
    df = df.replace(['nan', 'NaN', ''], pd.NA)
    
    # Convert numeric columns
    numeric_cols = ['attendance_percent', 'midterm_score', 'final_score', 
                   'assignments_avg', 'quizzes_avg', 'participation_score']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already taken! Try another.", "danger")
            return redirect(url_for("register"))

        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

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

@app.route("/dashboard")
def dashboard():
    if "user_id" in session:
        return render_template("home.html")
    else:
        flash("⚠️ Please log in first.", "warning")
        return redirect(url_for("login"))

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("✅ You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route("/predict", methods=["GET", "POST"])
def predict():
    if "user_id" not in session:
        flash("Please login first", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            # Convert inputs safely
            def to_float(x, default=0.0):
                try: return float(x) if x not in [None, "", "None"] else default
                except: return default

            student_data = {
                "name": request.form.get("name", "Student"),
                "attendance_percent": to_float(request.form.get("attendance_percent")),
                "midterm_score": to_float(request.form.get("midterm_score")),
                "private_class": 1 if request.form.get("private_class") == "YES" else 0,
                "physical_fitness": 1 if request.form.get("physical_fitness") == "YES" else 0,
                "mental_fitness": 1 if request.form.get("mental_fitness") == "YES" else 0,
                "subject1_duration": to_float(request.form.get("subject1_duration")),
                "subject2_duration": to_float(request.form.get("subject2_duration")),
                "test_preparation_course": 1 if request.form.get("test_preparation_course") == "completed" else 0,
                "participation_score": to_float(request.form.get("participation_score"))
            }
            
            # Load model
            model_path = os.path.join(app.config['UPLOAD_FOLDER'], f"model_{session.get('current_file_id')}.pkl")
            model_data = joblib.load(model_path)
            model = model_data['model']
            
            # Prepare features in EXACT order used during training
            features = [
                student_data['attendance_percent'],
                student_data['midterm_score'],
                student_data['private_class'],
                student_data['physical_fitness'],
                student_data['mental_fitness'],
                student_data['subject1_duration'],
                student_data['subject2_duration'],
                student_data['test_preparation_course'],
                student_data['participation_score']
            ]
            
            # Validate feature count
            if len(features) != 9:
                raise ValueError(f"Expected 9 features, got {len(features)}")
            
            prediction = model.predict([features])[0]
            
            # Performance evaluation
            if prediction >= 80:
                performance = "Excellent"
                feedback = "Your performance is excellent! Keep up the good work."
            elif prediction >= 60:
                performance = "Good"
                feedback = "According to our analysis, your performance is good. You just need to practise enough to remain in touch with the subjects and not lose your hold. Keep it up."
            else:
                performance = "Needs Improvement"
                feedback = "Your performance needs improvement. Consider spending more time studying and seek help from teachers if needed."
            
            return render_template("prediction_results.html",
                                 student_data=student_data,
                                 score=round(prediction, 2),
                                 performance=performance,
                                 feedback=feedback)
        
        except Exception as e:
            flash(f"Error during prediction: {str(e)}", "danger")
            return redirect(url_for("predict"))
    
    return render_template("detailed_predict.html")

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # Read file
                if file.filename.endswith('.csv'):
                    df = pd.read_csv(file)
                else:
                    df = pd.read_excel(file)
                
                # Clean data
                df = clean_data(df)
                
                # Store in database
                data_file = DataFile(
                    id=str(uuid.uuid4()),
                    user_id=session['user_id'],
                    filename=secure_filename(file.filename),
                    data=df.to_json()
                )
                db.session.add(data_file)
                db.session.commit()
                
                session['current_file_id'] = data_file.id
                flash('File uploaded and processed successfully!', 'success')
                return redirect(url_for('preview'))
            
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'danger')
                return redirect(url_for('upload_file'))
    
    return render_template('upload.html')

@app.route('/preview')
def preview():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
        
    if 'current_file_id' not in session:
        flash('Please upload a file first', 'warning')
        return redirect(url_for('upload_file'))
    
    try:
        data_file = db.session.get(DataFile, session['current_file_id'])
        if not data_file:
            flash('File not found', 'danger')
            return redirect(url_for('upload_file'))
        
        df = pd.read_json(StringIO(data_file.data))
        columns = [col for col in df.columns if col != 'email']
        
        return render_template('preview.html', 
                            students=df.head(100).to_dict('records'),
                            columns=columns,
                            filename=data_file.filename)
    
    except Exception as e:
        flash(f'Error loading data: {str(e)}', 'danger')
        return redirect(url_for('upload_file'))
@app.route('/train_model', methods=['POST'])
def train_model():
    try:
        data_file = db.session.get(DataFile, session['current_file_id'])
        df = pd.read_json(StringIO(data_file.data))
        df = clean_data(df)
        
        # Define your features list explicitly
        features = [
            'attendance_percent',
            'midterm_score',
            'private_class',
            'physical_fitness',
            'mental_fitness',
            'subject1_duration',
            'subject2_duration',
            'test_preparation_course',
            'participation_score'
        ]
        
        # Filter for only available features
        available_features = [f for f in features if f in df.columns]
        
        if not available_features:
            return jsonify({'error': 'No valid features found in dataset'}), 400
            
        # Handle missing values
        for col in available_features:
            df[col] = df[col].fillna(df[col].median())
        
        X = df[available_features]
        y = df['final_score']
        
        # Rest of your training code...
        
        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train model
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        # Save model
        model_path = os.path.join(app.config['UPLOAD_FOLDER'], f"model_{data_file.id}.pkl")
        joblib.dump(model, model_path)
        
        # Feature importance
        importance = dict(zip(features, model.feature_importances_))
        
        return jsonify({
            'success': True,
            'message': 'Model trained successfully!',
            'r2_score': model.score(X_test, y_test),
            'feature_importance': importance,
            'sample_size': len(df),
            'redirect': url_for('predict')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)