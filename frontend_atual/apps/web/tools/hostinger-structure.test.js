import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const readProjectFile = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');

test('Hostinger metadata presents a plain Vite app', () => {
  const pkg = JSON.parse(readProjectFile('package.json'));

  assert.equal(pkg.name, 'minerva-travel-frontend');
  assert.equal(pkg.private, undefined);
  assert.equal(pkg.engines.node, '22.x');
  assert.equal(pkg.scripts.build, 'vite build');
  assert.equal(pkg.scripts.start, 'vite preview --host 0.0.0.0 --port 3000');
  assert.equal(pkg.devDependencies.vite.startsWith('^'), true);
  assert.equal(pkg.devDependencies['@vitejs/plugin-react'].startsWith('^'), true);
});

test('Vite config stays simple for Hostinger framework detection', () => {
  const config = readProjectFile('vite.config.js');

  assert.match(config, /defineConfig/);
  assert.match(config, /@vitejs\/plugin-react/);
  assert.doesNotMatch(config, /visual-editor|selection-mode|pocketbase-auth|horizons|createLogger|optimizeDeps/);
});

test('Hostinger frontend does not hard-code Horizons backend paths', () => {
  const source = readProjectFile('src/lib/authClient.js');

  assert.doesNotMatch(source, /\/hcgi\/(?:platform|api)/);
});

test('Hostinger static files do not advertise Horizons or Vite defaults', () => {
  const source = [
    readProjectFile('index.html'),
    readProjectFile('public/.htaccess'),
  ].join('\n');

  assert.doesNotMatch(source, /Hostinger Horizons|vite\.svg/);
});

test('llms index advertises the real public and create routes', () => {
  const llms = readProjectFile('public/llms.txt');

  assert.match(llms, /\[Início\]\(\/\)/);
  assert.match(llms, /\[Criar guia\]\(\/create\)/);
  assert.doesNotMatch(llms, /\/home|\/createguide|Aventuras em Família/);
});

test('runtime config loads before the React entrypoint', () => {
  const index = readProjectFile('index.html');
  const head = index.match(/<head>([\s\S]*?)<\/head>/)?.[1] || '';

  assert.match(head, /<script src="\/config\.js\?v=[^"]+"><\/script>/);
  assert.match(head, /Cache-Control/);
  assert.match(head, /no-store/);
  assert.equal(index.indexOf('/config.js') < index.indexOf('/src/main.jsx'), true);
});

test('runtime cache guard refreshes stale Chrome app shells', () => {
  const index = readProjectFile('index.html');
  const config = readProjectFile('public/config.js');
  const indexVersion = index.match(/\/config\.js\?v=([^"]+)/)?.[1];
  const configVersion = config.match(/MINERVA_APP_VERSION:\s*'([^']+)'/)?.[1];

  assert.equal(indexVersion, configVersion);
  assert.notEqual(configVersion, '20260607-cache-guard');
  assert.match(config, /if \(!latest \|\| current === latest\)/);
  assert.doesNotMatch(config, /!current \|\| !latest \|\| current === latest/);
  assert.match(config, /const reloadToken = `\$\{runtimeVersion\}:\$\{latest\}`/);
  assert.match(config, /sessionStorage\.setItem\(reloadKey, reloadToken\)/);
});

test('runtime config and HTML are not cached by Hostinger CDN', () => {
  const htaccess = readProjectFile('public/.htaccess');
  const config = readProjectFile('public/config.js');

  assert.match(htaccess, /Header set Cache-Control "no-store, no-cache, must-revalidate, max-age=0"/);
  assert.doesNotMatch(htaccess, /s-maxage=604800/);
  assert.match(htaccess, /REQUEST_URI.+\^\/assets\/\.\*/);
  assert.match(config, /MINERVA_APP_VERSION/);
  assert.match(config, /minerva_cache_check/);
  assert.match(config, /location\.reload/);
});

test('password recovery route is wired to real auth flow', () => {
  const app = readProjectFile('src/App.jsx');
  const loginPage = readProjectFile('src/pages/LoginPage.jsx');
  const resetPage = readProjectFile('src/pages/ResetPasswordPage.jsx');

  assert.match(app, /path="\/reset-password"/);
  assert.match(loginPage, /requestPasswordReset/);
  assert.doesNotMatch(loginPage, /Recupera..o de senha em breve/);
  assert.match(resetPage, /preparePasswordRecovery/);
  assert.match(resetPage, /recoveryStatus === 'ready'/);
  assert.match(resetPage, /Link inv.lido ou expirado/);
  assert.match(resetPage, /updatePassword/);
});
