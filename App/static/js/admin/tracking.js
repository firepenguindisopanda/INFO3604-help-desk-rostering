document.addEventListener('DOMContentLoaded', function() {
  // Initialize staff card selection
  initializeStaffCards();
  
  // Set up button handlers
  initializeButtons();
  
  // Initialize pagination
  initializePagination();
});

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

function fetchStaffAttendance(staffId) {
  // Show loading state
  const tableBody = document.getElementById('attendanceTableBody');
  tableBody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Loading...</td></tr>';
  
  // Make a real fetch call to the backend API
  fetch(`/api/staff/${staffId}/attendance`)
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
      tableBody.innerHTML = `<tr><td colspan="5" class="empty-message">Failed to load attendance data. Please try again.</td></tr>`;
    });
}

function updateAttendanceTable(records) {
  const tableBody = document.getElementById('attendanceTableBody');
  tableBody.innerHTML = '';
  
  if (!records || records.length === 0) {
    tableBody.innerHTML = '<tr><td colspan="5" class="empty-message">No attendance records found for this period.</td></tr>';
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

function initializeButtons() {
  // Generate Report button handler
  const reportButton = document.querySelector('.generate-report-btn');
  if (reportButton) {
    reportButton.addEventListener('click', function() {
      const selectedCard = document.querySelector('.staff-card.selected');
      const staffId = selectedCard ? selectedCard.getAttribute('data-staff-id') : null;
      const staffName = selectedCard ? selectedCard.querySelector('h3').textContent : 'All Staff';
      
      generateAttendanceReport(staffId, staffName);
    });
  }
  
  // Profile Details button handlers
  const profileButtons = document.querySelectorAll('.staff-card .profile-details-btn');
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
      
      // Handle arrow buttons
      if (this.textContent === '←') {
        const activePage = document.querySelector('.page-btn.active');
        if (activePage && activePage.previousElementSibling && 
            activePage.previousElementSibling.textContent !== '←') {
          activePage.previousElementSibling.click();
        }
        return;
      }
      
      if (this.textContent === '→') {
        const activePage = document.querySelector('.page-btn.active');
        if (activePage && activePage.nextElementSibling && 
            activePage.nextElementSibling.textContent !== '→') {
          activePage.nextElementSibling.click();
        }
        return;
      }
      
      // Remove active class from all buttons
      pageButtons.forEach(b => b.classList.remove('active'));
      
      // Add active class to clicked button
      this.classList.add('active');
      
      // Currently pagination doesn't actually fetch different pages
      // This is where you would add code to fetch a specific page of data if needed
    });
  });
}

function generateAttendanceReport(staffId, staffName) {
  // Show a loading modal or indicator
  const loadingModal = document.createElement('div');
  loadingModal.className = 'loading-indicator';
  loadingModal.style.position = 'fixed';
  loadingModal.style.top = '0';
  loadingModal.style.left = '0';
  loadingModal.style.width = '100%';
  loadingModal.style.height = '100%';
  loadingModal.style.backgroundColor = 'rgba(0,0,0,0.5)';
  loadingModal.style.display = 'flex';
  loadingModal.style.alignItems = 'center';
  loadingModal.style.justifyContent = 'center';
  loadingModal.style.zIndex = '1000';
  
  loadingModal.innerHTML = `
    <div style="background: white; padding: 20px; border-radius: 5px; text-align: center;">
      <div class="spinner" style="margin: 0 auto 15px;"></div>
      <p>Generating attendance report for ${staffName}...</p>
    </div>
  `;
  document.body.appendChild(loadingModal);
  
  // Get the date range from the current filters
  const now = new Date();
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
  
  // Make the API call to generate the report
  fetch('/api/staff/attendance/report', {
    method: 'POST',
    headers: buildAuthHeaders(),
    credentials: 'same-origin',
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