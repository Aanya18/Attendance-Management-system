# Face Recognition Setup Guide

This guide explains how to set up and test the ArcFace (InsightFace) face recognition integration for the attendance management system.

## Overview

The face recognition system uses **InsightFace** with the **ArcFace** model to generate 512-dimensional face embeddings. This is a CPU-based implementation suitable for normal laptops.

## Architecture

- **Location**: `app/utils/face_recognition.py` - Face recognition utility module
- **Model**: ArcFace (buffalo_s) - Optimized for CPU execution
- **Embedding Size**: 512 dimensions
- **Storage**: JSON-serialized embeddings stored in database

## Installation Steps

### 1. Install Dependencies

Install the required packages:

```bash
pip install insightface onnxruntime
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

**Note**: The first time you run the code, InsightFace will automatically download the model files (~100MB). This happens automatically.

### 2. Update Database Schema

Run the migration script to add face recognition columns to the Student table:

```bash
python -m database.add_face_embedding_column
```

This adds two columns:
- `face_embedding`: Stores the 512-dimensional face embedding (JSON format)
- `face_image_path`: Stores the path to the image used for embedding

### 3. Test the Integration

#### Test 1: Single Student Face Registration

Use the test script to verify student face registration:

```bash
python -m database.test_face_recognition <path_to_face_image>
```

**Example**:
```bash
python -m database.test_face_recognition student_photo.jpg
```

The test script will:
1. ✅ Load the ArcFace model
2. ✅ Detect face in the image
3. ✅ Generate 512-dimensional embedding
4. ✅ Create/update a test student profile
5. ✅ Store the embedding in the database
6. ✅ Verify the storage was successful

#### Test 2: Group Photo Face Recognition

Test the complete flow with a group photo:

```bash
python -m database.test_group_face_recognition <student_face_image> <group_photo> [threshold]
```

**Example**:
```bash
python -m database.test_group_face_recognition student.jpg class_photo.jpg
python -m database.test_group_face_recognition student.jpg class_photo.jpg 0.65
```

The group photo test script will:
1. ✅ Create/update student profile with face embedding
2. ✅ Detect all faces in the group photo
3. ✅ Generate embeddings for each detected face
4. ✅ Compare each face with the student embedding
5. ✅ Identify if the student is present in the group photo
6. ✅ Create an annotated image showing matches

## Expected Output

When running the test script successfully, you should see:

```
INFO - Processing image: student_photo.jpg
INFO - Initializing ArcFace model...
INFO - ✓ ArcFace model loaded successfully
INFO - Detecting face and generating embedding...
INFO - ✓ Face detected successfully
INFO -   Bounding box: [x1, y1, x2, y2]
INFO -   Embedding shape: (512,)
INFO - ✓ Face embedding stored successfully in database
INFO - SUCCESS: Face recognition integration test completed!
```

## File Structure

```
app/
├── utils/
│   └── face_recognition.py      # Face recognition utility (ArcFace integration)
├── models.py                     # Updated Student model with face_embedding field
database/
├── add_face_embedding_column.py      # Database migration script
├── test_face_recognition.py          # Test script for single student registration
└── test_group_face_recognition.py    # Test script for group photo matching
```

## Usage in Code

### Basic Usage

```python
from app.utils.face_recognition import FaceRecognition
import json

# Initialize face recognition
face_rec = FaceRecognition()

# Process an image
embedding, face_image, bbox = face_rec.detect_and_extract_face('path/to/image.jpg')

if embedding is not None:
    # Convert to JSON for storage
    embedding_json = json.dumps(face_rec.embedding_to_json(embedding))
    
    # Store in database
    student.face_embedding = embedding_json
    student.face_image_path = 'path/to/image.jpg'
    db.session.commit()
```

### Comparing Faces

```python
# Compare two embeddings
is_same, similarity = face_rec.compare_faces(embedding1, embedding2, threshold=0.6)
print(f"Same person: {is_same}, Similarity: {similarity:.4f}")
```

### Group Photo Face Recognition

```python
from app.utils.face_recognition import FaceRecognition
from app.models import Student

# Initialize face recognition
face_rec = FaceRecognition()

# Get student with stored embedding
student = Student.query.filter_by(roll_number='TEST001').first()

# Find student in group photo
result = face_rec.find_student_in_group(
    student.face_embedding,
    'path/to/group_photo.jpg',
    threshold=0.6
)

if result['found']:
    print(f"Student found! Similarity: {result['best_similarity']:.4f}")
    print(f"Matched face index: {result['best_match_index']}")
else:
    print("Student not found in group photo")

# Create annotated image
annotated_path = face_rec.annotate_group_photo(
    'path/to/group_photo.jpg',
    result['all_matches']
)
```

### Detecting All Faces in Group Photo

```python
# Detect all faces and get embeddings
detected_faces = face_rec.detect_all_faces('path/to/group_photo.jpg')

for embedding, face_image, bbox, face_idx in detected_faces:
    print(f"Face {face_idx + 1}: Bounding box {bbox}")
    print(f"  Embedding shape: {embedding.shape}")
```

## Database Schema

The `Student` model now includes:

```python
face_embedding = db.Column(db.Text, nullable=True)      # JSON-serialized embedding
face_image_path = db.Column(db.String(255), nullable=True)  # Path to face image
```

## Model Information

- **Model Name**: buffalo_s (smaller, faster, CPU-optimized)
- **Alternative**: buffalo_l (larger, more accurate, slower)
- **Provider**: CPUExecutionProvider (CPU-only)
- **Input Size**: 640x640 pixels
- **Output**: Normalized 512-dimensional vector

## Troubleshooting

### No Face Detected

- Ensure the image contains a clear, front-facing face
- Check that the face is well-lit and visible
- Try a different image with better quality

### Model Download Issues

- First run will download model files (~100MB)
- Ensure internet connection is available
- Model files are cached in `~/.insightface/models/`

### Import Errors

- Ensure all dependencies are installed: `pip install insightface onnxruntime`
- Check Python version (3.7+ required)

## Features

### Current Implementation

1. ✅ **Single Student Registration**: Create one student profile with one face image
2. ✅ **Face Embedding Generation**: Generate 512-dimensional embeddings using ArcFace
3. ✅ **Group Photo Processing**: Detect all faces in a group/class photo
4. ✅ **Face Matching**: Compare student embedding with all faces in group photo
5. ✅ **Presence Detection**: Identify if registered student is present in group photo
6. ✅ **Visualization**: Generate annotated images showing matched faces

### Future Enhancements

1. 🔄 **Multiple Images**: Store multiple face images per student for better accuracy
2. 🔄 **Multiple Students**: Scale to handle multiple registered students
3. 🔄 **Attendance Integration**: Automatically mark attendance based on face recognition
4. 🔄 **Batch Processing**: Process multiple group photos efficiently
5. 🔄 **Web Interface**: Add UI for uploading group photos and viewing results

## Notes

- The system is designed for CPU execution (no GPU required)
- Embeddings are normalized vectors (L2 norm = 1)
- Similarity threshold of 0.6 is recommended for face matching
- The model automatically handles face detection and alignment

