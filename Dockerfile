# Используем официальный образ Python в качестве базового
FROM python:3.10-slim

# Установим зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Установим временную зону
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Установим необходимые Python пакеты
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Скопируем все файлы вашего проекта в контейнер
COPY . /app

# Установим рабочую директорию
WORKDIR /app

# Запустим скрипт при старте контейнера
CMD ["python", "main.py"]