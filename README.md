# SUTRA Fashion — Django Project

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env   # edit .env with your settings

# 3. Run migrations
python manage.py migrate

# 4. Create admin (first-time only)
# Visit http://127.0.0.1:8000/admin-panel/register/
# OR use Django CLI:
python manage.py createsuperuser

# 5. Collect static files (production)
python manage.py collectstatic

# 6. Run development server
python manage.py runserver
```

## URLs
- **Store**: http://127.0.0.1:8000/
- **Store Admin Panel**: http://127.0.0.1:8000/admin-panel/
- **Django Admin**: http://127.0.0.1:8000/django-admin/
