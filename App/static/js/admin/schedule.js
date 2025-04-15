// App/static/js/admin-schedule.js

// ==============================
// INITIALIZATION AND SETUP
// ==============================

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

    initializeDownloadPdfButton();
    
    // --- Add global event delegation for remove buttons ---
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('remove-staff') || e.target.parentElement.classList.contains('remove-staff')) {
            handleStaffRemoval(e);
        }
    });
    
    // --- Add CSS for availability indicators ---
    addAvailabilityStyles();
    
    // --- Load Current Schedule If Available ---
    loadCurrentSchedule();

    initializeClearScheduleButton();
    
    // Preload availability data after schedule loads
    setTimeout(function() {
        preloadAvailabilityData();
        prefetchCommonAvailabilityData();
    }, 1000);
});

// ==============================
// UPDATED NOTIFICATION SYSTEM
// ==============================

function showNotification(message, type = 'info') {
    // Remove any existing notifications
    const existingNotifications = document.querySelectorAll('.notification-message');
    existingNotifications.forEach(notification => {
      notification.remove();
    });
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification-message ${type}`;
    
    // Add icon based on type
    let icon = '';
    if (type === 'success') {
      icon = '<span style="margin-right: 8px;">✓</span>';
    } else if (type === 'error') {
      icon = '<span style="margin-right: 8px;">⚠️</span>';
    } else if (type === 'warning') {
      icon = '<span style="margin-right: 8px;">⚠</span>';
    } else {
      icon = '<span style="margin-right: 8px;">ℹ</span>';
    }
    
    notification.innerHTML = icon + message;
    
    // Add notification to the DOM
    document.body.appendChild(notification);
    
    // Style the notification for top-center positioning
    Object.assign(notification.style, {
      position: 'fixed',
      top: '1.5rem',
      left: '50%',
      transform: 'translateX(-50%) translateY(-20px)',
      padding: '0.8rem 1.2rem',
      borderRadius: '6px',
      color: 'white',
      zIndex: '9999',
      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      display: 'flex',
      alignItems: 'center',
      opacity: '0',
      transition: 'all 0.3s ease',
      maxWidth: '90%',
      fontSize: '0.95rem',
      fontWeight: '500'
    });
    
    // Set type-specific styles
    if (type === 'success') {
      notification.style.backgroundColor = '#10b981';
    } else if (type === 'error') {
      notification.style.backgroundColor = '#ef4444';
    } else if (type === 'warning') {
      notification.style.backgroundColor = '#f59e0b';
    } else {
      notification.style.backgroundColor = '#3b82f6';
    }
    
    // Animate in
    setTimeout(() => {
      notification.style.opacity = '1';
      notification.style.transform = 'translateX(-50%) translateY(0)';
    }, 10);
    
    // Remove after a delay
    setTimeout(() => {
      notification.style.opacity = '0';
      notification.style.transform = 'translateX(-50%) translateY(-20px)';
      
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
      }, 300);
    }, 5000);
  }

// Update styles to make the highlighting more distinct
function addAvailabilityStyles() {
    const style = document.createElement('style');
    style.textContent = `
        /* Not available cells - RED */
        .schedule-cell.not-available {
            background-color: #ffebee;
            border: 2px dashed #f44336;
            transition: background-color 0.2s;
        }
        
        /* Available cells - BLUE */
        .schedule-cell.droppable {
            background-color: #e3f2fd;
            border: 2px dashed #2196f3;
            transition: background-color 0.2s;
        }
        
        /* Duplicate assignment - YELLOW */
        .schedule-cell.duplicate-assignment {
            background-color: #fff8e1;
            border: 2px dashed #ffc107;
            transition: background-color 0.2s;
        }
        
        /* Already assigned message */
        .already-assigned-msg {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0.25rem;
            margin: 0.25rem 0;
            color: #b26a00;
            font-size: 0.75rem;
            background-color: #fff8e1;
            border: 1px solid #ffc107;
            border-radius: 3px;
        }
        
        .already-assigned-msg i {
            margin-right: 4px;
            color: #f0ad4e;
        }
        
        /* Currently hovered cell - GREEN outline */
        .schedule-cell.drag-over {
            box-shadow: inset 0 0 0 3px #4caf50;
        }
        
        /* Staff element being dragged */
        .staff-name.dragging {
            opacity: 0.5;
        }
        
        /* Other existing styles... */
        .modal-subtitle {
            color: #666;
            font-size: 14px;
            margin-top: -10px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .loading-message {
            text-align: center;
            padding: 20px;
            color: #666;
        }
        
        .warning-message {
            background-color: #fff3cd;
            color: #856404;
            padding: 8px;
            border-radius: 4px;
            margin-bottom: 10px;
            font-size: 14px;
        }
        
        .unavailable-assignment {
            background-color: #ffebee !important;
            border: 1px solid #f44336 !important;
            position: relative;
        }
        
        .unavailable-assignment::after {
            content: "⚠️";
            position: absolute;
            right: 25px;
            top: 50%;
            transform: translateY(-50%);
        }
    `;
    document.head.appendChild(style);
}

function setDefaultDates() {
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    
    if (!startDate || !endDate) {
        console.error("Date input elements not found");
        return;
    }
    
    // Get the current date
    const today = new Date();
    console.log("Today is:", today.toDateString(), "Day of week:", today.getDay());
    
    // Calculate Monday of current week
    const monday = getMonday(today);
    
    // Calculate Friday (Monday + 4 days)
    const friday = new Date(monday);
    friday.setDate(monday.getDate() + 4);
    
    // Log the calculated dates
    console.log("Setting date range:", monday.toDateString(), "to", friday.toDateString());
    
    // Set form values
    startDate.valueAsDate = monday;
    endDate.valueAsDate = friday;
}

/**
 * Helper function to get Monday of the week containing the specified date
 * @param {Date} date - The reference date
 * @return {Date} - Monday of the same week
 */
function getMonday(date) {
    const day = date.getDay();
    const monday = new Date(date);
    
    // If it's already Monday, return the same date
    if (day === 1) {
        monday.setHours(0, 0, 0, 0);
        return monday;
    }
    
    // Calculate days to subtract to get to Monday
    // If Sunday (0), go back 6 days
    // Otherwise, subtract (day - 1) days
    const daysToSubtract = day === 0 ? 6 : day - 1;
    
    // Calculate Monday
    monday.setDate(date.getDate() - daysToSubtract);
    monday.setHours(0, 0, 0, 0); // Reset time to midnight
    
    // Verify it's actually a Monday
    if (monday.getDay() !== 1) {
        console.error("Error calculating Monday: Result is", 
                     ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][monday.getDay()]);
    }
    
    return monday;
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

// ==============================
// SCHEDULE LOADING AND RENDERING
// ==============================

function loadCurrentSchedule() {
    console.log("Loading current schedule...");
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.style.display = 'flex';
    
    return fetch('/api/schedule/current')
        .then(response => {
            if (!response.ok) {
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
                
                // FIX: Check the day alignment before rendering
                if (data.schedule.days && data.schedule.days.length > 0) {
                    // Debug the days array to see what's happening
                    console.log("Days array:", data.schedule.days.map(d => d.day));
                    
                    // Make sure days are in correct order: Monday-Friday
                    const correctOrder = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
                    const currentOrder = data.schedule.days.map(d => d.day);
                    
                    // Check if we need to reorder
                    if (JSON.stringify(currentOrder) !== JSON.stringify(correctOrder)) {
                        console.warn("Day order mismatch, fixing alignment");
                        
                        // Create a properly ordered days array
                        const reorderedDays = [];
                        for (const dayName of correctOrder) {
                            const dayData = data.schedule.days.find(d => d.day === dayName);
                            if (dayData) {
                                reorderedDays.push(dayData);
                            } else {
                                // Create empty day if missing
                                reorderedDays.push({
                                    day: dayName,
                                    date: "",
                                    shifts: []
                                });
                            }
                        }
                        
                        // Replace with corrected order
                        data.schedule.days = reorderedDays;
                    }
                }
                
                // Now render with the fixed days array
                renderSchedule(data.schedule.days);
                
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
                
                // Update save button with schedule ID
                const saveBtn = document.getElementById('saveSchedule');
                if (saveBtn) {
                    saveBtn.setAttribute('data-schedule-id', scheduleId);
                }
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

function renderSchedule(days) {
    const scheduleBodyHelpDesk = document.getElementById('scheduleBodyHelpDesk');
    scheduleBodyHelpDesk.innerHTML = '';
    
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
        
        scheduleBodyHelpDesk.appendChild(row);
    });
    
    // After rendering is complete, attach events to all remove buttons
    document.querySelectorAll('.remove-staff').forEach(button => {
        button.removeEventListener('click', handleStaffRemoval); // Remove any existing handlers
        button.addEventListener('click', handleStaffRemoval);
    });
}


function renderScheduleLab(days) {
    const scheduleBodyLab = document.getElementById('scheduleBodyLab');
    scheduleBodyLab.innerHTML = '';
    
    // For the help desk, we have hourly slots from 9am to 4pm
    const timeSlots = ["8:00 am", "12:00 pm", "4:00 pm"];
    
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
        
        scheduleBodyLab.appendChild(row);
    });
    
    // After rendering is complete, attach events to all remove buttons
    document.querySelectorAll('.remove-staff').forEach(button => {
        button.removeEventListener('click', handleStaffRemoval); // Remove any existing handlers
        button.addEventListener('click', handleStaffRemoval);
    });
}


// ==============================
// SCHEDULE GENERATION AND MANAGEMENT
// ==============================

function initializeGenerateButton() {
    const generateBtn = document.getElementById('generateSchedule');
    const saveBtn = document.getElementById('saveSchedule');
    const loadingIndicator = document.getElementById('loadingIndicator');
  
    // Make save button always visible
    if (saveBtn) {
        saveBtn.style.display = 'block';
    }

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
                
                // Set the schedule ID on the save button
                if (saveBtn) {
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

// ==============================
// STAFF MANAGEMENT IN SCHEDULE
// ==============================

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
    
    // Add to container
    container.appendChild(staffNameElem);
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
    
    // Clear any "Already assigned" messages
    const assignedMsg = cell.querySelector('.already-assigned-msg');
    if (assignedMsg) {
        assignedMsg.remove();
    }
    
    // Log the removal
    console.log(`Staff ${staffName} (${staffId}) removed from ${cell.getAttribute('data-day')} at ${cell.getAttribute('data-time')}`);
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

// ==============================
// DRAG AND DROP FUNCTIONALITY
// ==============================

/**
 * Highlight all cells based on staff availability
 * @param {string} staffId - ID of the staff member being dragged
 */
function highlightAllCellsForStaff(staffId) {
    if (!staffId) return;
    
    console.log(`Highlighting all cells for staff: ${staffId}`);
    
    // Clear any existing highlights first
    clearAllCellHighlights();
    
    // Track count of available cells for debugging
    let availableCount = 0;
    let unavailableCount = 0;
    let duplicateCount = 0;
    
    // Get all schedule cells
    const cells = document.querySelectorAll('.schedule-cell');
    
    // For each cell, set the appropriate highlight
    cells.forEach(cell => {
        // Skip cells that are already full
        const staffContainer = cell.querySelector('.staff-container');
        const staffElements = staffContainer ? staffContainer.querySelectorAll('.staff-name') : [];
        const staffCount = staffElements.length;
        
        if (staffCount >= 3) return;
        
        // Check if this staff is already in this cell
        let isDuplicate = false;
        for (let i = 0; i < staffElements.length; i++) {
            if (staffElements[i].getAttribute('data-staff-id') === staffId) {
                isDuplicate = true;
                break;
            }
        }
        
        if (isDuplicate) {
            // Mark as duplicate with a visible message
            cell.classList.add('duplicate-assignment');
            duplicateCount++;
            
            // Add the "Already assigned" message if it doesn't exist
            if (!cell.querySelector('.already-assigned-msg')) {
                const assignedMsg = document.createElement('div');
                assignedMsg.className = 'already-assigned-msg';
                assignedMsg.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Already assigned';
                
                // Add after the staff container
                if (staffContainer) {
                    staffContainer.insertAdjacentElement('afterend', assignedMsg);
                } else {
                    cell.appendChild(assignedMsg);
                }
            }
            return; // Skip further processing for this cell
        }
        
        // Get the day and time for this cell
        const day = cell.getAttribute('data-day');
        const timeSlot = cell.getAttribute('data-time');
        
        // Generate the availability cache key
        const cacheKey = `${staffId}-${day}-${timeSlot}`;
        
        // Check if we have cached availability data
        if (availabilityCache[cacheKey] !== undefined) {
            // Use cached result
            if (availabilityCache[cacheKey]) {
                cell.classList.add('droppable');
                availableCount++;
            } else {
                cell.classList.add('not-available');
                unavailableCount++;
            }
        } else {
            // For now, don't apply any class - we'll update after fetching availability
            // This prevents momentary flashing of incorrect colors
            
            // Fetch the actual availability and update the display
            checkAndUpdateCellAvailability(staffId, day, timeSlot, cell);
        }
    });
    
    console.log(`Initial highlighting results: ${availableCount} available, ${unavailableCount} unavailable, ${duplicateCount} duplicate`);
}

function checkAndUpdateCellAvailability(staffId, day, timeSlot, cell) {
    const cacheKey = `${staffId}-${day}-${timeSlot}`;
    
    // Check for cached result again (in case it was updated since we started)
    if (availabilityCache[cacheKey] !== undefined) {
        if (availabilityCache[cacheKey]) {
            cell.classList.add('droppable');
            cell.classList.remove('not-available');
        } else {
            cell.classList.add('not-available');
            cell.classList.remove('droppable');
        }
        return;
    }
    
    // Make the API call to check availability
    fetch(`/api/staff/check-availability?staff_id=${encodeURIComponent(staffId)}&day=${encodeURIComponent(day)}&time=${encodeURIComponent(timeSlot)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Update cache with real availability data
            const isAvailable = data.status === 'success' && data.is_available;
            availabilityCache[cacheKey] = isAvailable;
            
            // Log for debugging
            console.log(`API result: ${staffId} on ${day} at ${timeSlot}: ${isAvailable ? 'Available ✓' : 'Not Available ✗'}`);
            
            // Only update the highlighting if we're still in drag mode with this staff
            const currentlyDragging = document.querySelector('.staff-name.dragging');
            if (currentlyDragging && currentlyDragging.getAttribute('data-staff-id') === staffId) {
                // Update cell highlighting
                if (isAvailable) {
                    cell.classList.add('droppable');
                    cell.classList.remove('not-available');
                } else {
                    cell.classList.add('not-available');
                    cell.classList.remove('droppable');
                }
            }
        })
        .catch(error => {
            console.error(`Error checking availability: ${error.message}`);
            
            // On error, mark as available to allow the drag operation to continue
            // but don't cache this result since it's not accurate
            if (cell) {
                cell.classList.add('droppable');
                cell.classList.remove('not-available');
            }
        });
}


/**
 * Fetch availability data and update cell highlighting
 */
function fetchAndUpdateAvailability(staffId, day, timeSlot, cell) {
    const cacheKey = `${staffId}-${day}-${timeSlot}`;
    
    // Make the API call
    fetch(`/api/staff/check-availability?staff_id=${staffId}&day=${encodeURIComponent(day)}&time=${encodeURIComponent(timeSlot)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch availability');
            }
            return response.json();
        })
        .then(data => {
            // Update cache with real availability data
            const isAvailable = data.status === 'success' && data.is_available;
            availabilityCache[cacheKey] = isAvailable;
            
            // Only update the highlighting if we're still in drag mode with this staff
            // This prevents changing highlights if the operation is already done
            const currentlyDragging = document.querySelector('.staff-name.dragging');
            if (currentlyDragging && currentlyDragging.getAttribute('data-staff-id') === staffId) {
                // Update cell highlighting
                if (isAvailable) {
                    cell.classList.add('droppable');
                    cell.classList.remove('not-available');
                } else {
                    cell.classList.add('not-available');
                    cell.classList.remove('droppable');
                }
                
                // Check if we have ANY available cells after this update
                const availableCells = document.querySelectorAll('.schedule-cell.droppable');
                if (availableCells.length === 0) {
                    // If no available cells, make some available to ensure dragging works
                    console.warn('No available cells after availability check, ensuring dragging can work');
                    const cells = document.querySelectorAll('.schedule-cell');
                    cells.forEach(c => {
                        if (!c.classList.contains('duplicate-assignment')) {
                            c.classList.add('droppable');
                            c.classList.remove('not-available');
                        }
                    });
                }
            }
        })
        .catch(error => {
            console.error('Error checking availability:', error);
            // Default to available in case of errors
            availabilityCache[cacheKey] = true;
            
            // Only update if still relevant
            const currentlyDragging = document.querySelector('.staff-name.dragging');
            if (currentlyDragging && currentlyDragging.getAttribute('data-staff-id') === staffId) {
                cell.classList.add('droppable');
                cell.classList.remove('not-available');
            }
        });
}

function initializeDragAndDrop() {
    // Track the currently dragged staff element
    let draggedStaff = null;
    let draggedStaffId = null;
    
    // Add event listener to all draggable elements (delegation)
    document.addEventListener('dragstart', function(e) {
        if (e.target.classList.contains('staff-name')) {
            console.log('Drag started for staff:', e.target.textContent.trim());
            
            draggedStaff = e.target;
            
            // Store the staff ID for transfer
            draggedStaffId = e.target.getAttribute('data-staff-id');
            const staffName = e.target.textContent.replace('×', '').trim();
            
            // Set data in multiple formats to improve compatibility
            e.dataTransfer.setData('text/plain', JSON.stringify({
                id: draggedStaffId,
                name: staffName
            }));
            e.dataTransfer.effectAllowed = 'move';
            
            // Add a small delay before adding the dragging class to ensure
            // the drag operation is fully initiated
            setTimeout(() => {
                if (draggedStaff) {
                    draggedStaff.classList.add('dragging');
                    
                    // Highlight all cells based on availability
                    highlightAllCellsForStaff(draggedStaffId);
                }
            }, 50);
        }
    });
    
    document.addEventListener('dragend', function(e) {
        if (draggedStaff) {
            // Reset opacity
            draggedStaff.classList.remove('dragging');
            
            // Clear all highlighting including "Already assigned" messages
            clearAllCellHighlights();
            
            // Reset tracking variables
            draggedStaff = null;
            draggedStaffId = null;
        }
    });
    
    // Prevent default to allow drop
    document.addEventListener('dragover', function(e) {
        // Always prevent default if we're dragging a staff element
        if (draggedStaff) {
            e.preventDefault();
            
            const cell = e.target.closest('.schedule-cell');
            if (cell) {
                // Add additional highlight for the current cell being hovered
                document.querySelectorAll('.schedule-cell.drag-over').forEach(c => {
                    c.classList.remove('drag-over');
                });
                
                // Only add hover highlight if cell isn't full
                const staffCount = cell.querySelectorAll('.staff-name').length;
                if (staffCount < 3) {
                    cell.classList.add('drag-over');
                }
            }
        }
    });
    
    // Clear the drag-over class when leaving a cell
    document.addEventListener('dragleave', function(e) {
        const cell = e.target.closest('.schedule-cell');
        if (cell) {
            cell.classList.remove('drag-over');
        }
    });
    
    // Drop handling
    document.addEventListener('drop', function(e) {
        e.preventDefault();
        
        // Find the drop target (schedule cell)
        const cell = e.target.closest('.schedule-cell');
        
        if (cell) {
            // Remove all highlighting immediately
            clearAllCellHighlights();
            
            // Check if cell is already full (3 staff)
            let staffContainer = cell.querySelector('.staff-container');
            if (staffContainer && staffContainer.querySelectorAll('.staff-name').length >= 3) {
                showNotification("This cell already has the maximum of 3 staff members", "warning");
                return; // Cell is full
            }
            
            // Get the staff data
            try {
                const staffData = JSON.parse(e.dataTransfer.getData('text/plain'));
                
                // Check if this cell has the "not-available" class
                if (cell.classList.contains('not-available')) {
                    // Show warning if staff is not available
                    showNotification(`${staffData.name} is not available at this time`, 'warning');
                    return;
                }
                
                // Check if staff is already assigned to this cell
                if (staffContainer) {
                    const existingStaff = Array.from(staffContainer.querySelectorAll('.staff-name'));
                    
                    // Check if this staff ID already exists in the cell
                    const isDuplicate = existingStaff.some(staffElem => 
                        staffElem.getAttribute('data-staff-id') === staffData.id
                    );
                    
                    if (isDuplicate) {
                        showNotification(`${staffData.name} is already assigned to this time slot`, 'warning');
                        return;
                    }
                }
                
                // If the dragged element exists, remove it from its original container
                if (draggedStaff) {
                    // Get the original container before removing the staff
                    const originalCell = draggedStaff.closest('.schedule-cell');
                    const originalContainer = draggedStaff.closest('.staff-container');
                    
                    // Remove the staff element
                    draggedStaff.remove();
                    
                    // Update the original cell's counter
                    if (originalCell && originalContainer) {
                        updateStaffCounter(originalCell);
                    }
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
                
                // Reset tracking variables to prevent issues if drop handler is called twice
                draggedStaff = null;
                draggedStaffId = null;
                
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

/**
 * Clear all cell highlights across the schedule
 */
function clearAllCellHighlights() {
    document.querySelectorAll('.schedule-cell').forEach(cell => {
        // Remove all highlighting classes
        cell.classList.remove('droppable');
        cell.classList.remove('not-available');
        cell.classList.remove('drag-over');
        cell.classList.remove('duplicate-assignment');
        
        // Remove any "Already assigned" messages
        const assignedMsg = cell.querySelector('.already-assigned-msg');
        if (assignedMsg) {
            assignedMsg.remove();
        }
    });
}

/**
 * Highlight all schedule cells based on staff availability
 * @param {string} staffId - ID of the staff being dragged
 */
// Add this function to run on page load to get the drag and drop feel faster
function prefetchCommonAvailabilityData() {
    // We'll perform a quick prefetch of availability data for common staff
    // This will make the drag and drop feel more responsive
    
    // Get all staff currently in the schedule
    const staffIds = new Set();
    document.querySelectorAll('.staff-name').forEach(staffElem => {
        const staffId = staffElem.getAttribute('data-staff-id');
        if (staffId) {
            staffIds.add(staffId);
        }
    });
    
    if (staffIds.size === 0) return;
    
    console.log(`Prefetching availability data for ${staffIds.size} staff members`);
    
    // Get all days and time slots
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
    const timeSlots = [];
    document.querySelectorAll('.time-cell').forEach(cell => {
        const timeText = cell.textContent.trim();
        if (timeText && !timeSlots.includes(timeText)) {
            timeSlots.push(timeText);
        }
    });
    
    // Prefetch availability data with staggered requests
    let delay = 0;
    const increment = 50; // 50ms between requests
    
    // Limit to first 3 staff to avoid too many requests
    const limitedStaffIds = Array.from(staffIds).slice(0, 3);
    
    limitedStaffIds.forEach(staffId => {
        days.forEach(day => {
            timeSlots.forEach(timeSlot => {
                delay += increment;
                setTimeout(() => {
                    isStaffAvailableForTimeSlot(staffId, day, timeSlot);
                }, delay);
            });
        });
    });
}

// ==============================
// STAFF SEARCH AND MODAL
// ==============================

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
        const day = modal.getAttribute('data-day');
        const timeSlot = modal.getAttribute('data-time');
        searchAvailableStaff(searchTerm, day, timeSlot);
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
    
    // Also store the day and time of the cell
    const day = cell.getAttribute('data-day');
    const timeSlot = cell.getAttribute('data-time');
    modal.setAttribute('data-day', day);
    modal.setAttribute('data-time', timeSlot);
    
    // Update modal title to include the time slot
    const modalTitle = modal.querySelector('h2');
    if (modalTitle) {
        modalTitle.textContent = `Add Staff for ${day} at ${timeSlot}`;
    }
    
    // Add subtitle to indicate only available staff are shown
    let modalSubtitle = modal.querySelector('.modal-subtitle');
    if (!modalSubtitle) {
        modalSubtitle = document.createElement('p');
        modalSubtitle.className = 'modal-subtitle';
        modalTitle.after(modalSubtitle);
    }
    modalSubtitle.textContent = 'Only showing staff available at this time';
    
    // Show the modal
    modal.style.display = 'block';
    
    // Focus the search input
    searchInput.focus();
    
    // Populate with all available staff for this time slot
    searchAvailableStaff('', day, timeSlot);
}

function searchAvailableStaff(searchTerm, day, timeSlot) {
    // First, show a loading indicator
    const resultsContainer = document.getElementById('staffSearchResults');
    resultsContainer.innerHTML = '<div class="loading-message">Loading available staff...</div>';
    
    // Fetch available staff from the API
    fetch(`/api/staff/available?day=${encodeURIComponent(day)}&time=${encodeURIComponent(timeSlot)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch available staff');
            }
            return response.json();
        })
        .then(data => {
            // Filter staff based on search term if provided
            let staffList = data.staff || [];
            
            if (searchTerm) {
                staffList = staffList.filter(staff => 
                    staff.name.toLowerCase().includes(searchTerm.toLowerCase())
                );
            }
            
            // Display results
            displayStaffSearchResults(staffList, resultsContainer);
        })
        .catch(error => {
            console.error('Error fetching available staff:', error);
            
            // Fallback to mock data if API fails
            let staffList = getMockStaffData();
            
            // Filter by availability (simulate this for now)
            staffList = staffList.filter(staff => isStaffAvailableForTimeSlot(staff.id, day, timeSlot));
            
            // Filter by search term if provided
            if (searchTerm) {
                staffList = staffList.filter(staff => 
                    staff.name.toLowerCase().includes(searchTerm.toLowerCase())
                );
            }
            
            // Display results with a warning about using mock data
            resultsContainer.innerHTML = '<div class="warning-message">Using mock data (API unavailable)</div>';
            displayStaffSearchResults(staffList, resultsContainer);
        });
}

function displayStaffSearchResults(staffList, container) {
    // Clear any existing content (except warnings)
    const warning = container.querySelector('.warning-message');
    container.innerHTML = '';
    if (warning) {
        container.appendChild(warning);
    }
    
    if (staffList.length === 0) {
        container.innerHTML += '<div class="search-result-item">No available staff found</div>';
        return;
    }
    
    // Add each staff member to the results
    staffList.forEach(staff => {
        const resultItem = document.createElement('div');
        resultItem.className = 'search-result-item';
        resultItem.textContent = staff.name;
        resultItem.setAttribute('data-staff-id', staff.id);
        
        resultItem.addEventListener('click', function() {
            selectStaffMember(staff.id, staff.name);
        });
        
        container.appendChild(resultItem);
    });
}

function selectStaffMember(staffId, staffName) {
    const modal = document.getElementById('staffSearchModal');
    const targetCellId = modal.getAttribute('data-target-cell');
    const day = modal.getAttribute('data-day');
    const timeSlot = modal.getAttribute('data-time');
    
    const targetCell = document.getElementById(targetCellId) || 
                     document.querySelector(`.schedule-cell[data-id="${targetCellId}"]`);
    
    if (targetCell) {
        // Double-check availability
        isStaffAvailableForTimeSlot(staffId, day, timeSlot).then(isAvailable => {
            if (!isAvailable) {
                showNotification(`${staffName} is not available at this time`, 'warning');
                modal.style.display = 'none';
                return;
            }
            
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
            
            // Close the modal
            modal.style.display = 'none';
        });
    } else {
        console.error(`Target cell ${targetCellId} not found`);
        modal.style.display = 'none';
    }
}

// Mock data function for fallback
function getMockStaffData() {
    return [
        { id: "816031001", name: 'Daniel Rasheed' },
        { id: "816031002", name: 'Michelle Liu' },
        { id: "816031003", name: 'Stayaan Maharaj' },
        { id: "816031004", name: 'Daniel Yatali' },
        { id: "816031005", name: 'Satish Maharaj' },
        { id: "816031006", name: 'Selena Madrey' },
        { id: "816031007", name: 'Veron Ramkissoon' },
        { id: "816031008", name: 'Tamika Ramkissoon' },
        { id: "816031009", name: 'Samuel Mahadeo' },
        { id: "816031010", name: 'Neha Maharaj' }
    ];
}

// ==============================
// AVAILABILITY CHECKING
// ==============================

// Cache for staff availability to reduce API calls
const availabilityCache = {};

// Function to check if a staff member is available for a specific time slot
async function isStaffAvailableForTimeSlot(staffId, day, timeSlot) {
    const cacheKey = `${staffId}-${day}-${timeSlot}`;
    
    // If we have cached results, use them
    if (availabilityCache[cacheKey] !== undefined) {
        return availabilityCache[cacheKey];
    }
    
    try {
        // Make API call to check availability
        const encodedDay = encodeURIComponent(day);
        const encodedTime = encodeURIComponent(timeSlot);
        const url = `/api/staff/check-availability?staff_id=${staffId}&day=${encodedDay}&time=${encodedTime}`;
        
        console.log(`Checking availability: ${url}`);
        const response = await fetch(url);
        
        if (!response.ok) {
            console.error(`Error checking availability: ${response.statusText}`);
            // Default to true in case of error to not block the UI
            availabilityCache[cacheKey] = true;
            return true;
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Cache the result
            availabilityCache[cacheKey] = data.is_available;
            console.log(`Availability for ${staffId} on ${day} at ${timeSlot}: ${data.is_available}`);
            return data.is_available;
        } else {
            console.error(`API error: ${data.message}`);
            availabilityCache[cacheKey] = true;
            return true;
        }
    } catch (error) {
        console.error(`Error checking availability: ${error}`);
        // Default to true in case of error to not block the UI
        availabilityCache[cacheKey] = true;
        return true;
    }
}

// Synchronous version for immediate feedback during drag operations
function checkAvailabilitySync(staffId, day, timeSlot) {
    const cacheKey = `${staffId}-${day}-${timeSlot}`;
    
    // If we have a cached result, use it
    if (availabilityCache[cacheKey] !== undefined) {
        return availabilityCache[cacheKey];
    }
    
    // For non-cached entries, queue up an async request but don't wait for it
    setTimeout(() => {
        // Only fetch if not already cached (could have been set by another request)
        if (availabilityCache[cacheKey] === undefined) {
            fetch(`/api/staff/check-availability?staff_id=${encodeURIComponent(staffId)}&day=${encodeURIComponent(day)}&time=${encodeURIComponent(timeSlot)}`)
                .then(response => response.ok ? response.json() : null)
                .then(data => {
                    if (data && data.status === 'success') {
                        availabilityCache[cacheKey] = data.is_available;
                    }
                })
                .catch(error => {
                    console.error(`Error in background availability check: ${error.message}`);
                });
        }
    }, 10);
    
    // Default to null for immediate sync response (meaning "unknown")
    return null;
}

function updateUiForAvailabilityChange(staffId, day, timeSlot, isAvailable) {
    // Find any cells that might have this staff member incorrectly assigned
    if (!isAvailable) {
        document.querySelectorAll('.schedule-cell').forEach(cell => {
            const cellDay = cell.getAttribute('data-day');
            const cellTime = cell.getAttribute('data-time');
            
            // If this is the cell being checked
            if (cellDay === day && cellTime === timeSlot) {
                // Find if this staff is assigned to this cell
                const staffElements = cell.querySelectorAll('.staff-name');
                staffElements.forEach(staffElem => {
                    if (staffElem.getAttribute('data-staff-id') === staffId) {
                        // Highlight this assignment as problematic
                        staffElem.classList.add('unavailable-assignment');
                        
                        // You could also add a tooltip or other indicator
                        staffElem.setAttribute('title', 'Staff member is not available at this time');
                    }
                });
            }
        });
    }
}

// Preload availability data for all staff in schedule
function preloadAvailabilityData() {
    console.log("Preloading availability data...");
    
    // Get all staff elements currently in the schedule
    const staffElements = document.querySelectorAll('.staff-name');
    const processedCombinations = new Set();
    
    // Track staff IDs to preload availability data for all time slots
    const allStaffIds = new Set();
    
    // For each staff element, preload availability data for its current cell
    staffElements.forEach(staffElem => {
        const staffId = staffElem.getAttribute('data-staff-id');
        if (!staffId) return;
        
        allStaffIds.add(staffId);
        
        const cell = staffElem.closest('.schedule-cell');
        
        if (cell) {
            const day = cell.getAttribute('data-day');
            const timeSlot = cell.getAttribute('data-time');
            
            // Create a unique key for this combination
            const comboKey = `${staffId}-${day}-${timeSlot}`;
            
            // Only process each combination once
            if (!processedCombinations.has(comboKey)) {
                processedCombinations.add(comboKey);
                
                // Check if we already have this in the cache
                if (availabilityCache[comboKey] === undefined) {
                    // Preload availability
                    checkAvailabilitySync(staffId, day, timeSlot);
                }
            }
        }
    });
    
    // Log the staff we found for debugging
    console.log(`Found ${allStaffIds.size} staff members in the schedule`);
    allStaffIds.forEach(staffId => {
        console.log(`- Staff ID: ${staffId}`);
    });
    
    // For each unique staff ID, preload availability for all time slots
    // This ensures drag and drop operations will be smoother
    if (allStaffIds.size > 0) {
        // Generate a debug report of current cache contents
        let availableCount = 0;
        let unavailableCount = 0;
        Object.keys(availabilityCache).forEach(key => {
            if (availabilityCache[key] === true) availableCount++;
            else if (availabilityCache[key] === false) unavailableCount++;
        });
        
        console.log(`Current cache: ${Object.keys(availabilityCache).length} entries (${availableCount} available, ${unavailableCount} unavailable)`);
    }
}


// Add this function to clear the schedule
function clearSchedule() {
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.style.display = 'flex';
    
    fetch('/api/schedule/clear', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errorData => {
                throw new Error(errorData.message || 'Failed to clear schedule.');
            });
        }
        return response.json();
    })
    .then(data => {
        loadingIndicator.style.display = 'none';
        
        if (data.status === 'success') {
            showNotification('Schedule cleared successfully', 'success');
            
            // Clear the schedule display
            const scheduleBodyHelpDesk = document.getElementById('scheduleBodyHelpDesk');
            scheduleBodyHelpDesk.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-schedule">
                        <p>No schedule generated yet. Click "Generate Schedule" to create a new schedule.</p>
                    </td>
                </tr>
            `;
            
            // Clear any cached data in the UI
            if (window.availabilityCache) {
                window.availabilityCache = {};
            }
            
            // Reset any schedule-related attributes
            document.querySelectorAll('[data-schedule-id]').forEach(elem => {
                elem.removeAttribute('data-schedule-id');
            });
            
            // Force reload of the page to ensure everything is fresh
            // Uncomment this if needed:
            // window.location.reload();
        } else {
            showNotification(`Failed to clear schedule: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        loadingIndicator.style.display = 'none';
        console.error('Error clearing schedule:', error);
        showNotification(`An error occurred: ${error.message || 'Unknown error'}`, 'error');
    });
}


function initializeClearScheduleButton() {
    const clearBtn = document.getElementById('clearSchedule');
    const confirmModal = document.getElementById('clearConfirmModal');
    const cancelBtn = document.getElementById('cancelClear');
    const confirmBtn = document.getElementById('confirmClear');
    const closeModalBtn = confirmModal.querySelector('.close-modal');
    
    // Open confirmation modal when clear button is clicked
    clearBtn.addEventListener('click', function() {
        confirmModal.style.display = 'block';
    });
    
    // Close modal when cancel is clicked
    cancelBtn.addEventListener('click', function() {
        confirmModal.style.display = 'none';
    });
    
    // Close modal when X is clicked
    closeModalBtn.addEventListener('click', function() {
        confirmModal.style.display = 'none';
    });
    
    // Close modal when clicking outside the modal
    window.addEventListener('click', function(event) {
        if (event.target === confirmModal) {
            confirmModal.style.display = 'none';
        }
    });
    
    // Execute clear schedule when confirm is clicked
    confirmBtn.addEventListener('click', function() {
        clearSchedule();
        confirmModal.style.display = 'none';
    });
}


//pdf gen 

function initializeDownloadPdfButton() {
    const downloadPdfBtn = document.getElementById('downloadPdf');
    
    if (downloadPdfBtn) {
        downloadPdfBtn.addEventListener('click', function() {
            // Show loading indicator
            const loadingIndicator = document.getElementById('loadingIndicator');
            loadingIndicator.style.display = 'flex';
            
            // Create a new anchor element for the download
            const downloadLink = document.createElement('a');
            downloadLink.href = '/api/schedule/pdf';
            downloadLink.target = '_blank';
            
            // Append the link to the body (required for Firefox)
            document.body.appendChild(downloadLink);
            
            // Trigger the download
            downloadLink.click();
            
            // Remove the link element
            document.body.removeChild(downloadLink);
            
            // Hide loading indicator after a short delay
            setTimeout(() => {
                loadingIndicator.style.display = 'none';
                
                // Show success notification
                showNotification('Schedule PDF is being downloaded', 'success');
            }, 1000);
        });
    }
}
