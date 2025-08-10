# core/middleware/rate_limit.py
import logging

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("core")

# Configuration with defaults
RATE_LIMIT_REQUESTS = getattr(settings, "RATE_LIMIT_REQUESTS", 30)
RATE_LIMIT_WINDOW = getattr(settings, "RATE_LIMIT_WINDOW", 300)
RATE_LIMIT_BLOCK_RESPONSE = getattr(settings, "RATE_LIMIT_BLOCK_RESPONSE", True)
RATE_LIMIT_WHITELIST_IPS = getattr(settings, "RATE_LIMIT_WHITELIST_IPS", [])
RATE_LIMIT_SKIP_PATHS = getattr(
    settings, "RATE_LIMIT_SKIP_PATHS", ["/admin/", "/static/", "/media/"]
)

BLOCK_MESSAGE = "تعداد درخواست‌های شما بیش از حد مجاز است. لطفاً بعداً دوباره تلاش کنید."


class RateLimitMiddleware(MiddlewareMixin):
    """
    Enhanced rate limiting middleware with sliding window approach
    """

    def process_request(self, request):
        """Process request before view is called"""

        # Debug logging
        logger.info(f"Processing request: {request.path}")
        logger.info(f"Has user attr: {hasattr(request, 'user')}")

        # Skip rate limiting for whitelisted IPs
        if self._is_whitelisted(request):
            logger.info("Request whitelisted by IP")
            return None

        # Skip rate limiting for certain paths
        if self._should_skip_path(request):
            logger.info(f"Request skipped for path: {request.path}")
            return None

        # Skip for superusers (safe check)
        if self._is_superuser(request):
            logger.info("Request skipped for superuser")
            return None

        # Get client identifier and cache key
        identifier = self._get_identifier(request)
        cache_key = self._get_cache_key(identifier)

        logger.info(f"Rate limiting identifier: {identifier}")

        # Get current window data
        current_count, window_start = self._get_window_data(cache_key)
        current_time = timezone.now().timestamp()

        # Initialize new window if needed
        if window_start is None or (current_time - window_start) >= RATE_LIMIT_WINDOW:
            current_count = 1
            window_start = current_time
            self._update_window_data(cache_key, current_count, window_start)
            logger.info(f"New rate limit window started for {identifier}")
        else:
            # Increment counter in current window
            current_count += 1
            self._update_window_data(cache_key, current_count, window_start)
            logger.info(f"Rate limit count: {current_count} for {identifier}")

        # Check if limit exceeded
        if current_count > RATE_LIMIT_REQUESTS:
            time_remaining = RATE_LIMIT_WINDOW - (current_time - window_start)

            # Log the rate limit violation
            logger.warning(
                f"Rate limit exceeded for {identifier}. "
                f"Requests: {current_count}/{RATE_LIMIT_REQUESTS}, "
                f"Path: {request.path}, "
                f"Method: {request.method}"
            )

            if RATE_LIMIT_BLOCK_RESPONSE:
                return self._create_blocked_response(
                    request, current_count, time_remaining
                )

        # Store rate limit info for response headers
        request.rate_limit_info = {
            "current_count": current_count,
            "limit": RATE_LIMIT_REQUESTS,
            "window": RATE_LIMIT_WINDOW,
        }

        return None

    def process_response(self, request, response):
        """Add rate limit headers to response"""
        if hasattr(request, "rate_limit_info"):
            info = request.rate_limit_info
            response["X-RateLimit-Limit"] = str(info["limit"])
            response["X-RateLimit-Remaining"] = str(
                max(0, info["limit"] - info["current_count"])
            )
            response["X-RateLimit-Window"] = str(info["window"])

        return response

    def _get_client_ip(self, request):
        """Get client IP address from request headers"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "unknown")
        return ip

    def _get_identifier(self, request):
        """Generate unique identifier for rate limiting"""
        try:
            if hasattr(request, "user") and hasattr(request.user, "is_authenticated"):
                if request.user.is_authenticated:
                    return f"user:{request.user.pk}"
        except Exception as e:
            logger.warning(f"Error checking user authentication: {e}")

        # Fallback to IP-based identification
        ip = self._get_client_ip(request)
        return f"ip:{ip}"

    def _is_whitelisted(self, request):
        """Check if IP is whitelisted"""
        client_ip = self._get_client_ip(request)
        is_whitelisted = client_ip in RATE_LIMIT_WHITELIST_IPS
        if is_whitelisted:
            logger.info(f"IP {client_ip} is whitelisted")
        return is_whitelisted

    def _should_skip_path(self, request):
        """Check if request path should be excluded from rate limiting"""
        path = request.path
        should_skip = any(
            path.startswith(skip_path) for skip_path in RATE_LIMIT_SKIP_PATHS
        )
        if should_skip:
            logger.info(f"Path {path} should be skipped")
        return should_skip

    def _is_superuser(self, request):
        """Safely check if user is superuser"""
        try:
            if (
                hasattr(request, "user")
                and hasattr(request.user, "is_authenticated")
                and hasattr(request.user, "is_superuser")
            ):
                return request.user.is_authenticated and request.user.is_superuser
        except Exception as e:
            logger.warning(f"Error checking superuser status: {e}")
        return False

    def _get_cache_key(self, identifier):
        """Generate cache key for rate limiting"""
        return f"rl:{identifier}"

    def _get_window_data(self, cache_key):
        """Get current window request count and start time"""
        data = cache.get(cache_key)
        if data is None:
            return 0, None

        if isinstance(data, dict):
            return data.get("count", 0), data.get("window_start")
        else:
            return data, None

    def _update_window_data(self, cache_key, count, window_start=None):
        """Update window data in cache"""
        if window_start is None:
            window_start = timezone.now().timestamp()

        data = {"count": count, "window_start": window_start}
        cache.set(
            cache_key, data, RATE_LIMIT_WINDOW + 10
        )  # Add extra time to prevent race conditions

    def _create_blocked_response(self, request, current_count, time_remaining):
        """Create appropriate response when rate limit is exceeded"""
        retry_after = max(1, int(time_remaining))

        if request.headers.get("Accept", "").startswith(
            "application/json"
        ) or request.path.startswith("/api/"):
            response_data = {
                "error": "Rate limit exceeded",
                "message": BLOCK_MESSAGE,
                "current_requests": current_count,
                "limit": RATE_LIMIT_REQUESTS,
                "window_seconds": RATE_LIMIT_WINDOW,
                "retry_after": retry_after,
                "timestamp": timezone.now().isoformat(),
            }
            response = JsonResponse(response_data, status=429)
        else:
            html_content = f"""
            <!DOCTYPE html>
            <html dir="rtl" lang="fa">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>محدودیت درخواست</title>
                <style>
                    body {{ font-family: Tahoma, Arial; text-align: center; padding: 50px; background: #f5f5f5; }}
                    .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .error-code {{ font-size: 48px; color: #e74c3c; margin-bottom: 20px; }}
                    .message {{ font-size: 18px; color: #333; margin-bottom: 20px; }}
                    .details {{ font-size: 14px; color: #666; margin-bottom: 30px; }}
                    .retry {{ background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="error-code">429</div>
                    <div class="message">{BLOCK_MESSAGE}</div>
                    <div class="details">
                        درخواست‌های شما: {current_count}/{RATE_LIMIT_REQUESTS}<br>
                        زمان انتظار: {retry_after} ثانیه
                    </div>
                    <button class="retry" onclick="location.reload()">تلاش مجدد</button>
                </div>
            </body>
            </html>
            """
            response = HttpResponse(html_content, status=429)

        response["X-RateLimit-Limit"] = str(RATE_LIMIT_REQUESTS)
        response["X-RateLimit-Remaining"] = str(
            max(0, RATE_LIMIT_REQUESTS - current_count)
        )
        response["X-RateLimit-Reset"] = str(
            int(timezone.now().timestamp() + time_remaining)
        )
        response["Retry-After"] = str(retry_after)

        return response
