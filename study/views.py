import re
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, F
from .models import StudyResource
from .serializers import StudyResourceSerializer, StudyResourceAdminSerializer
from users.permissions import IsChiefAdminOrReadOnly


class StudyResourceViewSet(viewsets.ModelViewSet):
    """
    /api/study/  —  Study Resources API

    Publicly readable (GET).  Write operations require admin.

    Filtering query params
    ──────────────────────
      type        = resource_type value (e.g. pyq, notes, syllabus …)
      department  = partial match on department
      semester    = partial match on semester  (e.g. "Sem 3")
      unit        = partial match on unit
      course      = partial match on course_name or course_code
      search      = full-text across title, course_name, course_code,
                    description, author, unit, source_website
      needs_review= true|1  — admin use: only flagged records
    """
    permission_classes = [IsChiefAdminOrReadOnly]

    def get_queryset(self):
        qs = StudyResource.objects.filter(is_active=True, is_pending_review=False)
        p  = self.request.query_params

        resource_type = p.get('type')
        if resource_type:
            qs = qs.filter(resource_type=resource_type)

        department = p.get('department')
        if department:
            qs = qs.filter(department__icontains=department)

        semester = p.get('semester')
        if semester:
            qs = qs.filter(semester__icontains=semester)

        unit = p.get('unit')
        if unit:
            qs = qs.filter(unit__icontains=unit)

        year = p.get('year')
        if year:
            qs = qs.filter(year=year)

        course = p.get('course')
        if course:
            qs = qs.filter(
                Q(course_name__icontains=course) | Q(course_code__icontains=course)
            )

        search = p.get('search')
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(course_name__icontains=search) |
                Q(course_code__icontains=search) |
                Q(year__icontains=search) |
                Q(exam_session__icontains=search) |
                Q(author__icontains=search) |
                Q(unit__icontains=search)
            )

        # Admin-only: filter by review status
        needs_review = p.get('needs_review', '').lower()
        if needs_review in ('true', '1') and self.request.user and self.request.user.is_staff:
            qs = qs.filter(needs_review=True)

        if resource_type == 'pyq':
            return qs.order_by('-year', '-created_at')
        return qs.order_by('-created_at')

    def get_serializer_class(self):
        """Use the admin serializer (with source fields) for staff users."""
        user = self.request.user
        if user and user.is_authenticated and (user.is_staff or user.is_superuser):
            return StudyResourceAdminSerializer
        return StudyResourceSerializer

    def perform_create(self, serializer):
        serializer.save(uploader=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def track_download(self, request, pk=None):
        """Atomically increment the download counter."""
        resource = self.get_object()
        StudyResource.objects.filter(id=resource.id).update(
            downloads_count=F('downloads_count') + 1
        )
        resource.refresh_from_db(fields=['downloads_count'])
        return Response({'downloads_count': resource.downloads_count})

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def meta(self, request):
        """
        Returns distinct filter dimensions AND a full hierarchy tree:

          hierarchy = {
            "Sem 3": {
              "Computer Science (CSE)": {
                "Data Structure": {
                  "types": ["notes", "pyq"],
                  "units": ["Unit 1", "Unit 2"]   # only non-empty units
                }
              }
            }
          }

        Flat lists (semesters, departments, resource_types, units) are preserved
        for backward compatibility with any existing callers.
        """
        qs = StudyResource.objects.filter(is_active=True, is_pending_review=False)

        # ── Flat lists (backward compat) ─────────────────────────────────────
        semesters = sorted(set(
            qs.exclude(semester='').values_list('semester', flat=True).distinct()
        ))
        departments = sorted(set(
            qs.exclude(department='').values_list('department', flat=True).distinct()
        ))
        type_map = dict(StudyResource.RESOURCE_TYPE_CHOICES)
        raw_types = list(
            qs.values_list('resource_type', flat=True).distinct().order_by('resource_type')
        )
        resource_types_labeled = [
            {'value': v, 'label': type_map.get(v, v)} for v in raw_types
        ]
        units = sorted(set(
            qs.exclude(unit='').values_list('unit', flat=True).distinct()
        ))
        years = sorted(
            set(qs.exclude(year='').values_list('year', flat=True).distinct()),
            key=lambda y: int(re.sub(r'\D', '', y)[:4]) if re.search(r'\d', y) else 0,
            reverse=True
        )

        # ── Hierarchy trees ──────────────────────────────────────────────────
        # Build: semester → department → course_name → {types, units, years}
        # One DB round-trip via values().
        rows = qs.values('semester', 'department', 'course_name', 'resource_type', 'unit', 'year', 'exam_session')

        hierarchy: dict = {}
        pyqs_hierarchy: dict = {}

        for row in rows:
            sem   = row['semester']      or ''
            dept  = row['department']    or ''
            subj  = row['course_name']   or ''
            rtype = row['resource_type'] or ''
            unit  = row['unit']          or ''
            yr    = row['year']          or ''
            sess  = row['exam_session']  or ''

            if not sem or not dept or not subj:
                continue

            # General hierarchy
            sem_node  = hierarchy.setdefault(sem, {})
            dept_node = sem_node.setdefault(dept, {})
            subj_node = dept_node.setdefault(subj, {'types': [], 'units': [], 'years': []})

            if rtype and rtype not in subj_node['types']:
                subj_node['types'].append(rtype)
            if unit and unit not in subj_node['units']:
                subj_node['units'].append(unit)
            if yr and yr not in subj_node['years']:
                subj_node['years'].append(yr)

            # Dedicated PYQ hierarchy
            if rtype == 'pyq':
                pyq_sem_node  = pyqs_hierarchy.setdefault(sem, {})
                pyq_dept_node = pyq_sem_node.setdefault(dept, {})
                pyq_subj_node = pyq_dept_node.setdefault(subj, {'years': [], 'sessions': []})
                if yr and yr not in pyq_subj_node['years']:
                    pyq_subj_node['years'].append(yr)
                if sess and sess not in pyq_subj_node['sessions']:
                    pyq_subj_node['sessions'].append(sess)

        # Sort within each subject node (years: Newest → Oldest)
        def year_sort_key(y_str):
            nums = re.findall(r'\d{4}', y_str)
            return int(nums[0]) if nums else 0

        for sem_val in hierarchy.values():
            for dept_val in sem_val.values():
                for subj_val in dept_val.values():
                    subj_val['types'].sort()
                    subj_val['units'].sort()
                    subj_val['years'].sort(key=year_sort_key, reverse=True)

        for sem_val in pyqs_hierarchy.values():
            for dept_val in sem_val.values():
                for subj_val in dept_val.values():
                    subj_val['years'].sort(key=year_sort_key, reverse=True)
                    subj_val['sessions'].sort()

        return Response({
            'semesters':      semesters,
            'departments':    departments,
            'resource_types': resource_types_labeled,
            'units':          units,
            'years':          years,
            'hierarchy':      hierarchy,
            'pyqs_hierarchy': pyqs_hierarchy,
        })

