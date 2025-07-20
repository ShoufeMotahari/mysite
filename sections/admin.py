# sections/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.forms import ModelForm
from django import forms
import json
import logging

from .models import Section

logger = logging.getLogger('sections')


class SectionForm(ModelForm):
    class Meta:
        model = Section
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter parent choices based on hierarchy rules
        if 'parent' in self.fields:
            queryset = Section.objects.all()

            # Exclude self and descendants
            if self.instance and self.instance.pk:
                descendants = self.instance.get_descendants()
                exclude_ids = [self.instance.pk] + [d.pk for d in descendants]
                queryset = queryset.exclude(pk__in=exclude_ids)

            queryset = queryset.filter(level__lt=3).order_by('level', 'order')

            choices = [('', '---------')]
            for section in queryset:
                level_indicator = "—" * (section.level - 1)
                label = f"{level_indicator} {section.display_title}"
                choices.append((section.pk, label))

            self.fields['parent'].choices = choices
            self.fields['parent'].widget = forms.Select(choices=choices)


class SectionAdmin(admin.ModelAdmin):
    form = SectionForm
    list_display = ['hierarchical_title', 'section_type', 'level_indicator', 'order', 'is_active', 'created_at', 'action_buttons']
    list_filter = ['is_active', 'level', 'section_type', 'created_at']
    search_fields = ['title', 'content']
    ordering = ['level', 'order']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'updated_at', 'level', 'get_full_path']  # تغییر کرد

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'section_type', 'parent', 'content', 'order', 'is_active')
        }),
        (_('Hierarchy Info'), {
            'fields': ('level', 'get_full_path'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_full_path(self, obj):
        return obj.full_path

    get_full_path.short_description = "Full Path"


    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('reorder/', self.admin_site.admin_view(self.reorder_view), name='sections_section_reorder'),
            path('drag-drop/', self.admin_site.admin_view(self.drag_drop_view), name='sections_section_drag_drop'),
            path('hierarchy/', self.admin_site.admin_view(self.hierarchy_view), name='sections_section_hierarchy'),
        ]
        return custom_urls + urls

    def hierarchical_title(self, obj):
        """نمایش عنوان با تورفتگی بر اساس سطح"""
        level_indicator = "—" * (obj.level - 1)
        return format_html('<span style="margin-left: {}px;">{} {}</span>',
                           (obj.level - 1) * 20, level_indicator, obj.title)
    hierarchical_title.short_description = _('Title')

    def level_indicator(self, obj):
        colors = {1: '#28a745', 2: '#ffc107', 3: '#dc3545'}
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">L{}</span>',
            colors.get(obj.level, '#6c757d'), obj.level
        )
    level_indicator.short_description = _('Level')

    def action_buttons(self, obj):
        buttons = []
        if obj.level < 3:
            buttons.append(
                format_html(
                    '<a class="button" href="{}?parent={}" title="Add Child Section">+ Child</a>',
                    '/admin/sections/section/add/', obj.pk
                )
            )
        if obj.children.exists():
            buttons.append(
                format_html(
                    '<a class="button" href="{}?parent__id__exact={}" title="View Children">Children ({})</a>',
                    '/admin/sections/section/', obj.pk, obj.children.count()
                )
            )
        return format_html(' '.join(buttons))
    action_buttons.short_description = _('Actions')

    def drag_drop_view(self, request):
        sections = Section.objects.all().order_by('level', 'order')
        grouped_sections = {}
        for section in sections:
            grouped_sections.setdefault(section.level, []).append(section)

        context = {
            'sections': sections,
            'grouped_sections': grouped_sections,
            'title': _('Reorder Sections'),
            'opts': self.model._meta,
            'has_change_permission': self.has_change_permission(request),
        }
        return render(request, 'admin/sections/drag_drop_hierarchical.html', context)

    def hierarchy_view(self, request):
        tree_structure = Section.get_tree_structure()
        context = {
            'tree_structure': tree_structure,
            'title': _('Section Hierarchy'),
            'opts': self.model._meta,
        }
        return render(request, 'admin/sections/hierarchy_view.html', context)

    @csrf_exempt
    def reorder_view(self, request):
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                if 'level_orders' in data:
                    for level, section_ids in data['level_orders'].items():
                        for index, section_id in enumerate(section_ids, start=1):
                            Section.objects.filter(id=section_id).update(order=index)
                else:
                    section_ids = data.get('section_ids', [])
                    Section.reorder_sections(section_ids)

                logger.info(f'Sections reordered by {request.user.username}')
                return JsonResponse({'success': True, 'message': _('Sections reordered successfully')})
            except Exception as e:
                logger.error(f'Error reordering sections: {str(e)}')
                return JsonResponse({'success': False, 'message': str(e)}, status=500)
        return JsonResponse({'success': False, 'message': _('Invalid method')}, status=405)

    def has_add_permission(self, request):
        parent_id = request.GET.get('parent')
        if parent_id:
            try:
                parent = Section.objects.get(pk=parent_id)
                if parent.level >= 3:
                    return False
            except Section.DoesNotExist:
                pass
        else:
            if Section.objects.filter(level=1).count() >= 7:
                return False
        return super().has_add_permission(request)

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        parent_id = request.GET.get('parent')
        if parent_id:
            try:
                parent = Section.objects.get(pk=parent_id)
                extra_context['parent_section'] = parent
                extra_context['adding_child'] = True
            except Section.DoesNotExist:
                pass
        else:
            root_count = Section.objects.filter(level=1).count()
            if root_count >= 6:
                messages.warning(request, _('You can only create {} more root section(s)').format(7 - root_count))
        return super().add_view(request, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        stats = {
            'total_sections': Section.objects.count(),
            'root_sections': Section.objects.filter(level=1).count(),
            'level_2_sections': Section.objects.filter(level=2).count(),
            'level_3_sections': Section.objects.filter(level=3).count(),
            'active_sections': Section.objects.filter(is_active=True).count(),
        }
        extra_context['hierarchy_stats'] = stats
        return super().changelist_view(request, extra_context)


admin.site.register(Section, SectionAdmin)
