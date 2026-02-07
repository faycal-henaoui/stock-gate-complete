from paddleocr import PaddleOCR
import fix_numpy

ocr = PaddleOCR(det=True, rec=True, lang='en')  # enable detection

result = ocr.ocr('test.jpg', det=True, rec=True)

for line in result:
    print(line)
