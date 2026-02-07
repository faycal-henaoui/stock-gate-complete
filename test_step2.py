import sys
import cv2
from step2_line_detection import LineDetectionStep

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_step2.py <image_path>")
        return

    image_path = sys.argv[1]
    step = LineDetectionStep()
    result = step.run(image_path)

    boxes = result["boxes"]
    print(f"[TEST] Detected {len(boxes)} lines")

    img = cv2.imread(image_path)
    for box in boxes:
        pts = [(int(p[0]), int(p[1])) for p in box]
        for i in range(4):
            cv2.line(img, pts[i], pts[(i + 1) % 4], (0, 255, 0), 2)

    cv2.imshow("Step 2 - Detected Lines", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()