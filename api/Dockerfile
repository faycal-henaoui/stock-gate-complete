# Use official lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for OpenCV and Paddle
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
# Note: Installing paddlepaddle-gpu is large. 
# For standard cloud hosting (cpu), use paddlepaddle
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install paddlepaddle==2.6.0  

# Copy the entire project context (respecting .dockerignore)
COPY . .

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
