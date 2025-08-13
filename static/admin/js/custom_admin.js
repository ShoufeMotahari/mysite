document.addEventListener('DOMContentLoaded', function() {
    // Ensure action dropdown is visible and styled properly
    const actionSelect = document.querySelector('.actions select');
    if (actionSelect) {
        actionSelect.style.visibility = 'visible';
        actionSelect.style.opacity = '1';
    }
});