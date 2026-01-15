"""
Student routes - For students to view their own profile and attendance
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Student, Attendance, User
from app.utils.decorators import student_required
from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length
from datetime import datetime, date
from calendar import monthrange

student = Blueprint('student', __name__, url_prefix='/student')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6, message='Password must be at least 6 characters long')])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')])
    submit = SubmitField('Change Password')


@student.route('/profile')
@login_required
@student_required
def profile():
    """Student profile page - shows their own information"""
    # Get student record linked to current user
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    if not student:
        flash('Student profile not found. Please contact administrator.', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Get teacher information
    from app.models import User
    teacher = User.query.get(student.teacher_id)
    
    # Get attendance statistics
    total_attendance = Attendance.query.filter_by(student_id=student.id).count()
    present_count = Attendance.query.filter_by(student_id=student.id, status=True).count()
    absent_count = Attendance.query.filter_by(student_id=student.id, status=False).count()
    
    # Calculate attendance percentage
    if total_attendance > 0:
        attendance_percentage = round((present_count / total_attendance) * 100, 2)
    else:
        attendance_percentage = 0
    
    return render_template('student/profile.html',
                         title='My Profile',
                         student=student,
                         teacher=teacher,
                         total_attendance=total_attendance,
                         present_count=present_count,
                         absent_count=absent_count,
                         attendance_percentage=attendance_percentage)


@student.route('/attendance')
@login_required
@student_required
def attendance():
    """Student attendance view - shows their own attendance"""
    # Get student record linked to current user
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    if not student:
        flash('Student profile not found. Please contact administrator.', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Get date from query parameters, default to current month
    today = date.today()
    year = int(request.args.get('year', today.year))
    month = int(request.args.get('month', today.month))
    
    # Get all dates in the selected month
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    
    # Get attendance records for the month
    attendance_records = Attendance.query.filter(
        Attendance.student_id == student.id,
        Attendance.date >= first_day,
        Attendance.date <= last_day
    ).order_by(Attendance.date.desc()).all()
    
    # Create a dictionary for quick lookup
    attendance_dict = {record.date: record for record in attendance_records}
    
    # Get all dates in month
    dates_in_month = []
    current_date = first_day
    while current_date <= last_day:
        dates_in_month.append({
            'date': current_date,
            'attendance': attendance_dict.get(current_date),
            'is_future': current_date > today
        })
        # Move to next day
        from datetime import timedelta
        current_date += timedelta(days=1)
    
    # Calculate statistics
    total_days = len([d for d in dates_in_month if not d['is_future']])
    present_days = len([d for d in dates_in_month if d['attendance'] and d['attendance'].status and not d['is_future']])
    absent_days = len([d for d in dates_in_month if d['attendance'] and not d['attendance'].status and not d['is_future']])
    not_marked = total_days - present_days - absent_days
    
    if total_days > 0:
        attendance_percentage = round((present_days / total_days) * 100, 2)
    else:
        attendance_percentage = 0
    
    return render_template('student/attendance.html',
                         title='My Attendance',
                         student=student,
                         dates_in_month=dates_in_month,
                         selected_year=year,
                         selected_month=month,
                         month_name=datetime(year, month, 1).strftime('%B'),
                         total_days=total_days,
                         present_days=present_days,
                         absent_days=absent_days,
                         not_marked=not_marked,
                         attendance_percentage=attendance_percentage,
                         today=today)


@student.route('/report')
@login_required
@student_required
def report():
    """Student attendance report - monthly/yearly view"""
    # Get student record linked to current user
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    if not student:
        flash('Student profile not found. Please contact administrator.', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Get date range from query parameters
    today = date.today()
    year = int(request.args.get('year', today.year))
    month = int(request.args.get('month', today.month))
    
    # Get all dates in the selected month
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    
    # Get attendance records
    attendance_records = Attendance.query.filter(
        Attendance.student_id == student.id,
        Attendance.date >= first_day,
        Attendance.date <= last_day
    ).order_by(Attendance.date).all()
    
    # Create attendance data
    attendance_data = []
    total_days = 0
    present_days = 0
    
    current_date = first_day
    while current_date <= last_day and current_date <= today:
        total_days += 1
        record = next((r for r in attendance_records if r.date == current_date), None)
        
        if record:
            if record.status:
                present_days += 1
            attendance_data.append({
                'date': current_date,
                'status': 'Present' if record.status else 'Absent',
                'marked_by': record.marker.display_name,
                'last_modified': record.last_modified
            })
        else:
            attendance_data.append({
                'date': current_date,
                'status': 'Not Marked',
                'marked_by': None,
                'last_modified': None
            })
        
        from datetime import timedelta
        current_date += timedelta(days=1)
    
    # Calculate attendance percentage
    if total_days > 0:
        attendance_percentage = round((present_days / total_days) * 100, 2)
    else:
        attendance_percentage = 0
    
    # Get teacher information
    teacher = User.query.get(student.teacher_id)
    
    return render_template('student/report.html',
                         title='My Attendance Report',
                         student=student,
                         teacher=teacher,
                         attendance_data=attendance_data,
                         total_days=total_days,
                         present_days=present_days,
                         absent_days=total_days - present_days,
                         attendance_percentage=attendance_percentage,
                         selected_year=year,
                         selected_month=month,
                         month_name=datetime(year, month, 1).strftime('%B'))


@student.route('/change-password', methods=['GET', 'POST'])
@login_required
@student_required
def change_password():
    """Student password change page"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        # Verify current password
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect', 'danger')
            return render_template('student/change_password.html', title='Change Password', form=form)
        
        # Check if new password is same as current
        if current_user.check_password(form.new_password.data):
            flash('New password must be different from current password', 'warning')
            return render_template('student/change_password.html', title='Change Password', form=form)
        
        # Update password
        current_user.set_password(form.new_password.data)
        db.session.commit()
        
        flash('Password changed successfully!', 'success')
        return redirect(url_for('student.profile'))
    
    return render_template('student/change_password.html', title='Change Password', form=form)

