from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_adminsettings'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserCapabilityGrant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('capability_code', models.CharField(max_length=100)),
                ('granted_at', models.DateTimeField(auto_now_add=True)),
                ('granted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='granted_capability_records', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='capability_grants', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Capability Grant',
                'verbose_name_plural': 'User Capability Grants',
                'ordering': ['capability_code', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='usercapabilitygrant',
            constraint=models.UniqueConstraint(fields=('user', 'capability_code'), name='unique_user_capability_grant'),
        ),
    ]
