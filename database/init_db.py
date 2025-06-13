from app import create_app, db
from app.models import User
import logging

# Set up logging
logger = logging.getLogger(__name__)

def init_db():
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if principal account exists
        principal = User.query.filter_by(username='principal').first()
        if not principal:
            # Create default principal account
            principal = User(
                username='principal',
                email='principal@example.com',
                role='principal'
            )
            principal.set_password('principal123')
            db.session.add(principal)
            db.session.commit()
            logger.info("Created default principal account:")
            logger.info("Username: principal")
            logger.info("Password: principal123")
        else:
            logger.info("Principal account already exists")

if __name__ == '__main__':
    # Set up logging for standalone execution
    logging.basicConfig(level=logging.INFO)
    init_db()
