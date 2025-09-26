from decimal import Decimal

from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from campaigns.models import Campaign
from donations.models import DonationIntent, Donation
from ngos.models import NGO


def _make_wallet(prefix: str = 'a') -> str:
    return '0x' + (prefix * 40)


@override_settings(INTERNAL_API_KEY='test-internal-key')
class DonationIntentViewTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        settings.INTERNAL_API_KEY = 'test-internal-key'
        assert getattr(settings, 'INTERNAL_API_KEY') == 'test-internal-key'
        self.ngo = NGO.objects.create(
            name='Relief Org',
            email='relief@example.com',
            wallet_address=_make_wallet('1'),
            description='Helping communities',
            status=NGO.STATUS_APPROVED,
            approved=True,
        )
        self.campaign = Campaign.objects.create(
            ngo=self.ngo,
            title='Flood Response',
            description='Support victims of flooding in the region.',
            status=Campaign.STATUS_APPROVED,
            token_options=['AVAX', 'USDT'],
            min_amount=Decimal('0.0001'),
        )

    def test_create_intent_and_confirm_donation(self):
        payload = {
            'campaign_id': self.campaign.id,
            'token': 'AVAX',
            'amount_decimal': '0.100000',
            'value_base_units': str(int(Decimal('0.1') * (Decimal(10) ** 18))),
            'donor_telegram_id': 123456789,
            'telegram_username': 'donor',
        }
        response = self.client.post(
            '/api/donations/intents/',
            payload,
            format='json',
            HTTP_X_INTERNAL_KEY='test-internal-key',
        )
        self.assertEqual(response.status_code, 201)
        reference = response.json()['reference']

        intent = DonationIntent.objects.get(reference=reference)
        self.assertEqual(intent.ngo, self.ngo)
        self.assertEqual(intent.campaign, self.campaign)
        self.assertEqual(intent.token, 'AVAX')
        self.assertEqual(intent.value_base_units, Decimal(payload['value_base_units']))

        confirm_payload = {
            'tx_hash': '0x' + 'f' * 64,
            'chain_id': 43113,
            'token': 'AVAX',
            'value_base_units': payload['value_base_units'],
            'from_address': _make_wallet('2'),
            'to_address': self.ngo.wallet_address,
            'block_number': 12345,
            'timestamp': timezone.now().isoformat(),
            'intent_reference': reference,
        }
        confirm_response = self.client.post(
            '/api/donations/confirm/',
            confirm_payload,
            format='json',
            HTTP_X_INTERNAL_KEY='test-internal-key',
        )
        self.assertEqual(confirm_response.status_code, 201)
        donation_payload = confirm_response.json()['donation']
        self.assertEqual(donation_payload['token'], 'AVAX')
        self.assertEqual(donation_payload['ngo']['id'], self.ngo.id)
        self.assertEqual(donation_payload['campaign']['id'], self.campaign.id)
        self.assertEqual(donation_payload['intent_reference'], reference)

        donation = Donation.objects.get(tx_hash=confirm_payload['tx_hash'])
        self.assertTrue(donation.is_confirmed)
        self.assertEqual(donation.intent.reference, reference)

        # Reconfirming should return existing donation and not create duplicates
        confirm_again = self.client.post(
            '/api/donations/confirm/',
            confirm_payload,
            format='json',
            HTTP_X_INTERNAL_KEY='test-internal-key',
        )
        self.assertEqual(confirm_again.status_code, 200)
        self.assertEqual(Donation.objects.count(), 1)

    def test_list_intents_filters_status(self):
        DonationIntent.objects.create(
            reference='abc',
            ngo=self.ngo,
            campaign=self.campaign,
            token='AVAX',
            token_decimals=18,
            amount_decimal=Decimal('0.050000'),
            value_base_units=Decimal(50000000000000000),
            wallet_address=self.ngo.wallet_address,
        )
        response = self.client.get(
            '/api/donations/intents/list/?status=pending',
            HTTP_X_INTERNAL_KEY='test-internal-key',
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['token'], 'AVAX')
