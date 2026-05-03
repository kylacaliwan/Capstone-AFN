from django.db import migrations, models


def promote_bootstrap_owner(apps, schema_editor):
    User = apps.get_model('users', 'User')

    if User.objects.filter(role='superadmin').exists():
        return

    superuser_admins = User.objects.filter(role='admin', is_superuser=True).order_by('id')
    if superuser_admins.count() == 1:
        owner = superuser_admins.first()
        owner.role = 'superadmin'
        owner.save(update_fields=['role'])
        return

    admins = User.objects.filter(role='admin').order_by('id')
    if admins.count() == 1:
        owner = admins.first()
        owner.role = 'superadmin'
        owner.save(update_fields=['role'])


def demote_promoted_owner(apps, schema_editor):
    User = apps.get_model('users', 'User')
    if User.objects.filter(role='superadmin').count() == 1 and not User.objects.filter(role='admin').exists():
        owner = User.objects.filter(role='superadmin').first()
        owner.role = 'admin'
        owner.save(update_fields=['role'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_alter_user_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('superadmin', 'Superadmin'),
                    ('admin', 'Admin'),
                    ('follow_up', 'Service Follow-Up'),
                    ('supervisor', 'Supervisor'),
                    ('technician', 'Technician'),
                    ('client', 'Client'),
                ],
                default='client',
                max_length=20,
            ),
        ),
        migrations.RunPython(promote_bootstrap_owner, demote_promoted_owner),
    ]
