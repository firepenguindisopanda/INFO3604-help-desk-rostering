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