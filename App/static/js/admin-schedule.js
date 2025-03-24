// App/static/js/admin-schedule.js
document.addEventListener('DOMContentLoaded', function() {
    // Set default dates
    setDefaultDates();
    
    // --- Drag and Drop Functionality ---
    initializeDragAndDrop();
    
    // --- Staff Search Modal ---
    initializeStaffSearchModal();
    
    // --- Generate Schedule Button ---
    initializeGenerateButton();
    
    // --- Flash Message Handling ---
    handleFlashMessages();
    
    // --- Add global event delegation for remove buttons ---
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('remove-staff') || e.target.parentElement.classList.contains('remove-staff')) {
            handleStaffRemoval(e);
        }
    });
    
    // --- Load Current Schedule If Available ---
    loadCurrentSchedule();
});

function setDefaultDates() {
  const today = new Date();
  const startDate = document.getElementById('startDate');
  const endDate = document.getElementById('endDate');
  
  // Set default start date to today
  startDate.valueAsDate = today;
  
  // Set default end date to Friday of current week
  const dayOfWeek = today.getDay(); // 0 = Sunday, 6 = Saturday
  const daysToFriday = 5 - (dayOfWeek === 0 ? 7 : dayOfWeek); // Convert Sunday (0) to 7
  const friday = new Date(today);
  friday.setDate(today.getDate() + daysToFriday);
  
  endDate.valueAsDate = friday;
}

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

function loadCurrentSchedule() {
    console.log("Loading current schedule...");
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.style.display = 'flex';
    
    fetch('/api/schedule/current')
        .then(response => {
            if (!response.ok) {
                // If no schedule exists yet, that's not an error - just don't display anything
                if (response.status === 404) {
                    console.log("No existing schedule found - nothing to load");
                    loadingIndicator.style.display = 'none';
                    return { status: 'error', message: 'No schedule found' };
                }
                return response.json().then(errorData => {
                    throw new Error(errorData.message || 'Failed to load schedule.');
                });
            }
            return response.json();
        })
        .then(data => {
            loadingIndicator.style.display = 'none';
            
            if (data.status === 'success' && data.schedule && data.schedule.schedule_id !== null) {
                console.log("Existing schedule found, rendering:", data.schedule);
                renderSchedule(data.schedule.days);
                
                // Show schedule stats
                const statsDiv = document.getElementById('scheduleStats');
                statsDiv.style.display = 'block';
                
                // Add stats
                const statsList = document.getElementById('statsList');
                statsList.innerHTML = `
                    <div class="stat-item">
                        <div class="stat-label">Schedule ID:</div>
                        <div class="stat-value">${data.schedule.schedule_id}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Schedule Date Range:</div>
                        <div class="stat-value">${data.schedule.date_range}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Published:</div>
                        <div class="stat-value">${data.schedule.is_published ? 'Yes' : 'No'}</div>
                    </div>
                `;
                
                // Add buttons in a container div
                const buttonContainer = document.createElement('div');
                buttonContainer.className = 'btn-group';
                
                // Add save button if not already published
                if (!data.schedule.is_published) {
                    const saveBtn = document.createElement('button');
                    saveBtn.id = 'saveSchedule';
                    saveBtn.className = 'btn btn-primary';
                    saveBtn.textContent = 'Save Changes';
                    saveBtn.setAttribute('data-schedule-id', data.schedule.schedule_id);
                    saveBtn.onclick = function() {
                        saveScheduleChanges();
                    };
                    buttonContainer.appendChild(saveBtn);
                }
                
                // Add publish button if not already published
                if (!data.schedule.is_published) {
                    const publishBtn = document.createElement('button');
                    publishBtn.className = 'btn btn-success';
                    publishBtn.textContent = 'Publish Schedule';
                    publishBtn.onclick = function() {
                        publishScheduleWithSync(data.schedule.schedule_id);
                    };
                    buttonContainer.appendChild(publishBtn);
                }
                
                // Add the button container to the stats list
                statsList.appendChild(buttonContainer);
                
                return true; // Signal that we loaded an existing schedule
            } else {
                console.log("No valid schedule data to load");
                return false;
            }
        })
        .catch(error => {
            loadingIndicator.style.display = 'none';
            console.error('Error loading schedule:', error);
            return false;
        });
  }

function handleStaffRemoval(event) {
    // Prevent default behavior and stop propagation
    event.preventDefault();
    event.stopPropagation();
    
    // Get the staff element to remove
    const staffElement = event.target.closest('.staff-name');
    if (!staffElement) return;
    
    // Get the containing cell
    const cell = staffElement.closest('.schedule-cell');
    
    // Get staff details for logging
    const staffId = staffElement.getAttribute('data-staff-id');
    const staffName = staffElement.textContent.replace('×', '').trim();
    console.log(`Removing staff: id=${staffId}, name=${staffName}`);
    
    // Remove the staff element
    staffElement.remove();
    
    // Update the staff counter
    updateStaffCounter(cell);
    
    // Log the removal
    console.log(`Staff ${staffName} (${staffId}) removed from ${cell.getAttribute('data-day')} at ${cell.getAttribute('data-time')}`);
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
    
    // Add click handler for existing remove buttons
    document.querySelectorAll('.remove-staff').forEach(button => {
        button.removeEventListener('click', handleStaffRemoval); // Remove any existing handlers
        button.addEventListener('click', handleStaffRemoval);
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
    removeButton.addEventListener('click', handleStaffRemoval);
    staffNameElem.appendChild(removeButton);
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
    const saveBtn = document.getElementById('saveSchedule');
    const loadingIndicator = document.getElementById('loadingIndicator');
  
    generateBtn.addEventListener('click', function() {
        // Show loading indicator
        loadingIndicator.style.display = 'flex';
        
        // Get form values
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        // Call the schedule generation API
        fetch('/api/schedule/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                start_date: startDate,
                end_date: endDate
            })
        })
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
                // Load the schedule data after successful generation
                loadScheduleData(data.schedule_id);
                
                // Show success message
                showNotification('Schedule generated successfully', 'success');
                
                // Show the save button now that we have a schedule
                if (saveBtn) {
                    saveBtn.style.display = 'block';
                    saveBtn.setAttribute('data-schedule-id', data.schedule_id);
                }
            } else {
                showNotification(`Failed to generate schedule: ${data.message}`, 'error');
            }
        })
        .catch(error => {
            loadingIndicator.style.display = 'none';
            console.error('Error generating schedule:', error);
            showNotification(`An error occurred: ${error.message || 'Unknown error'}`, 'error');
        });
    });
    
    // Add the save button handler
    if (saveBtn) {
        saveBtn.addEventListener('click', function() {
            saveScheduleChanges();
        });
    }
}

function loadScheduleData(scheduleId) {
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.style.display = 'flex';
    
    // Fetch the generated schedule data
    fetch(`/api/schedule/details?id=${scheduleId}`)
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw new Error(errorData.message || 'Failed to load schedule.');
                });
            }
            return response.json();
        })
        .then(data => {
            loadingIndicator.style.display = 'none';
            
            if (data.status === 'success') {
                renderSchedule(data.schedule.days);
                
                // Show schedule stats
                const statsDiv = document.getElementById('scheduleStats');
                statsDiv.style.display = 'block';
                
                // Add stats
                const statsList = document.getElementById('statsList');
                statsList.innerHTML = `
                    <div class="stat-item">
                        <div class="stat-label">Schedule Date Range:</div>
                        <div class="stat-value">${data.schedule.date_range}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Published:</div>
                        <div class="stat-value">${data.schedule.is_published ? 'Yes' : 'No'}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Schedule Type:</div>
                        <div class="stat-value">${data.details && !data.details.is_full_week ? 'Partial Week' : 'Full Week'}</div>
                    </div>
                `;
                
                // Add buttons in a container div for better styling
                const buttonContainer = document.createElement('div');
                buttonContainer.className = 'btn-group';
                
                // Add save button if it doesn't exist
                let saveBtn = document.getElementById('saveSchedule');
                if (!saveBtn) {
                    saveBtn = document.createElement('button');
                    saveBtn.id = 'saveSchedule';
                    saveBtn.className = 'btn btn-primary';
                    saveBtn.textContent = 'Save Changes';
                    saveBtn.setAttribute('data-schedule-id', scheduleId);
                    saveBtn.style.display = 'block'; // Make sure it's visible
                    saveBtn.onclick = function() {
                        saveScheduleChanges();
                    };
                    buttonContainer.appendChild(saveBtn);
                } else {
                    // Update existing save button
                    saveBtn.style.display = 'block';
                    saveBtn.setAttribute('data-schedule-id', scheduleId);
                    buttonContainer.appendChild(saveBtn);
                }
                
                // Add publish button if not already published
                if (!data.schedule.is_published) {
                    const publishBtn = document.createElement('button');
                    publishBtn.className = 'btn btn-success';
                    publishBtn.textContent = 'Publish Schedule';
                    publishBtn.onclick = function() {
                        publishScheduleWithSync(scheduleId);
                    };
                    buttonContainer.appendChild(publishBtn);
                }
                
                // Add the button container to the stats list
                statsList.appendChild(buttonContainer);
            } else {
                showNotification(`Failed to load schedule: ${data.message}`, 'error');
            }
        })
        .catch(error => {
            loadingIndicator.style.display = 'none';
            console.error('Error loading schedule:', error);
            showNotification(`An error occurred: ${error.message || 'Unknown error'}`, 'error');
        });
}

// Add a new function to call the sync-enabled publish endpoint
function publishScheduleWithSync(scheduleId) {
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.style.display = 'flex';
    
    fetch(`/api/schedule/${scheduleId}/publish_with_sync`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errorData => {
                throw new Error(errorData.message || 'Failed to publish schedule.');
            });
        }
        return response.json();
    })
    .then(data => {
        loadingIndicator.style.display = 'none';
        
        if (data.status === 'success') {
            showNotification('Schedule published successfully', 'success');
            // Reload schedule data to update UI
            loadScheduleData(scheduleId);
        } else {
            showNotification(`Failed to publish schedule: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        loadingIndicator.style.display = 'none';
        console.error('Error publishing schedule:', error);
        showNotification(`An error occurred: ${error.message || 'Unknown error'}`, 'error');
    });
}

function publishSchedule(scheduleId) {
  const loadingIndicator = document.getElementById('loadingIndicator');
  loadingIndicator.style.display = 'flex';
  
  fetch(`/api/schedule/${scheduleId}/publish`, {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json',
      }
  })
  .then(response => {
      if (!response.ok) {
          return response.json().then(errorData => {
              throw new Error(errorData.message || 'Failed to publish schedule.');
          });
      }
      return response.json();
  })
  .then(data => {
      loadingIndicator.style.display = 'none';
      
      if (data.status === 'success') {
          showNotification('Schedule published successfully', 'success');
          // Reload schedule data to update UI
          loadScheduleData(scheduleId);
      } else {
          showNotification(`Failed to publish schedule: ${data.message}`, 'error');
      }
  })
  .catch(error => {
      loadingIndicator.style.display = 'none';
      console.error('Error publishing schedule:', error);
      showNotification(`An error occurred: ${error.message || 'Unknown error'}`, 'error');
  });
}

function renderSchedule(days) {
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
        
        // Add cells for each day (days should be Monday through Friday)
        days.forEach((day, dayIndex) => {
            const cell = document.createElement('td');
            cell.className = 'schedule-cell';
            
            // Set unique id and data attributes for the cell
            const cellId = `cell-${dayIndex}-${timeIndex}`;
            cell.id = cellId;
            cell.setAttribute('data-day', day.day);
            cell.setAttribute('data-time', timeSlot);
            cell.setAttribute('data-id', cellId);
            
            // Get shift data for this cell if it exists
            const shift = day.shifts[timeIndex];
            
            const staffContainer = document.createElement('div');
            staffContainer.className = 'staff-container';
            
            // Show the number of staff assigned
            const staffIndicator = document.createElement('div');
            staffIndicator.className = 'staff-slot-indicator';
            
            if (shift && shift.assistants && shift.assistants.length > 0) {
                staffIndicator.textContent = `Staff: ${shift.assistants.length}/3`;
                
                // Add each staff member
                shift.assistants.forEach(assistant => {
                    addStaffToContainer(staffContainer, assistant.username, assistant.name);
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
            if (!shift || !shift.assistants || shift.assistants.length < 3) {
                staffContainer.appendChild(addButton);
            }
            
            cell.appendChild(staffContainer);
            row.appendChild(cell);
        });
        
        scheduleBody.appendChild(row);
    });
    
    // After rendering is complete, attach events to all remove buttons
    document.querySelectorAll('.remove-staff').forEach(button => {
        button.removeEventListener('click', handleStaffRemoval); // Remove any existing handlers
        button.addEventListener('click', handleStaffRemoval);
    });
}

function showNotification(message, type = 'info') {
  // Create a notification element
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  notification.textContent = message;
  
  // Add the notification to the page
  document.body.appendChild(notification);
  
  // Remove the notification after a delay
  setTimeout(() => {
      notification.classList.add('hiding');
      setTimeout(() => {
          notification.remove();
      }, 500);
  }, 3000);
}


function saveScheduleChanges() {
    console.log("Saving schedule changes...");
    // Show loading indicator
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.style.display = 'flex';
    
    // Collect ALL shift cells, including those with no staff assigned
    const assignments = [];
    const scheduleCells = document.querySelectorAll('.schedule-cell');
    
    scheduleCells.forEach(cell => {
        // Get day and time data
        const day = cell.getAttribute('data-day');
        const time = cell.getAttribute('data-time');
        const cellId = cell.getAttribute('data-id');
        
        // Debug output
        console.log(`Processing cell: day=${day}, time=${time}, id=${cellId}`);
        
        // Create an entry for this cell regardless of staff
        const staffAssignments = [];
        
        // Get the staff container
        const staffContainer = cell.querySelector('.staff-container');
        if (staffContainer) {
            // Get all staff in this cell
            const staffElements = staffContainer.querySelectorAll('.staff-name');
            
            staffElements.forEach(staff => {
                const staffId = staff.getAttribute('data-staff-id');
                const staffName = staff.textContent.replace('×', '').trim();
                
                staffAssignments.push({
                    id: staffId,
                    name: staffName
                });
                
                // Debug output
                console.log(`  - Staff: id=${staffId}, name=${staffName}`);
            });
        }
        
        // Always add this cell's assignment data, even if empty
        assignments.push({
            day: day,
            time: time,
            cell_id: cellId,
            staff: staffAssignments
        });
    });
    
    console.log(`Collected ${assignments.length} assignments to save`);
    
    // Get schedule metadata
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    // Create payload
    const payload = {
        start_date: startDate,
        end_date: endDate,
        assignments: assignments
    };
    
    console.log("Sending save request with payload:", payload);
    
    // Send to server
    fetch('/api/schedule/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errorData => {
                throw new Error(errorData.message || 'Failed to save schedule.');
            });
        }
        return response.json();
    })
    .then(data => {
        loadingIndicator.style.display = 'none';
        
        if (data.status === 'success') {
            console.log("Schedule saved successfully:", data);
            showNotification('Schedule saved successfully', 'success');
            
            // If schedule_id was returned, update any UI elements that use it
            if (data.schedule_id) {
                document.querySelectorAll('[data-schedule-id]').forEach(elem => {
                    elem.setAttribute('data-schedule-id', data.schedule_id);
                });
                
                // Add a timestamp to the save to track when it happened
                const saveTimestamp = document.createElement('div');
                saveTimestamp.className = 'save-timestamp';
                saveTimestamp.textContent = `Last saved: ${new Date().toLocaleTimeString()}`;
                saveTimestamp.style.marginTop = '10px';
                saveTimestamp.style.color = '#666';
                saveTimestamp.style.fontSize = '12px';
                
                const statsDiv = document.getElementById('scheduleStats');
                if (statsDiv) {
                    // Remove any existing timestamp
                    const existingTimestamp = statsDiv.querySelector('.save-timestamp');
                    if (existingTimestamp) {
                        existingTimestamp.remove();
                    }
                    
                    statsDiv.appendChild(saveTimestamp);
                }
            }
        } else {
            console.error("Failed to save schedule:", data);
            showNotification(`Failed to save schedule: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        loadingIndicator.style.display = 'none';
        console.error('Error saving schedule:', error);
        showNotification(`An error occurred: ${error.message || 'Unknown error'}`, 'error');
    });
}