FROM python:3.10-bullseye

# 1. Установка системных зависимостей
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

# 2. Установка Python-зависимостей
COPY requirements.txt .
RUN pip install attrdict3
RUN pip install --no-cache-dir \
    -r requirements.txt \
    -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/debian-11

# 3. Настройка рабочей директории
WORKDIR /app
COPY . .

# 4. Открытие порта и запуск
EXPOSE 5000
CMD ["python", "app.py"]