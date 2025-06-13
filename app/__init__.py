from flask import Flask, redirect, url_for, request, render_template
import logging
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from config import Config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
mail = Mail()

# Configure logging - Set to WARNING level to remove debug logs
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    # Register blueprints
    from app.routes.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from app.routes.students import students as students_blueprint
    app.register_blueprint(students_blueprint)

    from app.routes.attendance import attendance as attendance_blueprint
    app.register_blueprint(attendance_blueprint)

    from app.routes.reports import reports as reports_blueprint
    app.register_blueprint(reports_blueprint)

    from app.routes.images import images as images_blueprint
    app.register_blueprint(images_blueprint)

    # Create database tables
    with app.app_context():
        db.create_all()

        # Display Google Sheet URL if available
        sheet_id = app.config.get('ATTENDANCE_SHEET_ID')
        if sheet_id:
            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
            print(f"\nGoogle Sheet URL: {sheet_url}\n")

    # Add context processor to make datetime available to all templates
    @app.context_processor
    def inject_now():
        from datetime import datetime
        import pytz
        # Get local timezone - modify this to your timezone, e.g., 'Asia/Kolkata' for India
        local_tz = pytz.timezone('Asia/Kolkata')
        utc_now = datetime.utcnow().replace(tzinfo=pytz.UTC)
        local_now = utc_now.astimezone(local_tz)
        return {'now': local_now}

    # Add root route
    @app.route('/')
    def index():
        return render_template('landing.html')

    @app.route('/test')
    def test():
        return '<h1>Test Route Works!</h1>'

    return app
