# step04_reconstruct.py
import numpy as np
import fix_numpy
class Step04Reconstructor:
    def __init__(self):
        pass

    def reconstruct(self, step3_results):
        """
        step3_results = [
            { "index": i, "text": "...", "bbox": [(x1,y1),(x2,y2),(x3,y3),(x4,y4)] }
        ]
        """
        structured = []

        for entry in step3_results:
            box = entry["bbox"]
            text = entry["text"]
            idx = entry["index"]

            # Convert quadrilateral to bounding rectangle
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]

            x = int(min(xs))
            y = int(min(ys))
            w = int(max(xs) - min(xs))
            h = int(max(ys) - min(ys))

            structured.append({
                "line_index": idx,
                "text": text,
                "bbox": {
                    "x": x, "y": y,
                    "w": w, "h": h,
                    "quad": box  # keep original too
                }
            })

        # Sort by vertical position → ensures correct reading order
        structured = sorted(structured, key=lambda x: x["bbox"]["y"])

        return { "lines": structured }
