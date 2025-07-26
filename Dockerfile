FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
# RUN apt-get update \
#     && apt-get install -y libpq-dev

COPY requirements.txt /app/
RUN pip install -r requirements.txt

COPY . /app/
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
