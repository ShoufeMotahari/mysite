# sections/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from ckeditor_uploader.fields import RichTextUploadingField
from django.utils.text import slugify

SECTION_TYPE_CHOICES = [
    ('hero', 'بنر اصلی (Hero)'),
    ('about', 'درباره ما'),
    ('services', 'خدمات'),
    ('gallery', 'گالری تصاویر'),
    ('contact', 'تماس با ما'),
    ('cta', 'دعوت به اقدام (CTA)'),
    ('custom', 'سفارشی'),
]


class Section(models.Model):
    title = models.CharField(max_length=200, verbose_name=_('Title'))
    slug = models.SlugField(max_length=250, unique=True, blank=True, verbose_name=_('Slug'))
    section_type = models.CharField(
        max_length=20,
        choices=SECTION_TYPE_CHOICES,
        default='custom',
        verbose_name=_('نوع سکشن')
    )
    content = RichTextUploadingField(verbose_name=_('Content'), blank=True)
    order = models.PositiveIntegerField(default=0, verbose_name=_('Order'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_('Parent Section'),
        related_name='children'
    )
    level = models.PositiveIntegerField(default=1, verbose_name=_('Level'))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        ordering = ['level', 'order']
        verbose_name = _('Section')
        verbose_name_plural = _('Sections')

    def __str__(self):
        level_indicator = "—" * (self.level - 1)
        return f"{level_indicator} {self.title}" if self.level > 1 else self.title

    def clean(self):
        if self.parent:
            if self.parent.level >= 3:
                raise ValidationError(_('Maximum 3 levels allowed.'))
            self.level = self.parent.level + 1
        else:
            self.level = 1

        if self.level == 1 and not self.pk:
            root_sections_count = Section.objects.filter(level=1).count()
            if root_sections_count >= 7:
                raise ValidationError(_('Maximum 7 root sections allowed'))

        if self.parent and self.pk:
            current = self.parent
            while current:
                if current.pk == self.pk:
                    raise ValidationError(_('Cannot set self or descendant as parent'))
                current = current.parent

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            if self.parent:
                self.slug = f"{self.parent.slug}-{base_slug}"
            else:
                self.slug = base_slug

        self.level = self.parent.level + 1 if self.parent else 1

        if not self.order:
            max_order = Section.objects.filter(parent=self.parent if self.parent else None).aggregate(
                max_order=models.Max('order'))['max_order'] or 0
            self.order = max_order + 1

        super().save(*args, **kwargs)

    def get_descendants(self):
        """Get all descendant sections (children, grandchildren, etc.)"""
        descendants = []

        def collect_descendants(section):
            for child in section.children.all():
                descendants.append(child)
                collect_descendants(child)

        collect_descendants(self)
        return descendants

    def get_ancestors(self):
        """Get all ancestor sections (parent, grandparent, etc.)"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors

    @property
    def full_path(self):
        """Get the full hierarchical path of the section"""
        path_parts = []
        current = self
        while current:
            path_parts.insert(0, current.title)
            current = current.parent
        return ' > '.join(path_parts)

    @property
    def breadcrumb_path(self):
        """Get breadcrumb path for navigation"""
        return ' / '.join([ancestor.title for ancestor in reversed(self.get_ancestors())] + [self.title])

    def can_have_children(self):
        """Check if this section can have children based on level"""
        return self.level < 3

    def get_siblings(self):
        """Get sections at the same level with the same parent"""
        return Section.objects.filter(parent=self.parent, level=self.level).exclude(pk=self.pk)

    def get_next_sibling(self):
        """Get the next sibling by order"""
        return self.get_siblings().filter(order__gt=self.order).order_by('order').first()

    def get_previous_sibling(self):
        """Get the previous sibling by order"""
        return self.get_siblings().filter(order__lt=self.order).order_by('-order').first()

    def move_to_position(self, new_order):
        """Move section to a new position within its level"""
        old_order = self.order

        if new_order == old_order:
            return

        siblings = Section.objects.filter(parent=self.parent, level=self.level).exclude(pk=self.pk)

        if new_order > old_order:
            # Moving down - shift others up
            siblings.filter(order__gt=old_order, order__lte=new_order).update(order=models.F('order') - 1)
        else:
            # Moving up - shift others down
            siblings.filter(order__gte=new_order, order__lt=old_order).update(order=models.F('order') + 1)

        self.order = new_order
        self.save(update_fields=['order'])

    @classmethod
    def get_active_sections(cls):
        return cls.objects.filter(is_active=True).order_by('level', 'order')

    @classmethod
    def get_tree_structure(cls):
        """Get hierarchical tree structure of all active sections"""
        root_sections = cls.objects.filter(level=1, is_active=True).order_by('order')

        def build_tree(sections):
            tree = []
            for section in sections:
                tree.append({
                    'section': section,
                    'children': build_tree(section.children.filter(is_active=True).order_by('order'))
                })
            return tree

        return build_tree(root_sections)

    @classmethod
    def get_flat_tree(cls):
        """Get flattened tree structure for easier iteration"""

        def flatten_tree(tree, depth=0):
            flat = []
            for node in tree:
                section = node['section']
                section._tree_depth = depth
                flat.append(section)
                flat.extend(flatten_tree(node['children'], depth + 1))
            return flat

        return flatten_tree(cls.get_tree_structure())

    @classmethod
    def reorder_sections(cls, section_ids):
        """Reorder sections based on provided ID list"""
        for index, section_id in enumerate(section_ids, start=1):
            cls.objects.filter(id=section_id).update(order=index)

    @classmethod
    def reorder_level(cls, level, section_ids):
        """Reorder sections within a specific level"""
        for index, section_id in enumerate(section_ids, start=1):
            cls.objects.filter(id=section_id, level=level).update(order=index)

    @classmethod
    def get_level_statistics(cls):
        """Get statistics for each level"""
        from django.db.models import Count

        stats = {}
        for level in range(1, 4):
            stats[level] = {
                'total': cls.objects.filter(level=level).count(),
                'active': cls.objects.filter(level=level, is_active=True).count(),
                'inactive': cls.objects.filter(level=level, is_active=False).count(),
            }
        return stats

    @classmethod
    def get_max_order_for_level(cls, level, parent=None):
        """Get maximum order for a specific level"""
        queryset = cls.objects.filter(level=level)
        if parent:
            queryset = queryset.filter(parent=parent)
        else:
            queryset = queryset.filter(parent__isnull=True)

        max_order = queryset.aggregate(max_order=models.Max('order'))['max_order']
        return max_order or 0

    def duplicate(self, new_title=None):
        """Create a duplicate of this section"""
        new_title = new_title or f"{self.title} (Copy)"

        # Create duplicate
        duplicate = Section.objects.create(
            title=new_title,
            section_type=self.section_type,
            content=self.content,
            parent=self.parent,
            order=self.get_max_order_for_level(self.level, self.parent) + 1,
            is_active=False  # Start as inactive
        )

        return duplicate

    @property
    def display_title(self):
        """Get display title with hierarchy numbering"""
        if self.level == 1:
            return f"{self.order}. {self.title}"
        elif self.level == 2:
            parent_order = self.parent.order if self.parent else 1
            return f"{parent_order}.{self.order}. {self.title}"
        elif self.level == 3:
            grandparent_order = self.parent.parent.order if self.parent and self.parent.parent else 1
            parent_order = self.parent.order if self.parent else 1
            return f"{grandparent_order}.{parent_order}.{self.order}. {self.title}"
        return self.title

    @property
    def level_color(self):
        """Get color associated with the level"""
        colors = {1: '#28a745', 2: '#ffc107', 3: '#dc3545'}
        return colors.get(self.level, '#6c757d')

    @property
    def is_root(self):
        """Check if this is a root section"""
        return self.level == 1

    @property
    def is_leaf(self):
        """Check if this section has no children"""
        return not self.children.exists()

    def __unicode__(self):
        return self.__str__()