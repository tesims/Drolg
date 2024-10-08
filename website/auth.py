from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from .models import db, User
from sqlalchemy.exc import IntegrityError
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time

auth = Blueprint('auth', __name__)

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=current_app.config['SPOTIPY_CLIENT_ID'],
        client_secret=current_app.config['SPOTIPY_CLIENT_SECRET'],
        redirect_uri=current_app.config['SPOTIPY_REDIRECT_URI'],
        scope="user-library-read playlist-modify-public playlist-modify-private",
        cache_handler=None,
        show_dialog=True
    )

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists.', 'danger')
            return redirect(url_for('auth.register'))
        
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered.', 'danger')
            return redirect(url_for('auth.register'))
        
        new_user = User(username=username, email=email, password_hash=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        
        session['user_id'] = new_user.id
        flash('Registration successful. Please link your Spotify account.', 'success')
        return redirect(url_for('auth.spotify_login'))
    
    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            if not user.spotify_id:
                flash('Please link your Spotify account to continue.', 'warning')
                return redirect(url_for('auth.spotify_login'))
            
            flash('Login successful!', 'success')
            return redirect(url_for('views.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')

@auth.route('/spotify_login')
def spotify_login():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('auth.login'))
    
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@auth.route('/callback')
def callback():
    if 'user_id' not in session:
        flash('Session expired. Please log in again.', 'warning')
        return redirect(url_for('auth.login'))

    sp_oauth = create_spotify_oauth()
    session.pop('token_info', None)
    code = request.args.get('code')
    
    try:
        token_info = sp_oauth.get_access_token(code)
    except Exception as e:
        flash('Failed to get access token from Spotify. Please try again.', 'danger')
        return redirect(url_for('auth.spotify_login'))

    if not token_info:
        flash('Failed to get access token from Spotify. Please try again.', 'danger')
        return redirect(url_for('auth.spotify_login'))

    session['token_info'] = token_info

    sp = spotipy.Spotify(auth=token_info['access_token'])
    spotify_user_info = sp.me()
    
    user = User.query.get(session['user_id'])
    if not user:
        flash('User not found. Please register again.', 'danger')
        return redirect(url_for('auth.register'))

    try:
        user.spotify_id = spotify_user_info['id']
        user.spotify_token = token_info['access_token']
        user.refresh_token = token_info['refresh_token']
        user.token_expiry = int(token_info['expires_at'])
        db.session.commit()
        flash('Spotify account linked successfully!', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('This Spotify account is already linked to another user.', 'danger')
        return redirect(url_for('auth.spotify_login'))

    return redirect(url_for('views.dashboard'))

@auth.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))

def get_token():
    token_info = session.get('token_info', None)
    if not token_info:
        return None

    now = int(time.time())
    is_expired = token_info['expires_at'] - now < 60

    if is_expired:
        sp_oauth = create_spotify_oauth()
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info

    return token_info['access_token']

@auth.route('/refresh_token')
def refresh_token():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user or not user.refresh_token:
        return redirect(url_for('auth.spotify_login'))

    sp_oauth = create_spotify_oauth()
    token_info = sp_oauth.refresh_access_token(user.refresh_token)

    user.spotify_token = token_info['access_token']
    user.refresh_token = token_info['refresh_token']
    user.token_expiry = int(token_info['expires_at'])
    db.session.commit()

    session['token_info'] = token_info
    return redirect(url_for('views.dashboard'))
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user or not user.refresh_token:
        return redirect(url_for('auth.spotify_login'))

    token_info = refresh_token(user.refresh_token)
    session['token_info'] = token_info
    return redirect(url_for('views.dashboard'))
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user or not user.refresh_token:
        return redirect(url_for('auth.spotify_login'))

    sp_oauth = create_spotify_oauth()
    token_info = sp_oauth.refresh_access_token(user.refresh_token)

    user.spotify_token = token_info['access_token']
    user.refresh_token = token_info['refresh_token']
    user.token_expiry = int(token_info['expires_at'])
    db.session.commit()

    session['token_info'] = token_info
    return redirect(url_for('views.dashboard'))