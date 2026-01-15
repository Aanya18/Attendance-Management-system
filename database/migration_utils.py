"""
Generic database migration utilities.
This module provides reusable functions for database migrations.
"""
from app import create_app, db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_column_to_table(table_name, column_name, column_type, default=None, check_exists=True):
    """
    Generic function to add a column to a table
    
    Args:
        table_name: Name of the table
        column_name: Name of the column to add
        column_type: SQL type (e.g., 'INTEGER', 'VARCHAR(100)', 'BOOLEAN')
        default: Default value (optional, can be None, a value, or 'NULL' string)
        check_exists: Whether to check if column already exists
    
    Returns:
        bool: True if successful, False otherwise
    """
    app = create_app()
    with app.app_context():
        try:
            if check_exists:
                inspector = db.inspect(db.engine)
                columns = [col['name'] for col in inspector.get_columns(table_name)]
                
                if column_name in columns:
                    logger.info(f"{column_name} column already exists in {table_name} table")
                    return True
            
            logger.info(f"Adding {column_name} column to {table_name} table...")
            
            if default is not None and default != 'NULL':
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT {default}"
            else:
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            
            db.session.execute(text(sql))
            db.session.commit()
            logger.info(f"✓ {column_name} column added successfully")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding column {column_name} to {table_name}: {str(e)}")
            raise

def add_multiple_columns_to_table(table_name, columns_config):
    """
    Add multiple columns to a table
    
    Args:
        table_name: Name of the table
        columns_config: Dict of {column_name: (column_type, default_value)}
                       default_value can be None, a value, or 'NULL' string
    
    Returns:
        bool: True if successful, False otherwise
    """
    app = create_app()
    with app.app_context():
        try:
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
            
            for col_name, (col_type, default) in columns_config.items():
                if col_name not in existing_columns:
                    logger.info(f"Adding {col_name} column to {table_name} table...")
                    if default == 'NULL' or default is None:
                        sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
                    else:
                        sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} DEFAULT {default}"
                    
                    db.session.execute(text(sql))
                    db.session.commit()
                    logger.info(f"✓ {col_name} column added successfully")
                else:
                    logger.info(f"{col_name} column already exists")
            
            logger.info("Database migration completed successfully!")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during migration: {str(e)}")
            raise

def execute_sql_update(table_name, sql_update, description=None):
    """
    Execute a SQL UPDATE statement
    
    Args:
        table_name: Name of the table (for logging)
        sql_update: SQL UPDATE statement string
        description: Optional description for logging
    
    Returns:
        bool: True if successful, False otherwise
    """
    app = create_app()
    with app.app_context():
        try:
            if description:
                logger.info(description)
            else:
                logger.info(f"Executing SQL update on {table_name} table...")
            
            db.session.execute(text(sql_update))
            db.session.commit()
            logger.info("✓ SQL update executed successfully")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error executing SQL update: {str(e)}")
            raise

