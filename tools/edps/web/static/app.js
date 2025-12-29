// Auto-save debouncing
let saveTimeout = null;
const SAVE_DELAY = 5000; // 5 seconds

function queueSave(form) {
    if (saveTimeout) {
        clearTimeout(saveTimeout);
    }
    saveTimeout = setTimeout(() => {
        htmx.trigger(form, 'save');
    }, SAVE_DELAY);
}

// Attach to all auto-save forms
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-autosave]').forEach(form => {
        form.addEventListener('input', () => queueSave(form));
    });
});

// Show save indicator briefly
document.body.addEventListener('htmx:afterSwap', (event) => {
    if (event.detail.target.classList.contains('save-indicator')) {
        event.detail.target.style.opacity = '1';
        setTimeout(() => {
            event.detail.target.style.opacity = '0';
        }, 2000);
    }
});
