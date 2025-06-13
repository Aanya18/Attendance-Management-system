import sqlite3
import logging

# Set up logging
logger = logging.getLogger(__name__)

def rebuild_student_table():
    try:
        # Connect to database
        conn = sqlite3.connect('instance/attendance.db')
        cursor = conn.cursor()
        
        # Create new table with correct constraints
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS new_student (
            id INTEGER PRIMARY KEY, 
            name VARCHAR(100) NOT NULL, 
            roll_number VARCHAR(20) NOT NULL, 
            grade VARCHAR(10) NOT NULL, 
            teacher_id INTEGER NOT NULL,
            FOREIGN KEY(teacher_id) REFERENCES user(id),
            UNIQUE(roll_number, teacher_id)
        )
        ''')
        
        # Copy data from old table to new table
        cursor.execute('INSERT INTO new_student SELECT * FROM student')
        
        # Drop old table
        cursor.execute('DROP TABLE student')
        
        # Rename new table to original name
        cursor.execute('ALTER TABLE new_student RENAME TO student')
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        logger.info("Student table rebuilt successfully!")
        return True
    except Exception as e:
        logger.error(f"Error rebuilding student table: {e}")
        return False

if __name__ == "__main__":
    # Set up logging for standalone execution
    logging.basicConfig(level=logging.INFO)
    rebuild_student_table() 