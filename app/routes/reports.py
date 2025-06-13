from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, make_response, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from calendar import monthrange
from app import db
from app.models import Student, Attendance, User
from sqlalchemy import func
import io
import csv
import os
from app.utils.google_sheets import sync_attendance_data, sync_teacher_attendance_data, get_teacher_sheet_id
from app.utils.email_service import send_report_email
from app.utils.excel_export import export_attendance_to_excel
from database.index import flush_database, delete_teacher_sheet

reports = Blueprint('reports', __name__, url_prefix='/reports')

def get_month_dates(year, month):
    """Get all dates for a given month and year"""
    num_days = monthrange(year, month)[1]
    return [datetime(year, month, day).date() for day in range(1, num_days + 1)]

def generate_monthly_report(year, month):
    """Generate monthly attendance report data"""
    dates = get_month_dates(year, month)
    today = datetime.now().date()

    # Get all students and teachers
    students = Student.query.all()
    teachers = User.query.filter_by(role='teacher').all()

    # Daily summary (how many present/absent each day)
    daily_summary = []
    for date in dates:
        # Skip future dates
        if date > today:
            continue

        present_count = Attendance.query.filter_by(date=date, status=True).count()
        absent_count = Attendance.query.filter_by(date=date, status=False).count()
        total_marked = present_count + absent_count

        if total_marked > 0:
            daily_summary.append({
                'date': date,
                'present': present_count,
                'absent': absent_count,
                'total_marked': total_marked,
                'present_percentage': round((present_count / total_marked) * 100, 2) if total_marked > 0 else 0
            })

    # Student summary grouped by teacher
    teachers_with_students = []
    
    for teacher in teachers:
        teacher_students = Student.query.filter_by(teacher_id=teacher.id).all()
        if not teacher_students:
            continue
            
        student_summary = []
        for student in teacher_students:
            total_days = 0
            present_days = 0

            for date in dates:
                # Skip future dates
                if date > today:
                    continue

                attendance = Attendance.query.filter_by(
                    student_id=student.id,
                    date=date
                ).first()

                if attendance:
                    total_days += 1
                    if attendance.status:
                        present_days += 1

            if total_days > 0:
                attendance_percentage = round((present_days / total_days) * 100, 2)
            else:
                attendance_percentage = 0

            student_summary.append({
                'student': student,
                'total_days': total_days,
                'present_days': present_days,
                'absent_days': total_days - present_days,
                'attendance_percentage': attendance_percentage
            })
        
        if student_summary:  # Only add if there are students with attendance
            teachers_with_students.append({
                'teacher': teacher,
                'student_summary': student_summary
            })

    # Legacy student summary for compatibility with existing templates and email reports
    student_summary = []
    for student in students:
        total_days = 0
        present_days = 0

        for date in dates:
            # Skip future dates
            if date > today:
                continue

            attendance = Attendance.query.filter_by(
                student_id=student.id,
                date=date
            ).first()

            if attendance:
                total_days += 1
                if attendance.status:
                    present_days += 1

        if total_days > 0:
            attendance_percentage = round((present_days / total_days) * 100, 2)
        else:
            attendance_percentage = 0

        student_summary.append({
            'student': student,
            'total_days': total_days,
            'present_days': present_days,
            'absent_days': total_days - present_days,
            'attendance_percentage': attendance_percentage
        })

    return {
        'daily_summary': daily_summary,
        'student_summary': student_summary,
        'teachers_with_students': teachers_with_students,
        'month_name': datetime(year, month, 1).strftime('%B'),
        'year': year
    }

def send_monthly_report_email(year, month, report_data):
    """Send monthly report via email to teachers, principal, and additional recipients"""
    try:
        # Create CSV for daily summary
        daily_csv = io.StringIO()
        daily_writer = csv.writer(daily_csv)
        daily_writer.writerow(['Date', 'Present', 'Absent', 'Total Marked', 'Present Percentage'])
        for day in report_data['daily_summary']:
            daily_writer.writerow([
                day['date'].strftime('%Y-%m-%d'),
                day['present'],
                day['absent'],
                day['total_marked'],
                f"{day['present_percentage']}%"
            ])

        # Create CSV for student summary
        student_csv = io.StringIO()
        student_writer = csv.writer(student_csv)
        student_writer.writerow(['Student Name', 'Roll Number', 'Grade', 'Total Days', 'Present Days', 'Absent Days', 'Attendance Percentage'])
        for student_data in report_data['student_summary']:
            student = student_data['student']
            student_writer.writerow([
                student.name,
                student.roll_number,
                student.grade,
                student_data['total_days'],
                student_data['present_days'],
                student_data['absent_days'],
                f"{student_data['attendance_percentage']}%"
            ])

        # Get all teachers and principals
        users = User.query.all()
        recipients = [user.email for user in users]

        # Add additional recipients from environment variable
        additional_recipients = current_app.config.get('REPORT_RECIPIENTS', '')
        if additional_recipients:
            if isinstance(additional_recipients, str):
                # Split by comma if it's a comma-separated string
                additional_recipients = [email.strip() for email in additional_recipients.split(',')]
                recipients.extend(additional_recipients)

        # Remove duplicates while preserving order
        unique_recipients = []
        for email in recipients:
            if email and email not in unique_recipients:
                unique_recipients.append(email)

        # Create and send email
        month_name = report_data['month_name']
        year = report_data['year']

        # Create email subject
        subject = f'Monthly Attendance Report - {month_name} {year}'

        # Create attachments
        attachments = [
            (f'daily_summary_{month_name}_{year}.csv', 'text/csv', daily_csv.getvalue()),
            (f'student_summary_{month_name}_{year}.csv', 'text/csv', student_csv.getvalue())
        ]

        # Send the email using our email service
        success = send_report_email(subject, unique_recipients, report_data, month_name, year, attachments)

        if success:
            current_app.logger.info(f"Monthly report sent successfully to: {', '.join(unique_recipients)}")
        else:
            current_app.logger.error(f"Failed to send monthly report to: {', '.join(unique_recipients)}")

        return success
    except Exception as e:
        current_app.logger.error(f"Error sending report email: {str(e)}")
        current_app.logger.error(f"Mail settings: Server={current_app.config.get('MAIL_SERVER')}, Port={current_app.config.get('MAIL_PORT')}, Username={current_app.config.get('MAIL_USERNAME')}")
        current_app.logger.error(f"TLS Enabled: {current_app.config.get('MAIL_USE_TLS')}")
        current_app.logger.error(f"Password length: {len(current_app.config.get('MAIL_PASSWORD') or '')}")

        # Print to console for immediate debugging
        print(f"\nEMAIL ERROR: {str(e)}")
        print(f"Mail Server: {current_app.config.get('MAIL_SERVER')}")
        print(f"Mail Port: {current_app.config.get('MAIL_PORT')}")
        print(f"TLS Enabled: {current_app.config.get('MAIL_USE_TLS')}")
        print(f"Username: {current_app.config.get('MAIL_USERNAME')}")
        print(f"Password length: {len(current_app.config.get('MAIL_PASSWORD') or '')}")

        return False

@reports.route('/monthly', methods=['GET', 'POST'])
@login_required
def monthly():
    # Only principals can access monthly reports
    if not current_user.is_principal():
        flash('You do not have permission to access monthly reports', 'danger')
        return redirect(url_for('students.list'))
        
    today = datetime.now().date()
    current_year = today.year
    current_month = today.month

    # Handle date selection from form
    if request.method == 'POST':
        try:
            year = int(request.form.get('year', current_year))
            month = int(request.form.get('month', current_month))
            
            if year < 2020 or year > current_year + 1:
                flash('Invalid year selected', 'danger')
                year = current_year
            
            if month < 1 or month > 12:
                flash('Invalid month selected', 'danger')
                month = current_month
                
            # Don't allow future dates
            if year > current_year or (year == current_year and month > current_month):
                flash('Cannot view reports for future months', 'warning')
                year = current_year
                month = current_month
        except:
            year = current_year
            month = current_month
            flash('Invalid date format', 'danger')
    else:
        # Default to current month
        year = current_year
        month = current_month
    
    # Generate report data
    report_data = generate_monthly_report(year, month)
    
    # Get years and months for dropdowns
    years = range(2020, current_year + 1)
    months = range(1, 13)

    # Get month name and year for display
    month_name = datetime(year, month, 1).strftime('%B')
    
    # For email sending functionality
    email_sent = False
    if request.method == 'POST' and request.form.get('action') == 'send_email':
        if current_user.is_principal():  # Only principals can send emails
            try:
                send_monthly_report_email(year, month, report_data)
                flash('Monthly report sent via email successfully!', 'success')
                email_sent = True
            except Exception as e:
                current_app.logger.error(f"Error sending email: {str(e)}")
                flash(f'Error sending email: {str(e)}', 'danger')
    
    # For sync to Google Sheets functionality
    synced = False
    if request.method == 'POST' and request.form.get('action') == 'sync_sheets':
        if current_user.is_principal():  # Only principals can sync to sheets
            try:
                sync_attendance_data()
                flash('Attendance data synced to Google Sheets successfully!', 'success')
                synced = True
            except Exception as e:
                current_app.logger.error(f"Error syncing to sheets: {str(e)}")
                flash(f'Error syncing to Google Sheets: {str(e)}', 'danger')
    
    return render_template('reports/monthly.html', 
                          title=f'Monthly Report - {month_name} {year}',
                          report_data=report_data,
                          selected_year=year,
                          selected_month=month,
                          years=years,
                          months=months,
                          month_name=month_name,
                          email_sent=email_sent,
                          synced=synced)

@reports.route('/monthly/download', methods=['GET'])
@login_required
def download_monthly_report():
    # Only principals can download reports
    if not current_user.is_principal():
        flash('You do not have permission to download reports', 'danger')
        return redirect(url_for('students.list'))
    
    today = datetime.now().date()
    try:
        year = int(request.args.get('year', today.year))
        month = int(request.args.get('month', today.month))
        format = request.args.get('format', 'csv').lower()
        
        if year < 2020 or year > today.year:
            flash('Invalid year selected', 'danger')
            return redirect(url_for('reports.monthly'))
        
        if month < 1 or month > 12:
            flash('Invalid month selected', 'danger')
            return redirect(url_for('reports.monthly'))
            
        # Don't allow future dates
        if year > today.year or (year == today.year and month > today.month):
            flash('Cannot download reports for future months', 'warning')
            return redirect(url_for('reports.monthly'))
            
    except:
        flash('Invalid date parameters', 'danger')
        return redirect(url_for('reports.monthly'))
        
    # Generate report data
    report_data = generate_monthly_report(year, month)
    
    # Check if Excel format is requested
    if format == 'excel':
        # Generate Excel file
        file_path = 'Student_Attendance.xlsx'
        if export_attendance_to_excel(file_path):
            # Read the file and create a response
            with open(file_path, 'rb') as f:
                excel_data = f.read()

            # Create response
            response = make_response(excel_data)
            response.headers["Content-Disposition"] = f"attachment; filename=Student_Attendance.xlsx"
            response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

            return response
        else:
            flash('Failed to generate Excel report', 'danger')
            return redirect(url_for('reports.monthly'))

    # Default to CSV format
    # Create CSV for daily summary
    output = io.StringIO()
    writer = csv.writer(output)

    # Write headers
    writer.writerow(['Monthly Attendance Report', f'{report_data["month_name"]} {report_data["year"]}'])
    writer.writerow([])

    # Daily summary
    writer.writerow(['Daily Summary'])
    writer.writerow(['Date', 'Present', 'Absent', 'Total Marked', 'Present Percentage'])
    for day in report_data['daily_summary']:
        writer.writerow([
            day['date'].strftime('%Y-%m-%d'),
            day['present'],
            day['absent'],
            day['total_marked'],
            f"{day['present_percentage']}%"
        ])

    writer.writerow([])

    # Student summary
    writer.writerow(['Student Summary'])
    writer.writerow(['Student Name', 'Roll Number', 'Grade', 'Total Days', 'Present Days', 'Absent Days', 'Attendance Percentage'])
    for student_data in report_data['student_summary']:
        student = student_data['student']
        writer.writerow([
            student.name,
            student.roll_number,
            student.grade,
            student_data['total_days'],
            student_data['present_days'],
            student_data['absent_days'],
            f"{student_data['attendance_percentage']}%"
        ])

    # Create response
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=monthly_report_{report_data['month_name']}_{report_data['year']}.csv"
    response.headers["Content-type"] = "text/csv"

    return response

@reports.route('/student/<int:id>', methods=['GET'])
@login_required
def student(id):
    # Teachers can access student reports but only for their students and current date
    if not current_user.is_principal() and not current_user.is_teacher():
        flash('Only principals and teachers can access reports', 'danger')
        return redirect(url_for('students.list'))

    # Teachers can only view their own students
    student = Student.query.get_or_404(id)
    if current_user.is_teacher() and student.teacher_id != current_user.id:
        flash('You can only view reports for your own students', 'danger')
        return redirect(url_for('students.list'))

    # Get date range from query parameters, default to current month
    now = datetime.now()
    year = int(request.args.get('year', now.year))
    month = int(request.args.get('month', now.month))

    # Teachers can only view current month/year
    if current_user.is_teacher() and (year != now.year or month != now.month):
        flash('Teachers can only view reports for the current month', 'danger')
        year = now.year
        month = now.month

    # Check if download is requested
    if request.args.get('download') == '1':
        return download_student_report(student, year, month)

    dates = get_month_dates(year, month)

    # Get attendance for each day
    attendance_data = []
    total_days = 0
    present_days = 0

    today = datetime.now().date()

    for date in dates:
        # Skip future dates
        if date > today:
            continue

        attendance = Attendance.query.filter_by(
            student_id=student.id,
            date=date
        ).first()

        if attendance:
            total_days += 1
            if attendance.status:
                present_days += 1

            attendance_data.append({
                'date': date,
                'status': 'Present' if attendance.status else 'Absent',
                'marked_by': attendance.marker.display_name,
                'last_modified': attendance.last_modified
            })
        else:
            attendance_data.append({
                'date': date,
                'status': 'Not Marked',
                'marked_by': None,
                'last_modified': None
            })

    # Calculate attendance percentage
    if total_days > 0:
        attendance_percentage = round((present_days / total_days) * 100, 2)
    else:
        attendance_percentage = 0

    return render_template('reports/student.html',
                          title=f'Student Report - {student.name}',
                          student=student,
                          attendance_data=attendance_data,
                          total_days=total_days,
                          present_days=present_days,
                          absent_days=total_days - present_days,
                          attendance_percentage=attendance_percentage,
                          selected_year=year,
                          selected_month=month,
                          month_name=datetime(year, month, 1).strftime('%B'),
                          is_teacher=current_user.is_teacher())

# Excel download route removed as per user request

@reports.route('/sync-sheets', methods=['GET', 'POST'])
@login_required
def sync_sheets():
    """View to manually sync attendance data to Google Sheets"""
    # Only principals can sync data
    if not current_user.is_principal():
        flash('You do not have permission to sync data to Google Sheets', 'danger')
        return redirect(url_for('students.list'))
        
    if request.method == 'POST':
        try:
            # Sync all data
            result = sync_attendance_data()
            if result:
                flash('Attendance data synced to Google Sheets successfully!', 'success')
            else:
                flash('Error syncing attendance data to Google Sheets', 'danger')
        except Exception as e:
            current_app.logger.error(f"Error syncing to sheets: {str(e)}")
            flash(f'Error syncing to Google Sheets: {str(e)}', 'danger')
            
    # Get links to all teacher sheets for display
    sheet_links = get_all_sheet_links()
    
    return render_template('reports/sync_sheets.html', title='Sync to Google Sheets', sheet_links=sheet_links)
    
def get_all_sheet_links():
    """Get links to all teacher sheets"""
    from app.models import User
    from app.utils.google_sheets import get_teacher_sheet_id
    
    sheet_links = []
    
    # For principals, show links to all teachers' sheets
    if current_user.is_principal():
        teachers = User.query.filter_by(role='teacher').all()
        
        for teacher in teachers:
            sheet_id = get_teacher_sheet_id(teacher.id)
            if sheet_id:
                sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
                sheet_links.append({
                    'teacher': teacher,
                    'url': sheet_url
                })
    
    return sheet_links

def download_student_report(student, year, month):
    """Generate a downloadable CSV report for a student"""
    dates = get_month_dates(year, month)
    month_name = datetime(year, month, 1).strftime('%B')

    # Get attendance for each day
    attendance_data = []
    total_days = 0
    present_days = 0

    today = datetime.now().date()

    for date in dates:
        # Skip future dates
        if date > today:
            continue

        attendance = Attendance.query.filter_by(
            student_id=student.id,
            date=date
        ).first()

        if attendance:
            total_days += 1
            if attendance.status:
                present_days += 1

            attendance_data.append({
                'date': date,
                'status': 'Present' if attendance.status else 'Absent',
                'marked_by': attendance.marker.display_name,
                'last_modified': attendance.last_modified
            })
        else:
            attendance_data.append({
                'date': date,
                'status': 'Not Marked',
                'marked_by': None,
                'last_modified': None
            })

    # Calculate attendance percentage
    if total_days > 0:
        attendance_percentage = round((present_days / total_days) * 100, 2)
    else:
        attendance_percentage = 0

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Write headers
    writer.writerow([f'Student Attendance Report - {student.name}'])
    writer.writerow([f'Month: {month_name} {year}'])
    writer.writerow([])

    # Student info
    writer.writerow(['Student Information'])
    writer.writerow(['Name', student.name])
    writer.writerow(['Roll Number', student.roll_number])
    writer.writerow(['Grade', student.grade])
    writer.writerow(['Teacher', student.teacher.display_name])
    writer.writerow([])

    # Summary
    writer.writerow(['Attendance Summary'])
    writer.writerow(['Total Days', total_days])
    writer.writerow(['Present Days', present_days])
    writer.writerow(['Absent Days', total_days - present_days])
    writer.writerow(['Attendance Percentage', f'{attendance_percentage}%'])
    writer.writerow([])

    # Daily attendance
    writer.writerow(['Daily Attendance'])
    writer.writerow(['Date', 'Day', 'Status', 'Marked By'])

    for item in attendance_data:
        writer.writerow([
            item['date'].strftime('%Y-%m-%d'),
            item['date'].strftime('%A'),
            item['status'],
            item['marked_by'] if item['marked_by'] else '-'
        ])

    # Create response
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=student_report_{student.name}_{month_name}_{year}.csv"
    response.headers["Content-type"] = "text/csv"

    return response

@reports.route('/admin/flush-options', methods=['GET', 'POST'])
@login_required
def flush_options():
    """View to allow principals to flush database and reset Google Sheets"""
    # Only principals can access this page
    if not current_user.is_principal():
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('students.list'))
    
    # Get all teachers for the dropdown
    teachers = User.query.filter_by(role='teacher').all()
    
    # Process form submission
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'flush-db':
            success, message = flush_database()
            flash(message, 'success' if success else 'danger')
            return redirect(url_for('reports.flush_options'))
            
        elif action == 'reset-all-sheets':
            success, message = delete_teacher_sheet()
            flash(message, 'success' if success else 'danger')
            return redirect(url_for('reports.flush_options'))
            
        elif action == 'reset-teacher-sheet':
            teacher_id = request.form.get('teacher_id')
            if teacher_id and teacher_id.isdigit():
                success, message = delete_teacher_sheet(int(teacher_id))
                flash(message, 'success' if success else 'danger')
            else:
                flash('Invalid teacher selected', 'danger')
            return redirect(url_for('reports.flush_options'))
    
    return render_template('reports/flush_options.html', 
                          title='Database & Sheet Management',
                          teachers=teachers)
