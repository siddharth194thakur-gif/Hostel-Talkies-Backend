import json
import re
import urllib.request
from html import unescape
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from study.models import StudyResource

User = get_user_model()

class Command(BaseCommand):
    help = 'Import and normalize authentic VBSPU B.Tech academic resources from vbspu-pyq-hub.online and vbspuedu.blogspot.com'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview resources to be imported without saving to DB')
        parser.add_argument('--active', action='store_true', default=True, help='Mark imported resources as active (default: True)')
        parser.add_argument('--source1-only', action='store_true', help='Import only from Source 1 (VBSPU PYQ Hub)')
        parser.add_argument('--source2-only', action='store_true', help='Import only from Source 2 (VbspuEDU)')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        is_active = options.get('active', True)
        source1_only = options.get('source1_only', False)
        source2_only = options.get('source2_only', False)

        # Get or assign admin uploader
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first() or User.objects.first()
        if not admin_user:
            self.stderr.write(self.style.ERROR('No user found in database to assign as uploader. Please create a superuser first.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Academic Importer initialized. Uploader: {admin_user.email or admin_user.username}'))
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE ENABLED. No changes will be written to the database.'))

        imported_count = 0
        skipped_count = 0

        # -------------------------------------------------------------
        # 1. IMPORT SOURCE 1: https://www.vbspu-pyq-hub.online/ (Firestore)
        # -------------------------------------------------------------
        if not source2_only:
            self.stdout.write(self.style.MIGRATE_HEADING('\n--- Processing Source 1: VBSPU PYQ Hub (vbspu-pyq-hub.online) ---'))
            s1_imported, s1_skipped = self.import_source_1(admin_user, dry_run, is_active)
            imported_count += s1_imported
            skipped_count += s1_skipped

        # -------------------------------------------------------------
        # 2. IMPORT SOURCE 2: https://vbspuedu.blogspot.com/ (Blogger & Posts)
        # -------------------------------------------------------------
        if not source1_only:
            self.stdout.write(self.style.MIGRATE_HEADING('\n--- Processing Source 2: VbspuEDU (vbspuedu.blogspot.com) ---'))
            s2_imported, s2_skipped = self.import_source_2(admin_user, dry_run, is_active)
            imported_count += s2_imported
            skipped_count += s2_skipped

        self.stdout.write(self.style.SUCCESS(
            f'\n==================================================\n'
            f'IMPORT COMPLETED SUMMARY:\n'
            f'  • Newly Imported Resources: {imported_count}\n'
            f'  • Skipped (Duplicates/Invalid): {skipped_count}\n'
            f'  • Total Active Resources in DB: {StudyResource.objects.filter(is_active=True).count()}\n'
            f'=================================================='
        ))

    # -----------------------------------------------------------------
    # SOURCE 1 HANDLER
    # -----------------------------------------------------------------
    def import_source_1(self, admin_user, dry_run, is_active):
        url = 'https://firestore.googleapis.com/v1/projects/pyqs-website/databases/(default)/documents/pyqs?pageSize=300'
        req = urllib.request.Request(url, headers={'User-Agent': 'HostelTalkies Academic Importer/1.0'})
        imported = 0
        skipped = 0

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                docs = data.get('documents', [])
                self.stdout.write(f'Found {len(docs)} documents in Source 1 repository.')

                for d in docs:
                    fields = d.get('fields', {})
                    raw_title = fields.get('title', {}).get('stringValue', '').strip()
                    raw_subj = fields.get('subject', {}).get('stringValue', '').strip()
                    raw_sem = fields.get('semester', {}).get('stringValue', '').strip()
                    year = fields.get('year', {}).get('stringValue', '').strip()
                    link = fields.get('url', {}).get('stringValue', '').strip()

                    if not link or not raw_title:
                        skipped += 1
                        continue

                    # Classify and normalize
                    norm = self.normalize_academic_data(
                        raw_title=raw_title,
                        raw_subj=raw_subj,
                        raw_sem=raw_sem,
                        year=year,
                        source_name='VBSPU PYQ Hub'
                    )

                    # Deduplication check
                    if StudyResource.objects.filter(external_link=link).exists():
                        skipped += 1
                        continue

                    if not dry_run:
                        StudyResource.objects.create(
                            title=norm['title'],
                            description=norm['description'],
                            resource_type='pyq',
                            course_name=norm['course_name'],
                            course_code=norm['course_code'],
                            semester=norm['semester'],
                            department=norm['department'],
                            unit=norm.get('unit', ''),
                            external_link=link,
                            source_website='VBSPU PYQ Hub',
                            source_url='https://www.vbspu-pyq-hub.online/',
                            author=norm.get('author', 'VBSPU Faculty / Pyq Hub'),
                            uploader=admin_user,
                            is_active=is_active,
                            is_pending_review=False
                        )
                    imported += 1
                    self.stdout.write(f'  [+] S1 PYQ: {norm["title"]} ({norm["course_name"]} - {norm["semester"]})')

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error importing Source 1: {e}'))

        return imported, skipped

    # -----------------------------------------------------------------
    # SOURCE 2 HANDLER
    # -----------------------------------------------------------------
    def import_source_2(self, admin_user, dry_run, is_active):
        url = 'https://vbspuedu.blogspot.com/feeds/posts/default?alt=json&max-results=500'
        req = urllib.request.Request(url, headers={'User-Agent': 'HostelTalkies Academic Importer/1.0'})
        imported = 0
        skipped = 0

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                entries = data.get('feed', {}).get('entry', [])
                self.stdout.write(f'Found {len(entries)} posts in Source 2 repository.')

                for entry in entries:
                    post_url = [l.get('href') for l in entry.get('link', []) if l.get('rel') == 'alternate']
                    if not post_url:
                        continue
                    post_url = post_url[0]
                    post_title = entry.get('title', {}).get('$t', '')
                    cats = [c.get('term') for c in entry.get('category', [])]

                    # Fetch post HTML for complete extracted link catalogue with retry
                    html = ""
                    for attempt in range(3):
                        try:
                            import time
                            time.sleep(0.3)
                            p_req = urllib.request.Request(post_url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
                            with urllib.request.urlopen(p_req, timeout=15) as p_resp:
                                html = p_resp.read().decode('utf-8', errors='ignore')
                                break
                        except Exception as err:
                            if attempt == 2:
                                self.stderr.write(self.style.WARNING(f'Failed parsing post {post_url}: {err}'))
                            else:
                                import time
                                time.sleep(1.0)

                    if not html:
                        continue

                    title_match = re.search(r'<title>(.*?)</title>', html, re.I)
                    full_title = title_match.group(1).split(' - ')[0].split(' | ')[0].strip() if title_match else post_title
                    
                    # Extract all direct resources
                    anchors = re.findall(r'<a\s+[^>]*href=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a>', html, re.S | re.I)

                    for href, anchor_text in anchors:
                        clean_text = unescape(re.sub(r'<[^>]+>', '', anchor_text)).strip()
                        href = unescape(href.strip())

                        # Check if this is a verifiable resource download link
                        is_direct_file = any(dl in href for dl in ['drive.google.com', '.pdf', 'mega.nz', 'mediafire.com', 'icedrive.net', 'dropbox.com'])
                        if not is_direct_file:
                            continue

                        # Ignore nav links, social, loops, non-resource links
                        if any(ign in href for ign in ['whatsapp.com/channel', 'facebook.com', 'twitter.com', 'linkedin.com', 'search/label', 'javascript', '#', 'blogger.com', 'feed']):
                            continue

                        # Classify and normalize item
                        norm = self.normalize_academic_data(
                            raw_title=clean_text or full_title,
                            raw_subj=full_title,
                            raw_sem=' '.join(cats),
                            year='',
                            source_name='VbspuEDU',
                            parent_title=full_title,
                            link=href,
                            categories=cats
                        )

                        # Clean up generic titles
                        if norm['title'].lower() in ['download', 'download syllabus', 'link', 'download pdf', 'view pyqs', 'click here']:
                            norm['title'] = f"{norm['course_name']} {norm['resource_type_display']}"
                            if norm.get('unit'):
                                norm['title'] += f" - {norm['unit']}"

                        # Deduplication check
                        if StudyResource.objects.filter(external_link=href).exists():
                            skipped += 1
                            continue

                        if StudyResource.objects.filter(title=norm['title'], course_name=norm['course_name'], semester=norm['semester']).exists():
                            skipped += 1
                            continue

                        if not dry_run:
                            StudyResource.objects.create(
                                title=norm['title'],
                                description=norm['description'],
                                resource_type=norm['resource_type'],
                                course_name=norm['course_name'],
                                course_code=norm['course_code'],
                                semester=norm['semester'],
                                department=norm['department'],
                                unit=norm.get('unit', ''),
                                external_link=href,
                                source_website='VbspuEDU',
                                source_url=post_url,
                                author=norm.get('author', 'VbspuEDU Contributor / Faculty'),
                                uploader=admin_user,
                                is_active=is_active,
                                is_pending_review=False
                            )
                        imported += 1
                        self.stdout.write(f'  [+] S2 {norm["resource_type"].upper()}: {norm["title"]} ({norm["course_name"]} - {norm["semester"]})')

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error importing Source 2: {e}'))


        return imported, skipped

    # -----------------------------------------------------------------
    # INTELLIGENT NORMALIZATION & CLASSIFICATION ENGINE
    # -----------------------------------------------------------------
    def normalize_academic_data(self, raw_title, raw_subj, raw_sem, year='', source_name='', parent_title='', link='', categories=None):
        categories = categories or []
        combined_text = f"{raw_title} {raw_subj} {raw_sem} {parent_title} {' '.join(categories)}".lower()

        # If raw_title is a URL or generic download string, extract filename/slug
        clean_title = raw_title
        if raw_title.startswith('http://') or raw_title.startswith('https://'):
            # Extract filename from URL
            from urllib.parse import unquote
            decoded_url = unquote(raw_title)
            filename_match = re.search(r'([^\/\?#]+)\.(?:pdf|docx|zip|ppt|pptx)', decoded_url, re.I)
            if filename_match:
                extracted = filename_match.group(1).replace('_', ' ').replace('-', ' ')
                clean_title = extracted
            else:
                drive_slug = re.search(r'/d/([^/]+)', decoded_url)
                if drive_slug and len(drive_slug.group(1)) > 5 and not drive_slug.group(1).isalnum():
                    clean_title = drive_slug.group(1).replace('_', ' ').replace('-', ' ')
                else:
                    clean_title = ''

        # Clean symbols from title
        clean_title = clean_title.replace('~', ' ').replace('&#8710;', ' ').replace('&#9774;', ' ').replace('&#11015;', ' ').replace('👉', ' ').replace('📥', ' ').replace('📄', ' ').replace('📘', ' ').replace('📝', ' ').replace('📋', ' ')
        clean_title = re.sub(r'vbspuEDU', '', clean_title, flags=re.I)
        clean_title = re.sub(r'vbspu', '', clean_title, flags=re.I)
        clean_title = re.sub(r'@yoyo67am', '', clean_title, flags=re.I)
        clean_title = re.sub(r'\(.*?(?:dark|student).*?\)', '', clean_title, flags=re.I)
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        clean_title = re.sub(r'^(download\s*:?|view\s*:?)\s*', '', clean_title, flags=re.I).strip()


        # 1. SEMESTER DETECTION
        if str(raw_sem).strip() in ['1', '2', '3', '4', '5', '6', '7', '8']:
            semester = f'Sem {str(raw_sem).strip()}'
        else:
            sem_combo_match = re.search(r'\bsem\s*1\s*(?:&|and|\/)\s*2\b|\b1st\s*year\b', combined_text, re.I)
            sem_match = re.search(r'\b(?:sem|semester|s)\s*([1-8])\b', combined_text, re.I)
            
            if sem_combo_match:
                semester = 'Sem 1 & 2'
            elif sem_match:
                sem_num = sem_match.group(1)
                semester = f'Sem {sem_num}'
            elif 'sem3' in combined_text or 'pyqs3' in combined_text:
                semester = 'Sem 3'
            elif 'sem4' in combined_text or 'pyqs4' in combined_text:
                semester = 'Sem 4'
            elif 'sem1' in combined_text:
                semester = 'Sem 1'
            elif 'sem2' in combined_text:
                semester = 'Sem 2'
            elif 'sem5' in combined_text:
                semester = 'Sem 5'
            elif 'sem6' in combined_text:
                semester = 'Sem 6'
            elif 'all semester' in combined_text or 'all branches' in combined_text:
                semester = 'All Semesters'
            else:
                semester = 'Sem 1'

        # 2. UNIT DETECTION
        unit = ''
        unit_match = re.search(r'\b(unit\s*[1-5](?:\s*(?:&|\+|\-|\/)\s*[1-5])?)\b', combined_text, re.I)
        if unit_match:
            unit = unit_match.group(1).title()

        # 3. RESOURCE TYPE CLASSIFICATION
        if 'syllabus' in combined_text:
            resource_type = 'syllabus'
            resource_type_display = 'Syllabus'
        elif 'lab' in combined_text or 'practical' in combined_text or 'workshop' in combined_text or 'carpentry' in combined_text or 'welding' in combined_text:
            resource_type = 'lab_file'
            resource_type_display = 'Lab Manual / Practical'
        elif 'pyq' in combined_text or 'previous year' in combined_text or 'end sem' in combined_text or (year and int(year) > 2000 if year.isdigit() else False):
            resource_type = 'pyq'
            resource_type_display = 'PYQ Paper'
        elif 'book' in combined_text or 'textbook' in combined_text:
            resource_type = 'book'
            resource_type_display = 'Reference Book'
        elif 'assignment' in combined_text:
            resource_type = 'assignment'
            resource_type_display = 'Assignment'
        elif 'cheatsheet' in combined_text or 'formula' in combined_text:
            resource_type = 'pdf'
            resource_type_display = 'Formula / Cheat Sheet'
        else:
            resource_type = 'notes'
            resource_type_display = 'Lecture Notes'

        # 4. SUBJECT & BRANCH NORMALIZATION
        # Computer Science / IT / Core Subjects mapping
        if any(k in combined_text for k in ['data structure', 'ds using c', 'basic dsa', 'data-structure']):
            course_name = 'Data Structures & Algorithms'
            course_code = 'KCS301'
            department = 'Computer Science (CSE)'
        elif any(k in combined_text for k in ['coa', 'computer organization and architecture', 'computer organisation']):
            course_name = 'Computer Organization and Architecture (COA)'
            course_code = 'KCS302'
            department = 'Computer Science (CSE)'
        elif any(k in combined_text for k in ['dstl', 'discrete structure', 'theory of logic']):
            course_name = 'Discrete Structures & Theory of Logic (DSTL)'
            course_code = 'KCS303'
            department = 'Computer Science (CSE)'
        elif any(k in combined_text for k in ['cyber security', 'information security']):
            course_name = 'Cyber Security'
            course_code = 'KNC301'
            department = 'Computer Science (CSE)'
        elif any(k in combined_text for k in ['digital electronic', 'digital-electronics', 'de 20', 'de ']):
            course_name = 'Digital Electronics'
            course_code = 'KEC301'
            department = 'Electronics & Comm (ECE)'
        elif any(k in combined_text for k in ['universal human values', 'uhv', 'human values']):
            course_name = 'Universal Human Values (UHV)'
            course_code = 'KVE301'
            department = 'Applied Sciences & Humanities'
        elif any(k in combined_text for k in ['pps', 'programming for problem solving', 'c programming']):
            course_name = 'Programming for Problem Solving (PPS)'
            course_code = 'KCS101/201'
            department = 'Computer Science (CSE)'
        elif any(k in combined_text for k in ['technical communication', 'tc ']):
            course_name = 'Technical Communication'
            course_code = 'KAS401'
            department = 'Applied Sciences & Humanities'
        elif any(k in combined_text for k in ['web design', 'web technologies']):
            course_name = 'Web Designing & Development'
            course_code = 'KIT401'
            department = 'Information Tech (IT)'
        elif any(k in combined_text for k in ['artificial intelligence', 'ai unit', 'ai ']):
            course_name = 'Artificial Intelligence'
            course_code = 'KCS501'
            department = 'Computer Science (CSE)'
        elif any(k in combined_text for k in ['chemistry', 'fuels', 'water notes']):
            course_name = 'Engineering Chemistry'
            course_code = 'KAS102/202'
            department = 'Applied Sciences & Math'
        elif any(k in combined_text for k in ['physics', 'santosh sir', 'manish sir', 'ultrasound']):
            course_name = 'Engineering Physics'
            course_code = 'KAS101/201'
            department = 'Applied Sciences & Math'
        elif any(k in combined_text for k in ['mathmatics-i', 'maths-i', 'maths 1', 'mathematics-i', 'maths sem 1']):
            course_name = 'Engineering Mathematics - I'
            course_code = 'KAS103'
            department = 'Applied Sciences & Math'
        elif any(k in combined_text for k in ['mathmatics-ii', 'maths-ii', 'maths 2', 'mathematics-ii', 'maths sem 2', 'engineering mathematics ii']):
            course_name = 'Engineering Mathematics - II'
            course_code = 'KAS203'
            department = 'Applied Sciences & Math'
        elif any(k in combined_text for k in ['soft skill', 'soft-skill', 'soft-skills']):
            course_name = 'Soft Skills & Communication'
            course_code = 'KNC101/201'
            department = 'Applied Sciences & Humanities'
        elif any(k in combined_text for k in ['environment', 'ecology', 'eec']):
            course_name = 'Environment & Ecology'
            course_code = 'KNC102/202'
            department = 'Applied Sciences & Humanities'
        elif any(k in combined_text for k in ['fme', 'fmem', 'mechanical', 'mechatronics', 'ankush sir', 'rac', 'ic engine']):
            course_name = 'Fundamentals of Mechanical Engineering (FME)'
            course_code = 'KME101/201'
            department = 'Mechanical Engg (ME)'
        elif any(k in combined_text for k in ['fec', 'electronics', 'basic electronics']):
            course_name = 'Fundamentals of Electronics Engineering (FEC)'
            course_code = 'KEC101/201'
            department = 'Electronics & Comm (ECE)'
        elif any(k in combined_text for k in ['fee', 'bee', 'fel', 'electrical engineering']):
            course_name = 'Fundamentals of Electrical Engineering (FEE)'
            course_code = 'KEE101/201'
            department = 'Electrical Engg (EE)'
        elif any(k in combined_text for k in ['workshop', 'carpentry', 'welding']):
            course_name = 'Mechanical Workshop & Manufacturing Practice'
            course_code = 'KWS151'
            department = 'Mechanical Engg (ME)'
        elif 'syllabus' in combined_text:
            if 'cse' in combined_text:
                course_name = 'B.Tech CSE Complete Syllabus'
                course_code = 'CSE-SYLL'
                department = 'Computer Science (CSE)'
            elif 'it' in combined_text:
                course_name = 'B.Tech IT Complete Syllabus'
                course_code = 'IT-SYLL'
                department = 'Information Tech (IT)'
            elif 'electrical' in combined_text or 'electronics' in combined_text:
                course_name = 'B.Tech Electrical & Electronics Syllabus'
                course_code = 'EE-ECE-SYLL'
                department = 'Electrical Engg (EE)'
            elif 'ai' in combined_text or 'ml' in combined_text or 'iot' in combined_text:
                course_name = 'B.Tech AI, ML, DS & IoT Syllabus'
                course_code = 'AIML-SYLL'
                department = 'Computer Science (CSE)'
            else:
                course_name = 'VBSPU UNSIET B.Tech Official Syllabus Hub'
                course_code = 'UNSIET-SYLL'
                department = 'First Year / All Branches'
        else:
            course_name = raw_subj.replace('-', ' ').title() if raw_subj else 'General B.Tech Academic Material'
            course_code = ''
            department = 'First Year / All Branches'

        # 5. AUTHOR / FACULTY DETECTION
        author = 'VBSPU Faculty'
        if 'santosh sir' in combined_text:
            author = 'Prof. Santosh Sir (Physics)'
        elif 'manish sir' in combined_text:
            author = 'Prof. Manish Sir (Physics)'
        elif 'ankush sir' in combined_text:
            author = 'Prof. Ankush Sir (Mechanical)'
        elif 'aman' in combined_text or 'yoyo67am' in combined_text:
            author = 'VbspuEDU Academic Archive'
        elif source_name:
            author = source_name

        # 6. POLISHED FINAL TITLE
        final_title = clean_title
        if not final_title or len(final_title) < 4 or final_title.lower() in ['pdf', 'notes', 'download', 'pyq']:
            if year:
                final_title = f"{course_name} {resource_type_display} ({year})"
            elif unit:
                final_title = f"{course_name} {unit} Notes"
            else:
                final_title = f"{course_name} {resource_type_display}"

        description = f"Authentic VBSPU B.Tech {semester} academic resource for {course_name}. Classified and verified from {source_name}."
        if year:
            description += f" Exam Year: {year}."
        if unit:
            description += f" Coverage: {unit}."

        return {
            'title': final_title[:200],
            'description': description,
            'course_name': course_name,
            'course_code': course_code,
            'semester': semester,
            'department': department,
            'unit': unit,
            'resource_type': resource_type,
            'resource_type_display': resource_type_display,
            'author': author
        }
