FROM python:3.13-slim

# Install system-level dependencies required by mediapipe, deepface, and OpenCV headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer-cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Remove any GUI variant of OpenCV that may have been pulled in as a
# transitive dependency by deepface or mediapipe, then force-reinstall
# the headless variant so no X11/libxcb symbols are present at runtime.
RUN pip uninstall -y opencv-python opencv-contrib-python || true && \
    pip install --no-cache-dir --force-reinstall opencv-python-headless

# Copy application source
COPY bot.py .

CMD ["python", "bot.py"]
