// Shared notification functionality for both admin and volunteer

document.addEventListener('DOMContentLoaded', function() {
  // Get notification elements
  const notificationBadge = document.getElementById('notificationBadge');
  const notificationsPanel = document.getElementById('notificationsPanel');
  const closeNotificationsBtn = document.getElementById('closeNotifications');
  const quickNotificationsList = document.getElementById('quickNotificationsList');
  
  if (!notificationBadge || !notificationsPanel) return;
  
  // Check for unread notifications on load
  updateNotificationCount();
  
  // Toggle notification panel
  notificationBadge.addEventListener('click', function(e) {
      e.stopPropagation();
      
      if (notificationsPanel.style.display === 'none') {
          notificationsPanel.style.display = 'block';
          loadQuickNotifications();
      } else {
          notificationsPanel.style.display = 'none';
      }
  });
  
  // Close notifications panel with X button
  if (closeNotificationsBtn) {
      closeNotificationsBtn.addEventListener('click', function() {
          notificationsPanel.style.display = 'none';
      });
  }
  
  // Close when clicking outside
  document.addEventListener('click', function(e) {
      if (notificationsPanel && !notificationsPanel.contains(e.target) && e.target !== notificationBadge) {
          notificationsPanel.style.display = 'none';
      }
  });
});

// Functions to handle notifications
function updateNotificationCount() {
  fetch('/api/notifications/count')
      .then(response => response.json())
      .then(data => {
          const badge = document.querySelector('.notification-badge');
          if (badge) {
              if (data.count > 0) {
                  badge.classList.add('has-notifications');
                  badge.setAttribute('data-count', data.count);
              } else {
                  badge.classList.remove('has-notifications');
                  badge.removeAttribute('data-count');
              }
          }
      })
      .catch(error => console.error('Error fetching notification count:', error));
}

function loadQuickNotifications() {
  const quickNotificationsList = document.getElementById('quickNotificationsList');
  if (!quickNotificationsList) return;
  
  quickNotificationsList.innerHTML = '<div class="loading-indicator">Loading...</div>';
  
  fetch('/api/notifications?limit=5')
      .then(response => response.json())
      .then(notifications => {
          quickNotificationsList.innerHTML = '';
          
          if (notifications.length === 0) {
              quickNotificationsList.innerHTML = '<div class="empty-state">No new notifications</div>';
              return;
          }
          
          notifications.forEach(notification => {
              const notificationItem = document.createElement('div');
              notificationItem.classList.add('notification-item');
              
              // Get icon based on notification type
              let iconName = 'info';
              if (notification.notification_type === 'approval') iconName = 'check_circle';
              if (notification.notification_type === 'clock_in' || notification.notification_type === 'clock_out') iconName = 'schedule';
              if (notification.notification_type === 'schedule') iconName = 'event';
              if (notification.notification_type === 'reminder') iconName = 'alarm';
              if (notification.notification_type === 'request') iconName = 'assignment';
              if (notification.notification_type === 'missed') iconName = 'error';
              if (notification.notification_type === 'update') iconName = 'update';
              
              notificationItem.innerHTML = `
                  <div class="notification-icon">
                      <span class="material-icons">${iconName}</span>
                  </div>
                  <div class="notification-content">
                      <p>${notification.message}</p>
                      <div class="notification-time">${notification.friendly_time}</div>
                  </div>
              `;
              
              // Add click event to mark as read and navigate to notifications page
              const viewAllLink = document.getElementById('viewAllNotificationsLink');
              const notificationsUrl = viewAllLink ? viewAllLink.getAttribute('href') : '/notifications';
              
              notificationItem.addEventListener('click', function() {
                  markAsRead(notification.id);
                  window.location.href = notificationsUrl;
              });
              
              quickNotificationsList.appendChild(notificationItem);
          });
      })
      .catch(error => {
          console.error('Error loading notifications:', error);
          quickNotificationsList.innerHTML = '<div class="error-state">Failed to load notifications</div>';
      });
}

function markAsRead(notificationId) {
  fetch(`/api/notifications/${notificationId}/read`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
  })
  .then(response => response.json())
  .then(data => {
      if (data.success) {
          updateNotificationCount();
      }
  })
  .catch(error => console.error('Error marking notification as read:', error));
}

function markAllAsRead() {
  fetch('/api/notifications/read-all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
  })
  .then(response => response.json())
  .then(data => {
      if (data.success) {
          // Mark all notifications as read in the UI
          document.querySelectorAll('.notification-item:not(.read)').forEach(item => {
              item.classList.add('read');
              const markReadBtn = item.querySelector('.mark-read-btn');
              if (markReadBtn) markReadBtn.remove();
          });
          updateNotificationCount();
      }
  })
  .catch(error => console.error('Error marking all notifications as read:', error));
}

function deleteNotification(notificationId, element) {
  if (!confirm('Are you sure you want to delete this notification?')) return;
  
  fetch(`/api/notifications/${notificationId}`, {
      method: 'DELETE'
  })
  .then(response => response.json())
  .then(data => {
      if (data.success) {
          if (element) {
              element.remove();
              
              // Check if there are any notifications left
              const notificationsList = document.getElementById('notificationsList');
              if (notificationsList && notificationsList.children.length === 0) {
                  notificationsList.innerHTML = '<div class="empty-state">No notifications yet</div>';
              }
          }
          
          updateNotificationCount();
      }
  })
  .catch(error => console.error('Error deleting notification:', error));
}

// Function to create notification elements for the full notifications page
function createNotificationElement(notification) {
  const item = document.createElement('div');
  item.classList.add('notification-item');
  if (notification.is_read) {
      item.classList.add('read');
  }
  
  // Get icon based on notification type
  let iconName = 'info';
  if (notification.notification_type === 'approval') iconName = 'check_circle';
  if (notification.notification_type === 'clock_in' || notification.notification_type === 'clock_out') iconName = 'schedule';
  if (notification.notification_type === 'schedule') iconName = 'event';
  if (notification.notification_type === 'reminder') iconName = 'alarm';
  if (notification.notification_type === 'request') iconName = 'assignment';
  if (notification.notification_type === 'missed') iconName = 'error';
  if (notification.notification_type === 'update') iconName = 'update';
  
  item.innerHTML = `
      <div class="notification-icon">
          <span class="material-icons">${iconName}</span>
      </div>
      <div class="notification-content">
          <p>${notification.message}</p>
          <div class="notification-time">${notification.friendly_time}</div>
      </div>
      <div class="notification-actions">
          ${!notification.is_read ? 
              `<button class="mark-read-btn" data-id="${notification.id}">
                  <span class="material-icons">done</span>
              </button>` : ''}
          <button class="delete-btn" data-id="${notification.id}">
              <span class="material-icons">delete</span>
          </button>
      </div>
  `;
  
  // Add event listeners
  setTimeout(() => {
      const markReadBtn = item.querySelector('.mark-read-btn');
      if (markReadBtn) {
          markReadBtn.addEventListener('click', function(e) {
              e.stopPropagation();
              markAsRead(notification.id);
              item.classList.add('read');
              markReadBtn.remove();
              updateNotificationCount();
          });
      }
      
      const deleteBtn = item.querySelector('.delete-btn');
      if (deleteBtn) {
          deleteBtn.addEventListener('click', function(e) {
              e.stopPropagation();
              deleteNotification(notification.id, item);
          });
      }
  }, 0);
  
  return item;
}

// Load notifications for the full notification page
function loadNotifications() {
  const notificationsList = document.getElementById('notificationsList');
  if (!notificationsList) return;
  
  fetch('/api/notifications?limit=50&include_read=true')
      .then(response => response.json())
      .then(notifications => {
          // Clear loading indicator
          notificationsList.innerHTML = '';
          
          if (notifications.length === 0) {
              notificationsList.innerHTML = '<div class="empty-state">No notifications yet</div>';
              return;
          }
          
          notifications.forEach(notification => {
              const notificationItem = createNotificationElement(notification);
              notificationsList.appendChild(notificationItem);
          });
      })
      .catch(error => {
          console.error('Error loading notifications:', error);
          notificationsList.innerHTML = 
              '<div class="error-state">Failed to load notifications. Please try again.</div>';
      });
}

// Enhanced notification system for Help Desk application
// Place this in App/static/js/notifications.js to provide consistent notifications across all pages

/**
 * Display a notification message to the user
 * @param {string} message - Message to display
 * @param {string} type - Message type: 'success', 'error', 'info' or 'warning'
 * @param {number} duration - How long to display the message (in ms)
 */
function showNotification(message, type = 'info', duration = 5000) {
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
      icon = '<span class="notification-icon">✓</span>';
    } else if (type === 'error') {
      icon = '<span class="notification-icon">⚠️</span>';
    } else if (type === 'warning') {
      icon = '<span class="notification-icon">⚠</span>';
    } else {
      icon = '<span class="notification-icon">ℹ</span>';
    }
    
    notification.innerHTML = icon + message;
    
    // Add notification to the DOM
    document.body.appendChild(notification);
    
    // Style the notification
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
    }, duration);
  }
  
  /**
   * Converts Flask flash messages to notifications
   * Call this on page load to convert any Flask flash messages to our custom notifications
   */
  function handleFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash-message');
    if (flashMessages.length === 0) return;
    
    // Process each flash message
    flashMessages.forEach((message, index) => {
      // Allow slight delay between messages if there are multiple
      setTimeout(() => {
        // Determine the type of message
        let type = 'info';
        if (message.classList.contains('success')) {
          type = 'success';
        } else if (message.classList.contains('error')) {
          type = 'error';
        } else if (message.classList.contains('warning')) {
          type = 'warning';
        }
        
        // Show the notification and hide the original flash message
        showNotification(message.textContent.trim(), type);
        
        // Hide the original message
        message.style.display = 'none';
      }, index * 300); // Stagger multiple notifications
    });
  }
  
  // Initialize on page load
  document.addEventListener('DOMContentLoaded', function() {
    // Convert any existing flash messages to notifications
    handleFlashMessages();
  });
  
  // Export functions for use in other scripts
  window.showNotification = showNotification;
  window.handleFlashMessages = handleFlashMessages;