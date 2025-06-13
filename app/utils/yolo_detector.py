import cv2
import numpy as np
from ultralytics import YOLO
import os
from datetime import datetime
from flask import current_app

class YOLODetector:
    def __init__(self):
        """Initialize YOLO detector"""
        self._model = None
        
    @property
    def model(self):
        """Lazy load the YOLO model only when needed"""
        if self._model is None:
            self._model = YOLO('yolov8n.pt')
        return self._model
        
    def detect_people(self, image_path):
        """
        Detect people in an image using YOLO and return annotated image with count
        
        Args:
            image_path (str): Path to the input image
            
        Returns:
            tuple: (annotated_image_path, person_count, confidence_scores)
        """
        try:
            # Read the image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image at {image_path}")
            
            # Run YOLO detection
            results = self.model(image, classes=[0])  # class 0 is person in COCO dataset
            
            # Get detection results
            boxes = results[0].boxes
            person_count = len(boxes)
            confidence_scores = boxes.conf.tolist() if person_count > 0 else []
            
            # Draw bounding boxes and add count overlay
            annotated_img = results[0].plot()
            
            # Add count overlay
            cv2.putText(
                annotated_img,
                f'People Count: {person_count}',
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )
            
            # Save annotated image
            base_path = os.path.dirname(image_path)
            filename = os.path.basename(image_path)
            name, ext = os.path.splitext(filename)
            annotated_path = os.path.join(base_path, f"{name}_annotated{ext}")
            cv2.imwrite(annotated_path, annotated_img)
            
            return annotated_path, person_count, confidence_scores
            
        except Exception as e:
            current_app.logger.error(f"Error in YOLO detection: {str(e)}")
            return None, 0, []
            
    def compare_with_attendance(self, person_count, present_count):
        """
        Compare YOLO-detected count with recorded attendance
        
        Args:
            person_count (int): Number of people detected by YOLO
            present_count (int): Number of students marked as present
            
        Returns:
            tuple: (discrepancy, message)
        """
        discrepancy = abs(person_count - present_count)
        
        if discrepancy == 0:
            return (False, "YOLO count matches your attendance records.")
        else:
            if person_count > present_count:
                return (
                    True,
                    f"Discrepancy detected: YOLO counted {person_count} people, but {present_count} students marked present. " +
                    f"Difference of {discrepancy} people. You may have missed marking some students present."
                )
            else:
                return (
                    True,
                    f"Discrepancy detected: YOLO counted {person_count} people, but {present_count} students marked present. " +
                    f"Difference of {discrepancy} people. Some marked students may not be visible in the image."
                )