/**
 * Session Cache Utility
 * Manages form data persistence across tab navigation
 */

class SessionCache {
  constructor() {
    this.cacheKey = 'ai_content_suite_session';
    this.initCache();
  }

  initCache() {
    // Initialize cache from sessionStorage if exists
    const existingCache = sessionStorage.getItem(this.cacheKey);
    if (!existingCache) {
      sessionStorage.setItem(this.cacheKey, JSON.stringify({}));
    }
  }

  /**
   * Get cached data for a specific component
   * @param {string} componentName - Name of the component
   * @returns {object} Cached data or empty object
   */
  get(componentName) {
    try {
      const cache = JSON.parse(sessionStorage.getItem(this.cacheKey) || '{}');
      return cache[componentName] || {};
    } catch (error) {
      console.error('Error reading cache:', error);
      return {};
    }
  }

  /**
   * Set cached data for a specific component
   * @param {string} componentName - Name of the component
   * @param {object} data - Data to cache
   */
  set(componentName, data) {
    try {
      const cache = JSON.parse(sessionStorage.getItem(this.cacheKey) || '{}');
      cache[componentName] = {
        ...cache[componentName],
        ...data,
        timestamp: Date.now()
      };
      sessionStorage.setItem(this.cacheKey, JSON.stringify(cache));
    } catch (error) {
      console.error('Error setting cache:', error);
    }
  }

  /**
   * Update a specific field in the cache
   * @param {string} componentName - Name of the component
   * @param {string} fieldName - Name of the field
   * @param {any} value - Value to set
   */
  updateField(componentName, fieldName, value) {
    try {
      const cache = JSON.parse(sessionStorage.getItem(this.cacheKey) || '{}');
      if (!cache[componentName]) {
        cache[componentName] = {};
      }
      cache[componentName][fieldName] = value;
      cache[componentName].timestamp = Date.now();
      sessionStorage.setItem(this.cacheKey, JSON.stringify(cache));
    } catch (error) {
      console.error('Error updating cache field:', error);
    }
  }

  /**
   * Clear cache for a specific component
   * @param {string} componentName - Name of the component
   */
  clear(componentName) {
    try {
      const cache = JSON.parse(sessionStorage.getItem(this.cacheKey) || '{}');
      delete cache[componentName];
      sessionStorage.setItem(this.cacheKey, JSON.stringify(cache));
    } catch (error) {
      console.error('Error clearing cache:', error);
    }
  }

  /**
   * Clear all cached data
   */
  clearAll() {
    try {
      sessionStorage.setItem(this.cacheKey, JSON.stringify({}));
    } catch (error) {
      console.error('Error clearing all cache:', error);
    }
  }

  /**
   * Check if cache exists for a component
   * @param {string} componentName - Name of the component
   * @returns {boolean} Whether cache exists
   */
  has(componentName) {
    try {
      const cache = JSON.parse(sessionStorage.getItem(this.cacheKey) || '{}');
      return !!cache[componentName] && Object.keys(cache[componentName]).length > 0;
    } catch (error) {
      console.error('Error checking cache:', error);
      return false;
    }
  }

  /**
   * Get cache age in milliseconds
   * @param {string} componentName - Name of the component
   * @returns {number} Age in milliseconds or -1 if not found
   */
  getAge(componentName) {
    try {
      const cache = JSON.parse(sessionStorage.getItem(this.cacheKey) || '{}');
      if (cache[componentName] && cache[componentName].timestamp) {
        return Date.now() - cache[componentName].timestamp;
      }
      return -1;
    } catch (error) {
      console.error('Error getting cache age:', error);
      return -1;
    }
  }
}

// Create singleton instance
const sessionCache = new SessionCache();

export default sessionCache;