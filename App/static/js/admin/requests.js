// Admin requests page functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize user cards and their expandable sections
    initializeUserCards();
    
    // Initialize search functionality
    initializeSearch();
    
    // Make sure tabs are working correctly
    initializeTabs();
    
    // Hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.remove();
            }, 500);
        }, 5000);
    });
});

// Function to initialize the tabs
function initializeTabs() {
    const tabs = document.querySelectorAll('.tab');
    
    // Make sure the correct tab is active based on the current URL
    const currentPath = window.location.pathname;
    
    tabs.forEach(tab => {
        // For tabs that are direct links, make them active if the path matches
        const linkPath = tab.getAttribute('onclick');
        if (linkPath && linkPath.includes('window.location.href')) {
            // Extract the URL from the onclick attribute
            const matches = linkPath.match(/'([^']+)'/);
            if (matches && matches[1]) {
                const tabPath = matches[1];
                if (currentPath === tabPath) {
                    tab.classList.add('active');
                } else if (currentPath.includes('requests') && !currentPath.includes('registrations') && tabPath.includes('request')) {
                    tab.classList.add('active');
                } else {
                    tab.classList.remove('active');
                }
            }
        }
        
        // If the tab is not a direct link, handle click events to toggle active state
        tab.addEventListener('click', function() {
            // Only handle styling for tabs without direct links
            if (!this.getAttribute('onclick')) {
                tabs.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
            }
        });
    });
}

function initializeUserCards() {
    const userCards = document.querySelectorAll('.user-card');
    
    userCards.forEach(card => {
        card.addEventListener('click', function() {
            const userId = this.getAttribute('data-id');
            const detailsElement = document.getElementById(`details-${userId}`);
            const expandIcon = this.querySelector('.expand-icon');
            
            // Check if this card is already expanded
            const isExpanded = this.classList.contains('expanded');
            
            // First, collapse all cards
            document.querySelectorAll('.user-card').forEach(c => {
                c.classList.remove('expanded');
                c.querySelector('.expand-icon').textContent = 'expand_more';
            });
            
            document.querySelectorAll('.request-details').forEach(details => {
                details.style.display = 'none';
            });
            
            // Then, expand this card if it wasn't already expanded
            if (!isExpanded) {
                this.classList.add('expanded');
                expandIcon.textContent = 'expand_less';
                detailsElement.style.display = 'block';
            }
        });
    });
}

function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        
        document.querySelectorAll('.user-card').forEach(card => {
            const name = card.querySelector('.user-name').textContent.toLowerCase();
            const id = card.querySelector('.user-id').textContent.toLowerCase();
            const role = card.querySelector('.user-role').textContent.toLowerCase();
            
            if (name.includes(searchTerm) || id.includes(searchTerm) || role.includes(searchTerm)) {
                card.style.display = 'flex';
            } else {
                card.style.display = 'none';
                
                // Also hide the details section if card is hidden
                const userId = card.getAttribute('data-id');
                const detailsElement = document.getElementById(`details-${userId}`);
                if (detailsElement) {
                    detailsElement.style.display = 'none';
                }
            }
        });
    });
}

function approveRequest(requestId) {
    // Show confirmation dialog
    if (!confirm('Are you sure you want to approve this request?')) {
        return;
    }
    
    // Show loading overlay
    showLoading();
    
    // Make API call to approve the request
    fetch(`/api/requests/${requestId}/approve`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        // Hide loading overlay
        hideLoading();
        
        if (data.success) {
            // Update the UI
            const requestElement = findRequestElement(requestId);
            if (requestElement) {
                requestElement.classList.remove('pending');
                requestElement.classList.add('approved');
                
                const statusElement = requestElement.querySelector('.request-status');
                if (statusElement) {
                    statusElement.textContent = 'APPROVED';
                }
                
                // Remove the action buttons
                const actionsElement = requestElement.querySelector('.request-actions');
                if (actionsElement) {
                    actionsElement.remove();
                }
            }
            
            // Show success message
            showNotification('Request approved successfully', 'success');
        } else {
            showNotification(`Error: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        // Hide loading overlay
        hideLoading();
        
        console.error('Error:', error);
        showNotification('An error occurred while approving the request', 'error');
    });
}

function rejectRequest(requestId) {
    // Show confirmation dialog
    if (!confirm('Are you sure you want to reject this request?')) {
        return;
    }
    
    // Show loading overlay
    showLoading();
    
    // Make API call to reject the request
    fetch(`/api/requests/${requestId}/reject`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        // Hide loading overlay
        hideLoading();
        
        if (data.success) {
            // Update the UI
            const requestElement = findRequestElement(requestId);
            if (requestElement) {
                requestElement.classList.remove('pending');
                requestElement.classList.add('rejected');
                
                const statusElement = requestElement.querySelector('.request-status');
                if (statusElement) {
                    statusElement.textContent = 'REJECTED';
                }
                
                // Remove the action buttons
                const actionsElement = requestElement.querySelector('.request-actions');
                if (actionsElement) {
                    actionsElement.remove();
                }
            }
            
            // Show success message
            showNotification('Request rejected', 'success');
        } else {
            showNotification(`Error: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        // Hide loading overlay
        hideLoading();
        
        console.error('Error:', error);
        showNotification('An error occurred while rejecting the request', 'error');
    });
}

function findRequestElement(requestId) {
    // Find the request element by its ID
    const requestElements = document.querySelectorAll('.request-item');
    for (const element of requestElements) {
        // Check if this element has an approve/reject button with the right request ID
        const approveButton = element.querySelector(`.btn-approve[onclick*="${requestId}"]`);
        const rejectButton = element.querySelector(`.btn-reject[onclick*="${requestId}"]`);
        
        if (approveButton || rejectButton) {
            return element;
        }
    }
    
    return null;
}

function showLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
    }
}

function hideLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
}

function showNotification(message, type = 'info') {
    // Create a notification element
    const notification = document.createElement('div');
    notification.className = `flash-message ${type}`;
    notification.textContent = message;
    
    // Add the notification to the page
    document.body.appendChild(notification);
    
    // Remove the notification after a delay
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 500);
    }, 5000);
}