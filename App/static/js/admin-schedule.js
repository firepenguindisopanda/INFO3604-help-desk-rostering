document.addEventListener('DOMContentLoaded', function() {
  // --- Drag and Drop Functionality ---
  initializeDragAndDrop();
  
  // --- Staff Search Modal ---
  initializeStaffSearchModal();
  
  // --- Generate Schedule Button ---
  initializeGenerateButton();
  
  // --- Flash Message Handling ---
  handleFlashMessages();
});

function handleFlashMessages() {
  // Get all flash messages
  const flashMessages = document.querySelectorAll('.flash-message');
  
  // Set a timeout to remove each message after 5 seconds
  flashMessages.forEach(message => {
    setTimeout(() => {
      message.remove();
    }, 5000);
  });
}

function initializeDragAndDrop() {
  // Track the currently dragged staff element
  let draggedStaff = null;
  
  // Add event listener to all draggable elements (delegation)
  document.addEventListener('dragstart', function(e) {
    if (e.target.classList.contains('staff-name')) {
      draggedStaff = e.target;
      
      // Store the staff ID for transfer
      const staffId = e.target.getAttribute('data-staff-id');
      const staffName = e.target.textContent.replace('×', '').trim();
      e.dataTransfer.setData('text/plain', JSON.stringify({
        id: staffId,
        name: staffName
      }));
      
      // Set opacity to indicate dragging
      e.target.classList.add('dragging');
    }
  });
  
  document.addEventListener('dragend', function(e) {
    if (draggedStaff) {
      // Reset opacity
      draggedStaff.classList.remove('dragging');
      draggedStaff = null;
    }
    
    // Remove the droppable indicator from all cells
    document.querySelectorAll('.schedule-cell').forEach(cell => {
      cell.classList.remove('droppable');
      cell.classList.remove('drag-over');
    });
  });
  
  // Prevent default to allow drop
  document.addEventListener('dragover', function(e) {
    const cell = e.target.closest('.schedule-cell');
    if (cell) {
      e.preventDefault();
      
      // Get staff count to check if cell is full
      const staffCount = cell.querySelectorAll('.staff-name').length;
      
      // Add highlight only if not full
      if (staffCount < 3) {
        cell.classList.add('droppable');
      }
    }
  });
  
  // Remove highlight when leaving
  document.addEventListener('dragleave', function(e) {
    const cell = e.target.closest('.schedule-cell');
    if (cell) {
      cell.classList.remove('droppable');
      cell.classList.remove('drag-over');
    }
  });
  
  // Handle drop
  document.addEventListener('drop', function(e) {
    e.preventDefault();
    
    // Find the drop target (schedule cell)
    const cell = e.target.closest('.schedule-cell');
    
    if (cell) {
      // Remove highlight
      cell.classList.remove('droppable');
      cell.classList.remove('drag-over');
      
      // Check if cell is already full (3 staff)
      let staffContainer = cell.querySelector('.staff-container');
      if (staffContainer && staffContainer.querySelectorAll('.staff-name').length >= 3) {
        return; // Cell is full
      }
      
      // Get the staff data
      try {
        const staffData = JSON.parse(e.dataTransfer.getData('text/plain'));
        
        // If the dragged element exists, remove it from its original container
        if (draggedStaff) {
          draggedStaff.remove();
          
          // Check if the original container is now empty
          const originalContainer = document.querySelectorAll('.staff-container');
          originalContainer.forEach(container => {
            updateStaffCounter(container.closest('.schedule-cell'));
          });
        }
        
        // Create or get staff container
        if (!staffContainer) {
          staffContainer = document.createElement('div');
          staffContainer.className = 'staff-container';
          
          // Create staff indicator
          const indicator = document.createElement('div');
          indicator.className = 'staff-slot-indicator';
          indicator.textContent = 'Staff: 0/3';
          staffContainer.appendChild(indicator);
          
          cell.appendChild(staffContainer);
        }
        
        // Add the staff name to the container
        addStaffToContainer(staffContainer, staffData.id, staffData.name);
        
        // Update counter
        updateStaffCounter(cell);
      } catch (error) {
        console.error('Error parsing staff data:', error);
      }
    }
  });
}

function addStaffToContainer(container, staffId, staffName) {
  // Create new staff element
  const staffNameElem = document.createElement('div');
  staffNameElem.className = 'staff-name';
  staffNameElem.setAttribute('draggable', 'true');
  staffNameElem.setAttribute('data-staff-id', staffId);
  staffNameElem.textContent = staffName;
  
  // Add remove button
  const removeButton = document.createElement('button');
  removeButton.className = 'remove-staff';
  removeButton.innerHTML = '&times;';
  removeButton.onclick = function(e) {
    e.stopPropagation();
    staffNameElem.remove();
    updateStaffCounter(container.closest('.schedule-cell'));
  };
  staffNameElem.appendChild(removeButton);
  
  // Add to container
  container.appendChild(staffNameElem);
}

function updateStaffCounter(cell) {
  if (!cell) return;
  
  const staffContainer = cell.querySelector('.staff-container');
  if (!staffContainer) return;
  
  const staffCount = staffContainer.querySelectorAll('.staff-name').length;
  let indicator = staffContainer.querySelector('.staff-slot-indicator');
  
  if (!indicator) {
    indicator = document.createElement('div');
    indicator.className = 'staff-slot-indicator';
    staffContainer.prepend(indicator);
  }
  
  // Update the counter text
  indicator.textContent = `Staff: ${staffCount}/3`;
  
  // Add the "add staff" button if it doesn't exist
  if (!staffContainer.querySelector('.add-staff-btn')) {
    const addButton = document.createElement('button');
    addButton.className = 'add-staff-btn';
    addButton.textContent = '+ Add Staff';
    addButton.onclick = function(e) {
      e.stopPropagation();
      openStaffSearchModal(cell);
    };
    staffContainer.appendChild(addButton);
  }
  
  // Remove the add button if maximum staff reached
  if (staffCount >= 3) {
    const addButton = staffContainer.querySelector('.add-staff-btn');
    if (addButton) {
      addButton.remove();
    }
  }
}

function initializeStaffSearchModal() {
  const modal = document.getElementById('staffSearchModal');
  const closeBtn = modal.querySelector('.close-modal');
  
  // Close when clicking the X
  closeBtn.addEventListener('click', function() {
    modal.style.display = 'none';
  });
  
  // Close when clicking outside the modal
  window.addEventListener('click', function(event) {
    if (event.target === modal) {
      modal.style.display = 'none';
    }
  });
  
  // Initialize search functionality
  const searchInput = document.getElementById('staffSearchInput');
  searchInput.addEventListener('input', function() {
    const searchTerm = this.value.toLowerCase();
    searchStaff(searchTerm);
  });
}

function openStaffSearchModal(cell) {
  const modal = document.getElementById('staffSearchModal');
  const searchInput = document.getElementById('staffSearchInput');
  
  // Clear previous search
  searchInput.value = '';
  document.getElementById('staffSearchResults').innerHTML = '';
  
  // Store the target cell as a data attribute on the modal
  modal.setAttribute('data-target-cell', cell.id);
  
  // Show the modal
  modal.style.display = 'block';
  
  // Focus the search input
  searchInput.focus();
  
  // Populate with all staff initially
  searchStaff('');
}

function searchStaff(searchTerm) {
  // Mock staff data - in a real app, this would come from an API call
  const staffList = [
    { id: 0, name: 'Daniel Rasheed' },
    { id: 1, name: 'Michelle Liu' },
    { id: 2, name: 'Stayaan Maharaj' },
    { id: 3, name: 'Daniel Yatali' },
    { id: 4, name: 'Satish Maharaj' },
    { id: 5, name: 'Selena Madrey' },
    { id: 6, name: 'Veron Ramkissoon' },
    { id: 7, name: 'Tamika Ramkissoon' },
    { id: 8, name: 'Samuel Mahadeo' },
    { id: 9, name: 'Neha Maharaj' }
  ];
  
  // Filter staff based on search term
  const filteredStaff = staffList.filter(staff => 
    staff.name.toLowerCase().includes(searchTerm)
  );
  
  // Display results
  const resultsContainer = document.getElementById('staffSearchResults');
  resultsContainer.innerHTML = '';
  
  if (filteredStaff.length === 0) {
    resultsContainer.innerHTML = '<div class="search-result-item">No staff found</div>';
    return;
  }
  
  filteredStaff.forEach(staff => {
    const resultItem = document.createElement('div');
    resultItem.className = 'search-result-item';
    resultItem.textContent = staff.name;
    resultItem.setAttribute('data-staff-id', staff.id);
    
    resultItem.addEventListener('click', function() {
      selectStaffMember(staff.id, staff.name);
    });
    
    resultsContainer.appendChild(resultItem);
  });
}

function selectStaffMember(staffId, staffName) {
  const modal = document.getElementById('staffSearchModal');
  const targetCellId = modal.getAttribute('data-target-cell');
  const targetCell = document.getElementById(targetCellId) || 
                     document.querySelector(`.schedule-cell[data-id="${targetCellId}"]`);
  
  if (targetCell) {
    let staffContainer = targetCell.querySelector('.staff-container');
    
    // Check if the cell already has this staff member
    const existingStaff = staffContainer.querySelectorAll('.staff-name');
    for (let i = 0; i < existingStaff.length; i++) {
      if (existingStaff[i].getAttribute('data-staff-id') == staffId) {
        // Staff already exists in this cell
        modal.style.display = 'none';
        return;
      }
    }
    
    // Check if the container is full
    if (existingStaff.length >= 3) {
      alert('This shift already has the maximum number of staff (3)');
      modal.style.display = 'none';
      return;
    }
    
    // Add the staff to the container
    addStaffToContainer(staffContainer, staffId, staffName);
    
    // Update counter
    updateStaffCounter(targetCell);
  }
  
  // Close the modal
  modal.style.display = 'none';
}

function initializeGenerateButton() {
  const generateBtn = document.getElementById('generateSchedule');
  const loadingIndicator = document.getElementById('loadingIndicator');
  
  generateBtn.addEventListener('click', function() {
    loadingIndicator.style.display = 'flex';
    
    fetch('/api/schedule/details')
      .then(response => {
        if (!response.ok) {
          return response.json().then(errorData => {
            throw new Error(errorData.message || 'Failed to generate schedule.');
          });
        }
        return response.json();
      })
      .then(data => {
        loadingIndicator.style.display = 'none';
        
        if (data.status === 'success') {
          renderSchedule(data.schedule, data.staff_index);
          
          // Show schedule stats
          const statsDiv = document.getElementById('scheduleStats');
          statsDiv.style.display = 'block';
          
          // Add stats
          const statsList = document.getElementById('statsList');
          statsList.innerHTML = `
            <div class="stat-item">
              <div class="stat-label">Total Staff:</div>
              <div class="stat-value">${Object.keys(data.staff_index).length}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">Total Shifts:</div>
              <div class="stat-value">40</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">Schedule Type:</div>
              <div class="stat-value">Help Desk</div>
            </div>
          `;
        } else {
          alert(`Failed to generate schedule: ${data.message}`);
        }
      })
      .catch(error => {
        loadingIndicator.style.display = 'none';
        console.error('Error generating schedule:', error);
        alert(`An error occurred: ${error.message || 'Unknown error'}`);
      });
  });
}

function renderSchedule(schedule, staffIndex) {
  const scheduleBody = document.getElementById('scheduleBody');
  scheduleBody.innerHTML = '';
  
  // For the help desk, we have hourly slots from 9am to 4pm
  const timeSlots = ["9:00 am", "10:00 am", "11:00 am", "12:00 pm", 
                    "1:00 pm", "2:00 pm", "3:00 pm", "4:00 pm"];
  
  // Create a row for each time slot
  timeSlots.forEach((timeSlot, timeIndex) => {
    const row = document.createElement('tr');
    
    // Add time cell
    const timeCell = document.createElement('td');
    timeCell.className = 'time-cell';
    timeCell.textContent = timeSlot;
    row.appendChild(timeCell);
    
    // Add cells for each day
    schedule.forEach((day, dayIndex) => {
      const shift = day.shifts[timeIndex];
      const cell = document.createElement('td');
      cell.className = 'schedule-cell';
      
      // Set unique id and data attributes for the cell
      const cellId = `cell-${dayIndex}-${timeIndex}`;
      cell.id = cellId;
      cell.setAttribute('data-day', day.day);
      cell.setAttribute('data-time', timeSlot);
      cell.setAttribute('data-id', cellId);
      
      const staffContainer = document.createElement('div');
      staffContainer.className = 'staff-container';
      
      // Show the number of staff assigned
      const staffIndicator = document.createElement('div');
      staffIndicator.className = 'staff-slot-indicator';
      
      if (shift && shift.staff && shift.staff.length > 0) {
        staffIndicator.textContent = `Staff: ${shift.staff.length}/3`;
        
        // Add each staff member
        shift.staff.forEach(staffId => {
          if (staffIndex[staffId]) {
            addStaffToContainer(staffContainer, staffId, staffIndex[staffId]);
          }
        });
      } else {
        staffIndicator.textContent = 'Staff: 0/3';
      }
      
      staffContainer.appendChild(staffIndicator);
      
      // Add "Add Staff" button
      const addButton = document.createElement('button');
      addButton.className = 'add-staff-btn';
      addButton.textContent = '+ Add Staff';
      addButton.onclick = function(e) {
        e.stopPropagation();
        openStaffSearchModal(cell);
      };
      
      // Only add the button if there's room for more staff
      if (!shift || !shift.staff || shift.staff.length < 3) {
        staffContainer.appendChild(addButton);
      }
      
      cell.appendChild(staffContainer);
      row.appendChild(cell);
    });
    
    scheduleBody.appendChild(row);
  });
}