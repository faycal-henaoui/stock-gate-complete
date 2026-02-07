import cv2
import numpy as np
from typing import List, Tuple, Optional

# Tunable parameters
MIN_CHAR_WIDTH = 4           # smaller so slim letters (l, i) are kept
MIN_CHAR_HEIGHT_RATIO = 0.5  # char must be at least 50% of line height
NOISE_MIN_AREA = 25          # remove tiny blobs
VALLEY_PROM_RATIO = 0.06     # more sensitive splitting
VALLEY_MIN_GAP = 2
MERGE_GAP_PX = 2             # merge boxes that almost touch

def order_box_points(box):
    return np.array(box, dtype=np.int32)

def crop_from_polygon(img: np.ndarray, poly: np.ndarray, pad: int = 4) -> np.ndarray:
    x_coords = poly[:, 0]; y_coords = poly[:, 1]
    x_min, x_max = int(x_coords.min()), int(x_coords.max())
    y_min, y_max = int(y_coords.min()), int(y_coords.max())
    h, w = img.shape[:2]
    x_min = max(0, x_min - pad); y_min = max(0, y_min - pad)
    x_max = min(w - 1, x_max + pad); y_max = min(h - 1, y_max + pad)
    return img[y_min:y_max, x_min:x_max]

def to_gray(img):
    if img is None:
        return None
    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img

def robust_binarize(gray: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    th = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        15, 10
    )
    kernel_c = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel_c, iterations=1)
    nb, labels, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)
    res = np.zeros_like(closed)
    for i in range(1, nb):
        if stats[i, cv2.CC_STAT_AREA] >= NOISE_MIN_AREA:
            res[labels == i] = 255
    return res

def vertical_valley_cuts(bin_img: np.ndarray) -> List[int]:
    col_sums = np.sum(bin_img > 0, axis=0).astype(np.float32)
    if col_sums.max() == 0:
        return []
    col_sums /= (col_sums.max() + 1e-8)
    kernel = np.ones(3, dtype=np.float32) / 3.0
    smooth = np.convolve(col_sums, kernel, mode='same')
    thresh = VALLEY_PROM_RATIO * smooth.max()
    valley = smooth < thresh
    cuts = []
    start = None
    for i, v in enumerate(valley):
        if v and start is None:
            start = i
        elif not v and start is not None:
            end = i - 1
            if (end - start + 1) >= VALLEY_MIN_GAP:
                cuts.append((start + end) // 2)
            start = None
    if start is not None:
        end = len(valley) - 1
        if (end - start + 1) >= VALLEY_MIN_GAP:
            cuts.append((start + end) // 2)
    w = bin_img.shape[1]
    cuts = [c for c in cuts if 2 < c < w - 2]
    return cuts

def split_wide_region(bin_img: np.ndarray, x0: int, x1: int) -> List[Tuple[int, int]]:
    sub = bin_img[:, x0:x1]
    cuts = vertical_valley_cuts(sub)
    if not cuts:
        return [(x0, x1)]
    edges = [0] + cuts + [sub.shape[1]]
    boxes = []
    for i in range(len(edges) - 1):
        a = edges[i]; b = edges[i + 1]
        if (b - a) >= MIN_CHAR_WIDTH:
            boxes.append((x0 + a, x0 + b))
    return boxes or [(x0, x1)]

def extract_chars_from_line(line_img: np.ndarray) -> List[Tuple[np.ndarray, Tuple[int, int]]]:
    """Simpler vertical-projection splitter tuned for thin invoice fonts."""
    if line_img is None or line_img.size == 0:
        return []

    gray = to_gray(line_img)
    if gray is None:
        return []

    # Basic global binarization (inverse: text = white)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = bw.shape
    if w <= MIN_CHAR_WIDTH:
        return [(line_img, (0, w))]

    # 1D vertical projection
    proj = np.sum(bw, axis=0).astype(np.float32)
    if proj.max() == 0:
        return [(line_img, (0, w))]

    # Smooth to avoid micro-gaps
    k = max(3, w // 80)
    if k % 2 == 0:
        k += 1
    proj_smooth = cv2.GaussianBlur(proj.reshape(1, -1), (k, 1), 0).flatten()

    proj_norm = proj_smooth / (proj_smooth.max() + 1e-8)

    # Valleys are low-ink columns
    valley_thresh = 0.2
    valleys = np.where(proj_norm < valley_thresh)[0]

    gaps = []
    if len(valleys) > 0:
        start = valleys[0]
        prev = valleys[0]
        for x in valleys[1:]:
            if x == prev + 1:
                prev = x
            else:
                gaps.append((start, prev))
                start = x
                prev = x
        gaps.append((start, prev))

    cuts = []
    for g0, g1 in gaps:
        cx = (g0 + g1) // 2
        if MIN_CHAR_WIDTH <= cx <= w - MIN_CHAR_WIDTH:
            cuts.append(cx)
    cuts = sorted(set(cuts))

    xs = [0] + cuts + [w]

    intervals: List[Tuple[int, int]] = []
    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        if x1 - x0 >= MIN_CHAR_WIDTH:
            intervals.append((x0, x1))

    if not intervals:
        intervals = [(0, w)]

    chars: List[Tuple[np.ndarray, Tuple[int, int]]] = []
    for x0, x1 in intervals:
        crop = line_img[:, x0:x1]
        chars.append((crop, (int(x0), int(x1))))

    return chars


def split_by_recognized_text(line_img: np.ndarray, text: str) -> List[Tuple[np.ndarray, Tuple[int, int], str]]:
    """Split a word/line image into equal-width character crops using known text.

    Each output crop is paired with its character label from `text`.
    This is much more stable than purely geometric segmentation and is
    intended for building training data for a character CNN.
    """
    if line_img is None or line_img.size == 0:
        return []

    text = text or ""
    # Strip spaces at ends but keep internal spaces if they exist
    text = text.strip("\n\r")
    if len(text) == 0:
        return []

    h, w = line_img.shape[:2]
    n = len(text)
    if n == 0 or w < n:
        # too narrow; just return one crop with the whole text
        return [(line_img, (0, w), text)]

    # Compute equally spaced cut positions across width
    char_width = w / float(n)
    crops: List[Tuple[np.ndarray, Tuple[int, int], str]] = []
    for i, ch in enumerate(text):
        x0 = int(round(i * char_width))
        x1 = int(round((i + 1) * char_width))
        x0 = max(0, min(w - 1, x0))
        x1 = max(x0 + 1, min(w, x1))
        crop = line_img[:, x0:x1]
        crops.append((crop, (x0, x1), ch))

    return crops

def segment_line_boxes_v2(
    image: np.ndarray,
    boxes: List[List[Tuple[int, int]]],
    pad: int = 4,
    recognized_texts: Optional[List[str]] = None,
) -> List[dict]:
    results = []
    for idx_box, box in enumerate(boxes):
        poly = order_box_points(box)
        crop = crop_from_polygon(image, poly, pad=pad)
        char_list = []

        # If we have recognized text for this box, use it to split
        if recognized_texts is not None and idx_box < len(recognized_texts):
            txt = recognized_texts[idx_box]
            crops = split_by_recognized_text(crop, txt)
            if crops:
                for ci, (cimg, xr, ch) in enumerate(crops):
                    char_list.append({
                        "img": cimg,
                        "x_range": xr,
                        "index": ci,
                        "label": ch,
                        "source": "rec_text_split",
                    })
            else:
                # Fallback to geometric segmentation
                try:
                    chars = extract_chars_from_line(crop)
                except Exception:
                    h, w = crop.shape[:2]
                    chars = [(crop, (0, w))]
                for ci, (cimg, xr) in enumerate(chars):
                    char_list.append({
                        "img": cimg,
                        "x_range": xr,
                        "index": ci,
                        "source": "geom_fallback",
                    })
        else:
            # No recognized text provided: use geometric segmentation only
            try:
                chars = extract_chars_from_line(crop)
            except Exception:
                h, w = crop.shape[:2]
                chars = [(crop, (0, w))]
            for ci, (cimg, xr) in enumerate(chars):
                char_list.append({
                    "img": cimg,
                    "x_range": xr,
                    "index": ci,
                    "source": "geom_only",
                })
        results.append({"box": box, "line_crop": crop, "chars": char_list})
    return results