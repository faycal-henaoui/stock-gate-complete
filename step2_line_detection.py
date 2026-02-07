# step2_line_detection.py
import cv2
import fix_numpy
from paddleocr import PaddleOCR
import numpy as np

class LineDetectionStep:
    def __init__(self):
        print("[Step2] Initializing PaddleOCR for Detection...")
        # PaddleOCR 2.8.1 compliant (Updated for v3+)
        self.ocr = PaddleOCR(use_angle_cls=False, lang='en')

    def run(self, img_path):
        """
        Returns dict with "boxes" and "crops"
        """
        print(f"[Step2] Processing: {img_path}")
        img = cv2.imread(img_path)
        if img is None:
            print("Error: Could not read image")
            return {"boxes": [], "crops": []}
            
        # Run detection (handle PaddleOCR API differences)
        try:
            # Older API
            result = self.ocr.ocr(img, det=True, rec=False, cls=False)
        except TypeError:
            try:
                # Newer API (det/rec args removed)
                result = self.ocr.ocr(img, cls=False)
            except TypeError:
                # Newest API (no kwargs)
                result = self.ocr.ocr(img)
        
        boxes = []
        if result and result[0] is not None:
             first = result[0]
             # If result is list of boxes: [[x,y],...]
             if first and isinstance(first[0], list) and len(first[0]) == 4:
                 boxes = first
             else:
                 # If result is list of [box, (text, score)]
                 boxes = [item[0] for item in first if isinstance(item, list) and item]

        # Generate crops
        crops = []
        for box in boxes:
             # box is [[x,y], [x,y], [x,y], [x,y]]
             xs = [p[0] for p in box]
             ys = [p[1] for p in box]
             x1, y1 = int(min(xs)), int(min(ys))
             x2, y2 = int(max(xs)), int(max(ys))
             
             # Safety check
             h, w = img.shape[:2]
             x1 = max(0, x1)
             y1 = max(0, y1)
             x2 = min(w, x2)
             y2 = min(h, y2)
             
             crop = img[y1:y2, x1:x2]
             crops.append(crop)

        return {
            "boxes": boxes, # List of boxes
            "crops": crops, # List of crop images (numpy arrays)
        }
