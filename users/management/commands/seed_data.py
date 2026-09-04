from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal

from users.models import StudentProfile
from hostels.models import Hostel, Block, Room
from posts.models import Category, Post, PostImage, Comment, Like, SavedPost, BorrowRequest
from notices.models import Notice
from events.models import Event
from services.models import HostelService
from study.models import StudyResource
from messaging.models import Conversation, Message
from notifications.models import Notification
from moderation.models import SiteSetting, Report, Feedback

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds database with realistic HostelTalkies initial data and demo accounts'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding HostelTalkies database..."))

        # 1. Site Settings
        SiteSetting.objects.get_or_create(
            id=1,
            defaults={
                'site_name': 'HostelTalkies',
                'tagline': 'Your Hostel. Your People. Your Talkies.',
                'community_rules': '1. Be respectful to fellow hostelers\n2. Genuine student items only\n3. Return borrowed items on time\n4. Report lost items with precise location details\n5. Follow campus & hostel ethics',
                'guidelines': 'Welcome to HostelTalkies! A private community for hostel residents to trade, help, coordinate, and connect.',
                'contact_email': 'support@hosteltalkies.edu',
                'maintenance_mode': False
            }
        )

        # 2. Hostels, Blocks, Rooms
        hostel_data = [
            {
                'name': 'Aryabhata Hostel',
                'code': 'HOSTEL-A',
                'description': 'Senior Boys Hostel near West Academic Block',
                'gender': 'boys',
                'warden_name': 'Dr. K. S. Sharma',
                'warden_contact': 'warden.aryabhata@campus.edu',
                'blocks': [
                    {'name': 'Block A1', 'floors': 4, 'rooms': ['101', '102', '103', '201', '202', '301', '401']},
                    {'name': 'Block A2', 'floors': 4, 'rooms': ['104', '105', '203', '204', '302', '402']},
                ]
            },
            {
                'name': 'Bhaskara Hostel',
                'code': 'HOSTEL-B',
                'description': 'Junior Boys Hostel equipped with study lounges & recreation rooms',
                'gender': 'boys',
                'warden_name': 'Prof. A. R. Verma',
                'warden_contact': 'warden.bhaskara@campus.edu',
                'blocks': [
                    {'name': 'Block B1', 'floors': 3, 'rooms': ['101', '102', '201', '202', '301']},
                    {'name': 'Block B2', 'floors': 3, 'rooms': ['103', '104', '203', '204', '302']},
                ]
            },
            {
                'name': 'Gargi Hostel',
                'code': 'HOSTEL-G',
                'description': 'Girls Hostel with badminton court and central library annex',
                'gender': 'girls',
                'warden_name': 'Dr. Meenakshi Sundaram',
                'warden_contact': 'warden.gargi@campus.edu',
                'blocks': [
                    {'name': 'Block G1', 'floors': 4, 'rooms': ['101', '102', '201', '202', '301']},
                    {'name': 'Block G2', 'floors': 4, 'rooms': ['103', '104', '203', '204', '302']},
                ]
            },
            {
                'name': 'Chanakya Hostel',
                'code': 'HOSTEL-C',
                'description': 'Postgraduate & Research Scholars Hostel',
                'gender': 'coed',
                'warden_name': 'Dr. R. C. Mathur',
                'warden_contact': 'warden.chanakya@campus.edu',
                'blocks': [
                    {'name': 'Block C1', 'floors': 5, 'rooms': ['101', '201', '301', '401', '501']},
                ]
            },
        ]

        created_hostels = {}
        for h_info in hostel_data:
            hostel, _ = Hostel.objects.get_or_create(
                name=h_info['name'],
                defaults={
                    'code': h_info['code'],
                    'description': h_info['description'],
                    'gender': h_info['gender'],
                    'warden_name': h_info['warden_name'],
                    'warden_contact': h_info['warden_contact'],
                    'is_active': True
                }
            )
            created_hostels[hostel.name] = hostel

            for b_info in h_info['blocks']:
                block, _ = Block.objects.get_or_create(
                    hostel=hostel,
                    name=b_info['name'],
                    defaults={'floors': b_info['floors'], 'is_active': True}
                )
                for r_num in b_info['rooms']:
                    Room.objects.get_or_create(
                        block=block,
                        room_number=r_num,
                        defaults={'floor': int(r_num[0]), 'capacity': 2, 'is_active': True}
                    )

        # 3. Categories
        categories_data = [
            ('Electronics & Gadgets', 'laptop', 'marketplace'),
            ('Bicycles & Transport', 'bike', 'marketplace'),
            ('Books & Stationery', 'book-open', 'all'),
            ('Furniture & Mattresses', 'armchair', 'marketplace'),
            ('Sports & Fitness', 'trophy', 'marketplace'),
            ('Lab Equipment & Aprons', 'flask-conical', 'all'),
            ('Lost & Found Items', 'search', 'lost_found'),
            ('Room & Roommate Needs', 'home', 'roommate'),
            ('Study Notes & PYQs', 'file-text', 'study'),
            ('Hostel Services', 'wrench', 'services'),
            ('General Discussion', 'message-square', 'general'),
        ]

        created_categories = {}
        for cat_name, icon, p_type in categories_data:
            cat, _ = Category.objects.get_or_create(
                name=cat_name,
                defaults={'icon': icon, 'post_type': p_type, 'is_active': True}
            )
            created_categories[cat_name] = cat

        # 4. Users (Admin + Students)
        # Superuser / Admin
        admin_user, _ = User.objects.get_or_create(
            email='admin@hosteltalkies.com',
            defaults={
                'username': 'hosteladmin',
                'first_name': 'Admin',
                'last_name': '',
                'is_staff': True,
                'is_superuser': True,
                'is_hostel_admin': False,
                'is_student': False
            }
        )
        admin_user.first_name = 'Admin'
        admin_user.last_name = ''
        admin_user.set_password('Admin@12345')
        admin_user.save()

        # Student 1: Siddharth Singh (Aryabhata, Block A1, Room 201)
        siddharth, _ = User.objects.get_or_create(
            email='siddharth@student.edu',
            defaults={
                'username': 'siddharth',
                'first_name': 'Siddharth',
                'last_name': 'Singh',
                'is_student': True,
            }
        )
        siddharth.set_password('Student@12345')
        siddharth.save()

        h_aryabhata = created_hostels['Aryabhata Hostel']
        b_a1 = h_aryabhata.blocks.filter(name='Block A1').first()
        r_201 = b_a1.rooms.filter(room_number='201').first() if b_a1 else None

        StudentProfile.objects.update_or_create(
            user=siddharth,
            defaults={
                'hostel': h_aryabhata,
                'block': b_a1,
                'room': r_201,
                'bio': '3rd Year Computer Science student. Badminton enthusiast and tech tinkerer.',
                'phone_number': '+91 9876543210',
            }
        )

        # Student 2: Rahul Sharma (Bhaskara, Block B2, Room 104)
        rahul, _ = User.objects.get_or_create(
            email='rahul@student.edu',
            defaults={
                'username': 'rahul',
                'first_name': 'Rahul',
                'last_name': 'Sharma',
                'is_student': True,
            }
        )
        rahul.set_password('Student@12345')
        rahul.save()

        h_bhaskara = created_hostels['Bhaskara Hostel']
        b_b2 = h_bhaskara.blocks.filter(name='Block B2').first()
        r_104 = b_b2.rooms.filter(room_number='104').first() if b_b2 else None

        StudentProfile.objects.update_or_create(
            user=rahul,
            defaults={
                'hostel': h_bhaskara,
                'block': b_b2,
                'room': r_104,
                'bio': '2nd Year Mechanical Engineering. Love football and chess.',
                'phone_number': '+91 9811223344',
            }
        )

        # Student 3: Ananya Iyer (Gargi, Block G1, Room 301)
        ananya, _ = User.objects.get_or_create(
            email='ananya@student.edu',
            defaults={
                'username': 'ananya',
                'first_name': 'Ananya',
                'last_name': 'Iyer',
                'is_student': True,
            }
        )
        ananya.set_password('Student@12345')
        ananya.save()

        h_gargi = created_hostels['Gargi Hostel']
        b_g1 = h_gargi.blocks.filter(name='Block G1').first()
        r_301 = b_g1.rooms.filter(room_number='301').first() if b_g1 else None

        StudentProfile.objects.update_or_create(
            user=ananya,
            defaults={
                'hostel': h_gargi,
                'block': b_g1,
                'room': r_301,
                'bio': '4th Year Electrical Engineering. Design, robotics and reading.',
                'phone_number': '+91 9723456789',
            }
        )

        # Student 4: Rohit Verma (Aryabhata, NO block, NO room - testing optional fields)
        rohit, _ = User.objects.get_or_create(
            email='rohit@student.edu',
            defaults={
                'username': 'rohit',
                'first_name': 'Rohit',
                'last_name': 'Verma',
                'is_student': True,
            }
        )
        rohit.set_password('Student@12345')
        rohit.save()

        StudentProfile.objects.update_or_create(
            user=rohit,
            defaults={
                'hostel': h_aryabhata,
                'block': None,
                'room': None,
                'bio': '1st Year Freshman. Excited to explore college life!',
            }
        )

        # 5. Notices
        Notice.objects.get_or_create(
            title='Hostel Wi-Fi Network Upgrade & Maintenance',
            defaults={
                'content': 'Please be informed that network routers across all hostels will undergo scheduled maintenance tonight between 1:00 AM and 4:00 AM. High-speed 5G Wi-Fi nodes will be active tomorrow morning.',
                'priority': 'important',
                'target_hostel': None, # All hostels
                'publish_date': timezone.now() - timedelta(hours=2),
                'created_by': admin_user,
                'is_active': True
            }
        )

        Notice.objects.get_or_create(
            title='Urgent: Water Tank Cleaning in Aryabhata Hostel',
            defaults={
                'content': 'Water supply will be suspended in Aryabhata Hostel tomorrow from 9:00 AM to 1:00 PM for overhead tank cleaning and chlorination. Please store adequate water beforehand.',
                'priority': 'urgent',
                'target_hostel': h_aryabhata,
                'publish_date': timezone.now() - timedelta(hours=5),
                'created_by': admin_user,
                'is_active': True
            }
        )

        Notice.objects.get_or_create(
            title='Annual Hostel Premier League (HPL) Registration Open',
            defaults={
                'content': 'Inter-hostel Cricket and Badminton tournaments commence next weekend. Submit your team rosters at the Sports Secretary room before Friday 6:00 PM.',
                'priority': 'normal',
                'target_hostel': None,
                'publish_date': timezone.now() - timedelta(days=1),
                'created_by': admin_user,
                'is_active': True
            }
        )

        # 6. Events
        Event.objects.get_or_create(
            title='Inter-Hostel Badminton & Table Tennis Tournament',
            defaults={
                'description': 'Join the intra-hostel sports showdown! Bring your racquets, represent your floor, and win medals + exciting prizes.',
                'event_date': date.today() + timedelta(days=3),
                'event_time': '18:00:00',
                'location': 'Chanakya Recreation Hall & Sports Arena',
                'hostel': None,
                'organizer': 'Campus Sports Club & Hostel Council',
                'created_by': admin_user,
                'is_active': True
            }
        )

        Event.objects.get_or_create(
            title='Hostel Talkies Open Mic & Acoustic Night',
            defaults={
                'description': 'An evening of music, poetry, standup comedy, and acoustic performances under the hostel gazebo. Chai and snacks provided!',
                'event_date': date.today() + timedelta(days=5),
                'event_time': '20:00:00',
                'location': 'Aryabhata Quadrangle',
                'hostel': h_aryabhata,
                'organizer': 'Hostel Cultural Committee',
                'created_by': admin_user,
                'is_active': True
            }
        )

        # 7. Services
        HostelService.objects.get_or_create(
            name='Campus Express Laundry & Dry Cleaning',
            defaults={
                'category': 'laundry',
                'description': 'Same-day washing, steam ironing, and dry cleaning for student clothes and bedsheets.',
                'contact_person': 'Ramesh Kumar',
                'phone_number': '+91 9845012345',
                'location': 'Ground Floor, Behind Mess Hall',
                'timings': '8:00 AM - 8:30 PM (Mon-Sat)',
                'is_active': True
            }
        )

        HostelService.objects.get_or_create(
            name='Block B Xerox, Printing & Binding Shop',
            defaults={
                'category': 'printing',
                'description': 'High-speed B&W and color laser printing, project spiral binding, thesis hard-binding, and stationery items.',
                'contact_person': 'Suresh Printer',
                'phone_number': '+91 9876500011',
                'location': 'Bhaskara Hostel Annex, Room 002',
                'timings': '9:00 AM - 10:00 PM (Daily)',
                'is_active': True
            }
        )

        HostelService.objects.get_or_create(
            name='Hostel Electrician & Appliance Repair',
            defaults={
                'category': 'repair',
                'description': 'Quick repair for table fans, extension cords, study lamps, chargers, and room switches.',
                'contact_person': 'Manoj Electrician',
                'phone_number': '+91 9988776655',
                'location': 'Maintenance Office, Main Gate',
                'timings': '10:00 AM - 6:00 PM (On Call)',
                'is_active': True
            }
        )

        HostelService.objects.get_or_create(
            name='Campus Grooming & Barber Salon',
            defaults={
                'category': 'barber',
                'description': 'Haircuts, beard styling, head massage, and grooming for hostel students at subsidized rates.',
                'contact_person': 'Vikram Salon',
                'phone_number': '+91 9123456780',
                'location': 'Student Activity Center, 1st Floor',
                'timings': '9:30 AM - 8:00 PM (Closed Tuesdays)',
                'is_active': True
            }
        )

        # 8. Study Resources
        StudyResource.objects.get_or_create(
            title='Data Structures & Algorithms Complete Hand-Written Notes',
            defaults={
                'description': 'Comprehensive handwritten notes covering Trees, Graphs, Dynamic Programming, Heap, and Sorting algorithms with time complexity cheatsheet.',
                'resource_type': 'notes',
                'course_name': 'Data Structures & Algorithms',
                'course_code': 'CS201',
                'semester': 'Semester 3',
                'department': 'Computer Science',
                'uploader': siddharth,
                'downloads_count': 42,
                'is_active': True
            }
        )

        StudyResource.objects.get_or_create(
            title='Engineering Mathematics III (Calculus & Transforms) 5-Year PYQs',
            defaults={
                'description': 'Solved Previous Year Question papers with step-by-step solutions for Laplace transform, Fourier series, and PDE.',
                'resource_type': 'pyq',
                'course_name': 'Engineering Mathematics III',
                'course_code': 'MA201',
                'semester': 'Semester 3',
                'department': 'All Branches',
                'uploader': rahul,
                'downloads_count': 78,
                'is_active': True
            }
        )

        StudyResource.objects.get_or_create(
            title='Digital Electronics & Microprocessors Cheatsheet (PDF)',
            defaults={
                'description': 'Quick revision formulas, K-maps, timing diagrams, 8085 opcode reference table.',
                'resource_type': 'pdf',
                'course_name': 'Digital Electronics',
                'course_code': 'EC202',
                'semester': 'Semester 4',
                'department': 'Electronics & Electrical',
                'uploader': ananya,
                'downloads_count': 35,
                'is_active': True
            }
        )

        # 9. Posts & Marketplace items
        post1, _ = Post.objects.get_or_create(
            title='Hero Sprint Pro 21-Speed Geared Bicycle (With Lock & Helmet)',
            defaults={
                'author': siddharth,
                'hostel': h_aryabhata,
                'block': b_a1,
                'post_type': 'buy_sell',
                'category': created_categories.get('Bicycles & Transport'),
                'description': 'Selling my Hero Sprint Pro 21-speed geared cycle. In top running condition, newly tuned brakes and smooth shifting gears. Includes number cable lock and helmet for free. Perfect for commuting between hostels and department blocks.',
                'price': Decimal('2800.00'),
                'condition': 'like_new',
                'status': 'available',
                'location': 'Aryabhata Cycle Stand',
                'is_hidden': False,
                'is_deleted': False
            }
        )

        post2, _ = Post.objects.get_or_create(
            title='Casio FX-991EX ClassWiz Scientific Calculator',
            defaults={
                'author': rahul,
                'hostel': h_bhaskara,
                'block': b_b2,
                'post_type': 'buy_sell',
                'category': created_categories.get('Electronics & Gadgets'),
                'description': 'Authentic Casio ClassWiz fx-991EX scientific calculator with solar dual power. All matrix, integration, and statistical functions working perfectly.',
                'price': Decimal('650.00'),
                'condition': 'good',
                'status': 'available',
                'location': 'Bhaskara Block B2',
                'is_hidden': False,
                'is_deleted': False
            }
        )

        post3, _ = Post.objects.get_or_create(
            title='Solid Wood Study Table with Bookshelf Attachment',
            defaults={
                'author': ananya,
                'hostel': h_gargi,
                'block': b_g1,
                'post_type': 'giveaway',
                'category': created_categories.get('Furniture & Mattresses'),
                'description': 'Graduating final year, giving away my sturdy study desk and upper book rack for free to any junior who can pick it up from Gargi Hostel Ground floor.',
                'price': Decimal('0.00'),
                'condition': 'good',
                'status': 'available',
                'location': 'Gargi Hostel Room 301',
                'is_hidden': False,
                'is_deleted': False
            }
        )

        post4, _ = Post.objects.get_or_create(
            title='Looking to Borrow: Lab Coat & Chemistry Safety Goggles for Mid-Sem Exam',
            defaults={
                'author': rohit,
                'hostel': h_aryabhata,
                'block': None,
                'post_type': 'borrow',
                'category': created_categories.get('Lab Equipment & Aprons'),
                'description': 'Need a medium size lab coat and chemistry goggles for tomorrow afternoon lab exam (2 PM - 5 PM). Will return washed and sanitized immediately after exam.',
                'price': Decimal('0.00'),
                'condition': 'na',
                'status': 'available',
                'location': 'Aryabhata Hostel',
                'event_date': date.today() + timedelta(days=1),
                'is_hidden': False,
                'is_deleted': False
            }
        )

        post5, _ = Post.objects.get_or_create(
            title='LOST: Blue Boat Rockerz 450 Bluetooth Headphones',
            defaults={
                'author': rahul,
                'hostel': h_bhaskara,
                'block': b_b2,
                'post_type': 'lost',
                'category': created_categories.get('Lost & Found Items'),
                'description': 'Lost my navy blue Boat Rockerz 450 on-ear headphones yesterday evening near the Central Library study room 2 or the corridor towards hostel mess. Has a small sticker of Naruto on the right cup. Please message if found!',
                'location': 'Central Library 2nd Floor / Mess Corridor',
                'event_date': date.today() - timedelta(days=1),
                'status': 'available',
                'is_hidden': False,
                'is_deleted': False
            }
        )

        post6, _ = Post.objects.get_or_create(
            title='FOUND: Set of 3 Keys with Ferrari Red Keychain',
            defaults={
                'author': siddharth,
                'hostel': h_aryabhata,
                'block': b_a1,
                'post_type': 'found',
                'category': created_categories.get('Lost & Found Items'),
                'description': 'Found a set of 3 Godrej room keys with a red Ferrari metallic keychain on the bench outside Aryabhata canteen. Kept safely with me, message to identify and collect.',
                'location': 'Aryabhata Canteen Bench',
                'event_date': date.today(),
                'status': 'available',
                'is_hidden': False,
                'is_deleted': False
            }
        )

        post7, _ = Post.objects.get_or_create(
            title='Looking for 1 Chill Roommate for 2-Sharing Room next semester',
            defaults={
                'author': siddharth,
                'hostel': h_aryabhata,
                'block': b_a1,
                'post_type': 'roommate',
                'category': created_categories.get('Room & Roommate Needs'),
                'description': 'Looking for a non-smoker, clean roommate for next semester in Aryabhata Block A1. I am into coding, sleep around midnight, and respect personal space. Drop a message to discuss.',
                'location': 'Aryabhata Block A1',
                'status': 'available',
                'is_hidden': False,
                'is_deleted': False
            }
        )

        # 10. Social interactions: Likes, Comments, Saved Posts
        Like.objects.get_or_create(post=post1, user=rahul)
        Like.objects.get_or_create(post=post1, user=ananya)
        Like.objects.get_or_create(post=post3, user=siddharth)
        Like.objects.get_or_create(post=post3, user=rohit)

        Comment.objects.get_or_create(
            post=post1,
            author=rahul,
            defaults={'content': 'Hey Siddharth, is the bicycle still available? Can I test ride it this evening around 5 PM?'}
        )
        Comment.objects.get_or_create(
            post=post1,
            author=siddharth,
            defaults={'content': 'Yes Rahul! Meet me near the Aryabhata cycle stand at 5:15 PM.'}
        )

        SavedPost.objects.get_or_create(post=post1, user=rahul)
        SavedPost.objects.get_or_create(post=post3, user=rohit)

        # 11. Conversation & Message between Rahul and Siddharth
        conv, _ = Conversation.objects.get_or_create(related_post=post1)
        conv.participants.add(rahul, siddharth)
        
        if not Message.objects.filter(conversation=conv, sender=rahul).exists():
            Message.objects.create(
                conversation=conv,
                sender=rahul,
                content='Hey! Interested in the Hero Sprint bicycle. Is the price slightly negotiable?'
            )
        if not Message.objects.filter(conversation=conv, sender=siddharth).exists():
            Message.objects.create(
                conversation=conv,
                sender=siddharth,
                content='Hi Rahul, yes we can do ₹2600 if you take it today! It has the helmet and lock included.'
            )

        # 12. Sample Notification
        Notification.objects.get_or_create(
            recipient=siddharth,
            sender=rahul,
            notification_type='message',
            title='New Message from Rahul',
            defaults={
                'message': 'Rahul sent you a message regarding Hero Sprint Pro cycle.',
                'link': f'/messages/{conv.id}',
                'is_read': False
            }
        )

        self.stdout.write(self.style.SUCCESS("✓ Successfully seeded HostelTalkies database!"))
        self.stdout.write(self.style.SUCCESS("  Admin credentials: admin@hosteltalkies.com / Admin@12345"))
        self.stdout.write(self.style.SUCCESS("  Student 1 credentials: siddharth@student.edu / Student@12345"))
        self.stdout.write(self.style.SUCCESS("  Student 2 credentials: rahul@student.edu / Student@12345"))
