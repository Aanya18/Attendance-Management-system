"""
Test script to debug InsightFace embedding access
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.face_recognition import FaceRecognition
import cv2
import numpy as np

def test_embedding_access():
    """Test how to access embeddings from InsightFace face objects"""
    fr = FaceRecognition()
    
    # Test with a sample image
    test_image_path = 'app/static/student_faces/1_1767612713.jpg'
    
    if not os.path.exists(test_image_path):
        print(f"Test image not found: {test_image_path}")
        print("Please upload a student face image first")
        return
    
    print(f"Testing embedding access with image: {test_image_path}")
    
    # Load image
    image = cv2.imread(test_image_path)
    if image is None:
        print(f"Could not load image: {test_image_path}")
        return
    
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Get face app (access the property)
    face_app = fr.app
    
    # Detect faces
    faces = face_app.get(image_rgb)
    
    if len(faces) == 0:
        print("No faces detected")
        return
    
    face = faces[0]
    print(f"\nDetected {len(faces)} face(s)")
    print(f"Face object type: {type(face)}")
    print(f"Face object dir: {[attr for attr in dir(face) if not attr.startswith('_')]}")
    
    # Try different ways to access embedding
    print("\n=== Testing embedding access methods ===")
    
    # Method 1: Attribute access
    if hasattr(face, 'embedding'):
        emb1 = face.embedding
        print(f"1. face.embedding: type={type(emb1)}, shape={getattr(emb1, 'shape', 'no shape')}")
        if hasattr(emb1, '__len__'):
            print(f"   Length: {len(emb1)}")
        if isinstance(emb1, np.ndarray):
            print(f"   Array shape: {emb1.shape}, dtype: {emb1.dtype}")
    
    # Method 2: Dict access
    try:
        if hasattr(face, '__getitem__'):
            emb2 = face['embedding']
            print(f"2. face['embedding']: type={type(emb2)}, shape={getattr(emb2, 'shape', 'no shape')}")
    except Exception as e:
        print(f"2. face['embedding']: Error - {e}")
    
    # Method 3: get() method
    try:
        if hasattr(face, 'get'):
            emb3 = face.get('embedding')
            print(f"3. face.get('embedding'): type={type(emb3)}, shape={getattr(emb3, 'shape', 'no shape')}")
    except Exception as e:
        print(f"3. face.get('embedding'): Error - {e}")
    
    # Method 4: normed_embedding
    if hasattr(face, 'normed_embedding'):
        emb4 = face.normed_embedding
        print(f"4. face.normed_embedding: type={type(emb4)}, shape={getattr(emb4, 'shape', 'no shape')}")
    
    # Method 5: Check if it's a dict
    if isinstance(face, dict):
        print(f"5. face is dict: {list(face.keys())}")
        if 'embedding' in face:
            emb5 = face['embedding']
            print(f"   face['embedding']: type={type(emb5)}, shape={getattr(emb5, 'shape', 'no shape')}")
    
    # Method 6: Try to convert to dict
    try:
        face_dict = dict(face)
        print(f"6. dict(face): keys={list(face_dict.keys())}")
        if 'embedding' in face_dict:
            emb6 = face_dict['embedding']
            print(f"   dict(face)['embedding']: type={type(emb6)}, shape={getattr(emb6, 'shape', 'no shape')}")
    except Exception as e:
        print(f"6. dict(face): Error - {e}")
    
    print("\n=== Testing detect_and_extract_face ===")
    embedding, face_image, bbox = fr.detect_and_extract_face(test_image_path)
    if embedding is not None:
        print(f"Success! Embedding shape: {embedding.shape}, norm: {np.linalg.norm(embedding):.4f}")
    else:
        print("Failed to extract embedding")

if __name__ == '__main__':
    test_embedding_access()

