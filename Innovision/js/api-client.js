/**
 * api-client.js - KhetRakshak Unified API & Supabase Realtime Client
 * Connects frontend HTML pages to the FastAPI backend and Supabase Realtime DB.
 */

const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000/api';
const SUPABASE_URL = 'https://desbzybcnxhawjltxrjm.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRlc2J6eWJjbnhoYXdqbHR4cmptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU1MTI3MzgsImV4cCI6MjEwMTA4ODczOH0.EKxLzHCuC0h7Jsfge4B6LVNfcwvB632wa5it8bWoSMs';

// Initialize Supabase Client if library is available
let supabaseClient = null;
if (window.supabase) {
  try {
    supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    console.log('[KhetRakshak Client] Supabase client initialized.');
  } catch (err) {
    console.warn('[KhetRakshak Client] Supabase init warning:', err);
  }
}

/**
 * Fetch API helper with fallback error handling.
 */
async function fetchAPI(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });
    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.warn(`[KhetRakshak API] ${endpoint} request failed:`, error.message);
    return null;
  }
}

// -----------------------------------------------------------------------------
// API Service Methods
// -----------------------------------------------------------------------------
const KhetRakshakAPI = {
  // System Health
  async checkHealth() {
    return (await fetchAPI('/health')) || { status: 'offline' };
  },

  // Dashboard Summary Metrics
  async getDashboardSummary() {
    return await fetchAPI('/dashboard/summary');
  },

  // Detection History
  async getDetections(limit = 50) {
    const res = await fetchAPI(`/detections?limit=${limit}`);
    return Array.isArray(res) ? res : [];
  },

  // Speaker Status & Control
  async getSpeakers() {
    return (await fetchAPI('/speakers')) || [];
  },

  async controlSpeaker(action) {
    return await fetchAPI(`/speakers/control?action=${action}`, { method: 'POST' });
  },

  // Warning Light Status & Control
  async controlLight(action) {
    return await fetchAPI(`/lights/control?action=${action}`, { method: 'POST' });
  },

  // Notifications Log
  async getNotifications(limit = 50) {
    const res = await fetchAPI(`/notifications?limit=${limit}`);
    return Array.isArray(res) ? res : [];
  },

  // Analytics Metrics
  async getAnalytics() {
    return (await fetchAPI('/analytics')) || { total_detections: 0, daily_records: [] };
  },

  // Subscribe to Supabase Realtime Detections
  subscribeToDetections(onNewDetection) {
    if (!supabaseClient) return null;

    try {
      const channel = supabaseClient
        .channel('public:detections')
        .on(
          'postgres_changes',
          { event: 'INSERT', schema: 'public', table: 'detections' },
          (payload) => {
            console.log('[KhetRakshak Realtime] New detection event:', payload.new);
            if (typeof onNewDetection === 'function') {
              onNewDetection(payload.new);
            }
          }
        )
        .subscribe();

      return channel;
    } catch (e) {
      console.warn('[KhetRakshak Realtime] Subscription error:', e);
      return null;
    }
  },
};

// Global export
window.KhetRakshakAPI = KhetRakshakAPI;
