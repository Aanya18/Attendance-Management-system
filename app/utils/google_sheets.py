import os
import json
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import current_app

def get_google_sheets_client():
    """
    Get a Google Sheets client using the service account credentials.
    """
    try:
        # Get the path to the credentials file
        credentials_file = current_app.config.get('GOOGLE_SHEETS_CREDENTIALS_FILE')

        if not credentials_file:
            current_app.logger.error("Google Sheets credentials file not specified in config")
            return None

        # Check if the file exists
        if not os.path.exists(credentials_file):
            current_app.logger.error(f"Google Sheets credentials file not found: {credentials_file}")
            # Try to look for the file in the root directory
            root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
            alt_path = os.path.join(root_path, credentials_file)
            if os.path.exists(alt_path):
                current_app.logger.info(f"Found credentials file at alternate path: {alt_path}")
                credentials_file = alt_path
            else:
                return None

        # Define the scope - include both spreadsheets and drive scopes for service account
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']

        # Log the credentials file being used
        current_app.logger.info(f"Using Google Sheets credentials file: {credentials_file}")

        # Authenticate using the service account credentials
        credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)

        # Log the service account email being used
        with open(credentials_file, 'r') as f:
            creds_data = json.load(f)
            client_email = creds_data.get('client_email')
            current_app.logger.info(f"Using service account email: {client_email}")

        # Create a gspread client
        client = gspread.authorize(credentials)

        return client

    except Exception as e:
        current_app.logger.error(f"Error creating Google Sheets client: {str(e)}")
        current_app.logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
        return None

def get_or_create_attendance_sheet():
    """
    Get or create the attendance sheet.
    """
    try:
        client = get_google_sheets_client()
        if not client:
            current_app.logger.error("Failed to get Google Sheets client")
            return None

        sheet_id = current_app.config.get('ATTENDANCE_SHEET_ID')

        # If we have a sheet ID, try to open it
        if sheet_id:
            current_app.logger.info(f"Attempting to access existing sheet with ID: {sheet_id}")
            try:
                sheet = client.open_by_key(sheet_id)
                current_app.logger.info(f"Successfully opened existing sheet: {sheet.title}")
                return sheet
            except gspread.exceptions.SpreadsheetNotFound:
                current_app.logger.info(f"Sheet with ID {sheet_id} not found, will create a new one")
            except Exception as e:
                current_app.logger.error(f"Error opening sheet: {str(e)}")
                # Continue to try creating a new sheet
        else:
            current_app.logger.info("No sheet ID provided, will create a new one")

        # If we get here, we need to create a new sheet
        try:
            # Create a new spreadsheet with a better name
            sheet_name = f"Student Attendance - {datetime.now().strftime('%B %Y')}"
            current_app.logger.info(f"Creating new sheet with name: {sheet_name}")

            # Create the sheet
            sheet = client.create(sheet_name)
            current_app.logger.info(f"Created new Google Sheet with ID: {sheet.id}")

            # Update the sheet ID in the app config
            current_app.config['ATTENDANCE_SHEET_ID'] = sheet.id

            # Update the .env file with the new sheet ID
            try:
                env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
                if os.path.exists(env_path):
                    with open(env_path, 'r') as f:
                        env_content = f.read()

                    # Replace the ATTENDANCE_SHEET_ID line
                    if 'ATTENDANCE_SHEET_ID=' in env_content:
                        env_content = env_content.replace('ATTENDANCE_SHEET_ID=', f'ATTENDANCE_SHEET_ID={sheet.id}')
                    else:
                        env_content += f'\nATTENDANCE_SHEET_ID={sheet.id}'

                    with open(env_path, 'w') as f:
                        f.write(env_content)

                    current_app.logger.info(f"Updated .env file with new sheet ID: {sheet.id}")
            except Exception as e:
                current_app.logger.error(f"Error updating .env file: {str(e)}")
                # Continue even if we can't update the .env file

            # Share the sheet with the admin email and make it accessible to anyone with the link
            admin_email = current_app.config.get('MAIL_USERNAME')
            try:
                # First make the sheet accessible to anyone with the link (view only)
                sheet.share('', perm_type='anyone', role='reader')
                current_app.logger.info("Made sheet accessible to anyone with the link (view only)")

                # Then share it specifically with the admin email as an editor
                if admin_email:
                    sheet.share(admin_email, perm_type='user', role='writer')
                    current_app.logger.info(f"Shared sheet with {admin_email}")

                # Get the sheet URL and log it
                sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet.id}/edit"
                current_app.logger.info(f"Sheet URL: {sheet_url}")
                print(f"\nGoogle Sheet created successfully!")
                print(f"You can access it at: {sheet_url}\n")
            except Exception as e:
                current_app.logger.error(f"Error sharing sheet: {str(e)}")
                # Continue even if sharing fails

            # Create the initial worksheets
            try:
                # Create Students worksheet
                students_worksheet = sheet.add_worksheet(title='Students', rows=100, cols=20)
                students_worksheet.append_row(['Roll No', 'Student Name', 'Class', 'Teacher'])
                current_app.logger.info("Created Students worksheet")

                # Create Login Log worksheet
                login_worksheet = sheet.add_worksheet(title='Login Log', rows=100, cols=20)
                login_worksheet.append_row(['ID', 'Username', 'Email', 'Role', 'Last Login'])
                current_app.logger.info("Created Login Log worksheet")

                # Get current month and year
                current_month_year = datetime.now().strftime('%B-%Y')

                # Create worksheet for current month
                month_worksheet = sheet.add_worksheet(title=current_month_year, rows=100, cols=50)
                month_headers = ['Roll No', 'Student Name', 'Class']
                month_worksheet.append_row(month_headers)
                current_app.logger.info(f"Created worksheet for {current_month_year}")

                # Delete the default Sheet1
                try:
                    sheet1 = sheet.worksheet('Sheet1')
                    sheet.del_worksheet(sheet1)
                    current_app.logger.info("Deleted default Sheet1")
                except:
                    pass  # Sheet1 might not exist
            except Exception as e:
                current_app.logger.error(f"Error creating initial worksheet: {str(e)}")
                # Continue even if worksheet creation fails

            return sheet
        except Exception as e:
            current_app.logger.error(f"Error creating new sheet: {str(e)}")
            return None

    except Exception as e:
        current_app.logger.error(f"Error getting or creating attendance sheet: {str(e)}")
        current_app.logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
        return None

def get_month_dates(year=None, month=None):
    """
    Get all dates in the current month or specified month
    """
    from calendar import monthrange

    if year is None or month is None:
        now = datetime.now()
        year = now.year
        month = now.month

    num_days = monthrange(year, month)[1]
    return [datetime(year, month, day).date() for day in range(1, num_days + 1)]

def format_attendance_data_by_date():
    """
    Format attendance data with students as rows and dates as columns
    """
    from app.models import Student, Attendance
    from collections import defaultdict

    # Get all students
    students = Student.query.all()

    # Get all attendance records
    attendance_records = Attendance.query.all()

    # Create a dictionary to store attendance by student and date
    attendance_by_student = defaultdict(dict)

    # Get all dates with attendance records
    attendance_dates = sorted(list(set([record.date for record in attendance_records])))

    # If no attendance dates, use current month dates
    if not attendance_dates:
        attendance_dates = get_month_dates()

    # Organize attendance data by student and date
    for record in attendance_records:
        student_id = record.student_id
        date = record.date
        status = 'P' if record.status else 'A'  # P for Present, A for Absent
        attendance_by_student[student_id][date] = status

    # Prepare data for the worksheet
    headers = ['Roll No', 'Student Name', 'Class']
    for date in attendance_dates:
        headers.append(date.strftime('%d-%m-%Y'))  # Format: DD-MM-YYYY

    rows = [headers]

    for student in students:
        row = [student.roll_number, student.name, student.grade]
        for date in attendance_dates:
            status = attendance_by_student[student.id].get(date, '')  # Empty if no record
            row.append(status)
        rows.append(row)

    return rows, attendance_dates[0].strftime('%B-%Y') if attendance_dates else datetime.now().strftime('%B-%Y')

def sync_login_data():
    """
    Sync login data to Google Sheets
    """
    from app.models import User
    from flask_login import current_user
    from datetime import datetime

    # Get all users
    users = User.query.all()

    # Prepare login data
    headers = ['ID', 'Username', 'Email', 'Role', 'Last Login']
    rows = [headers]

    for user in users:
        role = 'Principal' if user.is_principal() else 'Teacher'
        last_login = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # This would ideally come from user data
        rows.append([user.id, user.username, user.email, role, last_login])

    return rows

def sync_attendance_data():
    """
    Sync attendance data to Google Sheets in the requested format.
    """
    from app.models import Student, Attendance

    try:
        # Get the Google Sheet
        sheet = get_or_create_attendance_sheet()
        if not sheet:
            current_app.logger.error("Failed to get or create Google Sheet")
            return False

        current_app.logger.info(f"Successfully connected to Google Sheet: {sheet.title}")

        # Sync Students data
        try:
            # Get or create the Students worksheet
            try:
                students_worksheet = sheet.worksheet('Students')
                current_app.logger.info("Found existing Students worksheet")
            except gspread.exceptions.WorksheetNotFound:
                current_app.logger.info("Creating new Students worksheet")
                students_worksheet = sheet.add_worksheet(title='Students', rows=100, cols=20)

            # Get student data
            students = Student.query.all()
            current_app.logger.info(f"Found {len(students)} students to sync")

            # Prepare student data
            student_headers = ['Roll No', 'Student Name', 'Class', 'Teacher']
            student_rows = [student_headers]

            for student in students:
                try:
                    teacher_name = student.teacher.display_name if hasattr(student.teacher, 'display_name') else student.teacher.username
                except:
                    teacher_name = "Unknown"

                student_rows.append([student.roll_number, student.name, student.grade, teacher_name])

            # Clear and update the worksheet
            students_worksheet.clear()
            students_worksheet.update(student_rows)

            # Format the header row
            students_worksheet.format('A1:D1', {
                "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8},
                "horizontalAlignment": "CENTER",
                "textFormat": {"bold": True}
            })

            current_app.logger.info(f"Updated Students worksheet with {len(student_rows)-1} student rows")
        except Exception as e:
            current_app.logger.error(f"Error syncing student data: {str(e)}")
            current_app.logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            # Continue with attendance data even if student data fails

        # Sync Login data
        try:
            # Get or create the Login Log worksheet
            try:
                login_worksheet = sheet.worksheet('Login Log')
                current_app.logger.info("Found existing Login Log worksheet")
            except gspread.exceptions.WorksheetNotFound:
                current_app.logger.info("Creating new Login Log worksheet")
                login_worksheet = sheet.add_worksheet(title='Login Log', rows=100, cols=20)

            # Get login data
            login_data = sync_login_data()

            # Clear and update the worksheet
            login_worksheet.clear()
            login_worksheet.update(login_data)

            # Format the header row
            login_worksheet.format('A1:E1', {
                "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8},
                "horizontalAlignment": "CENTER",
                "textFormat": {"bold": True}
            })

            current_app.logger.info(f"Updated Login Log worksheet with {len(login_data)-1} user rows")
        except Exception as e:
            current_app.logger.error(f"Error syncing login data: {str(e)}")
            current_app.logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            # Continue with attendance data even if login data fails

        # Format attendance data by date
        attendance_data, month_year = format_attendance_data_by_date()

        # Get or create the monthly attendance worksheet
        try:
            # Try to find an existing worksheet for this month
            attendance_worksheet = sheet.worksheet(month_year)
            current_app.logger.info(f"Found existing worksheet for {month_year}")
        except gspread.exceptions.WorksheetNotFound:
            # Create a new worksheet for this month
            current_app.logger.info(f"Creating new worksheet for {month_year}")
            attendance_worksheet = sheet.add_worksheet(title=month_year, rows=100, cols=50)
        except Exception as e:
            current_app.logger.error(f"Error accessing worksheet: {str(e)}")
            return False

        # Clear the worksheet
        try:
            attendance_worksheet.clear()
            current_app.logger.info(f"Cleared worksheet for {month_year}")
        except Exception as e:
            current_app.logger.error(f"Error clearing worksheet: {str(e)}")
            # Continue anyway

        # Add the formatted attendance data
        try:
            attendance_worksheet.update(attendance_data)
            current_app.logger.info(f"Updated worksheet with {len(attendance_data)-1} student rows and {len(attendance_data[0])-3} date columns")

            # Format the header row
            attendance_worksheet.format('A1:Z1', {
                "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8},
                "horizontalAlignment": "CENTER",
                "textFormat": {"bold": True}
            })

            # Format the date columns
            for col in range(4, len(attendance_data[0]) + 1):
                col_letter = chr(64 + col)  # Convert column number to letter (A=1, B=2, etc.)
                attendance_worksheet.format(f"{col_letter}2:{col_letter}100", {
                    "horizontalAlignment": "CENTER"
                })

            current_app.logger.info("Applied formatting to the worksheet")
        except Exception as e:
            current_app.logger.error(f"Error updating worksheet: {str(e)}")
            current_app.logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            # Continue anyway

        # Try to delete the Attendance worksheet if it exists (we don't need it anymore)
        try:
            old_attendance_worksheet = sheet.worksheet('Attendance')
            sheet.del_worksheet(old_attendance_worksheet)
            current_app.logger.info("Deleted old Attendance worksheet")
        except:
            # Worksheet might not exist, which is fine
            pass

        # Get the sheet URL and display it
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet.id}/edit"
        current_app.logger.info(f"Successfully synced attendance data to Google Sheets: {sheet_url}")
        print(f"\nAttendance data synced successfully!")
        print(f"You can access the Google Sheet at: {sheet_url}\n")
        return True

    except Exception as e:
        current_app.logger.error(f"Error syncing attendance data to Google Sheets: {str(e)}")
        current_app.logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
        return False

def create_teacher_folder_and_sheet(teacher_name):
    """
    Create a folder and Google Sheet specifically for a teacher.
    
    Args:
        teacher_name (str): The name of the teacher
        
    Returns:
        tuple: (folder_id, sheet_id, sheet_url) or (None, None, None) if unsuccessful
    """
    try:
        from app.utils.google_drive import create_drive_folder
        
        # Create a folder for the teacher
        folder_name = f"{teacher_name} - Attendance Management"
        folder_id = create_drive_folder(folder_name)
        
        if not folder_id:
            current_app.logger.error(f"Failed to create folder for teacher: {teacher_name}")
            return None, None, None
            
        current_app.logger.info(f"Created folder for teacher: {teacher_name}, folder ID: {folder_id}")
            
        # Get the Google Sheets client
        client = get_google_sheets_client()
        if not client:
            current_app.logger.error("Failed to get Google Sheets client")
            return folder_id, None, None
            
        # Create a spreadsheet in the teacher's folder
        sheet_name = f"Attendance Sheet - {teacher_name}"
        sheet = client.create(sheet_name, folder_id)
        sheet_id = sheet.id
        
        current_app.logger.info(f"Created spreadsheet for teacher: {teacher_name}, sheet ID: {sheet_id}")
        
        # Share the sheet with anyone with the link (view only)
        sheet.share('', perm_type='anyone', role='reader')
        
        # Share it with the admin email as an editor
        admin_email = current_app.config.get('MAIL_USERNAME')
        if admin_email:
            sheet.share(admin_email, perm_type='user', role='writer')
            
        # Create the initial worksheets similar to the main attendance sheet
        try:
            # Create Students worksheet
            students_worksheet = sheet.add_worksheet(title='Students', rows=100, cols=20)
            students_worksheet.append_row(['Roll No', 'Student Name', 'Class', 'Teacher'])
            students_worksheet.format('A1:D1', {
                "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8},
                "horizontalAlignment": "CENTER",
                "textFormat": {"bold": True}
            })
            
            # Create Login Log worksheet
            login_worksheet = sheet.add_worksheet(title='Login Log', rows=100, cols=20)
            login_worksheet.append_row(['ID', 'Username', 'Email', 'Role', 'Last Login'])
            login_worksheet.format('A1:E1', {
                "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8},
                "horizontalAlignment": "CENTER",
                "textFormat": {"bold": True}
            })
            
            # Get current month and year
            current_month_year = datetime.now().strftime('%B-%Y')
            
            # Create worksheet for current month
            month_worksheet = sheet.add_worksheet(title=current_month_year, rows=100, cols=50)
            month_headers = [ 'Student Name','Roll No', 'Class']
            month_worksheet.append_row(month_headers)
            month_worksheet.format('A1:C1', {
                "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8},
                "horizontalAlignment": "CENTER",
                "textFormat": {"bold": True}
            })
            
            # Delete the default Sheet1
            try:
                sheet1 = sheet.worksheet('Sheet1')
                sheet.del_worksheet(sheet1)
            except:
                pass  # Sheet1 might not exist
        except Exception as e:
            current_app.logger.error(f"Error creating initial worksheets: {str(e)}")
            # Continue even if worksheet creation fails
            
        # Get the sheet URL
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
        
        return folder_id, sheet_id, sheet_url
        
    except Exception as e:
        current_app.logger.error(f"Error creating teacher folder and sheet: {str(e)}")
        return None, None, None

def format_teacher_attendance_data(teacher_id):
    """
    Format attendance data for a specific teacher
    
    Args:
        teacher_id (int): ID of the teacher
        
    Returns:
        tuple: (attendance_data, month_year)
    """
    from app.models import Student, Attendance
    from collections import defaultdict

    # Get only students of this teacher
    students = Student.query.filter_by(teacher_id=teacher_id).all()
    
    # Prepare headers for the worksheet
    headers = ['Student Name', 'Roll No', 'Class']
    rows = [headers]
    
    # If no students found, return empty data
    if not students:
        current_app.logger.warning(f"No students found for teacher ID: {teacher_id}")
        return rows, datetime.now().strftime('%B-%Y')

    # Get attendance records for these students
    student_ids = [student.id for student in students]
    attendance_records = Attendance.query.filter(Attendance.student_id.in_(student_ids)).all()

    # Create a dictionary to store attendance by student and date
    attendance_by_student = defaultdict(dict)

    # Get all dates with attendance records
    attendance_dates = sorted(list(set([record.date for record in attendance_records])))

    # If no attendance dates, use current month dates
    if not attendance_dates:
        attendance_dates = get_month_dates()

    # Organize attendance data by student and date
    for record in attendance_records:
        student_id = record.student_id
        date = record.date
        status = 'P' if record.status else 'A'  # P for Present, A for Absent
        attendance_by_student[student_id][date] = status

    # Add dates to the headers
    for date in attendance_dates:
        headers.append(date.strftime('%d-%m-%Y'))  # Format: DD-MM-YYYY

    # Add data rows for each student
    for student in students:
        row = [student.name, student.roll_number, student.grade]
        for date in attendance_dates:
            status = attendance_by_student[student.id].get(date, '')  # Empty if no record
            row.append(status)
        rows.append(row)

    return rows, attendance_dates[0].strftime('%B-%Y') if attendance_dates else datetime.now().strftime('%B-%Y')

def get_teacher_sheet_id(teacher_id):
    """
    Get the Google Sheet ID for a specific teacher
    
    Args:
        teacher_id (int): ID of the teacher
        
    Returns:
        str: Sheet ID or None if not found
    """
    from app.models import User
    
    teacher = User.query.get(teacher_id)
    if not teacher:
        return None
        
    # Check if sheet ID exists in config
    sheet_id_key = f"TEACHER_SHEET_ID_{teacher_id}"
    sheet_id = current_app.config.get(sheet_id_key)
    
    if not sheet_id:
        # Try to create a new sheet for the teacher
        folder_id, sheet_id, sheet_url = create_teacher_folder_and_sheet(teacher.display_name)
        if sheet_id:
            # Store the sheet ID in config for future use
            current_app.config[sheet_id_key] = sheet_id
            
    return sheet_id

def sync_teacher_attendance_data(teacher_id):
    """
    Sync attendance data to a teacher-specific Google Sheet
    
    Args:
        teacher_id (int): ID of the teacher
        
    Returns:
        bool: True if sync was successful, False otherwise
    """
    from app.models import User, Student
    
    try:
        # Get the teacher
        teacher = User.query.get(teacher_id)
        if not teacher or not teacher.is_teacher():
            current_app.logger.error(f"Invalid teacher ID: {teacher_id}")
            return False
            
        # Get the sheet ID
        sheet_id = get_teacher_sheet_id(teacher_id)
        if not sheet_id:
            current_app.logger.error(f"Failed to get sheet ID for teacher: {teacher_id}")
            return False
            
        # Get the Google Sheets client
        client = get_google_sheets_client()
        if not client:
            current_app.logger.error("Failed to get Google Sheets client")
            return False
            
        # Open the sheet
        sheet = client.open_by_key(sheet_id)
        
        # Update the students worksheet
        try:
            # Get or create the Students worksheet
            try:
                students_worksheet = sheet.worksheet('Students')
            except gspread.exceptions.WorksheetNotFound:
                students_worksheet = sheet.add_worksheet(title='Students', rows=100, cols=20)
                
            # Get student data for this teacher
            students = Student.query.filter_by(teacher_id=teacher_id).all()
            
            # Prepare student data
            student_headers = ['Student Name', 'Roll No', 'Class', 'Teacher']
            student_rows = [student_headers]
            
            for student in students:
                student_rows.append([student.name, student.roll_number, student.grade, teacher.display_name])
                
            # Clear and update the worksheet
            students_worksheet.clear()
            students_worksheet.update(student_rows)
            
            # Format the header row
            students_worksheet.format('A1:D1', {
                "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8},
                "horizontalAlignment": "CENTER",
                "textFormat": {"bold": True}
            })
        except Exception as e:
            current_app.logger.error(f"Error updating students worksheet: {str(e)}")
            # Continue with attendance data even if student data fails
            
        # Format attendance data for this teacher
        attendance_data, month_year = format_teacher_attendance_data(teacher_id)
        
        # Get or create the monthly attendance worksheet
        try:
            # Try to find an existing worksheet for this month
            try:
                attendance_worksheet = sheet.worksheet(month_year)
            except gspread.exceptions.WorksheetNotFound:
                attendance_worksheet = sheet.add_worksheet(title=month_year, rows=100, cols=50)
                
            # Clear and update the worksheet
            attendance_worksheet.clear()
            attendance_worksheet.update(attendance_data)
            
            # Format the header row - all columns in the header
            header_range = f"A1:{chr(64 + len(attendance_data[0]))}1"
            attendance_worksheet.format(header_range, {
                "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8},
                "horizontalAlignment": "CENTER",
                "textFormat": {"bold": True}
            })
            
            # Format the date columns starting from column D (4th column)
            if len(attendance_data[0]) > 3:  # Make sure we have date columns
                for col in range(4, len(attendance_data[0]) + 1):
                    col_letter = chr(64 + col)  # Convert column number to letter (A=1, B=2, etc.)
                    attendance_worksheet.format(f"{col_letter}2:{col_letter}{len(attendance_data)}", {
                        "horizontalAlignment": "CENTER"
                    })
        except Exception as e:
            current_app.logger.error(f"Error updating attendance worksheet: {str(e)}")
            current_app.logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            return False
            
        current_app.logger.info(f"Successfully synced attendance data for teacher: {teacher.display_name}")
        return True
    except Exception as e:
        current_app.logger.error(f"Error syncing teacher attendance data: {str(e)}")
        return False
