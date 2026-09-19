import os
import re
import sqlite3
from datetime import datetime, date, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, g, abort

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
app.secret_key = "doctor-app-super-secret-key-2026"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)


@app.context_processor
def inject_globals():
    return {"cities": CITIES, "all_specialties": SPECIALTIES, "current_year": 2026}


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

CITIES = ["Dera Ismail Khan", "Karachi", "Lahore", "Islamabad", "Rawalpindi", "Multan", "Peshawar", "Quetta", "Faisalabad"]

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
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city_id INTEGER NOT NULL,
            address TEXT,
            phone TEXT,
            rating REAL DEFAULT 0,
            FOREIGN KEY (city_id) REFERENCES cities(id)
        );

        CREATE TABLE doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialty_id INTEGER NOT NULL,
            city_id INTEGER NOT NULL,
            hospital_id INTEGER,
            fee INTEGER DEFAULT 0,
            experience INTEGER DEFAULT 0,
            rating REAL DEFAULT 0,
            reviews INTEGER DEFAULT 0,
            mbbs TEXT,
            fellowship TEXT,
            online INTEGER DEFAULT 0,
            pmdc TEXT,
            about TEXT,
            image TEXT,
            FOREIGN KEY (specialty_id) REFERENCES specialties(id),
            FOREIGN KEY (city_id) REFERENCES cities(id),
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
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
        """
    )

    for c in CITIES:
        cur.execute("INSERT INTO cities (name) VALUES (?)", (c,))
    for s in SPECIALTIES:
        cur.execute("INSERT INTO specialties (name) VALUES (?)", (s,))
    for h in HOSPITALS:
        cur.execute(
            "INSERT INTO hospitals (name, city_id, address, phone, rating) VALUES (?, "
            "(SELECT id FROM cities WHERE name=?), ?, ?, ?)",
            (h[0], h[1], h[2], h[3], h[4]),
        )
    for d in DOCTORS:
        cur.execute(
            "INSERT INTO doctors (name, specialty_id, city_id, hospital_id, fee, experience, rating, reviews, mbbs, fellowship, online) "
            "VALUES (?, (SELECT id FROM specialties WHERE name=?), (SELECT id FROM cities WHERE name=?), "
            "(SELECT id FROM hospitals WHERE name=? AND city_id=(SELECT id FROM cities WHERE name=?)), ?, ?, ?, ?, ?, ?, ?)",
            (d[0], d[1], d[2], d[3], d[2], d[4], d[5], d[6], d[7], d[8], d[9], d[10]),
        )
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
    """Add new columns to an existing database without wiping data."""
    cur = db.cursor()
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

@app.route("/")
def index():
    specialties = query("SELECT * FROM specialties ORDER BY name")
    hospitals_lhr = query(
        "SELECT * FROM hospitals WHERE city_id=(SELECT id FROM cities WHERE name='Lahore') ORDER BY rating DESC LIMIT 6"
    )
    hospitals_khi = query(
        "SELECT * FROM hospitals WHERE city_id=(SELECT id FROM cities WHERE name='Karachi') ORDER BY rating DESC LIMIT 6"
    )
    hospitals_isb = query(
        "SELECT * FROM hospitals WHERE city_id=(SELECT id FROM cities WHERE name='Islamabad') ORDER BY rating DESC LIMIT 6"
    )
    top_specialties = query("SELECT * FROM specialties LIMIT 14")
    reviews = query("SELECT * FROM reviews")
    stats = {
        "doctors": query("SELECT COUNT(*) c FROM doctors")[0]["c"],
        "patients": query("SELECT COUNT(*) c FROM patients")[0]["c"] * 1000 + 50000,
        "appointments": query("SELECT COUNT(*) c FROM appointments")[0]["c"] * 100,
    }
    featured = recommend_doctors(6)
    online_count = query("SELECT COUNT(*) c FROM doctors WHERE online=1")[0]["c"]
    return render_template(
        "index.html",
        specialties=specialties,
        hospitals_lhr=hospitals_lhr,
        hospitals_khi=hospitals_khi,
        hospitals_isb=hospitals_isb,
        top_specialties=top_specialties,
        reviews=reviews,
        stats=stats,
        featured=featured,
        online_count=online_count,
        conditions=CONDITIONS,
        cities=CITIES,
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
        cities=CITIES,
        city=city,
        specialty=specialty,
        search=search,
        online=online,
        total=len(results),
    )


@app.route("/doctor/<int:doctor_id>")
def doctor_profile(doctor_id):
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
        "doctor_profile.html", doc=doc, similar=similar, min_date=min_date
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
    return render_template("hospitals.html", hospitals=results, cities=CITIES, city=city)


@app.route("/hospital/<int:hospital_id>")
def hospital_profile(hospital_id):
    hosp = query(
        "SELECT h.*, c.name AS city_name FROM hospitals h JOIN cities c ON h.city_id=c.id WHERE h.id=?",
        (hospital_id,),
        one=True,
    )
    if not hosp:
        abort(404)
    docs = query(
        "SELECT d.*, s.name AS specialty_name FROM doctors d "
        "JOIN specialties s ON d.specialty_id = s.id WHERE d.hospital_id=? ORDER BY d.rating DESC",
        (hospital_id,),
    )
    return render_template("hospital_profile.html", hospital=hosp, doctors=docs)


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


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="127.0.0.1", port=port)