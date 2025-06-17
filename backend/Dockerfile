FROM python:3.11-slim

# 1️⃣ system deps for Playwright
RUN apt-get update && apt-get install -y wget gnupg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 2️⃣ app deps
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# 3️⃣ install browser binaries
RUN playwright install --with-deps chromium

# 4️⃣ copy source
COPY backend/app /app/app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 