# utils/image_utils.py
import cv2
import numpy as np

def draw_boxes(img, boxes, color=(0,255,0), thickness=2):
    out = img.copy()
    for box in boxes:
        pts = np.array(box, np.int32).reshape((-1,1,2))
        cv2.polylines(out, [pts], isClosed=True, color=color, thickness=thickness)
    return out

def save_img(path, img):
    cv2.imwrite(path, img)

def show_img_win(title, img, scale=1.0):
    # For quick local debugging (not for headless servers)
    h, w = img.shape[:2]
    resized = cv2.resize(img, (int(w*scale), int(h*scale)))
    cv2.imshow(title, resized)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
