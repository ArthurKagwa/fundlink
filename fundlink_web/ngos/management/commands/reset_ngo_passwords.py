from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ngos.models import NGO


class Command(BaseCommand):
    help = 'Reset passwords for all NGO users to "password1"'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which NGOs would be affected without making changes',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Get all NGOs that have associated users
        ngos_with_users = NGO.objects.filter(user__isnull=False).select_related('user')
        
        if not ngos_with_users.exists():
            self.stdout.write(self.style.WARNING('No NGOs with user accounts found.'))
            return
        
        if dry_run:
            self.stdout.write(self.style.NOTICE(f'DRY RUN: Would reset passwords for {ngos_with_users.count()} NGO users:'))
            for ngo in ngos_with_users:
                self.stdout.write(f'  - {ngo.name} (email: {ngo.email}, username: {ngo.user.username})')
            return
        
        # Confirm the action
        self.stdout.write(self.style.WARNING(f'This will reset passwords for {ngos_with_users.count()} NGO users to "password1".'))
        
        # Reset passwords
        updated_count = 0
        for ngo in ngos_with_users:
            ngo.user.set_password('password1')
            ngo.user.save()
            updated_count += 1
            self.stdout.write(f'  Reset password for {ngo.name} (email: {ngo.email})')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully reset passwords for {updated_count} NGO users.')
        )