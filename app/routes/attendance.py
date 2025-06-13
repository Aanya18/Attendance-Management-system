from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import pytz
from app import db
from app.models import Student, Attendance, get_local_datetime, get_local_date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from app.utils.auto_sync import auto_sync_to_sheets
from app.utils.google_sheets import sync_attendance_data

attendance = Blueprint('attendance', __name__, url_prefix='/attendance')

# Helper function to get current local time
def get_today():
    # Set to your local timezone, e.g., 'Asia/Kolkata' for India
    local_tz = pytz.timezone('Asia/Kolkata')
    utc_now = datetime.utcnow().replace(tzinfo=pytz.UTC)
    local_now = utc_now.astimezone(local_tz)
    return local_now.date()

def update_google_sheet(attendance_record):
    """Update Google Sheet with attendance data"""
    try:
        # Load credentials from app config
        credentials_json = current_app.config['GOOGLE_SHEETS_CREDENTIALS']
        sheet_id = current_app.config['ATTENDANCE_SHEET_ID']

        if not credentials_json or not sheet_id:
            current_app.logger.warning("Google Sheets credentials or sheet ID not configured")
            return False

        # Parse credentials JSON
        credentials_dict = json.loads(credentials_json)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

        # Authorize and open the sheet
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(sheet_id)

        # Get or create worksheet for the current month
        month_year = attendance_record.date.strftime('%B %Y')
        try:
            worksheet = sheet.worksheet(month_year)
        except gspread.exceptions.WorksheetNotFound:
            # Create a new worksheet for this month
            worksheet = sheet.add_worksheet(title=month_year, rows=100, cols=20)
            # Add headers
            worksheet.update('A1:D1', [['Date', 'Student Name', 'Roll Number', 'Status']])

        # Find the next empty row
        records = worksheet.get_all_values()
        next_row = len(records) + 1

        # Add the attendance record
        status = "Present" if attendance_record.status else "Absent"
        worksheet.update(f'A{next_row}:D{next_row}',
                        [[attendance_record.date.strftime('%Y-%m-%d'),
                          attendance_record.student.name,
                          attendance_record.student.roll_number,
                          status]])

        return True
    except Exception as e:
        current_app.logger.error(f"Error updating Google Sheet: {str(e)}")
        return False

@attendance.route('/mark', methods=['GET', 'POST'])
@login_required
def mark():
    # Only teachers can mark attendance
    if not current_user.is_teacher():
        flash('Only teachers can mark attendance', 'danger')
        return redirect(url_for('students.list'))

    today = get_today()
    students = Student.query.filter_by(teacher_id=current_user.id).all()

    # Check if already marked for today
    attendance_count = Attendance.query.filter(
        Attendance.student_id.in_([s.id for s in students]),
        Attendance.date == today
    ).count()

    # Handle POST request
    if request.method == 'POST':
        any_attendance_marked = False

        # Process attendance for each student
        for student in students:
            status_key = f'status_{student.id}'
            
            if status_key in request.form:
                status_value = request.form.get(status_key)
                
                # Set attendance status based on the value
                if status_value in ['present', 'absent']:
                    status = (status_value == 'present')

                    # Check if attendance record already exists for this student and date
                    existing_record = Attendance.query.filter_by(
                        student_id=student.id,
                        date=today
                    ).first()

                    if existing_record:
                        # Update existing record
                        existing_record.status = status
                        existing_record.last_modified = get_local_datetime()
                    else:
                        # Create new record
                        new_attendance = Attendance(
                            student_id=student.id,
                            date=today,
                            status=status,
                            marked_by=current_user.id,
                            last_modified=get_local_datetime()
                        )
                        db.session.add(new_attendance)

                    any_attendance_marked = True

        # Commit changes if any attendance was marked
        if any_attendance_marked:
            db.session.commit()
            
            # Store the teacher ID for the auto-sync function to use
            current_user.marked_student_id = students[0].id if students else None

            # Auto-sync to Google Sheets after all attendance records are updated
            sync_result = auto_sync_to_sheets()
            if not sync_result:
                current_app.logger.warning("Auto-sync failed after marking attendance")
                
            if sync_result:
                flash('Attendance marked successfully and Google Sheet updated!', 'success')
            else:
                flash('Attendance marked successfully but Google Sheet update failed.', 'warning')
        else:
            flash('No attendance was marked. Please select attendance status for at least one student.', 'warning')
            
        return redirect(url_for('attendance.view'))

    # For GET request, show the form
    return render_template('attendance/mark.html',
                          title='Mark Attendance',
                          students=students,
                          today=today)

@attendance.route('/view', methods=['GET'])
@login_required
def view():
    today = get_today()

    # Get date from query parameters, default to today
    date_str = request.args.get('date')
    try:
        if date_str:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            selected_date = today
    except ValueError:
        flash('Invalid date format', 'danger')
        selected_date = today

    # Check for future dates
    if selected_date > today:
        flash('Cannot view attendance for future dates', 'danger')
        selected_date = today

    # Teachers can only view attendance for the current date
    if current_user.is_teacher() and selected_date != today:
        flash('Teachers can only view attendance for the current date', 'danger')
        selected_date = today

    # For teachers, show only their students
    if current_user.is_teacher():
        students = Student.query.filter_by(teacher_id=current_user.id).all()
        
        attendance_data = []
        for student in students:
            attendance_record = Attendance.query.filter_by(
                student_id=student.id,
                date=selected_date
            ).first()
            
            attendance_data.append({
                'student': student,
                'attendance': attendance_record
            })
            
        return render_template('attendance/view.html',
                              title='View Attendance',
                              attendance_data=attendance_data,
                              selected_date=selected_date,
                              today=today)
    # For principals, show all students
    else:
        from app.models import User
        teachers = User.query.filter_by(role='teacher').all()
        
        all_attendance_data = []
        for teacher in teachers:
            students = Student.query.filter_by(teacher_id=teacher.id).all()
            
            for student in students:
                attendance_record = Attendance.query.filter_by(
                    student_id=student.id,
                    date=selected_date
                ).first()
                
                all_attendance_data.append({
                    'student': student,
                    'attendance': attendance_record,
                    'teacher': teacher
                })
                
        return render_template('attendance/view_all.html',
                              title='View Attendance',
                              attendance_data=all_attendance_data,
                              selected_date=selected_date,
                              today=today)

@attendance.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    # Get the attendance record
    attendance_record = Attendance.query.get_or_404(id)
    
    # Only principal and the teacher who marked it can edit
    if not current_user.is_principal() and current_user.id != attendance_record.marked_by:
        flash('You do not have permission to edit this attendance record', 'danger')
        return redirect(url_for('attendance.view'))
    
    # Handle POST request
    if request.method == 'POST':
        status = request.form.get('status')
        
        if status in ['present', 'absent']:
            # Update attendance record
            attendance_record.status = (status == 'present')
            attendance_record.last_modified = get_local_datetime()
            db.session.commit()
            
            # Sync to Google Sheets
            student = Student.query.get(attendance_record.student_id)
            if student:
                sync_result = sync_attendance_data(student.teacher_id)
                if sync_result:
                    flash('Attendance record updated successfully and Google Sheet updated!', 'success')
                else:
                    flash('Attendance record updated successfully but Google Sheet update failed.', 'warning')
            else:
                flash('Attendance record updated successfully but student not found.', 'warning')
                
            return redirect(url_for('attendance.view', date=attendance_record.date.strftime('%Y-%m-%d')))
        else:
            flash('Invalid attendance status', 'danger')
    
    # For GET request, show the form
    student = Student.query.get(attendance_record.student_id)
    return render_template('attendance/edit.html',
                          title='Edit Attendance',
                          attendance=attendance_record,
                          student=student)
