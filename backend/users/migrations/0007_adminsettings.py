from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_alter_user_admin_scope_alter_user_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('system_name', models.CharField(default='AFN Service Management', max_length=255)),
                ('support_email', models.EmailField(default='support@afnservice.com', max_length=254)),
                ('enable_notifications', models.BooleanField(default=True)),
                ('auto_dispatch_enabled', models.BooleanField(default=False)),
                ('sms_notifications_enabled', models.BooleanField(default=False)),
                ('default_time_zone', models.CharField(default='UTC', max_length=100)),
                ('max_technician_assignments', models.PositiveSmallIntegerField(default=5)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='admin_settings_updates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Admin Settings',
                'verbose_name_plural': 'Admin Settings',
            },
        ),
    ]
