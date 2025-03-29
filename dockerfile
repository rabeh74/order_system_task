FROM python:3.12.0-slim

LABEL maintainer="rabehrabie"
ENV PYTHONUNBUFFERED=1

COPY ./app /app
COPY ./requirements.txt /app/requirements.txt

EXPOSE 8000
WORKDIR /app

RUN pip install --upgrade pip --no-cache-dir && \
    pip install -r requirements.txt --no-cache-dir && \
    # Create a system user without a home directory
    useradd -r django-user --no-create-home && \
    # Create directories for media and static files
    mkdir -p /vol/web/media /vol/web/static && \
    chown -R django-user:django-user /vol && \
    chmod -R 755 /vol

USER django-user