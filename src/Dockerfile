# Dockerfile
# Използваме официален Python образ
FROM python:3.10-slim-buster

# Задаваме работна директория
WORKDIR /app

# Копираме requirements.txt и инсталираме зависимостите
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копираме целия код на приложението
COPY src/main.py .

# Задаваме порта, на който Uvicorn ще слуша (Cloud Run автоматично задава PORT променлива)
ENV PORT 8080

# Команда за стартиране на Uvicorn сървъра
# --host 0.0.0.0 е критично за Cloud Run, за да слуша на всички интерфейси
# src.main:app - указва, че приложението е в main.py (или src/main.py, ако го оставим в src/) и променливата "app"
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT
