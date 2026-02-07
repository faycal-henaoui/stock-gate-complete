# step03_svtr.py
import cv2
import fix_numpy
from paddleocr import PaddleOCR

class SVTRRecognizer:
    def __init__(self):
        print("[SVTR] Initializing OCR...")
        # PaddleOCR 2.8.1 compliant (Updated for v3+)
        self.ocr = PaddleOCR(use_angle_cls=False, lang='en')

    def recognize_lines(self, img, boxes):
        """
        Takes full image and list of boxes (from step 2),
        Crops each box, and runs recognition on it.
        """
        results = []
        for box in boxes:
             xs = [p[0] for p in box]
             ys = [p[1] for p in box]
             x1, y1 = int(min(xs)), int(min(ys))
             x2, y2 = int(max(xs)), int(max(ys))
             
             # Small padding
             h, w = img.shape[:2]
             x1 = max(0, x1-2)
             y1 = max(0, y1-2)
             x2 = min(w, x2+2)
             y2 = min(h, y2+2)

             crop = img[y1:y2, x1:x2]
             
             if crop.size == 0 or crop.shape[0] == 0 or crop.shape[1] == 0:
                 results.append("")
                 continue
                 
             try:
                 # Run Recognition Only (det=False, rec=True)
                 res = self.ocr.ocr(crop, det=False, rec=True, cls=False)
                 
                 text = ""
                 # Parse result structure: [ [('text', score)] ]
                 if res and isinstance(res, list) and len(res) > 0:
                     first_res = res[0] 
                     if first_res and isinstance(first_res, list) and len(first_res) > 0:
                         item = first_res[0] # ('text', score)
                         if isinstance(item, tuple) or isinstance(item, list):
                             # Return tuple (text, score)
                             results.append((item[0], item[1]))
                             continue
                             
                 results.append(("", 0.0))
             except Exception as e:
                 print(f"Rec Error: {e}")
                 results.append(("", 0.0))

        return results
