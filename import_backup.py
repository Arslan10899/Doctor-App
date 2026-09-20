"""Import all data from the Aazaz firestore_backup.json into the Doctor App SQLite DB."""
import os
import re
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
INI_PATH = "/tmp/does_not_exist"

def find_backup():
    candidates = [
        os.path.join(BASE_DIR, "firestore_backup.json"),          # same folder as script
        os.path.join(os.path.dirname(BASE_DIR), "Aazaz", "firestore_backup.json"),  # original local path
        os.path.expanduser("~/firestore_backup.json"),
        "/home/DoctorApp/firestore_backup.json",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

BACKUP_PATH = find_backup()

MALE_IMAGES = ["m1", "m2", "m3", "m4", "m5", "m6", "m11", "m12", "m13", "m14"]
FEMALE_IMAGES = ["f1", "f2", "f3", "f4", "f5", "f7", "f8", "f9", "f10", "f11", "f12"]
FEMALE_NAMES = {
    "ayesha", "saima", "nida", "rabia", "maria", "zainab", "sadia", "mahnoor",
    "amina", "hira", "mehwish", "sehrish", "samina", "maleeha", "rahat", "sana",
    "anum", "lubna", "yasmin", "tania", "humaira", "fiza", "noor", "rameela",
    "eman", "fatima", "rukhsana", "kausar", "shazia", "nazia", "farah",
}


def clean(text):
    """Trim padded spaces/tabs that wrap English + Urdu hospital names."""
    if not text:
        return ""
    text = re.sub(r"[\t ]+", " ", str(text)).strip()
    return text


def split_en(name):
    """Keep only the ASCII (English) portion of a mixed English-Urdu line."""
    if not name:
        return ""
    m = re.match(r"[\x20-\x7E]+", str(name))
    return clean(m.group(0)) if m else clean(str(name))


def parse_fee(raw):
    digits = "".join(ch for ch in (raw or "") if ch.isdigit() or ch == ".")
    try:
        return int(float(digits)) if digits else 0
    except ValueError:
        return 0


def get_images(db):
    return set(r[0] for r in db.execute("SELECT image FROM doctors WHERE image IS NOT NULL").fetchall())


FEMALE_IMAGES_CYCLE = iter(FEMALE_IMAGES)
MALE_IMAGES_CYCLE = iter(MALE_IMAGES)
_used = set()


def assign_image(db, cur, doctor_id, first_name, gender):
    fem = gender == "Female" or first_name.lower() in FEMALE_NAMES
    pool = FEMALE_IMAGES if fem else MALE_IMAGES
    cycle = FEMALE_IMAGES_CYCLE if fem else MALE_IMAGES_CYCLE
    for _ in range(len(pool)):
        try:
            name = next(cycle)
        except StopIteration:
            cycle = iter(pool)
            name = next(cycle)
        if name not in _used:
            _used.add(name)
            cur.execute("UPDATE doctors SET image=? WHERE id=?", (f"doctors/{name}.jpg", doctor_id))
            return name
    name = pool[0]
    cur.execute("UPDATE doctors SET image=? WHERE id=?", (f"doctors/{name}.jpg", doctor_id))
    return name


def import_backup():
    if not BACKUP_PATH:
        print("Backup file not found. Looked for firestore_backup.json in:")
        print("  - " + os.path.join(BASE_DIR, "firestore_backup.json"))
        print("  - " + os.path.dirname(BASE_DIR) + "/Aazaz/firestore_backup.json")
        print("  - " + os.path.expanduser("~/firestore_backup.json"))
        print("  - /home/DoctorApp/firestore_backup.json")
        print("Upload firestore_backup.json next to import_backup.py (i.e. in the project folder), then re-run this script.")
        raise SystemExit(1)

    with open(BACKUP_PATH, encoding="utf-8") as fh:
        data = json.load(fh)

    # Import app schema by running init_db + migrate in-process
    import app
    app.init_db()

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    # --- wipe existing doctor/hospital lookups & master data (keep patients/appointments/reviews) ---
    cur.executescript("""
        DELETE FROM clinics;
        DELETE FROM doctors;
        DELETE FROM hospitals;
        DELETE FROM specialties;
        DELETE FROM cities;
        DELETE FROM announcements;
        DELETE FROM carousel_images;
        DELETE FROM notifications;
        DELETE FROM admins;
        DELETE FROM sqlite_sequence WHERE name IN
            ('clinics','doctors','hospitals','specialties','cities','announcements',
             'carousel_images','notifications','admins');
    """)

    # --- cities ---
    city_ids = {}
    for c in data.get("cities", {}).values():
        name = clean(c.get("name", ""))
        if not name:
            continue
        cur.execute("INSERT INTO cities (name) VALUES (?)", (name,))
        city_ids[name] = cur.lastrowid
    if "Dera Ismail Khan" not in city_ids:
        cur.execute("INSERT INTO cities (name) VALUES (?)", ("Dera Ismail Khan",))
        city_ids["Dera Ismail Khan"] = cur.lastrowid

    # --- specialties ---
    spec_ids = {}
    for s in data.get("specialties", {}).values():
        name = clean(s.get("name", ""))
        if not name:
            continue
        urdu = s.get("urduName") or ""
        icon = s.get("iconUrl") or ""
        cur.execute("INSERT INTO specialties (name, urdu_name, icon) VALUES (?,?,?)", (name, urdu, icon))
        spec_ids[name] = cur.lastrowid
    for fallback in ["Gynaecologist", "Medical Specialist", "General Physician"]:
        # ensure common values exist even if lookup table lacks them
        if fallback not in spec_ids and not cur.execute("SELECT id FROM specialties WHERE name=?", (fallback,)).fetchone():
            cur.execute("INSERT INTO specialties (name, urdu_name, icon) VALUES (?,?,?)", (fallback, "", ""))
            spec_ids[fallback] = cur.lastrowid
    for s in data.get("opd-specialties", {}).values():
        en = clean(s.get("specialtyEnglish", ""))
        if en and en not in spec_ids and not cur.execute("SELECT id FROM specialties WHERE name=?", (en,)).fetchone():
            urdu = s.get("specialtyUrdu") or ""
            cur.execute("INSERT INTO specialties (name, urdu_name, icon) VALUES (?,?,?)", (en, urdu, ""))
            spec_ids[en] = cur.lastrowid

    def spec_id(name):
        name = clean(name)
        if name in spec_ids:
            return spec_ids[name]
        row = cur.execute("SELECT id FROM specialties WHERE name=?", (name,)).fetchone()
        if row:
            return row["id"]
        cur.execute("INSERT INTO specialties (name) VALUES (?)", (name,))
        spec_ids[name] = cur.lastrowid
        return spec_ids[name]

    def city_id(name):
        name = clean(name)
        if name in city_ids:
            return city_ids[name]
        row = cur.execute("SELECT id FROM cities WHERE name=?", (name,)).fetchone()
        if row:
            city_ids[name] = row["id"]
            return city_ids[name]
        cur.execute("INSERT INTO cities (name) VALUES (?)", (name,))
        city_ids[name] = cur.lastrowid
        return city_ids[name]

    # --- hospitals (fix trailing whitespace/Urdu mixes) ---
    hospital_ids = {}
    for h in data.get("hospitals", {}).values():
        raw_name = h.get("hospitalName") or ""
        name = split_en(h.get("hospitalName"))
        if not name:
            continue
        city = clean(h.get("hospitalCity") or "") or "Dera Ismail Khan"
        cid = city_id(city)
        ot = h.get("otSchedules") or []
        cur.execute(
            "INSERT INTO hospitals (name, city_id, address, phone, rating, ot_schedules) VALUES (?,?,?,?,?,?)",
            (name, cid, "", "", 4.5, json.dumps(ot, ensure_ascii=False) if ot else None),
        )
        hospital_ids[name.strip().lower()] = cur.lastrowid

    # --- doctors ---
    male_idx = 0
    used_imgs = set()
    total_calls_sum = 0
    views_sum = 0
    for doc in data.get("doctors", {}).values():
        name = clean(doc.get("doctorName") or "")
        if not name:
            continue
        urdu = (doc.get("urduName") or "").strip()
        specialty = clean(doc.get("specialty") or "") or "General Physician"
        city = clean(doc.get("city") or "") or "Dera Ismail Khan"
        fee = parse_fee(doc.get("fee"))
        experience = doc.get("experience") or ""
        exp_years = 0
        m = re.search(r"\d+", str(experience))
        if m:
            exp_years = int(m.group())
        rating_raw = doc.get("rating")
        try:
            rating = float(rating_raw) if rating_raw not in (None, "") else 4.5
        except (TypeError, ValueError):
            rating = 4.5
        gender = (doc.get("gender") or "Male").strip()
        phone = clean(doc.get("phone"))
        whatsapp = clean(doc.get("whatsappNumber"))
        qual = (doc.get("qualification") or "").strip()
        diseases = (doc.get("diseases") or doc.get("disease") or "").strip()
        message = (doc.get("doctorsMessage") or "").strip()
        sehat = (doc.get("sehatCardEmpaneled") or "").strip()
        try:
            views = int(doc.get("views") or 0)
        except (TypeError, ValueError):
            views = 0
        try:
            total_calls = int(doc.get("totalCalls") or 0)
        except (TypeError, ValueError):
            total_calls = 0
        image_url = (doc.get("imageUrl") or "").strip() or None
        ot_schedule = doc.get("otSchedule") or []
        opd_map = doc.get("opdMap")
        if isinstance(opd_map, dict):
            opd_map = json.dumps(opd_map, ensure_ascii=False)
        elif isinstance(opd_map, list):
            opd_map = json.dumps(opd_map, ensure_ascii=False)
        else:
            opd_map = None
        online = 1 if whatsapp else 0

        # map to a hospital if any otSchedule references a known hospital
        hospital_id = None
        for entry in ot_schedule:
            ref = split_en(entry.get("hospitalName")).strip().lower()
            if ref in hospital_ids:
                hospital_id = hospital_ids[ref]
                break

        mbbs = qual.split(",")[0].strip() if qual else "MBBS"
        fellowship = qual if len(qual) > len(mbbs) else ""
        about = (f"{name} is a highly-qualified and experienced specialist. "
                 f"Specializing in {specialty}, they provide compassionate, evidence-based care "
                 f"to patients in {city}.")
        if message:
            about += f" {message}"

        cur.execute(
            "INSERT INTO doctors (name, urdu_name, specialty_id, city_id, hospital_id, fee, experience, "
            " experience_text, rating, gender, phone, whatsapp_number, qualification, diseases, "
            " doctor_message, sehat_card, views, total_calls, image_url, mbbs, fellowship, online, "
            " pmdc, about, image, ot_schedule, opd_map) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (name, urdu, spec_id(specialty), city_id(city), hospital_id, fee, exp_years,
             experience, rating, gender, phone, whatsapp, qual, diseases, message, sehat,
             views, total_calls, image_url, mbbs or "MBBS", fellowship or qual, online,
             "Verified", about, None, json.dumps(ot_schedule, ensure_ascii=False) if ot_schedule else None,
             opd_map),
        )
        doc_id = cur.lastrowid
        assign_image(db, cur, doc_id, name.replace("Dr. ", "").split()[0], gender)

        # clinics with per-day timings
        for clinic in doc.get("clinics") or []:
            cname = (clinic.get("clinicName") or "").strip()
            address = (clinic.get("address") or "").strip()
            timings = clinic.get("timings") or {}
            cur.execute(
                "INSERT INTO clinics (doctor_id, clinic_name, address, timings) VALUES (?,?,?,?)",
                (doc_id, cname, address, json.dumps(timings, ensure_ascii=False) if timings else None),
            )

        total_calls_sum += total_calls
        views_sum += views

    # --- admins from backup ---
    seen_usernames = set()
    default_flags = False
    for a in data.get("admins", {}).values():
        email = (a.get("email") or "").strip()
        username = (email or a.get("name") or "admin").strip()
        # derive a short unique username
        uname = username
        if uname in seen_usernames:
            uname = ("admin" + str(len(seen_usernames) + 1))
        password = a.get("password") or "12345678"
        name = (a.get("name") or "").strip() or uname
        cur.execute("INSERT INTO admins (username, password, name, email) VALUES (?,?,?,?)",
                    (uname, password, name, email or None))
        seen_usernames.add(uname)
    # ensure default admin/admin123 works
    if not cur.execute("SELECT id FROM admins WHERE username='admin'").fetchone():
        cur.execute("INSERT INTO admins (username, password, name, email) VALUES (?,?,?,?)",
                    ("admin", "admin123", "Admin", "admin@doctorapp.pk"))

    # --- content tables ---
    for c in data.get("carousel_images", {}).values():
        cur.execute(
            "INSERT INTO carousel_images (title, image_url, date_from, date_to) VALUES (?,?,?,?)",
            (clean(c.get("title")), c.get("imageUrl") or "", c.get("from"), c.get("to")),
        )
    for c in data.get("commercial_texts", {}).values():
        cur.execute(
            "INSERT INTO announcements (title, content, date_from, date_to) VALUES (?,?,?,?)",
            (clean(c.get("title")), c.get("content") or "", c.get("from"), c.get("to")),
        )
    for c in data.get("notifications", {}).values():
        cur.execute(
            "INSERT INTO notifications (title, description, image_url) VALUES (?,?,?)",
            (clean(c.get("title")), c.get("description") or "", c.get("imageUrl") or ""),
        )

    db.commit()
    counts = {t: cur.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"] for t in
              ["doctors", "hospitals", "specialties", "cities", "clinics", "admins",
               "carousel_images", "announcements", "notifications"]}
    db.close()
    print("Import complete:")
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    import_backup()