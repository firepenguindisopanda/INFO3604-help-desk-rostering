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

  // Make request-status banners dismissible
  document.querySelectorAll('.request-dismiss').forEach(btn => {
      btn.addEventListener('click', function(e) {
          const banner = e.target.closest('.request-status');
          if (banner) {
              banner.style.opacity = '0';
              banner.style.transform = 'translateY(-8px)';
              setTimeout(() => banner.remove(), 250);
          }
      });
  });

  // Auto-hide non-critical request banners after 12 seconds
  document.querySelectorAll('.request-status.request_accepted').forEach(b => {
      setTimeout(() => {
          b.style.opacity = '0';
          b.style.transform = 'translateY(-8px)';
          setTimeout(() => b.remove(), 300);
      }, 12000);
  });
});