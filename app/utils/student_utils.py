"""
Utility functions for student account management
"""
import re
from app.models import User


def generate_username_from_name(name, roll_number):
    """
    Generate username from student name and roll number
    Example: "Rahul Kumar" + "101" -> "rahul101" or "rahulkumar101"
    """
    # Convert to lowercase and remove special characters
    name_clean = re.sub(r'[^a-zA-Z\s]', '', name.lower())
    # Replace spaces with nothing or keep first letter of each word
    name_parts = name_clean.split()
    
    if len(name_parts) >= 2:
        # Use first name + roll number
        username = name_parts[0] + roll_number
    else:
        # Use full name without spaces + roll number
        username = ''.join(name_parts) + roll_number
    
    # Check if username already exists, if yes, add suffix
    base_username = username
    counter = 1
    while User.query.filter_by(username=username).first():
        username = f"{base_username}{counter}"
        counter += 1
    
    return username


def generate_email_from_name(name, roll_number, domain='school.com'):
    """
    Generate email from student name and roll number
    Example: "Rahul Kumar" + "101" -> "rahul101@school.com"
    """
    username = generate_username_from_name(name, roll_number)
    email = f"{username}@{domain}"
    
    # Check if email already exists, if yes, add suffix
    base_email = email
    counter = 1
    while User.query.filter_by(email=email).first():
        email = f"{username}{counter}@{domain}"
        counter += 1
    
    return email


def create_student_user_account(student, common_password='student123'):
    """
    Create a User account for a student with auto-generated credentials
    
    Args:
        student: Student model instance
        common_password: Common password for all students (default: 'student123')
    
    Returns:
        User instance if created successfully, None otherwise
    """
    try:
        # Generate username and email from name
        username = generate_username_from_name(student.name, student.roll_number)
        email = generate_email_from_name(student.name, student.roll_number)
        
        # Create User account
        user = User(
            username=username,
            full_name=student.name,
            email=email,
            role='student',
            is_approved=True  # Students are auto-approved
        )
        user.set_password(common_password)
        
        return user
    except Exception as e:
        print(f"Error creating student user account: {str(e)}")
        return None

