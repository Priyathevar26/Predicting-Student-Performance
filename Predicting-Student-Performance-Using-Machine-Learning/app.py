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
            return redirect(url_for("upload_file"))
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

@app.route("/predict")
def predict():
    return render_template("predict.html")

@app.route("/predict_datapoint")
def predict_datapoint():
    return redirect(url_for('predict'))

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
        data_file = DataFile.query.get(session['current_file_id'])
        if not data_file:
            flash('File not found', 'danger')
            return redirect(url_for('upload_file'))
        
        df = pd.read_json(data_file.data)
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
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    if 'current_file_id' not in session:
        return jsonify({'error': 'No data available for training'}), 400
    
    try:
        data_file = DataFile.query.get(session['current_file_id'])
        df = pd.read_json(data_file.data)
        df = clean_data(df)
        
        # Data cleaning
        df = df.dropna(subset=['final_score'])  # Drop rows missing target
        
        # Feature selection
        features = ['attendance_percent', 'midterm_score', 
                   'assignments_avg', 'quizzes_avg', 'participation_score']
        
        # Handle missing values in features
        for col in features:
            if col in df.columns:
                df[col] = df[col].fillna(df[col].median())
        
        X = df[features]
        y = df['final_score']
        
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
            'sample_size': len(df)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)