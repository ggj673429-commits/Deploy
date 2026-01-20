/**
 * AuthContext - SINGLE SOURCE OF TRUTH FOR AUTH STATE
 * 
 * Rules:
 * - Uses ONLY localStorage["token"] for token storage
 * - Uses ONLY src/api/http.js for API calls
 * - Exposes: login(), logout(), isAuthenticated, user, role, serverUnavailable
 * - On network failure during validation, sets serverUnavailable flag (does NOT logout)
 * - On explicit 401 invalid/expired, clears token
 * - Handles both validate-token response schemas for compatibility
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import http, { getErrorMessage, isServerUnavailable, formatLockoutTime } from '../api/http';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [serverUnavailable, setServerUnavailable] = useState(false);
  
  // Ref to prevent race conditions during auth initialization
  const isInitializing = React.useRef(false);

  // Get token from localStorage
  const getToken = useCallback(() => localStorage.getItem('token'), []);

  /**
   * Parse user from validate-token response
   * Handles both response schemas:
   * 1) { valid: true, user: { id, username, role } }
   * 2) { valid: true, user_id, username, role }
   */
  const parseValidateTokenResponse = (data) => {
    if (!data.valid) return null;
    
    // Schema 1: { valid: true, user: {...} }
    if (data.user && typeof data.user === 'object') {
      return {
        user_id: data.user.user_id || data.user.id,
        username: data.user.username,
        display_name: data.user.display_name || data.user.username,
        role: data.user.role || 'user',
        referral_code: data.user.referral_code,
      };
    }
    
    // Schema 2: { valid: true, user_id, username, role }
    if (data.user_id && data.username) {
      return {
        user_id: data.user_id,
        username: data.username,
        display_name: data.display_name || data.username,
        role: data.role || 'user',
        referral_code: data.referral_code,
      };
    }
    
    return null;
  };

  // Validate token on app load
  useEffect(() => {
    const initAuth = async () => {
      // Prevent multiple simultaneous initializations
      if (isInitializing.current) {
        return;
      }
      isInitializing.current = true;
      
      const storedToken = getToken();
      
      if (!storedToken) {
        setLoading(false);
        isInitializing.current = false;
        return;
      }

      try {
        const response = await http.post('/auth/validate-token');
        
        const userData = parseValidateTokenResponse(response.data);
        if (userData) {
          setUser(userData);
          setServerUnavailable(false);
          // Update stored user data
          localStorage.setItem('user', JSON.stringify(userData));
        } else {
          // Invalid response format - clear token
          console.warn('Invalid validate-token response format', response.data);
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          setUser(null);
        }
      } catch (error) {
        if (isServerUnavailable(error)) {
          // Server is down - keep token, set flag
          console.warn('Server unavailable during token validation');
          setServerUnavailable(true);
          // Try to restore user from localStorage if available
          const storedUser = localStorage.getItem('user');
          if (storedUser) {
            try {
              setUser(JSON.parse(storedUser));
            } catch (e) {
              // Invalid JSON, ignore
            }
          }
        } else if (error.isAuthError && error.status === 401) {
          // Explicit 401 invalid/expired token - clear it
          console.log('Token invalid or expired, logging out');
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          setUser(null);
        } else {
          // Other error (4xx, transient failures) - DON'T clear token
          // Keep user logged in, they can retry. Only explicit 401 should force logout.
          console.warn('Token validation failed (non-auth error), keeping session:', error.message);
          // Try to restore user from localStorage
          const storedUser = localStorage.getItem('user');
          if (storedUser) {
            try {
              setUser(JSON.parse(storedUser));
            } catch (e) {
              // Invalid JSON - can't restore, but don't clear token
              console.warn('Could not restore user from localStorage');
            }
          }
        }
      } finally {
        setLoading(false);
        isInitializing.current = false;
      }
    };

    initAuth();
  }, [getToken]);

  /**
   * Login with username and password
   */
  const login = async (username, password) => {
    try {
      const response = await http.post('/auth/login', { username, password });
      
      if (!response.data.success) {
        throw new Error(response.data.message || 'Login failed');
      }
      
      const { access_token, user: userData } = response.data;
      
      // Store token FIRST, then set user state
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(userData));
      
      // Update state
      setUser(userData);
      setServerUnavailable(false);
      
      return { success: true, user: userData };
    } catch (error) {
      const message = getErrorMessage(error, 'Login failed');
      const isNetwork = isServerUnavailable(error);
      
      if (isNetwork) {
        setServerUnavailable(true);
      }
      
      // Format lockout message if present
      let finalMessage = message;
      if (error.lockout_remaining) {
        const timeStr = formatLockoutTime(error.lockout_remaining);
        finalMessage = `Account temporarily locked. Try again in ${timeStr}.`;
      }
      
      return { 
        success: false, 
        message: finalMessage,
        isNetworkError: isNetwork,
        lockout_remaining: error.lockout_remaining,
      };
    }
  };

  /**
   * Register new user
   * Returns:
   * - { success: true, user } on full success (signup + auto-login)
   * - { success: true, mode: 'signup_only', username } when signup succeeded but login failed
   * - { success: false, message } on signup failure
   */
  const register = async (username, password, displayName, referralCode) => {
    // Step 1: Attempt signup
    let signupSucceeded = false;
    try {
      const response = await http.post('/auth/signup', {
        username,
        password,
        display_name: displayName,
        referred_by_code: referralCode || null,
      });
      
      if (!response.data.success) {
        // Signup failed - return the backend error
        return { 
          success: false, 
          message: response.data.message || 'Registration failed',
        };
      }
      
      signupSucceeded = true;
    } catch (error) {
      // Signup failed - preserve backend message
      const message = getErrorMessage(error, 'Registration failed');
      return { 
        success: false, 
        message,
        isNetworkError: isServerUnavailable(error),
      };
    }
    
    // Step 2: Signup succeeded, attempt auto-login
    try {
      const loginResult = await login(username, password);
      
      if (loginResult.success) {
        // Full success - signup + login worked
        return loginResult;
      }
      
      // Login failed after successful signup
      // Return success with mode='signup_only' so UI can handle gracefully
      return {
        success: true,
        mode: 'signup_only',
        username,
        message: 'Account created successfully. Please sign in.',
      };
    } catch (error) {
      // Login threw an error after successful signup
      // Still a "success" from signup perspective
      return {
        success: true,
        mode: 'signup_only',
        username,
        message: 'Account created successfully. Please sign in.',
      };
    }
  };

  /**
   * Validate a portal magic-link token
   * Used by /p/:token route
   */
  const validatePortalToken = async (token) => {
    try {
      const response = await http.post('/auth/validate-token', {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      const userData = parseValidateTokenResponse(response.data);
      if (userData) {
        // Store token and user
        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(userData));
        
        setUser(userData);
        setServerUnavailable(false);
        
        return { success: true, user: userData };
      }
      
      return { success: false, message: 'Invalid or expired token' };
    } catch (error) {
      const message = getErrorMessage(error, 'Token validation failed');
      const isNetwork = isServerUnavailable(error);
      
      if (isNetwork) {
        setServerUnavailable(true);
      }
      
      return { 
        success: false, 
        message,
        isNetworkError: isNetwork,
      };
    }
  };

  /**
   * Logout - clear all auth state
   */
  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
  }, []);

  /**
   * Clear server unavailable flag (for retry)
   */
  const clearServerError = useCallback(() => {
    setServerUnavailable(false);
  }, []);

  const value = {
    // State
    user,
    loading,
    serverUnavailable,
    
    // Computed
    isAuthenticated: !!user,
    role: user?.role || null,
    isAdmin: user?.role === 'admin',
    isClient: user?.role === 'client' || (user && user.role !== 'admin'),
    
    // Actions
    login,
    register,
    logout,
    validatePortalToken,
    clearServerError,
    getToken,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
