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

// Determine current admin role (helpdesk or lab)
const CURRENT_ROLE = document.querySelector('.schedule-header-helpdesk') ? 'helpdesk' : 'lab';
console.log(`Current admin role: ${CURRENT_ROLE}`);

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


function addAvailabilityStyles() {
    const style = document.createElement('style');
    style.textContent = `
        /* Not available cells - RED */
        .schedule-cell.not-available {
            background-color: #ffebee;
            border: 2px dashed #f44336;
            transition: background-color 0.2s;
        }
        
        /* Additional style for unavailable cells when hovered during drag */
        .schedule-cell.unavailable-hover {
            box-shadow: inset 0 0 0 3px #f44336;
            position: relative;
        }
        
        .schedule-cell.unavailable-hover::before {
            content: '⛔';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 24px;
            opacity: 0.7;
            pointer-events: none;
            z-index: 10;
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
    
    // Determine the current user role (helpdesk or lab)
    const currentRole = document.querySelector('.schedule-header-helpdesk') ? 'helpdesk' : 'lab';
    
    // Calculate end date based on role (Friday for helpdesk, Saturday for lab)
    const daysToAdd = currentRole === 'helpdesk' ? 4 : 5; // 4 days from Monday = Friday, 5 days = Saturday
    const endDay = new Date(monday);
    endDay.setDate(monday.getDate() + daysToAdd);
    
    // Log the calculated dates
    console.log(`Setting date range for ${currentRole}:`, monday.toDateString(), "to", endDay.toDateString());
    
    // Set form values
    startDate.valueAsDate = monday;
    endDate.valueAsDate = endDay;
}


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
    
    // Determine the current user role (helpdesk or lab)
    const currentRole = document.querySelector('.schedule-header-helpdesk') ? 'helpdesk' : 'lab';
    console.log(`Current admin role: ${currentRole}`);
    
    return fetch('/api/schedule/current')
        .then(response => {
            if (!response.ok) {
                if (response.status === 404) {
                    console.log(`No existing ${currentRole} schedule found - nothing to load`);
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
            console.log("Received schedule data:", data);
            
            if (data.status === 'success' && data.schedule && data.schedule.schedule_id !== null) {
                console.log(`Existing ${currentRole} schedule found, rendering:`, data.schedule);
                
                // Now render with the fixed days array using the appropriate renderer
                if (currentRole === 'helpdesk') {
                    console.log("Rendering helpdesk schedule on page load");
                    renderSchedule(data.schedule.days);
                } else {
                    console.log("Rendering lab schedule on page load");
                    renderScheduleLab(data.schedule.days);
                }
                
                return true; // Signal that we loaded an existing schedule
            } else {
                console.log(`No valid ${currentRole} schedule data to load`);
                return false;
            }
        })
        .catch(error => {
            loadingIndicator.style.display = 'none';
            console.error(`Error loading ${currentRole} schedule:`, error);
            return false;
        });
}

function loadScheduleData(scheduleId) {
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.style.display = 'flex';
    
    // Determine the current user role (helpdesk or lab)
    const currentRole = document.querySelector('.schedule-header-helpdesk') ? 'helpdesk' : 'lab';
    
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
                // Choose the correct render function based on role
                if (currentRole === 'helpdesk') {
                    renderSchedule(data.schedule.days);
                } else {
                    renderScheduleLab(data.schedule.days);
                }
                
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
    
    const timeSlots = ["9:00 am", "10:00 am", "11:00 am", "12:00 pm", 
                    "1:00 pm", "2:00 pm", "3:00 pm", "4:00 pm"];
    
    timeSlots.forEach((timeSlot, timeIndex) => {
        const row = document.createElement('tr');
        
        const timeCell = document.createElement('td');
        timeCell.className = 'time-cell';
        timeCell.textContent = timeSlot;
        row.appendChild(timeCell);
        
        days.forEach((day, dayIndex) => {
            const cell = document.createElement('td');
            cell.className = 'schedule-cell';
            
            const cellId = `cell-${dayIndex}-${timeIndex}`;
            cell.id = cellId;
            cell.setAttribute('data-day', day.day);
            cell.setAttribute('data-time', timeSlot);
            cell.setAttribute('data-id', cellId);
            
            // Get shift data for this cell if it exists
            const shift = day.shifts[timeIndex];
            
            // Store shift ID if it exists
            if (shift && shift.shift_id) {
                cell.setAttribute('data-shift-id', shift.shift_id);
            }
            
            const staffContainer = document.createElement('div');
            staffContainer.className = 'staff-container';
            
            // Show the number of staff assigned
            const staffIndicator = document.createElement('div');
            staffIndicator.className = 'staff-slot-indicator';
            
            if (shift && shift.assistants && shift.assistants.length > 0) {
                staffIndicator.textContent = `Staff: ${shift.assistants.length}/3`;
                
                // Add each staff member
                shift.assistants.forEach(assistant => {
                    addStaffToContainer(staffContainer, assistant.username || assistant.id, assistant.name);
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
    console.log("Rendering lab schedule with days:", days);
    const scheduleBodyLab = document.getElementById('scheduleBodyLab');
    if (!scheduleBodyLab) {
        console.error("Lab schedule body element not found!");
        showNotification("Error loading lab schedule - please refresh the page", "error");
        return;
    }
    
    scheduleBodyLab.innerHTML = '';
    
    // Lab schedules have 3 time slots per day
    const timeSlots = ["8:00 am - 12:00 pm", "12:00 pm - 4:00 pm", "4:00 pm - 8:00 pm"];
    
    // Create a row for each time slot
    timeSlots.forEach((timeSlot, timeIndex) => {
        const row = document.createElement('tr');
        
        // Add time cell
        const timeCell = document.createElement('td');
        timeCell.className = 'time-cell';
        timeCell.textContent = timeSlot;
        row.appendChild(timeCell);
        
        // Add cells for each day (days should be Monday through Saturday for lab)
        days.forEach((day, dayIndex) => {
            const cell = document.createElement('td');
            cell.className = 'schedule-cell';
            
            // Set unique id and data attributes for the cell
            const cellId = `cell-lab-${dayIndex}-${timeIndex}`;
            cell.id = cellId;
            cell.setAttribute('data-day', day.day);
            cell.setAttribute('data-time', timeSlot);
            cell.setAttribute('data-id', cellId);
            
            // First, build a mapping from time slot index to shift
            let shiftForThisTimeSlot = null;
            
            if (day.shifts && Array.isArray(day.shifts)) {
                // Method 1: Direct index matching (if shifts are ordered by time)
                if (day.shifts[timeIndex]) {
                    shiftForThisTimeSlot = day.shifts[timeIndex];
                }
                
                // Method 2: Try to find by hour property
                if (!shiftForThisTimeSlot) {
                    const hourToFind = timeIndex === 0 ? 8 : timeIndex === 1 ? 12 : 16;
                    shiftForThisTimeSlot = day.shifts.find(s => s.hour === hourToFind);
                }
                
                // Method 3: Try to find by time string if available
                if (!shiftForThisTimeSlot) {
                    const timeMatch = timeIndex === 0 ? "8:00" : 
                                     timeIndex === 1 ? "12:00" : "4:00";
                    shiftForThisTimeSlot = day.shifts.find(s => 
                        (s.time && s.time.includes(timeMatch)) || 
                        (s.start_time && s.start_time.includes(timeMatch))
                    );
                }
            }
            
            const staffContainer = document.createElement('div');
            staffContainer.className = 'staff-container';
            
            // Show the number of staff assigned
            const staffIndicator = document.createElement('div');
            staffIndicator.className = 'staff-slot-indicator';
            
            if (shiftForThisTimeSlot && shiftForThisTimeSlot.assistants && shiftForThisTimeSlot.assistants.length > 0) {
                staffIndicator.textContent = `Staff: ${shiftForThisTimeSlot.assistants.length}/3`;
                
                // Add each staff member
                shiftForThisTimeSlot.assistants.forEach(assistant => {
                    const staffId = assistant.id || assistant.username || assistant.user_id;
                    const staffName = assistant.name || staffId;
                    addStaffToContainer(staffContainer, staffId, staffName);
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
            if (!shiftForThisTimeSlot || !shiftForThisTimeSlot.assistants || shiftForThisTimeSlot.assistants.length < 3) {
                staffContainer.appendChild(addButton);
            }
            
            cell.appendChild(staffContainer);
            row.appendChild(cell);
        });
        
        scheduleBodyLab.appendChild(row);
    });
    
    // After rendering is complete, attach events to all remove buttons
    document.querySelectorAll('.remove-staff').forEach(button => {
        button.removeEventListener('click', handleStaffRemoval);
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
  
    if (!generateBtn) {
        console.error("Generate button not found");
        return;
    }
    
    // Make save button always visible
    if (saveBtn) {
        saveBtn.style.display = 'block';
    }
    
    // Determine the current user role (helpdesk or lab)
    const currentRole = document.querySelector('.schedule-header-helpdesk') ? 'helpdesk' : 'lab';
    console.log(`Initialize button for ${currentRole} role`);

    generateBtn.addEventListener('click', function() {
        // Show loading indicator
        loadingIndicator.style.display = 'flex';
        
        // Get form values
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        console.log(`Generating ${currentRole} schedule for dates ${startDate} to ${endDate}`);

        fetch('/api/schedule/generate', {
            method: 'POST',
            headers: buildAuthHeaders(),
            credentials: 'same-origin',
            body: JSON.stringify({
                start_date: startDate,
                end_date: endDate
            })
        })
        .then(response => {
            console.log(`Got response from generate endpoint: ${response.status}`);
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw new Error(errorData.message || 'Failed to generate schedule.');
                });
            }
            return response.json();
        })
        .then(data => {
            console.log(`Schedule generation results:`, data);
            
            if (data.status === 'success') {
                const scheduleId = data.schedule_id;
                
                // Set the schedule ID on the save button
                if (saveBtn) {
                    saveBtn.setAttribute('data-schedule-id', scheduleId);
                }
                
                // Show success message
                showNotification('Schedule generated successfully', 'success');
                
                if (currentRole === 'lab') {
                    console.log("Lab schedule generated - reloading page to ensure proper rendering");
                    window.location.reload();
                    return;
                }
                
                // For helpdesk, continue with the normal flow (fetch and render)
                console.log(`Fetching schedule details for ID: ${scheduleId}`);
                return fetch(`/api/schedule/details?id=${scheduleId}`)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('Failed to fetch schedule details.');
                        }
                        return response.json();
                    })
                    .then(scheduleData => {
                        loadingIndicator.style.display = 'none';
                        
                        if (scheduleData.status === 'success') {
                            console.log(`Successfully fetched ${currentRole} schedule:`, scheduleData.schedule);
                            
                            // Render the appropriate schedule
                            if (currentRole === 'helpdesk') {
                                console.log("Rendering helpdesk schedule");
                                renderSchedule(scheduleData.schedule.days);
                            } else {
                                console.log("Rendering lab schedule");
                                renderScheduleLab(scheduleData.schedule.days);
                            }
                        } else {
                            throw new Error(`Failed to load schedule: ${scheduleData.message}`);
                        }
                    });
            } else {
                throw new Error(`Failed to generate schedule: ${data.message}`);
            }
        })
        .catch(error => {
            loadingIndicator.style.display = 'none';
            console.error('Error generating or loading schedule:', error);
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
    
    // Determine current role
    const currentRole = document.querySelector('.schedule-header-helpdesk') ? 'helpdesk' : 'lab';
    
    // Get the appropriate schedule body element based on role
    const scheduleCells = document.querySelectorAll(currentRole === 'helpdesk' ? 
        '#scheduleBodyHelpDesk .schedule-cell' : 
        '#scheduleBodyLab .schedule-cell');
    
    console.log(`Found ${scheduleCells.length} schedule cells for ${currentRole} schedule`);
    
    // Collect ALL shift cells, including those with no staff assigned
    const assignments = [];
    
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
        assignments: assignments,
        schedule_type: currentRole // Add schedule type to payload
    };
    
    console.log("Sending save request with payload:", payload);
    
    // Send to server
    fetch('/api/schedule/save', {
        method: 'POST',
        headers: buildAuthHeaders(),
        credentials: 'same-origin',
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
            
            // For lab schedules, reload the page to ensure consistent view
            if (currentRole === 'lab') {
                setTimeout(() => {
                    window.location.reload();
                }, 1500); // Delay the reload a bit to show the success message
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
        headers: buildAuthHeaders(),
        credentials: 'same-origin'
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
        headers: buildAuthHeaders(),
        credentials: 'same-origin'
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

async function handleStaffRemoval(event) {
    event.preventDefault();
    event.stopPropagation();
    
    const staffElement = event.target.closest('.staff-name');
    if (!staffElement) return;
    
    const cell = staffElement.closest('.schedule-cell');
    const staffId = staffElement.getAttribute('data-staff-id');
    const staffName = staffElement.textContent.replace('×', '').trim();
    const cellDay = cell.getAttribute('data-day');
    const cellTime = cell.getAttribute('data-time');
    
    // Try to get the shift_id from data attribute if available
    let shiftId = cell.getAttribute('data-shift-id');
    
    // If not directly available, try to find it through the schedule structure
    if (!shiftId) {
        const cellId = cell.getAttribute('data-id');
        // You might need to implement a way to store shift IDs in the cell data attributes
        // when rendering the schedule
    }
    
    // First, remove from database through API
    try {
        const response = await fetch('/api/schedule/remove-staff', {
            method: 'POST',
            headers: buildAuthHeaders(),
            credentials: 'same-origin',
            body: JSON.stringify({
                staff_id: staffId,
                day: cellDay,
                time: cellTime,
                shift_id: shiftId  // Include shift_id if available
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            // Clear the availability cache
            const cacheKey = `${staffId}-${cellDay}-${cellTime}`;
            if (availabilityCache[cacheKey] !== undefined) {
                delete availabilityCache[cacheKey];
            }
            
            // Remove from UI
            staffElement.remove();
            updateStaffCounter(cell);
            
            // Clear all highlighting
            clearAllCellHighlights();
            
            // Show success message
            showNotification(`${staffName} removed successfully`, 'success');
        } else {
            showNotification(`Failed to remove ${staffName}: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('Error removing staff:', error);
        showNotification(`Error: ${error.message}`, 'error');
    }
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

function highlightAllCellsForStaff(staffId) {
    if (!staffId) return;
    
    console.log(`Highlighting all cells for staff: ${staffId}`);
    
    // Clear any existing highlights first
    clearAllCellHighlights();
    
    // Collect queries for batch request
    const cells = Array.from(document.querySelectorAll('.schedule-cell'));
    const batchQueries = [];
    const cellMeta = []; // parallel metadata to map results
    cells.forEach(cell => {
        const staffContainer = cell.querySelector('.staff-container');
        const staffElements = staffContainer ? staffContainer.querySelectorAll('.staff-name') : [];
        const staffCount = staffElements.length;
        if (staffCount >= 3) return; // full
        let isAlreadyAssigned = false;
        for (let i = 0; i < staffElements.length; i++) {
            if (staffElements[i].getAttribute('data-staff-id') === staffId) { isAlreadyAssigned = true; break; }
        }
        if (isAlreadyAssigned) {
            cell.classList.add('duplicate-assignment');
            if (!cell.querySelector('.already-assigned-msg')) {
                const assignedMsg = document.createElement('div');
                assignedMsg.className = 'already-assigned-msg';
                assignedMsg.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Already assigned';
                if (staffContainer) staffContainer.insertAdjacentElement('afterend', assignedMsg); else cell.appendChild(assignedMsg);
            }
            return;
        }
        const day = cell.getAttribute('data-day');
        const timeSlot = cell.getAttribute('data-time');
        batchQueries.push({ staff_id: staffId, day: day, time: timeSlot });
        cellMeta.push({ cell, day, timeSlot });
    });

    if (batchQueries.length === 0) return;

    // Perform single batch request
    fetch('/api/staff/check-availability/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ queries: batchQueries })
    })
    .then(r => r.ok ? r.json() : Promise.reject(new Error('Batch availability failed')))
    .then(data => {
        if (!data || data.status !== 'success') return;
        const resultMap = new Map();
        data.results.forEach(r => {
            const key = `${r.staff_id}-${r.day}-${r.time}`;
            resultMap.set(key, r.is_available);
            // Populate cache for future single lookups
            availabilityCache[key] = r.is_available;
        });
        // Apply to cells
        cellMeta.forEach(meta => {
            const k = `${staffId}-${meta.day}-${meta.timeSlot}`;
            const isAvail = resultMap.get(k);
            if (isAvail === undefined) return;
            if (isAvail) {
                meta.cell.classList.add('droppable');
                meta.cell.classList.remove('not-available');
            } else {
                meta.cell.classList.add('not-available');
                meta.cell.classList.remove('droppable');
            }
        });
    })
    .catch(err => {
        console.error('Batch availability error', err);
        // Fallback: mark all as droppable to not block UI
        cellMeta.forEach(meta => meta.cell.classList.add('droppable'));
    });
}

function checkAndUpdateCellAvailability(staffId, day, timeSlot, cell) {
    const cacheKey = `${staffId}-${day}-${timeSlot}`;
    
    // Check if staff is already in this cell - don't mark as unavailable if they are
    const existingStaff = cell.querySelectorAll('.staff-name');
    const isAlreadyInCell = Array.from(existingStaff).some(staffElem => 
        staffElem.getAttribute('data-staff-id') === staffId
    );
    
    if (isAlreadyInCell) {
        // Don't apply any availability classes if staff is already assigned
        cell.classList.remove('not-available', 'droppable');
        return;
    }
    
    // Check for cached result
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
    
    // Make API call if no cached result
    fetch(`/api/staff/check-availability?staff_id=${encodeURIComponent(staffId)}&day=${encodeURIComponent(day)}&time=${encodeURIComponent(timeSlot)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const isAvailable = data.status === 'success' && data.is_available;
            availabilityCache[cacheKey] = isAvailable;
            
            console.log(`API result: ${staffId} on ${day} at ${timeSlot}: ${isAvailable ? 'Available ✓' : 'Not Available ✗'}`);
            
            // Only update if we're still dragging
            const currentlyDragging = document.querySelector('.staff-name.dragging');
            if (currentlyDragging && currentlyDragging.getAttribute('data-staff-id') === staffId) {
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
            
            // Default to droppable on error
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
    let draggedStaff = null;
    let draggedStaffId = null;
    
    document.addEventListener('dragstart', function(e) {
        if (e.target.classList.contains('staff-name')) {
            draggedStaff = e.target;
            draggedStaffId = e.target.getAttribute('data-staff-id');
            const staffName = e.target.textContent.replace('×', '').trim();
            
            e.dataTransfer.setData('text/plain', JSON.stringify({
                id: draggedStaffId,
                name: staffName
            }));
            e.dataTransfer.effectAllowed = 'move';
            
            setTimeout(() => {
                if (draggedStaff) {
                    draggedStaff.classList.add('dragging');
                    highlightAllCellsForStaff(draggedStaffId);
                }
            }, 50);
        }
    });
    
    document.addEventListener('dragend', function(e) {
        if (draggedStaff) {
            draggedStaff.classList.remove('dragging');
            clearAllCellHighlights();
            
            // Reset tracking variables
            draggedStaff = null;
            draggedStaffId = null;
            
            // Reset cursor styles
            document.querySelectorAll('.schedule-cell').forEach(cell => {
                cell.style.cursor = '';
                cell.classList.remove('unavailable-hover');
            });
        }
    });
    
    // Prevent default to allow drop
    document.addEventListener('dragover', function(e) {
        // Always prevent default if we're dragging a staff element
        if (draggedStaff) {
            e.preventDefault();
            
            const cell = e.target.closest('.schedule-cell');
            if (cell) {
                // Remove drag-over highlight from all cells
                document.querySelectorAll('.schedule-cell.drag-over').forEach(c => {
                    c.classList.remove('drag-over');
                });
                
                // Remove unavailable-hover from all cells
                document.querySelectorAll('.schedule-cell.unavailable-hover').forEach(c => {
                    c.classList.remove('unavailable-hover');
                });
                
                // Count current staff in cell
                const staffCount = cell.querySelectorAll('.staff-name').length;
                
                // Different visual feedback based on availability
                if (cell.classList.contains('not-available')) {
                    // Cell is not available - show unavailable indicators
                    cell.classList.add('unavailable-hover');
                    cell.style.cursor = 'not-allowed';
                } else if (staffCount >= 3) {
                    // Cell is full - show not allowed cursor
                    cell.style.cursor = 'not-allowed';
                } else {
                    // Cell is available - show droppable highlight
                    cell.classList.add('drag-over');
                    cell.style.cursor = 'copy';
                }
            }
        }
    });
    
    // Clear the drag-over class when leaving a cell
    document.addEventListener('dragleave', function(e) {
        const cell = e.target.closest('.schedule-cell');
        if (cell) {
            cell.classList.remove('drag-over');
            cell.classList.remove('unavailable-hover');
            cell.style.cursor = ''; // Reset cursor
        }
    });
    
    // Drop handling
    document.addEventListener('drop', function(e) {
        e.preventDefault();
        
        // Find the drop target (schedule cell)
        const cell = e.target.closest('.schedule-cell');
        
        if (cell) {
            // Reset cursor styles immediately
            cell.style.cursor = '';
            document.querySelectorAll('.schedule-cell').forEach(c => {
                c.style.cursor = '';
            });
            
            try {
                // Parse staff data early to use in error messages
                const staffData = JSON.parse(e.dataTransfer.getData('text/plain'));
                
                // Check if cell is unavailable before anything else
                if (cell.classList.contains('not-available')) {
                    // Show warning if staff is not available
                    showNotification(`${staffData.name} is not available at this time`, 'warning');
                    
                    // Clear all highlighting
                    clearAllCellHighlights();
                    return; // Prevent drop completely
                }
                
                // Now that we've handled unavailable cells, clear all highlighting
                clearAllCellHighlights();
                
                // Check if cell is already full (3 staff)
                let staffContainer = cell.querySelector('.staff-container');
                if (staffContainer && staffContainer.querySelectorAll('.staff-name').length >= 3) {
                    showNotification("This cell already has the maximum of 3 staff members", "warning");
                    return; // Cell is full
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
                clearAllCellHighlights();
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
        cell.classList.remove('unavailable-hover');
        
        // Reset any inline styles
        cell.style.cursor = '';
        
        // Remove any "Already assigned" messages
        const assignedMsg = cell.querySelector('.already-assigned-msg');
        if (assignedMsg) {
            assignedMsg.remove();
        }
        
        // Remove any visual indicators from staff elements
        const staffElements = cell.querySelectorAll('.staff-name');
        staffElements.forEach(staffElem => {
            staffElem.classList.remove('unavailable-assignment');
            staffElem.removeAttribute('title');
        });
    });
}


function prefetchCommonAvailabilityData() {
    // Gather staff IDs in schedule
    const staffIds = [...new Set(Array.from(document.querySelectorAll('.staff-name')).map(s => s.getAttribute('data-staff-id')).filter(Boolean))];
    if (staffIds.length === 0) return;
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
    const timeSlots = [];
    document.querySelectorAll('.time-cell').forEach(cell => { const t = cell.textContent.trim(); if (t && !timeSlots.includes(t)) timeSlots.push(t); });
    const limitedStaffIds = staffIds.slice(0,3);
    // Build batch queries (cap to avoid huge payload)
    const queries = [];
    limitedStaffIds.forEach(id => {
        days.forEach(d => {
            timeSlots.forEach(ts => {
                if (queries.length < 500) queries.push({ staff_id: id, day: d, time: ts });
            });
        });
    });
    if (queries.length === 0) return;
    console.log(`Batch prefetching ${queries.length} availability combinations`);
    fetch('/api/staff/check-availability/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ queries })
    }).then(r => r.ok ? r.json() : null).then(data => {
        if (!data || data.status !== 'success') return;
        data.results.forEach(r => {
            const key = `${r.staff_id}-${r.day}-${r.time}`;
            availabilityCache[key] = r.is_available;
        });
        console.log(`Prefetch cache size now ${Object.keys(availabilityCache).length}`);
    }).catch(e => console.warn('Batch prefetch failed', e));
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
            // Async availability check can't be directly used inside filter; rely on API already filtered.
            
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
    
    // Force a cache reset if needed
    setTimeout(() => {
        const currentKey = `${staffId}-${day}-${timeSlot}`;
        if (availabilityCache[currentKey] === undefined) {
            // Fetch fresh availability
            fetch(`/api/staff/check-availability?staff_id=${encodeURIComponent(staffId)}&day=${encodeURIComponent(day)}&time=${encodeURIComponent(timeSlot)}`)
                .then(response => response.json())
                .then(data => {
                    if (data && data.status === 'success') {
                        availabilityCache[currentKey] = data.is_available;
                        
                        // Update the cell if needed
                        const cell = document.querySelector(`.schedule-cell[data-day="${day}"][data-time="${timeSlot}"]`);
                        if (cell) {
                            checkAndUpdateCellAvailability(staffId, day, timeSlot, cell);
                        }
                    }
                })
                .catch(error => {
                    console.error(`Error checking availability: ${error.message}`);
                });
        }
    }, 10);
    
    // Default to null (unknown) for immediate sync response
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
    
    // Determine the current role
    const currentRole = document.querySelector('.schedule-header-helpdesk') ? 'helpdesk' : 'lab';
    const scheduleId = currentRole === 'helpdesk' ? 1 : 2; // Helpdesk = 1, Lab = 2
    
    fetch('/api/schedule/clear', {
        method: 'POST',
        headers: buildAuthHeaders(),
        credentials: 'same-origin',
        body: JSON.stringify({
            schedule_type: currentRole,
            schedule_id: scheduleId
        })
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
            
            // Clear the appropriate schedule body based on role
            if (currentRole === 'helpdesk') {
                const scheduleBody = document.getElementById('scheduleBodyHelpDesk');
                if (scheduleBody) {
                    scheduleBody.innerHTML = `
                        <tr>
                            <td colspan="6" class="empty-schedule">
                                <p>No schedule generated yet. Click "Generate Schedule" to create a new schedule.</p>
                            </td>
                        </tr>
                    `;
                }
            } else {
                const scheduleBody = document.getElementById('scheduleBodyLab');
                if (scheduleBody) {
                    scheduleBody.innerHTML = `
                        <tr>
                            <td colspan="7" class="empty-schedule">
                                <p>No schedule generated yet. Click "Generate Schedule" to create a new schedule.</p>
                            </td>
                        </tr>
                    `;
                }
            }
            
            // Clear any cached data in the UI
            if (window.availabilityCache) {
                window.availabilityCache = {};
            }
            
            // Reset any schedule-related attributes
            document.querySelectorAll('[data-schedule-id]').forEach(elem => {
                elem.removeAttribute('data-schedule-id');
            });
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

function resetAvailabilityState() {
    // Clear the availability cache
    Object.keys(availabilityCache).forEach(key => {
        delete availabilityCache[key];
    });
    
    // Clear all cell highlights
    clearAllCellHighlights();
}

// Call this function after removing staff or when needed
function cleanupAfterStaffRemoval(staffId) {
    // Remove all cache entries for this staff
    Object.keys(availabilityCache).forEach(key => {
        if (key.startsWith(`${staffId}-`)) {
            delete availabilityCache[key];
        }
    });
    
    // Remove any visual indicators
    document.querySelectorAll('.staff-name').forEach(staffElem => {
        if (staffElem.getAttribute('data-staff-id') === staffId) {
            staffElem.classList.remove('unavailable-assignment');
            staffElem.removeAttribute('title');
        }
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
