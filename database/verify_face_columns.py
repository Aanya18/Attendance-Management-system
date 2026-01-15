"""Verify that face_embedding columns exist in the Student table"""
from app import create_app, db
from sqlalchemy import inspect

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('student')]
    
    print("Current columns in Student table:")
    for col in columns:
        print(f"  - {col}")
    
    print("\nChecking for face recognition columns:")
    if 'face_embedding' in columns:
        print("  ✓ face_embedding column exists")
    else:
        print("  ✗ face_embedding column MISSING")
    
    if 'face_image_path' in columns:
        print("  ✓ face_image_path column exists")
    else:
        print("  ✗ face_image_path column MISSING")


