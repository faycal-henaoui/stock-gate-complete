import sys, os
import shutil
import tempfile
import json
import fitz # PyMuPDF

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, UploadFile, File, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from pipeline import Pipeline
import os

# --- Security Config ---
API_KEY_NAME = "x-api-key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Get API Key from environment variable (or default for local test)
SERVER_API_KEY = os.getenv("OCR_API_KEY", "test_secret_key")

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == SERVER_API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate credentials")

app = FastAPI(title="Invoice Extraction API")
pipeline = Pipeline(debug_mode=False)

@app.get("/")
def read_root():
    return {"message": "Invoice Extraction API is running"}

@app.post("/extract")
async def extract_invoice(
    file: UploadFile = File(...), 
    api_key: str = Depends(get_api_key)
):
    try:
        # Create a temporary file to save the upload
        suffix = os.path.splitext(file.filename)[1].lower()
        if suffix not in [".jpg", ".jpeg", ".png", ".pdf"]:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            uploaded_path = tmp_file.name

        print(f"[API] Received file: {uploaded_path}")
        
        processing_path = uploaded_path
        
        # Helper: Convert PDF inside API if needed
        if suffix == ".pdf":
            print("[API] Converting PDF to Image...")
            try:
                doc = fitz.open(uploaded_path)
                if len(doc) < 1:
                    raise HTTPException(status_code=400, detail="Empty PDF")
                page = doc.load_page(0)
                pix = page.get_pixmap(dpi=300)
                
                # Save as PNG
                base_name = os.path.splitext(uploaded_path)[0]
                processing_path = f"{base_name}_converted.png"
                pix.save(processing_path)
                doc.close()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"PDF Conversion Failed: {str(e)}")

        # --- Run Pipeline Steps ---
        # Step 2: Detection
        s2 = pipeline.run_step2(processing_path)
        
        # Step 3: Recognition
        s3 = pipeline.run_step3_recognize(s2)
        
        # Step 4: Reconstruction
        s4 = pipeline.run_step4_reconstruct(s2, s3)
        
        # Step 5: Extraction (Dynamic + Innovative)
        final_result = pipeline.run_step5_extract(s4)
        
        # [OPTIMIZATION] Skipped PDF Report Generation for speed
        # The frontend only needs the JSON data.
        final_result["report_generated"] = False

        # Cleanup temp source files (optional, maybe keep for debug?)
        # os.remove(uploaded_path)

        return JSONResponse(content={"status": "success", "data": final_result})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

if __name__ == "__main__":
    import uvicorn
    # Run server
    uvicorn.run(app, host="0.0.0.0", port=8000)
