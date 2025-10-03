// Registration Requests Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize search functionality
    initializeSearch();
    
    // Add animation to registration cards
    animateRegistrationCards();
    
    // Add profile picture preview modal
    setupProfilePicturePreview();
    
    // Hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            message.style.transform = 'translate(-50%, -10px)';
            setTimeout(() => {
                if (message.parentNode) {
                    message.parentNode.removeChild(message);
                }
            }, 500);
        }, 5000);
    });
});

/**
* Setup profile picture preview functionality
*/
function setupProfilePicturePreview() {
    // Create profile preview modal and append to body
    const body = document.querySelector('body');
    
    // Create profile preview modal if it doesn't exist
    if (!document.querySelector('.profile-preview-modal')) {
        const profilePreviewModal = document.createElement('div');
        profilePreviewModal.className = 'profile-preview-modal';
        profilePreviewModal.innerHTML = `
            <div class="profile-preview-content">
                <div class="profile-preview-close">&times;</div>
                <img id="profilePreviewImage" src="" alt="Profile Picture Preview">
            </div>
        `;
        body.appendChild(profilePreviewModal);
    }
    
    // Handle click on profile image or view profile picture links
    const profileImages = document.querySelectorAll('.registration-profile-image img, .view-profile-pic');
    profileImages.forEach(img => {
        img.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Get the image source
            let imageSrc;
            if (this.tagName.toLowerCase() === 'img') {
                imageSrc = this.src;
            } else { // It's a link
                imageSrc = this.href;
            }
            
            // Set the image in the modal
            document.getElementById('profilePreviewImage').src = imageSrc;
            
            // Show the modal
            document.querySelector('.profile-preview-modal').style.display = 'block';
        });
    });
    
    // Close the modal when clicking the close button
    const closeBtn = document.querySelector('.profile-preview-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            document.querySelector('.profile-preview-modal').style.display = 'none';
        });
    }
    
    // Close the modal when clicking outside the image
    const profilePreviewModal = document.querySelector('.profile-preview-modal');
    if (profilePreviewModal) {
        profilePreviewModal.addEventListener('click', function(e) {
            if (e.target === profilePreviewModal) {
                profilePreviewModal.style.display = 'none';
            }
        });
    }
}
  
/**
* Initialize search functionality for registration cards
*/
function initializeSearch() {
    const searchInput = document.getElementById('registrationSearchInput');
    if (!searchInput) return;
    
    // Add transition styles to registration cards for smoother filtering
    const registrationCards = document.querySelectorAll('.registration-card');
    registrationCards.forEach(card => {
        card.style.transition = 'all 0.3s ease, opacity 0.3s ease, transform 0.3s ease';
    });
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        let foundResults = false;
        
        // Create counters for each section
        const sectionCounts = {
            'pendingRegistrations': 0,
            'approvedRegistrations': 0,
            'rejectedRegistrations': 0
        };
        
        // Search in all registration cards (pending, approved, and rejected)
        registrationCards.forEach(card => {
            const name = card.getAttribute('data-name').toLowerCase();
            const id = card.getAttribute('data-id').toLowerCase();
            const parent = card.parentNode.id;
            
            if (name.includes(searchTerm) || id.includes(searchTerm)) {
                card.style.display = 'block';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
                foundResults = true;
                
                // Increment counter for this section
                if (sectionCounts.hasOwnProperty(parent)) {
                    sectionCounts[parent]++;
                }
                
                // Optional: Highlight the matching text
                if (searchTerm.length > 1) {
                    highlightMatch(card.querySelector('.registration-name'), name, searchTerm);
                    highlightMatch(card.querySelector('.registration-id'), id, searchTerm);
                }
            } else {
                card.style.opacity = '0';
                card.style.transform = 'translateY(10px)';
                
                // Hide after transition completes
                setTimeout(() => {
                    if (!name.includes(searchTerm) && !id.includes(searchTerm)) {
                        card.style.display = 'none';
                    }
                }, 300);
            }
        });
        
        // Check if each section is now empty after filtering
        checkEmptySections(sectionCounts, searchTerm);
    });
}
  
/**
* Highlight matching text in registration information
*/
function highlightMatch(element, text, searchTerm) {
    // Skip if element doesn't exist
    if (!element) return;
    
    // Get original text content
    const originalText = element.textContent;
    
    // Find the match location (case insensitive)
    const lowerText = originalText.toLowerCase();
    const matchIndex = lowerText.indexOf(searchTerm.toLowerCase());
    
    if (matchIndex >= 0) {
        // Extract parts of the text
        const prefix = originalText.substring(0, matchIndex);
        const match = originalText.substring(matchIndex, matchIndex + searchTerm.length);
        const suffix = originalText.substring(matchIndex + searchTerm.length);
        
        // Create highlighted text with span
        element.innerHTML = prefix + 
            `<span style="background-color: rgba(255, 243, 160, 0.5); padding: 0 2px; border-radius: 2px; font-weight: 600;">${match}</span>` + 
            suffix;
    }
}
  
/**
* Check if sections are empty after filtering and show appropriate messages
*/
function checkEmptySections(sectionCounts, searchTerm) {
    // Messages for each section
    const sections = [
        { 
            containerId: 'pendingRegistrations', 
            message: 'No pending registration requests matching your search.',
            count: sectionCounts.pendingRegistrations
        },
        { 
            containerId: 'approvedRegistrations', 
            message: 'No approved registration requests matching your search.',
            count: sectionCounts.approvedRegistrations
        },
        { 
            containerId: 'rejectedRegistrations', 
            message: 'No rejected registration requests matching your search.',
            count: sectionCounts.rejectedRegistrations
        }
    ];
    
    sections.forEach(section => {
        const container = document.getElementById(section.containerId);
        if (!container) return;
        
        // Remove existing "no results" message
        const existingNoResults = container.querySelector('.no-registrations.search-results');
        if (existingNoResults) {
            existingNoResults.remove();
        }
        
        // Only add "no results" message if there are cards but none are visible due to search
        const totalCards = container.querySelectorAll('.registration-card').length;
        
        if (searchTerm && totalCards > 0 && section.count === 0) {
            const noResults = document.createElement('div');
            noResults.className = 'no-registrations search-results';
            noResults.innerHTML = `<p>${section.message}</p>`;
            container.appendChild(noResults);
            
            // Add fade-in animation
            noResults.style.animation = 'fadeIn 0.3s ease';
        }
    });
}
  
/**
* Add entrance animations to registration cards
*/
function animateRegistrationCards() {
    const registrationCards = document.querySelectorAll('.registration-card');
    
    registrationCards.forEach((card, index) => {
        // Set initial state
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        // Create staggered animation
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 50 * index);
    });
}
  
/**
* Custom confirmation dialog
*/
function showConfirmation(message, onConfirm) {
    const modal = document.getElementById('confirmationModal');
    const confirmMessage = document.getElementById('confirmMessage');
    const confirmOk = document.getElementById('confirmOk');
    const confirmCancel = document.getElementById('confirmCancel');
    
    // Set the confirmation message
    confirmMessage.textContent = message;
    
    // Show the modal
    modal.style.display = 'block';
    
    // Setup event handlers for the buttons
    const handleConfirm = () => {
        modal.style.display = 'none';
        removeEventListeners();
        onConfirm();
    };
    
    const handleCancel = () => {
        modal.style.display = 'none';
        removeEventListeners();
    };
    
    const removeEventListeners = () => {
        confirmOk.removeEventListener('click', handleConfirm);
        confirmCancel.removeEventListener('click', handleCancel);
    };
    
    // Add event listeners
    confirmOk.addEventListener('click', handleConfirm);
    confirmCancel.addEventListener('click', handleCancel);
}
  
/**
* Approve registration request
*/
function getCsrfToken() {
    const value = `; ${document.cookie}`;
    const parts = value.split('; csrf_access_token=');
    if (parts.length === 2) {
        return parts.pop().split(';').shift();
    }
    return null;
}

function buildAuthHeaders() {
    const headers = {
        'Content-Type': 'application/json'
    };

    const csrfToken = getCsrfToken();
    if (csrfToken) {
        headers['X-CSRF-TOKEN'] = csrfToken;
    }

    return headers;
}

function approveRegistration(registrationId) {
    // Show custom confirmation dialog
    showConfirmation('Are you sure you want to approve this registration request?', () => {
        // Show loading overlay
        showLoading();
        
        // Make API call to approve the registration
        fetch(`/api/registrations/${registrationId}/approve`, {
            method: 'POST',
            headers: buildAuthHeaders(),
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            // Hide loading overlay
            hideLoading();
            
            if (data.success) {
                // Show success message
                showNotification('Registration approved successfully', 'success');
                
                // Reload the page after a short delay
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showNotification(`Error: ${data.message}`, 'error');
            }
        })
        .catch(error => {
            // Hide loading overlay
            hideLoading();
            
            console.error('Error:', error);
            showNotification('An error occurred while approving the registration', 'error');
        });
    });
}
  
/**
* Reject registration request
*/
function rejectRegistration(registrationId) {
    // Show custom confirmation dialog
    showConfirmation('Are you sure you want to reject this registration request?', () => {
        // Show loading overlay
        showLoading();
        
        // Make API call to reject the registration
        fetch(`/api/registrations/${registrationId}/reject`, {
            method: 'POST',
            headers: buildAuthHeaders(),
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            // Hide loading overlay
            hideLoading();
            
            if (data.success) {
                // Show success message
                showNotification('Registration rejected successfully', 'success');
                
                // Reload the page after a short delay
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showNotification(`Error: ${data.message}`, 'error');
            }
        })
        .catch(error => {
            // Hide loading overlay
            hideLoading();
            
            console.error('Error:', error);
            showNotification('An error occurred while rejecting the registration', 'error');
        });
    });
}
  
/**
* Show loading overlay
*/
function showLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
    }
}
  
/**
* Hide loading overlay
*/
function hideLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        // Add slight delay to make loading feel more natural
        setTimeout(() => {
            loadingOverlay.style.display = 'none';
        }, 300);
    }
}
  
/**
* Show notification message with enhanced styling
*/
function showNotification(message, type = 'info') {
    // Remove any existing notifications first
    document.querySelectorAll('.flash-message').forEach(el => {
        if (el.parentNode) el.parentNode.removeChild(el);
    });
    
    // Create a notification element
    const notification = document.createElement('div');
    notification.className = `flash-message ${type}`;
    
    // Add icon based on notification type
    let icon = '';
    if (type === 'success') {
        icon = '<span class="icon material-icons">check_circle</span>';
    } else if (type === 'error') {
        icon = '<span class="icon material-icons">error</span>';
    } else if (type === 'info') {
        icon = '<span class="icon material-icons">info</span>';
    }
    
    notification.innerHTML = `${icon}<span>${message}</span>`;
    
    // Add the notification to the page
    document.body.appendChild(notification);
    
    // Remove the notification after a delay
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translate(-50%, -10px)';
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 500);
    }, 5000);
    
    // Make the notification dismissable on click
    notification.addEventListener('click', function() {
        this.style.opacity = '0';
        this.style.transform = 'translate(-50%, -10px)';
        setTimeout(() => {
            if (document.body.contains(this)) {
                document.body.removeChild(this);
            }
        }, 300);
    });
}