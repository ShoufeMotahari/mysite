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

    @classmethod
    def get_active_sections(cls):
        return cls.objects.filter(is_active=True).order_by('level', 'order')

    @classmethod
    def get_tree_structure(cls):
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
    def reorder_sections(cls, section_ids):
        for index, section_id in enumerate(section_ids, start=1):
            cls.objects.filter(id=section_id).update(order=index)

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