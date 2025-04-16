document.addEventListener('DOMContentLoaded', function() {
    // --- Element references ---
    const updateAvailabilityBtn = document.querySelector('.update-availability-btn');
    const availabilityModal = document.getElementById('availabilityModal');
    const closeAvailabilityModal = document.getElementById('closeAvailabilityModal');
    const submitAvailabilityBtn = document.getElementById('submitAvailability');
    const cancelAvailabilityBtn = document.getElementById('cancelAvailability');
    const selectableSlots = document.querySelectorAll('.availability-grid .time-slot.selectable');
    const availabilitySpinner = document.getElementById('availabilitySpinner');
    
    // --- Profile Image Upload Elements ---
    const profileImage = document.querySelector('.profile-image');
    const profileImageOverlay = document.querySelector('.profile-image-overlay');
    const profileImageUpload = document.getElementById('profileImageUpload');
    const profileDisplayImage = document.getElementById('profileDisplayImage');

    // --- Constants ---
    // Time slots in the display
    const timeSlots = [
        '9am - 10am', '10am - 11am', '11am - 12pm', '12pm - 1pm',
        '1pm - 2pm', '2pm - 3pm', '3pm - 4pm'
    ];
    
    // Day mapping for processing availability data
    const dayMapping = {
        'MON': 0,
        'TUE': 1,
        'WED': 2,
        'THUR': 3,
        'FRI': 4
    };

    const days = ['MON', 'TUE', 'WED', 'THUR', 'FRI'];

    // --- Initialize ---
    // Flash messages auto-hide
    setTimeout(function() {
        const messages = document.querySelectorAll('.flash-message');
        messages.forEach(message => {
            message.style.opacity = '0';
            message.style.transition = 'opacity 0.5s';
            setTimeout(() => message.remove(), 500);
        });
    }, 5000);
    
    // --- Profile Image Upload Functionality ---
    if (profileImage && profileImageUpload) {
        // Create and add loading spinner element
        const loadingEl = document.createElement('div');
        loadingEl.className = 'profile-image-loading';
        loadingEl.innerHTML = '<div class="profile-image-spinner"></div>';
        profileImage.appendChild(loadingEl);
        
        // Handle clicking the profile image
        profileImage.addEventListener('click', function() {
            profileImageUpload.click();
        });
        
        // Handle file selection
        profileImageUpload.addEventListener('change', function(e) {
            if (this.files && this.files[0]) {
                // Show loading spinner
                loadingEl.classList.add('active');
                
                // Create FormData object for the upload
                const formData = new FormData();
                formData.append('profile_image', this.files[0]);
                
                // Send the request
                fetch('/volunteer/update_profile', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    // Hide loading spinner
                    loadingEl.classList.remove('active');
                    
                    if (data.success) {
                        // Update the image if URL is returned
                        if (data.image_url) {
                            profileDisplayImage.src = data.image_url;
                        }
                        showFlashMessage('Profile picture updated successfully!', 'success');
                    } else {
                        showFlashMessage('Error updating profile picture: ' + data.message, 'error');
                    }
                })
                .catch(error => {
                    // Hide loading spinner
                    loadingEl.classList.remove('active');
                    console.error('Error updating profile picture:', error);
                    showFlashMessage('An error occurred while updating your profile picture.', 'error');
                });
            }
        });
    }
    
    // --- Event Listeners for Availability ---
    
    // Availability Modal
    if (updateAvailabilityBtn) {
        updateAvailabilityBtn.addEventListener('click', function() {
            initializeAvailabilityModal();
            availabilityModal.style.display = 'block';
        });
    }
    
    if (closeAvailabilityModal) {
        closeAvailabilityModal.addEventListener('click', function() {
            availabilityModal.style.display = 'none';
        });
    }
    
    if (cancelAvailabilityBtn) {
        cancelAvailabilityBtn.addEventListener('click', function() {
            availabilityModal.style.display = 'none';
        });
    }
    
    // Close modals on outside click
    window.addEventListener('click', function(event) {
        if (event.target === availabilityModal) {
            availabilityModal.style.display = 'none';
        }
    });
    
    // Toggle time slots one by one (fixed to prevent multiple selection)
    if (selectableSlots) {
        selectableSlots.forEach(slot => {
            slot.addEventListener('click', function(e) {
                // Toggle only the clicked element - prevent event bubbling
                e.stopPropagation();
                this.classList.toggle('selected');
            });
        });
    }
    
    // Handle availability form submit
    if (submitAvailabilityBtn) {
        submitAvailabilityBtn.addEventListener('click', submitAvailability);
    }
    
    // --- Function Definitions ---
    
    // Initialize the modal's selectable time slots based on current availability
    function initializeAvailabilityModal() {
        console.log("Initializing availability modal");
        // Reset all selections first
        document.querySelectorAll('.availability-grid .time-slot.selectable').forEach(slot => {
            slot.classList.remove('selected');
        });
        
        // Get current availability data from display
        const availabilityMap = extractAvailabilityFromDisplay();
        console.log("Extracted availability:", availabilityMap);
        
        // Mark slots that are currently available
        for (const day in availabilityMap) {
            const dayCol = Array.from(document.querySelectorAll('.availability-grid .day-column')).find(col => {
                const header = col.querySelector('.header');
                return header && header.textContent.trim() === day;
            });
            
            if (dayCol) {
                const availableTimeSlots = availabilityMap[day];
                
                availableTimeSlots.forEach(timeSlot => {
                    const slots = dayCol.querySelectorAll('.time-slot.selectable');
                    
                    slots.forEach(slot => {
                        const slotText = slot.getAttribute('data-time-slot') || slot.textContent.trim();
                        
                        // Check if this slot's time range matches the available time slot
                        if (slotText === timeSlot) {
                            slot.classList.add('selected');
                            console.log(`Marked ${day} ${timeSlot} as selected`);
                        }
                    });
                });
            }
        }
    }

    // Extract availability data from the display table
    function extractAvailabilityFromDisplay() {
        const availabilityMap = {};
        
        // For each day column in the display
        days.forEach(day => {
            availabilityMap[day] = [];
            
            // Find the day column in the display
            const dayColumns = document.querySelectorAll('.availability-table.display-mode .day-column');
            let dayColumn = null;
            
            for (let i = 0; i < dayColumns.length; i++) {
                const header = dayColumns[i].querySelector('.day-header');
                if (header && header.textContent.trim() === day) {
                    dayColumn = dayColumns[i];
                    break;
                }
            }
            
            if (dayColumn) {
                // Get all available time slots for this day
                const availableSlots = dayColumn.querySelectorAll('.time-slot.available');
                availableSlots.forEach(slot => {
                    const timeText = slot.textContent.trim();
                    if (timeText) {
                        availabilityMap[day].push(timeText);
                    }
                });
            }
        });
        
        return availabilityMap;
    }
    
    // Submit availability data
    function submitAvailability() {
        if (availabilitySpinner) {
            availabilitySpinner.style.display = 'inline-block';
        }
        
        // Collect all selected slots
        const selectedSlots = [];
        const dayColumns = document.querySelectorAll('.availability-grid .day-column');
        
        dayColumns.forEach((column, columnIndex) => {
            if (column.classList.contains('header-column')) return;
            
            const dayHeader = column.querySelector('.header');
            const dayName = dayHeader ? dayHeader.textContent.trim() : '';
            const dayIndex = dayMapping[dayName] !== undefined ? dayMapping[dayName] : columnIndex - 1;
            
            const slots = column.querySelectorAll('.time-slot.selectable.selected');
            
            slots.forEach(slot => {
                const timeText = slot.getAttribute('data-time-slot') || slot.textContent.trim();
                const [startStr, endStr] = timeText.split(' - ');
                
                // Convert time strings to 24-hour format for database storage
                selectedSlots.push({
                    day: dayIndex,
                    start_time: formatTime(startStr),
                    end_time: formatTime(endStr)
                });
            });
        });
        
        console.log("Submitting availability:", selectedSlots);
        
        // Send update to server
        fetch('/volunteer/update_availability', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ availabilities: selectedSlots })
        })
        .then(response => response.json())
        .then(data => {
            if (availabilitySpinner) {
                availabilitySpinner.style.display = 'none';
            }
            
            if (data.success) {
                showFlashMessage('Availability updated successfully!', 'success');
                availabilityModal.style.display = 'none';
                
                // Update the availability display without reloading
                updateAvailabilityDisplay(selectedSlots);
            } else {
                showFlashMessage('Error updating availability: ' + data.message, 'error');
            }
        })
        .catch(error => {
            if (availabilitySpinner) {
                availabilitySpinner.style.display = 'none';
            }
            console.error('Error:', error);
            showFlashMessage('An error occurred while updating availability.', 'error');
        });
    }
    
    // Update availability display without page reload
    function updateAvailabilityDisplay(selectedSlots) {
        // Create a map of day/time slots for easier lookup
        const availabilityMap = {};
        days.forEach(day => {
            availabilityMap[day] = new Set();
        });
        
        // Fill in the map with selected slots
        selectedSlots.forEach(slot => {
            const day = days[slot.day];
            if (!day) return;
            
            const startTime = formatDisplayTime(slot.start_time);
            const endTime = formatDisplayTime(slot.end_time);
            const displaySlot = `${startTime} - ${endTime}`;
            
            availabilityMap[day].add(displaySlot);
        });
        
        // Update the UI
        days.forEach(day => {
            // Find the day column in the display table
            const dayColumns = document.querySelectorAll('.availability-table.display-mode .day-column');
            let dayColumn = null;
            
            for (let i = 0; i < dayColumns.length; i++) {
                const header = dayColumns[i].querySelector('.day-header');
                if (header && header.textContent.trim() === day) {
                    dayColumn = dayColumns[i];
                    break;
                }
            }
            
            if (!dayColumn) return;
            
            // Clear all slots first
            const timeSlotElements = dayColumn.querySelectorAll('.time-slot');
            timeSlotElements.forEach(element => {
                element.className = 'time-slot';
                element.textContent = '';
            });
            
            // Fill in the available slots
            availabilityMap[day].forEach(timeSlot => {
                const timeIndex = timeSlots.indexOf(timeSlot);
                if (timeIndex !== -1 && timeIndex < timeSlotElements.length) {
                    const slotElement = timeSlotElements[timeIndex];
                    slotElement.className = 'time-slot available';
                    slotElement.textContent = timeSlot;
                }
            });
        });
    }
    
    // Display flash messages
    function showFlashMessage(message, type = 'success') {
        const flashContainer = document.getElementById('flashMessages');
        
        const flashMessage = document.createElement('div');
        flashMessage.className = `flash-message ${type}`;
        flashMessage.textContent = message;
        
        flashContainer.appendChild(flashMessage);
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            flashMessage.style.opacity = '0';
            flashMessage.style.transition = 'opacity 0.5s';
            setTimeout(() => flashMessage.remove(), 500);
        }, 5000);
    }
    
    // Helper function to format time for database
    function formatTime(timeStr) {
        if (!timeStr) return "00:00:00";
        
        let hour, minute, period;
        
        if (timeStr.includes('am')) {
            period = 'am';
            timeStr = timeStr.replace('am', '').trim();
        } else if (timeStr.includes('pm')) {
            period = 'pm';
            timeStr = timeStr.replace('pm', '').trim();
        }
        
        if (timeStr.includes(':')) {
            [hour, minute] = timeStr.split(':').map(part => parseInt(part, 10));
        } else {
            hour = parseInt(timeStr, 10);
            minute = 0;
        }
        
        if (period === 'pm' && hour < 12) hour += 12;
        if (period === 'am' && hour === 12) hour = 0;
        
        return `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}:00`;
    }
    
    // Helper function to format time for display
    function formatDisplayTime(timeStr) {
        // Convert 24h format like "09:00:00" to "9am"
        if (timeStr && timeStr.includes(':')) {
            const [hourStr, minuteStr] = timeStr.split(':');
            const hour = parseInt(hourStr, 10);
            const ampm = hour >= 12 ? 'pm' : 'am';
            const displayHour = hour > 12 ? hour - 12 : (hour === 0 ? 12 : hour);
            return `${displayHour}${ampm}`;
        }
        return timeStr;
    }
});