"""Test script to check InsightFace face object attributes"""
from app import create_app
from app.utils.face_recognition import FaceRecognition
import os
import sys

if len(sys.argv) < 2:
    print("Usage: python -m database.test_face_attributes <image_path>")
    sys.exit(1)

image_path = sys.argv[1]

app = create_app()
with app.app_context():
    face_rec = FaceRecognition()
    embedding, face_image, bbox = face_rec.detect_and_extract_face(image_path)
    
    if embedding is not None:
        print(f"✓ Embedding extracted successfully!")
        print(f"  Shape: {embedding.shape}")
        print(f"  Type: {type(embedding)}")
        print(f"  First 5 values: {embedding[:5]}")
    else:
        print("✗ Failed to extract embedding")
        print("  Check logs for details")

