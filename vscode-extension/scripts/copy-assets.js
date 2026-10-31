const fs = require('node:fs');
const path = require('node:path');

const extensionRoot = path.resolve(__dirname, '..');
const repositoryRoot = path.resolve(extensionRoot, '..');

function replaceDirectory(source, target, filter = () => true) {
  fs.rmSync(target, { recursive: true, force: true });
  fs.mkdirSync(target, { recursive: true });

  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    if (!filter(entry.name, entry)) continue;
    const sourcePath = path.join(source, entry.name);
    const targetPath = path.join(target, entry.name);
    if (entry.isDirectory()) {
      replaceDirectory(sourcePath, targetPath);
    } else if (entry.isFile()) {
      fs.copyFileSync(sourcePath, targetPath);
    }
  }
}

replaceDirectory(path.join(repositoryRoot, 'webview'), path.join(extensionRoot, 'media', 'webview'));
replaceDirectory(
  path.join(repositoryRoot, 'src'),
  path.join(extensionRoot, 'python'),
  (name, entry) => entry.isFile() && name.endsWith('.py')
);