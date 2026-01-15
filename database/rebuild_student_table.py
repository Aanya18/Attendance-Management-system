"""
Database migration script to rebuild Student table using SQLAlchemy.
This ensures consistency with the rest of the codebase.
"""
from app import create_app, db
from app.models import Student
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rebuild_student_table():
    """
    Rebuild student table using SQLAlchemy.
    Note: This will drop and recreate the table, losing all data.
    Use with caution!
    """
    app = create_app()
    with app.app_context():
        try:
            logger.warning("This will drop and recreate the student table, losing all data!")
            logger.info("Dropping existing student table...")
            Student.__table__.drop(db.engine, checkfirst=True)
            
            logger.info("Creating new student table...")
            Student.__table__.create(db.engine, checkfirst=True)
            
            logger.info("✓ Student table rebuilt successfully!")
            return True
        except Exception as e:
            logger.error(f"Error rebuilding student table: {e}")
            return False

if __name__ == "__main__":
    rebuild_student_table() 