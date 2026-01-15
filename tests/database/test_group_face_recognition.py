"""
Test script for group photo face recognition.
This script demonstrates the complete flow:
1. Create/use one student profile with one face image
2. Upload a group photo
3. Detect all faces in the group photo
4. Compare each face with the student embedding
5. Identify if the student is present in the group photo

Usage:
    python -m database.test_group_face_recognition <student_face_image> <group_photo>
    
Example:
    python -m database.test_group_face_recognition student_photo.jpg class_photo.jpg
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

def test_group_face_recognition(student_image_path, group_image_path, threshold=0.6):
    """
    Test group photo face recognition:
    1. Create/update student profile with face embedding
    2. Process group photo to detect all faces
    3. Compare each face with student embedding
    4. Identify if student is present
    """
    app = create_app()
    
    with app.app_context():
        try:
            # Step 1: Verify input files exist
            if not os.path.exists(student_image_path):
                logger.error(f"Student face image not found: {student_image_path}")
                return False
            
            if not os.path.exists(group_image_path):
                logger.error(f"Group photo not found: {group_image_path}")
                return False
            
            logger.info("="*60)
            logger.info("GROUP PHOTO FACE RECOGNITION TEST")
            logger.info("="*60)
            
            # Step 2: Initialize face recognition
            logger.info("\n[Step 1] Initializing ArcFace model...")
            face_rec = FaceRecognition()
            logger.info("✓ ArcFace model loaded successfully")
            
            # Step 3: Process student face image
            logger.info(f"\n[Step 2] Processing student face image: {student_image_path}")
            student_embedding, student_face_image, student_bbox = face_rec.detect_and_extract_face(student_image_path)
            
            if student_embedding is None:
                logger.error("Failed to detect face in student image. Please ensure:")
                logger.error("  - The image contains a clear, front-facing face")
                logger.error("  - The face is well-lit and visible")
                return False
            
            logger.info(f"✓ Student face detected successfully")
            logger.info(f"  Bounding box: {student_bbox}")
            logger.info(f"  Embedding shape: {student_embedding.shape}")
            logger.info(f"  Embedding norm: {np.linalg.norm(student_embedding):.4f}")
            
            # Step 4: Get or create principal user
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
            
            # Step 5: Create or update student profile
            test_student = Student.query.filter_by(roll_number='TEST001').first()
            
            if test_student:
                logger.info(f"\n[Step 3] Updating existing student: {test_student.name}")
                test_student.face_embedding = json.dumps(face_rec.embedding_to_json(student_embedding))
                test_student.face_image_path = student_image_path
                db.session.commit()
                logger.info("✓ Student profile updated with face embedding")
            else:
                logger.info("\n[Step 3] Creating student profile...")
                test_student = Student(
                    name='Test Student',
                    roll_number='TEST001',
                    grade='10',
                    teacher_id=principal.id,
                    face_embedding=json.dumps(face_rec.embedding_to_json(student_embedding)),
                    face_image_path=student_image_path
                )
                db.session.add(test_student)
                db.session.commit()
                logger.info("✓ Student profile created with face embedding")
            
            logger.info(f"  Student ID: {test_student.id}")
            logger.info(f"  Student Name: {test_student.name}")
            logger.info(f"  Roll Number: {test_student.roll_number}")
            
            # Step 6: Process group photo
            logger.info(f"\n[Step 4] Processing group photo: {group_image_path}")
            logger.info("  Detecting all faces in group photo...")
            
            result = face_rec.find_student_in_group(
                test_student.face_embedding,
                group_image_path,
                threshold=threshold
            )
            
            # Step 7: Display results
            logger.info("\n" + "="*60)
            logger.info("RESULTS")
            logger.info("="*60)
            logger.info(f"Total faces detected in group photo: {result['total_faces']}")
            
            if result['total_faces'] == 0:
                logger.warning("⚠ No faces detected in group photo!")
                return False
            
            logger.info(f"\nBest match similarity: {result['best_similarity']:.4f}")
            logger.info(f"Similarity threshold: {threshold}")
            
            if result['found']:
                logger.info("\n" + "="*60)
                logger.info("✓ STUDENT FOUND IN GROUP PHOTO!")
                logger.info("="*60)
                logger.info(f"  Match found at face index: {result['best_match_index']}")
                logger.info(f"  Similarity score: {result['best_similarity']:.4f}")
                
                # Show all matches above threshold
                matches_above_threshold = [
                    m for m in result['all_matches'] 
                    if m['similarity'] >= threshold
                ]
                logger.info(f"\n  Total matches above threshold ({threshold}): {len(matches_above_threshold)}")
                
            else:
                logger.info("\n" + "="*60)
                logger.info("✗ STUDENT NOT FOUND IN GROUP PHOTO")
                logger.info("="*60)
                logger.info(f"  Best similarity: {result['best_similarity']:.4f} (below threshold {threshold})")
            
            # Display all face comparisons
            logger.info("\n" + "-"*60)
            logger.info("DETAILED FACE COMPARISONS:")
            logger.info("-"*60)
            for match in result['all_matches']:
                status = "✓ MATCH" if match['is_match'] else "✗ No match"
                logger.info(f"  Face {match['index'] + 1}: {status} - Similarity: {match['similarity']:.4f}")
            
            # Step 8: Create annotated image
            logger.info(f"\n[Step 5] Creating annotated group photo...")
            annotated_path = face_rec.annotate_group_photo(
                group_image_path,
                result['all_matches'],
                output_path=None  # Will auto-generate path
            )
            
            if annotated_path:
                logger.info(f"✓ Annotated image saved to: {annotated_path}")
                logger.info("  - Green boxes: Matched faces")
                logger.info("  - Red boxes: Non-matched faces")
            
            # Step 9: Final summary
            logger.info("\n" + "="*60)
            logger.info("TEST SUMMARY")
            logger.info("="*60)
            logger.info(f"✓ Student profile: {test_student.name} (ID: {test_student.id})")
            logger.info(f"✓ Student face embedding: Generated and stored")
            logger.info(f"✓ Group photo processed: {result['total_faces']} faces detected")
            logger.info(f"✓ Student presence: {'FOUND' if result['found'] else 'NOT FOUND'}")
            if result['found']:
                logger.info(f"  - Best match similarity: {result['best_similarity']:.4f}")
                logger.info(f"  - Matched face index: {result['best_match_index']}")
            
            logger.info("\n" + "="*60)
            logger.info("SUCCESS: Group photo face recognition test completed!")
            logger.info("="*60)
            logger.info("\nThe system is ready to:")
            logger.info("  - Scale to multiple students")
            logger.info("  - Handle multiple images per student")
            logger.info("  - Integrate with attendance marking")
            
            return True
                
        except Exception as e:
            logger.error(f"\nError during group face recognition test: {str(e)}", exc_info=True)
            db.session.rollback()
            return False

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python -m database.test_group_face_recognition <student_face_image> <group_photo> [threshold]")
        print("\nArguments:")
        print("  student_face_image: Path to the student's face image")
        print("  group_photo: Path to the group/class photo")
        print("  threshold: Optional similarity threshold (default: 0.6)")
        print("\nExample:")
        print("  python -m database.test_group_face_recognition student.jpg class_photo.jpg")
        print("  python -m database.test_group_face_recognition student.jpg class_photo.jpg 0.65")
        sys.exit(1)
    
    student_image = sys.argv[1]
    group_image = sys.argv[2]
    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.6
    
    success = test_group_face_recognition(student_image, group_image, threshold)
    sys.exit(0 if success else 1)

