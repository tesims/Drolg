from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from functools import wraps
import jwt
from .models import db, User, Event, Playlist, Song, Vote, Mood
import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from config import Config
import os

views = Blueprint('views', __name__)

def create_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=current_app.config['SPOTIPY_CLIENT_ID'],
        client_secret=current_app.config['SPOTIPY_CLIENT_SECRET'],
        redirect_uri=current_app.config['SPOTIPY_REDIRECT_URI'],
        scope="playlist-modify-public,playlist-modify-private"))

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = session.get('token')
        if not token:
            flash('Login required to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['user_id']).first()
        except:
            flash('Token is invalid or expired.', 'danger')
            return redirect(url_for('auth.login'))
        return f(current_user, *args, **kwargs)
    return decorated

@views.route('/')
def index():
    return render_template('index.html')

@views.route('/dashboard')
@token_required
def dashboard(current_user):
    hosted_events = Event.query.filter_by(host_id=current_user.id).all()
    joined_events = current_user.joined_events
    return render_template('dashboard.html', hosted_events=hosted_events, joined_events=joined_events)

@views.route('/events/create', methods=['GET', 'POST'])
@token_required
def create_event(current_user):
    mood_options = [
        {'id': 1, 'name': 'Energetic'},
        {'id': 2, 'name': 'Chill'},
        {'id': 3, 'name': 'Romantic'},
        {'id': 4, 'name': 'Upbeat'},
        {'id': 5, 'name': 'Mellow'}
    ]

    sp = create_spotify_client()
    playlists = sp.current_user_playlists()['items']

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        date_event_str = request.form['date_event']
        end_time_str = request.form['end_time']
        mood_id = request.form['mood_id']
        playlist_id = request.form['playlist_id']
        
        try:
            date_event = datetime.datetime.fromisoformat(date_event_str)
            end_time = datetime.datetime.fromisoformat(end_time_str)
        except ValueError:
            flash('Invalid date format. Please enter a valid date.', 'danger')
            return redirect(url_for('views.create_event'))

        invite_code = 'INVITE-' + str(len(Event.query.all()) + 1)
        event = Event(
            title=title,
            description=description,
            date_event=date_event,
            end_time=end_time,
            invite_code=invite_code,
            host_id=current_user.id,
            spotify_playlist_id=playlist_id,
            mood_id=mood_id
        )
        event.calculate_duration()
        db.session.add(event)
        db.session.commit()
        flash('Event created successfully!', 'success')
        return redirect(url_for('views.dashboard'))
    
    return render_template('create_event.html', mood_options=mood_options, playlists=playlists)

@views.route('/events/<int:event_id>')
@token_required
def event(current_user, event_id):
    event = Event.query.get_or_404(event_id)
    if event.host_id != current_user.id and current_user not in event.attendees:
        flash('Not authorized to view this event.', 'danger')
        return redirect(url_for('views.dashboard'))
    return render_template('event.html', event=event)

@views.route('/songs/search/<int:event_id>', methods=['GET', 'POST'])
@token_required
def search_song(current_user, event_id):
    event = Event.query.get_or_404(event_id)
    if request.method == 'POST':
        query = request.form['query']
        sp = create_spotify_client()
        results = sp.search(q=query, type='track', limit=10)
        tracks = results['tracks']['items']
        return render_template('search_song.html', event_id=event_id, tracks=tracks)
    return render_template('search_song.html', event_id=event_id)

@views.route('/songs/add/<int:event_id>/<spotify_track_id>', methods=['POST'])
@token_required
def add_song(current_user, event_id, spotify_track_id):
    event = Event.query.get_or_404(event_id)
    sp = create_spotify_client()
    track = sp.track(spotify_track_id)
    title = track['name']
    artist = ', '.join([artist['name'] for artist in track['artists']])
    
    # Add song to Spotify playlist
    sp.playlist_add_items(event.spotify_playlist_id, [spotify_track_id])
    
    # Add song to database
    song = Song(title=title, artist=artist, spotify_track_id=spotify_track_id, playlist_id=event.playlists[0].id, mood_id=event.mood_id)
    db.session.add(song)
    db.session.commit()
    flash('Song added to the playlist!', 'success')
    return redirect(url_for('views.event', event_id=event_id))

@views.route('/events/join', methods=['GET', 'POST'])
@token_required
def join_event(current_user):
    if request.method == 'POST':
        invite_code = request.form['invite_code']
        event = Event.query.filter_by(invite_code=invite_code).first()
        if event:
            event.attendees.append(current_user)
            db.session.commit()
            flash('Successfully joined the event!', 'success')
            return redirect(url_for('views.event', event_id=event.id))
        else:
            flash('Invalid invite code. Please try again.', 'danger')
            return redirect(url_for('views.join_event'))
    return render_template('join_event.html')

@views.route('/songs/vote/<int:song_id>', methods=['POST'])
@token_required
def vote_song(current_user, song_id):
    song = Song.query.get_or_404(song_id)
    event = song.playlist.event
    if current_user not in event.attendees and current_user != event.host:
        flash('Not authorized to vote in this event.', 'danger')
        return redirect(url_for('views.dashboard'))
    vote = Vote(user_id=current_user.id, song_id=song.id, event_id=event.id)
    db.session.add(vote)
    db.session.commit()
    flash('Vote added!', 'success')
    return redirect(url_for('views.event', event_id=event.id))

@views.route('/profile')
@token_required
def profile(current_user):
    return render_template('profile.html', user=current_user)
