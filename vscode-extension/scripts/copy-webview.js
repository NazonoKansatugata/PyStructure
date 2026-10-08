const fs = require('node:fs');
const path = require('node:path');

const source = path.resolve(__dirname, '..', '..', 'webview');
const target = path.resolve(__dirname, '..', 'media', 'webview');

fs.rmSync(target, { recursive: true, force: true });
fs.cpSync(source, target, { recursive: true });
