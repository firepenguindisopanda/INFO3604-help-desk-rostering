# Next.js Schedule Page Design Documentation

## Overview
This document analyzes the Flask admin schedule page design and provides a comprehensive guide for recreating it in Next.js. The schedule page features a sophisticated calendar interface with drag-and-drop staff assignment, availability checking, and modal interactions.

## Page Structure & Layout

### Main Layout Components
```
┌─────────────────────────────────────────────────────────────┐
│                     Page Header                              │
│  - Schedule Type Title (Helpdesk/Lab Assistant Schedule)     │
│  - Role-specific branding                                    │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   Date Controls Section                      │
│  ┌─────────────┐  ┌─────────────┐                          │
│  │ Start Date  │  │  End Date   │  [Generate] [Clear]      │
│  │   Input     │  │   Input     │   [Save]   [Download]    │
│  └─────────────┘  └─────────────┘                          │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     Schedule Table                           │
│  ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┐               │
│  │Time │ Mon │ Tue │ Wed │ Thu │ Fri │ Sat │               │
│  ├─────┼─────┼─────┼─────┼─────┼─────┼─────┤               │
│  │9:00 │     │     │     │     │     │     │               │
│  │10:00│     │     │     │     │     │     │               │
│  │...  │     │     │     │     │     │     │               │
│  └─────┴─────┴─────┴─────┴─────┴─────┴─────┘               │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                       Legend                                │
│  🟢 Available  🔴 Unavailable  🟡 Already Assigned         │
└─────────────────────────────────────────────────────────────┘
```

## Date Controls Design

### Date Input Fields
- **Start Date**: Auto-populates to Monday of current week
- **End Date**: Auto-populates based on schedule type:
  - Helpdesk: Friday (Mon-Fri)
  - Lab: Saturday (Mon-Sat)
- **Styling**: Modern date inputs with Material Design styling

### Action Buttons
1. **Generate Schedule** 
   - Primary blue button
   - Triggers schedule generation API call
   - Shows loading state during generation

2. **Clear Schedule**
   - Secondary red button 
   - Shows confirmation modal before clearing
   - Clears all assignments and schedule data

3. **Save Schedule**
   - Green button for saving current assignments
   - Always visible, enabled when schedule exists
   - Saves staff assignments to database

4. **Download PDF**
   - Purple button for PDF export
   - Downloads current schedule as formatted PDF

```css
/* Button Styling Example */
.schedule-actions {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.3s ease;
}

.btn-danger {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.btn-success {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}
```

## Schedule Calendar Table

### Table Structure
- **Time Column**: Shows time slots (9:00 AM - 5:00 PM for helpdesk, 4-hour blocks for lab)
- **Day Columns**: Monday through Friday/Saturday depending on schedule type
- **Responsive Design**: Horizontal scroll on mobile devices

### Schedule Cell Design
Each schedule cell contains:
1. **Staff Container**: Holds assigned staff members
2. **Staff Slot Indicator**: Shows "Staff: X/3" counter
3. **Add Staff Button**: Triggers staff search modal
4. **Staff Name Elements**: Draggable staff assignments with remove buttons

```jsx
// React Component Example
const ScheduleCell = ({ day, time, shift }) => {
  return (
    <td 
      className="schedule-cell"
      data-day={day}
      data-time={time}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
    >
      <div className="staff-container">
        <div className="staff-slot-indicator">
          Staff: {shift?.assistants?.length || 0}/3
        </div>
        
        {shift?.assistants?.map(assistant => (
          <div 
            key={assistant.id}
            className="staff-name"
            draggable
            onDragStart={handleDragStart}
            data-staff-id={assistant.id}
          >
            {assistant.name}
            <button 
              className="remove-staff"
              onClick={() => removeStaff(assistant.id)}
            >
              ×
            </button>
          </div>
        ))}
        
        {(!shift?.assistants || shift.assistants.length < 3) && (
          <button 
            className="add-staff-btn"
            onClick={() => openStaffModal(day, time)}
          >
            + Add Staff
          </button>
        )}
      </div>
    </td>
  );
};
```

## Drag and Drop Functionality

### Visual Feedback System
The drag and drop system provides comprehensive visual feedback:

1. **Available Cells** (Blue highlight)
   - Cells where staff can be dropped
   - Blue dashed border with light blue background
   - CSS class: `droppable`

2. **Unavailable Cells** (Red highlight)  
   - Cells where staff is not available
   - Red dashed border with light red background
   - Shows prohibition icon (⛔) on hover
   - CSS class: `not-available`

3. **Already Assigned** (Yellow highlight)
   - Cells where staff is already assigned
   - Yellow dashed border with warning message
   - Shows "Already assigned" text with warning icon
   - CSS class: `duplicate-assignment`

4. **Currently Hovered** (Green outline)
   - Cell currently being hovered during drag
   - Green box-shadow outline
   - CSS class: `drag-over`

### Drag and Drop Implementation

```jsx
// Drag and Drop Hooks
const useDragAndDrop = () => {
  const [draggedStaff, setDraggedStaff] = useState(null);
  const [availabilityCache, setAvailabilityCache] = useState({});

  const handleDragStart = (e, staffData) => {
    setDraggedStaff(staffData);
    e.dataTransfer.setData('text/plain', JSON.stringify(staffData));
    e.dataTransfer.effectAllowed = 'move';
    
    // Highlight available cells
    highlightAvailableCells(staffData.id);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    const cell = e.target.closest('.schedule-cell');
    if (cell && draggedStaff) {
      updateCellHighlight(cell, draggedStaff.id);
    }
  };

  const handleDrop = async (e, targetCell) => {
    e.preventDefault();
    
    const staffData = JSON.parse(e.dataTransfer.getData('text/plain'));
    const day = targetCell.dataset.day;
    const time = targetCell.dataset.time;
    
    // Check availability before assignment
    const isAvailable = await checkStaffAvailability(staffData.id, day, time);
    
    if (!isAvailable) {
      showNotification(`${staffData.name} is not available at this time`, 'warning');
      return;
    }
    
    // Assign staff to cell
    assignStaffToCell(staffData, targetCell);
    clearAllHighlights();
  };

  return { handleDragStart, handleDragOver, handleDrop };
};
```

## Staff Search Modal

### Modal Structure
```jsx
const StaffSearchModal = ({ isOpen, onClose, targetCell }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [availableStaff, setAvailableStaff] = useState([]);
  const [loading, setLoading] = useState(false);

  return (
    <div className={`modal ${isOpen ? 'modal-open' : ''}`}>
      <div className="modal-backdrop" onClick={onClose} />
      <div className="modal-content">
        <div className="modal-header">
          <h2>Add Staff for {targetCell?.day} at {targetCell?.time}</h2>
          <p className="modal-subtitle">
            Only showing staff available at this time
          </p>
          <button className="close-modal" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-body">
          <input
            type="text"
            placeholder="Search staff by name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          
          <div className="staff-search-results">
            {loading ? (
              <div className="loading-message">Loading available staff...</div>
            ) : (
              availableStaff
                .filter(staff => 
                  staff.name.toLowerCase().includes(searchTerm.toLowerCase())
                )
                .map(staff => (
                  <div
                    key={staff.id}
                    className="search-result-item"
                    onClick={() => selectStaff(staff)}
                  >
                    {staff.name}
                  </div>
                ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
```

### Modal Styling
```css
.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
  display: none;
}

.modal-open {
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-backdrop {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
  max-width: 500px;
  width: 90%;
  max-height: 70vh;
  overflow: hidden;
  position: relative;
  z-index: 1001;
}

.search-result-item {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #eee;
  cursor: pointer;
  transition: background-color 0.2s;
}

.search-result-item:hover {
  background-color: #f8f9fa;
}
```

## Clear Schedule Confirmation Modal

### Confirmation Dialog
```jsx
const ClearScheduleModal = ({ isOpen, onClose, onConfirm }) => {
  return (
    <div className={`modal ${isOpen ? 'modal-open' : ''}`}>
      <div className="modal-backdrop" onClick={onClose} />
      <div className="modal-content confirmation-modal">
        <div className="modal-header">
          <h2>Confirm Clear Schedule</h2>
        </div>
        
        <div className="modal-body">
          <p>Are you sure you want to clear the entire schedule?</p>
          <p className="warning-text">This action cannot be undone.</p>
        </div>
        
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-danger" onClick={onConfirm}>
            Clear Schedule
          </button>
        </div>
      </div>
    </div>
  );
};
```

## Notification System

### Toast Notifications
```jsx
const NotificationSystem = () => {
  const [notifications, setNotifications] = useState([]);

  const showNotification = (message, type = 'info') => {
    const id = Date.now();
    const notification = { id, message, type };
    
    setNotifications(prev => [...prev, notification]);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 5000);
  };

  return (
    <div className="notification-container">
      {notifications.map(notification => (
        <div
          key={notification.id}
          className={`notification notification-${notification.type}`}
        >
          <span className="notification-icon">
            {notification.type === 'success' && '✓'}
            {notification.type === 'error' && '⚠️'}
            {notification.type === 'warning' && '⚠'}
            {notification.type === 'info' && 'ℹ'}
          </span>
          {notification.message}
        </div>
      ))}
    </div>
  );
};
```

## Color Coding & Legend

### Visual Indicators
- **🟢 Available**: Staff can be assigned (blue highlight during drag)
- **🔴 Unavailable**: Staff cannot be assigned (red highlight during drag)  
- **🟡 Already Assigned**: Staff is already in this time slot (yellow highlight)
- **⚫ Currently Hovered**: Cell being hovered during drag (green outline)

### Legend Component
```jsx
const ScheduleLegend = () => {
  return (
    <div className="schedule-legend">
      <h3>Schedule Legend</h3>
      <div className="legend-items">
        <div className="legend-item">
          <div className="legend-color available"></div>
          <span>Available for assignment</span>
        </div>
        <div className="legend-item">
          <div className="legend-color unavailable"></div>
          <span>Staff not available</span>
        </div>
        <div className="legend-item">
          <div className="legend-color assigned"></div>
          <span>Already assigned</span>
        </div>
        <div className="legend-item">
          <div className="legend-color hover"></div>
          <span>Currently hovering</span>
        </div>
      </div>
    </div>
  );
};
```

## API Integration

### Key API Endpoints
1. **Generate Schedule**: `POST /api/schedule/generate`
2. **Save Schedule**: `POST /api/schedule/save` 
3. **Clear Schedule**: `POST /api/schedule/clear`
4. **Check Availability**: `GET /api/staff/check-availability`
5. **Available Staff**: `GET /api/staff/available`
6. **Download PDF**: `GET /api/schedule/pdf`

### API State Management
```jsx
const useScheduleAPI = () => {
  const [loading, setLoading] = useState(false);
  const [schedule, setSchedule] = useState(null);

  const generateSchedule = async (startDate, endDate) => {
    setLoading(true);
    try {
      const response = await fetch('/api/schedule/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start_date: startDate, end_date: endDate })
      });
      
      const data = await response.json();
      if (data.status === 'success') {
        setSchedule(data.schedule);
        return data;
      }
      throw new Error(data.message);
    } catch (error) {
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const saveSchedule = async (assignments) => {
    setLoading(true);
    try {
      const response = await fetch('/api/schedule/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assignments })
      });
      
      const data = await response.json();
      if (data.status !== 'success') {
        throw new Error(data.message);
      }
      return data;
    } finally {
      setLoading(false);
    }
  };

  return { generateSchedule, saveSchedule, loading, schedule };
};
```

## Responsive Design

### Mobile Adaptations
```css
/* Mobile Schedule Table */
@media (max-width: 768px) {
  .schedule-table-container {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
  
  .schedule-table {
    min-width: 600px;
  }
  
  .schedule-cell {
    min-width: 120px;
    font-size: 0.875rem;
  }
  
  .staff-name {
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
  }
  
  .add-staff-btn {
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
  }
}

/* Touch-friendly drag and drop */
@media (pointer: coarse) {
  .staff-name {
    padding: 0.75rem;
    margin: 0.25rem 0;
  }
  
  .remove-staff {
    width: 24px;
    height: 24px;
  }
}
```

## Performance Optimizations

### Availability Caching
```jsx
const useAvailabilityCache = () => {
  const [cache, setCache] = useState({});

  const getCachedAvailability = (staffId, day, time) => {
    const key = `${staffId}-${day}-${time}`;
    return cache[key];
  };

  const setCachedAvailability = (staffId, day, time, isAvailable) => {
    const key = `${staffId}-${day}-${time}`;
    setCache(prev => ({ ...prev, [key]: isAvailable }));
  };

  const batchCheckAvailability = async (queries) => {
    const response = await fetch('/api/staff/check-availability/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ queries })
    });
    
    const data = await response.json();
    if (data.status === 'success') {
      data.results.forEach(result => {
        setCachedAvailability(result.staff_id, result.day, result.time, result.is_available);
      });
    }
    
    return data.results;
  };

  return { getCachedAvailability, setCachedAvailability, batchCheckAvailability };
};
```

## Implementation Checklist

### Core Features
- [ ] Date range selection with auto-population
- [ ] Schedule table with time slots and days
- [ ] Drag and drop staff assignment
- [ ] Staff search modal with availability filtering
- [ ] Visual feedback for availability states
- [ ] Staff removal functionality
- [ ] Save/load schedule functionality
- [ ] Clear schedule with confirmation
- [ ] PDF download capability

### UI/UX Features  
- [ ] Loading states for API calls
- [ ] Toast notification system
- [ ] Responsive design for mobile
- [ ] Accessibility features (ARIA labels, keyboard navigation)
- [ ] Color-coded legend
- [ ] Hover effects and animations
- [ ] Error handling and user feedback

### Performance Features
- [ ] Availability data caching
- [ ] Batch API requests for availability
- [ ] Optimistic UI updates
- [ ] Debounced search input
- [ ] Virtual scrolling for large schedules
- [ ] Memoized components and calculations

This comprehensive design document provides all the necessary details to recreate the Flask schedule page in Next.js while maintaining the same functionality and user experience.