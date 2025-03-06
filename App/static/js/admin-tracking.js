document.addEventListener('DOMContentLoaded', function() {
  // Store current filter values
  let currentWeek = document.querySelector('.filter-group:nth-child(2) .dropdown-btn').textContent.trim().split(' ')[0];
  let currentMonth = document.querySelector('.filter-group:nth-child(1) .dropdown-btn').textContent.trim().split(' ')[0];
  
  // Initialize dropdowns
  initializeDropdowns();
  
  // Handle staff card selection
  initializeStaffCards();
  
  // Handle pagination
  initializePagination();
  
  // Set up button handlers
  initializeButtons();
});

function initializeDropdowns() {
  const dropdownBtns = document.querySelectorAll('.dropdown-btn');
  
  dropdownBtns.forEach(btn => {
      // Create dropdown menu
      const dropdown = document.createElement('div');
      dropdown.className = 'dropdown-menu';
      dropdown.style.display = 'none';
      btn.parentNode.appendChild(dropdown);
      
      // Fill with options
      if (btn.textContent.includes('Week')) {
          for (let i = 1; i <= 10; i++) {
              addDropdownOption(dropdown, i.toString(), btn);
          }
      } else if (btn.textContent.includes('Nov')) {
          const months = ['Sept', 'Oct', 'Nov', 'Dec'];
          months.forEach(month => {
              addDropdownOption(dropdown, month, btn);
          });
      }
      
      // Toggle dropdown on button click
      btn.addEventListener('click', function() {
          const isVisible = dropdown.style.display === 'block';
          dropdown.style.display = isVisible ? 'none' : 'block';
      });
      
      // Close dropdown when clicking outside
      document.addEventListener('click', function(event) {
          if (!btn.contains(event.target) && !dropdown.contains(event.target)) {
              dropdown.style.display = 'none';
          }
      });
  });
}

function addDropdownOption(dropdown, value, button) {
  const option = document.createElement('div');
  option.className = 'dropdown-option';
  option.textContent = value;
  option.addEventListener('click', function() {
      button.textContent = value + ' ▼';
      dropdown.style.display = 'none';
      
      // Update current filters
      if (button.textContent.includes('Week')) {
          currentWeek = value;
      } else {
          currentMonth = value;
      }
      
      // Refresh data with new filters
      const selectedCard = document.querySelector('.staff-card.selected');
      if (selectedCard) {
          const staffId = selectedCard.getAttribute('data-staff-id');
          fetchStaffAttendance(staffId);
      }
  });
  dropdown.appendChild(option);
}

function initializeStaffCards() {
  const staffCards = document.querySelectorAll('.staff-card');
  
  staffCards.forEach(card => {
      card.addEventListener('click', function() {
          // Remove selected class from all cards
          staffCards.forEach(c => c.classList.remove('selected'));
          
          // Add selected class to clicked card
          this.classList.add('selected');
          
          // Get staff ID and name
          const staffId = this.getAttribute('data-staff-id');
          const staffName = this.querySelector('h3').textContent;
          
          // Show staff ID under name when selected
          let smallEl = this.querySelector('small');
          if (!smallEl) {
              smallEl = document.createElement('small');
              this.querySelector('.staff-header').appendChild(smallEl);
          }
          smallEl.textContent = staffId;
          
          // Remove small from other cards
          staffCards.forEach(c => {
              if (c !== this && c.querySelector('small')) {
                  c.querySelector('small').remove();
              }
          });
          
          // Fetch attendance data for this staff
          fetchStaffAttendance(staffId);
      });
  });
}

function initializePagination() {
  const pageButtons = document.querySelectorAll('.page-btn');
  
  pageButtons.forEach(button => {
      button.addEventListener('click', function() {
          // Skip if it's already active or it's an arrow button
          if (this.classList.contains('active') || 
              this.textContent === '←' || 
              this.textContent === '→') {
              return;
          }
          
          // Remove active class from all buttons
          pageButtons.forEach(b => b.classList.remove('active'));
          
          // Add active class to clicked button
          this.classList.add('active');
          
          // Get the selected staff
          const selectedCard = document.querySelector('.staff-card.selected');
          const staffId = selectedCard ? selectedCard.getAttribute('data-staff-id') : null;
          
          // In a real application, you'd load attendance data for this page
          const page = this.textContent;
          console.log(`Loading page ${page} for staff ${staffId}`);
      });
  });
}

function initializeButtons() {
  // Generate Report button handler
  const reportButton = document.querySelector('.attendance-list-header .btn-primary');
  reportButton.addEventListener('click', function() {
      const selectedCard = document.querySelector('.staff-card.selected');
      const staffId = selectedCard ? selectedCard.getAttribute('data-staff-id') : null;
      const staffName = selectedCard ? selectedCard.querySelector('h3').textContent : 'All Staff';
      
      alert(`Generating attendance report for ${staffName} (Week ${currentWeek}, ${currentMonth})`);
      // In a real application, this would likely trigger a download or open a report view
  });
  
  // Profile Details button handlers
  const profileButtons = document.querySelectorAll('.staff-card .btn-secondary');
  profileButtons.forEach(button => {
      button.addEventListener('click', function(e) {
          // Stop the event from bubbling up to the card
          e.stopPropagation();
          
          // Get the staff info from the parent card
          const card = this.closest('.staff-card');
          const staffId = card.getAttribute('data-staff-id');
          const staffName = card.querySelector('h3').textContent;
          
          alert(`Viewing profile details for ${staffName} (${staffId})`);
          // In a real application, this would navigate to a profile page or open a modal
      });
  });
}

function fetchStaffAttendance(staffId) {
  // In a real application, this would be an actual fetch call
  // fetch(`/api/staff/${staffId}/attendance?week=${currentWeek}&month=${currentMonth}`)
  //   .then(response => response.json())
  //   .then(data => updateAttendanceTable(data))
  //   .catch(error => console.error('Error fetching attendance data:', error));
  
  // For demo purposes, we'll simulate the response with mock data
  simulateFetchAttendance(staffId);
}

function simulateFetchAttendance(staffId) {
  const staffData = {
      "816039080": { name: "Taylor Swift", status: "absent" },
      "816031872": { name: "Liam Johnson", status: "present" },
      "816023111": { name: "Lisa Jerado", status: "on-duty" },
      "816042305": { name: "Lewis Winter", status: "present" },
      "816057482": { name: "Andy Callan", status: "present" },
      "816063921": { name: "Quincie Woody", status: "late" }
  };
  
  const staff = staffData[staffId] || { name: "Unknown", status: "unknown" };
  
  // Generate random dates for the past week
  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
  const records = [];
  
  for (let i = 0; i < 3; i++) {
      const record = {
          staff_id: staffId,
          staff_name: staff.name,
          date: `11-${20 + i}-24`,
          day: days[i % 5],
          image: "/api/placeholder/30/30"
      };
      
      // Set login/logout times based on status
      if (staff.status === 'on-duty' && i === 0) {
          record.login_time = "09:30AM";
          record.logout_time = "ON DUTY";
      } else if (staff.status === 'absent' && i === 2) {
          record.login_time = "ABSENT";
          record.logout_time = "ABSENT";
      } else if (staff.status === 'late' && i === 1) {
          record.login_time = "10:15AM";
          record.logout_time = "05:00PM";
      } else {
          record.login_time = "09:00AM";
          record.logout_time = Math.random() > 0.5 ? "05:00PM" : "04:30PM";
      }
      
      records.push(record);
  }
  
  // Update the table with the new data
  updateAttendanceTable(records);
}

function updateAttendanceTable(records) {
  const tableBody = document.getElementById('attendanceTableBody');
  tableBody.innerHTML = '';
  
  records.forEach(record => {
      const row = document.createElement('tr');
      
      // Create cells
      row.innerHTML = `
          <td>${record.staff_id}</td>
          <td>
              <div class="staff-row">
                  <img src="${record.image}" alt="${record.staff_name}" class="avatar avatar-sm">
                  <span>${record.staff_name}</span>
              </div>
          </td>
          <td>${record.date}<br>${record.day}</td>
          <td>${record.login_time}</td>
          <td>${record.logout_time}</td>
      `;
      
      tableBody.appendChild(row);
  });
}