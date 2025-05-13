#!/bin/bash

# Активация виртуального окружения
source venv/bin/activate

# Установка зависимостей
pip install django djangorestframework PyJWT PyPDF2 pdfminer.six pillow pytesseract

# Создание необходимых директорий
mkdir -p media
mkdir -p static

# Миграции базы данных
python manage.py makemigrations
python manage.py migrate

# Проверка наличия суперпользователя
echo "Проверка наличия суперпользователя..."
if python -c "import django; django.setup(); from django.contrib.auth.models import User; exit(0 if User.objects.filter(is_superuser=True).exists() else 1)"; then
    echo "Суперпользователь уже существует"
else
    echo "Создание суперпользователя..."
    python manage.py createsuperuser
fi

# Запуск сервера
echo "Запуск сервера Django..."
python manage.py runserver 