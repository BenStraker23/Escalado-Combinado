# Imagen para el microservicio
FROM python:3.10-slim

WORKDIR /app

COPY app.py /app
COPY requirements.txt /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
