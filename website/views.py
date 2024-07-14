from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from .models import db, User, Event, Playlist, Song, Vote, Mood
from .spotify_utils import get_spotify_client
from datetime import datetime
import random
import string

views = Blueprint('views', __name__)

@views.route('/')
def index():
    return render_template('index.html')

@views.route('/dashboard')
@login_required
def dashboard():
    hosted_events = Event.query.filter_by(host_id=current_user.id).all()
    joined_events = current_user.joined_events
    return render_template('dashboard.html', hosted_events=hosted_events, joined_events=joined_events)

@views.route('/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        date_event = datetime.strptime(request.form.get('date_event'), '%Y-%m-%dT%H:%M')
        end_time = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')
        mood_name = request.form.get('mood')
        playlist_option = request.form.get('playlist_option')

        sp = get_spotify_client()
        if not sp:
            flash('Failed to connect to Spotify. Please check your Spotify connection.', 'danger')
            return redirect(url_for('views.create_event'))

        try:
            # Find or create the Mood
            mood = Mood.query.filter_by(name=mood_name).first()
            if not mood:
                mood = Mood(name=mood_name)
                db.session.add(mood)
                db.session.commit()

            if playlist_option == 'new':
                playlist_name = request.form.get('new_playlist_name')
                spotify_playlist = sp.user_playlist_create(user=sp.me()['id'], name=playlist_name)
            else:
                existing_playlist_id = request.form.get('existing_playlist_id')
                spotify_playlist = sp.playlist(existing_playlist_id)

            event = Event(
                title=title,
                description=description,
                date_event=date_event,
                end_time=end_time,
                mood_id=mood.id,
                host_id=current_user.id,
                spotify_playlist_id=spotify_playlist['id']
            )
            db.session.add(event)
            db.session.commit()

            flash('Event created successfully!', 'success')
            return redirect(url_for('views.dashboard'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating event: {str(e)}")
            flash('An error occurred while creating the event. Please try again.', 'danger')

    user_playlists = []
    try:
        sp = get_spotify_client()
        if sp:
            user_playlists = sp.current_user_playlists()['items']
    except Exception as e:
        current_app.logger.error(f"Error fetching user playlists: {str(e)}")
        flash('Unable to fetch your Spotify playlists. Some features may be limited.', 'warning')

    moods = Mood.query.all()
    return render_template('create_event.html', user_playlists=user_playlists, moods=moods)

@views.route('/event/<int:event_id>')
@login_required
def event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.host_id != current_user.id and current_user not in event.attendees:
        flash('You do not have permission to view this event.', 'danger')
        return redirect(url_for('views.dashboard'))
    
    sp = get_spotify_client()
    if sp and event.spotify_playlist_id:
        playlist = sp.playlist(event.spotify_playlist_id)
        tracks = playlist['tracks']['items']
    else:
        tracks = []
        flash('Unable to fetch playlist tracks. Please check your Spotify connection.', 'warning')
    
    return render_template('event.html', event=event, tracks=tracks)

@views.route('/join_event', methods=['GET', 'POST'])
@login_required
def join_event():
    if request.method == 'POST':
        invite_code = request.form.get('invite_code')
        event = Event.query.filter_by(invite_code=invite_code).first()
        if event:
            if current_user not in event.attendees:
                event.attendees.append(current_user)
                db.session.commit()
                flash('Successfully joined the event!', 'success')
            else:
                flash('You are already attending this event.', 'info')
            return redirect(url_for('views.event', event_id=event.id))
        else:
            flash('Invalid invite code. Please try again.', 'danger')
    return render_template('join_event.html')

@views.route('/vote/<int:song_id>', methods=['POST'])
@login_required
def vote_song(song_id):
    song = Song.query.get_or_404(song_id)
    event = song.playlist.event
    if current_user not in event.attendees and current_user != event.host:
        flash('Not authorized to vote in this event.', 'danger')
        return redirect(url_for('views.dashboard'))
    
    existing_vote = Vote.query.filter_by(user_id=current_user.id, song_id=song.id).first()
    if existing_vote:
        db.session.delete(existing_vote)
        flash('Vote removed!', 'info')
    else:
        vote = Vote(user_id=current_user.id, song_id=song.id, event_id=event.id)
        db.session.add(vote)
        flash('Vote added!', 'success')
    
    db.session.commit()
    return redirect(url_for('views.event', event_id=event.id))

@views.route('/search_songs')
@login_required
def search_songs():
    query = request.args.get('query', '')
    event_id = request.args.get('event_id')
    event = Event.query.get_or_404(event_id)
    
    if event.host_id != current_user.id and current_user not in event.attendees:
        return jsonify({'error': 'Not authorized'}), 403
    
    sp = get_spotify_client()
    if sp:
        results = sp.search(q=query, type='track', limit=10)
        tracks = results['tracks']['items']
    else:
        tracks = []
        flash('Unable to search songs. Please check your Spotify connection.', 'warning')
    
    return render_template('search_songs.html', tracks=tracks, event_id=event_id)

@views.route('/add_song/<int:event_id>/<string:track_id>', methods=['POST'])
@login_required
def add_song(event_id, track_id):
    event = Event.query.get_or_404(event_id)
    if event.host_id != current_user.id and current_user not in event.attendees:
        flash('You do not have permission to add songs to this event.', 'danger')
        return redirect(url_for('views.dashboard'))
    
    sp = get_spotify_client()
    if sp:
        track = sp.track(track_id)
        sp.user_playlist_add_tracks(current_user.id, event.spotify_playlist_id, [track_id])
        
        new_song = Song(
            title=track['name'],
            artist=', '.join([artist['name'] for artist in track['artists']]),
            spotify_track_id=track_id,
            playlist_id=event.playlist[0].id if event.playlist else None,
            mood_id=event.mood_id
        )
        db.session.add(new_song)
        db.session.commit()
        flash('Song added to the playlist!', 'success')
    else:
        flash('Unable to add song. Please check your Spotify connection.', 'warning')
    
    return redirect(url_for('views.event', event_id=event_id))

@views.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@views.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        
        if User.query.filter(User.username == username, User.id != current_user.id).first():
            flash('Username already taken.', 'danger')
        elif User.query.filter(User.email == email, User.id != current_user.id).first():
            flash('Email already in use.', 'danger')
        else:
            current_user.username = username
            current_user.email = email
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        
        return redirect(url_for('views.profile'))
    
    return render_template('edit_profile.html', user=current_user)
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        
        if User.query.filter(User.username == username, User.id != current_user.id).first():
            flash('Username already taken.', 'danger')
        elif User.query.filter(User.email == email, User.id != current_user.id).first():
            flash('Email already in use.', 'danger')
        else:
            current_user.username = username
            current_user.email = email
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        
        return redirect(url_for('views.profile'))
    
    return render_template('edit_profile.html', user=current_user)