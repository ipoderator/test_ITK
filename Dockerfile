FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ=Europe/Moscow

# Устанавливаем tzdata для поддержки часовых поясов
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && \
    rm -rf /var/lib/apt/lists/* && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

WORKDIR /app

COPY requirements.txt .

RUN echo "Установка зависимостей..." && \
    pip install --no-cache-dir -r requirements.txt && \
    echo "Зависимости установлены успешно"

RUN mkdir -p /app/logs

COPY main.py schemas.py storage.py database.py ./

EXPOSE 8000

# Команда для запуска приложения (будет переопределена в docker-compose для hot reload)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]

