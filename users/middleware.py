from django.http import JsonResponse
from django.utils import timezone

class BlockedAccountMiddleware:
    """
    Middleware that ensures blocked or suspended users cannot perform protected actions.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Exclude admin and static assets from blocking checks
        if request.path.startswith('/admin/') or request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)

        if getattr(request, 'user', None) and request.user.is_authenticated:
            if getattr(request.user, 'is_blocked', False):
                return JsonResponse({
                    'detail': 'Your account has been blocked by an administrator.',
                    'reason': getattr(request.user, 'block_reason', ''),
                    'code': 'account_blocked'
                }, status=403)
            
            if getattr(request.user, 'is_suspended', False):
                if request.user.suspended_until and timezone.now() > request.user.suspended_until:
                    request.user.is_suspended = False
                    request.user.suspended_until = None
                    request.user.save(update_fields=['is_suspended', 'suspended_until'])
                else:
                    return JsonResponse({
                        'detail': 'Your account has been temporarily suspended by an administrator.',
                        'suspended_until': request.user.suspended_until.isoformat() if request.user.suspended_until else None,
                        'reason': getattr(request.user, 'block_reason', ''),
                        'code': 'account_suspended'
                    }, status=403)

        return self.get_response(request)
