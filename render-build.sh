#!/usr/bin/env bash
# Xatolik bo'lsa to'xtash
set -o errexit

# Kutubxonalarni o'rnatish
pip install -r requirements.txt

# Statik fayllarni yig'ish
python manage.py collectstatic --no-input

# Bazani migratsiya qilish
python manage.py migrate