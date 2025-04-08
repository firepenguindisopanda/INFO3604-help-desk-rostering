// Password Reset Requests JavaScript
document.addEventListener('DOMContentLoaded', function() {
  // Initialize search functionality
  initializeSearch();
  
  // Add animation to reset cards
  animateResetCards();
  
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

/**
* Initialize search functionality for reset request cards
*/
function initializeSearch() {
  const searchInput = document.getElementById('resetSearchInput');
  if (!searchInput) return;
  
  // Add transition styles to reset cards for smoother filtering
  const resetCards = document.querySelectorAll('.reset-card');
  resetCards.forEach(card => {
      card.style.transition = 'all 0.3s ease, opacity 0.3s ease, transform 0.3s ease';
  });
  
  searchInput.addEventListener('input', function() {
      const searchTerm = this.value.toLowerCase();
      let foundResults = {
          pendingResets: 0,
          completedResets: 0
      };
      
      // Search in all reset cards
      resetCards.forEach(card => {
          const name = card.getAttribute('data-name').toLowerCase();
          const id = card.getAttribute('data-id').toLowerCase();
          const parent = card.parentNode.id;
          
          if (name.includes(searchTerm) || id.includes(searchTerm)) {
              card.style.display = 'block';
              card.style.opacity = '1';
              card.style.transform = 'translateY(0)';
              
              // Increment counter for this section
              if (parent === 'pendingResets') {
                  foundResults.pendingResets++;
              } else if (parent === 'completedResets') {
                  foundResults.completedResets++;
              }
              
              // Optional: Highlight the matching text
              if (searchTerm.length > 1) {
                  highlightMatch(card.querySelector('.reset-name'), name, searchTerm);
                  highlightMatch(card.querySelector('.reset-id'), id, searchTerm);
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
      checkEmptySections(foundResults, searchTerm);
  });
}

/**
* Highlight matching text in search results
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
function checkEmptySections(foundResults, searchTerm) {
  // Messages for each section
  const sections = [
      { 
          containerId: 'pendingResets', 
          message: 'No pending password reset requests matching your search.',
          count: foundResults.pendingResets
      },
      { 
          containerId: 'completedResets', 
          message: 'No completed password reset requests matching your search.',
          count: foundResults.completedResets
      }
  ];
  
  sections.forEach(section => {
      const container = document.getElementById(section.containerId);
      if (!container) return;
      
      // Remove existing "no results" message
      const existingNoResults = container.querySelector('.no-resets.search-results');
      if (existingNoResults) {
          existingNoResults.remove();
      }
      
      // Only add "no results" message if there are cards but none are visible due to search
      const totalCards = container.querySelectorAll('.reset-card').length;
      
      if (searchTerm && totalCards > 0 && section.count === 0) {
          const noResults = document.createElement('div');
          noResults.className = 'no-resets search-results';
          noResults.innerHTML = `<p>${section.message}</p>`;
          container.appendChild(noResults);
          
          // Add fade-in animation
          noResults.style.animation = 'fadeIn 0.3s ease';
      }
  });
}

/**
* Add entrance animations to reset cards
*/
function animateResetCards() {
  const resetCards = document.querySelectorAll('.reset-card');
  
  resetCards.forEach((card, index) => {
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
* Open the complete reset modal
*/
function openCompleteModal(resetId, username) {
  const modal = document.getElementById('completeModal');
  const resetIdInput = document.getElementById('resetId');
  const usernameInput = document.getElementById('username');
  
  resetIdInput.value = resetId;
  usernameInput.value = username;
  
  modal.style.display = 'block';
}

/**
* Open the reject reset modal
*/
function openRejectModal(resetId) {
  const modal = document.getElementById('rejectModal');
  const resetIdInput = document.getElementById('rejectResetId');
  
  resetIdInput.value = resetId;
  
  modal.style.display = 'block';
}

/**
* Close all modals
*/
function closeModals() {
  document.getElementById('completeModal').style.display = 'none';
  document.getElementById('rejectModal').style.display = 'none';
  
  // Clear form inputs
  document.getElementById('newPassword').value = '';
  document.getElementById('confirmPassword').value = '';
  document.getElementById('rejectionReason').value = '';
}

/**
* Complete a password reset
*/
function completePasswordReset() {
  const resetId = document.getElementById('resetId').value;
  const newPassword = document.getElementById('newPassword').value;
  const confirmPassword = document.getElementById('confirmPassword').value;
  
  // Validate inputs
  if (newPassword === '') {
      showNotification('Please enter a new password', 'error');
      return;
  }
  
  if (newPassword !== confirmPassword) {
      showNotification('Passwords do not match', 'error');
      return;
  }
  
  // Show confirmation dialog
  if (!confirm('Are you sure you want to reset this password?')) {
      return;
  }
  
  // Show loading overlay
  showLoading();
  
  // Make API call to complete the password reset
  fetch(`/api/password-resets/${resetId}/complete`, {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json',
      },
      body: JSON.stringify({
          new_password: newPassword
      })
  })
  .then(response => response.json())
  .then(data => {
      // Hide loading overlay
      hideLoading();
      
      if (data.success) {
          // Show success message
          showNotification('Password has been reset successfully', 'success');
          
          // Close the modal
          closeModals();
          
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
      showNotification('An error occurred while processing the request', 'error');
  });
}

/**
* Reject a password reset
*/
function rejectPasswordReset() {
  const resetId = document.getElementById('rejectResetId').value;
  const rejectionReason = document.getElementById('rejectionReason').value;
  
  // Show confirmation dialog
  if (!confirm('Are you sure you want to reject this password reset request?')) {
      return;
  }
  
  // Show loading overlay
  showLoading();
  
  // Make API call to reject the password reset
  fetch(`/api/password-resets/${resetId}/reject`, {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json',
      },
      body: JSON.stringify({
          reason: rejectionReason
      })
  })
  .then(response => response.json())
  .then(data => {
      // Hide loading overlay
      hideLoading();
      
      if (data.success) {
          // Show success message
          showNotification('Password reset request has been rejected', 'success');
          
          // Close the modal
          closeModals();
          
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
      showNotification('An error occurred while processing the request', 'error');
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
* Show notification message
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