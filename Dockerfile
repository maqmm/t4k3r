# ============================================
# ЭТАП 1: СБОРКА (builder)
# ============================================
FROM python:3.10-slim AS builder

# Устанавливаем только инструменты сборки
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Копируем только requirements.txt для установки зависимостей
COPY requirements.txt .

# Устанавливаем Python пакеты в отдельную директорию
RUN pip install --user --no-cache-dir -r requirements.txt

# ============================================
# ЭТАП 2: ФИНАЛЬНЫЙ ОБРАЗ (runtime)
# ============================================
FROM python:3.10-slim

# Устанавливаем только runtime зависимости (без gcc)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем временную зону
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Копируем установленные Python пакеты из builder
COPY --from=builder /root/.local /root/.local

# Обновляем PATH для пользовательских пакетов
ENV PATH=/root/.local/bin:$PATH

# Копируем проект (с учетом .dockerignore)
COPY . /app

# Устанавливаем рабочую директорию
WORKDIR /app

# Запускаем скрипт
CMD ["python", "main.py"]