# app.py
from flask import (
    Flask, render_template, request, redirect, url_for, flash
)
from models import db, Club, Room, Meeting
from datetime import datetime, date as dt_date, time as dt_time
import os

# ----------------------------
# App setup (must be first)
# ----------------------------
app = Flask(__name__, instance_relative_config=True)
app.secret_key = "dev"  # required for flash messages

# ensure instance/ exists and use an absolute path for SQLite
os.makedirs(app.instance_path, exist_ok=True)
db_path = os.path.join(app.instance_path, "app.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()

    # ---- Seed data if tables are empty (for cloud deployment) ----
    if not Club.query.first():
        db.session.add_all([
            Club(name="Chess Club"),
            Club(name="Robotics"),
            Club(name="Art Society"),
        ])

    if not Room.query.first():
        db.session.add_all([
            Room(building="Eng", number="101", max_capacity=40),
            Room(building="Sci", number="202", max_capacity=60),
        ])

    db.session.commit()


# ----------------------------
# Helpers
# ----------------------------
def parse_date(s: str):
    """HTML date input -> Python date (YYYY-MM-DD)."""
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None

def parse_time(s: str):
    """Accept both HH:MM and HH:MM:SS from forms."""
    if not s:
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    # fall back to None (or raise if you prefer)
    return None

def reject_if_past(d, t):
    """Return True if the combined datetime is in the past."""
    if not d or not t:
        return False
    return datetime.combine(d, t) < datetime.now()

# ----------------------------
# Routes
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

# ---- Meetings: list
@app.route("/meetings")
def meetings_list():
    rows = Meeting.query.order_by(Meeting.date.desc(), Meeting.start_time.desc()).all()
    return render_template("meetings_list.html", rows=rows)

# ---- Meetings: new (form)
@app.route("/meetings/new")
def meetings_new():
    clubs = Club.query.order_by(Club.name).all()
    rooms = Room.query.order_by(Room.building, Room.number).all()
    return render_template("meeting_form.html",
                           mode="create", m=None, clubs=clubs, rooms=rooms, now=datetime.now())

# ---- Meetings: create (submit)
@app.route("/meetings", methods=["POST"])
def meetings_create():
    d = parse_date(request.form.get("date"))
    t = parse_time(request.form.get("start_time"))

    if reject_if_past(d, t):
        flash("Cannot schedule a meeting in the past!")
        return redirect(url_for("meetings_new"))

    invited = max(0, int(request.form.get("invited_count") or 0))
    accepted = max(0, int(request.form.get("accepted_count") or 0))

    m = Meeting(
        date=d,
        start_time=t,
        duration_minutes=int(request.form.get("duration_minutes") or 0),
        description=request.form.get("description"),
        club_id=int(request.form.get("club_id")),
        room_id=int(request.form.get("room_id")),
        invited_count=invited,
        accepted_count=accepted,
    )
    db.session.add(m)
    db.session.commit()
    flash("Meeting created!")
    return redirect(url_for("meetings_list"))

# ---- Meetings: edit (form)
@app.route("/meetings/<int:meeting_id>/edit")
def meetings_edit(meeting_id):
    m = Meeting.query.get_or_404(meeting_id)
    clubs = Club.query.order_by(Club.name).all()
    rooms = Room.query.order_by(Room.building, Room.number).all()
    return render_template("meeting_form.html",
                           mode="edit", m=m, clubs=clubs, rooms=rooms, now=datetime.now())

# ---- Meetings: update (submit)
@app.route("/meetings/<int:meeting_id>/update", methods=["POST"])
def meetings_update(meeting_id):
    m = Meeting.query.get_or_404(meeting_id)

    d = parse_date(request.form.get("date"))
    t = parse_time(request.form.get("start_time"))

    if reject_if_past(d, t):
        flash("Cannot schedule a meeting in the past!")
        return redirect(url_for("meetings_edit", meeting_id=meeting_id))

    m.date = d
    m.start_time = t
    m.duration_minutes = int(request.form.get("duration_minutes") or 0)
    m.description = request.form.get("description")
    m.club_id = int(request.form.get("club_id"))
    m.room_id = int(request.form.get("room_id"))
    m.invited_count = max(0, int(request.form.get("invited_count") or 0))
    m.accepted_count = max(0, int(request.form.get("accepted_count") or 0))

    db.session.commit()
    flash("Meeting updated!")
    return redirect(url_for("meetings_list"))

# ---- Meetings: delete
@app.route("/meetings/<int:meeting_id>/delete", methods=["POST"])
def meetings_delete(meeting_id):
    m = Meeting.query.get_or_404(meeting_id)
    db.session.delete(m)
    db.session.commit()
    flash("Meeting deleted!")
    return redirect(url_for("meetings_list"))

# ---- Report
@app.route("/report")
def report():
    clubs = Club.query.order_by(Club.name).all()
    rooms = Room.query.order_by(Room.building, Room.number).all()

    club_id = request.args.get("club_id", type=int)
    room_id = request.args.get("room_id", type=int)
    date_from_s = request.args.get("date_from")
    date_to_s = request.args.get("date_to")
    date_from = parse_date(date_from_s) if date_from_s else None
    date_to = parse_date(date_to_s) if date_to_s else None

    q = Meeting.query
    if club_id:
        q = q.filter(Meeting.club_id == club_id)
    if room_id:
        q = q.filter(Meeting.room_id == room_id)
    if date_from:
        q = q.filter(Meeting.date >= date_from)
    if date_to:
        q = q.filter(Meeting.date <= date_to)

    rows = q.order_by(Meeting.date, Meeting.start_time).all()

    n = len(rows)
    avg_duration = (sum(m.duration_minutes for m in rows)/n) if n else 0
    avg_invited  = (sum(m.invited_count  for m in rows)/n) if n else 0
    avg_accepted = (sum(m.accepted_count for m in rows)/n) if n else 0
    rates = [(m.accepted_count/m.invited_count) for m in rows if m.invited_count]
    avg_attendance_rate = (sum(rates)/len(rates)) if rates else 0

    return render_template(
        "report.html",
        clubs=clubs, rooms=rooms, rows=rows,
        filters={
            "club_id": club_id, "room_id": room_id,
            "date_from": date_from_s, "date_to": date_to_s
        },
        stats={
            "avg_duration": round(avg_duration, 2),
            "avg_invited": round(avg_invited, 2),
            "avg_accepted": round(avg_accepted, 2),
            "avg_attendance_rate": round(avg_attendance_rate, 3),
        },
    )

# ----------------------------
# CLI: flask --app app init-db
# ----------------------------
@app.cli.command("init-db")
def init_db():
    """Create tables and seed a little data."""
    with app.app_context():
        db.create_all()
        if not Club.query.first():
            db.session.add_all([
                Club(name="Chess Club"),
                Club(name="Robotics"),
                Club(name="Art Society"),
            ])
        if not Room.query.first():
            db.session.add_all([
                Room(building="Eng", number="101", max_capacity=40),
                Room(building="Sci", number="202", max_capacity=60),
            ])
        if not Meeting.query.first():
            db.session.add_all([
                Meeting(date=dt_date(2025, 11, 10), start_time=dt_time(12, 0),
                        duration_minutes=60, description="Weekly meetup",
                        club_id=1, room_id=1, invited_count=20, accepted_count=12),
                Meeting(date=dt_date(2025, 11, 12), start_time=dt_time(15, 30),
                        duration_minutes=90, description="Workshop",
                        club_id=2, room_id=2, invited_count=35, accepted_count=22),
            ])
        db.session.commit()
        print("Database initialized & seeded.")
