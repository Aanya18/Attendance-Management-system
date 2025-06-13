from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, current_user, logout_user, login_required
from urllib.parse import urlparse
from app import db
from app.models import User
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from app.utils.google_sheets import create_teacher_folder_and_sheet

auth = Blueprint('auth', __name__, url_prefix='/auth')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
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
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[])
    password2 = PasswordField('Confirm Password', validators=[EqualTo('password')])
    submit = SubmitField('Register Teacher')

    def __init__(self, *args, **kwargs):
        super(TeacherRegistrationForm, self).__init__(*args, **kwargs)
        if kwargs.get('formdata'):
            # If form is being submitted, validate password if provided
            if self.password.data:
                self.password.validators = [DataRequired()]
                self.password2.validators = [DataRequired(), EqualTo('password')]

class PrincipalRegistrationForm(FlaskForm):
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

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('students.list'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user is None:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        flash('Logged in successfully!', 'success')
        
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('students.list')
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
                username=form.username.data,
                email=form.email.data,
                role='teacher'  # All new registrations are teachers by default
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            
            # Create teacher folder and sheet using display_name
            folder_id, sheet_id, sheet_url = create_teacher_folder_and_sheet(user.display_name)
            if folder_id and sheet_id:
                print(f"Created folder and sheet for teacher {user.display_name}")
                print(f"Sheet URL: {sheet_url}")
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')
            print(f"Registration error: {str(e)}")  # For debugging
    
    return render_template('auth/register.html', title='Register', form=form)

# Principal setup route removed - using fixed credentials instead

@auth.route('/register/teacher', methods=['GET', 'POST'])
@login_required
def register_teacher():
    # Only principals can register teachers
    if not current_user.is_principal():
        flash('Only principals can register teachers', 'danger')
        return redirect(url_for('students.list'))

    form = TeacherRegistrationForm()
    if form.validate_on_submit():
        teacher = User(
            username=form.username.data,
            email=form.email.data,
            role='teacher'
        )
        teacher.set_password(form.password.data)
        db.session.add(teacher)
        db.session.commit()
        
        # Create teacher folder and sheet using display_name
        folder_id, sheet_id, sheet_url = create_teacher_folder_and_sheet(teacher.display_name)
        if folder_id and sheet_id:
            flash(f'Teacher registered successfully! Created Google Drive folder and Sheet.', 'success')
        else:
            flash('Teacher registered successfully but Drive folder/Sheet creation failed.', 'warning')
            
        return redirect(url_for('auth.user_list'))
    return render_template('auth/register_teacher.html', title='Register Teacher', form=form)

@auth.route('/register/principal', methods=['GET', 'POST'])
@login_required
def register_principal():
    # Only principals can register new principals
    if not current_user.is_principal():
        flash('Only principals can register new principals', 'danger')
        return redirect(url_for('students.list'))

    form = PrincipalRegistrationForm()
    if form.validate_on_submit():
        principal = User(
            username=form.username.data,
            email=form.email.data,
            role='principal'
        )
        principal.set_password(form.password.data)
        db.session.add(principal)
        db.session.commit()
        flash('Principal registered successfully!', 'success')
        return redirect(url_for('auth.user_list'))
    return render_template('auth/register_principal.html', title='Register Principal', form=form)

@auth.route('/users')
@login_required
def user_list():
    # Only principals can view the user list
    if not current_user.is_principal():
        flash('Access denied', 'danger')
        return redirect(url_for('students.list'))

    teachers = User.query.filter_by(role='teacher').all()
    principals = User.query.filter_by(role='principal').all()
    return render_template('auth/users_list.html', title='Users', teachers=teachers, principals=principals)

@auth.route('/edit-user/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    # Only principals can edit users
    if not current_user.is_principal():
        flash('Access denied', 'danger')
        return redirect(url_for('students.list'))
    
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
def delete_user(id):
    # Only principals can delete users
    if not current_user.is_principal():
        flash('Access denied', 'danger')
        return redirect(url_for('students.list'))
    
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
