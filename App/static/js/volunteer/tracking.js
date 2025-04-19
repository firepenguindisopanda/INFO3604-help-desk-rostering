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
  
  // Only initialize if we have bars to animate
  if (barElements.length > 0) {
    console.log('Initializing chart with ' + barElements.length + ' bars');
    
    // Reset all bars to 0 height
    barElements.forEach(bar => {
      // Save the original percentage as a data attribute if it's not already there
      const originalHeight = bar.style.height;
      if (originalHeight && !bar.hasAttribute('data-original-height')) {
        bar.setAttribute('data-original-height', originalHeight);
      }
      
      // Reset to 0
      bar.style.height = '0px';
    });
    
    // Force browser to acknowledge the change
    setTimeout(() => {
      // Now animate each bar with a slight delay
      barElements.forEach((bar, index) => {
        setTimeout(() => {
          // Get the original height from the data attribute
          let finalHeight = bar.getAttribute('data-original-height') || 
                            bar.getAttribute('data-percentage') || 
                            '0%';
          
          // Make sure data-hours values greater than 0 have visible height
          const dataHours = parseFloat(bar.getAttribute('data-hours') || '0');
          if (dataHours > 0 && (finalHeight === '0%' || finalHeight === '0px')) {
            finalHeight = '5%'; // Minimum visible height
          }
          
          console.log(`Setting bar ${index} height to ${finalHeight}`);
          bar.style.height = finalHeight;
        }, 100 * index);
      });
    }, 50);
  } else {
    console.log('No chart bars found to animate');
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