import os
import re
import json
import sqlite3
from datetime import datetime, date, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, g, abort, Response
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
app.secret_key = "doctor-app-super-secret-key-2026"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


@app.context_processor
def inject_globals():
    try:
        cities = [r["name"] for r in query("SELECT name FROM cities ORDER BY name")]
        specs = [r["name"] for r in query("SELECT name FROM specialties ORDER BY name")]
    except Exception:
        cities, specs = CITIES, SPECIALTIES
    return {"cities": cities, "all_specialties": specs, "current_year": 2026}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Schema + seed
# ---------------------------------------------------------------------------

CITIES = ["Dera Ismail Khan", "Karachi", "Lahore", "Islamabad", "Rawalpindi", "Multan", "Peshawar", "Quetta", "Faisalabad", "Bannu", "Tank", "Wana", "Paharpur, D.I.Khan", "Mianwali", "Gujranwala, Punjab"]

SPECIALTIES = [
    "Dermatologist", "Gynecologist", "Urologist", "Gastroenterologist", "Neurologist",
    "ENT Specialist", "Psychiatrist", "Child Specialist", "Dentist", "Sexologist",
    "Cardiologist", "Orthopedic Surgeon", "Eye Specialist", "General Physician",
    "Pulmonologist", "Nephrologist", "Obesity Specialist", "Physiotherapist",
    "Dietitian", "Endocrinologist",
]

DOCTORS = [
    # name, specialty, city, hospital, fee, experience, rating, reviews, mbbs, fellowship, online
    ("Dr. Ayesha Khan", "Dermatologist", "Karachi", "Dynamic Medical Center", 2000, 12, 4.9, 312, "MBBS, MCPS", "FCPS Dermatology", 1),
    ("Dr. Imran Malik", "Dermatologist", "Lahore", "Doctors Hospital", 2500, 15, 4.8, 285, "MBBS", "FCPS Dermatology", 1),
    ("Dr. Fahad Riaz", "Dermatologist", "Islamabad", "Shifa International Hospital", 3000, 10, 4.7, 198, "MBBS", "MCPS Skin & VD", 0),

    ("Dr. Saima Anwar", "Gynecologist", "Lahore", "Fatima Memorial Hospital", 2800, 18, 4.9, 421, "MBBS, FCPS", "FCPS Obstetrics & Gynaecology", 1),
    ("Dr. Nida Yasmin", "Gynecologist", "Karachi", "South City Hospital", 2200, 11, 4.8, 260, "MBBS", "FCPS Gynaecology", 0),
    ("Dr. Rabia Tariq", "Gynecologist", "Islamabad", "Maroof International Hospital", 3000, 14, 4.9, 340, "MBBS, MCPS", "FCPS Obstetrics & Gynaecology", 1),

    ("Dr. Bilal Ahmed", "Urologist", "Lahore", "Hameed Latif Hospital", 3000, 16, 4.8, 240, "MBBS, FCPS", "FRCS Urology", 0),
    ("Dr. Hamza Qureshi", "Urologist", "Karachi", "Aga Khan University Hospital", 3500, 20, 4.9, 355, "MBBS", "FCPS Urology", 1),
    ("Dr. Ali Raza", "Urologist", "Rawalpindi", "Citi Lab & Medical Centre", 2000, 8, 4.6, 120, "MBBS", "MCPS Urology", 0),

    ("Dr. Maria Shah", "Gastroenterologist", "Karachi", "Darul Sehat Hospital", 2600, 13, 4.8, 215, "MBBS, FCPS", "MCPS Gastroenterology", 1),
    ("Dr. Kamran Javed", "Gastroenterologist", "Lahore", "Doctors Hospital", 3200, 17, 4.9, 300, "MBBS", "FCPS Gastro & Hepatology", 0),
    ("Dr. Zainab Fatima", "Gastroenterologist", "Islamabad", "Ali Medical Centre", 2800, 9, 4.7, 165, "MBBS", "FCPS Gastroenterology", 1),

    ("Dr. Adnan Siddiqui", "Neurologist", "Karachi", "Patel Hospital", 3000, 15, 4.8, 275, "MBBS, MD", "Fellowship Neurology", 1),
    ("Dr. Hassan Mehmood", "Neurologist", "Lahore", "Omar Hospital & Cardiac Centre", 2800, 12, 4.7, 190, "MBBS", "FCPS Neurology", 0),
    ("Dr. Farhan Akhtar", "Neurologist", "Islamabad", "Shifa International Hospital", 3500, 19, 4.9, 330, "MBBS", "FRCP Neurology", 1),

    ("Dr. Sadia Yousaf", "ENT Specialist", "Lahore", "Evercare Hospital", 2200, 10, 4.7, 175, "MBBS", "MCPS ENT", 1),
    ("Dr. Usman Ghani", "ENT Specialist", "Karachi", "Liaquat National Hospital", 2400, 14, 4.8, 230, "MBBS", "FCPS ENT", 0),
    ("Dr. Mahnoor Aslam", "ENT Specialist", "Islamabad", "Quaid-e-Azam International Hospital", 2600, 11, 4.8, 200, "MBBS", "FCPS ENT", 1),

    ("Dr. Junaid Rana", "Psychiatrist", "Karachi", "International Care Hospital", 2800, 12, 4.7, 210, "MBBS, FCPS", "FRCP Psychiatry", 1),
    ("Dr. Amina Zafar", "Psychiatrist", "Islamabad", "Melody Psychiatric Centre", 3000, 16, 4.8, 245, "MBBS", "FCPS Psychiatry", 0),
    ("Dr. Saad Maqsood", "Psychiatrist", "Lahore", "Pakistan Kidney & Liver Institute", 2600, 9, 4.6, 130, "MBBS", "FCPS Psychiatry", 1),

    ("Dr. Hira Nawaz", "Child Specialist", "Lahore", "Ittefaq Hospital", 2000, 10, 4.8, 250, "MBBS", "FCPS Paediatrics", 1),
    ("Dr. Waqas Mughal", "Child Specialist", "Karachi", "Saifee Hospital", 2200, 13, 4.8, 220, "MBBS, FCPS", "MRCPCH", 0),
    ("Dr. Mehwish Akram", "Child Specialist", "Islamabad", "KRL Hospital", 2400, 11, 4.7, 185, "MBBS", "FCPS Paediatrics", 1),

    ("Dr. Omar Farooq", "Dentist", "Karachi", "Park Lane Dental Clinic", 1500, 8, 4.8, 310, "BDS", "MCPS Dental Surgery", 1),
    ("Dr. Sehrish Butt", "Dentist", "Lahore", "National Hospital", 1800, 9, 4.9, 295, "BDS", "RDS", 0),
    ("Dr. Taimoor Ali", "Dentist", "Islamabad", "Islamabad Dental Clinic", 1600, 7, 4.7, 180, "BDS", "MCPS Dental Surgery", 1),

    ("Dr. Nauman Saeed", "Sexologist", "Karachi", "Machlak Clinic", 1200, 10, 4.5, 95, "MBBS", "Diploma Sexual Health", 1),
    ("Dr. Asad Rahim", "Sexologist", "Lahore", "Care & Cure Clinic", 1300, 8, 4.6, 110, "MBBS", "Diploma Sexual Medicine", 0),

    ("Dr. Kashif Rehman", "Cardiologist", "Karachi", "Dr. Ziauddin Hospital", 3200, 18, 4.9, 380, "MBBS, FCPS", "FRCP Cardiology", 1),
    ("Dr. Samina Qazi", "Cardiologist", "Lahore", "Omar Hospital & Cardiac Centre", 3000, 16, 4.9, 355, "MBBS", "FRCP Cardiology", 0),
    ("Dr. Zeeshan Malik", "Cardiologist", "Islamabad", "Advanced International Hospital", 3500, 20, 4.8, 290, "MBBS", "FCPS Cardiology", 1),

    ("Dr. Shoaib Naseem", "Orthopedic Surgeon", "Lahore", "Gulab Devi Hospital", 2500, 14, 4.8, 265, "MBBS", "FCPS Orthopaedics", 0),
    ("Dr. Maleeha Hussain", "Orthopedic Surgeon", "Karachi", "Dow University Hospital", 2600, 13, 4.7, 200, "MBBS, FCPS", "FRCS Orthopaedics", 1),
    ("Dr. Owais Hai", "Orthopedic Surgeon", "Islamabad", "Shifa International Hospital", 3000, 17, 4.8, 235, "MBBS", "FCPS Orthopaedics", 0),

    ("Dr. Rahat Jabeen", "Eye Specialist", "Karachi", "Al-Shifa Trust Eye Hospital", 1800, 12, 4.8, 270, "MBBS", "FCPS Ophthalmology", 1),
    ("Dr. Irfan Lodhi", "Eye Specialist", "Lahore", "Mayo Hospital", 1600, 15, 4.8, 255, "MBBS, FCPS", "FRCS Ophthalmology", 0),
    ("Dr. Sana Khalid", "Eye Specialist", "Islamabad", "Al-Shifa Eye Trust", 2000, 9, 4.7, 165, "MBBS", "FCPS Ophthalmology", 1),

    ("Dr. Rizwan Paracha", "General Physician", "Karachi", "National Medical Centre", 1200, 9, 4.7, 320, "MBBS", "MCPS Medicine", 1),
    ("Dr. Anum Rehman", "General Physician", "Lahore", "Lahore General Hospital", 1000, 7, 4.6, 290, "MBBS", "RMP", 1),
    ("Dr. Danish Nawaz", "General Physician", "Rawalpindi", "Benazir Bhutto Hospital", 900, 6, 4.6, 240, "MBBS", "RMP", 0),

    ("Dr. Faraz Ahmed", "Pulmonologist", "Karachi", "Indus Hospital", 2600, 12, 4.8, 175, "MBBS", "FCPS Pulmonology", 1),
    ("Dr. Lubna Kamal", "Pulmonologist", "Islamabad", "Shifa International Hospital", 3000, 15, 4.8, 190, "MBBS", "FCPS Pulmonology", 0),

    ("Dr. Shahid Abbas", "Nephrologist", "Lahore", "Pakistan Kidney & Liver Institute", 3200, 16, 4.8, 205, "MBBS", "FCPS Nephrology", 1),
    ("Dr. Yasmin Khan", "Nephrologist", "Karachi", "Sindh Institute of Urology", 3000, 14, 4.8, 180, "MBBS", "FRCP Nephrology", 0),

    ("Dr. Tania Aslam", "Obesity Specialist", "Karachi", "Bariatric Solutions Clinic", 2200, 8, 4.7, 140, "MBBS", "Fellowship Bariatric Medicine", 1),
    ("Dr. Humaira Zafar", "Obesity Specialist", "Lahore", "Body Care Clinic", 2000, 7, 4.6, 115, "MBBS", "Certified Weight Management", 1),

    ("Dr. Salman Virk", "Physiotherapist", "Lahore", "Mobility Physio Center", 1500, 10, 4.8, 230, "DPT", "MS Orthopedic Physiotherapy", 1),
    ("Dr. Fiza Kiran", "Physiotherapist", "Karachi", "Rehab First Clinic", 1400, 8, 4.7, 175, "DPT", "Sports Physiotherapy", 0),

    ("Dr. Noor Aftab", "Dietitian", "Islamabad", "NutriCare Clinic", 1800, 9, 4.8, 200, "RD", "MSc Clinical Nutrition", 1),
    ("Dr. Rameela Nawab", "Dietitian", "Karachi", "Diet & Wellness Center", 1600, 10, 4.8, 215, "RD", "ADHD Certified Nutritionist", 0),

    ("Dr. Naveed Iqbal", "Endocrinologist", "Lahore", "Endocrine & Diabetes Center", 3000, 15, 4.8, 185, "MBBS", "FCPS Endocrinology", 1),
    ("Dr. Eman Sajjad", "Endocrinologist", "Karachi", "Life Care Diabetes Clinic", 2800, 12, 4.7, 160, "MBBS", "MRCP Endocrinology", 0),
]

HOSPITALS = [
    ("Doctors Hospital", "Lahore", "155-C, DHA Phase 1, Lahore", "042-111-111-266", 4.8),
    ("Hameed Latif Hospital", "Lahore", "15-A, Judicial Colony, Lahore", "042-111-111-260", 4.7),
    ("Fatima Memorial Hospital", "Lahore", "Shadman, Lahore", "042-9923-2340", 4.7),
    ("Evercare Hospital", "Lahore", "18-KM Ferozepur Road, Lahore", "042-111-222-933", 4.6),
    ("Omar Hospital & Cardiac Centre", "Lahore", "Jail Road, Lahore", "042-3594-3930", 4.7),
    ("Ittefaq Hospital", "Lahore", "73-C, Model Town, Lahore", "042-3592-2010", 4.6),
    ("Shifa International Hospital", "Islamabad", "Pitras Bukhari Road, H-8/4, Islamabad", "051-846-3333", 4.9),
    ("Maroof International Hospital", "Islamabad", "Plot 1/57, G-10/4, Islamabad", "051-926-1000", 4.7),
    ("Ali Medical Centre", "Islamabad", "Shalimar H-16, Islamabad", "051-111-643-643", 4.7),
    ("Quaid-e-Azam International Hospital", "Islamabad", "University Road, Islamabad", "051-111-111-814", 4.6),
    ("Aga Khan University Hospital", "Karachi", "Stadium Road, Karachi", "021-3486-1235", 4.9),
    ("Liaquat National Hospital", "Karachi", "National Stadium Road, Karachi", "021-3445-6123", 4.7),
    ("Dr. Ziauddin Hospital", "Karachi", "North Nazimabad, Karachi", "021-3586-2931", 4.7),
    ("South City Hospital", "Karachi", "Shahrah-e-Faisal, Karachi", "021-3454-3231", 4.6),
    ("Patel Hospital", "Karachi", "Karimabad, Karachi", "021-3453-0710", 4.6),
    ("Saifee Hospital", "Karachi", "Block 9, Clifton, Karachi", "021-3521-6032", 4.7),
]

PATIENTS = [
    ("umersaleem", "umersaleem@example.com", "03001234567", "Umer Saleem", "Male", "123456"),
    ("aneebryan", "aneebryan@example.com", "03019876543", "Aneeb Ryan", "Male", "123456"),
]

REVIEWS = [
    ("Umer Saleem", "Great platform, very efficient and works really well on both phone and web. This is the easiest way of booking appointments in Pakistan.", 5),
    ("Aneeb Ryan", "A very helpful platform for booking appointments and searching for the required doctors. Made my life a lot easier.", 5),
    ("Zainab Tariq", "Best website to book doctor appointments online. The service is great and ongoing staff is very helpful.", 5),
    ("Moin Umar", "The only good healthcare website. Suggested doctors are good and very responsive.", 5),
    ("Riffat Afzaal", "Very helpful staff. Helped me book an appointment with my gastroenterologist. Thanks a bunch.", 5),
    ("Kashif Ali", "Booked a video consultation in minutes. Doctor was on time and very professional. Highly recommended.", 4),
]

CONDITIONS = [
    "Fever", "Piles", "Acne", "Migraine", "Stomach Pain", "High Blood Pressure",
    "Diabetes", "Erectile Dysfunction", "Asthma", "Pregnancy Care",
]


def init_db():
    had_schema = False
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            has_patients = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='patients'"
            ).fetchone() is not None
            conn.close()
            if has_patients:
                had_schema = True
        except sqlite3.Error:
            pass
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    if had_schema:
        migrate(db)
        return
    cur.executescript(
        """
        CREATE TABLE cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE specialties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            urdu_name TEXT,
            icon TEXT
        );

        CREATE TABLE hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city_id INTEGER NOT NULL,
            address TEXT,
            phone TEXT,
            rating REAL DEFAULT 0,
            ot_schedules TEXT,
            FOREIGN KEY (city_id) REFERENCES cities(id)
        );

        CREATE TABLE doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            urdu_name TEXT,
            specialty_id INTEGER NOT NULL,
            city_id INTEGER NOT NULL,
            hospital_id INTEGER,
            fee INTEGER DEFAULT 0,
            experience INTEGER DEFAULT 0,
            experience_text TEXT,
            rating REAL DEFAULT 0,
            reviews INTEGER DEFAULT 0,
            gender TEXT,
            phone TEXT,
            whatsapp_number TEXT,
            qualification TEXT,
            diseases TEXT,
            doctor_message TEXT,
            sehat_card TEXT,
            views INTEGER DEFAULT 0,
            total_calls INTEGER DEFAULT 0,
            image_url TEXT,
            mbbs TEXT,
            fellowship TEXT,
            online INTEGER DEFAULT 0,
            pmdc TEXT,
            about TEXT,
            image TEXT,
            ot_schedule TEXT,
            opd_map TEXT,
            FOREIGN KEY (specialty_id) REFERENCES specialties(id),
            FOREIGN KEY (city_id) REFERENCES cities(id),
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
        );

        CREATE TABLE clinics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            clinic_name TEXT,
            address TEXT,
            timings TEXT,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
        );

        CREATE TABLE patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            gender TEXT DEFAULT 'Other',
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            slot TEXT NOT NULL,
            type TEXT DEFAULT 'In-Clinic',
            status TEXT DEFAULT 'pending',
            patient_name TEXT,
            patient_phone TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        );

        CREATE TABLE reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            content TEXT NOT NULL,
            rating INTEGER DEFAULT 5
        );

        CREATE TABLE admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT,
            email TEXT
        );

        CREATE TABLE announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            date_from TEXT,
            date_to TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE carousel_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            image_url TEXT,
            date_from TEXT,
            date_to TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    for c in CITIES:
        if not cur.execute("SELECT id FROM cities WHERE name=?", (c,)).fetchone():
            cur.execute("INSERT INTO cities (name) VALUES (?)", (c,))
    for s in SPECIALTIES:
        if not cur.execute("SELECT id FROM specialties WHERE name=?", (s,)).fetchone():
            cur.execute("INSERT INTO specialties (name) VALUES (?)", (s,))
    for p in PATIENTS:
        cur.execute(
            "INSERT INTO patients (username, email, password, full_name, gender, phone) VALUES (?, ?, ?, ?, ?, ?)",
            (p[0], p[1], p[5], p[3], p[4], p[2]),
        )
    for r in REVIEWS:
        cur.execute(
            "INSERT INTO reviews (patient_name, content, rating) VALUES (?, ?, ?)",
            (r[0], r[1], r[2]),
        )
    cur.execute("INSERT INTO admins (username, password) VALUES (?, ?)", (ADMIN_USERNAME, ADMIN_PASSWORD))

    # Give all doctors about text + PMDC
    cur.execute("SELECT id, name FROM doctors")
    for row in cur.fetchall():
        about = (
            f"{row[1]} is a highly-qualified and experienced specialist practicing in Pakistan. "
            f"With a strong academic background and years of clinical experience, they provide "
            f"compassionate, evidence-based care to every patient. Known for excellent patient "
            f"bedside manner and modern treatment approaches."
        )
        cur.execute(
            "UPDATE doctors SET pmdc=?, about=? WHERE id=?",
            (f"PMDC-{83000 + row[0] * 137 % 9000}", about, row[0]),
        )

    assign_doctor_images(cur)
    db.commit()
    db.close()


FEMALE_FIRST_NAMES = {
    "ayesha", "saima", "nida", "rabia", "maria", "zainab", "sadia", "mahnoor",
    "amina", "hira", "mehwish", "sehrish", "samina", "maleeha", "rahat", "sana",
    "anum", "lubna", "yasmin", "tania", "humaira", "fiza", "noor", "rameela",
    "eman", "mehzabeen", "fauzia", "qurat",
}

MALE_IMAGES = ["m1", "m2", "m3", "m4", "m5", "m6", "m11", "m12", "m13", "m14"]
FEMALE_IMAGES = ["f1", "f2", "f3", "f4", "f5", "f7", "f8", "f9", "f10", "f11", "f12"]


def migrate(db):
    """Add new columns/tables to an existing database without wiping data."""
    cur = db.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS admins ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " username TEXT UNIQUE NOT NULL,"
        " password TEXT NOT NULL,"
        " name TEXT,"
        " email TEXT)"
    )
    if not cur.execute("SELECT id FROM admins LIMIT 1").fetchone():
        cur.execute("INSERT INTO admins (username, password) VALUES (?, ?)", (ADMIN_USERNAME, ADMIN_PASSWORD))

    cols = [r[1] for r in cur.execute("PRAGMA table_info(doctors)").fetchall()]
    for col, ddl in {
        "urdu_name": "TEXT",
        "experience_text": "TEXT",
        "gender": "TEXT",
        "phone": "TEXT",
        "whatsapp_number": "TEXT",
        "qualification": "TEXT",
        "diseases": "TEXT",
        "doctor_message": "TEXT",
        "sehat_card": "TEXT",
        "views": "INTEGER DEFAULT 0",
        "total_calls": "INTEGER DEFAULT 0",
        "image_url": "TEXT",
        "ot_schedule": "TEXT",
        "opd_map": "TEXT",
    }.items():
        if col not in cols:
            cur.execute(f"ALTER TABLE doctors ADD COLUMN {col} {ddl}")

    scols = [r[1] for r in cur.execute("PRAGMA table_info(specialties)").fetchall()]
    for col, ddl in {"urdu_name": "TEXT", "icon": "TEXT"}.items():
        if col not in scols:
            cur.execute(f"ALTER TABLE specialties ADD COLUMN {col} {ddl}")

    hcols = [r[1] for r in cur.execute("PRAGMA table_info(hospitals)").fetchall()]
    if "ot_schedules" not in hcols:
        cur.execute("ALTER TABLE hospitals ADD COLUMN ot_schedules TEXT")

    acols = [r[1] for r in cur.execute("PRAGMA table_info(admins)").fetchall()]
    for col, ddl in {"name": "TEXT", "email": "TEXT"}.items():
        if col not in acols:
            cur.execute(f"ALTER TABLE admins ADD COLUMN {col} {ddl}")

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS clinics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            clinic_name TEXT,
            address TEXT,
            timings TEXT,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            date_from TEXT,
            date_to TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS carousel_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            image_url TEXT,
            date_from TEXT,
            date_to TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    if not cur.execute("SELECT id FROM cities WHERE name='Dera Ismail Khan'").fetchone():
        cur.execute("INSERT INTO cities (name) VALUES (?)", ("Dera Ismail Khan",))
    assign_doctor_images(cur)
    db.commit()
    db.close()


def assign_doctor_images(cur):
    """Ensure doctors.image column exists and assign a local photo to every doctor."""
    cols = [r[1] for r in cur.execute("PRAGMA table_info(doctors)").fetchall()]
    if "image" not in cols:
        cur.execute("ALTER TABLE doctors ADD COLUMN image TEXT")

    male_idx = 0
    female_idx = 0
    rows = cur.execute("SELECT id, name FROM doctors ORDER BY id").fetchall()
    for doc_id, name in rows:
        first = name.replace("Dr. ", "").split()[0].lower()
        if first in FEMALE_FIRST_NAMES:
            img = FEMALE_IMAGES[female_idx % len(FEMALE_IMAGES)]
            female_idx += 1
        else:
            img = MALE_IMAGES[male_idx % len(MALE_IMAGES)]
            male_idx += 1
        cur.execute(
            "UPDATE doctors SET image=? WHERE id=? AND (image IS NULL OR image='')",
            (f"doctors/{img}.jpg", doc_id),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "patient_id" not in session:
            flash("Please login first to continue.", "warning")
            return redirect(url_for("auth", next=request.path))
        return fn(*args, **kwargs)
    return wrapper


def get_current_patient():
    if "patient_id" not in session:
        return None
    return query("SELECT * FROM patients WHERE id=?", (session["patient_id"],), one=True)


def available_slots(doctor_id, booking_date):
    """Return list of free half-hour slots for a doctor on a given date."""
    slots = [
        ("09:00 AM", "09:30 AM"), ("09:30 AM", "10:00 AM"), ("10:00 AM", "10:30 AM"),
        ("10:30 AM", "11:00 AM"), ("11:00 AM", "11:30 AM"), ("11:30 AM", "12:00 PM"),
        ("12:00 PM", "12:30 PM"), ("12:30 PM", "01:00 PM"), ("05:00 PM", "05:30 PM"),
        ("05:30 PM", "06:00 PM"), ("06:00 PM", "06:30 PM"), ("06:30 PM", "07:00 PM"),
        ("07:00 PM", "07:30 PM"), ("07:30 PM", "08:00 PM"),
    ]
    taken = {
        r["slot"]
        for r in query(
            "SELECT slot FROM appointments WHERE doctor_id=? AND appointment_date=? AND status != 'cancelled'",
            (doctor_id, booking_date),
        )
    }
    return [s for s in slots if s[0] not in taken]


def recommend_doctors(limit=6):
    return query(
        "SELECT d.*, s.name AS specialty_name, c.name AS city_name, h.name AS hospital_name "
        "FROM doctors d "
        "JOIN specialties s ON d.specialty_id = s.id "
        "JOIN cities c ON d.city_id = c.id "
        "LEFT JOIN hospitals h ON d.hospital_id = h.id "
        "ORDER BY d.reviews DESC, d.rating DESC LIMIT ?",
        (limit,),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def _parse_ann_dt(val):
    if not val:
        return None
    val = val.strip()
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(val.replace("+00:00", "").replace("+0000", ""), fmt)
        except ValueError:
            continue
    return None

def _active_announcements():
    all_ann = query("SELECT * FROM announcements ORDER BY id DESC")
    now = datetime.now()
    active = []
    for a in all_ann:
        d_from = _parse_ann_dt(a["date_from"])
        d_to = _parse_ann_dt(a["date_to"])
        if not a["date_from"] and not a["date_to"]:
            active.append(a)
            continue
        if d_from and now < d_from:
            continue
        if d_to and now > d_to:
            continue
        active.append(a)
    return active

@app.route("/")
def index():
    specialties = query("SELECT * FROM specialties ORDER BY name")
    top_hospitals = query(
        "SELECT h.*, c.name AS city_name, (SELECT COUNT(*) FROM doctors WHERE hospital_id=h.id) AS doctor_count "
        "FROM hospitals h JOIN cities c ON h.city_id=c.id ORDER BY h.rating DESC LIMIT 6"
    )
    top_specialties = query("SELECT * FROM specialties ORDER BY (SELECT COUNT(*) FROM doctors WHERE specialty_id=specialties.id) DESC LIMIT 14")
    reviews = query("SELECT * FROM reviews")
    stats = {
        "doctors": query("SELECT COUNT(*) c FROM doctors")[0]["c"],
        "patients": query("SELECT COUNT(*) c FROM patients")[0]["c"] * 1000 + 50000,
        "appointments": query("SELECT COUNT(*) c FROM appointments")[0]["c"] * 100,
    }
    featured = recommend_doctors(6)
    online_count = query("SELECT COUNT(*) c FROM doctors WHERE online=1")[0]["c"]
    announcements = _active_announcements()
    carousel = query("SELECT * FROM carousel_images ORDER BY id DESC LIMIT 6")
    return render_template(
        "index.html",
        specialties=specialties,
        top_hospitals=top_hospitals,
        hospitals_lhr=top_hospitals,
        hospitals_khi=top_hospitals,
        hospitals_isb=top_hospitals,
        top_specialties=top_specialties,
        reviews=reviews,
        stats=stats,
        featured=featured,
        online_count=online_count,
        conditions=CONDITIONS,
        cities=[r["name"] for r in query("SELECT name FROM cities ORDER BY name")],
        announcements=announcements,
        carousel=carousel,
        notifications=query("SELECT * FROM notifications ORDER BY id DESC LIMIT 3"),
    )


@app.route("/doctors")
def doctors():
    city = request.args.get("city", "").strip()
    specialty = request.args.get("specialty", "").strip()
    search = request.args.get("q", "").strip()
    online = request.args.get("online", "") == "1"

    sql = (
        "SELECT d.*, s.name AS specialty_name, c.name AS city_name, h.name AS hospital_name "
        "FROM doctors d "
        "JOIN specialties s ON d.specialty_id = s.id "
        "JOIN cities c ON d.city_id = c.id "
        "LEFT JOIN hospitals h ON d.hospital_id = h.id WHERE 1=1"
    )
    args = []
    if city:
        sql += " AND c.name=?"
        args.append(city)
    if specialty:
        sql += " AND s.name=?"
        args.append(specialty)
    if online:
        sql += " AND d.online=1"
    if search:
        sql += " AND (d.name LIKE ? OR s.name LIKE ? OR c.name LIKE ? OR h.name LIKE ?)"
        like = f"%{search}%"
        args += [like, like, like, like]
    sql += " ORDER BY d.rating DESC, d.reviews DESC"

    results = query(sql, args)
    specialties = query("SELECT * FROM specialties ORDER BY name")
    return render_template(
        "doctors.html",
        doctors=results,
        specialties=specialties,
        cities=[r["name"] for r in query("SELECT name FROM cities ORDER BY name")],
        city=city,
        specialty=specialty,
        search=search,
        online=online,
        total=len(results),
    )


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify({"results": []})
    like = f"%{q}%"
    doctors = query(
        "SELECT d.id, d.name, d.urdu_name, s.name AS specialty_name, c.name AS city_name "
        "FROM doctors d JOIN specialties s ON d.specialty_id=s.id JOIN cities c ON d.city_id=c.id "
        "WHERE d.name LIKE ? OR s.name LIKE ? OR c.name LIKE ? OR d.urdu_name LIKE ? "
        "ORDER BY d.rating DESC, d.reviews DESC LIMIT 5",
        (like, like, like, like),
    )
    specialties = query("SELECT name FROM specialties WHERE name LIKE ? LIMIT 4", (like,))
    hospitals = query("SELECT name FROM hospitals WHERE name LIKE ? LIMIT 4", (like,))
    qs = re.sub(r"[^A-Za-z0-9]+", "+", q).strip("+")
    results = []
    for d in doctors:
        results.append({"type": "doctor", "name": d["name"], "sub": d["specialty_name"] + " \u00b7 " + d["city_name"], "url": "/doctor/%d" % d["id"]})
    for s in specialties:
        results.append({"type": "specialty", "name": s["name"], "sub": "Specialty", "url": "/doctors?specialty=" + qs})
    for h in hospitals:
        results.append({"type": "hospital", "name": h["name"], "sub": "Hospital", "url": "/doctors?q=" + qs})
    return jsonify({"results": results[:8]})


@app.route("/doctor/<int:doctor_id>")
def doctor_profile(doctor_id):
    import json as _json
    doc = query(
        "SELECT d.*, s.name AS specialty_name, c.name AS city_name, h.name AS hospital_name, "
        "h.address AS hospital_address, h.phone AS hospital_phone "
        "FROM doctors d "
        "JOIN specialties s ON d.specialty_id = s.id "
        "JOIN cities c ON d.city_id = c.id "
        "LEFT JOIN hospitals h ON d.hospital_id = h.id WHERE d.id=?",
        (doctor_id,),
        one=True,
    )
    if not doc:
        abort(404)
    clinics = query("SELECT * FROM clinics WHERE doctor_id=? ORDER BY id", (doctor_id,))
    for cl in clinics:
        cl_dict = dict(cl)
        if cl_dict.get("timings"):
            try:
                cl_dict["timings_dict"] = _json.loads(cl_dict["timings"])
            except ValueError:
                cl_dict["timings_dict"] = None
        else:
            cl_dict["timings_dict"] = None
        clinics[clinics.index(cl)] = cl_dict

    opd_schedule = []
    if doc["ot_schedule"]:
        try:
            opd_schedule = _json.loads(doc["ot_schedule"])
        except ValueError:
            opd_schedule = []
    elif doc["opd_map"]:
        try:
            opd_map = _json.loads(doc["opd_map"])
            if isinstance(opd_map, dict):
                opd_schedule = [opd_map]
            elif isinstance(opd_map, list):
                opd_schedule = opd_map
        except ValueError:
            opd_schedule = []

    min_date = (date.today() + timedelta(days=1)).isoformat()
    similar = query(
        "SELECT d.*, s.name AS specialty_name, c.name AS city_name, h.name AS hospital_name "
        "FROM doctors d "
        "JOIN specialties s ON d.specialty_id = s.id "
        "JOIN cities c ON d.city_id = c.id "
        "LEFT JOIN hospitals h ON d.hospital_id = h.id "
        "WHERE d.specialty_id=? AND d.id != ? LIMIT 4",
        (doc["specialty_id"], doctor_id),
    )
    return render_template(
        "doctor_profile.html", doc=doc, similar=similar, min_date=min_date,
        clinics=clinics, opd_schedule=opd_schedule,
    )


@app.route("/hospitals")
def hospitals():
    city = request.args.get("city", "").strip()
    results = query(
        "SELECT h.*, c.name AS city_name, (SELECT COUNT(*) FROM doctors WHERE hospital_id=h.id) AS doctor_count "
        "FROM hospitals h JOIN cities c ON h.city_id=c.id "
        + ("WHERE c.name=?" if city else "WHERE 1=1") + " ORDER BY h.rating DESC",
        ((city,) if city else ()),
    )
    return render_template("hospitals.html", hospitals=results, cities=[r["name"] for r in query("SELECT name FROM cities ORDER BY name")], city=city)


@app.route("/hospital/<int:hospital_id>")
def hospital_profile(hospital_id):
    import json as _json
    hosp = query(
        "SELECT h.*, c.name AS city_name FROM hospitals h JOIN cities c ON h.city_id=c.id WHERE h.id=?",
        (hospital_id,),
        one=True,
    )
    if not hosp:
        abort(404)
    hospital_ot = []
    if hosp["ot_schedules"]:
        try:
            parsed = _json.loads(hosp["ot_schedules"])
            if isinstance(parsed, list):
                hospital_ot = parsed
        except ValueError:
            hospital_ot = []
    docs = query(
        "SELECT d.*, s.name AS specialty_name FROM doctors d "
        "JOIN specialties s ON d.specialty_id = s.id WHERE d.hospital_id=? ORDER BY d.rating DESC",
        (hospital_id,),
    )
    return render_template("hospital_profile.html", hospital=hosp, doctors=docs, hospital_ot=hospital_ot)


@app.route("/specialties")
def specialties_page():
    specs = query(
        "SELECT s.*, (SELECT COUNT(*) FROM doctors WHERE specialty_id=s.id) AS count "
        "FROM specialties s ORDER BY s.name"
    )
    return render_template("specialties.html", specialties=specs)


@app.route("/specialty/<int:specialty_id>")
def specialty_page(specialty_id):
    spec = query("SELECT * FROM specialties WHERE id=?", (specialty_id,), one=True)
    if not spec:
        abort(404)
    return redirect(url_for("doctors", specialty=spec["name"]))


@app.route("/conditions")
def conditions_page():
    return render_template("conditions.html", conditions=CONDITIONS)


@app.route("/auth", methods=["GET", "POST"])
def auth():
    if request.method == "POST":
        form_type = request.form.get("form_type")
        if form_type == "login":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            row = query("SELECT * FROM patients WHERE email=? OR username=?", (email, email), one=True)
            if row and row["password"] == password:
                session.clear()
                session["patient_id"] = row["id"]
                session["patient_name"] = row["full_name"]
                session.permanent = True
                flash(f"Welcome back, {row['full_name']}!", "success")
                nxt = request.args.get("next") or url_for("dashboard")
                return redirect(nxt)
            flash("Invalid email or password. Please try again.", "danger")
        elif form_type == "signup":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip().lower()
            phone = request.form.get("phone", "").strip()
            gender = request.form.get("gender", "Other")
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")

            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email or ""):
                flash("Please enter a valid email address.", "danger")
            elif len(password) < 6:
                flash("Password must be at least 6 characters long.", "danger")
            elif username and query("SELECT id FROM patients WHERE username=?", (username,), one=True):
                flash("That username is already taken.", "danger")
            elif query("SELECT id FROM patients WHERE email=?", (email,), one=True):
                flash("An account with this email already exists.", "danger")
            elif confirm != password:
                flash("Passwords do not match.", "danger")
            else:
                uid = execute(
                    "INSERT INTO patients (username, email, password, full_name, gender, phone) VALUES (?,?,?,?,?,?)",
                    (username or email.split("@")[0], email, password, full_name, gender, phone),
                )
                session.clear()
                session["patient_id"] = uid
                session["patient_name"] = full_name
                session.permanent = True
                flash("Account created successfully! Welcome to Doctor App.", "success")
                return redirect(url_for("dashboard"))
    return render_template("auth.html", cities=CITIES)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    patient = get_current_patient()
    appts = query(
        "SELECT a.*, d.name AS doctor_name, s.name AS specialty_name, c.name AS city_name "
        "FROM appointments a "
        "JOIN doctors d ON a.doctor_id=d.id "
        "JOIN specialties s ON d.specialty_id=s.id "
        "JOIN cities c ON d.city_id=c.id "
        "WHERE a.patient_id=? ORDER BY a.created_at DESC",
        (patient["id"],),
    )
    active = [
        a for a in appts if a["status"] in ("pending", "confirmed") and a["appointment_date"] >= date.today().isoformat()
    ]
    past = [a for a in appts if a["status"] in ("completed", "cancelled") or a["appointment_date"] < date.today().isoformat()]
    return render_template("dashboard.html", patient=patient, active=active, past=past)


@app.route("/book/<int:doctor_id>", methods=["POST"])
@login_required
def book(doctor_id):
    doc = query("SELECT * FROM doctors WHERE id=?", (doctor_id,), one=True)
    if not doc:
        abort(404)
    patient = get_current_patient()
    date_str = request.form.get("appointment_date", "")
    slot = request.form.get("slot", "")
    appt_type = request.form.get("appointment_type", "In-Clinic")
    notes = request.form.get("notes", "").strip()

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        d = None
    if not d or d < date.today():
        flash("Please pick a valid future date for your appointment.", "danger")
        return redirect(url_for("doctor_profile", doctor_id=doctor_id))
    if not slot:
        flash("Please select an appointment time slot.", "danger")
        return redirect(url_for("doctor_profile", doctor_id=doctor_id))

    exists = query(
        "SELECT id FROM appointments WHERE doctor_id=? AND appointment_date=? AND slot=? AND status != 'cancelled'",
        (doctor_id, date_str, slot),
        one=True,
    )
    if exists:
        flash("Sorry, that slot was just booked. Please choose another time.", "danger")
        return redirect(url_for("doctor_profile", doctor_id=doctor_id))

    execute(
        "INSERT INTO appointments (patient_id, doctor_id, appointment_date, slot, type, status, patient_name, patient_phone, notes) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (patient["id"], doctor_id, date_str, slot, appt_type, "confirmed", patient["full_name"], patient["phone"], notes),
    )
    flash(
        f"Appointment confirmed with {doc['name']} on {d.strftime('%A, %d %B %Y')} at {slot}. "
        f"Fee: Rs. {doc['fee']:,} (payable at clinic).",
        "success",
    )
    return redirect(url_for("dashboard"))


@app.route("/appointment/<int:appointment_id>/cancel", methods=["POST"])
@login_required
def cancel_appointment(appointment_id):
    row = query(
        "SELECT * FROM appointments WHERE id=? AND patient_id=?",
        (appointment_id, session["patient_id"]),
        one=True,
    )
    if row:
        execute("UPDATE appointments SET status='cancelled' WHERE id=?", (appointment_id,))
        flash("Your appointment has been cancelled.", "info")
    else:
        abort(404)
    return redirect(url_for("dashboard"))


@app.route("/slots")
def slots_api():
    doctor_id = request.args.get("doctor_id", type=int)
    date_str = request.args.get("date", "")
    if not doctor_id or not date_str:
        return jsonify({"error": "Missing parameters"}), 400
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date"}), 400
    return jsonify({"slots": available_slots(doctor_id, date_str)})


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return redirect(url_for("doctors"))
    return redirect(url_for("doctors", q=q))


@app.route("/about")
def about():
    stats = {
        "doctors": query("SELECT COUNT(*) c FROM doctors")[0]["c"],
        "patients": query("SELECT COUNT(*) c FROM patients")[0]["c"] * 1000 + 50000,
    }
    return render_template("about.html", stats=stats)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()
        if name and email and message:
            flash("Your message has been sent! Our team will contact you within 24 hours.", "success")
        else:
            flash("Please fill in all required fields.", "danger")
    return render_template("contact.html")


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# ---------------------------------------------------------------------------
# Admin panel
# ---------------------------------------------------------------------------

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please login to access the admin panel.", "warning")
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        row = query("SELECT * FROM admins WHERE username=? OR email=?", (username, username), one=True)
        if row and row["password"] == password:
            session["admin_logged_in"] = True
            session["admin_name"] = row["name"] or row["username"]
            session.permanent = True
            flash("Welcome to Admin Panel, " + (row["name"] or row["username"]) + "!", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("admin/admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    session.pop("admin_name", None)
    flash("Logged out of admin panel.", "info")
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    counts = {
        "doctors": query("SELECT COUNT(*) c FROM doctors")[0]["c"],
        "hospitals": query("SELECT COUNT(*) c FROM hospitals")[0]["c"],
        "specialties": query("SELECT COUNT(*) c FROM specialties")[0]["c"],
        "cities": query("SELECT COUNT(*) c FROM cities")[0]["c"],
        "patients": query("SELECT COUNT(*) c FROM patients")[0]["c"],
        "appointments": query("SELECT COUNT(*) c FROM appointments")[0]["c"],
        "online": query("SELECT COUNT(*) c FROM doctors WHERE online=1")[0]["c"],
        "clinics": query("SELECT COUNT(*) c FROM clinics")[0]["c"],
    }
    recent = query(
        "SELECT d.id, d.name, d.fee, d.online, s.name AS specialty_name, c.name AS city_name "
        "FROM doctors d "
        "JOIN specialties s ON d.specialty_id=s.id "
        "JOIN cities c ON d.city_id=c.id "
        "ORDER BY d.id DESC LIMIT 8"
    )
    return render_template("admin/admin_dashboard.html", counts=counts, recent=recent)


@app.route("/admin/doctors")
@admin_required
def admin_doctors_list():
    doctors = query(
        "SELECT d.*, s.name AS specialty_name, c.name AS city_name, h.name AS hospital_name "
        "FROM doctors d "
        "JOIN specialties s ON d.specialty_id=s.id "
        "JOIN cities c ON d.city_id=c.id "
        "LEFT JOIN hospitals h ON d.hospital_id=h.id "
        "ORDER BY d.id DESC"
    )
    return render_template("admin/admin_doctors.html", doctors=doctors)


@app.route("/admin/doctors/delete/<int:doctor_id>", methods=["POST"])
@admin_required
def admin_doctor_delete(doctor_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM appointments WHERE doctor_id=?", (doctor_id,))
    cur.execute("DELETE FROM doctors WHERE id=?", (doctor_id,))
    db.commit()
    flash("Doctor removed.", "info")
    return redirect(url_for("admin_doctors_list"))


@app.route("/admin/doctors/add", methods=["GET", "POST"])
@admin_required
def admin_doctor_add():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        urdu_name = request.form.get("urdu_name", "").strip()
        specialty = request.form.get("specialty", "").strip()
        city = request.form.get("city", "").strip()
        gender = request.form.get("gender", "Male").strip()
        phone = request.form.get("phone", "").strip()
        whatsapp = request.form.get("whatsapp", "").strip()
        qualification = request.form.get("qualification", "").strip()
        diseases = request.form.get("diseases", "").strip()
        doctor_message = request.form.get("doctor_message", "").strip()
        sehat_card = request.form.get("sehat_card", "").strip()
        online = 1 if request.form.get("online") else 0
        try:
            fee = float(request.form.get("fee") or 0)
            experience = int(request.form.get("experience") or 0)
            rating = min(float(request.form.get("rating") or 4.5), 5.0)
            reviews = int(request.form.get("reviews") or 0)
        except ValueError:
            rating, fee, experience, reviews = 4.5, 0, 0, 0
        mbbs = request.form.get("mbbs", "").strip() or "MBBS"
        fellowship = request.form.get("fellowship", "").strip()
        image_url = request.form.get("image_url", "").strip()

        sp = query("SELECT id FROM specialties WHERE name=?", (specialty,), one=True)
        ct = query("SELECT id FROM cities WHERE name=?", (city,), one=True)
        if not name:
            flash("Doctor name is required.", "danger")
        elif not sp:
            flash("Please choose a valid specialty.", "danger")
        elif not ct:
            flash("Please choose a valid city.", "danger")
        else:
            db = get_db()
            cur = db.cursor()
            hospital_name = request.form.get("hospital", "").strip()
            hospital_id = None
            if hospital_name:
                hosp = query("SELECT id FROM hospitals WHERE name=?", (hospital_name,), one=True)
                if hosp:
                    hospital_id = hosp["id"]
                else:
                    cur.execute(
                        "INSERT INTO hospitals (name, city_id, phone, rating) VALUES (?,?,?,?)",
                        (hospital_name, ct["id"], phone, 5.0),
                    )
                    hospital_id = cur.lastrowid
            cur.execute(
                "INSERT INTO doctors (name, urdu_name, specialty_id, city_id, hospital_id, fee, experience, "
                "experience_text, rating, reviews, gender, phone, whatsapp_number, qualification, diseases, "
                "doctor_message, sehat_card, mbbs, fellowship, online, about, image, image_url) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,?)",
                (name, urdu_name or None, sp["id"], ct["id"], hospital_id, fee, experience,
                 f"{experience} years" if experience else None, rating, reviews, gender,
                 phone or None, whatsapp or None, qualification or None, diseases or None,
                 doctor_message or None, sehat_card or None, mbbs, fellowship, online,
                 f"{name} is a highly-qualified and experienced specialist practicing in Pakistan. "
                 f"With a strong academic background and years of clinical experience, they provide "
                 f"compassionate, evidence-based care to every patient.",
                 image_url or None),
            )
            doctor_id = cur.lastrowid
            assign_doctor_images(cur)
            db.commit()
            import json as _json
            clinic_names = request.form.getlist("clinic_name")
            clinic_addresses = request.form.getlist("clinic_address")
            clinic_timings = request.form.getlist("clinic_timings")
            for cname, caddr, ctim in zip(clinic_names, clinic_addresses, clinic_timings):
                if not (cname.strip() or caddr.strip() or ctim.strip()):
                    continue
                timings = None
                try:
                    parsed = _json.loads(ctim)
                    timings = _json.dumps(parsed, ensure_ascii=False) if isinstance(parsed, dict) else None
                except (ValueError, TypeError):
                    timings = None
                cur.execute(
                    "INSERT INTO clinics (doctor_id, clinic_name, address, timings) VALUES (?,?,?,?)",
                    (doctor_id, cname.strip() or None, caddr.strip() or None, timings),
                )
            db.commit()
            flash(name + " added successfully!", "success")
            return redirect(url_for("admin_doctors_list"))

    specialties = query("SELECT * FROM specialties ORDER BY name")
    hospitals = query("SELECT * FROM hospitals ORDER BY name")
    return render_template(
        "admin/admin_doctor_add.html",
        specialties=specialties,
        hospitals=hospitals,
        cities=query("SELECT name FROM cities ORDER BY name"),
        edoc=None, edit_mode=False,
    )


@app.route("/admin/doctors/edit/<int:doctor_id>", methods=["GET", "POST"])
@admin_required
def admin_doctor_edit(doctor_id):
    import json as _json
    doc = query("SELECT d.*, s.name AS specialty_name, c.name AS city_name, h.name AS hospital_name "
                "FROM doctors d "
                "JOIN specialties s ON d.specialty_id=s.id "
                "JOIN cities c ON d.city_id=c.id "
                "LEFT JOIN hospitals h ON d.hospital_id=h.id WHERE d.id=?", (doctor_id,), one=True)
    if not doc:
        abort(404)
    clinics = query("SELECT * FROM clinics WHERE doctor_id=? ORDER BY id", (doctor_id,))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        urdu_name = request.form.get("urdu_name", "").strip()
        specialty = request.form.get("specialty", "").strip()
        city = request.form.get("city", "").strip()
        gender = request.form.get("gender", "Male").strip()
        phone = request.form.get("phone", "").strip()
        whatsapp = request.form.get("whatsapp", "").strip()
        qualification = request.form.get("qualification", "").strip()
        diseases = request.form.get("diseases", "").strip()
        doctor_message = request.form.get("doctor_message", "").strip()
        sehat_card = request.form.get("sehat_card", "").strip()
        online = 1 if request.form.get("online") else 0
        try:
            fee = float(request.form.get("fee") or 0)
            experience = int(request.form.get("experience") or 0)
            rating = min(float(request.form.get("rating") or 4.5), 5.0)
            reviews = int(request.form.get("reviews") or 0)
        except ValueError:
            rating, fee, experience, reviews = 4.5, 0, 0, 0
        mbbs = request.form.get("mbbs", "").strip() or "MBBS"
        fellowship = request.form.get("fellowship", "").strip()
        image_url = request.form.get("image_url", "").strip()

        sp = query("SELECT id FROM specialties WHERE name=?", (specialty or doc["specialty_name"],), one=True)
        ct = query("SELECT id FROM cities WHERE name=?", (city or doc["city_name"],), one=True)
        if not name:
            flash("Doctor name is required.", "danger")
        else:
            db = get_db()
            cur = db.cursor()
            hospital_name = request.form.get("hospital", "").strip()
            hospital_id = None
            if hospital_name:
                hosp = query("SELECT id FROM hospitals WHERE name=?", (hospital_name,), one=True)
                if hosp:
                    hospital_id = hosp["id"]
                else:
                    cur.execute(
                        "INSERT INTO hospitals (name, city_id, phone, rating) VALUES (?,?,?,?)",
                        (hospital_name, ct["id"], phone, 5.0),
                    )
                    hospital_id = cur.lastrowid
            cur.execute(
                "UPDATE doctors SET name=?, urdu_name=?, specialty_id=?, city_id=?, hospital_id=?, "
                "fee=?, experience=?, experience_text=?, rating=?, reviews=?, gender=?, phone=?, "
                "whatsapp_number=?, qualification=?, diseases=?, doctor_message=?, sehat_card=?, "
                "mbbs=?, fellowship=?, online=?, image_url=? WHERE id=?",
                (name, urdu_name or None, sp["id"], ct["id"], hospital_id, fee, experience,
                 f"{experience} years" if experience else None, rating, reviews, gender,
                 phone or None, whatsapp or None, qualification or None, diseases or None,
                 doctor_message or None, sehat_card or None, mbbs, fellowship, online, image_url or None, doctor_id),
            )
            cur.execute("DELETE FROM clinics WHERE doctor_id=?", (doctor_id,))
            clinic_names = request.form.getlist("clinic_name")
            clinic_addresses = request.form.getlist("clinic_address")
            clinic_timings = request.form.getlist("clinic_timings")
            for cname, caddr, ctim in zip(clinic_names, clinic_addresses, clinic_timings):
                if not (cname.strip() or caddr.strip() or ctim.strip()):
                    continue
                timings = None
                try:
                    parsed = _json.loads(ctim)
                    timings = _json.dumps(parsed, ensure_ascii=False) if isinstance(parsed, dict) else None
                except (ValueError, TypeError):
                    timings = None
                cur.execute(
                    "INSERT INTO clinics (doctor_id, clinic_name, address, timings) VALUES (?,?,?,?)",
                    (doctor_id, cname.strip() or None, caddr.strip() or None, timings),
                )
            db.commit()
            flash(name + " updated successfully!", "success")
            return redirect(url_for("admin_doctors_list"))

    specialties = query("SELECT * FROM specialties ORDER BY name")
    hospitals = query("SELECT * FROM hospitals ORDER BY name")
    return render_template(
        "admin/admin_doctor_add.html",
        specialties=specialties,
        hospitals=hospitals,
        cities=query("SELECT name FROM cities ORDER BY name"),
        edoc=doc, edit_mode=True, clinics=clinics,
    )


@app.route("/admin/hospitals", methods=["GET", "POST"])
@admin_required
def admin_hospitals():
    import json as _json
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        city = request.form.get("city", "").strip()
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()
        try:
            rating = min(float(request.form.get("rating") or 4.5), 5.0)
        except ValueError:
            rating = 4.5
        ot_schedules = request.form.get("ot_schedules", "").strip()
        try:
            ot_parsed = _json.loads(ot_schedules) if ot_schedules else None
            ot_schedules = _json.dumps(ot_parsed, ensure_ascii=False) if isinstance(ot_parsed, list) else None
        except (ValueError, TypeError):
            ot_schedules = None
        ct = query("SELECT id FROM cities WHERE name=?", (city,), one=True)
        if name and ct:
            execute("INSERT INTO hospitals (name, city_id, address, phone, rating, ot_schedules) VALUES (?,?,?,?,?,?)",
                    (name, ct["id"], address, phone, rating, ot_schedules))
            flash(name + " added successfully!", "success")
        else:
            flash("Hospital/clinic name and a valid city are required.", "danger")
        return redirect(url_for("admin_hospitals"))
    hospitals = query(
        "SELECT h.*, c.name AS city_name FROM hospitals h JOIN cities c ON h.city_id=c.id ORDER BY h.id DESC"
    )
    return render_template(
        "admin/admin_hospitals.html",
        hospitals=hospitals,
        cities=query("SELECT name FROM cities ORDER BY name"),
    )


@app.route("/admin/hospitals/edit/<int:hospital_id>", methods=["GET", "POST"])
@admin_required
def admin_hospital_edit(hospital_id):
    import json as _json
    hosp = query(
        "SELECT h.*, c.name AS city_name FROM hospitals h JOIN cities c ON h.city_id=c.id WHERE h.id=?",
        (hospital_id,),
        one=True,
    )
    if not hosp:
        abort(404)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        city = request.form.get("city", "").strip()
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()
        try:
            rating = min(float(request.form.get("rating") or hosp["rating"] or 4.5), 5.0)
        except ValueError:
            rating = hosp["rating"] or 4.5
        ot_schedules = request.form.get("ot_schedules", "").strip()
        try:
            ot_parsed = _json.loads(ot_schedules) if ot_schedules else None
            ot_schedules = _json.dumps(ot_parsed, ensure_ascii=False) if isinstance(ot_parsed, list) else None
        except (ValueError, TypeError):
            ot_schedules = None
        ct = query("SELECT id FROM cities WHERE name=?", (city,), one=True)
        if name and ct:
            execute(
                "UPDATE hospitals SET name=?, city_id=?, address=?, phone=?, rating=?, ot_schedules=? WHERE id=?",
                (name, ct["id"], address, phone, rating, ot_schedules, hospital_id),
            )
            flash(name + " updated successfully!", "success")
        else:
            flash("Hospital/clinic name and a valid city are required.", "danger")
        return redirect(url_for("admin_hospitals"))
    return render_template(
        "admin/admin_hospital_edit.html",
        hospital=hosp,
        cities=query("SELECT name FROM cities ORDER BY name"),
    )


@app.route("/admin/hospitals/delete/<int:hospital_id>", methods=["POST"])
@admin_required
def admin_hospital_delete(hospital_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE doctors SET hospital_id=NULL WHERE hospital_id=?", (hospital_id,))
    cur.execute("DELETE FROM hospitals WHERE id=?", (hospital_id,))
    db.commit()
    flash("Hospital/clinic removed.", "info")
    return redirect(url_for("admin_hospitals"))


@app.route("/admin/admins", methods=["GET", "POST"])
@admin_required
def admin_admins():
    if request.method == "POST":
        action = request.form.get("action", "").strip()
        if action == "admin_edit":
            aid = request.form.get("id", type=int)
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            row = query("SELECT * FROM admins WHERE id=?", (aid,), one=True) if aid else None
            if not row:
                flash("Admin not found.", "danger")
            elif not username:
                flash("Username is required.", "danger")
            elif query("SELECT id FROM admins WHERE id!=? AND (username=? OR email=?)", (aid, username, email), one=True):
                flash("Another admin already uses that username/email.", "danger")
            else:
                if password:
                    execute("UPDATE admins SET username=?, password=?, name=?, email=? WHERE id=?",
                            (username, password, name or None, email or None, aid))
                    flash("Admin updated.", "success")
                else:
                    execute("UPDATE admins SET username=?, name=?, email=? WHERE id=?",
                            (username, name or None, email or None, aid))
                    flash("Admin updated (password unchanged).", "success")
                if session.get("admin_logged_in") and session.get("admin_name") == row["name"]:
                    session["admin_name"] = name or username
        else:
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            if not username or not password:
                flash("Username and password are required.", "danger")
            elif query("SELECT id FROM admins WHERE username=? OR email=?", (username, email), one=True):
                flash("An admin with that username/email already exists.", "danger")
            else:
                execute("INSERT INTO admins (username, password, name, email) VALUES (?,?,?,?)",
                        (username, password, name or None, email or None))
                flash("Admin '" + username + "' added.", "success")
        return redirect(url_for("admin_admins"))
    return render_template("admin/admin_admins.html", admins=query("SELECT * FROM admins ORDER BY id"))


@app.route("/admin/admins/delete/<int:admin_id>", methods=["POST"])
@admin_required
def admin_admin_delete(admin_id):
    row = query("SELECT * FROM admins WHERE id=?", (admin_id,), one=True)
    if not row:
        abort(404)
    if session.get("admin_name") == row["name"] and session.get("admin_logged_in"):
        flash("You cannot delete your own account.", "warning")
    else:
        cur_total = query("SELECT COUNT(*) c FROM admins")[0]["c"]
        if cur_total <= 1:
            flash("Cannot delete the last remaining admin.", "warning")
        else:
            execute("DELETE FROM admins WHERE id=?", (admin_id,))
            flash("Admin removed.", "info")
    return redirect(url_for("admin_admins"))


@app.route("/admin/content", methods=["GET", "POST"])
@admin_required
def admin_content():
    import json as _json
    if request.method == "POST":
        section = request.form.get("section")
        if section == "announcement":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            date_from = request.form.get("date_from", "").strip() or None
            date_to = request.form.get("date_to", "").strip() or None
            if content:
                execute("INSERT INTO announcements (title, content, date_from, date_to) VALUES (?,?,?,?)",
                        (title or None, content, date_from, date_to))
                flash("Announcement added.", "success")
        elif section == "carousel":
            title = request.form.get("title", "").strip()
            image_url = request.form.get("image_url", "").strip()
            if image_url:
                execute("INSERT INTO carousel_images (title, image_url, date_from, date_to) VALUES (?,?,?,?)",
                        (title or None, image_url, None, None))
                flash("Carousel slide added.", "success")
        elif section == "carousel_edit":
            cid = request.form.get("id", type=int)
            title = request.form.get("title", "").strip()
            image_url = request.form.get("image_url", "").strip()
            if not cid or not image_url:
                flash("Image URL is required to save a carousel slide.", "warning")
            else:
                execute("UPDATE carousel_images SET title=?, image_url=? WHERE id=?",
                        (title or None, image_url, cid))
                flash("Carousel slide updated.", "success")
        elif section == "notification":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            image_url = request.form.get("image_url", "").strip()
            if title:
                execute("INSERT INTO notifications (title, description, image_url) VALUES (?,?,?)",
                        (title, description or None, image_url or None))
                flash("Notification added.", "success")
        elif section == "announcement_edit":
            aid = request.form.get("id", type=int)
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            date_from = request.form.get("date_from", "").strip() or None
            date_to = request.form.get("date_to", "").strip() or None
            if aid and content:
                execute("UPDATE announcements SET title=?, content=?, date_from=?, date_to=? WHERE id=?",
                        (title or None, content, date_from, date_to, aid))
                flash("Announcement updated.", "success")
            else:
                flash("Announcement content is required.", "warning")
        elif section == "notification_edit":
            nid = request.form.get("id", type=int)
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            image_url = request.form.get("image_url", "").strip()
            if nid and title:
                execute("UPDATE notifications SET title=?, description=?, image_url=? WHERE id=?",
                        (title, description or None, image_url or None, nid))
                flash("Notification updated.", "success")
            else:
                flash("Notification title is required.", "warning")
        elif section == "delete":
            table = request.form.get("table", "")
            cid = request.form.get("id", type=int)
            if table in ("announcements", "carousel_images", "notifications") and cid:
                execute(f"DELETE FROM {table} WHERE id=?", (cid,))
                flash("Item removed.", "info")
        return redirect(url_for("admin_content"))
    return render_template(
        "admin/admin_content.html",
        announcements=query("SELECT * FROM announcements ORDER BY id DESC"),
        carousel=query("SELECT * FROM carousel_images ORDER BY id DESC"),
        notifications=query("SELECT * FROM notifications ORDER BY id DESC"),
    )


@app.route("/admin/upload", methods=["POST"])
@admin_required
def admin_upload():
    """Upload an image (used for carousel / notifications) and return its URL."""
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "No file selected."}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"):
        return jsonify({"ok": False, "error": "Only image files are allowed (png/jpg/jpeg/gif/webp/svg)."}), 400
    up_dir = os.path.join(BASE_DIR, "static", "uploads")
    os.makedirs(up_dir, exist_ok=True)
    fname = secure_filename(f.filename)
    if not fname:
        fname = "image" + ext
    fname = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + fname
    f.save(os.path.join(up_dir, fname))
    return jsonify({"ok": True, "url": url_for("static", filename="uploads/" + fname)})


@app.route("/admin/backup", methods=["GET", "POST"])
@admin_required
def admin_backup():
    """Import a firestore_backup.json / exported backup, or download a backup of the DB."""
    if request.method == "POST":
        action = request.form.get("action")
        uploaded = request.files.get("backup_file")
        if action == "import" and uploaded and uploaded.filename:
            fname = secure_filename(uploaded.filename) or "backup.json"
            if not fname.endswith(".json"):
                flash("Please upload a .json backup file.", "warning")
                return redirect(url_for("admin_backup"))
            try:
                raw = uploaded.read().decode("utf-8-sig")
                data = json.loads(raw)
            except Exception as exc:
                flash("Could not parse the uploaded file as JSON: " + str(exc), "danger")
                return redirect(url_for("admin_backup"))
            flash("Backup imported — all doctors/hospitals/specialties replaced.", "info")
            try:
                from import_backup import run_import
                counts = run_import(data)
                summary = ", ".join(f"{t}: {n}" for t, n in counts.items())
                flash("Import complete. " + summary, "success")
            except Exception as exc:
                db = get_db()
                db.rollback()
                flash("Import failed: " + str(exc), "danger")
        elif action == "export":
            try:
                from import_backup import build_export
                export_data = build_export()
            except Exception:
                export_data = {}
            blob = json.dumps(export_data, ensure_ascii=False, indent=2).encode("utf-8")
            fname = "doctorapp_backup_%s.json" % date.today().isoformat()
            return Response(
                blob,
                mimetype="application/json",
                headers={"Content-Disposition": f"attachment; filename={fname}"},
            )
        return redirect(url_for("admin_backup"))
    totals = {
        "doctors": query("SELECT COUNT(*) c FROM doctors")[0]["c"],
        "hospitals": query("SELECT COUNT(*) c FROM hospitals")[0]["c"],
        "specialties": query("SELECT COUNT(*) c FROM specialties")[0]["c"],
        "clinics": query("SELECT COUNT(*) c FROM clinics")[0]["c"],
    }
    return render_template("admin/admin_backup.html", totals=totals)


@app.route("/admin/lookups", methods=["GET", "POST"])
@admin_required
def admin_lookups():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "city":
            name = request.form.get("name", "").strip()
            if not name:
                flash("City name is required.", "warning")
            elif query("SELECT id FROM cities WHERE name=?", (name,), one=True):
                flash("City already exists.", "warning")
            else:
                execute("INSERT INTO cities (name) VALUES (?)", (name,))
                if name not in CITIES:
                    CITIES.append(name)
                flash("City '" + name + "' added.", "success")
        elif action == "specialty":
            name = request.form.get("name", "").strip()
            urdu = request.form.get("urdu_name", "").strip()
            icon = request.form.get("icon", "").strip()
            if not name:
                flash("Specialty name is required.", "warning")
            elif query("SELECT id FROM specialties WHERE name=?", (name,), one=True):
                flash("Specialty already exists.", "warning")
            else:
                execute("INSERT INTO specialties (name, urdu_name, icon) VALUES (?,?,?)", (name, urdu or None, icon or None))
                if name not in SPECIALTIES:
                    SPECIALTIES.append(name)
                flash("Specialty '" + name + "' added.", "success")
        elif action == "city_edit":
            cid = request.form.get("id", type=int)
            name = request.form.get("name", "").strip()
            if cid and name:
                if query("SELECT id FROM cities WHERE name=? AND id<>?", (name, cid), one=True):
                    flash("Another city already uses that name.", "warning")
                else:
                    execute("UPDATE cities SET name=? WHERE id=?", (name, cid))
                    flash("City updated.", "success")
            else:
                flash("City name is required.", "warning")
        elif action == "city_delete":
            cid = request.form.get("id", type=int)
            if cid:
                cnt = query("SELECT COUNT(*) c FROM doctors WHERE city_id=?", (cid,), one=True)["c"]
                if cnt:
                    flash(f"Cannot delete: {cnt} doctor(s) use this city.", "warning")
                else:
                    execute("DELETE FROM cities WHERE id=?", (cid,))
                    flash("City removed.", "info")
        elif action == "specialty_edit":
            sid = request.form.get("id", type=int)
            name = request.form.get("name", "").strip()
            urdu = request.form.get("urdu_name", "").strip()
            icon = request.form.get("icon", "").strip()
            if not sid or not name:
                flash("Specialty name is required.", "warning")
            elif query("SELECT id FROM specialties WHERE name=? AND id<>?", (name, sid), one=True):
                flash("Another specialty already uses that name.", "warning")
            else:
                execute("UPDATE specialties SET name=?, urdu_name=?, icon=? WHERE id=?",
                        (name, urdu or None, icon or None, sid))
                flash("Specialty updated.", "success")
        elif action == "specialty_delete":
            sid = request.form.get("id", type=int)
            if sid:
                cnt = query("SELECT COUNT(*) c FROM doctors WHERE specialty_id=?", (sid,), one=True)["c"]
                if cnt:
                    flash(f"Cannot delete: {cnt} doctor(s) use this specialty.", "warning")
                else:
                    execute("DELETE FROM specialties WHERE id=?", (sid,))
                    flash("Specialty removed.", "info")
        return redirect(url_for("admin_lookups"))
    return render_template(
        "admin/admin_lookups.html",
        cities=query("SELECT * FROM cities ORDER BY name"),
        specialties=query("SELECT * FROM specialties ORDER BY name"),
    )


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="127.0.0.1", port=port)