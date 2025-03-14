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
        
        generateAttendanceReport(staffId, staffName);
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
            
            viewProfileDetails(staffId, staffName);
        });
    });
  }
  
  function fetchStaffAttendance(staffId) {
    // Make a real fetch call to the backend API
    fetch(`/api/staff/${staffId}/attendance?week=${currentWeek}&month=${currentMonth}`)
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(data => updateAttendanceTable(data.attendance_records))
      .catch(error => {
        console.error('Error fetching attendance data:', error);
        // Show a user-friendly error message
        const tableBody = document.getElementById('attendanceTableBody');
        tableBody.innerHTML = `<tr><td colspan="5">Failed to load attendance data. Please try again.</td></tr>`;
      });
  }
  
  function updateAttendanceTable(records) {
    const tableBody = document.getElementById('attendanceTableBody');
    tableBody.innerHTML = '';
    
    if (!records || records.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="5">No attendance records found for this period.</td></tr>';
      return;
    }
    
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
  
  function generateAttendanceReport(staffId, staffName) {
    // Show a loading modal or indicator
    const loadingModal = document.createElement('div');
    loadingModal.className = 'loading-indicator';
    loadingModal.innerHTML = `
      <div class="spinner"></div>
      <p>Generating attendance report for ${staffName}...</p>
    `;
    document.body.appendChild(loadingModal);
    
    // Get the date range from the current filters
    const now = new Date();
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
    
    // Make the API call to generate the report
    fetch('/api/staff/attendance/report', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        staff_id: staffId,
        start_date: startOfMonth.toISOString().split('T')[0],
        end_date: now.toISOString().split('T')[0],
        download: true
      })
    })
    .then(response => {
      // Remove loading indicator
      loadingModal.remove();
      
      if (!response.ok) {
        throw new Error('Failed to generate report');
      }
      
      // For direct download, we need to create a blob from the response
      return response.blob();
    })
    .then(blob => {
      // Create a download link for the blob
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `attendance_report_${staffId || 'all'}_${new Date().toISOString().slice(0, 10)}.json`;
      
      // Add to the document and trigger the download
      document.body.appendChild(a);
      a.click();
      
      // Clean up
      window.URL.revokeObjectURL(url);
      a.remove();
    })
    .catch(error => {
      // Remove loading indicator
      if (document.body.contains(loadingModal)) {
        loadingModal.remove();
      }
      
      console.error('Error generating report:', error);
      alert('An error occurred while generating the report. Please try again.');
    });
  }
  
  function viewProfileDetails(staffId, staffName) {
    // Navigate to the staff profile page
    window.location.href = `/admin/staff/${staffId}/profile`;
}
