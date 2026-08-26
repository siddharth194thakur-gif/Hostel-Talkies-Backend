from django.db import migrations

def update_admin_names(apps, schema_editor):
    User = apps.get_model('users', 'User')
    User.objects.filter(email='admin@hosteltalkies.com').update(first_name='Admin', last_name='')
    User.objects.filter(first_name='Chief', last_name__in=['Warden', 'Administrator']).update(first_name='Admin', last_name='')

def rollback_admin_names(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_userblock'),
    ]

    operations = [
        migrations.RunPython(update_admin_names, rollback_admin_names),
    ]
