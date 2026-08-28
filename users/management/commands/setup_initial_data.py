import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from hostels.models import Hostel, Block, Room

User = get_user_model()

class Command(BaseCommand):
    help = 'Automatically seeds default superuser admin and campus hostels on Render deploy'

    def handle(self, *args, **options):
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@hosteltalkies.com').strip().lower()
        admin_password = os.environ.get('ADMIN_PASSWORD', 'Admin@HostelTalkies2026').strip()
        admin_username = 'admin'

        if not User.objects.filter(email=admin_email).exists():
            User.objects.create_superuser(
                username=admin_username,
                email=admin_email,
                password=admin_password,
                first_name='HostelTalkies',
                last_name='Admin',
                is_staff=True,
                is_superuser=True,
                is_student=False
            )
            self.stdout.write(self.style.SUCCESS(f"Superuser '{admin_email}' created successfully."))
        else:
            self.stdout.write(f"Superuser '{admin_email}' already exists.")

        # Create standard initial hostels if empty
        default_hostels = [
            {'name': 'VISHWAKARMA HOSTEL', 'code': 'VK-HOSTEL', 'gender': 'boys'},
            {'name': 'ARYABHATTA HOSTEL', 'code': 'AB-HOSTEL', 'gender': 'boys'},
            {'name': 'KALPANA CHAWLA HOSTEL', 'code': 'KC-HOSTEL', 'gender': 'girls'},
            {'name': 'SAROJINI NAIDU HOSTEL', 'code': 'SN-HOSTEL', 'gender': 'girls'},
            {'name': 'TAGORE HOSTEL', 'code': 'TG-HOSTEL', 'gender': 'coed'},
        ]

        for h in default_hostels:
            hostel, created = Hostel.objects.get_or_create(
                name=h['name'],
                defaults={'code': h['code'], 'gender': h['gender'], 'is_active': True}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Hostel '{hostel.name}' created."))
                for b_name in ['Block A', 'Block B', 'Block C']:
                    block, _ = Block.objects.get_or_create(hostel=hostel, name=b_name)
                    for r_num in ['101', '102', '103', '201', '202']:
                        Room.objects.get_or_create(block=block, room_number=r_num)
