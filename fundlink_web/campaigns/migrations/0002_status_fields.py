from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

def forwards(apps, schema_editor):
    Campaign = apps.get_model('campaigns', 'Campaign')
    for c in Campaign.objects.all():
        if c.published and c.active:
            c.status = 'approved'
        else:
            c.status = 'draft'
        c.save()

def backwards(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('campaigns', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='campaign',
            name='rejection_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='campaign',
            name='reviewed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_campaigns', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='campaign',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='draft', max_length=20),
        ),
        migrations.AddField(
            model_name='campaign',
            name='submitted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(forwards, backwards),
    ]
