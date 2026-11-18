FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TZ=Asia/Seoul
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY korail2/ korail2/
COPY notifier/ notifier/

RUN useradd --create-home app
USER app

CMD ["python", "-m", "notifier"]
