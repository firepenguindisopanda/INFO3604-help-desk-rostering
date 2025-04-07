document.addEventListener('DOMContentLoaded', function() {
  const registrationForm = document.getElementById('registrationForm');
  const idInput = document.getElementById('id');
  const passwordInput = document.getElementById('password');
  const confirmPasswordInput = document.getElementById('confirm_password');
  const nameInput = document.getElementById('name');
  const emailInput = document.getElementById('email');
  const degreeSelect = document.getElementById('degree');
  const transcriptInput = document.getElementById('transcript');
  const fileNameDisplay = document.getElementById('file-name');
  const availabilityDataInput = document.getElementById('availabilityData');
  
  // Update file name display when a file is selected
  transcriptInput.addEventListener('change', function() {
      if (this.files && this.files[0]) {
          fileNameDisplay.textContent = this.files[0].name;
      } else {
          fileNameDisplay.textContent = 'No file chosen';
      }
  });
  
  // Form validation
  registrationForm.addEventListener('submit', function(e) {
      let isValid = true;
      
      // Validate ID
      if (!idInput.value) {
          document.getElementById('idError').style.display = 'block';
          idInput.style.borderColor = '#dc3545';
          isValid = false;
      } else if (!/^[0-9]+$/.test(idInput.value)) {
          document.getElementById('idError').style.display = 'block';
          document.getElementById('idError').textContent = 'ID must contain only numbers';
          idInput.style.borderColor = '#dc3545';
          isValid = false;
      } else if (!/^(816|816)\d{6}$/.test(idInput.value)) {
          document.getElementById('idError').style.display = 'block';
          document.getElementById('idError').textContent = 'ID must follow the standard uwi format eg. 81604279';
          idInput.style.borderColor = '#dc3545';
          isValid = false;
      } else {
          document.getElementById('idError').style.display = 'none';
          idInput.style.borderColor = '#ddd';
      }
      
      // Validate name
      if (!nameInput.value) {
          document.getElementById('nameError').style.display = 'block';
          nameInput.style.borderColor = '#dc3545';
          isValid = false;
      } else {
          document.getElementById('nameError').style.display = 'none';
          nameInput.style.borderColor = '#ddd';
      }
      
      // Validate email
      const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailInput.value || !emailPattern.test(emailInput.value)) {
          document.getElementById('emailError').style.display = 'block';
          emailInput.style.borderColor = '#dc3545';
          isValid = false;
      } else {
          document.getElementById('emailError').style.display = 'none';
          emailInput.style.borderColor = '#ddd';
      }
      
      // Validate password
      if (!passwordInput.value) {
          document.getElementById('passwordError').style.display = 'block';
          passwordInput.style.borderColor = '#dc3545';
          isValid = false;
      } else if (passwordInput.value.length < 8) {
          document.getElementById('passwordError').style.display = 'block';
          document.getElementById('passwordError').textContent = 'Password must be at least 8 characters';
          passwordInput.style.borderColor = '#dc3545';
          isValid = false;
      } else if (!/[A-Z]/.test(passwordInput.value)) {
          document.getElementById('passwordError').style.display = 'block';
          document.getElementById('passwordError').textContent = 'Password must contain at least one uppercase letter';
          passwordInput.style.borderColor = '#dc3545';
          isValid = false;
      } else if (!/[0-9]/.test(passwordInput.value)) {
          document.getElementById('passwordError').style.display = 'block';
          document.getElementById('passwordError').textContent = 'Password must contain at least one number';
          passwordInput.style.borderColor = '#dc3545';
          isValid = false;
      } else if (!/[^A-Za-z0-9]/.test(passwordInput.value)) {
          document.getElementById('passwordError').style.display = 'block';
          document.getElementById('passwordError').textContent = 'Password must contain at least one special character';
          passwordInput.style.borderColor = '#dc3545';
          isValid = false;
      } else {
          document.getElementById('passwordError').style.display = 'none';
          passwordInput.style.borderColor = '#ddd';
      }
      
      // Validate password confirmation
      if (passwordInput.value !== confirmPasswordInput.value) {
          document.getElementById('confirmPasswordError').style.display = 'block';
          confirmPasswordInput.style.borderColor = '#dc3545';
          isValid = false;
      } else {
          document.getElementById('confirmPasswordError').style.display = 'none';
          confirmPasswordInput.style.borderColor = '#ddd';
      }
      
      // Validate degree
      if (!degreeSelect.value) {
          document.getElementById('degreeError').style.display = 'block';
          degreeSelect.style.borderColor = '#dc3545';
          isValid = false;
      } else {
          document.getElementById('degreeError').style.display = 'none';
          degreeSelect.style.borderColor = '#ddd';
      }
      
      // Check if any courses are selected
      const courseCheckboxes = document.querySelectorAll('input[name="courses[]"]:checked');
      if (courseCheckboxes.length === 0) {
          document.getElementById('coursesError').style.display = 'block';
          document.querySelector('.course-selection').style.borderColor = '#dc3545';
          isValid = false;
      } else {
          document.getElementById('coursesError').style.display = 'none';
          document.querySelector('.course-selection').style.borderColor = '#ddd';
      }
      
      // Check if any availability slots are selected
      const availabilityData = JSON.parse(availabilityDataInput.value);
      if (availabilityData.length === 0) {
          document.getElementById('availabilityError').style.display = 'block';
          document.getElementById('availabilityGrid').style.borderColor = '#dc3545';
          isValid = false;
      } else {
          document.getElementById('availabilityError').style.display = 'none';
          document.getElementById('availabilityGrid').style.borderColor = '';
      }
      
      if (!isValid) {
          e.preventDefault();
          // Scroll to the first error
          const firstError = document.querySelector('.error-message[style="display: block"]');
          if (firstError) {
              firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
      }
  });
  
  // Clear errors on input
  const inputs = [nameInput, emailInput];
  inputs.forEach(input => {
      input.addEventListener('input', function() {
          this.style.borderColor = '#ddd';
          const errorElement = document.getElementById(`${this.id}Error`);
          if (errorElement) {
              errorElement.style.display = 'none';
          }
      });
  });
  
  // ID input validation - only allow valid student ID format
  idInput.addEventListener('input', function() {
      this.value = this.value.replace(/[^0-9]/g, ''); // Remove any non-numeric characters
      
      // Clear error message while typing
      if (this.value) {
          document.getElementById('idError').style.display = 'none';
          this.style.borderColor = '#ddd';
      }
      
      // Optional: If you want to validate as they type (only when they've entered enough digits)
      if (this.value.length >= 9) {
          if (!/^(816|816)\d{6}$/.test(this.value)) {
              document.getElementById('idError').style.display = 'block';
              document.getElementById('idError').textContent = 'ID must start with 81603 or 81604 followed by 4 digits';
              this.style.borderColor = '#dc3545';
          } else {
              document.getElementById('idError').style.display = 'none';
              this.style.borderColor = '#ddd';
          }
      }
  });
  
  // Password validation on input
  passwordInput.addEventListener('input', function() {
      this.style.borderColor = '#ddd';
      document.getElementById('passwordError').style.display = 'none';
      
      // Check password confirmation
      if (confirmPasswordInput.value && this.value !== confirmPasswordInput.value) {
          document.getElementById('confirmPasswordError').style.display = 'block';
          confirmPasswordInput.style.borderColor = '#dc3545';
      } else if (confirmPasswordInput.value) {
          document.getElementById('confirmPasswordError').style.display = 'none';
          confirmPasswordInput.style.borderColor = '#ddd';
      }
  });
  
  // Password confirmation validation on input
  confirmPasswordInput.addEventListener('input', function() {
      if (this.value !== passwordInput.value) {
          document.getElementById('confirmPasswordError').style.display = 'block';
          this.style.borderColor = '#dc3545';
      } else {
          document.getElementById('confirmPasswordError').style.display = 'none';
          this.style.borderColor = '#ddd';
      }
  });
  
  degreeSelect.addEventListener('change', function() {
      this.style.borderColor = '#ddd';
      document.getElementById('degreeError').style.display = 'none';
  });
  
  // Add event listeners to course checkboxes
  document.querySelectorAll('input[name="courses[]"]').forEach(checkbox => {
      checkbox.addEventListener('change', function() {
          if (document.querySelectorAll('input[name="courses[]"]:checked').length > 0) {
              document.getElementById('coursesError').style.display = 'none';
              document.querySelector('.course-selection').style.borderColor = '#ddd';
          }
      });
  });
});

// Function to toggle availability cell selection
function toggleAvailability(cell) {
  cell.classList.toggle('selected');
  updateAvailabilityData();
}

// Function to update availability data in hidden input
function updateAvailabilityData() {
  const selectedCells = document.querySelectorAll('.availability-cell.selected');
  const availabilityData = [];
  
  selectedCells.forEach(cell => {
      const day = parseInt(cell.getAttribute('data-day'));
      const hour = parseInt(cell.getAttribute('data-hour'));
      
      availabilityData.push({
          day: day,
          start_time: `${hour}:00:00`,
          end_time: `${hour+1}:00:00`
      });
  });
  
  // Update the hidden input
  document.getElementById('availabilityData').value = JSON.stringify(availabilityData);
  
  // Clear error if data is available
  if (availabilityData.length > 0) {
      document.getElementById('availabilityError').style.display = 'none';
      document.getElementById('availabilityGrid').style.borderColor = '';
  }
}