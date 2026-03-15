import sqlite3
from datetime import datetime
import os

# Using the filename from your existing setup
DB_FILE = "interview_log.db"

def initialize_db():
    """Creates the database tables if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_description TEXT NOT NULL,
        interview_mode TEXT NOT NULL, 
        start_time TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        interview_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        feedback TEXT NOT NULL,
        score INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (interview_id) REFERENCES interviews (id)
    );
    """)

    conn.commit()
    conn.close()

def create_interview_session(job_description, interview_mode):
    """Logs a new interview session and returns its unique ID."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    start_time = datetime.now().isoformat()

    cursor.execute(
        "INSERT INTO interviews (job_description, interview_mode, start_time) VALUES (?, ?, ?)",
        (job_description, interview_mode, start_time)
    )

    conn.commit()
    session_id = cursor.lastrowid
    conn.close()
    return session_id

def save_record(interview_id, question, answer, feedback, score):
    """Saves a single Q&A record linked to a specific session."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()

    cursor.execute(
        "INSERT INTO records (interview_id, question, answer, feedback, score, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (interview_id, question, answer, feedback, score, timestamp)
    )

    conn.commit()
    conn.close()

def get_all_sessions():
    """
    FIXED: Uses a SQL LEFT JOIN to calculate 'question_count' 
    and 'average_score' for each interview session.
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        # We join interviews (i) with records (r) to count entries and average scores
        query = """
        SELECT 
            i.id, 
            i.job_description, 
            i.interview_mode, 
            i.start_time,
            COUNT(r.id) as question_count, 
            IFNULL(AVG(r.score), 0) as average_score
        FROM interviews i
        LEFT JOIN records r ON i.id = r.interview_id
        GROUP BY i.id
        ORDER BY i.start_time DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        conn.close()

def format_datetime(iso_string):
    """
    FIX FOR My_Progress.py:
    Converts ISO format string (e.g., 2025-12-17T...) into 'Dec 17, 2025, 12:00 PM'
    """
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%b %d, %Y, %I:%M %p")
    except (ValueError, TypeError):
        return iso_string

def get_session_details(interview_id):
    """Retrieves metadata and records for the Final Report."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM interviews WHERE id = ?", (interview_id,))
    session_meta = cursor.fetchone()
    cursor.execute("SELECT * FROM records WHERE interview_id = ? ORDER BY timestamp ASC", (interview_id,))
    records = cursor.fetchall()
    conn.close()
    return dict(session_meta) if session_meta else {}, [dict(r) for r in records]

if not os.path.exists(DB_FILE):
    initialize_db()