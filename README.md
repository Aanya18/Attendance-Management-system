# Student Attendance Management System

A modern web-based attendance management system built with Flask, designed for educational institutions to efficiently track and manage student attendance through image verification.

## Features

### For Teachers
- Mark daily attendance for assigned students
- Upload and verify attendance through image verification
- View attendance records for the current day
- Add and manage student profiles
- View attendance reports for their students

### For Principals
- Manage all users (teachers and other principals)
- View and edit attendance records for all students
- Access comprehensive monthly attendance reports
- Manage all student records
- View and verify attendance images
- Automatic synchronization with Google Sheets

## How It Works

The system uses a simple but effective approach for attendance verification:
1. Teachers upload images of the attendance records
2. The system processes these images to verify attendance
3. No facial recognition is used - the system simply verifies the attendance marks from the uploaded images
4. This provides a quick and efficient way to digitize physical attendance records

## Technology Stack

- **Backend**: Python Flask
- **Database**: SQLAlchemy
- **Authentication**: Flask-Login
- **External Integration**: Google Sheets API

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Attendance-Management-system.git
cd Attendance-Management-system
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Create a .env file with the following variables
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your_secret_key
DATABASE_URL=sqlite:///attendance.db
GOOGLE_SHEETS_CREDENTIALS=your_google_sheets_credentials_json
ATTENDANCE_SHEET_ID=your_google_sheet_id
```

5. Initialize the database:
```bash
flask db upgrade
```

6. Run the application:
```bash
flask run
```

## User Roles

### Principal
- System administrator with full access
- Can manage users, view/edit all attendance records
- Access to all reports and student management features

### Teacher
- Can mark attendance for assigned students
- View their students' attendance records
- Manage their assigned students' profiles

## Google Sheets Integration

The system automatically syncs attendance records with Google Sheets:
- Creates monthly worksheets automatically
- Updates in real-time when attendance is marked
- Maintains a backup of all attendance records
- Provides easy access to attendance data for reporting

## Security Features

- Secure user authentication and authorization
- Role-based access control
- Password hashing
- Session management
- Protected routes and API endpoints




