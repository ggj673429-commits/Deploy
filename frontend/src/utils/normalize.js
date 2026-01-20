/**
 * Normalization Utilities
 * 
 * Handles schema/casing/numeric-format inconsistencies across API responses.
 * Prevents crashes from:
 * - .toFixed() on strings
 * - status casing mismatches (PENDING_REVIEW vs pending_review)
 * - inconsistent ID fields (order_id vs transaction_id vs id)
 * - ledger type detection (type vs transaction_type, CREDIT/DEBIT vs credit/debit)
 */

/**
 * Convert any value to a finite number
 * @param {*} value - Value to convert (string, number, null, undefined)
 * @param {number} fallback - Fallback value if conversion fails (default: 0)
 * @returns {number} - Finite number
 */
export const toNumber = (value, fallback = 0) => {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }
  const num = typeof value === 'number' ? value : parseFloat(value);
  return Number.isFinite(num) ? num : fallback;
};

/**
 * Format value as money string (2 decimal places)
 * @param {*} value - Value to format
 * @param {number} fallback - Fallback if conversion fails (default: 0)
 * @returns {string} - Formatted string like "0.00"
 */
export const toMoney = (value, fallback = 0) => {
  return toNumber(value, fallback).toFixed(2);
};

/**
 * Normalize status to lowercase for consistent comparisons
 * @param {*} value - Status string (PENDING_REVIEW, pending_review, etc.)
 * @returns {string} - Lowercase status or empty string
 */
export const normStatus = (value) => {
  if (!value || typeof value !== 'string') return '';
  return value.toLowerCase();
};

/**
 * Get entity ID from object with various ID field names
 * Priority: order_id > transaction_id > id > request_id > game_account_id > ledger_id
 * @param {Object} obj - Object that may contain various ID fields
 * @returns {string|number|undefined} - The ID value or undefined
 */
export const getEntityId = (obj) => {
  if (!obj || typeof obj !== 'object') return undefined;
  return obj.order_id || obj.transaction_id || obj.id || obj.request_id || obj.game_account_id || obj.ledger_id;
};

/**
 * Parse date value safely
 * @param {*} value - Date string, Date object, or timestamp
 * @returns {Date|null} - Valid Date or null
 */
export const safeDate = (value) => {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  return isNaN(date.getTime()) ? null : date;
};

/**
 * Determine if a transaction/ledger entry is incoming (credit/deposit)
 * Handles various API response formats
 * @param {Object} entry - Transaction or ledger entry
 * @returns {boolean} - True if incoming/credit
 */
export const isIncoming = (entry) => {
  if (!entry) return false;
  
  // Check explicit type field (handles CREDIT/credit/DEBIT/debit)
  const type = normStatus(entry.type || entry.transaction_type);
  if (type === 'credit' || type === 'in') return true;
  if (type === 'debit' || type === 'out') return false;
  
  // Check order_type for transactions
  const orderType = normStatus(entry.order_type || '');
  if (orderType.includes('load') || orderType.includes('deposit') || orderType.includes('credit')) {
    return true;
  }
  if (orderType.includes('withdraw') || orderType.includes('redeem') || orderType.includes('debit')) {
    return false;
  }
  
  // Default to checking if amount is positive
  return toNumber(entry.amount) >= 0;
};

/**
 * Get game display name with fallbacks
 * @param {Object} entry - Entry with possible game fields
 * @returns {string} - Game name or empty string
 */
export const getGameName = (entry) => {
  if (!entry) return '';
  return entry.game_name || entry.game || entry.game_display_name || '';
};

/**
 * Check if status indicates completion/success
 * @param {string} status - Status value
 * @returns {boolean}
 */
export const isCompletedStatus = (status) => {
  const s = normStatus(status);
  return ['approved', 'completed', 'credited', 'approved_executed', 'success'].includes(s);
};

/**
 * Check if status indicates pending state
 * @param {string} status - Status value
 * @returns {boolean}
 */
export const isPendingStatus = (status) => {
  const s = normStatus(status);
  return ['pending', 'pending_approval', 'pending_review', 'initiated', 'awaiting_payment_proof', 'processing'].includes(s);
};

/**
 * Check if status indicates failure/rejection
 * @param {string} status - Status value
 * @returns {boolean}
 */
export const isFailedStatus = (status) => {
  const s = normStatus(status);
  return ['failed', 'rejected', 'cancelled', 'declined', 'error'].includes(s);
};

/**
 * Get status color classes based on normalized status
 * @param {string} status - Status value
 * @returns {string} - Tailwind classes for text and background
 */
export const getStatusColorClass = (status) => {
  if (isCompletedStatus(status)) {
    return 'text-emerald-400 bg-emerald-500/10';
  }
  if (isPendingStatus(status)) {
    return 'text-amber-400 bg-amber-500/10';
  }
  if (isFailedStatus(status)) {
    return 'text-red-400 bg-red-500/10';
  }
  return 'text-gray-400 bg-gray-500/10';
};

export default {
  toNumber,
  toMoney,
  normStatus,
  getEntityId,
  safeDate,
  isIncoming,
  getGameName,
  isCompletedStatus,
  isPendingStatus,
  isFailedStatus,
  getStatusColorClass,
};
