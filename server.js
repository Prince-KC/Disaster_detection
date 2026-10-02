import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { exec } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const preferredPort = Number(process.env.PORT) || 3000;
const siteRoot = path.join(__dirname, 'index');
const imagesRoot = path.join(__dirname, 'images');
const apiHost = process.env.API_HOST || '127.0.0.1';
const apiPort = Number(process.env.API_PORT) || 8000;

const contentTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

const requestHandler = (request, response) => {
  const url = new URL(request.url, 'http://localhost');
  if (url.pathname === '/api' || url.pathname.startsWith('/api/')) {
    const proxyRequest = http.request({
      hostname: apiHost,
      port: apiPort,
      path: `${url.pathname}${url.search}`,
      method: request.method,
      headers: { ...request.headers, host: `${apiHost}:${apiPort}` }
    }, (proxyResponse) => {
      response.writeHead(proxyResponse.statusCode || 502, proxyResponse.headers);
      proxyResponse.pipe(response);
    });

    proxyRequest.on('error', (error) => {
      console.error(`Backend API proxy failed: ${error.message}`);
      if (!response.headersSent) {
        response.writeHead(502, { 'Content-Type': 'text/plain; charset=utf-8' });
      }
      response.end('Backend API unavailable');
    });
    request.pipe(proxyRequest);
    return;
  }

  let requestPath;
  try {
    requestPath = decodeURIComponent(url.pathname);
  } catch {
    response.writeHead(400, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('Invalid path');
    return;
  }

  const isImage = requestPath.startsWith('/images/');
  const root = isImage ? imagesRoot : siteRoot;
  const relativePath = isImage
    ? requestPath.slice('/images/'.length)
    : requestPath === '/' ? 'landing-page.html' : requestPath.slice(1);
  const filePath = path.resolve(root, relativePath);

  if (filePath !== root && !filePath.startsWith(root + path.sep)) {
    response.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('Forbidden');
    return;
  }

  fs.stat(filePath, (error, stats) => {
    if (error || !stats.isFile()) {
      response.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      response.end('Not found');
      return;
    }

    response.writeHead(200, {
      'Content-Type': contentTypes[path.extname(filePath).toLowerCase()] || 'application/octet-stream'
    });
    fs.createReadStream(filePath).pipe(response);
  });
};

function startServer(port) {
  const server = http.createServer(requestHandler);

  server.once('error', (error) => {
    if (error.code === 'EADDRINUSE' && !process.env.PORT) {
      console.log(`Port ${port} is busy; trying port ${port + 1}.`);
      startServer(port + 1);
      return;
    }

    throw error;
  });

  server.listen(port, () => {
    const url = `http://localhost:${port}`;
    console.log(`Disaster frontend is running at ${url}`);

    if (process.platform === 'win32') {
      exec(`start "" "${url}"`);
    } else if (process.platform === 'darwin') {
      exec(`open "${url}"`);
    } else {
      exec(`xdg-open "${url}"`);
    }
  });
}

startServer(preferredPort);