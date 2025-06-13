from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db
from app.models import ImageUpload, Attendance, User, Student
from app.utils.google_drive import upload_file_to_drive, get_or_create_folder
from app.utils.yolo_detector import YOLODetector
import os
from werkzeug.utils import secure_filename
import numpy as np

images = Blueprint('images', __name__, url_prefix='/images')

# Initialize YOLO detector
yolo_detector = YOLODetector()

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
def upload():
    """Handle image upload and YOLO detection"""
    # Only teachers can upload images
    if not current_user.is_teacher():
        flash('Only teachers can upload images', 'danger')
        return redirect(url_for('images.list'))
        
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
                # Run YOLO detection
                annotated_path, person_count, confidence_scores = yolo_detector.detect_people(file_path)
                avg_confidence = float(np.mean(confidence_scores)) if confidence_scores else 0.0

                # Get only the current teacher's students with present status for today
                # Get all students for the current teacher
                teacher_students = Student.query.filter_by(teacher_id=current_user.id).all()
                student_ids = [student.id for student in teacher_students]
                
                # Count how many of this teacher's students are marked present today
                present_count = Attendance.query.filter(
                    Attendance.student_id.in_(student_ids),
                    Attendance.date == today,
                    Attendance.status == True
                ).count()

                # Compare counts
                has_discrepancy, discrepancy_message = yolo_detector.compare_with_attendance(
                    person_count, 
                    present_count
                )

                # Get or create the folder and upload both original and annotated images to Google Drive
                folder_id = get_or_create_folder("Student_Attendance_Images")
                
                # Upload original image
                drive_file = upload_file_to_drive(file_path, filename, folder_id)
                
                # Upload annotated image if available
                annotated_drive_file = None
                if annotated_path:
                    annotated_filename = os.path.basename(annotated_path)
                    annotated_drive_file = upload_file_to_drive(annotated_path, annotated_filename, folder_id)

                # Create a new image upload record
                image_upload = ImageUpload(
                    date=today,
                    file_name=filename,
                    file_path=file_path,
                    uploaded_by=current_user.id,
                    description=description,
                    yolo_count=person_count,
                    yolo_confidence=avg_confidence,
                    annotated_file_path=annotated_path,
                    has_discrepancy=has_discrepancy,
                    discrepancy_message=discrepancy_message
                )

                # Save Drive file IDs and view links
                if drive_file:
                    image_upload.drive_file_id = drive_file.get('id')
                    image_upload.drive_view_link = drive_file.get('webViewLink')
                
                if annotated_drive_file:
                    image_upload.annotated_drive_file_id = annotated_drive_file.get('id')
                    image_upload.annotated_drive_view_link = annotated_drive_file.get('webViewLink')

                db.session.add(image_upload)
                db.session.commit()

                # Flash appropriate message
                if has_discrepancy:
                    flash(f'Image uploaded successfully. {discrepancy_message}', 'warning')
                else:
                    flash('Image uploaded successfully! YOLO count matches attendance records.', 'success')
                
                return redirect(url_for('images.list'))

            except Exception as e:
                current_app.logger.error(f"Error in YOLO processing: {str(e)}")
                flash(f'Error processing image with YOLO: {str(e)}', 'danger')
                return redirect(request.url)
        else:
            flash('Invalid file type. Allowed types: png, jpg, jpeg, gif', 'danger')

    return render_template('images/upload.html', title='Upload Image')

@images.route('/view/<int:id>')
@login_required
def view(id):
    """
    View a specific image
    """
    # Get current date for template
    now = datetime.now()

    image = ImageUpload.query.get_or_404(id)
    
    # Access control for viewing images
    if current_user.is_principal():
        # Principals can view all images
        pass
    elif current_user.id != image.uploaded_by:
        # Teachers can only view their own uploads
        flash('You can only view your own uploads', 'danger')
        return redirect(url_for('images.list'))

    return render_template('images/view.html', title='View Image', image=image, now=now)

@images.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """
    Delete an image - only principals can delete images
    """
    image = ImageUpload.query.get_or_404(id)

    # Only principals can delete images
    if not current_user.is_principal():
        flash('Only principals are authorized to delete images', 'danger')
        return redirect(url_for('images.list'))

    # Delete the file from the local filesystem
    if os.path.exists(image.file_path):
        os.remove(image.file_path)
    
    # Delete the annotated file if it exists
    if image.annotated_file_path and os.path.exists(image.annotated_file_path):
        os.remove(image.annotated_file_path)
    
    # Delete the database record
    db.session.delete(image)
    db.session.commit()
    
    flash('Image deleted successfully', 'success')
    return redirect(url_for('images.list'))
