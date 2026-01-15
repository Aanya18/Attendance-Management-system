"""
Face Recognition Utility using ArcFace (InsightFace)
This module provides face detection and embedding generation capabilities.
"""
import cv2
import numpy as np
from insightface.app import FaceAnalysis
import os
import json
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class FaceRecognition:
    """
    Face recognition utility using InsightFace ArcFace model.
    Provides face detection and embedding generation for CPU-based execution.
    """
    
    def __init__(self):
        """Initialize the InsightFace model"""
        self._app = None
        self._model_loaded = False
        
    @property
    def app(self):
        """Lazy load the InsightFace model only when needed"""
        if self._app is None:
            try:
                # Initialize InsightFace with ArcFace model
                # Using 'buffalo_l' for better accuracy, or 'buffalo_s' for faster inference
                # For CPU, 'buffalo_s' is recommended
                self._app = FaceAnalysis(
                    name='buffalo_s',  # Smaller model for CPU
                    providers=['CPUExecutionProvider']  # CPU-only execution
                )
                self._app.prepare(ctx_id=-1, det_size=(640, 640))
                self._model_loaded = True
                logger.info("InsightFace ArcFace model loaded successfully")
            except ImportError as e:
                error_msg = str(e)
                logger.error(f"Import error loading InsightFace model: {error_msg}", exc_info=True)
                raise ImportError("InsightFace library not installed. Please install: pip install insightface onnxruntime") from e
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e) if str(e) else repr(e)
                logger.error(f"Error loading InsightFace model: {error_type}: {error_msg}", exc_info=True)
                
                # Check for specific ONNX Runtime errors
                if "bad allocation" in error_msg.lower() or "onnxruntimeerror" in error_type.lower():
                    detailed_msg = (
                        f"Failed to load InsightFace model due to memory allocation error. "
                        f"This usually indicates:\n"
                        f"1. Insufficient system memory (RAM)\n"
                        f"2. Corrupted model files - try deleting ~/.insightface/models/ and re-downloading\n"
                        f"3. Model file path issues\n"
                        f"Original error: {error_type}: {error_msg}"
                    )
                    logger.error(detailed_msg)
                    raise RuntimeError(detailed_msg) from e
                elif "onnxruntime" in error_msg.lower() and "not installed" in error_msg.lower():
                    raise ImportError("ONNX Runtime not installed. Please install: pip install onnxruntime") from e
                else:
                    raise RuntimeError(f"Failed to load InsightFace model: {error_type}: {error_msg}") from e
        return self._app
    
    def detect_and_extract_face(self, image_path):
        """
        Detect face in an image and extract face embedding using ArcFace.
        
        Args:
            image_path (str): Path to the input image file
            
        Returns:
            tuple: (face_embedding, face_image, bbox) or (None, None, None) if no face detected
                - face_embedding: numpy array of shape (512,) containing the face embedding
                - face_image: cropped face image (numpy array)
                - bbox: bounding box coordinates [x1, y1, x2, y2]
        """
        try:
            # Read the image
            if not os.path.exists(image_path):
                error_msg = f"Image file not found: {image_path}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            image = cv2.imread(image_path)
            if image is None:
                error_msg = f"Could not read image at {image_path}. File may be corrupted or unsupported format."
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Check image dimensions
            height, width = image.shape[:2]
            logger.info(f"Processing image: {image_path}, Size: {width}x{height}")
            
            if width < 50 or height < 50:
                error_msg = f"Image too small: {width}x{height}. Minimum size: 50x50 pixels"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Convert BGR to RGB (InsightFace expects RGB)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Ensure model is loaded
            logger.info("Loading InsightFace model...")
            face_app = self.app  # This will trigger model loading if not already loaded
            logger.info("InsightFace model loaded, detecting faces...")
            
            # Detect faces and extract embeddings
            faces = face_app.get(image_rgb)
            logger.info(f"Detected {len(faces)} face(s) in image")
            
            if len(faces) == 0:
                logger.warning(f"No face detected in image: {image_path}")
                logger.warning("Tips: Ensure image contains a clear, front-facing face with good lighting")
                return None, None, None
            
            if len(faces) > 1:
                logger.warning(f"Multiple faces detected in image: {image_path}. Using the largest face.")
                # Use the face with the largest bounding box
                largest_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
                face = largest_face
            else:
                face = faces[0]
            
            # Extract embedding (normalized vector of 512 dimensions)
            try:
                # Extract embedding from InsightFace face object
                if hasattr(face, 'embedding'):
                    embedding = np.asarray(face.embedding, dtype=np.float32)
                elif hasattr(face, '__getitem__'):
                    embedding = np.asarray(face['embedding'], dtype=np.float32)
                else:
                    logger.error(f"Face object does not have embedding attribute")
                    return None, None, None
                
                # Verify embedding shape
                if len(embedding.shape) == 0:
                    logger.error(f"Embedding is scalar, cannot use")
                    return None, None, None
                
                # Flatten if needed
                if len(embedding.shape) > 1:
                    embedding = embedding.flatten()
                
                # Normalize if needed
                norm = np.linalg.norm(embedding)
                if norm > 0 and abs(norm - 1.0) > 0.01:
                    embedding = embedding / norm
                
                # Final verification
                if embedding.shape[0] != 512:
                    logger.error(f"Invalid embedding shape: {embedding.shape}, expected 512 for image: {image_path}")
                    return None, None, None
                
                logger.info(f"Embedding extracted successfully: shape={embedding.shape}")
                
            except AttributeError as e:
                attrs = [attr for attr in dir(face) if not attr.startswith('_')]
                logger.error(f"Face object does not have embedding attribute: {str(e)}")
                logger.error(f"Face object type: {type(face)}, Available attributes: {attrs}")
                return None, None, None
            except Exception as e:
                logger.error(f"Error extracting embedding: {str(e)}", exc_info=True)
                return None, None, None
            
            # Get bounding box
            bbox = face.bbox.astype(int).tolist()  # [x1, y1, x2, y2]
            
            # Crop face image
            x1, y1, x2, y2 = bbox
            # Ensure coordinates are within image bounds
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(image.shape[1], x2)
            y2 = min(image.shape[0], y2)
            face_image = image[y1:y2, x1:x2]
            
            logger.info(f"Successfully extracted face embedding from {image_path}, BBox: {bbox}, Embedding shape: {embedding.shape}")
            return embedding, face_image, bbox
            
        except Exception as e:
            error_msg = f"Error in face detection/extraction: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Re-raise the exception so the caller can see the actual error
            raise Exception(error_msg) from e
    
    def embedding_to_json(self, embedding):
        """
        Convert numpy embedding array to JSON-serializable format.
        
        Args:
            embedding: numpy array of shape (512,)
            
        Returns:
            list: List of floats representing the embedding
        """
        if embedding is None:
            return None
        return embedding.tolist()
    
    def json_to_embedding(self, embedding_json):
        """
        Convert JSON-serialized embedding back to numpy array.
        
        Args:
            embedding_json: List of floats or JSON string
            
        Returns:
            numpy array of shape (512,)
        """
        if embedding_json is None:
            return None
        
        if isinstance(embedding_json, str):
            embedding_json = json.loads(embedding_json)
        
        return np.array(embedding_json, dtype=np.float32)
    
    def detect_all_faces(self, image_path):
        """
        Detect all faces in a group photo and extract embeddings for each.
        
        Args:
            image_path (str): Path to the group photo
            
        Returns:
            list: List of tuples, each containing (embedding, face_image, bbox, face_index)
                - embedding: numpy array of shape (512,) containing the face embedding
                - face_image: cropped face image (numpy array)
                - bbox: bounding box coordinates [x1, y1, x2, y2]
                - face_index: index of the face (0-based)
        """
        try:
            # Read the image
            if not os.path.exists(image_path):
                raise ValueError(f"Image file not found: {image_path}")
            
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image at {image_path}")
            
            # Convert BGR to RGB (InsightFace expects RGB)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detect all faces and extract embeddings
            try:
                faces = self.app.get(image_rgb)
            except (ImportError, RuntimeError) as e:
                # Re-raise model loading errors with proper context
                logger.error(f"Model loading error in detect_all_faces: {str(e)}", exc_info=True)
                raise
            except Exception as e:
                logger.error(f"Unexpected error during face detection: {str(e)}", exc_info=True)
                raise RuntimeError(f"Face detection failed: {str(e)}") from e
            
            if len(faces) == 0:
                logger.warning(f"No faces detected in group photo: {image_path}")
                return []
            
            results = []
            for idx, face in enumerate(faces):
                # Extract embedding (normalized vector of 512 dimensions)
                # Test confirmed that face.embedding works correctly
                try:
                    if hasattr(face, 'embedding'):
                        embedding = np.asarray(face.embedding, dtype=np.float32)
                    elif hasattr(face, '__getitem__'):
                        embedding = np.asarray(face['embedding'], dtype=np.float32)
                    else:
                        logger.warning(f"Face {idx} does not have embedding attribute, skipping")
                        continue
                    
                    # Verify shape
                    if len(embedding.shape) == 0:
                        logger.warning(f"Face {idx} embedding is scalar, skipping")
                        continue
                    
                    # Flatten if 2D
                    if len(embedding.shape) > 1:
                        embedding = embedding.flatten()
                    
                    if embedding.shape[0] != 512:
                        logger.warning(f"Invalid embedding shape {embedding.shape} for face {idx}, skipping")
                        continue
                    
                    # Normalize if needed
                    norm = np.linalg.norm(embedding)
                    if norm > 0 and abs(norm - 1.0) > 0.01:
                        embedding = embedding / norm
                        
                except Exception as e:
                    logger.warning(f"Error extracting embedding for face {idx}: {e}, skipping")
                    continue
                
                # Get bounding box
                bbox = face.bbox.astype(int).tolist()  # [x1, y1, x2, y2]
                
                # Crop face image
                x1, y1, x2, y2 = bbox
                # Ensure coordinates are within image bounds
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(image.shape[1], x2)
                y2 = min(image.shape[0], y2)
                face_image = image[y1:y2, x1:x2]
                
                results.append((embedding, face_image, bbox, idx))
            
            logger.info(f"Successfully detected {len(results)} faces in group photo: {image_path}")
            return results
            
        except (ImportError, RuntimeError) as e:
            # Re-raise model loading and runtime errors so caller can handle them
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else repr(e)
            logger.error(f"Error detecting faces in group photo: {error_type}: {error_msg}", exc_info=True)
            raise
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else repr(e)
            logger.error(f"Error detecting faces in group photo: {error_type}: {error_msg}", exc_info=True)
            # Return empty list for other errors (e.g., image reading issues)
            return []
    
    def find_student_in_group(self, student_embedding, group_image_path, threshold=0.6):
        """
        Find a student in a group photo by comparing their embedding with all detected faces.
        
        Args:
            student_embedding: numpy array or JSON-serialized embedding of the student
            group_image_path (str): Path to the group photo
            threshold: similarity threshold (default 0.6)
            
        Returns:
            dict: Results containing:
                - found: bool - Whether the student was found
                - best_match_index: int - Index of the best matching face (-1 if not found)
                - best_similarity: float - Similarity score of the best match
                - all_matches: list - List of all matches with (index, similarity, bbox)
                - total_faces: int - Total number of faces detected in group photo
        """
        try:
            # Convert student embedding to numpy if needed
            if isinstance(student_embedding, (list, str)):
                student_embedding = self.json_to_embedding(student_embedding)
            
            if student_embedding is None:
                return {
                    'found': False,
                    'best_match_index': -1,
                    'best_similarity': 0.0,
                    'all_matches': [],
                    'total_faces': 0
                }
            
            # Detect all faces in group photo
            detected_faces = self.detect_all_faces(group_image_path)
            
            if len(detected_faces) == 0:
                return {
                    'found': False,
                    'best_match_index': -1,
                    'best_similarity': 0.0,
                    'all_matches': [],
                    'total_faces': 0
                }
            
            # Compare student embedding with each detected face
            matches = []
            best_match_idx = -1
            best_similarity = 0.0
            
            for embedding, face_image, bbox, face_idx in detected_faces:
                is_match, similarity = self.compare_faces(student_embedding, embedding, threshold=0.0)
                matches.append({
                    'index': face_idx,
                    'similarity': similarity,
                    'bbox': bbox,
                    'is_match': similarity >= threshold
                })
                
                # Track best match
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_idx = face_idx
            
            # Determine if student was found
            found = best_similarity >= threshold
            
            return {
                'found': found,
                'best_match_index': best_match_idx if found else -1,
                'best_similarity': float(best_similarity),
                'all_matches': matches,
                'total_faces': len(detected_faces)
            }
            
        except Exception as e:
            logger.error(f"Error finding student in group photo: {str(e)}")
            return {
                'found': False,
                'best_match_index': -1,
                'best_similarity': 0.0,
                'all_matches': [],
                'total_faces': 0
            }
    
    def annotate_group_photo(self, image_path, matches, output_path=None):
        """
        Annotate a group photo with bounding boxes and labels for matched faces.
        
        Args:
            image_path (str): Path to the group photo
            matches: List of match dictionaries from find_student_in_group
            output_path (str): Optional path to save annotated image
            
        Returns:
            str: Path to the annotated image
        """
        try:
            # Read the image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image at {image_path}")
            
            # Draw bounding boxes and labels
            for match in matches:
                bbox = match['bbox']
                similarity = match['similarity']
                is_match = match.get('is_match', False)
                face_idx = match['index']
                
                x1, y1, x2, y2 = bbox
                
                # Choose color: green for match, red for non-match
                color = (0, 255, 0) if is_match else (0, 0, 255)
                thickness = 3 if is_match else 2
                
                # Draw bounding box
                cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)
                
                # Add label
                student_name = match.get('student_name', '')
                label = f"Face {face_idx + 1}"
                if is_match:
                    if student_name:
                        label = f"{student_name} ({similarity:.3f})"
                    else:
                        label += f" MATCH ({similarity:.3f})"
                else:
                    label += f" ({similarity:.3f})"
                
                # Calculate text size and position
                (text_width, text_height), baseline = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                )
                
                # Draw text background
                cv2.rectangle(
                    image,
                    (x1, y1 - text_height - baseline - 5),
                    (x1 + text_width, y1),
                    color,
                    -1
                )
                
                # Draw text
                cv2.putText(
                    image,
                    label,
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )
            
            # Save annotated image
            if output_path is None:
                base_path = os.path.dirname(image_path)
                filename = os.path.basename(image_path)
                name, ext = os.path.splitext(filename)
                output_path = os.path.join(base_path, f"{name}_annotated{ext}")
            
            cv2.imwrite(output_path, image)
            logger.info(f"Annotated image saved to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error annotating group photo: {str(e)}")
            return None
    
    def compare_faces(self, embedding1, embedding2, threshold=0.6):
        """
        Compare two face embeddings using cosine similarity.
        
        Args:
            embedding1: numpy array or JSON-serialized embedding
            embedding2: numpy array or JSON-serialized embedding
            threshold: similarity threshold (default 0.6)
            
        Returns:
            tuple: (is_same_person, similarity_score)
        """
        try:
            # Convert to numpy if needed
            if isinstance(embedding1, (list, str)):
                embedding1 = self.json_to_embedding(embedding1)
            if isinstance(embedding2, (list, str)):
                embedding2 = self.json_to_embedding(embedding2)
            
            if embedding1 is None or embedding2 is None:
                return False, 0.0
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            )
            
            is_same = similarity >= threshold
            return is_same, float(similarity)
            
        except Exception as e:
            logger.error(f"Error comparing faces: {str(e)}")
            return False, 0.0

