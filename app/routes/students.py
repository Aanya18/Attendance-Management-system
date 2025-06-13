from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Student, User
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, ValidationError
from app.utils.auto_sync import auto_sync_to_sheets

students = Blueprint('students', __name__, url_prefix='/students')

class StudentForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    roll_number = StringField('Roll Number', validators=[DataRequired()])
    grade = SelectField('Grade', choices=[
        ('NC', 'Nursery Class (NC)'),
        ('KG', 'Kindergarten (KG)'),
        ('1', '1st Grade'),
        ('2', '2nd Grade'),
        ('3', '3rd Grade'),
        ('4', '4th Grade'),
        ('5', '5th Grade'),
        ('6', '6th Grade'),
        ('7', '7th Grade'),
        ('8', '8th Grade'),
        ('9', '9th Grade'),
        ('10', '10th Grade'),
        ('11', '11th Grade'),
        ('12', '12th Grade')
    ], validators=[DataRequired()])
    submit = SubmitField('Submit')

    def validate_roll_number(self, roll_number):
        # Check if the roll number exists for the same teacher
        student = Student.query.filter_by(roll_number=roll_number.data, teacher_id=current_user.id).first()
        if student is not None and student.id != getattr(self, 'student_id', None):
            raise ValidationError('You already have a student with this roll number.')

@students.route('/')
@login_required
def list():
    if current_user.is_principal():
        # Get all teachers and their students
        teachers = User.query.filter_by(role='teacher').all()
        teachers_with_students = []
        
        for teacher in teachers:
            teacher_students = Student.query.filter_by(teacher_id=teacher.id).all()
            if teacher_students:  # Only include teachers who have students
                teachers_with_students.append({
                    'teacher': teacher,
                    'students': teacher_students
                })
                
        return render_template('students/list.html', title='Students', teachers_with_students=teachers_with_students, is_principal=True)
    else:
        students_list = Student.query.filter_by(teacher_id=current_user.id).all()
        return render_template('students/list.html', title='Students', students=students_list, is_principal=False)

@students.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    # Only teachers can add students
    if not current_user.is_teacher():
        flash('Only teachers can add students', 'danger')
        return redirect(url_for('students.list'))

    form = StudentForm()
    if form.validate_on_submit():
        student = Student(
            name=form.name.data,
            roll_number=form.roll_number.data,
            grade=form.grade.data,
            teacher_id=current_user.id
        )
        db.session.add(student)
        db.session.commit()

        # Auto-sync to Google Sheets
        sync_result = auto_sync_to_sheets()
        if sync_result:
            flash('Student added successfully and Google Sheet updated!', 'success')
        else:
            flash('Student added successfully but Google Sheet update failed. Principal will need to refresh.', 'warning')

        return redirect(url_for('students.list'))
    return render_template('students/add.html', title='Add Student', form=form)

@students.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    student = Student.query.get_or_404(id)

    # Access control logic
    if current_user.is_principal():
        # Principals can edit any student
        pass
    elif student.teacher_id != current_user.id:
        # Teachers can only edit their own students
        flash('You can only edit your own students', 'danger')
        return redirect(url_for('students.list'))

    form = StudentForm()
    form.student_id = student.id  # Pass student ID to the form for validation

    if form.validate_on_submit():
        student.name = form.name.data
        student.roll_number = form.roll_number.data
        student.grade = form.grade.data
        db.session.commit()

        # Auto-sync to Google Sheets
        sync_result = auto_sync_to_sheets()
        if sync_result:
            flash('Student updated successfully and Google Sheet updated!', 'success')
        else:
            flash('Student updated successfully but Google Sheet update failed. Principal will need to refresh.', 'warning')

        return redirect(url_for('students.list'))

    elif request.method == 'GET':
        form.name.data = student.name
        form.roll_number.data = student.roll_number
        form.grade.data = student.grade

    return render_template('students/edit.html', title='Edit Student', form=form, student=student)

@students.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    student = Student.query.get_or_404(id)

    # Access control logic
    if current_user.is_principal():
        # Principals can delete any student
        pass
    elif student.teacher_id != current_user.id:
        # Teachers can only delete their own students
        flash('You can only delete your own students', 'danger')
        return redirect(url_for('students.list'))

    try:
        # First delete all attendance records for this student
        from app.models import Attendance

        # Use a direct SQL query to delete attendance records
        # This avoids the SQLAlchemy ORM which might be causing the issue
        db.session.execute(f"DELETE FROM attendance WHERE student_id = {student.id}")
        db.session.commit()

        # Then delete the student
        db.session.delete(student)
        db.session.commit()

        # Auto-sync to Google Sheets
        sync_result = auto_sync_to_sheets()
        if sync_result:
            flash('Student deleted successfully and Google Sheet updated!', 'success')
        else:
            flash('Student deleted successfully but Google Sheet update failed. Principal will need to refresh.', 'warning')

        return redirect(url_for('students.list'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting student: {str(e)}', 'danger')
        return redirect(url_for('students.list'))
