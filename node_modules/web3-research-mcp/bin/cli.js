#!/usr/bin/env node

import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { spawn } from 'child_process';

// Get the directory name of the current module
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const serverPath = join(__dirname, '../dist/server.js');

// Parse any CLI arguments
const args = process.argv.slice(2);

// Check for help command
if (args.includes('--help') || args.includes('-h')) {
  process.exit(0);
}

// Start the server
const server = spawn('node', [serverPath, ...args], { stdio: 'inherit' });

// Handle process termination
process.on('SIGINT', () => {
  server.kill('SIGINT');
});