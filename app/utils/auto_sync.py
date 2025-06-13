from flask import current_app, request
from app.utils.google_sheets import sync_teacher_attendance_data
from flask_login import current_user
import logging

def auto_sync_to_sheets():
    """
    Automatically sync data to Google Sheets for the current teacher only
    """
    try:
        # Get the current teacher ID
        teacher_id = None
        
        # If the current user is a teacher, use their ID
        if hasattr(current_user, 'is_teacher') and current_user.is_teacher():
            teacher_id = current_user.id
            current_app.logger.info(f"Using teacher ID from current user: {teacher_id}")
        # If we're marking attendance for a specific student, use their teacher's ID
        elif hasattr(current_user, 'marked_student_id') and current_user.marked_student_id:
            from app.models import Student
            student = Student.query.get(current_user.marked_student_id)
            if student:
                teacher_id = student.teacher_id
                current_app.logger.info(f"Using teacher ID from marked student: {teacher_id}")
        # If we're editing a specific attendance record, get the teacher from the student
        elif request.endpoint == 'attendance.edit' and request.view_args:
            try:
                from app.models import Attendance, Student
                attendance_id = request.view_args.get('id')
                if attendance_id:
                    attendance = Attendance.query.get(attendance_id)
                    if attendance:
                        student = Student.query.get(attendance.student_id)
                        if student:
                            teacher_id = student.teacher_id
                            current_app.logger.info(f"Using teacher ID from edited attendance: {teacher_id}")
            except Exception as e:
                current_app.logger.error(f"Error identifying teacher from attendance edit: {str(e)}")
                
        # If we have a teacher ID, sync their data
        if teacher_id:
            current_app.logger.info(f"Auto-sync to teacher-specific Google Sheet started for teacher ID: {teacher_id}")
            result = sync_teacher_attendance_data(teacher_id)
            if result:
                current_app.logger.info("Auto-sync to teacher-specific Google Sheet completed successfully")
            else:
                current_app.logger.error("Auto-sync to teacher-specific Google Sheet failed")
            return result
        else:
            current_app.logger.warning("No teacher ID found for auto-sync")
            return False
    except Exception as e:
        current_app.logger.error(f"Error in auto-sync: {str(e)}")
        current_app.logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
        # Log the current route to help with debugging
        current_route = request.endpoint if request else "Unknown"
        current_app.logger.error(f"Current route: {current_route}")
        return False
