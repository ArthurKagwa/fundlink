from django.core.management.base import BaseCommand
from django.contrib.auth import authenticate
from ngos.models import NGO


class Command(BaseCommand):
    help = 'Verify that NGO passwords have been reset to "password1"'
    
    def handle(self, *args, **options):
        ngos_with_users = NGO.objects.filter(user__isnull=False).select_related('user')
        
        if not ngos_with_users.exists():
            self.stdout.write(self.style.WARNING('No NGOs with user accounts found.'))
            return
        
        self.stdout.write(f'Verifying passwords for {ngos_with_users.count()} NGO users:')
        
        success_count = 0
        for ngo in ngos_with_users:
            # Try to authenticate with the reset password
            user = authenticate(username=ngo.user.username, password='password1')
            if user is not None:
                self.stdout.write(self.style.SUCCESS(f'  ✓ {ngo.name} (email: {ngo.email}) - Password verified'))
                success_count += 1
            else:
                self.stdout.write(self.style.ERROR(f'  ✗ {ngo.name} (email: {ngo.email}) - Password verification failed'))
        
        if success_count == ngos_with_users.count():
            self.stdout.write(self.style.SUCCESS(f'\nAll {success_count} NGO passwords successfully verified!'))
        else:
            self.stdout.write(self.style.WARNING(f'\n{success_count}/{ngos_with_users.count()} passwords verified successfully.'))