"""
Database migration script to add face recognition columns to ImageUpload table.
Run this script to update the database schema for face recognition support.
"""
from database.migration_utils import add_multiple_columns_to_table
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_face_recognition_columns():
    """Add face recognition columns to ImageUpload table"""
    try:
        columns_config = {
            'face_recognition_enabled': ('BOOLEAN', 'False'),
            'faces_detected': ('INTEGER', None),
            'students_matched': ('INTEGER', None),
            'attendance_marked_count': ('INTEGER', None),
            'face_matches_json': ('TEXT', None),
            'face_annotated_path': ('VARCHAR(255)', None)
        }
        add_multiple_columns_to_table('image_upload', columns_config)
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        raise

if __name__ == '__main__':
    add_face_recognition_columns()

