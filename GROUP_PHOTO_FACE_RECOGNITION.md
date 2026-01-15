# Group Photo Face Recognition - Quick Guide

## Overview

This feature allows you to:
1. Register one student with one face image
2. Upload a group/class photo
3. Automatically detect if the registered student is present in the group photo

## Quick Start

### Step 1: Register Student Face

```bash
python -m database.test_face_recognition student_photo.jpg
```

This creates a student profile (TEST001) with the face embedding stored in the database.

### Step 2: Test Group Photo Recognition

```bash
python -m database.test_group_face_recognition student_photo.jpg class_photo.jpg
```

This will:
- Detect all faces in the class photo
- Compare each face with the registered student
- Identify if the student is present
- Generate an annotated image showing matches

## Expected Output

```
============================================================
GROUP PHOTO FACE RECOGNITION TEST
============================================================

[Step 1] Initializing ArcFace model...
✓ ArcFace model loaded successfully

[Step 2] Processing student face image: student.jpg
✓ Student face detected successfully
  Bounding box: [x1, y1, x2, y2]
  Embedding shape: (512,)

[Step 3] Creating student profile...
✓ Student profile created with face embedding

[Step 4] Processing group photo: class_photo.jpg
  Detecting all faces in group photo...

============================================================
RESULTS
============================================================
Total faces detected in group photo: 5

Best match similarity: 0.8234
Similarity threshold: 0.6

============================================================
✓ STUDENT FOUND IN GROUP PHOTO!
============================================================
  Match found at face index: 2
  Similarity score: 0.8234

DETAILED FACE COMPARISONS:
------------------------------------------------------------
  Face 1: ✗ No match - Similarity: 0.4521
  Face 2: ✓ MATCH - Similarity: 0.8234
  Face 3: ✗ No match - Similarity: 0.3892
  Face 4: ✗ No match - Similarity: 0.5123
  Face 5: ✗ No match - Similarity: 0.4012

[Step 5] Creating annotated group photo...
✓ Annotated image saved to: class_photo_annotated.jpg
  - Green boxes: Matched faces
  - Red boxes: Non-matched faces

============================================================
TEST SUMMARY
============================================================
✓ Student profile: Test Student (ID: 1)
✓ Student face embedding: Generated and stored
✓ Group photo processed: 5 faces detected
✓ Student presence: FOUND
  - Best match similarity: 0.8234
  - Matched face index: 2
```

## Parameters

### Similarity Threshold

The default threshold is **0.6**. You can adjust it:

- **Lower threshold (0.5)**: More lenient, may have false positives
- **Default (0.6)**: Balanced accuracy
- **Higher threshold (0.7)**: Stricter, fewer false positives but may miss matches

```bash
python -m database.test_group_face_recognition student.jpg class.jpg 0.65
```

## Annotated Images

The system automatically generates annotated images:
- **Green boxes**: Faces that match the student (above threshold)
- **Red boxes**: Faces that don't match
- **Labels**: Show face index and similarity score

## Code Usage

```python
from app.utils.face_recognition import FaceRecognition
from app.models import Student

# Initialize
face_rec = FaceRecognition()

# Get student
student = Student.query.filter_by(roll_number='TEST001').first()

# Find in group photo
result = face_rec.find_student_in_group(
    student.face_embedding,
    'group_photo.jpg',
    threshold=0.6
)

# Check result
if result['found']:
    print(f"Found! Similarity: {result['best_similarity']:.4f}")
else:
    print("Not found")
```

## Troubleshooting

### Student Not Found (but should be)

- **Lower the threshold**: Try 0.55 or 0.5
- **Check image quality**: Ensure good lighting and clear face
- **Verify student image**: Make sure the registered face is clear

### Too Many False Positives

- **Raise the threshold**: Try 0.65 or 0.7
- **Improve student image**: Use a clearer, front-facing photo

### No Faces Detected

- **Check image format**: Use JPG or PNG
- **Verify image quality**: Ensure faces are visible
- **Try different photo**: Some photos may not work well

## Next Steps

After successful testing:
1. ✅ System is ready to scale to multiple students
2. ✅ Can be integrated with attendance marking
3. ✅ Can handle multiple images per student
4. ✅ Ready for web interface integration


