from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import permissions

class LenientJWTAuthentication(JWTAuthentication):
    """
    Standard JWT authentication that does not reject safe read-only methods
    (GET, HEAD, OPTIONS) or public auth endpoints (register, login) when an
    expired or invalid Bearer token is present in the request.

    Instead of raising AuthenticationFailed and terminating the request with HTTP 401,
    it gracefully treats the request as unauthenticated (AnonymousUser). This allows
    prospective students and visitors with stale browser tokens to load available hostels,
    public notices, and community resources without encountering 401 errors.

    Protected write endpoints (POST/PUT/PATCH/DELETE on user/post resources) still strictly
    validate the token and raise AuthenticationFailed if the token is invalid or expired.
    """

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        except Exception:
            path = getattr(request, 'path', '')
            # If safe read-only method or public auth endpoint, gracefully fallback to AnonymousUser
            if (
                request.method in permissions.SAFE_METHODS
                or '/auth/register/' in path
                or '/auth/login/' in path
            ):
                return None
            raise
