# Generated migration for session management fields
# Run: python manage.py makemigrations whatsappplugin1 --name add_session_management

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('whatsappplugin1', '0001_initial'),  # Replace with your latest migration
    ]

    operations = [
        migrations.AddField(
            model_name='whatsappplugin1usersession',
            name='current_session_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='whatsappplugin1usersession',
            name='last_activity_time',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='whatsappplugin1usersession',
            name='session_start_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='whatsappplugin1usersession',
            name='is_new_session_pending',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='whatsappplugin1usersession',
            name='conversation_sessions',
            field=models.JSONField(blank=True, default=list, help_text="Stores summaries of previous conversation sessions"),
        ),
        migrations.AddField(
            model_name='whatsappplugin1usersession',
            name='current_session_context',
            field=models.JSONField(blank=True, default=dict, help_text="Important context for current session"),
        ),
    ]