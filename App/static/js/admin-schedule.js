document.addEventListener('DOMContentLoaded', function() {
  // --- Week Selection and Date Management ---
  initializeWeekSelector();
  
  // --- Drag and Drop Functionality ---
  initializeDragAndDrop();
});

function initializeWeekSelector() {
  const weekSelector = document.getElementById('weekSelector');
  const weekDropdown = document.getElementById('weekDropdown');
  const weekOptions = document.querySelectorAll('.week-option');
  
  // Show/hide dropdown when clicking the selector
  weekSelector.addEventListener('click', function() {
      weekDropdown.classList.toggle('active');
  });

  // Close dropdown when clicking outside
  document.addEventListener('click', function(event) {
      if (!weekSelector.contains(event.target)) {
          weekDropdown.classList.remove('active');
      }
  });

  // Handle week selection
  weekOptions.forEach(option => {
      option.addEventListener('click', function() {
          const weekText = this.textContent;
          weekSelector.firstChild.textContent = weekText;
          weekDropdown.classList.remove('active');
          
          // Extract week number and date range from the selected option
          const weekMatch = weekText.match(/Week (\d+):/);
          if (weekMatch) {
              const weekNum = parseInt(weekMatch[1]);
              updateScheduleDates(weekNum);
          }
      });
  });
  
  // Initialize with the first week
  const firstWeek = weekOptions[0].textContent;
  const weekMatch = firstWeek.match(/Week (\d+):/);
  if (weekMatch) {
      const weekNum = parseInt(weekMatch[1]);
      updateScheduleDates(weekNum);
  }
}

function updateScheduleDates(weekNum) {
  // Calculate the Monday of the selected week
  // For academic scheduling, we'll use Sept 1, 2024 as reference (Week 1)
  const baseDate = new Date(2024, 8, 1); // Sept 1, 2024
  
  // Adjust to first Monday if base date is not Monday
  const dayOfWeek = baseDate.getDay();
  const daysToAdd = dayOfWeek === 0 ? 1 : (dayOfWeek === 1 ? 0 : 8 - dayOfWeek);
  baseDate.setDate(baseDate.getDate() + daysToAdd);
  
  // Calculate Monday of the selected week
  const mondayOfSelectedWeek = new Date(baseDate);
  mondayOfSelectedWeek.setDate(baseDate.getDate() + (weekNum - 1) * 7);
  
  // Update the date headers
  const dayHeaders = document.querySelectorAll('.day-header');
  const daysOfWeek = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
  const monthNames = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
  ];
  
  dayHeaders.forEach((header, index) => {
      if (index < daysOfWeek.length) {
          const currentDate = new Date(mondayOfSelectedWeek);
          currentDate.setDate(mondayOfSelectedWeek.getDate() + index);
          
          const dayDate = currentDate.getDate();
          const month = monthNames[currentDate.getMonth()];
          
          const dateSpan = header.querySelector('.day-date');
          const nameSpan = header.querySelector('.day-name');
          
          if (dateSpan && nameSpan) {
              dateSpan.textContent = String(dayDate).padStart(2, '0');
              nameSpan.textContent = `${month}, ${daysOfWeek[index]}`;
          }
      }
  });
}

function initializeDragAndDrop() {
  // Track the currently dragged staff element and its source
  let draggedStaff = null;
  let dragSource = null;
  
  // Add event listener to all draggable elements
  document.addEventListener('dragstart', function(e) {
      if (e.target.classList.contains('staff-name') || e.target.classList.contains('staff-item')) {
          draggedStaff = e.target;
          dragSource = e.target.closest('.staff-container') || e.target.closest('.staff-legend');
          
          // Store the staff ID for transfer
          const staffId = e.target.getAttribute('data-staff-id');
          e.dataTransfer.setData('text/plain', staffId);
          
          // Set opacity to indicate dragging
          e.target.style.opacity = '0.4';
      }
  });
  
  document.addEventListener('dragend', function(e) {
      if (draggedStaff) {
          // Reset opacity
          draggedStaff.style.opacity = '1';
          draggedStaff = null;
          dragSource = null;
      }
  });
  
  // Prevent default to allow drop
  document.addEventListener('dragover', function(e) {
      if (e.target.classList.contains('schedule-cell') || 
          e.target.closest('.schedule-cell')) {
          e.preventDefault();
          
          // Find the actual cell
          const cell = e.target.classList.contains('schedule-cell') ? 
                      e.target : e.target.closest('.schedule-cell');
          
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
      if (e.target.classList.contains('schedule-cell') || 
          e.target.closest('.schedule-cell')) {
          const cell = e.target.classList.contains('schedule-cell') ? 
                      e.target : e.target.closest('.schedule-cell');
          cell.classList.remove('droppable');
      }
  });
  
  // Handle drop
  document.addEventListener('drop', function(e) {
      e.preventDefault();
      
      // Find the drop target (schedule cell)
      const dropTarget = e.target.classList.contains('schedule-cell') ? 
                        e.target : e.target.closest('.schedule-cell');
      
      if (dropTarget) {
          // Remove highlight
          dropTarget.classList.remove('droppable');
          
          // Check if cell is already full (3 staff)
          const staffContainer = dropTarget.querySelector('.staff-container');
          if (staffContainer && staffContainer.querySelectorAll('.staff-name').length >= 3) {
              return; // Cell is full
          }
          
          // Get the staff ID
          const staffId = e.dataTransfer.getData('text/plain');
          
          // If dragging from another cell, remove from original location
          if (draggedStaff && draggedStaff.classList.contains('staff-name') && 
              dragSource && dragSource.classList.contains('staff-container')) {
              // This is moving an existing staff member, not creating a new one
              draggedStaff.remove();
              
              // Update counter in source cell
              updateStaffCounter(dragSource.closest('.schedule-cell'));
          }
          
          // Create or get staff container
          let container = staffContainer;
          if (!container) {
              container = document.createElement('div');
              container.className = 'staff-container';
              dropTarget.appendChild(container);
          }
          
          // Create staff indicator if it doesn't exist
          if (!container.querySelector('.staff-slot-indicator')) {
              const indicator = document.createElement('div');
              indicator.className = 'staff-slot-indicator';
              container.appendChild(indicator);
          }
          
          // Create new staff element
          const staffName = document.createElement('div');
          staffName.className = 'staff-name';
          staffName.setAttribute('draggable', 'true');
          staffName.setAttribute('data-staff-id', staffId);
          
          // Get staff name from legend or from the dragged element
          let staffNameText = '';
          if (draggedStaff && draggedStaff.classList.contains('staff-name')) {
              // Use the text from the dragged staff name
              const draggedText = draggedStaff.textContent.trim();
              staffNameText = draggedText.replace('×', '').trim(); // Remove the × if present
          } else {
              // Find name in staff legend
              const staffLegend = document.getElementById('staffLegend');
              const staffItems = staffLegend.querySelectorAll('.staff-item');
              
              for (let i = 0; i < staffItems.length; i++) {
                  if (staffItems[i].getAttribute('data-staff-id') === staffId) {
                      staffNameText = staffItems[i].querySelector('.staff-name-text').textContent;
                      break;
                  }
              }
          }
          
          staffName.textContent = staffNameText;
          
          // Add remove button
          const removeButton = document.createElement('button');
          removeButton.className = 'remove-staff';
          removeButton.innerHTML = '&times;';
          removeButton.onclick = function(e) {
              e.stopPropagation();
              staffName.remove();
              updateStaffCounter(dropTarget);
          };
          staffName.appendChild(removeButton);
          
          // Add to container
          container.appendChild(staffName);
          
          // Update counter
          updateStaffCounter(dropTarget);
      }
  });
}

// This function is reused from the original code
function updateStaffCounter(cell) {
  if (!cell) return;
  
  const staffCount = cell.querySelectorAll('.staff-name').length;
  let indicator = cell.querySelector('.staff-slot-indicator');
  
  if (!indicator) {
      indicator = document.createElement('div');
      indicator.className = 'staff-slot-indicator';
      const container = cell.querySelector('.staff-container');
      if (container) {
          container.prepend(indicator);
      }
  }
  
  indicator.textContent = `Staff: ${staffCount}/3`;
  
  if (staffCount === 0) {
      indicator.textContent = 'Drop staff here (0/3)';
  } else if (staffCount >= 3) {
      // Disable dropping if max staff reached
      cell.setAttribute('ondragover', 'return false;');
  } else {
      // Re-enable dropping
      cell.setAttribute('ondragover', 'allowDrop(event)');
  }
}