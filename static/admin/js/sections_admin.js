// static/admin/js/sections_admin.js

(function($) {
    'use strict';

    $(document).ready(function() {

        // Add sections-admin class to body for styling
        $('body').addClass('sections-admin');

        // Enhanced hierarchy stats display
        if ($('.hierarchy-stats').length) {
            enhanceHierarchyStats();
        }

        // Add confirmation for critical actions
        $('.delete-link').on('click', function(e) {
            if (!confirm('Are you sure you want to delete this section? This action cannot be undone.')) {
                e.preventDefault();
                return false;
            }
        });

        // Auto-select parent when adding child sections
        const urlParams = new URLSearchParams(window.location.search);
        const parentId = urlParams.get('parent');
        if (parentId && $('#id_parent').length) {
            $('#id_parent').val(parentId);
            showParentInfo(parentId);
        }

        // Show parent information when parent is selected
        $('#id_parent').on('change', function() {
            const selectedParentId = $(this).val();
            if (selectedParentId) {
                showParentInfo(selectedParentId);
            } else {
                hideParentInfo();
            }
        });

        // Enhance section type display
        enhanceSectionTypeDisplay();

        // Add keyboard shortcuts
        addKeyboardShortcuts();

        // Initialize tooltips if available
        if (typeof $.fn.tooltip === 'function') {
            $('[title]').tooltip();
        }

        // Auto-save draft functionality
        initAutoSave();
    });

    function enhanceHierarchyStats() {
        const statsContainer = $('.hierarchy-stats');
        if (statsContainer.length) {
            const statsData = statsContainer.data('stats');
            if (statsData) {
                renderStatsGrid(statsContainer, statsData);
            }
        }
    }

    function renderStatsGrid(container, stats) {
        const grid = $('<div class="stats-grid"></div>');

        Object.keys(stats).forEach(function(key) {
            const value = stats[key];
            const label = key.replace(/_/g, ' ').toUpperCase();

            const statItem = $(`
                <div class="stat-item">
                    <span class="stat-number">${value}</span>
                    <span class="stat-label">${label}</span>
                </div>
            `);

            grid.append(statItem);
        });

        container.append(grid);
    }

    function showParentInfo(parentId) {
        // Show information about the selected parent
        $.get(`/admin/sections/section/${parentId}/change/`, function(data) {
            const parentTitle = $(data).find('#id_title').val();
            const parentLevel = $(data).find('#id_level').val();

            if (parentTitle) {
                const infoHtml = `
                    <div class="hierarchy-info">
                        <strong>Parent Section:</strong> ${parentTitle}<br>
                        <strong>New Section Level:</strong> ${parseInt(parentLevel) + 1}
                    </div>
                `;

                $('.field-parent').after(infoHtml);
            }
        }).fail(function() {
            console.log('Could not fetch parent information');
        });
    }

    function hideParentInfo() {
        $('.hierarchy-info').remove();
    }

    function enhanceSectionTypeDisplay() {
        const sectionTypeField = $('#id_section_type');
        if (sectionTypeField.length) {
            sectionTypeField.on('change', function() {
                const selectedType = $(this).val();
                updateSectionTypeHelp(selectedType);
            });

            // Initial update
            updateSectionTypeHelp(sectionTypeField.val());
        }
    }

    function updateSectionTypeHelp(sectionType) {
        const helpTexts = {
            'hero': 'Hero section typically appears at the top of the page with a large banner or featured content.',
            'about': 'About section contains information about your organization or service.',
            'services': 'Services section showcases the different services or products offered.',
            'gallery': 'Gallery section displays images or media content.',
            'contact': 'Contact section includes contact information and forms.',
            'cta': 'Call-to-Action section encourages users to take specific actions.',
            'custom': 'Custom section for any other type of content.'
        };

        const helpText = helpTexts[sectionType] || '';

        // Remove existing help
        $('.section-type-help').remove();

        if (helpText) {
            const helpElement = $(`<p class="help section-type-help">${helpText}</p>`);
            $('#id_section_type').after(helpElement);
        }
    }

    function addKeyboardShortcuts() {
        $(document).on('keydown', function(e) {
            // Ctrl+S or Cmd+S to save
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                const saveButton = $('.submit-row input[type="submit"]').first();
                if (saveButton.length) {
                    saveButton.click();
                }
            }

            // Escape to cancel/go back
            if (e.key === 'Escape') {
                const cancelLink = $('.submit-row a').first();
                if (cancelLink.length) {
                    window.location.href = cancelLink.attr('href');
                }
            }
        });
    }

    function initAutoSave() {
        const form = $('form#section_form');
        if (form.length && window.localStorage) {
            const formId = 'section_form_' + (form.find('#id_id').val() || 'new');

            // Load saved data
            loadFormData(form, formId);

            // Save on input change
            form.find('input, textarea, select').on('change input', function() {
                saveFormData(form, formId);
            });

            // Clear saved data on successful submit
            form.on('submit', function() {
                localStorage.removeItem(formId);
            });
        }
    }

    function saveFormData(form, formId) {
        const formData = {};
        form.find('input, textarea, select').each(function() {
            const element = $(this);
            const name = element.attr('name');
            if (name && name !== 'csrfmiddlewaretoken') {
                if (element.is(':checkbox') || element.is(':radio')) {
                    formData[name] = element.is(':checked');
                } else {
                    formData[name] = element.val();
                }
            }
        });

        try {
            localStorage.setItem(formId, JSON.stringify(formData));
        } catch (e) {
            console.log('Could not save form data:', e);
        }
    }

    function loadFormData(form, formId) {
        try {
            const savedData = localStorage.getItem(formId);
            if (savedData) {
                const formData = JSON.parse(savedData);

                Object.keys(formData).forEach(function(name) {
                    const element = form.find(`[name="${name}"]`);
                    const value = formData[name];

                    if (element.length) {
                        if (element.is(':checkbox') || element.is(':radio')) {
                            element.prop('checked', value);
                        } else {
                            element.val(value);
                        }
                    }
                });

                // Show notification
                showAutoSaveNotification();
            }
        } catch (e) {
            console.log('Could not load form data:', e);
        }
    }

    function showAutoSaveNotification() {
        const notification = $(`
            <div class="auto-save-notification" style="
                background: #fff3cd; 
                border: 1px solid #ffeaa7; 
                color: #856404; 
                padding: 10px; 
                margin: 10px 0; 
                border-radius: 4px;
            ">
                <strong>Auto-saved data restored.</strong> 
                Your previous changes have been restored from local storage.
                <button type="button" style="float: right; background: none; border: none; color: #856404; cursor: pointer;" onclick="$(this).parent().remove();">×</button>
            </div>
        `);

        $('form').prepend(notification);

        // Auto-hide after 5 seconds
        setTimeout(function() {
            notification.fadeOut();
        }, 5000);
    }

    // Utility functions for other scripts
    window.SectionsAdmin = {
        showMessage: function(message, type) {
            type = type || 'info';
            const messageHtml = `
                <div class="alert alert-${type}" style="
                    padding: 10px 15px; 
                    margin: 10px 0; 
                    border-radius: 4px; 
                    background: ${type === 'success' ? '#d4edda' : type === 'error' ? '#f8d7da' : '#d1ecf1'};
                    color: ${type === 'success' ? '#155724' : type === 'error' ? '#721c24' : '#0c5460'};
                    border: 1px solid ${type === 'success' ? '#c3e6cb' : type === 'error' ? '#f5c6cb' : '#bee5eb'};
                ">
                    ${message}
                    <button type="button" style="float: right; background: none; border: none; cursor: pointer;" onclick="$(this).parent().remove();">×</button>
                </div>
            `;

            $('body').prepend(messageHtml);

            // Auto-hide after 5 seconds
            setTimeout(function() {
                $('.alert').fadeOut();
            }, 5000);
        },

        confirmAction: function(message, callback) {
            if (confirm(message)) {
                if (typeof callback === 'function') {
                    callback();
                }
                return true;
            }
            return false;
        }
    };

})(django.jQuery || jQuery);