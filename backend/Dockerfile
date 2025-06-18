FROM python:3.11-slim

# 1️⃣ system deps for Playwright
RUN apt-get update && apt-get install -y wget gnupg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 2️⃣ create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# 3️⃣ app deps
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# 4️⃣ install browser binaries
RUN playwright install --with-deps chromium

# 5️⃣ copy source and set ownership
COPY app /app/app
RUN chown -R appuser:appuser /app

# 6️⃣ switch to non-root user
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 