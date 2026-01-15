from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db
from app.models import ImageUpload, Attendance, User, Student
from app.utils.timezone_utils import get_local_datetime
from app.utils.google_drive import upload_file_to_drive, get_or_create_folder
from app.utils.face_recognition import FaceRecognition
from app.utils.decorators import teacher_required, principal_required, principal_or_owner_required
import os
from werkzeug.utils import secure_filename
import numpy as np
import json

images = Blueprint('images', __name__, url_prefix='/images')

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@images.route('/')
@login_required
def list():
    """
    List all images
    """
    # Get current date for template
    now = datetime.now()

    # If user is a teacher, show only their uploads
    if current_user.is_teacher():
        images = ImageUpload.query.filter_by(
            uploaded_by=current_user.id
        ).order_by(ImageUpload.uploaded_at.desc()).all()
        
        return render_template('images/list.html', title='Images', images=images, now=now, is_principal=False)
    
    # If user is a principal, show all images grouped by teacher
    else:
        # If user is a principal, group images by teacher
        teachers = User.query.filter_by(role='teacher').all()
        teachers_with_images = []
        
        for teacher in teachers:
            teacher_images = ImageUpload.query.filter_by(
                uploaded_by=teacher.id
            ).order_by(ImageUpload.uploaded_at.desc()).all()
            
            if teacher_images:  # Only include teachers who have uploaded images
                teachers_with_images.append({
                    'teacher': teacher,
                    'images': teacher_images
                })
        
        return render_template('images/list.html', title='Images', 
                              teachers_with_images=teachers_with_images, 
                              now=now, 
                              is_principal=True)

@images.route('/upload', methods=['GET', 'POST'])
@login_required
@teacher_required
def upload():
    """Handle image upload and face recognition"""
        
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(request.url)

        file = request.files['file']
        description = request.form.get('description', '')
        today = date.today()

        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            # Secure the filename
            filename = secure_filename(file.filename)

            # Create uploads directory if it doesn't exist
            uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)

            # Save the file locally
            file_path = os.path.join(uploads_dir, filename)
            file.save(file_path)

            try:
                # Get all students for the current teacher
                teacher_students = Student.query.filter_by(teacher_id=current_user.id).all()
                student_ids = [student.id for student in teacher_students]
                
                # FACE RECOGNITION: Detect faces and mark attendance automatically
                face_recognition_results = {
                    'faces_detected': 0,
                    'students_matched': 0,
                    'attendance_marked': 0,
                    'absent_marked': 0,
                    'matches': []
                }
                face_annotated_path = None
                face_annotated_drive_file = None  # Initialize early to avoid undefined error
                
                try:
                    # Initialize face recognition
                    try:
                        face_rec = FaceRecognition()
                    except Exception as init_error:
                        error_type = type(init_error).__name__
                        error_msg = str(init_error) if str(init_error) else repr(init_error)
                        current_app.logger.error(f"Failed to initialize FaceRecognition: {error_type}: {error_msg}", exc_info=True)
                        raise Exception(f"Face recognition initialization failed: {error_msg or error_type}. Please ensure InsightFace is installed: pip install insightface onnxruntime")
                    
                    # Detect all faces in the uploaded image
                    try:
                        detected_faces = face_rec.detect_all_faces(file_path)
                    except ImportError as import_error:
                        error_msg = str(import_error)
                        current_app.logger.error(f"Face recognition library import error: {error_msg}", exc_info=True)
                        # Don't fail the upload, just skip face recognition
                        detected_faces = []
                        face_recognition_results['error'] = f"Face recognition library not available: {error_msg}"
                    except RuntimeError as runtime_error:
                        error_msg = str(runtime_error)
                        current_app.logger.error(f"Face recognition model loading error: {error_msg}", exc_info=True)
                        # Don't fail the upload, just skip face recognition
                        detected_faces = []
                        face_recognition_results['error'] = f"Face recognition model failed to load: {error_msg}"
                    except Exception as detect_error:
                        error_type = type(detect_error).__name__
                        error_msg = str(detect_error) if str(detect_error) else repr(detect_error)
                        current_app.logger.error(f"Failed to detect faces: {error_type}: {error_msg}", exc_info=True)
                        # Don't fail the upload, just skip face recognition
                        detected_faces = []
                        face_recognition_results['error'] = f"Face detection failed: {error_msg or error_type}"
                    face_recognition_results['faces_detected'] = len(detected_faces)
                    
                    if len(detected_faces) > 0:
                        # Get students with face embeddings
                        students_with_faces = [s for s in teacher_students if s.face_embedding]
                        
                        if students_with_faces:
                            # Match each detected face with student profiles
                            matched_students = set()  # To avoid duplicate matches
                            
                            for embedding, face_image, bbox, face_idx in detected_faces:
                                best_match = None
                                best_similarity = 0.0
                                best_student = None
                                
                                # Compare with all students
                                for student in students_with_faces:
                                    student_embedding = face_rec.json_to_embedding(student.face_embedding)
                                    is_match, similarity = face_rec.compare_faces(
                                        embedding, 
                                        student_embedding, 
                                        threshold=0.0  # Get all similarities, filter later
                                    )
                                    
                                    if similarity > best_similarity:
                                        best_similarity = similarity
                                        best_student = student
                                        best_match = {
                                            'face_index': face_idx,
                                            'student_id': student.id,
                                            'student_name': student.name,
                                            'roll_number': student.roll_number,
                                            'similarity': similarity,
                                            'bbox': bbox
                                        }
                                
                                # If similarity is above threshold, mark as match
                                if best_match and best_similarity >= 0.6:  # Threshold for matching
                                    matched_students.add(best_student.id)
                                    face_recognition_results['matches'].append(best_match)
                                    face_recognition_results['students_matched'] += 1
                            
                            # Mark attendance for matched students (PRESENT)
                            for student_id in matched_students:
                                # Check if attendance already exists for today
                                existing_attendance = Attendance.query.filter_by(
                                    student_id=student_id,
                                    date=today
                                ).first()
                                
                                if existing_attendance:
                                    # Update to present if not already present
                                    if not existing_attendance.status:
                                        existing_attendance.status = True
                                        existing_attendance.last_modified = get_local_datetime()
                                        face_recognition_results['attendance_marked'] += 1
                                else:
                                    # Create new attendance record as PRESENT
                                    new_attendance = Attendance(
                                        student_id=student_id,
                                        date=today,
                                        status=True,  # Present
                                        marked_by=current_user.id,
                                        last_modified=get_local_datetime()
                                    )
                                    db.session.add(new_attendance)
                                    face_recognition_results['attendance_marked'] += 1
                            
                            # Mark attendance for students NOT in photo (ABSENT)
                            # Get all students with face embeddings for this teacher
                            all_student_ids = [s.id for s in students_with_faces]
                            unmatched_student_ids = [sid for sid in all_student_ids if sid not in matched_students]
                            
                            absent_marked = 0
                            for student_id in unmatched_student_ids:
                                # Check if attendance already exists for today
                                existing_attendance = Attendance.query.filter_by(
                                    student_id=student_id,
                                    date=today
                                ).first()
                                
                                if existing_attendance:
                                    # Update to absent if currently marked as present
                                    if existing_attendance.status:
                                        existing_attendance.status = False  # Absent
                                        existing_attendance.last_modified = get_local_datetime()
                                        absent_marked += 1
                                else:
                                    # Create new attendance record as ABSENT
                                    new_attendance = Attendance(
                                        student_id=student_id,
                                        date=today,
                                        status=False,  # Absent
                                        marked_by=current_user.id,
                                        last_modified=get_local_datetime()
                                    )
                                    db.session.add(new_attendance)
                                    absent_marked += 1
                            
                            face_recognition_results['attendance_marked'] += absent_marked
                            face_recognition_results['absent_marked'] = absent_marked
                            
                            # Create annotated image with face recognition results
                            if face_recognition_results['matches']:
                                matches_for_annotation = [
                                    {
                                        'index': m['face_index'],
                                        'similarity': m['similarity'],
                                        'bbox': m['bbox'],
                                        'is_match': True,
                                        'student_name': m['student_name']
                                    }
                                    for m in face_recognition_results['matches']
                                ]
                                face_annotated_path = face_rec.annotate_group_photo(
                                    file_path,
                                    matches_for_annotation,
                                    output_path=None  # Auto-generate path
                                )
                        
                        else:
                            current_app.logger.info("No students with face embeddings found for face recognition")
                            flash('No students with face images found. Please upload face images for students first in their profiles.', 'info')
                    else:
                        current_app.logger.info("No faces detected in uploaded image for face recognition")
                        
                except Exception as face_error:
                    current_app.logger.error(f"Face recognition error: {str(face_error)}", exc_info=True)
                
                # Get or create the folder and upload both original and annotated images to Google Drive
                folder_id = get_or_create_folder("Student_Attendance_Images")
                
                # Upload original image
                drive_file = upload_file_to_drive(file_path, filename, folder_id)
                
                # Upload face recognition annotated image if available
                if face_annotated_path:
                    face_annotated_filename = os.path.basename(face_annotated_path)
                    face_annotated_drive_file = upload_file_to_drive(face_annotated_path, face_annotated_filename, folder_id)

                # Create a new image upload record
                image_upload = ImageUpload(
                    date=today,
                    file_name=filename,
                    file_path=file_path,
                    uploaded_by=current_user.id,
                    description=description,
                    # Face recognition fields
                    face_recognition_enabled=True,
                    faces_detected=face_recognition_results['faces_detected'],
                    students_matched=face_recognition_results['students_matched'],
                    attendance_marked_count=face_recognition_results['attendance_marked'],
                    face_matches_json=json.dumps(face_recognition_results['matches']),
                    face_annotated_path=face_annotated_path
                )

                # Save Drive file IDs and view links
                if drive_file:
                    image_upload.drive_file_id = drive_file.get('id')
                    image_upload.drive_view_link = drive_file.get('webViewLink')
                
                # Note: face_annotated_drive_file is uploaded but not stored in separate fields
                # The face_annotated_path is stored in the database for reference

                db.session.add(image_upload)
                db.session.commit()
                
                # Auto-sync to Google Sheets after marking attendance
                if face_recognition_results['attendance_marked'] > 0:
                    from app.utils.auto_sync import auto_sync_to_sheets
                    auto_sync_to_sheets()

                # Flash appropriate message with face recognition results
                messages = []
                messages.append('Image uploaded successfully!')
                
                # Check for face recognition errors first
                if 'error' in face_recognition_results:
                    messages.append(f"Face Recognition Error: {face_recognition_results['error']}")
                    flash(' '.join(messages), 'warning')
                elif face_recognition_results['faces_detected'] > 0:
                    present_count = face_recognition_results['attendance_marked'] - face_recognition_results.get('absent_marked', 0)
                    absent_count = face_recognition_results.get('absent_marked', 0)
                    
                    face_msg = f"Face Recognition: {face_recognition_results['faces_detected']} face(s) detected"
                    
                    if face_recognition_results['students_matched'] > 0:
                        face_msg += f", {face_recognition_results['students_matched']} student(s) matched. "
                        if present_count > 0 or absent_count > 0:
                            face_msg += f"Attendance: {present_count} marked Present, {absent_count} marked Absent."
                    else:
                        face_msg += ". No students matched - please ensure students have face images uploaded in their profiles."
                    
                    messages.append(face_msg)
                    
                    if face_recognition_results['attendance_marked'] > 0:
                        flash(' '.join(messages), 'success')
                    else:
                        flash(' '.join(messages), 'info')
                elif face_recognition_results['faces_detected'] == 0:
                    messages.append("No faces detected in image. Please upload a clear group photo.")
                    flash(' '.join(messages), 'info')
                else:
                    flash(' '.join(messages), 'info')
                
                return redirect(url_for('images.list'))

            except Exception as e:
                current_app.logger.error(f"Error processing image: {str(e)}")
                flash(f'Error processing image: {str(e)}', 'danger')
                return redirect(request.url)
        else:
            flash('Invalid file type. Allowed types: png, jpg, jpeg, gif', 'danger')

    return render_template('images/upload.html', title='Upload Image')

@images.route('/view/<int:id>')
@login_required
@principal_or_owner_required(lambda user, *args, **kwargs: 
    (lambda img: img.uploaded_by == user.id if img else False)(
        ImageUpload.query.get(kwargs.get('id', args[0] if args else None))
    ))
def view(id):
    """
    View a specific image
    """
    # Get current date for template
    now = datetime.now()

    image = ImageUpload.query.get_or_404(id)

    return render_template('images/view.html', title='View Image', image=image, now=now)

@images.route('/delete/<int:id>', methods=['POST'])
@login_required
@principal_required
def delete(id):
    """
    Delete an image - only principals can delete images
    """
    image = ImageUpload.query.get_or_404(id)

    # Delete the file from the local filesystem
    if os.path.exists(image.file_path):
        os.remove(image.file_path)
    
    # Delete the annotated file if it exists
    if image.face_annotated_path and os.path.exists(image.face_annotated_path):
        os.remove(image.face_annotated_path)
    
    # Delete the database record
    db.session.delete(image)
    db.session.commit()
    
    flash('Image deleted successfully', 'success')
    return redirect(url_for('images.list'))
