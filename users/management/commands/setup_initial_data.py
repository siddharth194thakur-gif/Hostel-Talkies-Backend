import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from hostels.models import Hostel, Block, Room
from posts.models import Category

User = get_user_model()

class Command(BaseCommand):
    help = 'Automatically seeds default superuser admin, campus hostels, and categories on Render deploy'

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

        # Create comprehensive standard categories for campus hostel life
        default_categories = [
            {'name': 'Electronics & Gadgets', 'icon': 'laptop', 'post_type': 'all'},
            {'name': 'Books, Notes & PYQs', 'icon': 'book', 'post_type': 'all'},
            {'name': 'Cycles & Mobility', 'icon': 'bicycle', 'post_type': 'all'},
            {'name': 'Room Essentials & Decor', 'icon': 'home', 'post_type': 'all'},
            {'name': 'Study Desks & Furniture', 'icon': 'armchair', 'post_type': 'all'},
            {'name': 'Lab Gear & Uniforms', 'icon': 'shirt', 'post_type': 'all'},
            {'name': 'Sports & Fitness Equipment', 'icon': 'dumbbell', 'post_type': 'all'},
            {'name': 'Mess & Kitchen Appliances', 'icon': 'utensils', 'post_type': 'all'},
            {'name': 'Lost & Found Items', 'icon': 'search', 'post_type': 'all'},
            {'name': 'Roommate & Accommodation', 'icon': 'users', 'post_type': 'all'},
            {'name': 'General Campus Talkies', 'icon': 'sparkles', 'post_type': 'all'},
        ]

        for cat_data in default_categories:
            slug = slugify(cat_data['name'])
            category, cat_created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'slug': slug,
                    'icon': cat_data['icon'],
                    'post_type': cat_data['post_type'],
                    'is_active': True
                }
            )
            if cat_created:
                self.stdout.write(self.style.SUCCESS(f"Category '{category.name}' created."))
