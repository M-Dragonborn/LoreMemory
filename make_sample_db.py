import os
import sqlite3
from pathlib import Path
import auth
from config import DATA_DIR, USERS_DB, MEMORY_DB
from memory import Memory

def build_sample():
    sample_dir = Path(__file__).resolve().parent / "sample"
    sample_dir.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    db_path = sample_dir / "school.db"
    if db_path.exists():
        db_path.unlink()

    # Create school.db
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(
        """
        CREATE TABLE students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            email      TEXT UNIQUE,
            major      TEXT,
            gpa        REAL
        );

        CREATE TABLE courses (
            course_id INTEGER PRIMARY KEY AUTOINCREMENT,
            code      TEXT NOT NULL UNIQUE,
            title     TEXT NOT NULL,
            credits   INTEGER NOT NULL
        );

        CREATE TABLE enrollments (
            enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
            course_id     INTEGER NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
            grade         TEXT
        );
        """
    )

    # Insert sample courses
    courses_data = [
        ("CS101", "Introduction to Computer Science", 4),
        ("MATH201", "Calculus and Linear Algebra", 3),
        ("PHYS101", "General Physics", 4),
        ("ENG102", "Literature and Composition", 3),
        ("CS202", "Data Structures and Algorithms", 4)
    ]
    con.executemany("INSERT INTO courses (code, title, credits) VALUES (?, ?, ?)", courses_data)

    # Insert sample students
    students_data = [
        ("Alice Smith", "alice.smith@university.edu", "Computer Science", 3.85),
        ("Bob Jones", "bob.jones@university.edu", "Mathematics", 3.42),
        ("Charlie Brown", "charlie.brown@university.edu", "Physics", 3.90),
        ("Diana Prince", "diana.prince@university.edu", "Computer Science", 3.95),
        ("Evan Wright", "evan.wright@university.edu", "English", 3.20)
    ]
    con.executemany("INSERT INTO students (name, email, major, gpa) VALUES (?, ?, ?, ?)", students_data)

    # Insert sample enrollments
    enrollments_data = [
        (1, 1, "A"),
        (1, 2, "A-"),
        (1, 5, "A"),
        (2, 2, "B+"),
        (2, 1, "B"),
        (3, 3, "A"),
        (3, 2, "A"),
        (4, 1, "A+"),
        (4, 5, "A+"),
        (5, 4, "A-")
    ]
    con.executemany("INSERT INTO enrollments (student_id, course_id, grade) VALUES (?, ?, ?)", enrollments_data)
    con.commit()
    con.close()
    print(f"Created sample database at {db_path}")

    # Seed default users if not present
    u_con = sqlite3.connect(USERS_DB)
    auth.init_users(u_con)
    auth.register(u_con, "musfiq", "musfiq121")
    auth.register(u_con, "rayed", "rayed097")
    auth.register(u_con, "anower", "anower122")
    u_con.close()
    print(f"Seeded users 'musfiq', 'rayed', and 'anower' in {USERS_DB}")

    # Seed memory.db
    mem = Memory(MEMORY_DB)
    mem.remember("User discussed optimizing SQL queries for school.db enrollments", importance=0.8, session="session-001")
    mem.remember("User mentioned preferring dark theme when editing databases", importance=0.7, session="session-001")
    mem.remember("Reviewed student grade statistics for CS101", importance=0.5, session="session-002")
    mem.save_episode([1, 2], "Initial setup session covering school schema and preferences", importance=0.8)
    mem.close()
    print(f"Seeded memory items in {MEMORY_DB}")

if __name__ == "__main__":
    build_sample()

