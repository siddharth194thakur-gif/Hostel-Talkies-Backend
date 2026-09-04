"""
normalize_study_resources.py
—————————————————————————————————————————————————————
Management command that audits and normalises all existing StudyResource records.

Rules
-----
• Semester strings like "Semester 3" → "Sem 3"
• Non-canonical department names → canonical equivalents
• resource_type "book" → "reference_material" (aligns with new choice set)
• resource_type "pdf" → "pdf" (stays, it is a valid type – cheatsheet/formula)
• resource_type "assignment" → "study_material" (aligned to new public label)
• Physics notes titled "Sem 2" but stored as "Sem 1" → corrected from title
• Removes 3 records that have no file AND no external_link (dead records)
• Marks records as needs_review=True when classification is genuinely uncertain
• Reports full before/after statistics
"""

import re
from django.core.management.base import BaseCommand
from study.models import StudyResource


# ── Canonical semester normalisations ────────────────────────────────────────
SEM_NORM = {
    'semester 1': 'Sem 1',
    'semester 2': 'Sem 2',
    'semester 3': 'Sem 3',
    'semester 4': 'Sem 4',
    'semester 5': 'Sem 5',
    'semester 6': 'Sem 6',
    'semester 7': 'Sem 7',
    'semester 8': 'Sem 8',
    '1': 'Sem 1',
    '2': 'Sem 2',
    '3': 'Sem 3',
    '4': 'Sem 4',
    '5': 'Sem 5',
    '6': 'Sem 6',
    '7': 'Sem 7',
    '8': 'Sem 8',
}

# ── Canonical department normalisations ──────────────────────────────────────
DEPT_NORM = {
    'computer science':         'Computer Science (CSE)',
    'cse':                      'Computer Science (CSE)',
    'electronics & electrical': 'Electronics & Comm (ECE)',
    'all branches':             'First Year / All Branches',
    'all branch':               'First Year / All Branches',
}

# ── resource_type migrations (old value → new value) ─────────────────────────
TYPE_MIGRATE = {
    'book':       'reference_material',
    'assignment': 'study_material',
}

# ── Semester extraction from title / description ──────────────────────────────
def extract_sem_from_text(text):
    """Return 'Sem N' if a confident semester is found in text, else None."""
    text = text.lower()
    # Match "sem 2", "semester 2", "s2", "2nd sem", "sem2"
    m = re.search(r'(?:semester|sem|s)\s*([1-8])\b', text)
    if m:
        return f'Sem {m.group(1)}'
    m2 = re.search(r'\b([1-8])(?:st|nd|rd|th)?\s*sem(?:ester)?\b', text)
    if m2:
        return f'Sem {m2.group(1)}'
    return None


class Command(BaseCommand):
    help = 'Normalise and audit all existing StudyResource records. Safe to re-run.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Preview changes without saving')
        parser.add_argument('--remove-dead', action='store_true', default=True,
                            help='Remove records with no file and no external_link (default: True)')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        remove_dead = options.get('remove_dead', True)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY-RUN — no changes will be saved.'))

        qs = StudyResource.objects.all()
        total = qs.count()
        self.stdout.write(f'\nTotal records to inspect: {total}')

        sem_fixed       = 0
        dept_fixed      = 0
        type_migrated   = 0
        sem_from_title  = 0
        marked_review   = 0
        dead_removed    = 0
        changed_records = 0

        for r in qs:
            dirty = False

            # ── 1. Remove dead records (no file, no link) ─────────────────────
            if remove_dead and not r.file and not r.external_link:
                self.stdout.write(
                    self.style.WARNING(f'  [DEAD] id={r.id} "{r.title[:60]}" — no file/link → removing')
                )
                if not dry_run:
                    r.delete()
                dead_removed += 1
                continue

            # ── 1b. Clean unwanted decorative symbols from title (∆☮) ────────
            from urllib.parse import unquote
            unquoted_title = unquote(r.title)
            cleaned_title = re.sub(r'[\s\-_(]*[💙~]*[∆\u2206][☮\u262e\ufe0f]+[💙~]*[\s\-_)]*', ' ', unquoted_title)
            cleaned_title = re.sub(r'[\s~]{2,}', ' ', cleaned_title)
            cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()
            if cleaned_title != r.title:
                self.stdout.write(f'  [TITLE-CLEAN] id={r.id} "{r.title}" → "{cleaned_title}"')
                r.title = cleaned_title
                dirty = True

            # ── 2. Normalise semester string ──────────────────────────────────
            raw_sem = r.semester.strip()
            if raw_sem.lower() in SEM_NORM:
                new_sem = SEM_NORM[raw_sem.lower()]
                if new_sem != r.semester:
                    self.stdout.write(f'  [SEM-FIX] id={r.id} "{r.semester}" → "{new_sem}"')
                    r.semester = new_sem
                    dirty = True
                    sem_fixed += 1

            # ── 3. Correct semester from title when stored value is wrong ─────
            # Heuristic: if title mentions "sem N" and stored semester differs,
            # correct it — but only when the stored semester is generic ("Sem 1")
            # and the title match is unambiguous.
            if not dirty or True:  # always try this
                title_sem = extract_sem_from_text(f"{r.title} {r.description}")
                if title_sem and title_sem != r.semester:
                    # Only auto-correct if stored semester looks like a fallback
                    # (was defaulted to Sem 1 by importer) and title is specific
                    if r.semester == 'Sem 1' and title_sem in ['Sem 2', 'Sem 3', 'Sem 4']:
                        self.stdout.write(
                            f'  [SEM-TITLE] id={r.id} "{r.title[:50]}" '
                            f'stored={r.semester} → title says {title_sem}'
                        )
                        r.semester = title_sem
                        dirty = True
                        sem_from_title += 1

            # ── 4. Normalise department name ──────────────────────────────────
            dept_key = r.department.strip().lower()
            if dept_key in DEPT_NORM:
                new_dept = DEPT_NORM[dept_key]
                if new_dept != r.department:
                    self.stdout.write(f'  [DEPT-FIX] id={r.id} "{r.department}" → "{new_dept}"')
                    r.department = new_dept
                    dirty = True
                    dept_fixed += 1

            # ── 5. Migrate deprecated resource_type values ────────────────────
            if r.resource_type in TYPE_MIGRATE:
                new_type = TYPE_MIGRATE[r.resource_type]
                self.stdout.write(
                    f'  [TYPE-MIG] id={r.id} resource_type "{r.resource_type}" → "{new_type}"'
                )
                r.resource_type = new_type
                dirty = True
                type_migrated += 1

            # ── 6. Mark needs_review for genuinely ambiguous records ──────────
            # Criteria: course_name is a vague fallback value
            vague_courses = {
                'general b.tech academic material',
                'vbspu unsiet b.tech official syllabus hub',
            }
            if r.course_name.strip().lower() in vague_courses and not r.needs_review:
                self.stdout.write(
                    f'  [REVIEW] id={r.id} "{r.title[:50]}" — vague course_name, flagging for review'
                )
                r.needs_review = True
                dirty = True
                marked_review += 1

            # Mark needs_review if semester is still empty after all corrections
            if not r.semester.strip() and not r.needs_review:
                r.needs_review = True
                dirty = True
                marked_review += 1

            if dirty:
                changed_records += 1
                if not dry_run:
                    r.save()

        self.stdout.write(self.style.SUCCESS(
            f'\n==============================\n'
            f'NORMALISATION COMPLETE\n'
            f'  Records inspected  : {total}\n'
            f'  Semester fixed     : {sem_fixed}\n'
            f'  Semester from title: {sem_from_title}\n'
            f'  Department fixed   : {dept_fixed}\n'
            f'  Type migrated      : {type_migrated}\n'
            f'  Flagged for review : {marked_review}\n'
            f'  Dead records removed: {dead_removed}\n'
            f'  Total changed      : {changed_records}\n'
            f'=============================='
        ))

        if not dry_run:
            # Final state report
            from django.db import connection
            cursor = connection.cursor()
            self.stdout.write('\n--- POST-NORMALISATION STATE ---')
            self.stdout.write(f'Total active: {StudyResource.objects.filter(is_active=True).count()}')
            self.stdout.write(f'Needs review: {StudyResource.objects.filter(needs_review=True).count()}')
            cursor.execute("SELECT resource_type, COUNT(*) FROM study_studyresource GROUP BY resource_type ORDER BY COUNT(*) DESC")
            self.stdout.write('By type:')
            for row in cursor.fetchall():
                self.stdout.write(f'  {row[0]}: {row[1]}')
            cursor.execute("SELECT semester, COUNT(*) FROM study_studyresource GROUP BY semester ORDER BY semester")
            self.stdout.write('By semester:')
            for row in cursor.fetchall():
                self.stdout.write(f'  {row[0]}: {row[1]}')
