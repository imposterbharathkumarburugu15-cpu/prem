import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const distDir = path.resolve(__dirname, 'dist');
const webConsoleDir = path.resolve(__dirname, '..', 'web_console');
const targetTemplate = path.resolve(webConsoleDir, 'templates', 'index.html');
const targetStaticAssets = path.resolve(webConsoleDir, 'static', 'assets');

// Ensure directories exist
fs.mkdirSync(path.dirname(targetTemplate), { recursive: true });
fs.mkdirSync(targetStaticAssets, { recursive: true });

// Copy index.html
const srcHtml = path.resolve(distDir, 'index.html');
if (fs.existsSync(srcHtml)) {
  fs.copyFileSync(srcHtml, targetTemplate);
  console.log(`[sync] Copied ${srcHtml} -> ${targetTemplate}`);
}

// Copy assets
const srcAssets = path.resolve(distDir, 'assets');
if (fs.existsSync(srcAssets)) {
  const files = fs.readdirSync(srcAssets);
  for (const f of files) {
    const from = path.resolve(srcAssets, f);
    const to = path.resolve(targetStaticAssets, f);
    fs.copyFileSync(from, to);
    console.log(`[sync] Copied asset ${f} -> ${to}`);
  }
}
console.log('[sync] Distribution successfully synchronized to web_console.');
