import logging
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django_jalali.admin.filters import JDateFieldListFilter
from users.models.comment import Comment

logger = logging.getLogger(__name__)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Enhanced Comment admin for MANAGING user comments"""

    list_display = [
        "id",
        "user_info",
        "subject_display",
        "content_preview",
        "status_badge",
        "response_status",
        "related_object",
        "created_at_display"
    ]

    # Remove editable fields from list - force admins to open each comment
    list_editable = []

    list_filter = [
        "is_approved",
        "is_active",
        ("created_at", JDateFieldListFilter),
        "content_type",
        ("admin_response", admin.EmptyFieldListFilter),  # Filter by response status
        # "responded_by",
        "user",  # Added user filter for better user management
    ]

    search_fields = [
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "subject",
        "content",
        "admin_response"
    ]

    ordering = ["-created_at"]
    list_per_page = 20
    # date_hierarchy = "created_at"

    readonly_fields = (
        "user", "subject", "content", "content_object",  # User content is read-only
        "created_at", "updated_at", "content_object_link"
    )

    fieldsets = (
        ("نظر کاربر (فقط خواندنی)", {
            "fields": ("user", "subject", "content"),
            "classes": ("wide",),
            "description": "این بخش توسط کاربر ارسال شده و قابل ویرایش نیست"
        }),
        ("مدیریت نظر", {
            "fields": ("is_approved", "is_active"),
            "classes": ("wide",),
        }),
        ("پاسخ مدیر", {
            "fields": ("admin_response",),
            "classes": ("wide",),
            "description": "در صورت نیاز می‌توانید به این نظر پاسخ دهید"
        }),
        ("ارتباط با محتوا", {
            "fields": ("content_type", "object_id", "content_object_link",),
            "classes": ("collapse",)
        }),
        ("زمان‌ها", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    actions = [
        "approve_comments",
        "reject_comments",
        "activate_comments",
        "deactivate_comments",
        "mark_as_responded",
        "export_comments_csv",
        "select_users_for_action",  # New action for user selection
        "export_user_emails",  # New action to export user emails
    ]

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)  # Custom CSS to fix styling issues
        }
        js = ('admin/js/custom_admin.js',)  # Custom JS for enhanced functionality

    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related(
            'user', 'content_type'
        ).prefetch_related('content_object')

    def has_add_permission(self, request):
        """Disable adding comments through admin - users add them via frontend"""
        return False

    def save_model(self, request, obj, form, change):
        """Auto-set response metadata when admin responds"""
        # if change and 'admin_response' in form.changed_data and obj.admin_response:
            # if not obj.responded_by:
            #     obj.responded_by = request.user
            #     obj.responded_at = timezone.now()
        super().save_model(request, obj, form, change)

    def user_info(self, obj):
        """Display user information with link to user admin (dynamic for custom user model)"""
        user = obj.user
        user_url = reverse(
            f"admin:{user._meta.app_label}_{user._meta.model_name}_change",
            args=[user.pk]
        )
        return format_html(
            '<a href="{}" title="مشاهده کاربر">{}</a><br>'
            '<small style="color:#666">{}</small>',
            user_url,
            user.get_full_name() or user.username,
            user.email or 'ایمیل ندارد'
        )

    user_info.short_description = "کاربر"

    def subject_display(self, obj):
        """Display subject with better formatting"""
        if obj.subject:
            return format_html(
                '<strong title="{}">{}</strong>',
                obj.subject,
                obj.subject[:30] + "..." if len(obj.subject) > 30 else obj.subject
            )
        return format_html('<em style="color: #999;">بدون موضوع</em>')

    subject_display.short_description = "موضوع"

    def content_preview(self, obj):
        """Show preview of comment content"""
        content = obj.content[:60]
        if len(obj.content) > 60:
            content += "..."

        return format_html(
            '<div title="{}" style="max-width: 180px; line-height: 1.3; font-size: 12px;">{}</div>',
            obj.content.replace('"', '&quot;'),
            content
        )

    content_preview.short_description = "متن نظر"

    def status_badge(self, obj):
        """Display status with colored badges"""
        if not obj.is_active:
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">غیرفعال</span>'
            )
        elif obj.is_approved:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">تایید شده</span>'
            )
        else:
            return format_html(
                '<span style="background: #ffc107; color: black; padding: 2px 6px; border-radius: 3px; font-size: 11px;">در انتظار</span>'
            )

    status_badge.short_description = "وضعیت"

    def response_status(self, obj):
        """Show if admin has responded"""
        if obj.admin_response:
            return format_html(
                '<span style="background: #17a2b8; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;" title="پاسخ داده شده توسط: {}">پاسخ داده شده</span>',
                 'نامشخص'
            )
        else:
            return format_html(
                '<span style="background: #6c757d; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">بدون پاسخ</span>'
            )

    response_status.short_description = "وضعیت پاسخ"

    def related_object(self, obj):
        """Display related object information"""
        if obj.content_object:
            return format_html(
                '<small>{}: {}</small>',
                obj.content_type.name,
                str(obj.content_object)[:30]
            )
        return format_html('<em style="color: #999;">-</em>')

    related_object.short_description = "مرتبط با"

    def created_at_display(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y/%m/%d %H:%M')

    created_at_display.short_description = "تاریخ ایجاد"

    def content_object_link(self, obj):
        """Show link to related object in admin"""
        if obj.content_object and hasattr(obj.content_object, '_meta'):
            try:
                url = reverse(
                    f'admin:{obj.content_object._meta.app_label}_{obj.content_object._meta.model_name}_change',
                    args=[obj.content_object.pk]
                )
                return format_html(
                    '<a href="{}" target="_blank">{}: {}</a>',
                    url,
                    obj.content_type.name,
                    str(obj.content_object)
                )
            except:
                return str(obj.content_object)
        return "-"

    content_object_link.short_description = "لینک به شی مرتبط"

    # Admin Actions
    def approve_comments(self, request, queryset):
        """Approve selected comments"""
        updated = queryset.update(is_approved=True)
        self.message_user(
            request,
            f"{updated} نظر تایید شد.",
            level=messages.SUCCESS
        )

    approve_comments.short_description = "تایید نظرات انتخاب شده"

    def reject_comments(self, request, queryset):
        """Reject selected comments"""
        updated = queryset.update(is_approved=False)
        self.message_user(
            request,
            f"{updated} نظر رد شد.",
            level=messages.WARNING
        )

    reject_comments.short_description = "رد نظرات انتخاب شده"

    def activate_comments(self, request, queryset):
        """Activate selected comments"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f"{updated} نظر فعال شد.",
            level=messages.SUCCESS
        )

    activate_comments.short_description = "فعال کردن نظرات انتخاب شده"

    def deactivate_comments(self, request, queryset):
        """Deactivate selected comments"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f"{updated} نظر غیرفعال شد.",
            level=messages.WARNING
        )

    deactivate_comments.short_description = "غیرفعال کردن نظرات انتخاب شده"

    def mark_as_responded(self, request, queryset):
        """Mark comments as responded (without adding actual response)"""
        count = 0
        for comment in queryset:
            # if not comment.responded_at:
            #     comment.responded_by = request.user
            #     comment.responded_at = timezone.now()
            comment.save()
            count += 1

        self.message_user(
            request,
            f"{count} نظر به عنوان پاسخ داده شده علامت‌گذاری شد.",
            level=messages.SUCCESS
        )

    mark_as_responded.short_description = "علامت‌گذاری به عنوان پاسخ داده شده"

    def export_comments_csv(self, request, queryset):
        """Export selected comments to CSV"""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="comments.csv"'
        response.write('\ufeff')  # UTF-8 BOM for Excel

        writer = csv.writer(response)
        writer.writerow(['شناسه', 'کاربر', 'موضوع', 'متن نظر', 'تاریخ ایجاد', 'وضعیت', 'پاسخ مدیر'])

        for comment in queryset:
            writer.writerow([
                comment.id,
                comment.user.username,
                comment.subject or '',
                comment.content,
                comment.created_at.strftime('%Y/%m/%d %H:%M'),
                'تایید شده' if comment.is_approved else 'در انتظار',
                comment.admin_response or ''
            ])

        return response

    export_comments_csv.short_description = "صدور فایل CSV از نظرات انتخاب شده"

    # NEW USER SELECTION ACTIONS
    def select_users_for_action(self, request, queryset):
        """Select unique users from selected comments for further actions"""
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        from urllib.parse import urlencode

        # Get unique user IDs from selected comments
        user_ids = list(queryset.values_list('user_id', flat=True).distinct())

        if not user_ids:
            self.message_user(
                request,
                "هیچ کاربری در نظرات انتخاب شده یافت نشد.",
                level=messages.WARNING
            )
            return

        # Store selected user IDs in session for use in user admin
        request.session['selected_user_ids'] = user_ids
        request.session['selected_from_comments'] = True

        # Redirect to user admin with pre-filtered users
        User = queryset.first().user.__class__
        user_admin_url = reverse(f'admin:{User._meta.app_label}_{User._meta.model_name}_changelist')
        params = {'id__in': ','.join(map(str, user_ids))}

        self.message_user(
            request,
            f"{len(user_ids)} کاربر منحصر به فرد از نظرات انتخاب شده استخراج شد.",
            level=messages.SUCCESS
        )

        return HttpResponseRedirect(f"{user_admin_url}?{urlencode(params)}")

    select_users_for_action.short_description = "انتخاب کاربران از نظرات انتخاب شده"

    def export_user_emails(self, request, queryset):
        """Export unique user emails from selected comments"""
        import csv
        from django.http import HttpResponse
        from django.db.models import Q

        # Get unique users from selected comments
        users = set()
        for comment in queryset.select_related('user'):
            if comment.user.email:
                users.add((comment.user.email, comment.user.get_full_name() or comment.user.username))

        if not users:
            self.message_user(
                request,
                "هیچ ایمیل کاربری در نظرات انتخاب شده یافت نشد.",
                level=messages.WARNING
            )
            return

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="user_emails.csv"'
        response.write('\ufeff')  # UTF-8 BOM for Excel

        writer = csv.writer(response)
        writer.writerow(['ایمیل', 'نام کاربر'])

        for email, name in sorted(users):
            writer.writerow([email, name])

        self.message_user(
            request,
            f"{len(users)} ایمیل کاربر منحصر به فرد صادر شد.",
            level=messages.SUCCESS
        )

        return response

    export_user_emails.short_description = "صدور ایمیل کاربران انتخاب شده"

    def changelist_view(self, request, extra_context=None):
        """Override changelist view to handle custom functionality"""
        extra_context = extra_context or {}

        # Add custom context for templates if needed
        extra_context['custom_actions_available'] = True

        return super().changelist_view(request, extra_context)

class CommentInline(admin.StackedInline):
    """Inline for user comments"""
    model = Comment
    fk_name = "user"
    extra = 0
    fields = ["content", "admin_response", "is_approved", "is_active", "created_at", "updated_at"]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        """Only show comments related to this user"""
        return super().get_queryset(request).select_related("user")

class HasCommentsFilter(admin.SimpleListFilter):
    """Custom filter to show users with or without comments"""

    title = "وضعیت نظرات"
    parameter_name = "has_comments"

    def lookups(self, request, model_admin):
        return (
            ("yes", "دارای نظر"),
            ("no", "بدون نظر"),
            ("approved", "دارای نظر تایید شده"),
            ("pending", "دارای نظر در انتظار تایید"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(comments__isnull=False).distinct()
        elif self.value() == "no":
            return queryset.filter(comments__isnull=True).distinct()
        elif self.value() == "approved":
            return queryset.filter(comments__is_approved=True).distinct()
        elif self.value() == "pending":
            return queryset.filter(comments__is_approved=False).distinct()
        return queryset
