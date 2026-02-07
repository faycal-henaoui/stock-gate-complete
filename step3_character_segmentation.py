# step03_character_segmentation.py
"""
Character segmentation for line crops (Option A).
Input: full invoice image + list of line bounding boxes (4-point polygons).
Output: for each line -> list of character images (numpy arrays) and their x-order boxes.

Algorithm:
 - Convert crop to grayscale and binarize (adaptive)
 - Option A (preferred): vertical projection (sum of pixels on columns) to find character cuts
 - Fallback: connected components on dilated image to extract cc bounding boxes
 - Return characters in left->right order
"""

import cv2
import numpy as np
from typing import List, Tuple

def order_box_points(box):
    # ensure box is in the shape [(x1,y1),(x2,y2),(x3,y3),(x4,y4)]
    return np.array(box, dtype=np.int32)

def crop_from_polygon(img: np.ndarray, poly: np.ndarray, pad: int = 2) -> np.ndarray:
    x_coords = poly[:,0]; y_coords = poly[:,1]
    x_min, x_max = int(x_coords.min()), int(x_coords.max())
    y_min, y_max = int(y_coords.min()), int(y_coords.max())
    h, w = img.shape[:2]
    x_min = max(0, x_min - pad); y_min = max(0, y_min - pad)
    x_max = min(w-1, x_max + pad); y_max = min(h-1, y_max + pad)
    return img[y_min:y_max, x_min:x_max]

def binarize(img_gray: np.ndarray) -> np.ndarray:
    # adaptive thresholding robust to lighting
    blur = cv2.GaussianBlur(img_gray, (3,3), 0)
    th = cv2.adaptiveThreshold(blur, 255,
                               cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY_INV, 15, 9)
    return th

def vertical_projection_cuts(bin_img: np.ndarray,
                             min_gap_width: int=2,
                             peak_prominence: float=0.15) -> List[int]:
    """
    Return x positions where to cut (between characters).
    Uses vertical pixel sums and finds valleys.
    """
    col_sums = np.sum(bin_img, axis=0) / 255.0  # how many black pixels per column
    # normalize
    if col_sums.max() > 0:
        col_norm = col_sums / (col_sums.max() + 1e-8)
    else:
        col_norm = col_sums

    # Smooth the signal
    kernel = np.ones(3) / 3.0
    smooth = np.convolve(col_norm, kernel, mode='same')

    # A valley is where smooth is below a threshold and sustained for some columns
    thresh = peak_prominence * smooth.max()
    valley_mask = smooth < thresh

    # find contiguous valley regions
    cuts = []
    start = None
    for i, v in enumerate(valley_mask):
        if v and start is None:
            start = i
        elif (not v) and start is not None:
            end = i - 1
            width = end - start + 1
            if width >= min_gap_width:
                cutpos = (start + end) // 2
                cuts.append(cutpos)
            start = None
    # end-case
    if start is not None:
        end = len(valley_mask) - 1
        if end - start + 1 >= min_gap_width:
            cuts.append((start + end)//2)

    # remove cuts too close to image borders
    h, w = bin_img.shape
    cuts = [c for c in cuts if 2 < c < w - 2]
    return cuts

def cuts_to_char_boxes(cuts: List[int], width: int) -> List[Tuple[int,int]]:
    """
    Given vertical cuts, produce list of (x_start, x_end) intervals for characters.
    """
    if len(cuts) == 0:
        return [(0, width)]
    # add edges
    edges = [0] + cuts + [width]
    boxes = []
    for i in range(len(edges)-1):
        x0 = edges[i]
        x1 = edges[i+1]
        # avoid empty boxes
        if x1 - x0 > 1:
            boxes.append((x0, x1))
    return boxes

def extract_char_images_from_line(line_img: np.ndarray,
                                  min_char_width: int = 5) -> List[Tuple[np.ndarray, Tuple[int,int]]]:
    """
    Given a line crop, return list of (char_image, (x0,x1)) in left->right order.
    """
    gray = cv2.cvtColor(line_img, cv2.COLOR_BGR2GRAY) if len(line_img.shape) == 3 else line_img
    bin_img = binarize(gray)

    # attempt vertical projection
    cuts = vertical_projection_cuts(bin_img, min_gap_width=2, peak_prominence=0.12)
    char_boxes = cuts_to_char_boxes(cuts, bin_img.shape[1])

    char_images = []
    for (x0, x1) in char_boxes:
        w = x1 - x0
        if w < min_char_width:
            continue
        char_crop = line_img[:, x0:x1]
        char_images.append((char_crop, (x0, x1)))

    # If segmentation produced 1 or 0 boxes for a long string, fallback to connected components
    if len(char_images) <= 1:
        char_images = extract_by_connected_components(bin_img, line_img, min_char_width)

    return char_images

def extract_by_connected_components(bin_img: np.ndarray, orig_img: np.ndarray,
                                    min_char_width: int = 5) -> List[Tuple[np.ndarray, Tuple[int,int]]]:
    # morphology to join character pieces
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    dil = cv2.dilate(bin_img, kernel, iterations=1)

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(dil, connectivity=8)
    boxes = []
    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]
        if w >= min_char_width and h >= 5 and area >= 10:
            boxes.append((x, x+w))

    # sort boxes left->right and produce crops
    boxes = sorted(boxes, key=lambda b: b[0])
    char_images = []
    for x0, x1 in boxes:
        char_crop = orig_img[:, x0:x1]
        char_images.append((char_crop, (x0, x1)))
    return char_images

def segment_line_boxes(image: np.ndarray, boxes: List[List[Tuple[int,int]]],
                       pad: int = 2) -> List[dict]:
    """
    For each polygonal box, crop and segment into characters.
    Returns list of dicts:
      {
        "box": original_box,
        "line_crop": numpy array,
        "chars": [
           { "img": numpy array, "x_range": (x0,x1), "index": i },
           ...
        ]
      }
    """
    results = []
    for box in boxes:
        poly = order_box_points(box)
        crop = crop_from_polygon(image, poly, pad=pad)
        chars = extract_char_images_from_line(crop)
        char_list = []
        for idx, (cimg, xr) in enumerate(chars):
            char_list.append({"img": cimg, "x_range": xr, "index": idx})
        results.append({"box": box, "line_crop": crop, "chars": char_list})
    return results

# Example debug run (only run when testing this file directly)
if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "/mnt/data/98a192dc-65a7-4bc4-bceb-e40a159b1e70.png"
    img = cv2.imread(path)
    # Example synthetic box covering center (use your step2 outputs in real use)
    h, w = img.shape[:2]
    sample_box = [[10,10],[w-10,10],[w-10,60],[10,60]]
    res = segment_line_boxes(img, [sample_box])
    print("Found chars per line:", [len(r['chars']) for r in res])

