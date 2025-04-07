// Force modal to display properly
document.addEventListener('DOMContentLoaded', function() {
  // Get elements
  const editBtn = document.getElementById('editProfileBtn');
  const editModal = document.getElementById('editModal');
  const modalContent = document.querySelector('.edit-modal-content');
  const closeBtn = document.querySelector('.close-btn');
  const cancelBtn = document.getElementById('cancelBtn');
  
  // Make sure the modal content is visible and properly positioned
  if (modalContent) {
      // Ensure modal content has proper styling
      modalContent.style.position = 'relative';
      modalContent.style.zIndex = '1001';
      modalContent.style.opacity = '1';
      modalContent.style.visibility = 'visible';
  }
  
  // Edit button click handler
  if (editBtn && editModal) {
      editBtn.addEventListener('click', function() {
          // Force display of modal with specific styling
          editModal.style.display = 'block';
          editModal.style.opacity = '1';
          editModal.style.visibility = 'visible';
          editModal.style.backgroundColor = 'rgba(0,0,0,0.5)';
          editModal.style.zIndex = '1000';
          
          // Force display of modal content
          if (modalContent) {
              modalContent.style.display = 'block';
              modalContent.style.opacity = '1';
              modalContent.style.visibility = 'visible';
          }
          
          // Load courses if needed
          setTimeout(function() {
              const coursesTab = document.querySelector('.edit-tab[data-tab="courses"]');
              if (coursesTab) {
                  loadCourses();
              }
          }, 100);
      });
  }
  
  // Close button handlers
  if (closeBtn) {
      closeBtn.addEventListener('click', function() {
          editModal.style.display = 'none';
      });
  }
  
  if (cancelBtn) {
      cancelBtn.addEventListener('click', function() {
          editModal.style.display = 'none';
      });
  }
  
  // Close when clicking outside
  window.addEventListener('click', function(event) {
      if (event.target === editModal) {
          editModal.style.display = 'none';
      }
  });
  
  // Tab navigation
  const tabs = document.querySelectorAll('.edit-tab');
  const tabContents = document.querySelectorAll('.tab-content');
  
  tabs.forEach(tab => {
      tab.addEventListener('click', function() {
          const tabId = this.getAttribute('data-tab');
          
          // Remove active class from all tabs and contents
          tabs.forEach(t => t.classList.remove('active'));
          tabContents.forEach(c => c.classList.remove('active'));
          
          // Add active class to clicked tab and corresponding content
          this.classList.add('active');
          document.getElementById(`${tabId}-tab`).classList.add('active');
          
          // Load content for specific tabs
          if (tabId === 'courses') {
              loadCourses();
          } else if (tabId === 'availability') {
              initializeAvailability();
          }
      });
  });
  
  // Generate report button
  const reportBtn = document.getElementById('generateReportBtn');
  if (reportBtn) {
      reportBtn.addEventListener('click', function() {
          generateAttendanceReport(
              document.querySelector('input[name="username"]').value,
              document.querySelector('.profile-name').textContent
          );
      });
  }
  
  // Setup time slot selection
  setupTimeSlots();
  
  // Form submission
  const editForm = document.getElementById('editForm');
  if (editForm) {
      editForm.addEventListener('submit', function(e) {
          e.preventDefault();
          submitForm();
      });
  }
  
  // ---- Helper Functions ----
  
  function setupTimeSlots() {
      const slots = document.querySelectorAll('.availability-grid .selectable');
      slots.forEach(slot => {
          slot.addEventListener('click', function() {
              this.classList.toggle('selected');
          });
      });
  }
  
  function loadCourses() {
      const courseSelection = document.getElementById('courseSelection');
      if (!courseSelection) return;
      
      // Show loading spinner
      courseSelection.innerHTML = '<div class="loading-spinner" style="display: block; margin: 2rem auto;"></div><p>Loading courses...</p>';
      
      // Get current courses from the page
      const currentCourseTags = document.querySelectorAll('.courses-list .course-tag');
      const currentCourses = [];
      
      currentCourseTags.forEach(tag => {
          currentCourses.push(tag.textContent.trim());
      });
      
      // Fetch all available courses
      fetch('/api/courses')
          .then(response => response.json())
          .then(data => {
              if (data.success && data.courses) {
                  courseSelection.innerHTML = '';
                  
                  // Sort courses
                  data.courses.sort((a, b) => a.code.localeCompare(b.code));
                  
                  // Create checkbox for each course
                  data.courses.forEach(course => {
                      const isChecked = currentCourses.includes(course.code);
                      
                      const courseItem = document.createElement('div');
                      courseItem.className = 'course-item';
                      
                      courseItem.innerHTML = `
                          <input type="checkbox" id="course-${course.code}" name="courses[]" value="${course.code}" ${isChecked ? 'checked' : ''}>
                          <label for="course-${course.code}">${course.code} - ${course.name}</label>
                      `;
                      
                      courseSelection.appendChild(courseItem);
                  });
              } else {
                  courseSelection.innerHTML = '<p>No courses available or error loading courses.</p>';
              }
          })
          .catch(error => {
              console.error('Error loading courses:', error);
              courseSelection.innerHTML = '<p>Error loading courses. Please try again.</p>';
          });
  }
  
  function initializeAvailability() {
      // Reset all selections
      document.querySelectorAll('.availability-grid .selectable').forEach(slot => {
          slot.classList.remove('selected');
      });
      
      // Get availability data from the table
      const availabilityTable = document.querySelector('.availability-table');
      if (!availabilityTable) return;
      
      const rows = availabilityTable.querySelectorAll('tbody tr');
      
      // Map of day names to day codes
      const dayMapping = {
          'Monday': 'MON',
          'Tuesday': 'TUE',
          'Wednesday': 'WED',
          'Thursday': 'THUR',
          'Friday': 'FRI'
      };
      
      // For each row in availability table
      rows.forEach(row => {
          const cells = row.querySelectorAll('td');
          if (cells.length >= 3) {
              const dayName = cells[0].textContent.trim();
              const startTime = cells[1].textContent.trim();
              const endTime = cells[2].textContent.trim();
              
              const dayCode = dayMapping[dayName] || dayName;
              
              // Find matching start time
              let matchingTimeSlot = null;
              
              // Try to match a time slot
              if (startTime.includes('09:00') || startTime.includes('9:00')) {
                  matchingTimeSlot = '9am - 10am';
              } else if (startTime.includes('10:00')) {
                  matchingTimeSlot = '10am - 11am';
              } else if (startTime.includes('11:00')) {
                  matchingTimeSlot = '11am - 12pm';
              } else if (startTime.includes('12:00')) {
                  matchingTimeSlot = '12pm - 1pm';
              } else if (startTime.includes('13:00') || startTime.includes('1:00 PM')) {
                  matchingTimeSlot = '1pm - 2pm';
              } else if (startTime.includes('14:00') || startTime.includes('2:00 PM')) {
                  matchingTimeSlot = '2pm - 3pm';
              } else if (startTime.includes('15:00') || startTime.includes('3:00 PM')) {
                  matchingTimeSlot = '3pm - 4pm';
              }
              
              if (matchingTimeSlot) {
                  // Find the corresponding time slot element and select it
                  const slot = document.querySelector(`.availability-grid .selectable[data-day="${dayCode}"][data-time-slot="${matchingTimeSlot}"]`);
                  if (slot) {
                      slot.classList.add('selected');
                  }
              }
          }
      });
  }
  
  function submitForm() {
      const formSpinner = document.getElementById('formSpinner');
      
      // Show loading spinner
      if (formSpinner) {
          formSpinner.style.display = 'inline-block';
      }
      
      // Get all form values
      const formData = {
          username: document.querySelector('input[name="username"]').value,
          name: document.getElementById('name').value,
          degree: document.getElementById('degree').value,
          email: document.getElementById('email').value,
          phone: document.getElementById('phone').value,
          rate: parseFloat(document.getElementById('rate').value || 0),
          hours_minimum: parseInt(document.getElementById('hours_minimum').value || 0),
          active: document.querySelector('input[name="active"]:checked')?.value === 'true'
      };
      
      // Get selected courses
      const courseCheckboxes = document.querySelectorAll('input[name="courses[]"]:checked');
      formData.courses = Array.from(courseCheckboxes).map(checkbox => checkbox.value);
      
      // Get selected availability time slots
      const availabilitySlots = [];
      const selectedSlots = document.querySelectorAll('.availability-grid .selectable.selected');
      
      selectedSlots.forEach(slot => {
          const dayCode = slot.getAttribute('data-day');
          const timeSlot = slot.getAttribute('data-time-slot');
          
          // Map day codes to day indices
          const dayMapping = {
              'MON': 0,
              'TUE': 1,
              'WED': 2,
              'THUR': 3,
              'FRI': 4
          };
          
          const dayIndex = dayMapping[dayCode];
          
          // Parse time slot to get start and end time
          const [startStr, endStr] = timeSlot.split(' - ');
          
          // Convert to 24-hour format for database storage
          const formatTime = (timeStr) => {
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
          };
          
          // Add to availability slots
          availabilitySlots.push({
              day: dayIndex,
              start_time: formatTime(startStr),
              end_time: formatTime(endStr)
          });
      });
      
      formData.availabilities = availabilitySlots;
      
      console.log('Submitting Student Assistant profile update:', formData);
      
      // Send update to server
      fetch('/api/admin/staff/update-profile', {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json'
          },
          body: JSON.stringify(formData)
      })
      .then(response => response.json())
      .then(data => {
          if (formSpinner) {
              formSpinner.style.display = 'none';
          }
          
          if (data.success) {
              // Show success message
              showNotification('Profile updated successfully!', 'success');
              
              // Reload the page to see changes
              setTimeout(() => {
                  window.location.reload();
              }, 1500);
          } else {
              showNotification(`Error updating profile: ${data.message || 'Unknown error'}`, 'error');
          }
      })
      .catch(error => {
          if (formSpinner) {
              formSpinner.style.display = 'none';
          }
          console.error('Error updating profile:', error);
          showNotification('An error occurred while updating the profile. Please try again.', 'error');
      });
  }
  
  function generateAttendanceReport(staffId, staffName) {
      // Show a loading indicator
      const loadingIndicator = document.createElement('div');
      loadingIndicator.className = 'loading-indicator';
      loadingIndicator.style.position = 'fixed';
      loadingIndicator.style.top = '50%';
      loadingIndicator.style.left = '50%';
      loadingIndicator.style.transform = 'translate(-50%, -50%)';
      loadingIndicator.style.background = 'rgba(255, 255, 255, 0.9)';
      loadingIndicator.style.padding = '2rem';
      loadingIndicator.style.borderRadius = '8px';
      loadingIndicator.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
      loadingIndicator.style.zIndex = '1000';
      
      loadingIndicator.innerHTML = `
          <div class="spinner" style="border: 4px solid #f3f3f3; border-top: 4px solid #0066cc; border-radius: 50%; width: 40px; height: 40px; animation: spin 2s linear infinite; margin: 0 auto 1rem;"></div>
          <p style="text-align: center; margin: 0;">Generating report for ${staffName}...</p>
          <style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
      `;
      
      document.body.appendChild(loadingIndicator);
      
      // Make the API request
      fetch('/api/staff/attendance/report', {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json'
          },
          body: JSON.stringify({
              staff_id: staffId,
              download: true
          })
      })
      .then(response => {
          if (!response.ok) {
              throw new Error('Failed to generate report');
          }
          return response.blob();
      })
      .then(blob => {
          // Remove loading indicator
          document.body.removeChild(loadingIndicator);
          
          // Create download link
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.style.display = 'none';
          a.href = url;
          a.download = `attendance_report_${staffName.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.json`;
          
          document.body.appendChild(a);
          a.click();
          
          setTimeout(() => {
              window.URL.revokeObjectURL(url);
              document.body.removeChild(a);
          }, 100);
      })
      .catch(error => {
          console.error('Error generating report:', error);
          document.body.removeChild(loadingIndicator);
          showNotification('An error occurred while generating the report. Please try again.', 'error');
      });
  }
  
  function showNotification(message, type = 'info') {
      // Create notification element
      const notification = document.createElement('div');
      notification.className = `notification-message ${type}`;
      notification.textContent = message;
      
      // Style the notification
      Object.assign(notification.style, {
          position: 'fixed',
          top: '1.5rem',
          right: '1.5rem',
          padding: '1rem 1.5rem',
          borderRadius: '4px',
          color: 'white',
          zIndex: '9999',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
      });
      
      // Set color based on type
      if (type === 'success') {
          notification.style.backgroundColor = '#10b981';
      } else if (type === 'error') {
          notification.style.backgroundColor = '#ef4444';
      } else {
          notification.style.backgroundColor = '#3b82f6';
      }
      
      // Add to document
      document.body.appendChild(notification);
      
      // Remove after delay
      setTimeout(() => {
          notification.style.opacity = '0';
          notification.style.transition = 'opacity 0.5s';
          
          setTimeout(() => {
              if (document.body.contains(notification)) {
                  document.body.removeChild(notification);
              }
          }, 500);
      }, 5000);
  }
});