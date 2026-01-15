"""
Database migration script to add is_approved column to User table.
Run this script to update the database schema for teacher approval system.
"""
from database.migration_utils import add_column_to_table, execute_sql_update
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_is_approved_column():
    """Add is_approved column to User table"""
    try:
        # Add column with default True (for existing users)
        column_added = add_column_to_table('user', 'is_approved', 'BOOLEAN', default='1')
        
        # Update existing principals to be approved
        if column_added:
            execute_sql_update(
                'user',
                "UPDATE user SET is_approved = 1 WHERE role = 'principal'",
                "Updating existing principals to be approved..."
            )
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        raise

if __name__ == '__main__':
    add_is_approved_column()

