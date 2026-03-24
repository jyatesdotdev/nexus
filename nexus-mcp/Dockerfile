FROM python:3.14-slim

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Change ownership of the app directory to the non-root user
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["python", "server.py"]
