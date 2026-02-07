
try:
    import pdf2image
    print("pdf2image available")
except ImportError:
    print("pdf2image NOT available")

try:
    import fitz
    print("fitz (PyMuPDF) available")
except ImportError:
    print("fitz NOT available")
