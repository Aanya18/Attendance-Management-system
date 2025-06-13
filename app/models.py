from datetime import datetime
import pytz
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

# Helper function to get current local date and time
def get_local_datetime():
    # Set to your local timezone, e.g., 'Asia/Kolkata' for India
    local_tz = pytz.timezone('Asia/Kolkata')
    utc_now = datetime.utcnow().replace(tzinfo=pytz.UTC)
    local_now = utc_now.astimezone(local_tz)
    return local_now

def get_local_date():
    return get_local_datetime().date()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False, default='teacher')  # 'teacher' or 'principal'
    students = db.relationship('Student', backref='teacher', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_principal(self):
        return self.role == 'principal'

    def is_teacher(self):
        return self.role == 'teacher'

    def __repr__(self):
        return f'<User {self.username}>'

    @property
    def display_name(self):
        """Return a display name for the user"""
        return self.username

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(20), nullable=False)
    grade = db.Column(db.String(10), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    attendance_records = db.relationship('Attendance', backref='student', lazy=True)
    
    __table_args__ = (
        db.UniqueConstraint('roll_number', 'teacher_id', name='unique_roll_teacher'),
    )

    def __repr__(self):
        return f'<Student {self.name}>'

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=get_local_date)
    status = db.Column(db.Boolean, nullable=False)  # True for present, False for absent
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    marked_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    last_modified = db.Column(db.DateTime, nullable=False, default=get_local_datetime)

    # Relationship with the user who marked the attendance
    marker = db.relationship('User', foreign_keys=[marked_by])

    __table_args__ = (
        db.UniqueConstraint('date', 'student_id', name='unique_student_date'),
    )

    def __repr__(self):
        status_str = "Present" if self.status else "Absent"
        return f'<Attendance {self.student.name} on {self.date}: {status_str}>'

class ImageUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=get_local_date)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    drive_file_id = db.Column(db.String(255), nullable=True)
    drive_view_link = db.Column(db.String(512), nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=get_local_datetime)
    description = db.Column(db.Text, nullable=True)
    
    # YOLO detection fields
    yolo_count = db.Column(db.Integer, nullable=True)
    yolo_confidence = db.Column(db.Float, nullable=True)
    annotated_file_path = db.Column(db.String(255), nullable=True)
    annotated_drive_file_id = db.Column(db.String(255), nullable=True)
    annotated_drive_view_link = db.Column(db.String(512), nullable=True)
    has_discrepancy = db.Column(db.Boolean, nullable=True)
    discrepancy_message = db.Column(db.Text, nullable=True)

    # Relationship with the user who uploaded the image
    uploader = db.relationship('User', foreign_keys=[uploaded_by])

    def __repr__(self):
        return f'<ImageUpload {self.file_name} on {self.date}>'
