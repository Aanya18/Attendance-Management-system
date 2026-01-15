"""
Test script to debug face detection issues.
This will help identify why face detection might be failing.

Usage:
    python -m database.test_face_detection <image_path>
"""
import sys
import os
import logging
import cv2
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_face_detection(image_path):
    """Test face detection on a single image"""
    try:
        # Check if file exists
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return False
        
        logger.info(f"Testing face detection on: {image_path}")
        
        # Read image with OpenCV
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"Could not read image. File may be corrupted.")
            return False
        
        height, width = image.shape[:2]
        logger.info(f"Image loaded successfully")
        logger.info(f"  Dimensions: {width}x{height}")
        logger.info(f"  File size: {os.path.getsize(image_path) / 1024:.2f} KB")
        
        # Check image properties
        if width < 50 or height < 50:
            logger.error(f"Image too small: {width}x{height}. Minimum: 50x50 pixels")
            return False
        
        # Try to load InsightFace
        logger.info("\nAttempting to load InsightFace model...")
        try:
            from insightface.app import FaceAnalysis
            logger.info("✓ InsightFace imported successfully")
        except ImportError as e:
            logger.error(f"✗ Failed to import InsightFace: {e}")
            logger.error("Please install: pip install insightface onnxruntime")
            return False
        
        # Initialize model
        try:
            logger.info("Initializing FaceAnalysis model (buffalo_s)...")
            app = FaceAnalysis(
                name='buffalo_s',
                providers=['CPUExecutionProvider']
            )
            logger.info("✓ Model initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize model: {e}")
            return False
        
        # Prepare model
        try:
            logger.info("Preparing model for CPU execution...")
            app.prepare(ctx_id=-1, det_size=(640, 640))
            logger.info("✓ Model prepared successfully")
        except Exception as e:
            logger.error(f"✗ Failed to prepare model: {e}")
            return False
        
        # Convert image to RGB
        logger.info("\nProcessing image...")
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        logger.info("✓ Image converted to RGB")
        
        # Detect faces
        logger.info("Detecting faces...")
        faces = app.get(image_rgb)
        logger.info(f"✓ Detection complete. Found {len(faces)} face(s)")
        
        if len(faces) == 0:
            logger.warning("\n" + "="*60)
            logger.warning("NO FACE DETECTED")
            logger.warning("="*60)
            logger.warning("Possible reasons:")
            logger.warning("  1. Image doesn't contain a clear face")
            logger.warning("  2. Face is too small or too large")
            logger.warning("  3. Poor lighting or image quality")
            logger.warning("  4. Face is at an extreme angle")
            logger.warning("  5. Face is partially obscured")
            logger.warning("\nTips:")
            logger.warning("  - Use a clear, front-facing photo")
            logger.warning("  - Ensure good lighting")
            logger.warning("  - Face should be clearly visible")
            logger.warning("  - Image should be at least 200x200 pixels")
            return False
        
        # Show detection results
        logger.info("\n" + "="*60)
        logger.info("FACE DETECTION SUCCESSFUL")
        logger.info("="*60)
        
        for idx, face in enumerate(faces):
            bbox = face.bbox.astype(int)
            x1, y1, x2, y2 = bbox
            width_face = x2 - x1
            height_face = y2 - y1
            
            logger.info(f"\nFace {idx + 1}:")
            logger.info(f"  Bounding box: [{x1}, {y1}, {x2}, {y2}]")
            logger.info(f"  Size: {width_face}x{height_face} pixels")
            logger.info(f"  Confidence: {face.det_score:.4f}" if hasattr(face, 'det_score') else "  Confidence: N/A")
            
            if hasattr(face, 'norm_embeddings'):
                embedding = face.norm_embeddings
                logger.info(f"  Embedding shape: {embedding.shape}")
                logger.info(f"  Embedding norm: {np.linalg.norm(embedding):.4f}")
        
        logger.info("\n" + "="*60)
        logger.info("✓ Face detection test completed successfully!")
        logger.info("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"\nError during face detection test: {str(e)}", exc_info=True)
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python -m database.test_face_detection <image_path>")
        print("\nExample:")
        print("  python -m database.test_face_detection student_photo.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    success = test_face_detection(image_path)
    sys.exit(0 if success else 1)

