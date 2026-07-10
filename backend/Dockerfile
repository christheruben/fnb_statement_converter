FROM python:3.11-slim

WORKDIR /app

# System dependencies required by camelot-py[cv] and opencv-python:
# - ghostscript: actual binary needed for PDF table extraction (the pip
#   package "ghostscript" is only a Python wrapper around this)
# - libgl1, libglib2.0-0: required by opencv-python at import time on
#   slim/Debian images (missing libGL.so.1 is the classic failure here)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ghostscript \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]