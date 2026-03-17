// Zava Web Application JavaScript

// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent):not(.alert-persistent)');
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
const brandColor = getComputedStyle(document.documentElement).getPropertyValue('--dt-primary').trim();
console.log('%cZava', `font-size: 24px; font-weight: bold; color: ${brandColor};`);
console.log('%cAI-Powered Last-Mile Delivery Management System', 'font-size: 14px; color: #6c757d;');
console.log('Version: 1.0.0');

// ===== MOBILE OPTIMIZATIONS =====

// Highlight active bottom nav link
document.addEventListener('DOMContentLoaded', function() {
    const bottomNav = document.querySelector('.mobile-bottom-nav');
    if (bottomNav) {
        const currentPath = window.location.pathname;
        const links = bottomNav.querySelectorAll('.nav-link');
        links.forEach(link => {
            const href = link.getAttribute('href');
            if (href && href !== '#' && currentPath.startsWith(href)) {
                link.classList.add('active');
            }
        });
    }
});

// Detect mobile and add body class
document.addEventListener('DOMContentLoaded', function() {
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
        || window.innerWidth <= 768;
    if (isMobile) {
        document.body.classList.add('is-mobile');
    }

    // Update on resize
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(function() {
            if (window.innerWidth <= 768) {
                document.body.classList.add('is-mobile');
            } else {
                document.body.classList.remove('is-mobile');
            }
        }, 250);
    });
});

// Close mobile menu on nav item click
document.addEventListener('DOMContentLoaded', function() {
    const navLinks = document.querySelectorAll('.navbar-collapse .nav-link:not(.dropdown-toggle)');
    const navCollapse = document.querySelector('.navbar-collapse');
    if (navCollapse) {
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                if (window.innerWidth <= 991) {
                    const bsCollapse = bootstrap.Collapse.getInstance(navCollapse);
                    if (bsCollapse) bsCollapse.hide();
                }
            });
        });
    }
});

// Fix iOS viewport height issue (100vh includes address bar)
function setMobileVH() {
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--mobile-vh', `${vh}px`);
}
setMobileVH();
window.addEventListener('resize', setMobileVH);

// Prevent double-tap zoom on buttons (iOS)
document.addEventListener('DOMContentLoaded', function() {
    if (/iPhone|iPad|iPod/.test(navigator.userAgent)) {
        const buttons = document.querySelectorAll('.btn, .nav-link, .list-group-item-action');
        buttons.forEach(btn => {
            btn.addEventListener('touchend', function(e) {
                e.preventDefault();
                this.click();
            }, { passive: false });
        });
    }
});
