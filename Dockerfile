# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем переменные окружения для логирования
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ=Europe/Moscow

# Устанавливаем tzdata для поддержки часовых поясов
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && \
    rm -rf /var/lib/apt/lists/* && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости с логированием
RUN echo "📦 Установка зависимостей..." && \
    pip install --no-cache-dir -r requirements.txt && \
    echo "✅ Зависимости установлены успешно"

# Создаем директорию для логов
RUN mkdir -p /app/logs

# Копируем все файлы приложения
COPY main.py schemas.py storage.py database.py ./

# Открываем порт 8000
EXPOSE 8000

# Команда для запуска приложения (будет переопределена в docker-compose для hot reload)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]

