from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import DevelopmentConfig, ProductionConfig
import os
db = SQLAlchemy()
db = SQLAlchemy()
login_manager = LoginManager()
def create_app():
def create_app():
    app = Flask(__name__)
    
    if os.environ.get('FLASK_ENV') == 'production':
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)
    from .views import views
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    app.register_blueprint(auth, url_prefix='/')
    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
        return User.query.get(int(user_id))
    from .models import User
    return app
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app