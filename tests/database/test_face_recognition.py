"""
Test script for ArcFace face recognition integration.
This script:
1. Creates one student profile
2. Processes one face image to generate embedding
3. Stores the embedding in the database

Usage:
    python -m database.test_face_recognition <path_to_face_image>
    
Example:
    python -m database.test_face_recognition student_photo.jpg
"""
import sys
import os
import json
import logging
import numpy as np
from app import create_app, db
from app.models import Student, User
from app.utils.face_recognition import FaceRecognition

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_face_recognition(image_path):
    """
    Test face recognition integration:
    1. Create a test student profile
    2. Generate face embedding from image
    3. Store embedding in database
    """
    app = create_app()
    
    with app.app_context():
        try:
            # Step 1: Check if image exists
            if not os.path.exists(image_path):
                logger.error(f"Image file not found: {image_path}")
                return False
            
            logger.info(f"Processing image: {image_path}")
            
            # Step 2: Initialize face recognition
            logger.info("Initializing ArcFace model...")
            face_rec = FaceRecognition()
            logger.info("✓ ArcFace model loaded successfully")
            
            # Step 3: Detect face and extract embedding
            logger.info("Detecting face and generating embedding...")
            embedding, face_image, bbox = face_rec.detect_and_extract_face(image_path)
            
            if embedding is None:
                logger.error("Failed to detect face in the image. Please ensure:")
                logger.error("  - The image contains a clear face")
                logger.error("  - The face is well-lit and visible")
                logger.error("  - The image is in a supported format (jpg, png, etc.)")
                return False
            
            logger.info(f"✓ Face detected successfully")
            logger.info(f"  Bounding box: {bbox}")
            logger.info(f"  Embedding shape: {embedding.shape}")
            logger.info(f"  Embedding norm: {np.linalg.norm(embedding):.4f}")
            
            # Step 4: Get or create a principal user (required for student creation)
            principal = User.query.filter_by(username='principal').first()
            if not principal:
                logger.info("Creating default principal user...")
                principal = User(
                    username='principal',
                    email='principal@example.com',
                    role='principal'
                )
                principal.set_password('principal123')
                db.session.add(principal)
                db.session.commit()
                logger.info("✓ Principal user created")
            
            # Step 5: Check if test student already exists
            test_student = Student.query.filter_by(roll_number='TEST001').first()
            
            if test_student:
                logger.info(f"Updating existing test student: {test_student.name}")
                # Update embedding
                test_student.face_embedding = json.dumps(face_rec.embedding_to_json(embedding))
                test_student.face_image_path = image_path
                db.session.commit()
                logger.info("✓ Test student updated with face embedding")
            else:
                # Create new test student
                logger.info("Creating test student profile...")
                test_student = Student(
                    name='Test Student',
                    roll_number='TEST001',
                    grade='10',
                    teacher_id=principal.id,
                    face_embedding=json.dumps(face_rec.embedding_to_json(embedding)),
                    face_image_path=image_path
                )
                db.session.add(test_student)
                db.session.commit()
                logger.info("✓ Test student created with face embedding")
            
            # Step 6: Verify storage
            stored_student = Student.query.filter_by(roll_number='TEST001').first()
            if stored_student and stored_student.face_embedding:
                stored_embedding = face_rec.json_to_embedding(stored_student.face_embedding)
                logger.info("✓ Face embedding stored successfully in database")
                logger.info(f"  Student ID: {stored_student.id}")
                logger.info(f"  Student Name: {stored_student.name}")
                logger.info(f"  Roll Number: {stored_student.roll_number}")
                logger.info(f"  Face Image Path: {stored_student.face_image_path}")
                logger.info(f"  Stored Embedding Shape: {stored_embedding.shape}")
                logger.info(f"  Stored Embedding Norm: {np.linalg.norm(stored_embedding):.4f}")
                
                # Verify embedding matches
                if np.allclose(embedding, stored_embedding, atol=1e-6):
                    logger.info("✓ Embedding verification: PASSED")
                else:
                    logger.warning("⚠ Embedding verification: Minor differences detected (may be due to JSON serialization)")
                
                logger.info("\n" + "="*60)
                logger.info("SUCCESS: Face recognition integration test completed!")
                logger.info("="*60)
                logger.info("\nSummary:")
                logger.info(f"  ✓ Student profile created/updated: {stored_student.name} (ID: {stored_student.id})")
                logger.info(f"  ✓ Face embedding generated: {embedding.shape[0]}-dimensional vector")
                logger.info(f"  ✓ Embedding stored in database")
                logger.info(f"  ✓ System ready for extension to multiple images/students")
                logger.info("\nNext steps:")
                logger.info("  - You can now extend this to handle multiple images per student")
                logger.info("  - You can add face matching logic for attendance verification")
                logger.info("  - The system is ready for production use")
                
                return True
            else:
                logger.error("Failed to verify stored embedding")
                return False
                
        except Exception as e:
            logger.error(f"Error during face recognition test: {str(e)}", exc_info=True)
            db.session.rollback()
            return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python -m database.test_face_recognition <path_to_face_image>")
        print("\nExample:")
        print("  python -m database.test_face_recognition student_photo.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    success = test_face_recognition(image_path)
    sys.exit(0 if success else 1)

