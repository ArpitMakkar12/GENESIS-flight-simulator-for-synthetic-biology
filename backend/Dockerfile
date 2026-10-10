FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg2 and cobrapy
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    glpk-utils \
    libexpat1 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir -r requirements-ml.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
