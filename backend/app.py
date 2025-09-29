from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import random
import os
import pandas as pd
# If you want PDF parsing: pip install PyPDF2
from PyPDF2 import PdfReader  

app = Flask(__name__)
CORS(app)

DB_FILE = "interview_ai.db"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ========== DB INIT ==========
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT 'user'
        )
    """)

    # Questions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            difficulty TEXT
        )
    """)

    # Answers table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            question_id INTEGER,
            answer TEXT,
            feedback TEXT,
            confidence REAL,
            FOREIGN KEY (question_id) REFERENCES questions (id)
        )
    """)

    conn.commit()
    conn.close()


# ========== HELPERS ==========
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# ========== AUTH ROUTES ==========
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    username, password = data["username"], data["password"]

    conn = get_db()
    cur = conn.cursor()

    try:
        role = "admin" if username == "admin" else "user"
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    (username, password, role))
        conn.commit()
        return jsonify({"message": "Signup successful!", "role": role})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400
    finally:
        conn.close()


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username, password = data["username"], data["password"]

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT username, role FROM users WHERE username=? AND password=?",
                (username, password))
    row = cur.fetchone()
    conn.close()

    if row:
        return jsonify({"username": row["username"], "role": row["role"]})
    else:
        return jsonify({"error": "Invalid credentials"}), 401


# ========== QUESTION ROUTES ==========
@app.route("/get_question", methods=["GET"])
def get_question():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, question FROM questions ORDER BY RANDOM() LIMIT 1")
    row = cur.fetchone()
    conn.close()

    if row:
        return jsonify({"id": row["id"], "question": row["question"]})
    else:
        return jsonify({"error": "No questions available"}), 404


@app.route("/admin/add_question", methods=["POST"])
def add_question():
    data = request.json
    question, difficulty = data["question"], data.get("difficulty", "medium")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO questions (question, difficulty) VALUES (?, ?)", (question, difficulty))
    conn.commit()
    conn.close()

    return jsonify({"message": "Question added successfully"})


@app.route("/admin/get_all_users", methods=["GET"])
def get_all_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT username, role FROM users")
    rows = cur.fetchall()
    conn.close()

    return jsonify([{"username": r["username"], "role": r["role"]} for r in rows])


# ========== BULK UPLOAD QUESTIONS ==========
@app.route("/admin/upload_questions", methods=["POST"])
def upload_questions():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    conn = get_db()
    cur = conn.cursor()

    # CSV upload
    if file.filename.endswith(".csv"):
        try:
            df = pd.read_csv(filepath)
            for _, row in df.iterrows():
                question = row.get("Question")
                difficulty = row.get("Difficulty", "medium")
                if question:
                    cur.execute("INSERT INTO questions (question, difficulty) VALUES (?, ?)", 
                                (question, difficulty))
            conn.commit()
            return jsonify({"message": "CSV uploaded and questions added!"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # PDF upload
    elif file.filename.endswith(".pdf"):
        try:
            reader = PdfReader(filepath)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    for line in text.split("\n"):
                        if line.strip():
                            cur.execute("INSERT INTO questions (question, difficulty) VALUES (?, ?)", 
                                        (line.strip(), "medium"))
            conn.commit()
            return jsonify({"message": "PDF uploaded and questions added!"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    else:
        return jsonify({"error": "Only CSV or PDF allowed"}), 400
    conn.close()


# ========== ANSWERS & HISTORY ==========
@app.route("/submit_answer", methods=["POST"])
def submit_answer():
    data = request.json
    username, qid, answer = data["username"], data["question_id"], data["answer"]

    # Dummy feedback + confidence
    feedback = "Good attempt!" if len(answer) > 5 else "Answer too short."
    confidence = round(random.uniform(0.5, 1.0), 2)

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO answers (username, question_id, answer, feedback, confidence) VALUES (?, ?, ?, ?, ?)",
        (username, qid, answer, feedback, confidence)
    )
    conn.commit()
    conn.close()

    return jsonify({"feedback": feedback, "confidence": confidence})


@app.route("/get_history/<username>", methods=["GET"])
def get_history(username):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT q.question, a.answer, a.feedback
        FROM answers a
        JOIN questions q ON a.question_id = q.id
        WHERE a.username=?
    """, (username,))
    rows = cur.fetchall()
    conn.close()

    return jsonify([{"question": r["question"], "answer": r["answer"], "feedback": r["feedback"]} for r in rows])


# ========== MAIN ==========
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
