from flask import Flask, redirect, url_for, render_template
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
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

    from app.routes.student import student as student_blueprint
    app.register_blueprint(student_blueprint)

    # Register root route
    @app.route('/')
    def index():
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for('students.list_students'))
        return render_template('landing.html')

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
        from app.utils.timezone_utils import get_local_now
        return {'now': get_local_now()}

    return app
