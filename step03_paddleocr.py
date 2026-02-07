import cv2
import numpy as np
from paddleocr import PaddleOCR
from paddleocr.ppocr.utils.utility import get_rotate_crop_image


class PaddleLineRecognizer:
    def __init__(self):
        self.ocr = PaddleOCR(
            use_angle_cls=False,
            lang='en',
            det=False,          # only recognition
            rec=True,
            show_log=False
        )

    def recognize_lines(self, img, line_boxes):
        results = []

        for idx, box in enumerate(line_boxes):
            # box must be float32
            pts = np.array(box).astype(np.float32)

            # rotated crop
            crop = get_rotate_crop_image(img, pts)

            # run OCR
            rec = self.ocr.ocr(crop, det=False, rec=True)
            text = rec[0][0][0] if len(rec) > 0 else ""

            results.append({
                "index": idx,
                "text": text,
                "crop": crop
            })

        return results
