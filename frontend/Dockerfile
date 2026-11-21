FROM python:3.12-slim
WORKDIR /app
COPY frontend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY frontend /app/frontend
ENV PYTHONPATH=/app
CMD ["streamlit", "run", "frontend/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
