// Place this file in: static/admin/js/email_broadcast.js

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the form
    toggleRecipientSelection(getSelectedRecipientType());
});

function loadTemplate(templateId) {
    if (!templateId) return;

    // Show loading indicator
    const subjectField = document.getElementById('id_subject');
    const contentField = document.querySelector('iframe[title="Rich Text Area"]');

    if (subjectField) {
        subjectField.style.opacity = '0.5';
    }

    // Make AJAX request to load template
    fetch(`/admin/emails/emailbroadcast/load-template/${templateId}/`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update subject field
                if (subjectField) {
                    subjectField.value = data.subject;
                    subjectField.style.opacity = '1';
                }

                // Update CKEditor content
                if (window.CKEDITOR) {
                    // Find the CKEditor instance
                    for (let instance in window.CKEDITOR.instances) {
                        if (instance.includes('content')) {
                            window.CKEDITOR.instances[instance].setData(data.content);
                            break;
                        }
                    }
                } else {
                    // Fallback for regular textarea
                    const contentTextarea = document.getElementById('id_content');
                    if (contentTextarea) {
                        contentTextarea.value = data.content;
                    }
                }

                // Show success message
                showMessage('Template loaded successfully!', 'success');
            } else {
                showMessage('Error loading template: ' + data.error, 'error');
                if (subjectField) {
                    subjectField.style.opacity = '1';
                }
            }
        })
        .catch(error => {
            console.error('Error loading template:', error);
            showMessage('Error loading template', 'error');
            if (subjectField) {
                subjectField.style.opacity = '1';
            }
        });
}

function toggleRecipientSelection(recipientType) {
    const customRecipientsField = document.querySelector('.field-custom_recipients');
    const recipientPreviewField = document.querySelector('.field-recipient_list_preview');

    if (customRecipientsField) {
        if (recipientType === 'custom') {
            customRecipientsField.style.display = 'block';
            updateRecipientPreview(recipientType);
        } else {
            customRecipientsField.style.display = 'none';
            updateRecipientPreview(recipientType);
        }
    }
}

function getSelectedRecipientType() {
    const recipientTypeInputs = document.querySelectorAll('input[name="recipient_type"]');
    for (let input of recipientTypeInputs) {
        if (input.checked) {
            return input.value;
        }
    }
    return 'all';
}

function updateRecipientPreview(recipientType) {
    const previewDiv = document.querySelector('.field-recipient_list_preview .readonly');
    if (!previewDiv) return;

    previewDiv.innerHTML = '<em>Loading recipient preview...</em>';

    let customRecipientIds = '';
    if (recipientType === 'custom') {
        const checkedBoxes = document.querySelectorAll('input[name="custom_recipients"]:checked');
        const ids = Array.from(checkedBoxes).map(cb => cb.value);
        customRecipientIds = ids.join(',');
    }

    // Make AJAX request to preview recipients
    const formData = new FormData();
    formData.append('recipient_type', recipientType);
    formData.append('custom_recipient_ids', customRecipientIds);
    formData.append('csrfmiddlewaretoken', getCsrfToken());

    fetch('/admin/emails/preview-recipients/', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            let html = `<strong>${data.count} recipients will receive this email</strong><br>`;
            if (data.recipients && data.recipients.length > 0) {
                html += '<ul style="margin-top: 10px; max-height: 200px; overflow-y: auto;">';
                data.recipients.forEach(recipient => {
                    const name = recipient.first_name && recipient.last_name ?
                        `${recipient.first_name} ${recipient.last_name}` :
                        'No name';
                    const badges = [];
                    if (recipient.is_superuser) badges.push('<span style="background: #dc3545; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.8em;">Superuser</span>');
                    if (recipient.is_staff) badges.push('<span style="background: #007bff; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.8em;">Staff</span>');

                    html += `<li style="margin-bottom: 5px;">
                        <strong>${recipient.email}</strong> (${name})
                        ${badges.length > 0 ? ' ' + badges.join(' ') : ''}
                    </li>`;
                });
                html += '</ul>';

                if (data.count > data.recipients.length) {
                    html += `<p><em>... and ${data.count - data.recipients.length} more recipients</em></p>`;
                }
            }
            previewDiv.innerHTML = html;
        } else {
            previewDiv.innerHTML = '<em style="color: #dc3545;">Error loading recipient preview</em>';
        }
    })
    .catch(error => {
        console.error('Error previewing recipients:', error);
        previewDiv.innerHTML = '<em style="color: #dc3545;">Error loading recipient preview</em>';
    });
}

function showMessage(message, type) {
    // Remove existing messages
    const existingMessages = document.querySelectorAll('.admin-message');
    existingMessages.forEach(msg => msg.remove());

    // Create new message
    const messageDiv = document.createElement('div');
    messageDiv.className = `admin-message alert alert-${type}`;
    messageDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        padding: 15px 20px;
        border-radius: 5px;
        color: white;
        font-weight: bold;
        max-width: 400px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        ${type === 'success' ? 'background-color: #28a745;' : 'background-color: #dc3545;'}
    `;
    messageDiv.textContent = message;

    document.body.appendChild(messageDiv);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.remove();
        }
    }, 5000);
}

function getCsrfToken() {
    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return csrfInput ? csrfInput.value : '';
}

// Add event listeners for custom recipient checkboxes
document.addEventListener('change', function(e) {
    if (e.target.name === 'custom_recipients') {
        const recipientType = getSelectedRecipientType();
        if (recipientType === 'custom') {
            updateRecipientPreview(recipientType);
        }
    }

    if (e.target.name === 'recipient_type') {
        toggleRecipientSelection(e.target.value);
    }
});

// Add recipient count validation
document.addEventListener('submit', function(e) {
    const recipientType = getSelectedRecipientType();
    if (recipientType === 'custom') {
        const checkedBoxes = document.querySelectorAll('input[name="custom_recipients"]:checked');
        if (checkedBoxes.length === 0) {
            e.preventDefault();
            showMessage('Please select at least one recipient for custom sending.', 'error');
            return false;
        }
    }
});