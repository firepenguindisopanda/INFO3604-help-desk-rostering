// Enhanced Admin Profile JavaScript
document.addEventListener('DOMContentLoaded', function() {
  // Student profile edit
  const manageBtns = document.querySelectorAll('.manage-btn');
  const studentEditModal = document.getElementById('studentEditModal');
  const studentCancelBtn = document.getElementById('studentCancelBtn');
  const studentEditForm = document.getElementById('studentEditForm');
  const studentSpinner = document.getElementById('studentSpinner');
  
  // Search functionality
  const staffSearch = document.getElementById('staffSearch');
  const staffGrid = document.getElementById('staffGrid');
  
  // Close buttons
  const closeButtons = document.querySelectorAll('.close-btn');

  // Apply card entrance animations
  animateCards();
  
  // Staff card manage buttons
  if (manageBtns) {
    manageBtns.forEach(btn => {
      btn.addEventListener('click', function() {
        const username = this.getAttribute('data-username');
        
        // Apply button press animation
        this.style.transform = 'scale(0.95)';
        setTimeout(() => {
          this.style.transform = 'scale(1)';
        }, 150);
        
        // Add a small delay before redirect for the animation to be visible
        setTimeout(() => {
          window.location.href = `/admin/staff/${username}/profile`;
        }, 200);
      });
    });
  }
  
  // Close modals with cancel buttons
  if (studentCancelBtn) {
    studentCancelBtn.addEventListener('click', function() {
      fadeOutModal(studentEditModal);
    });
  }
  
  // Close modals with X buttons
  if (closeButtons) {
    closeButtons.forEach(btn => {
      btn.addEventListener('click', function() {
        // Find the parent modal
        const modal = this.closest('.edit-modal');
        if (modal) {
          fadeOutModal(modal);
        }
      });
    });
  }
  
  // Close modals when clicking outside
  window.addEventListener('click', function(event) {
    if (event.target === studentEditModal) {
      fadeOutModal(studentEditModal);
    }
  });
  
  // Student form submit with improved feedback
  if (studentEditForm) {
    studentEditForm.addEventListener('submit', function(e) {
      e.preventDefault();
      console.log('Submitting student profile form');
      
      // Disable the submit button to prevent multiple submissions
      const submitBtn = this.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      
      // Show spinner
      studentSpinner.style.display = 'inline-block';
      
      const username = document.getElementById('studentUsername').value;
      
      // Create the payload with proper type conversion
      const formData = {
        username: username,
        name: document.getElementById('studentName').value,
        degree: document.getElementById('studentDegree').value,
        rate: parseFloat(document.getElementById('studentRate').value || 0),
        hours_minimum: parseInt(document.getElementById('studentMinHours').value || 0),
        active: document.querySelector('input[name="active"]:checked').value === 'true'
      };
      
      // Log the data being sent
      console.log("Sending student update data:", formData);
      
      fetch('/api/student/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })
      .then(response => {
        if (!response.ok) {
          throw new Error(`Server responded with status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        // Hide spinner
        studentSpinner.style.display = 'none';
        
        if (data.success) {
          // Show success message with custom notification
          showNotification('Student profile updated successfully!', 'success');
          
          // Fade out the modal
          fadeOutModal(studentEditModal);
          
          // Reload page after a short delay
          setTimeout(() => {
            window.location.reload();
          }, 1000);
        } else {
          showNotification('Error: ' + data.message, 'error');
          // Re-enable the submit button
          submitBtn.disabled = false;
        }
      })
      .catch(error => {
        studentSpinner.style.display = 'none';
        console.error('Error:', error);
        showNotification('An error occurred while updating the student profile: ' + error.message, 'error');
        // Re-enable the submit button
        submitBtn.disabled = false;
      });
    });
  }
  
  // Load student data with improved loading state
  function loadStudentData(username) {
    studentSpinner.style.display = 'inline-block';
    
    // Show loading state on the modal
    const modalContent = studentEditModal.querySelector('.edit-modal-content');
    if (modalContent) {
      modalContent.style.opacity = '0.7';
      modalContent.style.pointerEvents = 'none';
    }
    
    fetch(`/api/staff/${username}/profile`)
    .then(response => response.json())
    .then(data => {
      studentSpinner.style.display = 'none';
      
      // Restore modal content
      if (modalContent) {
        modalContent.style.opacity = '1';
        modalContent.style.pointerEvents = 'auto';
      }
      
      if (data.success) {
        const profile = data.profile;
        
        // Fill the form with student data
        document.getElementById('studentUsername').value = profile.username;
        document.getElementById('studentName').value = profile.name;
        document.getElementById('studentDegree').value = profile.degree;
        document.getElementById('studentRate').value = profile.rate;
        document.getElementById('studentMinHours').value = profile.hours_minimum;
        
        // Set active status radio buttons
        if (profile.active) {
          document.getElementById('activeStatus').checked = true;
        } else {
          document.getElementById('inactiveStatus').checked = true;
        }
        
        // Display the modal with animation
        studentEditModal.style.display = 'block';
        studentEditModal.classList.add('visible');
      } else {
        showNotification('Error loading student data: ' + data.message, 'error');
      }
    })
    .catch(error => {
      studentSpinner.style.display = 'none';
      
      // Restore modal content
      if (modalContent) {
        modalContent.style.opacity = '1';
        modalContent.style.pointerEvents = 'auto';
      }
      
      console.error('Error:', error);
      showNotification('An error occurred while loading student data: ' + error.message, 'error');
    });
  }
  
  // Enhanced staff search with smooth filtering
  if (staffSearch) {
    staffSearch.addEventListener('input', function() {
      const searchTerm = this.value.toLowerCase();
      const staffItems = staffGrid.querySelectorAll('.staff-item');
      let foundResults = false;
      
      staffItems.forEach(item => {
        const name = item.querySelector('.staff-name').textContent.toLowerCase();
        const id = item.querySelector('.staff-id').textContent.toLowerCase();
        
        if (name.includes(searchTerm) || id.includes(searchTerm)) {
          // Show with animation if previously hidden
          if (item.style.display === 'none') {
            item.style.opacity = '0';
            item.style.transform = 'translateY(10px)';
            item.style.display = 'flex';
            
            setTimeout(() => {
              item.style.opacity = '1';
              item.style.transform = 'translateY(0)';
            }, 10);
          }
          
          // Optional: Highlight matching text if search term is not empty
          if (searchTerm) {
            highlightMatch(item.querySelector('.staff-name'), name, searchTerm);
            highlightMatch(item.querySelector('.staff-id'), id, searchTerm);
          }
          
          foundResults = true;
        } else {
          // Hide with animation
          item.style.opacity = '0';
          item.style.transform = 'translateY(10px)';
          
          setTimeout(() => {
            item.style.display = 'none';
          }, 300);
        }
      });
      
      // Show/hide no results message
      const noResultsMsg = document.getElementById('noResultsMessage');
      if (noResultsMsg) {
        if (!foundResults && searchTerm) {
          noResultsMsg.style.display = 'block';
          noResultsMsg.textContent = `No staff found matching "${searchTerm}"`;
        } else {
          noResultsMsg.style.display = 'none';
        }
      }
    });
  }
  
  // Animation for cards on page load
  function animateCards() {
    // Animate profile card
    const profileInfo = document.querySelector('.profile-info');
    if (profileInfo) {
      profileInfo.style.opacity = '0';
      profileInfo.style.transform = 'translateY(20px)';
      
      setTimeout(() => {
        profileInfo.style.transition = 'all 0.5s ease';
        profileInfo.style.opacity = '1';
        profileInfo.style.transform = 'translateY(0)';
      }, 100);
    }
    
    // Animate staff cards with staggered delay
    const staffItems = document.querySelectorAll('.staff-item');
    staffItems.forEach((item, index) => {
      item.style.opacity = '0';
      item.style.transform = 'translateY(20px)';
      
      setTimeout(() => {
        item.style.transition = 'all 0.5s ease';
        item.style.opacity = '1';
        item.style.transform = 'translateY(0)';
      }, 100 + (index * 50)); // Staggered delay
    });
  }
  
  // Helper function to fade out modals
  function fadeOutModal(modal) {
    if (!modal) return;
    
    // Remove visible class to trigger CSS transition
    modal.classList.remove('visible');
    
    // Hide the modal after transition completes
    setTimeout(() => {
      modal.style.display = 'none';
    }, 300);
  }
  
  // Helper function to highlight matching text
  function highlightMatch(element, text, searchTerm) {
    if (!element || !searchTerm) return;
    
    // Reset the element text first
    element.innerHTML = text;
    
    // Find the match location (case insensitive)
    const matchIndex = text.toLowerCase().indexOf(searchTerm.toLowerCase());
    if (matchIndex >= 0) {
      const prefix = text.substring(0, matchIndex);
      const match = text.substring(matchIndex, matchIndex + searchTerm.length);
      const suffix = text.substring(matchIndex + searchTerm.length);
      
      // Create highlighted text
      element.innerHTML = prefix + 
        `<span style="background-color: rgba(0, 102, 204, 0.15); padding: 0 2px; border-radius: 2px; font-weight: 600;">${match}</span>` + 
        suffix;
    }
  }
  
  // Custom notification function
  function showNotification(message, type = 'info') {
    // Remove any existing notifications
    const existingNotifications = document.querySelectorAll('.notification-message');
    existingNotifications.forEach(notification => {
      notification.remove();
    });
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification-message ${type}`;
    
    // Add icon based on type
    let icon = '';
    if (type === 'success') {
      icon = '<span style="margin-right: 8px;">✓</span>';
    } else if (type === 'error') {
      icon = '<span style="margin-right: 8px;">⚠️</span>';
    }
    
    notification.innerHTML = icon + message;
    
    // Add notification to the DOM
    document.body.appendChild(notification);
    
    // Style the notification
    Object.assign(notification.style, {
      position: 'fixed',
      top: '1.5rem',
      right: '1.5rem',
      padding: '1rem 1.5rem',
      borderRadius: '8px',
      color: 'white',
      zIndex: '9999',
      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      display: 'flex',
      alignItems: 'center',
      opacity: '0',
      transform: 'translateY(-10px)',
      transition: 'all 0.3s ease'
    });
    
    // Set type-specific styles
    if (type === 'success') {
      notification.style.backgroundColor = '#10b981';
    } else if (type === 'error') {
      notification.style.backgroundColor = '#ef4444';
    } else {
      notification.style.backgroundColor = '#3b82f6';
    }
    
    // Animate in
    setTimeout(() => {
      notification.style.opacity = '1';
      notification.style.transform = 'translateY(0)';
    }, 10);
    
    // Remove after a delay
    setTimeout(() => {
      notification.style.opacity = '0';
      notification.style.transform = 'translateY(-10px)';
      
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
      }, 300);
    }, 5000);
  }
});