import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: 'Innovision',   // Serve from the Innovision/ subfolder
  // NOTE: No publicDir override — assets/ stays at /assets/ path as authored
  server: {
    port: 3000,
    host: '0.0.0.0',
    strictPort: false,
    open: '/landingpage.html',
    proxy: {
      // Forward all /api/* calls to Express backend during dev
      '/api': {
        target: 'http://localhost:3002',
        changeOrigin: true,
      },
      // Forward all /flask/* calls to the Flask YOLO backend
      '/flask': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/flask/, ''),
      }
    }
  },
  preview: {
    port: 4173,
    host: '0.0.0.0',
  },
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        landingpage:            resolve(__dirname, 'Innovision/landingpage.html'),
        login:                  resolve(__dirname, 'Innovision/login.html'),
        registration:           resolve(__dirname, 'Innovision/registration.html'),
        dashboard:              resolve(__dirname, 'Innovision/dashboard.html'),
        'live-monitoring':      resolve(__dirname, 'Innovision/live-monitoring.html'),
        'detection-history':    resolve(__dirname, 'Innovision/detection-history.html'),
        'speaker-status':       resolve(__dirname, 'Innovision/speaker-status.html'),
        'warning-light-status': resolve(__dirname, 'Innovision/warning-light-status.html'),
        notifications:          resolve(__dirname, 'Innovision/notifications.html'),
        analytics:              resolve(__dirname, 'Innovision/analytics.html'),
        settings:               resolve(__dirname, 'Innovision/settings.html'),
        profile:                resolve(__dirname, 'Innovision/profile.html'),
        contact:                resolve(__dirname, 'Innovision/contact.html'),
      }
    }
  }
});

