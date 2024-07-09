from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from .models import db, User
import jwt
import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth

auth = Blueprint('auth', __name__)

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=current_app.config['SPOTIPY_CLIENT_ID'],
        client_secret=current_app.config['SPOTIPY_CLIENT_SECRET'],
        redirect_uri=current_app.config['SPOTIPY_REDIRECT_URI'],
        scope="user-library-read playlist-modify-public playlist-modify-private")

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_hash = generate_password_hash(password)

        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please use a different email.', 'danger')
            return redirect(url_for('auth.register'))

        # Create user in the database
        user = User(username=username, email=email, password_hash=password_hash)
        db.session.add(user)
        db.session.commit()

        # Redirect to Spotify authentication
        session['new_user_id'] = user.id
        return redirect(url_for('auth.spotify_login'))
    return render_template('register.html')

@auth.route('/spotify_login')
def spotify_login():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@auth.route('/callback')
def callback():
    sp_oauth = create_spotify_oauth()
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)

    if token_info:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        user_info = sp.current_user()
        
        # Save user info to the database
        user_id = session.get('new_user_id')
        if user_id:
            user = User.query.get(user_id)
            user.spotify_id = user_info['id']
            user.spotify_token = token_info['access_token']
            db.session.commit()
            session.pop('new_user_id', None)
            flash('Registration and Spotify authentication successful. Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Failed to authenticate with Spotify.', 'danger')
            return redirect(url_for('auth.register'))
    else:
        flash('Failed to authenticate with Spotify.', 'danger')
        return redirect(url_for('auth.register'))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid username or password. Please try again.', 'danger')
            return redirect(url_for('auth.login'))

        token = jwt.encode({'user_id': user.id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)}, current_app.config['SECRET_KEY'], algorithm="HS256")
        session['token'] = token
        flash('Login successful!', 'success')
        return redirect(url_for('views.dashboard'))
    return render_template('login.html')

@auth.route('/logout')
def logout():
    session.pop('token', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))
