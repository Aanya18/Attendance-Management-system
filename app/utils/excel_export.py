import os
import pandas as pd
from datetime import datetime
from flask import current_app
from app.models import Student, Attendance, User

def export_attendance_to_excel(file_path='Student_Attendance.xlsx'):
    """
    Export attendance data to Excel file.
    
    Args:
        file_path (str): Path to save the Excel file
    
    Returns:
        bool: True if export was successful, False otherwise
    """
    try:
        # Get all students and attendance records
        students = Student.query.all()
        attendance_records = Attendance.query.all()
        
        # Create a dictionary to store attendance by date and student
        attendance_by_date = {}
        
        # Get all unique dates
        dates = sorted(list(set([record.date for record in attendance_records])))
        
        # Initialize the attendance dictionary
        for date in dates:
            attendance_by_date[date] = {}
            for student in students:
                attendance_by_date[date][student.id] = 'A'  # Default to Absent
        
        # Fill in the attendance data
        for record in attendance_records:
            if record.status:  # If present
                attendance_by_date[record.date][record.student_id] = 'P'
        
        # Create a DataFrame for the attendance sheet
        attendance_data = []
        
        # Add header row with dates
        header = ['Roll No', 'Student Name', 'Class']
        date_columns = [date.strftime('%d-%m-%Y') for date in dates]
        header.extend(date_columns)
        
        # Add data rows
        for student in students:
            row = [student.roll_number, student.name, student.grade]
            for date in dates:
                row.append(attendance_by_date[date].get(student.id, 'A'))
            attendance_data.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(attendance_data, columns=header)
        
        # Create a summary sheet
        summary_data = []
        for date in dates:
            present_count = sum(1 for student_id, status in attendance_by_date[date].items() if status == 'P')
            absent_count = len(students) - present_count
            attendance_percentage = (present_count / len(students) * 100) if len(students) > 0 else 0
            
            summary_data.append([
                date.strftime('%d-%m-%Y'),
                present_count,
                absent_count,
                len(students),
                f"{attendance_percentage:.2f}%"
            ])
        
        summary_df = pd.DataFrame(
            summary_data, 
            columns=['Date', 'Present', 'Absent', 'Total Students', 'Attendance %']
        )
        
        # Create student summary
        student_summary_data = []
        for student in students:
            present_count = sum(1 for date in dates if attendance_by_date[date].get(student.id) == 'P')
            absent_count = len(dates) - present_count
            attendance_percentage = (present_count / len(dates) * 100) if len(dates) > 0 else 0
            
            student_summary_data.append([
                student.roll_number,
                student.name,
                student.grade,
                present_count,
                absent_count,
                len(dates),
                f"{attendance_percentage:.2f}%"
            ])
        
        student_summary_df = pd.DataFrame(
            student_summary_data,
            columns=['Roll No', 'Student Name', 'Class', 'Present Days', 'Absent Days', 'Total Days', 'Attendance %']
        )
        
        # Create Excel writer
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Attendance', index=False)
            summary_df.to_excel(writer, sheet_name='Daily Summary', index=False)
            student_summary_df.to_excel(writer, sheet_name='Student Summary', index=False)
        
        current_app.logger.info(f"Successfully exported attendance data to Excel: {file_path}")
        return True
    
    except Exception as e:
        current_app.logger.error(f"Error exporting attendance data to Excel: {str(e)}")
        current_app.logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
        return False
