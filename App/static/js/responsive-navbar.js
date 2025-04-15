/**
 * Responsive Navbar JavaScript
 * Path: App/static/js/responsive-navbar.js
 */

document.addEventListener('DOMContentLoaded', function() {
  // Create mobile menu toggle button if it doesn't exist
  if (!document.querySelector('.mobile-menu-toggle')) {
    const navContainer = document.querySelector('.nav-container');
    if (navContainer) {
      // Create hamburger icon
      const mobileMenuToggle = document.createElement('div');
      mobileMenuToggle.className = 'mobile-menu-toggle';
      mobileMenuToggle.innerHTML = '<span></span><span></span><span></span>';
      
      // Insert toggle before the first child of nav container
      navContainer.insertBefore(mobileMenuToggle, navContainer.firstChild);
      
      // Create overlay element
      const menuOverlay = document.createElement('div');
      menuOverlay.className = 'menu-overlay';
      document.body.appendChild(menuOverlay);
    }
  }
  
  // Get elements
  const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
  const navLinks = document.querySelector('.nav-links');
  const menuOverlay = document.querySelector('.menu-overlay');
  
  if (mobileMenuToggle && navLinks && menuOverlay) {
    // Toggle menu function
    function toggleMenu() {
      mobileMenuToggle.classList.toggle('open');
      navLinks.classList.toggle('open');
      menuOverlay.classList.toggle('open');
      
      // Prevent body scrolling when menu is open
      if (navLinks.classList.contains('open')) {
        document.body.style.overflow = 'hidden';
      } else {
        document.body.style.overflow = '';
      }
    }
    
    // Event listeners
    mobileMenuToggle.addEventListener('click', toggleMenu);
    menuOverlay.addEventListener('click', toggleMenu);
    
    // Close menu when a link is clicked
    const navLinkElements = document.querySelectorAll('.nav-links .nav-link');
    navLinkElements.forEach(link => {
      link.addEventListener('click', function() {
        if (navLinks.classList.contains('open')) {
          toggleMenu();
        }
      });
    });
    
    // Close menu when window is resized to desktop size
    window.addEventListener('resize', function() {
      if (window.innerWidth > 768 && navLinks.classList.contains('open')) {
        toggleMenu();
      }
    });
  }
});