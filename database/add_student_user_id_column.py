"""
Database migration script to add user_id column to Student table.
Run this script to update the database schema for student login support.
"""
from database.migration_utils import add_column_to_table
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_student_user_id_column():
    """Add user_id column to Student table"""
    try:
        add_column_to_table('student', 'user_id', 'INTEGER')
        logger.info("Note: Foreign key constraint will be enforced by SQLAlchemy")
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        raise

if __name__ == '__main__':
    add_student_user_id_column()

