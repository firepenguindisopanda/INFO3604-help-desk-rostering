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
            message.style.transform = 'translateY(-10px)';
            setTimeout(() => {
                if (message.parentNode) {
                    message.parentNode.removeChild(message);
                }
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
                const icon = c.querySelector('.expand-icon');
                if (icon) {
                    icon.textContent = 'expand_more';
                }
            });
            
            document.querySelectorAll('.request-details').forEach(details => {
                details.style.display = 'none';
            });
            
            // Then, expand this card if it wasn't already expanded
            if (!isExpanded) {
                this.classList.add('expanded');
                if (expandIcon) {
                    expandIcon.textContent = 'expand_less';
                }
                
                // Apply smooth display transition for details
                if (detailsElement) {
                    detailsElement.style.display = 'block';
                    detailsElement.style.animation = 'fadeIn 0.3s ease';
                }
            }
        });
    });
}

function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        let foundResults = false;
        
        document.querySelectorAll('.user-card').forEach(card => {
            const name = card.querySelector('.user-name').textContent.toLowerCase();
            const id = card.querySelector('.user-id').textContent.toLowerCase();
            const role = card.querySelector('.user-role').textContent.toLowerCase();
            
            if (name.includes(searchTerm) || id.includes(searchTerm) || role.includes(searchTerm)) {
                card.style.display = 'flex';
                foundResults = true;
                
                // Optional: Highlight the matching text for better UX
                if (searchTerm.length > 1) {
                    highlightMatch(card.querySelector('.user-name'), name, searchTerm);
                    highlightMatch(card.querySelector('.user-id'), id, searchTerm);
                    highlightMatch(card.querySelector('.user-role'), role, searchTerm);
                }
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
        
        // Show/hide "no results" message
        const emptyMessage = document.querySelector('.empty-message');
        if (emptyMessage) {
            if (searchTerm.length > 0 && !foundResults) {
                emptyMessage.style.display = 'block';
                emptyMessage.querySelector('p').textContent = `No results found for "${searchTerm}"`;
            } else if (document.querySelectorAll('.user-card').length === 0) {
                emptyMessage.style.display = 'block';
                emptyMessage.querySelector('p').textContent = 'No requests found in the system.';
            } else {
                emptyMessage.style.display = 'none';
            }
        }
    });
}

// Optional helper function to highlight matching text in search results
function highlightMatch(element, text, searchTerm) {
    // Skip if element doesn't exist
    if (!element) return;
    
    // Reset the element text first
    element.innerHTML = text;
    
    // Find the match location
    const matchIndex = text.toLowerCase().indexOf(searchTerm.toLowerCase());
    if (matchIndex >= 0) {
        const prefix = text.substring(0, matchIndex);
        const match = text.substring(matchIndex, matchIndex + searchTerm.length);
        const suffix = text.substring(matchIndex + searchTerm.length);
        
        // Create highlighted text
        element.innerHTML = prefix + 
            `<span style="background-color: rgba(255, 243, 160, 0.5); padding: 0 2px; border-radius: 2px;">${match}</span>` + 
            suffix;
    }
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
        // Add slight delay to make it look more natural
        setTimeout(() => {
            loadingOverlay.style.display = 'none';
        }, 300);
    }
}

function showNotification(message, type = 'info') {
    // Remove any existing notifications first
    document.querySelectorAll('.flash-message').forEach(el => {
        if (el.parentNode) el.parentNode.removeChild(el);
    });
    
    // Create a notification element
    const notification = document.createElement('div');
    notification.className = `flash-message ${type}`;
    
    // Add icon based on notification type
    if (type === 'success') {
        notification.innerHTML = `<span style="margin-right: 8px;">✓</span>${message}`;
    } else if (type === 'error') {
        notification.innerHTML = `<span style="margin-right: 8px;">⚠️</span>${message}`;
    } else {
        notification.textContent = message;
    }
    
    // Add the notification to the page
    document.body.appendChild(notification);
    
    // Remove the notification after a delay
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateY(-10px)';
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 500);
    }, 5000);
}