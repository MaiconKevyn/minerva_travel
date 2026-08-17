import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const readProjectFile = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');

test('dashboard uses authenticated FastAPI guide records without PocketBase profile writes', () => {
  const dashboard = readProjectFile('src/pages/DashboardPage.jsx');

  assert.doesNotMatch(dashboard, /pocketbaseClient|pb\.collection|handleUpdateProfile|updateProfile/);
  assert.match(dashboard, /listGuides/);
  assert.match(dashboard, /listGuideJobs/);
  assert.match(dashboard, /getGuide/);
  assert.match(dashboard, /deleteGuide/);
  assert.match(dashboard, /downloadGuidePdf/);
  assert.match(dashboard, /<dl className="space-y-4">/);
  assert.doesNotMatch(dashboard, />Editar</);
});

test('dashboard exposes loading, error, retry, status, detail and owner actions', () => {
  const dashboard = readProjectFile('src/pages/DashboardPage.jsx');

  assert.match(dashboard, /role="status"/);
  assert.match(dashboard, /role="alert"/);
  assert.match(dashboard, /Tentar novamente/);
  assert.match(dashboard, /aria-expanded=\{detailsOpen\}/);
  assert.match(dashboard, /Baixar PDF/);
  assert.match(dashboard, /Confirmar exclusão de/);
  assert.match(dashboard, /Excluir definitivamente/);
  assert.match(dashboard, /Excluir guia/);
  assert.match(dashboard, /succeeded: \{ label: 'Pronto'/);
  assert.match(dashboard, /running: \{ label: 'Em andamento'/);
  assert.match(dashboard, /failed: \{ label: 'Falhou'/);
  assert.match(dashboard, /Guias em criação/);
  assert.match(dashboard, /Preview aprovado/);
  assert.match(dashboard, /approved_page_count/);
  assert.match(dashboard, /setInterval\(\(\) => requestGuideList\(true\), 5000\)/);
});

test('guide API client targets list, owner detail and owner delete endpoints', () => {
  const api = readProjectFile('src/utils/minerva-api.js');

  assert.match(api, /export const listGuides/);
  assert.match(api, /export const listGuideJobs/);
  assert.match(api, /export const getGuide/);
  assert.match(api, /export const deleteGuide/);
  assert.match(api, /\/api\/guides\/\$\{encodeURIComponent\(normalizedGuideId\)\}/);
  assert.match(api, /method: 'DELETE'/);
  assert.match(api, /export const downloadGuidePdf/);
  assert.match(api, /resolvedUrl\.origin !== baseUrl\.origin/);
});
