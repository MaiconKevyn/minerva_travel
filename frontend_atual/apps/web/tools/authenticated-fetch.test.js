import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, extname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const projectRoot = dirname(fileURLToPath(new URL('../package.json', import.meta.url)));
const sourceRoot = join(projectRoot, 'src');

const sourceFiles = (directory) => readdirSync(directory, { withFileTypes: true })
  .flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    if (!['.js', '.jsx'].includes(extname(path)) || path.endsWith('.test.js')) return [];
    return [path];
  });

test('all frontend fetch calls use the authClient-backed gateway', () => {
  const directFetchPattern = /(?:^|[^\w])(?:window\.|globalThis\.)?fetch\s*\(/m;
  const directFetchFiles = sourceFiles(sourceRoot)
    .filter((path) => directFetchPattern.test(readFileSync(path, 'utf8')))
    .map((path) => relative(projectRoot, path));

  assert.deepEqual(directFetchFiles, []);

  const gateway = readFileSync(join(sourceRoot, 'lib/authFetch.js'), 'utf8');
  assert.match(gateway, /import authClient from '\.\/authClient\.js';/);
  assert.match(gateway, /client\.getAccessToken/);

  ['utils/minerva-api.js'].forEach((sourcePath) => {
    const source = readFileSync(join(sourceRoot, sourcePath), 'utf8');
    assert.match(source, /authenticatedFetch/);
  });
});
