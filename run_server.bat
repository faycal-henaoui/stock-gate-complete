@echo off
set PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
echo Starting Invoice Extraction API...
python api/main.py
pause