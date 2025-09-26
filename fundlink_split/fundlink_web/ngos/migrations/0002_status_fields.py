from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
from django.utils import timezone

def forwards(apps, schema_editor):
    NGO = apps.get_model('ngos', 'NGO')
    for ngo in NGO.objects.all():
        if ngo.approved:
            ngo.status = 'approved'
            ngo.approved_at = timezone.now()
        else:
            ngo.status = 'submitted'
        ngo.save()

def backwards(apps, schema_editor):
    # No-op revert: keep data
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('ngos', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='ngo',
            name='approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ngo',
            name='reviewed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_ngos', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='ngo',
            name='rejection_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='ngo',
            name='status',
            field=models.CharField(choices=[('submitted', 'Submitted'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='submitted', max_length=20),
        ),
        migrations.RunPython(forwards, backwards),
    ]
