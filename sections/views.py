import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext_lazy as _

from .models import Section

logger = logging.getLogger("sections")


def sections_list(request):
    """Public view to display all active sections in hierarchical structure"""
    # Get tree structure for hierarchical display
    tree_structure = Section.get_tree_structure()

    # Also get flat list for search/filter functionality
    sections = Section.get_active_sections()

    # Search functionality
    search_query = request.GET.get("search", "")
    if search_query:
        sections = sections.filter(
            Q(title__icontains=search_query) | Q(content__icontains=search_query)
        )

    # Filter by level
    level_filter = request.GET.get("level")
    if level_filter:
        try:
            level_filter = int(level_filter)
            sections = sections.filter(level=level_filter)
        except ValueError:
            pass

    # Pagination
    paginator = Paginator(sections, 10)  # Show 10 sections per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    logger.info(f"سکشن لیست درخواست شد - تعداد سکشن‌های فعال: {sections.count()}")

    context = {
        "tree_structure": tree_structure,
        "sections": sections,
        "page_obj": page_obj,
        "search_query": search_query,
        "level_filter": level_filter,
        "title": _("Sections"),
        "total_sections": Section.objects.filter(is_active=True).count(),
        "levels_count": {
            1: Section.objects.filter(level=1, is_active=True).count(),
            2: Section.objects.filter(level=2, is_active=True).count(),
            3: Section.objects.filter(level=3, is_active=True).count(),
        },
    }
    return render(request, "sections/sections_list.html", context)


def section_detail(request, section_id):
    """Public view to display a specific section with navigation"""
    section = get_object_or_404(Section, id=section_id, is_active=True)

    # Get navigation context
    context = {
        "section": section,
        "title": section.title,
        "breadcrumbs": section.get_ancestors() + [section],
        "children": section.children.filter(is_active=True).order_by("order"),
        "siblings": None,
        "parent": section.parent,
        "next_section": None,
        "prev_section": None,
    }

    # Get siblings if has parent
    if section.parent:
        siblings = section.parent.children.filter(is_active=True).order_by("order")
        context["siblings"] = siblings

        # Find next and previous sections within siblings
        siblings_list = list(siblings)
        try:
            current_index = siblings_list.index(section)
            if current_index > 0:
                context["prev_section"] = siblings_list[current_index - 1]
            if current_index < len(siblings_list) - 1:
                context["next_section"] = siblings_list[current_index + 1]
        except ValueError:
            pass
    else:
        # For root sections, get all root sections as siblings
        siblings = Section.objects.filter(level=1, is_active=True).order_by("order")
        context["siblings"] = siblings

        siblings_list = list(siblings)
        try:
            current_index = siblings_list.index(section)
            if current_index > 0:
                context["prev_section"] = siblings_list[current_index - 1]
            if current_index < len(siblings_list) - 1:
                context["next_section"] = siblings_list[current_index + 1]
        except ValueError:
            pass

    logger.info(f"سکشن {section.title} نمایش داده شد")
    return render(request, "sections/section_detail.html", context)


def section_by_slug(request, slug):
    """Access section by slug for SEO-friendly URLs"""
    section = get_object_or_404(Section, slug=slug, is_active=True)
    return section_detail(request, section.id)


def section_tree(request):
    """API endpoint to get section tree structure as JSON"""
    try:
        tree_structure = Section.get_tree_structure()

        def serialize_tree(tree):
            result = []
            for item in tree:
                section_data = {
                    "id": item["section"].id,
                    "title": item["section"].title,
                    "slug": item["section"].slug,
                    "level": item["section"].level,
                    "order": item["section"].order,
                    "display_title": item["section"].display_title,
                    "has_content": bool(item["section"].content),
                    "children": serialize_tree(item["children"]),
                }
                result.append(section_data)
            return result

        return JsonResponse({"success": True, "tree": serialize_tree(tree_structure)})
    except Exception as e:
        logger.error(f"Error getting section tree: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@staff_member_required
def admin_sections_preview(request):
    """Admin preview of all sections with management tools"""
    # Get sections with optional filtering
    sections = Section.objects.all()

    # Filter options
    status_filter = request.GET.get("status", "all")  # all, active, inactive
    level_filter = request.GET.get("level")

    if status_filter == "active":
        sections = sections.filter(is_active=True)
    elif status_filter == "inactive":
        sections = sections.filter(is_active=False)

    if level_filter:
        try:
            level_filter = int(level_filter)
            sections = sections.filter(level=level_filter)
        except ValueError:
            pass

    sections = sections.order_by("level", "order")

    # Get statistics
    stats = {
        "total": Section.objects.count(),
        "active": Section.objects.filter(is_active=True).count(),
        "inactive": Section.objects.filter(is_active=False).count(),
        "by_level": {
            1: Section.objects.filter(level=1).count(),
            2: Section.objects.filter(level=2).count(),
            3: Section.objects.filter(level=3).count(),
        },
        "with_content": Section.objects.exclude(content="").count(),
        "without_content": Section.objects.filter(content="").count(),
    }

    # Get tree structure for hierarchical view
    all_tree = []
    root_sections = Section.objects.filter(level=1).order_by("order")

    def build_admin_tree(sections, parent_level=0):
        result = []
        for section in sections:
            section_data = {
                "section": section,
                "children": build_admin_tree(
                    section.children.all().order_by("order"), parent_level + 1
                ),
            }
            result.append(section_data)
        return result

    all_tree = build_admin_tree(root_sections)

    context = {
        "sections": sections,
        "tree_structure": all_tree,
        "stats": stats,
        "status_filter": status_filter,
        "level_filter": level_filter,
        "title": _("Sections Preview"),
        "is_preview": True,
    }
    return render(request, "sections/admin_preview.html", context)


@staff_member_required
def admin_section_toggle_status(request, section_id):
    """AJAX endpoint to toggle section active status"""
    if request.method == "POST":
        try:
            section = get_object_or_404(Section, id=section_id)
            section.is_active = not section.is_active
            section.save()

            status_text = _("Active") if section.is_active else _("Inactive")
            logger.info(f"Section {section.title} status changed to: {status_text}")

            return JsonResponse(
                {
                    "success": True,
                    "is_active": section.is_active,
                    "status_text": status_text,
                    "message": _("Status updated successfully"),
                }
            )
        except Exception as e:
            logger.error(f"Error toggling section status: {str(e)}")
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse(
        {"success": False, "error": _("Invalid request method")}, status=405
    )


@staff_member_required
def admin_sections_bulk_action(request):
    """Handle bulk actions on sections"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            action = data.get("action")
            section_ids = data.get("section_ids", [])

            if not section_ids:
                return JsonResponse(
                    {"success": False, "error": _("No sections selected")}, status=400
                )

            sections = Section.objects.filter(id__in=section_ids)

            if action == "activate":
                sections.update(is_active=True)
                message = _("Selected sections activated")
            elif action == "deactivate":
                sections.update(is_active=False)
                message = _("Selected sections deactivated")
            elif action == "delete":
                # Check for dependencies before deleting
                for section in sections:
                    if section.children.exists():
                        return JsonResponse(
                            {
                                "success": False,
                                "error": _(
                                    f'Cannot delete "{section.title}" - it has child sections'
                                ),
                            },
                            status=400,
                        )

                sections.delete()
                message = _("Selected sections deleted")
            else:
                return JsonResponse(
                    {"success": False, "error": _("Invalid action")}, status=400
                )

            logger.info(
                f'Bulk action "{action}" performed on {len(section_ids)} sections'
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": message,
                    "affected_count": len(section_ids),
                }
            )

        except Exception as e:
            logger.error(f"Error in bulk action: {str(e)}")
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse(
        {"success": False, "error": _("Invalid request method")}, status=405
    )


def section_navigation(request):
    """API endpoint for section navigation data"""
    try:
        tree_structure = Section.get_tree_structure()

        def create_nav_structure(tree):
            result = []
            for item in tree:
                nav_item = {
                    "id": item["section"].id,
                    "title": item["section"].title,
                    "slug": item["section"].slug,
                    "url": f"/sections/{item['section'].id}/",
                    "level": item["section"].level,
                    "has_children": bool(item["children"]),
                    "children": (
                        create_nav_structure(item["children"])
                        if item["children"]
                        else []
                    ),
                }
                result.append(nav_item)
            return result

        return JsonResponse(
            {"success": True, "navigation": create_nav_structure(tree_structure)}
        )

    except Exception as e:
        logger.error(f"Error creating navigation: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# Keep your original view
def my_view(request):
    """Your original view - preserved"""
    logger.info("section")
    return render(request, "sections/my_view.html")
