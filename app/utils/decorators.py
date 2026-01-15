"""
Role-Based Access Control (RBAC) Decorators
Provides reusable decorators for enforcing role-based permissions
"""
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def principal_required(f):
    """
    Decorator to ensure only principals can access a route.
    Redirects to login if not authenticated, or to students list if not principal.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page', 'danger')
            return redirect(url_for('auth.login'))
        if not current_user.is_principal():
            flash('Access denied. Principal access required.', 'danger')
            return redirect(url_for('students.list'))
        return f(*args, **kwargs)
    return decorated_function


def teacher_required(f):
    """
    Decorator to ensure only teachers can access a route.
    Redirects to login if not authenticated, or to students list if not teacher.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page', 'danger')
            return redirect(url_for('auth.login'))
        if not current_user.is_teacher():
            flash('Access denied. Teacher access required.', 'danger')
            return redirect(url_for('students.list'))
        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    """
    Decorator to ensure only students can access a route.
    Redirects to login if not authenticated, or to student profile if not student.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page', 'danger')
            return redirect(url_for('auth.login'))
        if not current_user.is_student():
            flash('Access denied. Student access required.', 'danger')
            if current_user.is_principal():
                return redirect(url_for('auth.principal_dashboard'))
            elif current_user.is_teacher():
                return redirect(url_for('students.list'))
            else:
                return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def principal_or_owner_required(owner_check_func):
    """
    Decorator factory for routes that require principal access OR ownership.
    
    Args:
        owner_check_func: A function that takes (current_user, *args, **kwargs) 
                         and returns True if current_user owns the resource.
                         Should return False or None if resource doesn't exist or user doesn't own it.
    
    Example:
        @principal_or_owner_required(lambda user, *args, **kwargs: 
            (lambda s: s.teacher_id == user.id if s else False)(
                Student.query.get(kwargs.get('id', args[0] if args else None))
            ))
        def edit_student(id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page', 'danger')
                return redirect(url_for('auth.login'))
            
            # Allow if principal
            if current_user.is_principal():
                return f(*args, **kwargs)
            
            # Check ownership - if function returns True, allow access
            try:
                if owner_check_func(current_user, *args, **kwargs):
                    return f(*args, **kwargs)
            except (AttributeError, TypeError) as e:
                # If there's an error checking ownership (e.g., resource doesn't exist),
                # let the route handler deal with it (it will use get_or_404)
                # But we still need to deny access if user is not principal
                flash('Access denied. You do not have permission to access this resource.', 'danger')
                return redirect(url_for('students.list'))
            
            # Deny access
            flash('Access denied. You do not have permission to access this resource.', 'danger')
            return redirect(url_for('students.list'))
        return decorated_function
    return decorator

