import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const readProjectFile = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');

test('creation progress names the current and next step with progress semantics', () => {
  const progress = readProjectFile('src/components/GuideCreationProgress.jsx');

  assert.match(progress, /Próximo:/);
  assert.match(progress, /role="progressbar"/);
  assert.match(progress, /aria-valuemin=\{1\}/);
  assert.match(progress, /aria-valuemax=\{visibleSteps\.length\}/);
  assert.match(progress, /aria-valuenow=\{progressValue\}/);
  assert.match(progress, /aria-valuetext=/);
  assert.match(progress, /aria-current=\{isCurrent \? 'step' : undefined\}/);
  assert.match(progress, /motion-reduce:transition-none/);
});

test('draft status is truthful about autosave and photo privacy', () => {
  const notice = readProjectFile('src/components/DraftStatusNotice.jsx');

  assert.match(notice, /Salvando as escolhas mais recentes/);
  assert.match(notice, /Tudo salvo\. Você pode continuar depois\./);
  assert.match(notice, /Por privacidade, escolha a foto novamente quando retomar\./);
  assert.match(notice, /role=\{isError \? 'alert' : 'status'\}/);
  assert.match(notice, /if \(!config\) return null/);
  assert.match(notice, /if \(!message\) return null/);
});

test('continue later reuses the current persistence path before navigating', () => {
  const context = readProjectFile('src/contexts/ConversationalGuideContext.jsx');
  const page = readProjectFile('src/pages/CreateGuidePage.jsx');
  const actions = readProjectFile('src/components/GuideDraftActions.jsx');

  assert.match(context, /saveDraftNow: persistLatestDraft/);
  assert.match(context, /return activeSave\.current \|\| false/);
  assert.match(context, /return await activeSave\.current/);
  assert.match(page, /const saved = await saveDraftNow\(\)/);
  assert.match(page, /if \(saved\) \{\s+navigate\('\/dashboard'\)/);
  assert.match(page, /Não conseguimos salvar o rascunho agora/);
  assert.match(actions, /Continuar depois/);
  assert.match(actions, /disabled=\{busy \|\| discarding\}/);
});

test('discard remains behind an accessible confirmation and requires API confirmation', () => {
  const actions = readProjectFile('src/components/GuideDraftActions.jsx');
  const context = readProjectFile('src/contexts/ConversationalGuideContext.jsx');

  assert.match(actions, /<AlertDialog open=\{discardOpen\}/);
  assert.match(actions, /Descartar este rascunho\?/);
  assert.match(actions, /Manter rascunho/);
  assert.match(actions, /Descartar definitivamente/);
  assert.match(actions, /event\.preventDefault\(\)/);
  assert.match(context, /const deleted = await discardGuideDraft/);
  assert.match(context, /A API não confirmou o descarte do rascunho\./);
});
