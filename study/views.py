import re
from django.core.cache import cache
from django.db.models import Q, F
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from .models import StudyResource, STUDY_META_CACHE_KEY, invalidate_study_meta_cache
from .serializers import StudyResourceSerializer, StudyResourceAdminSerializer
from users.permissions import IsChiefAdminOrReadOnly


class StudyResourcePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class StudyResourceViewSet(viewsets.ModelViewSet):
    """
    /api/study/  —  Study Resources API

    Publicly readable (GET). Write operations require admin.

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
    pagination_class = StudyResourcePagination

    def get_queryset(self):
        qs = StudyResource.objects.filter(
            is_active=True, is_pending_review=False
        ).select_related('uploader', 'uploader__profile')
        p = self.request.query_params

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
        serializer.save(uploader=self.request.user, is_active=True)
        invalidate_study_meta_cache()

    def perform_update(self, serializer):
        serializer.save()
        invalidate_study_meta_cache()

    def perform_destroy(self, instance):
        instance.delete()
        invalidate_study_meta_cache()

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

        All extracted in a single fast query and cached in memory (1 hour TTL).
        """
        cached_data = cache.get(STUDY_META_CACHE_KEY)
        if cached_data is not None:
            return Response(cached_data)

        qs = StudyResource.objects.filter(is_active=True, is_pending_review=False)
        rows = list(qs.values('semester', 'department', 'course_name', 'resource_type', 'unit', 'year', 'exam_session'))

        semesters_set = set()
        departments_set = set()
        raw_types_set = set()
        units_set = set()
        years_set = set()
        type_counts = {}

        hierarchy = {}
        pyqs_hierarchy = {}

        def year_sort_key(y_str):
            nums = re.findall(r'\d{4}', str(y_str))
            return int(nums[0]) if nums else 0

        for row in rows:
            sem   = (row['semester'] or '').strip()
            dept  = (row['department'] or '').strip()
            subj  = (row['course_name'] or '').strip()
            rtype = (row['resource_type'] or '').strip()
            unit  = (row['unit'] or '').strip()
            yr    = (row['year'] or '').strip()
            sess  = (row['exam_session'] or '').strip()

            if sem:
                semesters_set.add(sem)
            if dept:
                departments_set.add(dept)
            if rtype:
                raw_types_set.add(rtype)
                type_counts[rtype] = type_counts.get(rtype, 0) + 1
            if unit:
                units_set.add(unit)
            if yr:
                years_set.add(yr)

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

        type_map = dict(StudyResource.RESOURCE_TYPE_CHOICES)
        resource_types_labeled = [
            {'value': v, 'label': type_map.get(v, v)} for v in sorted(raw_types_set)
        ]

        data = {
            'semesters':      sorted(semesters_set),
            'departments':    sorted(departments_set),
            'resource_types': resource_types_labeled,
            'type_counts':    type_counts,
            'total_count':    len(rows),
            'units':          sorted(units_set),
            'years':          sorted(years_set, key=year_sort_key, reverse=True),
            'hierarchy':      hierarchy,
            'pyqs_hierarchy': pyqs_hierarchy,
        }

        cache.set(STUDY_META_CACHE_KEY, data, timeout=3600)
        return Response(data)


