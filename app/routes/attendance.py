from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.models import Student, Attendance
from app.utils.decorators import teacher_required, principal_or_owner_required
from app.utils.timezone_utils import get_local_datetime, get_local_date
from app.utils.auto_sync import auto_sync_to_sheets
from app.utils.google_sheets import sync_teacher_attendance_data

attendance = Blueprint('attendance', __name__, url_prefix='/attendance')

# Helper function to get current local date (alias for consistency)
def get_today():
    return get_local_date()

@attendance.route('/mark', methods=['GET', 'POST'])
@login_required
@teacher_required
def mark():
    today = get_today()
    students = Student.query.filter_by(teacher_id=current_user.id).all()

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
@principal_or_owner_required(lambda user, *args, **kwargs: 
    (lambda a: a.marked_by == user.id if a else False)(
        Attendance.query.get(kwargs.get('id', args[0] if args else None))
    ))
def edit(id):
    # Get the attendance record
    attendance_record = Attendance.query.get_or_404(id)
    
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
                sync_result = sync_teacher_attendance_data(student.teacher_id)
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
