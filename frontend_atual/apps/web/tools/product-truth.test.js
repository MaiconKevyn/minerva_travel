import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const source = async (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

test('pricing reflects the server-owned checkout state without a hard-coded price', async () => {
  const pricing = await source('src/pages/PricingPage.jsx');

  assert.match(pricing, /getGuideProduct/);
  assert.match(pricing, /formatPrice/);
  assert.match(pricing, /Mercado Pago/);
  assert.match(pricing, /Sem cobrança ativa/);
  assert.doesNotMatch(pricing, /R\$\s*\d|€\s*\d|Transação 100% protegida/);
});

test('privacy and terms routes are real links', async () => {
  const [app, home, pricing, footer] = await Promise.all([
    source('src/App.jsx'),
    source('src/pages/HomePage.jsx'),
    source('src/pages/PricingPage.jsx'),
    source('src/components/SiteFooter.jsx'),
  ]);

  assert.match(app, /path="\/privacy"/);
  assert.match(app, /path="\/terms"/);
  assert.match(home, /SiteFooter/);
  assert.match(pricing, /SiteFooter/);
  assert.match(footer, /to="\/privacy"/);
  assert.match(footer, /to="\/terms"/);
});

test('photo step discloses processing and accepts only supported image types', async () => {
  const photoStep = await source('src/components/Step2CoverPhoto.jsx');

  assert.match(photoStep, /\.jpg,\.jpeg,\.png,\.webp/);
  assert.match(photoStep, /Autorizo o processamento desta foto/);
  assert.match(photoStep, /não será usada para treinamento/);
  assert.match(photoStep, /to="\/privacy"/);
});
