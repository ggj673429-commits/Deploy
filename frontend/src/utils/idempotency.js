/**
 * Idempotency Helper
 * 
 * Generates unique idempotency keys for API requests to prevent duplicate submissions.
 * Uses crypto.randomUUID() with fallback for older browsers.
 */

/**
 * Generate a unique idempotency key
 * @returns {string} UUID v4 string
 */
export const generateIdempotencyKey = () => {
  // Use crypto.randomUUID if available (modern browsers)
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  
  // Fallback for older browsers
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

/**
 * Create HTTP config with idempotency header
 * @param {string} [key] - Optional pre-generated key, generates new one if not provided
 * @returns {Object} Axios request config with Idempotency-Key header
 */
export const withIdempotency = (key) => ({
  headers: {
    'Idempotency-Key': key || generateIdempotencyKey(),
  },
});

export default {
  generateIdempotencyKey,
  withIdempotency,
};
