# sections/admin.py - WORKING VERSION
import json
import logging

from django import forms
from django.contrib import admin
from django.forms import ModelForm
from django.http import HttpResponse, JsonResponse
from django.urls import path, reverse
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt

from .models import Section

logger = logging.getLogger("sections")


class SectionForm(ModelForm):
    class Meta:
        model = Section
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter parent choices based on hierarchy rules
        if "parent" in self.fields:
            queryset = Section.objects.all()

            # Exclude self and descendants
            if self.instance and self.instance.pk:
                descendants = self.instance.get_descendants()
                exclude_ids = [self.instance.pk] + [d.pk for d in descendants]
                queryset = queryset.exclude(pk__in=exclude_ids)

            queryset = queryset.filter(level__lt=3).order_by("level", "order")

            choices = [("", "---------")]
            for section in queryset:
                level_indicator = "—" * (section.level - 1)
                label = f"{level_indicator} {section.display_title}"
                choices.append((section.pk, label))

            self.fields["parent"].choices = choices
            self.fields["parent"].widget = forms.Select(choices=choices)


class SectionAdmin(admin.ModelAdmin):
    form = SectionForm
    list_display = [
        "hierarchical_title",
        "section_type",
        "level_indicator",
        "order",
        "is_active",
        "created_at",
        "action_buttons",
    ]
    list_filter = ["is_active", "level", "section_type", "created_at"]
    search_fields = ["title", "content"]
    ordering = ["level", "order"]
    list_editable = ["is_active"]
    readonly_fields = ["created_at", "updated_at", "level", "get_full_path"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "slug",
                    "section_type",
                    "parent",
                    "content",
                    "order",
                    "is_active",
                )
            },
        ),
        (
            _("Hierarchy Info"),
            {"fields": ("level", "get_full_path"), "classes": ("collapse",)},
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_full_path(self, obj):
        """Display the full hierarchical path"""
        return obj.full_path if hasattr(obj, "full_path") else obj.title

    get_full_path.short_description = "Full Path"

    def get_urls(self):
        """Add custom URLs for drag & drop functionality"""
        urls = super().get_urls()
        custom_urls = [
            path(
                "reorder/", self.reorder_sections_view, name="sections_section_reorder"
            ),
            path("drag-drop/", self.drag_drop_view, name="sections_section_drag_drop"),
        ]
        return custom_urls + urls

    def hierarchical_title(self, obj):
        """نمایش عنوان با تورفتگی بر اساس سطح"""
        level_indicator = "—" * (obj.level - 1)
        return format_html(
            '<span style="margin-left: {}px;">{} {}</span>',
            (obj.level - 1) * 20,
            level_indicator,
            obj.title,
        )

    hierarchical_title.short_description = _("Title")

    def level_indicator(self, obj):
        colors = {1: "#28a745", 2: "#ffc107", 3: "#dc3545"}
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">L{}</span>',
            colors.get(obj.level, "#6c757d"),
            obj.level,
        )

    level_indicator.short_description = _("Level")

    def action_buttons(self, obj):
        buttons = []

        if obj.level < 3:
            buttons.append(
                format_html(
                    '<a class="button" href="{}?parent={}" title="Add Child Section">+ Child</a>',
                    reverse("admin:sections_section_add"),
                    obj.pk,
                )
            )
        if obj.children.exists():
            buttons.append(
                format_html(
                    '<a class="button" href="{}?parent__id__exact={}" title="View Children">Children ({})</a>',
                    reverse("admin:sections_section_changelist"),
                    obj.pk,
                    obj.children.count(),
                )
            )
        return format_html(" ".join(buttons))

    action_buttons.short_description = _("Actions")

    def drag_drop_view(self, request):
        """View for drag and drop reordering"""
        sections = (
            Section.objects.all().select_related("parent").order_by("level", "order")
        )
        grouped_sections = {}

        for section in sections:
            level = section.level
            if level not in grouped_sections:
                grouped_sections[level] = []
            grouped_sections[level].append(section)

        context = {
            "sections": sections,
            "grouped_sections": grouped_sections,
            "title": "Drag & Drop Reorder Sections",
            "opts": self.model._meta,
            "has_view_permission": self.has_view_permission(request),
            "has_change_permission": self.has_change_permission(request),
            "app_label": self.model._meta.app_label,
            "original": "sections",
        }

        # Create the HTML content directly
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Drag &amp; Drop Reorder Sections</title>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://code.jquery.com/ui/1.13.1/jquery-ui.min.js"></script>
    <link rel="stylesheet" href="https://code.jquery.com/ui/1.13.1/themes/ui-lightness/jquery-ui.css">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 5px; }
        .header { background: #417690; color: white; padding: 15px; margin: -20px -20px 20px -20px; border-radius: 5px 5px 0 0; }
        .level-container { margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; border: 1px solid #ddd; }
        .level-header { font-size: 16px; font-weight: bold; padding: 8px; border-radius: 4px; color: white; margin-bottom: 15px; }
        .level-1 { background-color: #28a745; }
        .level-2 { background-color: #ffc107; color: #212529; }
        .level-3 { background-color: #dc3545; }
        .sortable-list { list-style: none; padding: 0; margin: 0; min-height: 50px; }
        .sortable-item { 
            background: white; border: 1px solid #ddd; border-radius: 4px; padding: 12px; margin: 8px 0; 
            cursor: move; display: flex; justify-content: space-between; align-items: center;
        }
        .sortable-item:hover { box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-color: #007cba; }
        .sortable-item.ui-sortable-helper { transform: rotate(2deg); box-shadow: 0 5px 15px rgba(0,0,0,0.3); z-index: 1000; }
        .sortable-item.ui-sortable-placeholder { background: #e3f2fd; border: 2px dashed #2196f3; height: 50px; visibility: visible !important; }
        .section-info { display: flex; align-items: center; gap: 10px; }
        .section-title { font-weight: 600; color: #333; }
        .section-type { background: #6c757d; color: white; padding: 2px 6px; border-radius: 10px; font-size: 10px; }
        .drag-handle { cursor: grab; color: #6c757d; font-size: 16px; margin-right: 8px; }
        .controls { text-align: center; margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; }
        .btn { background: #007cba; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin: 0 5px; text-decoration: none; display: inline-block; }
        .btn:hover { background: #005a87; }
        .btn-success { background: #28a745; }
        .btn-success:hover { background: #218838; }
        .message { padding: 10px; margin: 10px 0; border-radius: 4px; display: none; }
        .message.success { background: #d4edda; color: #155724; }
        .message.error { background: #f8d7da; color: #721c24; }
        .empty-level { text-align: center; padding: 30px; color: #6c757d; font-style: italic; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔄 Drag &amp; Drop Reorder Sections</h1>
        </div>

        <div id="messages" class="message"></div>

        <div class="controls">
            <button id="save-order" class="btn btn-success">💾 Save New Order</button>
            <a href="../" class="btn">← Back to Sections</a>
        </div>
"""

        # Add sections by level
        for level in [1, 2, 3]:
            sections_in_level = grouped_sections.get(level, [])
            html_content += f"""
        <div class="level-container">
            <div class="level-header level-{level}">
                Level {level} Sections ({len(sections_in_level)})
            </div>
"""

            if sections_in_level:
                html_content += f'<ul class="sortable-list" data-level="{level}">'
                for section in sections_in_level:
                    section_type_display = dict(
                        section._meta.get_field("section_type").choices
                    ).get(section.section_type, section.section_type)
                    status = "Active" if section.is_active else "Inactive"
                    html_content += f"""
                <li class="sortable-item" data-id="{section.id}">
                    <div class="section-info">
                        <span class="drag-handle">☰</span>
                        <div>
                            <div class="section-title">{section.title}</div>
                            <span class="section-type">{section_type_display}</span>
                            <span class="section-type" style="background: {'#28a745' if section.is_active else '#dc3545'}">{status}</span>
                        </div>
                    </div>
                </li>"""
                html_content += "</ul>"
            else:
                html_content += (
                    f'<div class="empty-level">No sections at level {level}</div>'
                )

            html_content += "</div>"

        # Add JavaScript
        html_content += """
    </div>

    <script>
    $(document).ready(function() {
        console.log('Initializing sortable...');

        let originalOrders = {};

        $('.sortable-list').each(function() {
            const level = $(this).data('level');
            originalOrders[level] = [];

            $(this).find('.sortable-item').each(function() {
                originalOrders[level].push($(this).data('id'));
            });

            $(this).sortable({
                handle: '.drag-handle',
                placeholder: 'ui-sortable-placeholder',
                tolerance: 'pointer',
                cursor: 'grabbing',
                opacity: 0.8,
                start: function(event, ui) {
                    ui.placeholder.height(ui.item.height());
                },
                update: function(event, ui) {
                    console.log('Order changed for level', $(this).data('level'));
                }
            });
        });

        function showMessage(text, type) {
            $('#messages').removeClass('success error').addClass(type).text(text).show();
            setTimeout(() => $('#messages').fadeOut(), 5000);
        }

        $('#save-order').click(function() {
            const levelOrders = {};
            $('.sortable-list').each(function() {
                const level = $(this).data('level');
                const ids = [];
                $(this).find('.sortable-item').each(function() {
                    ids.push($(this).data('id'));
                });
                levelOrders[level] = ids;
            });

            console.log('Saving order:', levelOrders);

            const button = $(this);
            button.prop('disabled', true).text('💾 Saving...');

            $.ajax({
                url: '../reorder/',
                type: 'POST',
                data: JSON.stringify({level_orders: levelOrders}),
                contentType: 'application/json',
                success: function(response) {
                    if (response.success) {
                        showMessage('✅ Order saved successfully!', 'success');
                    } else {
                        showMessage('❌ Error: ' + response.message, 'error');
                    }
                },
                error: function(xhr) {
                    showMessage('❌ Failed to save order', 'error');
                    console.error('Error:', xhr.responseText);
                },
                complete: function() {
                    button.prop('disabled', false).text('💾 Save New Order');
                }
            });
        });

        console.log('Drag and drop initialized!');
    });
    </script>
</body>
</html>
"""

        return HttpResponse(html_content)

    @method_decorator(csrf_exempt)
    def reorder_sections_view(self, request):
        """Handle section reordering"""
        if request.method != "POST":
            return JsonResponse(
                {"success": False, "message": "Only POST allowed"}, status=405
            )

        try:
            data = json.loads(request.body.decode("utf-8"))
            level_orders = data.get("level_orders", {})

            success_count = 0
            for level_str, section_ids in level_orders.items():
                level = int(level_str)
                for index, section_id in enumerate(section_ids, start=1):
                    updated = Section.objects.filter(id=section_id, level=level).update(
                        order=index
                    )
                    if updated:
                        success_count += 1

            logger.info(
                f"Reordered {success_count} sections by {request.user.username}"
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Successfully reordered {success_count} sections",
                }
            )

        except Exception as e:
            logger.error(f"Reorder error: {str(e)}")
            return JsonResponse({"success": False, "message": str(e)}, status=500)

    def changelist_view(self, request, extra_context=None):
        """Add drag & drop button to changelist"""
        extra_context = extra_context or {}
        extra_context["show_drag_drop_button"] = True
        return super().changelist_view(request, extra_context)


admin.site.register(Section, SectionAdmin)
