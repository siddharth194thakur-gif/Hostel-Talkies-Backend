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
                Q(author__icontains=search) |
                Q(unit__icontains=search)
            )

        # Admin-only: filter by review status
        needs_review = p.get('needs_review', '').lower()
        if needs_review in ('true', '1') and self.request.user and self.request.user.is_staff:
            qs = qs.filter(needs_review=True)

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

        # ── Hierarchy tree ───────────────────────────────────────────────────
        # Build: semester → department → course_name → {types, units}
        # One DB round-trip via values().
        rows = qs.values('semester', 'department', 'course_name', 'resource_type', 'unit')

        hierarchy: dict = {}
        for row in rows:
            sem   = row['semester']      or ''
            dept  = row['department']    or ''
            subj  = row['course_name']   or ''
            rtype = row['resource_type'] or ''
            unit  = row['unit']          or ''

            if not sem or not dept or not subj:
                continue

            sem_node  = hierarchy.setdefault(sem, {})
            dept_node = sem_node.setdefault(dept, {})
            subj_node = dept_node.setdefault(subj, {'types': [], 'units': []})

            if rtype and rtype not in subj_node['types']:
                subj_node['types'].append(rtype)
            if unit and unit not in subj_node['units']:
                subj_node['units'].append(unit)

        # Sort types and units within each subject node
        for sem_val in hierarchy.values():
            for dept_val in sem_val.values():
                for subj_val in dept_val.values():
                    subj_val['types'].sort()
                    subj_val['units'].sort()

        return Response({
            'semesters':      semesters,
            'departments':    departments,
            'resource_types': resource_types_labeled,
            'units':          units,
            'hierarchy':      hierarchy,
        })

