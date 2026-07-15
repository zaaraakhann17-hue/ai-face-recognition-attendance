FROM python:3.10-slim

WORKDIR /app

# Install Flask for the database microservice
RUN pip install --no-cache-dir --default-timeout=1000 Flask

# Copy strictly the database service folder contents into the workspace
COPY ./db_service .

EXPOSE 5002

CMD ["python", "db_app.py"]