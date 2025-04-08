document.addEventListener('DOMContentLoaded', function() {
  // Get the navbar element
  const navbar = document.querySelector('.nav-container');
  if (!navbar) return;
  
  // Calculate the height of the navbar
  const navbarHeight = navbar.offsetHeight;
  
  // Apply padding to the content area to prevent content from being hidden behind navbar
  const contentArea = document.querySelector('.content');
  if (contentArea) {
    contentArea.style.paddingTop = navbarHeight + 'px';
  }
  
  // Add scroll event listener to add/remove box shadow based on scroll position
  window.addEventListener('scroll', function() {
    if (window.scrollY > 0) {
      navbar.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';
    } else {
      navbar.style.boxShadow = '0 1px 3px rgba(0,0,0,0.08)';
    }
  });
});