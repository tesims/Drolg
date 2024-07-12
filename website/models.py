from . import db
from datetime import datetime, timedelta
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    spotify_id = db.Column(db.String(150), nullable=True)
    spotify_token = db.Column(db.String(500), nullable=True)
    refresh_token = db.Column(db.String(500), nullable=True)
    token_expiry = db.Column(db.Integer, nullable=True)
    joined_events = db.relationship('Event', secondary='user_event', back_populates='attendees')

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    date_event = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Interval, nullable=False)
    invite_code = db.Column(db.String(150), unique=True, nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    spotify_playlist_id = db.Column(db.String(150), nullable=False)
    mood_id = db.Column(db.Integer, db.ForeignKey('mood.id'), nullable=False)
    playlists = db.relationship('Playlist', backref='event', lazy=True)
    attendees = db.relationship('User', secondary='user_event', back_populates='joined_events')

    def calculate_duration(self):
        self.duration = self.end_time - self.date_event

class Mood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    events = db.relationship('Event', backref='mood', lazy=True)

class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    songs = db.relationship('Song', backref='playlist', lazy=True)

class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    artist = db.Column(db.String(150), nullable=False)
    spotify_track_id = db.Column(db.String(150), nullable=False)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.id'), nullable=False)
    mood_id = db.Column(db.Integer, db.ForeignKey('mood.id'), nullable=False)
    votes = db.relationship('Vote', backref='song', lazy=True)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('song.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)

user_event = db.Table('user_event',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True)
)