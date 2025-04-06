// Student Assistant Dashboard JavaScript
document.addEventListener('DOMContentLoaded', function() {
  // Initialize dashboard elements
  initializeDashboard();
  
  // Handle shift card hover animations
  initializeShiftCards();
});

/**
 * Initialize dashboard elements and handle responsive layout
 */
function initializeDashboard() {
  // Get the current time for any time-based display updates
  const now = new Date();
  
  // Update any relative time displays (e.g., "starts in X minutes")
  updateRelativeTimesDisplay();
  
  // Check if we need to update any in-progress animations
  checkActiveShiftStatus();
}

/**
 * Add hover effects to schedule rows
 */
function initializeShiftCards() {
  const scheduleRows = document.querySelectorAll('.schedule-row');
  
  scheduleRows.forEach(row => {
    row.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-2px)';
    });
    
    row.addEventListener('mouseleave', function() {
      this.style.transform = 'translateY(0)';
    });
  });
}

/**
 * Update any relative time displays in the UI
 * For example: "Starts in 5 hours" or "Starts in 10 minutes"
 */
function updateRelativeTimesDisplay() {
  const timeUntilElements = document.querySelectorAll('.time-until');
  
  // Auto-update these time displays every minute
  if (timeUntilElements.length > 0) {
    setInterval(function() {
      // This would need server data to actually update
      // For now this is just a placeholder for future functionality
      console.log('Time displays would update here');
    }, 60000); // Every minute
  }
}

/**
 * Check if there's an active shift and update animations accordingly
 */
function checkActiveShiftStatus() {
  const activeShiftCard = document.querySelector('.next-shift-card.active');
  
  if (activeShiftCard) {
    // Add any special animations or highlighting for active shifts
    console.log('Active shift detected');
  }
}