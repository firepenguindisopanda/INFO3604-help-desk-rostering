document.addEventListener('DOMContentLoaded', function() {
  // Initialize user cards and their expandable sections
  initializeUserCards();
  
  // Initialize search functionality
  initializeSearch();
});

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
  
  // In a real application, you would make an API call to approve the request
  console.log(`Approving request #${requestId}`);
  
  // Simulate successful API call
  setTimeout(() => {
      // Update the UI to reflect the approved status
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
          
          // Show success message
          showNotification('Request approved successfully', 'success');
      }
      
      // In a real app, you would do something like:
      /*
      fetch(`/api/requests/${requestId}/approve`, {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json',
          }
      })
      .then(response => response.json())
      .then(data => {
          if (data.success) {
              // Update UI as above
              showNotification('Request approved successfully', 'success');
          } else {
              showNotification(`Error: ${data.message}`, 'error');
          }
      })
      .catch(error => {
          console.error('Error:', error);
          showNotification('An error occurred while approving the request', 'error');
      });
      */
  }, 500);
}

function rejectRequest(requestId) {
  // Show confirmation dialog
  if (!confirm('Are you sure you want to reject this request?')) {
      return;
  }
  
  // In a real application, you would make an API call to reject the request
  console.log(`Rejecting request #${requestId}`);
  
  // Simulate successful API call
  setTimeout(() => {
      // Update the UI to reflect the rejected status
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
          
          // Show success message
          showNotification('Request rejected', 'success');
      }
      
      // In a real app, you would do something like:
      /*
      fetch(`/api/requests/${requestId}/reject`, {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json',
          }
      })
      .then(response => response.json())
      .then(data => {
          if (data.success) {
              // Update UI as above
              showNotification('Request rejected', 'success');
          } else {
              showNotification(`Error: ${data.message}`, 'error');
          }
      })
      .catch(error => {
          console.error('Error:', error);
          showNotification('An error occurred while rejecting the request', 'error');
      });
      */
  }, 500);
}

function findRequestElement(requestId) {
  // Find the request element by its ID
  // In a real application, we would need a more reliable way to identify request elements
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

function showNotification(message, type = 'info') {
  // Create a notification element
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  notification.textContent = message;
  
  // Add the notification to the page
  document.body.appendChild(notification);
  
  // Remove the notification after a delay
  setTimeout(() => {
      notification.classList.add('hiding');
      setTimeout(() => {
          notification.remove();
      }, 500);
  }, 3000);
}