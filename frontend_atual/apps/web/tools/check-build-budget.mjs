import { readdir, stat } from 'node:fs/promises';
import path from 'node:path';

const assetDirectory = path.resolve('dist/assets');
const maxBytes = Number.parseInt(process.env.BUNDLE_MAX_ASSET_BYTES || '327680', 10);

if (!Number.isFinite(maxBytes) || maxBytes < 1) {
  throw new Error('BUNDLE_MAX_ASSET_BYTES must be a positive integer.');
}

const files = await readdir(assetDirectory);
const javascriptAssets = await Promise.all(
  files
    .filter((file) => file.endsWith('.js'))
    .map(async (file) => ({ file, bytes: (await stat(path.join(assetDirectory, file))).size })),
);
const oversized = javascriptAssets.filter((asset) => asset.bytes > maxBytes);

if (oversized.length) {
  const details = oversized
    .map((asset) => `${asset.file}: ${asset.bytes} bytes`)
    .join(', ');
  throw new Error(`JavaScript bundle budget exceeded (${maxBytes} bytes): ${details}`);
}

console.log(`Bundle budget OK: ${javascriptAssets.length} JavaScript chunks at <= ${maxBytes} bytes.`);
