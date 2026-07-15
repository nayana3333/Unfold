from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class Command(BaseCommand):
    help = 'Deletes all user accounts except the one specified by email'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email of the user to keep')

    def handle(self, *args, **options):
        email = options.get('email')
        
        if not email:
            self.stdout.write(self.style.ERROR('Please provide an email address using --email parameter'))
            return

        try:
            user_to_keep = User.objects.get(email=email)
            
            # Get all users except the one to keep
            users_to_delete = User.objects.exclude(email=email)
            count = users_to_delete.count()
            
            if count == 0:
                self.stdout.write(self.style.SUCCESS('No other user accounts found to delete.'))
                return
                
            # Confirm before deletion
            confirm = input(f'Are you sure you want to delete {count} user(s) except {email}? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('Operation cancelled.'))
                return
                
            # Delete users
            deleted_count, _ = users_to_delete.delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} user(s)'))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User with email {email} does not exist'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred: {str(e)}'))
