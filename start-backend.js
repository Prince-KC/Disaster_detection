import { spawn, spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = path.dirname(fileURLToPath(import.meta.url));
const workspaceRoot = path.dirname(projectRoot);
const pythonIn = environment => path.join(
  environment,
  process.platform === 'win32' ? 'Scripts' : 'bin',
  process.platform === 'win32' ? 'python.exe' : 'python'
);
const candidates = [
  process.env.PYTHON,
  process.env.VIRTUAL_ENV ? pythonIn(process.env.VIRTUAL_ENV) : null,
  pythonIn(path.join(workspaceRoot, '.venv-1')),
  pythonIn(path.join(projectRoot, '.venv-1')),
  pythonIn(path.join(workspaceRoot, '.venv')),
  pythonIn(path.join(projectRoot, '.venv')),
  process.platform === 'win32' ? 'python' : 'python3',
].filter(Boolean);

const backendPython = candidates.find(candidate => {
  const result = spawnSync(candidate, ['-c', 'import cv2, fastapi, uvicorn, ultralytics, supabase'], {
    cwd: projectRoot,
    stdio: 'ignore',
  });
  return !result.error && result.status === 0;
});

if (!backendPython) {
  console.error('No Python environment with the backend and detection dependencies was found.');
  console.error('Install backend/requirements.txt in a project virtual environment.');
  process.exit(1);
}

console.log(`Starting detection backend with ${backendPython}`);
const backend = spawn(backendPython, ['backend/main.py'], {
  cwd: projectRoot,
  stdio: 'inherit',
});

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => backend.kill(signal));
}

backend.on('error', error => {
  console.error(`Could not start detection backend: ${error.message}`);
  process.exitCode = 1;
});
backend.on('exit', code => {
  process.exitCode = code ?? 1;
});