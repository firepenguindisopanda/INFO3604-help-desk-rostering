(function (window) {
  'use strict';

  if (typeof window.getCsrfToken !== 'function') {
    window.getCsrfToken = function getCsrfToken() {
      const value = `; ${document.cookie}`;
      const parts = value.split('; csrf_access_token=');
      if (parts.length === 2) {
        return parts.pop().split(';').shift();
      }
      return null;
    };
  }

  if (typeof window.buildAuthHeaders !== 'function') {
    window.buildAuthHeaders = function buildAuthHeaders(extraHeaders) {
      const headers = Object.assign({
        'Content-Type': 'application/json'
      }, extraHeaders || {});

      try {
        const csrfToken = typeof window.getCsrfToken === 'function' ? window.getCsrfToken() : null;
        if (csrfToken) {
          headers['X-CSRF-TOKEN'] = csrfToken;
        }
      } catch (error) {
        console.warn('Unable to read CSRF token for auth headers', error);
      }

      return headers;
    };
  }
})(window);
