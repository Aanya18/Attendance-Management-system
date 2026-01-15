"""
Database migration script to add full_name column to User table.
Run this script to update the database schema for full name support.
"""
from database.migration_utils import add_column_to_table, execute_sql_update
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_full_name_column():
    """Add full_name column to User table"""
    try:
        # Add column if it doesn't exist
        column_added = add_column_to_table('user', 'full_name', 'VARCHAR(100)')
        
        # If column was just added or already exists, update existing users
        if column_added:
            execute_sql_update(
                'user',
                "UPDATE user SET full_name = username WHERE full_name IS NULL",
                "Setting existing usernames as full_name for existing users..."
            )
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        raise

if __name__ == '__main__':
    add_full_name_column()

