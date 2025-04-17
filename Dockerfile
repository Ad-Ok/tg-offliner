FROM python:3.9-slim-bullseye

# 1. Установка корректных зависимостей для wxPython 4.2.0
RUN apt-get update && apt-get install -y \
    build-essential \
    libgtk-3-dev \
    libwebkit2gtk-4.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libnotify-dev \
    freeglut3-dev \
    libsdl2-dev \
    libjpeg-dev \
    libtiff-dev \
    libsm-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install attrdict3
# 2. Установка wxPython с официального репозитория
RUN pip install --no-cache-dir \
    -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/debian-11 \
    wxPython==4.2.0

# 3. Остальные пакеты
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app
COPY . .

# Открываем порт для Flask
EXPOSE 5000

CMD ["python", "app.py"]

