document.addEventListener('DOMContentLoaded', function() {
  // Initialize notifications
  handleFlashMessages();
  
  const loginForm = document.getElementById('loginForm');
  const idInput = document.getElementById('id');
  const passwordInput = document.getElementById('password');
  const idError = document.getElementById('idError');
  const passwordError = document.getElementById('passwordError');
  
  // Form validation
  loginForm.addEventListener('submit', function(e) {
      let isValid = true;
      
      // Validate ID
      if (!idInput.value) {
          idInput.classList.add('invalid');
          idError.style.display = 'block';
          idError.textContent = 'ID is required';
          isValid = false;
      } else {
          idInput.classList.remove('invalid');
          idError.style.display = 'none';
      }
      
      // Validate password
      if (!passwordInput.value) {
          passwordInput.classList.add('invalid');
          passwordError.style.display = 'block';
          isValid = false;
      } else {
          passwordInput.classList.remove('invalid');
          passwordError.style.display = 'none';
      }
      
      if (!isValid) {
          e.preventDefault();
      }
  });
  
  // Clear errors on input
  idInput.addEventListener('input', function() {
      idInput.classList.remove('invalid');
      idError.style.display = 'none';
  });
  
  passwordInput.addEventListener('input', function() {
      passwordInput.classList.remove('invalid');
      passwordError.style.display = 'none';
  });
});