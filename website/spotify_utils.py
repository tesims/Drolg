from flask import current_app, session
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from .models import db, User
import time

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=current_app.config['SPOTIPY_CLIENT_ID'],
        client_secret=current_app.config['SPOTIPY_CLIENT_SECRET'],
        redirect_uri=current_app.config['SPOTIPY_REDIRECT_URI'],
        scope="user-library-read playlist-modify-public playlist-modify-private",
        cache_handler=None,
        show_dialog=True
    )

def get_spotify_client():
    token_info = session.get('token_info')
    if not token_info:
        return None

    if is_token_expired(token_info):
        token_info = refresh_token(token_info['refresh_token'])
        session['token_info'] = token_info

    return spotipy.Spotify(auth=token_info['access_token'])

def is_token_expired(token_info):
    now = int(time.time())
    return token_info['expires_at'] - now < 60

def refresh_token(refresh_token):
    sp_oauth = create_spotify_oauth()
    token_info = sp_oauth.refresh_access_token(refresh_token)
    
    user = User.query.get(session.get('user_id'))
    if user:
        user.spotify_token = token_info['access_token']
        user.refresh_token = token_info['refresh_token']
        user.token_expiry = int(token_info['expires_at'])
        db.session.commit()

    return token_info

def get_spotify_user_info(access_token):
    sp = spotipy.Spotify(auth=access_token)
    return sp.me()