# models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Club(db.Model):
    __tablename__ = "clubs"
    club_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

class Room(db.Model):
    __tablename__ = "rooms"
    room_id = db.Column(db.Integer, primary_key=True)
    building = db.Column(db.String(120), nullable=False)
    number = db.Column(db.String(40), nullable=False)
    max_capacity = db.Column(db.Integer)

class Meeting(db.Model):
    __tablename__ = "meetings"
    meeting_id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(255))
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.club_id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.room_id"), nullable=False)
    invited_count = db.Column(db.Integer, default=0)
    accepted_count = db.Column(db.Integer, default=0)

    club = db.relationship("Club")
    room = db.relationship("Room")
