from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, current_user, logout_user, login_required
from urllib.parse import urlparse
from app import db
from app.models import User
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from app.utils.google_sheets import create_teacher_folder_and_sheet
from app.utils.decorators import principal_required, teacher_required
import logging

logger = logging.getLogger(__name__)

auth = Blueprint('auth', __name__, url_prefix='/auth')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class TeacherRegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[])
    password2 = PasswordField('Confirm Password', validators=[])
    submit = SubmitField('Register Teacher')

    def validate_password2(self, password2):
        """Validate password2 only if password is provided"""
        if self.password.data:
            if not password2.data:
                raise ValidationError('Please confirm your password.')
            if password2.data != self.password.data:
                raise ValidationError('Passwords must match.')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class PrincipalRegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[])
    password2 = PasswordField('Confirm Password', validators=[EqualTo('password')])
    submit = SubmitField('Register Principal')

    def __init__(self, *args, **kwargs):
        super(PrincipalRegistrationForm, self).__init__(*args, **kwargs)
        if kwargs.get('formdata'):
            # If form is being submitted, validate password if provided
            if self.password.data:
                self.password.validators = [DataRequired()]
                self.password2.validators = [DataRequired(), EqualTo('password')]

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6, message='Password must be at least 6 characters long')])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')])
    submit = SubmitField('Change Password')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Redirect based on role
        if current_user.is_principal():
            return redirect(url_for('auth.principal_dashboard'))
        elif current_user.is_teacher():
            return redirect(url_for('students.list'))
        elif current_user.is_student():
            return redirect(url_for('student.profile'))
        else:
            return redirect(url_for('auth.login'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user is None:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))
        
        # Check if teacher is approved
        if user.is_teacher() and not user.is_approved:
            flash('Your account is pending approval from the principal. Please wait for approval before logging in.', 'warning')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        flash(f'Welcome back, {user.display_name}!', 'success')
        logger.info(f"User logged in: {user.username} ({user.role})")
        
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            # Redirect based on role
            if user.is_principal():
                next_page = url_for('auth.principal_dashboard')
            elif user.is_teacher():
                next_page = url_for('students.list')
            elif user.is_student():
                next_page = url_for('student.profile')
            else:
                next_page = url_for('auth.login')
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Sign In', form=form)

@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('students.list'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(
                full_name=form.full_name.data,
                username=form.username.data,
                email=form.email.data,
                role='teacher',  # All new registrations are teachers by default
                is_approved=False  # Requires principal approval
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            
            # Don't create folder/sheet until approved by principal
            
            flash('Registration successful! Your account is pending approval from the principal. You will be notified once approved.', 'info')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')
            print(f"Registration error: {str(e)}")  # For debugging
    
    return render_template('auth/register.html', title='Register', form=form)

# Principal setup route removed - using fixed credentials instead

@auth.route('/register/teacher', methods=['GET', 'POST'])
@login_required
@principal_required
def register_teacher():

    form = TeacherRegistrationForm()
    if form.validate_on_submit():
        # Use default password if not provided
        password = form.password.data if form.password.data else 'teacher123'
        
        teacher = User(
            full_name=form.full_name.data,
            username=form.username.data,
            email=form.email.data,
            role='teacher',
            is_approved=True  # Principal-registered teachers are auto-approved
        )
        teacher.set_password(password)
        db.session.add(teacher)
        db.session.commit()
        
        # Create teacher folder and sheet using display_name
        folder_id, sheet_id, sheet_url = create_teacher_folder_and_sheet(teacher.display_name)
        
        # Simple success message without password
        if folder_id and sheet_id:
            flash(f'Teacher "{teacher.full_name or teacher.username}" registered successfully. Username: {teacher.username}.', 'success')
            logger.info(f"Teacher registered: {teacher.username} by {current_user.username}")
        else:
            flash(f'Teacher "{teacher.full_name or teacher.username}" registered. Username: {teacher.username}. Google Drive setup incomplete.', 'warning')
            logger.warning(f"Teacher registered but Drive setup failed: {teacher.username}")
            
        return redirect(url_for('auth.user_list'))
    return render_template('auth/register_teacher.html', title='Register Teacher', form=form)

@auth.route('/register/principal', methods=['GET', 'POST'])
@login_required
@principal_required
def register_principal():

    form = PrincipalRegistrationForm()
    if form.validate_on_submit():
        principal = User(
            full_name=form.full_name.data,
            username=form.username.data,
            email=form.email.data,
            role='principal',
            is_approved=True  # Principals are auto-approved
        )
        principal.set_password(form.password.data)
        db.session.add(principal)
        db.session.commit()
        flash('Principal registered successfully!', 'success')
        return redirect(url_for('auth.user_list'))
    return render_template('auth/register_principal.html', title='Register Principal', form=form)

@auth.route('/users')
@login_required
@principal_required
def user_list():

    teachers = User.query.filter_by(role='teacher').all()
    principals = User.query.filter_by(role='principal').all()
    return render_template('auth/users_list.html', title='Users', teachers=teachers, principals=principals)

@auth.route('/edit-user/<int:id>', methods=['GET', 'POST'])
@login_required
@principal_required
def edit_user(id):
    
    user = User.query.get_or_404(id)
    
    # Use the appropriate form based on user role
    if user.role == 'teacher':
        form = TeacherRegistrationForm()
        title = 'Edit Teacher'
    else:
        form = PrincipalRegistrationForm()
        title = 'Edit Principal'
    
    if request.method == 'GET':
        # Pre-fill form when it's a GET request
        form.full_name.data = user.full_name
        form.username.data = user.username
        form.email.data = user.email
    
    if form.validate_on_submit():
        # Check if username is changed and if it's already taken
        if user.username != form.username.data and User.query.filter_by(username=form.username.data).first():
            flash('Username already taken', 'danger')
            return redirect(url_for('auth.edit_user', id=id))
        
        # Check if email is changed and if it's already taken
        if user.email != form.email.data and User.query.filter_by(email=form.email.data).first():
            flash('Email already taken', 'danger')
            return redirect(url_for('auth.edit_user', id=id))
        
        # Update user information
        user.full_name = form.full_name.data
        user.username = form.username.data
        user.email = form.email.data
        
        if form.password.data:
            user.set_password(form.password.data)
        
        db.session.commit()
        flash('User information updated successfully', 'success')
        return redirect(url_for('auth.user_list'))
    
    return render_template('auth/edit_user.html', title=title, form=form, user=user)

@auth.route('/delete-user/<int:id>')
@login_required
@principal_required
def delete_user(id):
    
    user = User.query.get_or_404(id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('auth.user_list'))
    
    # Delete user
    try:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('auth.user_list'))

@auth.route('/dashboard')
@login_required
@principal_required
def principal_dashboard():
    """Principal dashboard showing pending teacher approvals and statistics"""
    # Get pending teacher approvals
    pending_teachers = User.query.filter_by(role='teacher', is_approved=False).all()
    
    # Get approved teachers count
    approved_teachers = User.query.filter_by(role='teacher', is_approved=True).count()
    
    # Get total students count
    from app.models import Student
    total_students = Student.query.count()
    
    # Get today's attendance count
    from app.models import Attendance
    from datetime import date
    today_attendance = Attendance.query.filter_by(date=date.today()).count()
    
    return render_template('auth/principal_dashboard.html', 
                         title='Principal Dashboard',
                         pending_teachers=pending_teachers,
                         approved_teachers=approved_teachers,
                         total_students=total_students,
                         today_attendance=today_attendance)

@auth.route('/approve-teacher/<int:id>')
@login_required
@principal_required
def approve_teacher(id):
    """Approve a pending teacher registration"""
    teacher = User.query.get_or_404(id)
    
    if teacher.role != 'teacher':
        flash('Only teachers can be approved', 'danger')
        return redirect(url_for('auth.principal_dashboard'))
    
    if teacher.is_approved:
        flash('Teacher is already approved', 'info')
        return redirect(url_for('auth.principal_dashboard'))
    
    try:
        teacher.is_approved = True
        db.session.commit()
        
        # Create teacher folder and sheet after approval
        folder_id, sheet_id, sheet_url = create_teacher_folder_and_sheet(teacher.display_name)
        if folder_id and sheet_id:
            flash(f'Teacher {teacher.username} approved successfully! Google Drive folder and Sheet created.', 'success')
        else:
            flash(f'Teacher {teacher.username} approved successfully, but Drive folder/Sheet creation failed.', 'warning')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving teacher: {str(e)}', 'danger')
    
    return redirect(url_for('auth.principal_dashboard'))

@auth.route('/reject-teacher/<int:id>')
@login_required
@principal_required
def reject_teacher(id):
    """Reject and delete a pending teacher registration"""
    teacher = User.query.get_or_404(id)
    
    if teacher.role != 'teacher':
        flash('Only teachers can be rejected', 'danger')
        return redirect(url_for('auth.principal_dashboard'))
    
    if teacher.is_approved:
        flash('Cannot reject an approved teacher. Please delete instead.', 'warning')
        return redirect(url_for('auth.principal_dashboard'))
    
    try:
        username = teacher.username
        db.session.delete(teacher)
        db.session.commit()
        flash(f'Teacher {username} registration rejected and removed.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error rejecting teacher: {str(e)}', 'danger')
    
    return redirect(url_for('auth.principal_dashboard'))

@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
@teacher_required
def change_password():
    """Teacher password change page"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        # Verify current password
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect', 'danger')
            return render_template('auth/change_password.html', title='Change Password', form=form)
        
        # Check if new password is same as current
        if current_user.check_password(form.new_password.data):
            flash('New password must be different from current password', 'warning')
            return render_template('auth/change_password.html', title='Change Password', form=form)
        
        # Update password
        current_user.set_password(form.new_password.data)
        db.session.commit()
        
        flash('Password changed successfully. Please use your new password for future logins.', 'success')
        logger.info(f"Password changed for user: {current_user.username}")
        return redirect(url_for('students.list'))
    
    return render_template('auth/change_password.html', title='Change Password', form=form)
