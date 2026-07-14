FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY c4_project ./c4_project
COPY c4parser ./c4parser
COPY apps ./apps
COPY manage.py ./

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
