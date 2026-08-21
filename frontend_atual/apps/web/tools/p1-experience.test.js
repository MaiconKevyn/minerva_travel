import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const readProjectFile = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');

test('public decision pages share a single editorial footer implementation', () => {
  const footer = readProjectFile('src/components/SiteFooter.jsx');
  const publicPages = [
    'src/pages/HomePage.jsx',
    'src/pages/PricingPage.jsx',
    'src/pages/PrivacyPage.jsx',
    'src/pages/TermsPage.jsx',
  ];

  assert.match(footer, /<footer/);
  assert.match(footer, /Privacidade/);
  assert.match(footer, /Termos/);
  assert.match(footer, /Preço/);
  publicPages.forEach((path) => {
    const source = readProjectFile(path);
    assert.match(source, /SiteFooter/);
    assert.doesNotMatch(source, /<footer/);
  });
});

test('public copy describes the implemented optional-photo and cover-approval flow', () => {
  const faq = readProjectFile('src/components/HomeFaq.jsx');
  const anatomy = readProjectFile('src/components/BookAnatomy.jsx');

  assert.match(faq, /A foto é opcional/);
  assert.match(faq, /demais páginas são criadas em segundo plano/);
  assert.doesNotMatch(faq, /Nenhuma página entra no livro sem a sua aprovação/);
  assert.match(anatomy, /sem foto, a capa nasce do roteiro e dos destinos/);
});

test('dashboard P1 exposes journey summary, actionable empty state and semantic progress', () => {
  const dashboard = readProjectFile('src/pages/DashboardPage.jsx');

  assert.match(dashboard, /Resumo da biblioteca/);
  assert.match(dashboard, /Na estante/);
  assert.match(dashboard, /Em criação/);
  assert.match(dashboard, /Próximo passo/);
  assert.match(dashboard, /Criar meu primeiro guia/);
  assert.match(dashboard, /role="progressbar"/);
  assert.match(dashboard, /aria-valuemin=\{0\}/);
  assert.match(dashboard, /aria-valuemax=\{100\}/);
  assert.match(dashboard, /aria-valuenow=\{progress\}/);
});
