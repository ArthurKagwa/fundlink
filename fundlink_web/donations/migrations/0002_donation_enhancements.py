# Generated manually for donation intents and extended donation metadata

from django.db import migrations, models
import django.db.models.deletion
import donations.models


class Migration(migrations.Migration):

    dependencies = [
        ('donations', '0001_initial'),
        ('campaigns', '0001_initial'),
        ('ngos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='donation',
            name='block_number',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='donation',
            name='recipient_address',
            field=models.CharField(blank=True, max_length=42),
        ),
        migrations.AddField(
            model_name='donation',
            name='sender_address',
            field=models.CharField(blank=True, max_length=42),
        ),
        migrations.AddField(
            model_name='donation',
            name='tx_timestamp',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='donation',
            name='value_base_units',
            field=models.DecimalField(blank=True, decimal_places=0, max_digits=78, null=True),
        ),
        migrations.AlterField(
            model_name='donation',
            name='tx_hash',
            field=models.CharField(blank=True, max_length=66, null=True, unique=True),
        ),
        migrations.CreateModel(
            name='DonationIntent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference', models.CharField(default=donations.models._default_reference, max_length=36, unique=True)),
                ('token', models.CharField(choices=[('AVAX', 'AVAX'), ('USDT', 'USDT')], max_length=10)),
                ('token_decimals', models.PositiveSmallIntegerField(default=18)),
                ('amount_decimal', models.DecimalField(decimal_places=6, max_digits=20)),
                ('value_base_units', models.DecimalField(decimal_places=0, max_digits=78)),
                ('wallet_address', models.CharField(max_length=42)),
                ('donor_telegram_id', models.BigIntegerField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('fulfilled', 'Fulfilled'), ('expired', 'Expired')], default='pending', max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('fulfilled_at', models.DateTimeField(blank=True, null=True)),
                ('bot_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='donation_intents', to='donations.botuser')),
                ('campaign', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='donation_intents', to='campaigns.campaign')),
                ('ngo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='donation_intents', to='ngos.ngo')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='donation',
            name='intent',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='donation', to='donations.donationintent'),
        ),
        migrations.AddIndex(
            model_name='donation',
            index=models.Index(fields=['recipient_address', 'created_at'], name='donations_d_recipient_3d0e8d_idx'),
        ),
        migrations.AddIndex(
            model_name='donationintent',
            index=models.Index(fields=['wallet_address', 'status', 'token'], name='donationin_wallet__69ab82_idx'),
        ),
        migrations.AddIndex(
            model_name='donationintent',
            index=models.Index(fields=['donor_telegram_id', 'status'], name='donationin_donor_t_6bc256_idx'),
        ),
    ]
