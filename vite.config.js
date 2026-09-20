import { defineConfig } from 'vite';
import { resolve } from 'path';
import { createReadStream, existsSync, readdirSync, readFileSync } from 'fs';

const imagesDirectory = resolve(__dirname, 'images');
const imageContentTypes = {
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.webp': 'image/webp',
  '.gif': 'image/gif'
};

function disasterImagesPlugin() {
  const serveImages = (request, response, next) => {
    const imageName = decodeURIComponent(request.url.split('?')[0]).replace(/^\/+/, '');
    const imagePath = resolve(imagesDirectory, imageName);

    if (!imagePath.startsWith(imagesDirectory) || !existsSync(imagePath)) {
      next();
      return;
    }

    response.setHeader('Content-Type', imageContentTypes[resolve(imagePath).slice(resolve(imagePath).lastIndexOf('.')).toLowerCase()] || 'application/octet-stream');
    createReadStream(imagePath).pipe(response);
  };

  return {
    name: 'disaster-images',
    configureServer(server) {
      server.middlewares.use('/images', serveImages);
    },
    configurePreviewServer(server) {
      server.middlewares.use('/images', serveImages);
    },
    generateBundle() {
      for (const imageName of readdirSync(imagesDirectory)) {
        const imagePath = resolve(imagesDirectory, imageName);
        this.emitFile({ type: 'asset', fileName: `images/${imageName}`, source: readFileSync(imagePath) });
      }
    }
  };
}

export default defineConfig({
  root: 'index',
  plugins: [disasterImagesPlugin()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    strictPort: false,
    open: '/landing-page.html',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/video_feed': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
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
        'landing-page': resolve(__dirname, 'index/landing-page.html'),
        'login-page': resolve(__dirname, 'index/login-page.html'),
        'signup-role-selection': resolve(__dirname, 'index/signup-role-selection.html'),
        'response-dashboard': resolve(__dirname, 'index/response-dashboard.html'),
        'resource-mapping': resolve(__dirname, 'index/resource-mapping.html'),
        'available-resources': resolve(__dirname, 'index/available-resources.html'),
        'live-cameras': resolve(__dirname, 'index/live-cameras.html'),
        'incident-alerts': resolve(__dirname, 'index/incident-alerts.html'),
        'incident-detail': resolve(__dirname, 'index/incident-detail.html'),
        'live-map': resolve(__dirname, 'index/live-map.html'),
        'incident-history': resolve(__dirname, 'index/incident-history.html'),
        'my-reports-page': resolve(__dirname, 'index/my-reports-page.html'),
        'profile-page': resolve(__dirname, 'index/profile-page.html'),
        'notifications-page': resolve(__dirname, 'index/notifications-page.html'),
        'emergency-contacts-page': resolve(__dirname, 'index/emergency-contacts-page.html'),
        'authority-profile': resolve(__dirname, 'index/authority-profile.html'),
        'authority-settings': resolve(__dirname, 'index/authority-settings.html'),
        'authority-signup-page': resolve(__dirname, 'index/authority-signup-page.html'),
        'citizen-signup-page': resolve(__dirname, 'index/citizen-signup-page.html'),
        'incident-report-page': resolve(__dirname, 'index/incident-report-page.html'),
        'report-detail-page': resolve(__dirname, 'index/report-detail-page.html'),
        'home-landing-page': resolve(__dirname, 'index/home-landing-page.html')
      }
    }
  }
});

