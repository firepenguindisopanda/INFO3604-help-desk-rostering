// Time Tracking JavaScript

document.addEventListener('DOMContentLoaded', function() {
  // Initialize chart animations
  initializeCharts();
  
  // Set up clock in/out buttons
  setupClockButtons();
  
  // Add hover effects to cards
  addCardHoverEffects();
});

/**
 * Initialize chart animations with delayed appearance
 */
function initializeCharts() {
  const barElements = document.querySelectorAll('.bar-value');
  
  // Only initialize if we have bars to animate (i.e., data exists)
  if (barElements.length > 0) {
    // Animate each bar with a slight delay for each
    barElements.forEach((bar, index) => {
      // Initially set height to 0
      const finalHeight = bar.style.height;
      bar.style.height = '0%';
      
      // Animate to final height with a staggered delay
      setTimeout(() => {
        bar.style.height = finalHeight;
      }, 100 * index);
    });
  } else {
    console.log('No chart data available to animate');
  }
}

/**
 * Set up clock in/out button functionality
 */
function setupClockButtons() {
  const clockInBtn = document.getElementById('clockInBtn');
  const clockOutBtn = document.getElementById('clockOutBtn');
  
  if (clockInBtn) {
    clockInBtn.addEventListener('click', function() {
      // Disable the button to prevent multiple clicks
      this.disabled = true;
      this.textContent = 'Processing...';
      
      // Make the API call to clock in
      fetch('/volunteer/time_tracking/clock_in', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          showSuccessMessage('Clocked in successfully!');
          // Reload the page to update status
          setTimeout(() => {
            window.location.reload();
          }, 1000);
        } else {
          showErrorMessage('Error clocking in: ' + data.message);
          // Re-enable the button if there was an error
          this.disabled = false;
          this.textContent = 'Clock In';
        }
      })
      .catch(error => {
        console.error('Error:', error);
        showErrorMessage('An error occurred while clocking in. Please try again.');
        this.disabled = false;
        this.textContent = 'Clock In';
      });
    });
  }
  
  if (clockOutBtn) {
    clockOutBtn.addEventListener('click', function() {
      // Confirm before clocking out
      if (!confirm('Are you sure you want to clock out?')) {
        return;
      }
      
      // Disable the button to prevent multiple clicks
      this.disabled = true;
      this.textContent = 'Processing...';
      
      // Make the API call to clock out
      fetch('/volunteer/time_tracking/clock_out', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          showSuccessMessage('Clocked out successfully! Hours worked: ' + data.hours_worked);
          // Reload the page to update status
          setTimeout(() => {
            window.location.reload();
          }, 1500);
        } else {
          showErrorMessage('Error clocking out: ' + data.message);
          // Re-enable the button if there was an error
          this.disabled = false;
          this.textContent = 'Clock Out';
        }
      })
      .catch(error => {
        console.error('Error:', error);
        showErrorMessage('An error occurred while clocking out. Please try again.');
        this.disabled = false;
        this.textContent = 'Clock Out';
      });
    });
  }
}

/**
 * Add hover effects to the hours cards
 */
function addCardHoverEffects() {
  const hoursCards = document.querySelectorAll('.hours-card');
  
  hoursCards.forEach(card => {
    card.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-5px)';
      this.style.boxShadow = '0 8px 16px rgba(0, 102, 204, 0.3)';
    });
    
    card.addEventListener('mouseleave', function() {
      this.style.transform = 'translateY(0)';
      this.style.boxShadow = '0 4px 6px rgba(0, 102, 204, 0.2)';
    });
  });
}

/**
 * Display a success message to the user
 */
function showSuccessMessage(message) {
  // Remove any existing messages
  removeExistingMessages();
  
  // Create success message element
  const messageElement = document.createElement('div');
  messageElement.className = 'notification-message success';
  messageElement.textContent = message;
  
  // Add to the page
  document.body.appendChild(messageElement);
  
  // Remove after a delay
  setTimeout(() => {
    messageElement.classList.add('fade-out');
    setTimeout(() => {
      if (document.body.contains(messageElement)) {
        document.body.removeChild(messageElement);
      }
    }, 500);
  }, 3000);
}

/**
 * Display an error message to the user
 */
function showErrorMessage(message) {
  // Remove any existing messages
  removeExistingMessages();
  
  // Create error message element
  const messageElement = document.createElement('div');
  messageElement.className = 'notification-message error';
  messageElement.textContent = message;
  
  // Add to the page
  document.body.appendChild(messageElement);
  
  // Remove after a delay
  setTimeout(() => {
    messageElement.classList.add('fade-out');
    setTimeout(() => {
      if (document.body.contains(messageElement)) {
        document.body.removeChild(messageElement);
      }
    }, 500);
  }, 4000);
}

/**
 * Remove any existing notification messages
 */
function removeExistingMessages() {
  const existingMessages = document.querySelectorAll('.notification-message');
  existingMessages.forEach(message => {
    document.body.removeChild(message);
  });
}