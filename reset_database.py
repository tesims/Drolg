from website import create_app, db
from website.models import User, Event, Playlist, Song, Vote, Mood  # Import all your models

app = create_app()
with app.app_context():
    # Drop all tables
    db.drop_all()
    
    # Recreate all tables
    db.create_all()
    
    print("Database has been reset. All data has been deleted.")