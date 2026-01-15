from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Student, User
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, ValidationError, Optional
from app.utils.auto_sync import auto_sync_to_sheets
from app.utils.face_recognition import FaceRecognition
from app.utils.decorators import teacher_required, principal_or_owner_required
from app.utils.student_utils import create_student_user_account
from werkzeug.utils import secure_filename
import os
import json

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
    face_image = FileField('Face Image (for face recognition)', 
                           validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png'], 'Only image files (jpg, jpeg, png) are allowed!')])
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
@teacher_required
def add():

    form = StudentForm()
    if form.validate_on_submit():
        student = Student(
            name=form.name.data,
            roll_number=form.roll_number.data,
            grade=form.grade.data,
            teacher_id=current_user.id
        )
        
        # Handle face image upload
        if form.face_image.data:
            try:
                # Save uploaded file
                file = form.face_image.data
                filename = secure_filename(file.filename)
                
                # Create student_faces directory if it doesn't exist
                faces_dir = os.path.join(current_app.root_path, 'static', 'student_faces')
                if not os.path.exists(faces_dir):
                    os.makedirs(faces_dir)
                
                # Generate unique filename: roll_number_timestamp.ext
                import time
                name, ext = os.path.splitext(filename)
                unique_filename = f"{form.roll_number.data}_{int(time.time())}{ext}"
                file_path = os.path.join(faces_dir, unique_filename)
                
                # Save file
                file.save(file_path)
                
                # Generate face embedding
                try:
                    face_rec = FaceRecognition()
                    embedding, face_image, bbox = face_rec.detect_and_extract_face(file_path)
                    
                    if embedding is not None:
                        # Store embedding and relative image path
                        relative_path = os.path.join('student_faces', unique_filename)
                        embedding_json = json.dumps(face_rec.embedding_to_json(embedding))
                        student.face_embedding = embedding_json
                        student.face_image_path = relative_path
                        current_app.logger.info(f"Face embedding saved for student {student.name}: {len(embedding_json)} chars")
                        flash('Face image uploaded and embedding generated successfully!', 'success')
                    else:
                        # Keep the file but don't store embedding
                        relative_path = os.path.join('student_faces', unique_filename)
                        student.face_image_path = relative_path
                        student.face_embedding = None  # Explicitly set to None
                        flash('Face image uploaded but no face detected. Please ensure the image contains a clear, front-facing face. Image saved for review.', 'warning')
                        current_app.logger.warning(f"Face detection failed for image: {file_path}")
                except Exception as face_error:
                    # Keep the file even if there's an error
                    relative_path = os.path.join('student_faces', unique_filename)
                    student.face_image_path = relative_path
                    error_msg = str(face_error)
                    current_app.logger.error(f"Face recognition error: {error_msg}", exc_info=True)
                    
                    # Provide more helpful error messages
                    if "insightface" in error_msg.lower() or "import" in error_msg.lower():
                        flash('Face recognition failed: InsightFace model not available. Please install: pip install insightface onnxruntime', 'danger')
                    elif "no face detected" in error_msg.lower():
                        flash('No face detected in image. Please upload a clear, front-facing face photo with good lighting.', 'warning')
                    else:
                        flash(f'Face recognition error: {error_msg}. Image saved. Please check logs for details.', 'warning')
                    
            except Exception as e:
                current_app.logger.error(f"Error processing face image: {str(e)}")
                flash('Error processing face image. Student added but face recognition not available.', 'warning')
        
        db.session.add(student)
        db.session.flush()  # Flush to get student.id
        
        # Create User account for student with auto-generated credentials
        user_account = create_student_user_account(student, common_password='student123')
        if user_account:
            db.session.add(user_account)
            db.session.flush()  # Flush to get user_account.id
            
            # Link Student to User account
            student.user_id = user_account.id
            db.session.commit()
            
            flash(f'Student "{student.name}" added successfully! Username: {user_account.username}, Email: {user_account.email}.', 'success')
        else:
            db.session.commit()
            flash('Student added successfully but failed to create login account.', 'warning')
        
        # Auto-sync to Google Sheets
        sync_result = auto_sync_to_sheets()
        if sync_result:
            flash('Google Sheet updated!', 'success')
        else:
            flash('Google Sheet update failed. Principal will need to refresh.', 'warning')

        return redirect(url_for('students.list'))
    return render_template('students/add.html', title='Add Student', form=form)

@students.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@principal_or_owner_required(lambda user, *args, **kwargs: 
    (lambda s: s.teacher_id == user.id if s else False)(
        Student.query.get(kwargs.get('id', args[0] if args else None))
    ))
def edit(id):
    student = Student.query.get_or_404(id)

    form = StudentForm()
    form.student_id = student.id  # Pass student ID to the form for validation

    if form.validate_on_submit():
        student.name = form.name.data
        student.roll_number = form.roll_number.data
        student.grade = form.grade.data
        
        # Handle face image upload (optional - only if new image provided)
        if form.face_image.data:
            try:
                # Delete old face image if exists
                if student.face_image_path:
                    old_path = os.path.join(current_app.root_path, 'static', student.face_image_path)
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except:
                            pass  # Ignore if file doesn't exist
                
                # Save uploaded file
                file = form.face_image.data
                filename = secure_filename(file.filename)
                
                # Create student_faces directory if it doesn't exist
                faces_dir = os.path.join(current_app.root_path, 'static', 'student_faces')
                if not os.path.exists(faces_dir):
                    os.makedirs(faces_dir)
                
                # Generate unique filename: roll_number_timestamp.ext
                import time
                name, ext = os.path.splitext(filename)
                unique_filename = f"{form.roll_number.data}_{int(time.time())}{ext}"
                file_path = os.path.join(faces_dir, unique_filename)
                
                # Save file
                file.save(file_path)
                
                # Generate face embedding
                try:
                    face_rec = FaceRecognition()
                    embedding, face_image, bbox = face_rec.detect_and_extract_face(file_path)
                    
                    if embedding is not None:
                        # Store embedding and relative image path
                        relative_path = os.path.join('student_faces', unique_filename)
                        student.face_embedding = json.dumps(face_rec.embedding_to_json(embedding))
                        student.face_image_path = relative_path
                        flash('Face image updated and embedding regenerated successfully!', 'success')
                    else:
                        # Keep the new file but don't update embedding
                        relative_path = os.path.join('student_faces', unique_filename)
                        student.face_image_path = relative_path
                        flash('Face image uploaded but no face detected. Please ensure the image contains a clear, front-facing face. Image saved for review.', 'warning')
                        current_app.logger.warning(f"Face detection failed for image: {file_path}")
                except Exception as face_error:
                    # Keep the file even if there's an error
                    relative_path = os.path.join('student_faces', unique_filename)
                    student.face_image_path = relative_path
                    error_msg = str(face_error)
                    current_app.logger.error(f"Face recognition error: {error_msg}", exc_info=True)
                    flash(f'Face image uploaded but face recognition failed: {error_msg}. Image saved for review.', 'warning')
                    
            except Exception as e:
                current_app.logger.error(f"Error processing face image: {str(e)}")
                flash('Error processing face image. Student updated but face recognition not updated.', 'warning')
        
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
@principal_or_owner_required(lambda user, *args, **kwargs: 
    (lambda s: s.teacher_id == user.id if s else False)(
        Student.query.get(kwargs.get('id', args[0] if args else None))
    ))
def delete(id):
    student = Student.query.get_or_404(id)

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
