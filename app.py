from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")  # Use env variable in production

# ===============================
# TiDB / MySQL Database Config
# ===============================
DB_USER = os.environ.get("DB_USER", "tPbPsDAjFwvSaVr.root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "qlV5QsuWKeBkViwZ") 
DB_HOST = os.environ.get("DB_HOST", "gateway01.ap-southeast-1.prod.aws.tidbcloud.com")
DB_PORT = int(os.environ.get("DB_PORT", 4000))
DB_NAME = os.environ.get("DB_NAME", "test")
DB_CA_PATH = os.environ.get("DB_CA_PATH", "ca.pem")  # Ensure this file exists in your project folder

db_config = {
    "user": DB_USER,
    "password": DB_PASSWORD,
    "host": DB_HOST,
    "port": DB_PORT,
    "database": DB_NAME,
    "ssl_ca": DB_CA_PATH
}

# ===============================
# Helper: Get DB Connection
# ===============================
def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn

# ===============================
# Initialize Tables (run once)
# ===============================
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS updates (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            update_text TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

# Initialize tables
init_db()

# ===============================
# Routes
# ===============================
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
            conn.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash("Username already exists. Please choose another.", "error")
        finally:
            cursor.close()
            conn.close()
    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        update_text = request.form['update_text']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO updates (user_id, update_text) VALUES (%s, %s)", (session['user_id'], update_text))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Scrum update saved successfully!", "success")
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.username, up.update_text, up.timestamp
        FROM updates up
        JOIN users u ON up.user_id = u.id
        ORDER BY up.timestamp DESC
    """)
    updates = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("dashboard.html", updates=updates, username=session['username'])

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash("Logged out successfully.", "success")
    return redirect(url_for('login'))

# ===============================
# Run App
# ===============================
if __name__ == '__main__':
    app.run(debug=True)
