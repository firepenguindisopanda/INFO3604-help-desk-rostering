// Volunteer Requests Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
  // Initialize form validation
  initializeFormValidation();
  
  // Set up cancel request button handlers
  setupCancelButtons();
  
  // Handle flash messages
  setupFlashMessages();
  
  // Add fancy select styling
  enhanceSelectDropdowns();
});

/**
 * Initialize form validation for the new request form
 */
function initializeFormValidation() {
  const requestForm = document.getElementById('requestForm');
  
  if (requestForm) {
    requestForm.addEventListener('submit', function(e) {
      let isValid = true;
      
      // Validate shift selection
      const shiftSelect = document.getElementById('shiftToChange');
      const shiftError = document.getElementById('shiftError');
      
      if (shiftSelect && shiftSelect.value === '') {
        if (shiftError) shiftError.style.display = 'block';
        shiftSelect.classList.add('invalid');
        isValid = false;
      } else if (shiftSelect) {
        if (shiftError) shiftError.style.display = 'none';
        shiftSelect.classList.remove('invalid');
      }
      
      // Validate reason
      const reasonInput = document.getElementById('reasonForChange');
      const reasonError = document.getElementById('reasonError');
      
      if (reasonInput && reasonInput.value.trim() === '') {
        if (reasonError) reasonError.style.display = 'block';
        reasonInput.classList.add('invalid');
        isValid = false;
      } else if (reasonInput) {
        if (reasonError) reasonError.style.display = 'none';
        reasonInput.classList.remove('invalid');
      }
      
      if (!isValid) {
        e.preventDefault();
        
        // Scroll to the first error
        const firstInvalid = document.querySelector('.invalid');
        if (firstInvalid) {
          firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
          firstInvalid.focus();
        }
      }
    });
    
    // Clear errors on input
    const formElements = requestForm.querySelectorAll('select, textarea');
    formElements.forEach(element => {
      element.addEventListener('input', function() {
        this.classList.remove('invalid');
        const errorElement = document.getElementById(this.id + 'Error');
        if (errorElement) errorElement.style.display = 'none';
      });
      
      element.addEventListener('change', function() {
        this.classList.remove('invalid');
        const errorElement = document.getElementById(this.id + 'Error');
        if (errorElement) errorElement.style.display = 'none';
      });
    });
  }
}

/**
 * Set up cancel buttons for pending requests
 */
function setupCancelButtons() {
  const cancelButtons = document.querySelectorAll('.cancel-btn');
  
  cancelButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      // Get confirmation before submitting
      if (!confirm('Are you sure you want to cancel this request?')) {
        e.preventDefault();
      }
    });
  });
}

/**
 * Handle flash messages display and removal
 */
function setupFlashMessages() {
  const flashMessages = document.querySelectorAll('.flash-message');
  
  flashMessages.forEach(message => {
    // Auto-remove after 5 seconds
    setTimeout(() => {
      message.style.opacity = '0';
      setTimeout(() => {
        if (message.parentNode) {
          message.parentNode.removeChild(message);
        }
      }, 500);
    }, 5000);
  });
}

/**
 * Enhance select dropdowns with custom styling
 */
function enhanceSelectDropdowns() {
  const selects = document.querySelectorAll('.custom-select select');
  
  selects.forEach(select => {
    // Add focus styles 
    select.addEventListener('focus', function() {
      this.parentNode.classList.add('focused');
    });
    
    select.addEventListener('blur', function() {
      this.parentNode.classList.remove('focused');
    });
    
    // Add hover effects
    select.addEventListener('mouseenter', function() {
      if (!this.parentNode.classList.contains('focused')) {
        this.parentNode.classList.add('hover');
      }
    });
    
    select.addEventListener('mouseleave', function() {
      this.parentNode.classList.remove('hover');
    });
  });
}

/**
 * Display a success message
 */
function showSuccessMessage(message) {
  createFlashMessage(message, 'success');
}

/**
 * Display an error message
 */
function showErrorMessage(message) {
  createFlashMessage(message, 'error');
}

/**
 * Create and display a flash message
 */
function createFlashMessage(message, type) {
  // Remove any existing messages
  const existingMessages = document.querySelectorAll('.flash-message');
  existingMessages.forEach(msg => {
    if (msg.parentNode) msg.parentNode.removeChild(msg);
  });
  
  // Create new message
  const flashMessage = document.createElement('div');
  flashMessage.className = `flash-message ${type}`;
  flashMessage.textContent = message;
  
  // Add to page
  document.body.appendChild(flashMessage);
  
  // Remove after 5 seconds
  setTimeout(() => {
    flashMessage.style.opacity = '0';
    setTimeout(() => {
      if (flashMessage.parentNode) {
        flashMessage.parentNode.removeChild(flashMessage);
      }
    }, 500);
  }, 5000);
}