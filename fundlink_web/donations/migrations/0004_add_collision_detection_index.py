from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('donations', '0003_rename_donations_d_recipient_3d0e8d_idx_donations_d_recipie_6f0113_idx_and_more'),
    ]

    operations = [
        # Add database index for collision detection performance
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_donation_intent_collision_detection ON donations_donationintent (ngo_id, token, value_base_units, status, created_at) WHERE status = 'pending';",
            reverse_sql="DROP INDEX IF EXISTS idx_donation_intent_collision_detection;"
        ),
    ]