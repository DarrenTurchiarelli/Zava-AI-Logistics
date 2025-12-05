// DT Logistics Web Application JavaScript

// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Search functionality with debounce
let searchTimeout;
function searchParcels(query) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        fetch(`/api/parcels/search?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('Search results:', data.results);
                    // Update UI with results
                } else {
                    console.error('Search failed:', data.error);
                }
            })
            .catch(error => console.error('Search error:', error));
    }, 300);
}

// Form validation helper
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    if (!form.checkValidity()) {
        form.classList.add('was-validated');
        return false;
    }
    return true;
}

// Loading state management
function setLoadingState(element, loading) {
    if (loading) {
        element.disabled = true;
        element.dataset.originalHtml = element.innerHTML;
        element.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
    } else {
        element.disabled = false;
        if (element.dataset.originalHtml) {
            element.innerHTML = element.dataset.originalHtml;
        }
    }
}

// Real-time stats updater
function updateStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            console.log('Stats updated:', data);
            // Update dashboard elements if they exist
            const totalParcels = document.getElementById('totalParcels');
            if (totalParcels) {
                totalParcels.textContent = data.total_parcels;
            }
            
            const pendingApprovals = document.getElementById('pendingApprovals');
            if (pendingApprovals) {
                pendingApprovals.textContent = data.pending_approvals;
            }
        })
        .catch(error => console.error('Stats update failed:', error));
}

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Initialize popovers
document.addEventListener('DOMContentLoaded', function() {
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// Copy to clipboard helper
function copyToClipboard(text, buttonElement) {
    navigator.clipboard.writeText(text).then(() => {
        const originalText = buttonElement.innerHTML;
        buttonElement.innerHTML = '<i class="bi bi-check"></i> Copied!';
        buttonElement.classList.add('btn-success');
        
        setTimeout(() => {
            buttonElement.innerHTML = originalText;
            buttonElement.classList.remove('btn-success');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

// Confirmation dialogs
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Format tracking number for display
function formatTrackingNumber(trackingNumber) {
    return trackingNumber.replace(/(.{4})/g, '$1 ').trim();
}

// Status badge color helper
function getStatusBadgeClass(status) {
    const statusMap = {
        'Registered': 'bg-secondary',
        'Collected': 'bg-secondary',
        'At Depot': 'bg-warning',
        'Sorting': 'bg-warning',
        'In Transit': 'bg-primary',
        'Out for Delivery': 'bg-info',
        'Delivered': 'bg-success',
        'Exception': 'bg-warning',
        'Returned': 'bg-danger'
    };
    return statusMap[status] || 'bg-secondary';
}

// Auto-refresh for dashboard (every 30 seconds)
if (window.location.pathname === '/dashboard') {
    setInterval(updateStats, 30000);
}

// Print functionality
function printPage() {
    window.print();
}

// Export data helper
function exportData(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// Console welcome message
console.log('%cDT Logistics', 'font-size: 24px; font-weight: bold; color: #0d6efd;');
console.log('%cAI-Powered Last-Mile Delivery Management System', 'font-size: 14px; color: #6c757d;');
console.log('Version: 1.0.0');
