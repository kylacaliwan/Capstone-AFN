@echo off
cd /d d:\CAPSTONE\afn_service_management
py -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afn_service_management.settings'); import django; django.setup(); from users.models import User; u, c = User.objects.get_or_create(username='admin', defaults={'email':'admin@example.com', 'role':'admin', 'is_staff':True, 'is_superuser':True}); u.set_password('admin123'); u.save(); print('Admin user ready - username: admin, password: admin123')"
pause

