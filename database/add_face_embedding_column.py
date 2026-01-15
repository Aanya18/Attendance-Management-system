"""
Database migration script to add face_embedding and face_image_path columns to Student table.
Run this script to update the database schema for face recognition support.
"""
from database.migration_utils import add_column_to_table
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_face_embedding_columns():
    """Add face_embedding and face_image_path columns to Student table"""
    try:
        add_column_to_table('student', 'face_embedding', 'TEXT')
        add_column_to_table('student', 'face_image_path', 'VARCHAR(255)')
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        raise

if __name__ == '__main__':
    add_face_embedding_columns()

