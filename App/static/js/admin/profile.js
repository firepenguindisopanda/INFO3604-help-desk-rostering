document.addEventListener('DOMContentLoaded', function() {
  // Admin profile edit
  const editAdminProfileBtn = document.getElementById('editAdminProfileBtn');
  const adminEditModal = document.getElementById('adminEditModal');
  const adminCancelBtn = document.getElementById('adminCancelBtn');
  const adminEditForm = document.getElementById('adminEditForm');
  const adminSpinner = document.getElementById('adminSpinner');
  
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
  
  // Open admin edit modal
  if (editAdminProfileBtn) {
      editAdminProfileBtn.addEventListener('click', function() {
          adminEditModal.style.display = 'block';
      });
  }
  
  // Open student edit modal
  if (manageBtns) {
      manageBtns.forEach(btn => {
          btn.addEventListener('click', function() {
              const username = this.getAttribute('data-username');
              // Redirect to the staff profile page instead of loading the edit modal
              window.location.href = `/admin/staff/${username}/profile`;
          });
      });
  }
  
  // Close modals with cancel buttons
  if (adminCancelBtn) {
      adminCancelBtn.addEventListener('click', function() {
          adminEditModal.style.display = 'none';
      });
  }
  
  if (studentCancelBtn) {
      studentCancelBtn.addEventListener('click', function() {
          studentEditModal.style.display = 'none';
      });
  }
  
  // Close modals with X buttons
  if (closeButtons) {
      closeButtons.forEach(btn => {
          btn.addEventListener('click', function() {
              adminEditModal.style.display = 'none';
              studentEditModal.style.display = 'none';
          });
      });
  }
  
  // Close modals when clicking outside
  window.addEventListener('click', function(event) {
      if (event.target === adminEditModal) {
          adminEditModal.style.display = 'none';
      }
      if (event.target === studentEditModal) {
          studentEditModal.style.display = 'none';
      }
  });
  
  // Admin form submit
  if (adminEditForm) {
      adminEditForm.addEventListener('submit', function(e) {
          e.preventDefault();
          
          adminSpinner.style.display = 'inline-block';
          
          const formData = {
              name: document.getElementById('adminName').value,
              email: document.getElementById('adminEmail').value
          };
          
          console.log("Sending admin update data:", formData);
          
          fetch('/api/admin/profile', {
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
              adminSpinner.style.display = 'none';
              
              if (data.success) {
                  alert('Profile updated successfully!');
                  adminEditModal.style.display = 'none';
                  // Reload page to show updated info
                  window.location.reload();
              } else {
                  alert('Error: ' + data.message);
              }
          })
          .catch(error => {
              adminSpinner.style.display = 'none';
              console.error('Error:', error);
              alert('An error occurred while updating the profile: ' + error.message);
          });
      });
  }
  
  // Student form submit
  if (studentEditForm) {
      studentEditForm.addEventListener('submit', function(e) {
          e.preventDefault();
          console.log('Submitting student profile form');
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
              studentSpinner.style.display = 'none';
              
              if (data.success) {
                  alert('Student profile updated successfully!');
                  studentEditModal.style.display = 'none';
                  // Reload page to show updated info
                  window.location.reload();
              } else {
                  alert('Error: ' + data.message);
              }
          })
          .catch(error => {
              studentSpinner.style.display = 'none';
              console.error('Error:', error);
              alert('An error occurred while updating the student profile: ' + error.message);
          });
      });
  }
  
  // Load student data
  function loadStudentData(username) {
      studentSpinner.style.display = 'inline-block';
      
      fetch(`/api/staff/${username}/profile`)
      .then(response => response.json())
      .then(data => {
          studentSpinner.style.display = 'none';
          
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
              
              // Display the modal
              studentEditModal.style.display = 'block';
          } else {
              alert('Error loading student data: ' + data.message);
          }
      })
      .catch(error => {
          studentSpinner.style.display = 'none';
          console.error('Error:', error);
          alert('An error occurred while loading student data: ' + error.message);
      });
  }
  
  // Staff search
  if (staffSearch) {
      staffSearch.addEventListener('input', function() {
          const searchTerm = this.value.toLowerCase();
          const staffItems = staffGrid.querySelectorAll('.staff-item');
          
          staffItems.forEach(item => {
              const name = item.querySelector('.staff-name').textContent.toLowerCase();
              const id = item.querySelector('.staff-id').textContent.toLowerCase();
              
              if (name.includes(searchTerm) || id.includes(searchTerm)) {
                  item.style.display = 'flex';
              } else {
                  item.style.display = 'none';
              }
          });
      });
  }
});