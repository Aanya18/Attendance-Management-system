from app import create_app, db
from app.models import User, Student, Attendance, ImageUpload
from flask import current_app
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def flush_database():
    """
    Flush the database by dropping all tables and recreating them.
    This will delete all data except the principal account.
    """
    app = create_app()
    with app.app_context():
        try:
            # Get principal accounts before dropping tables
            principals = User.query.filter_by(role='principal').all()
            principal_data = []
            for p in principals:
                principal_data.append({
                    'username': p.username,
                    'email': p.email,
                    'password_hash': p.password_hash
                })
            
            # Drop all tables
            db.drop_all()
            logger.info("Dropped all database tables")
            
            # Create tables again
            db.create_all()
            logger.info("Recreated all database tables")
            
            # Restore principal accounts
            for p_data in principal_data:
                principal = User(
                    username=p_data['username'],
                    email=p_data['email'],
                    role='principal',
                    password_hash=p_data['password_hash']
                )
                db.session.add(principal)
            
            db.session.commit()
            logger.info(f"Restored {len(principal_data)} principal account(s)")
            
            return True, "Database flushed successfully. All data has been deleted except principal accounts."
        except Exception as e:
            logger.error(f"Error flushing database: {str(e)}")
            return False, f"Error flushing database: {str(e)}"

def delete_teacher_sheet(teacher_id=None):
    """
    Delete a specific teacher's Google Sheet or all teacher sheets.
    
    Args:
        teacher_id: Optional. If provided, only delete that teacher's sheet.
                   If None, delete all teacher sheets.
    """
    app = create_app()
    with app.app_context():
        try:
            from app.utils.google_sheets import get_google_sheets_client
            
            client = get_google_sheets_client()
            if not client:
                return False, "Failed to connect to Google Sheets API"
            
            if teacher_id:
                # Delete a specific teacher's sheet
                from app.models import User
                teacher = User.query.get(teacher_id)
                if not teacher:
                    return False, f"Teacher with ID {teacher_id} not found"
                
                sheet_id_key = f"TEACHER_SHEET_ID_{teacher_id}"
                sheet_id = current_app.config.get(sheet_id_key)
                
                if not sheet_id:
                    return False, f"No sheet found for teacher {teacher.username}"
                
                try:
                    sheet = client.open_by_key(sheet_id)
                    # Clear all worksheets instead of deleting the sheet
                    for worksheet in sheet.worksheets():
                        worksheet.clear()
                    
                    logger.info(f"Cleared all worksheets in sheet for teacher {teacher.username}")
                    return True, f"Successfully cleared sheet for teacher {teacher.username}"
                except Exception as e:
                    logger.error(f"Error clearing sheet for teacher {teacher.username}: {str(e)}")
                    return False, f"Error clearing sheet: {str(e)}"
            else:
                # Clear the main attendance sheet
                sheet_id = current_app.config.get('ATTENDANCE_SHEET_ID')
                if sheet_id:
                    try:
                        sheet = client.open_by_key(sheet_id)
                        # Clear all worksheets instead of deleting the sheet
                        for worksheet in sheet.worksheets():
                            worksheet.clear()
                        
                        logger.info("Cleared all worksheets in main attendance sheet")
                    except Exception as e:
                        logger.error(f"Error clearing main attendance sheet: {str(e)}")
                
                # Get all teacher sheet IDs from config
                teacher_sheet_ids = {}
                for key in current_app.config:
                    if key.startswith('TEACHER_SHEET_ID_'):
                        teacher_id = key.replace('TEACHER_SHEET_ID_', '')
                        teacher_sheet_ids[teacher_id] = current_app.config[key]
                
                success_count = 0
                error_count = 0
                
                # Clear each teacher's sheet
                for t_id, sheet_id in teacher_sheet_ids.items():
                    try:
                        sheet = client.open_by_key(sheet_id)
                        for worksheet in sheet.worksheets():
                            worksheet.clear()
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Error clearing sheet for teacher ID {t_id}: {str(e)}")
                        error_count += 1
                
                return True, f"Cleared {success_count} teacher sheets. Errors: {error_count}"
        except Exception as e:
            logger.error(f"Error during sheet operation: {str(e)}")
            return False, f"Error during operation: {str(e)}"

if __name__ == "__main__":
    # If run directly, provide simple interface
    import argparse
    
    parser = argparse.ArgumentParser(description="Flush database and reset Google Sheets")
    parser.add_argument("--flush-db", action="store_true", help="Flush the database")
    parser.add_argument("--reset-sheets", action="store_true", help="Reset all Google Sheets")
    parser.add_argument("--teacher-id", type=int, help="Teacher ID for resetting a specific teacher's sheet")
    
    args = parser.parse_args()
    
    if args.flush_db:
        success, message = flush_database()
        print(f"{'✓' if success else '✗'} {message}")
    
    if args.reset_sheets:
        success, message = delete_teacher_sheet(args.teacher_id)
        print(f"{'✓' if success else '✗'} {message}") 