const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { exec } = require('node:child_process');

const preferredPort = Number(process.env.PORT) || 3000;
const siteRoot = path.join(__dirname, 'Innovision');

const contentTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

const requestHandler = (request, response) => {
  const requestPath = decodeURIComponent(request.url.split('?')[0]);
  const relativePath = requestPath === '/' ? 'landingpage.html' : requestPath.slice(1);
  const filePath = path.resolve(siteRoot, relativePath);

  if (!filePath.startsWith(siteRoot + path.sep)) {
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
    console.log(`Innovision is running at ${url}`);

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