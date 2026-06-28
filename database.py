import sqlite3
import json
from datetime import datetime

DB_NAME = "talentscan.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def init_db():
    """Initializes the database schema if it doesn't already exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create candidates table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            location TEXT,
            years_of_experience REAL,
            summary TEXT,
            skills TEXT, -- Stored as a JSON list of strings
            original_filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create processing logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processing_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            status TEXT, -- 'SUCCESS' or 'ERROR'
            message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def insert_candidate(name, email, phone, location, years_of_experience, summary, skills, original_filename):
    """
    Inserts a candidate's details into the database.
    skills should be a list of strings, which will be stored as JSON.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    skills_json = json.dumps(skills) if isinstance(skills, list) else json.dumps([])
    
    try:
        cursor.execute("""
            INSERT INTO candidates (name, email, phone, location, years_of_experience, summary, skills, original_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, email, phone, location, years_of_experience, summary, skills_json, original_filename))
        conn.commit()
        candidate_id = cursor.lastrowid
        return candidate_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_all_candidates():
    """Retrieves all candidates from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidates ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    candidates = []
    for row in rows:
        candidate = dict(row)
        # Parse skills back to list
        try:
            candidate["skills"] = json.loads(candidate["skills"])
        except Exception:
            candidate["skills"] = []
        candidates.append(candidate)
    return candidates

def get_candidate_by_id(candidate_id):
    """Retrieves a single candidate by their ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        candidate = dict(row)
        try:
            candidate["skills"] = json.loads(candidate["skills"])
        except Exception:
            candidate["skills"] = []
        return candidate
    return None

def search_candidates(skill_query=None, min_experience=None, location_query=None, name_query=None):
    """
    Searches candidates by various optional criteria.
    Matches are case-insensitive and allow substring match.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM candidates WHERE 1=1"
    params = []
    
    if name_query and name_query.strip():
        query += " AND name LIKE ?"
        params.append(f"%{name_query.strip()}%")
        
    if location_query and location_query.strip():
        query += " AND location LIKE ?"
        params.append(f"%{location_query.strip()}%")
        
    if min_experience is not None:
        try:
            query += " AND years_of_experience >= ?"
            params.append(float(min_experience))
        except ValueError:
            pass # Ignore invalid experience inputs

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    candidates = []
    for row in rows:
        candidate = dict(row)
        try:
            candidate["skills"] = json.loads(candidate["skills"])
        except Exception:
            candidate["skills"] = []
            
        # Post-filter by skill in memory if skill_query is specified
        # (Since skills are stored as JSON strings like '["Python", "Java"]')
        if skill_query and skill_query.strip():
            skill_term = skill_query.strip().lower()
            # Match any skill in the list that contains the query
            skills_lower = [s.lower() for s in candidate["skills"]]
            if not any(skill_term in s for s in skills_lower):
                continue # Skip if skill term not found in candidate skills
                
        candidates.append(candidate)
        
    return candidates

def delete_candidate(candidate_id):
    """Deletes a candidate by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def insert_processing_log(filename, status, message):
    """Inserts a processing record to logs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO processing_logs (filename, status, message)
            VALUES (?, ?, ?)
        """, (filename, status, message))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_processing_logs(limit=50):
    """Retrieves recent processing logs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM processing_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_dashboard_stats():
    """Retrieves aggregate stats for display in the dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total candidates
    cursor.execute("SELECT COUNT(*) FROM candidates")
    total_candidates = cursor.fetchone()[0]
    
    # Avg experience
    cursor.execute("SELECT AVG(years_of_experience) FROM candidates")
    avg_experience = cursor.fetchone()[0] or 0.0
    
    # Skills distribution
    cursor.execute("SELECT skills FROM candidates")
    skills_rows = cursor.fetchall()
    
    skills_count = {}
    for row in skills_rows:
        try:
            skills_list = json.loads(row[0])
            for skill in skills_list:
                # Standardize skill capitalization for counting
                normalized = skill.strip().title()
                skills_count[normalized] = skills_count.get(normalized, 0) + 1
        except Exception:
            pass
            
    # Sort skills by count descending
    top_skills = sorted(skills_count.items(), key=lambda x: x[1], reverse=True)
    
    conn.close()
    
    return {
        "total_candidates": total_candidates,
        "avg_experience": round(avg_experience, 1),
        "top_skills": top_skills,
    }
