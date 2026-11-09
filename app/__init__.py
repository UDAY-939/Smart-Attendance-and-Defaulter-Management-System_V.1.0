import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
load_dotenv()
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login_portal'

def create_app():
    app = Flask(__name__)

    # TiDB Cloud Serverless requires SSL. We pass ssl=True via connect_args.
    # This works for both TiDB Cloud and plain MySQL (SSL is just ignored if not needed).
    db_url = os.getenv('DATABASE_URL', 'mysql+pymysql://root:password@localhost:3306/attendance_db?charset=utf8mb4')

    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev-only-change-this'),
        SQLALCHEMY_DATABASE_URI=db_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "connect_args": {
                "ssl": {"fake_flag_to_enable_tls": True}  # enables TLS for PyMySQL (TiDB Cloud requirement)
            },
            "pool_pre_ping": True,   # auto-reconnect if connection drops (important for hosted DBs)
            "pool_recycle": 1800,    # recycle connections every 30 min to avoid stale connections
        }
    )

    db.init_app(app)
    login_manager.init_app(app)
    from . import models
    from .auth import bp as auth_bp
    from .main import bp as main_bp
    from .admin import bp as admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    with app.app_context():
        db.create_all()
        from .models import User
        if not User.query.filter_by(role='admin').first() and os.getenv('ADMIN_EMAIL') and os.getenv('ADMIN_PASSWORD'):
            user = User(name=os.getenv('ADMIN_NAME', 'Administrator'), email=os.getenv('ADMIN_EMAIL').lower().strip(), role='admin')
            user.set_password(os.getenv('ADMIN_PASSWORD'))
            db.session.add(user)
            db.session.commit()
    return app
