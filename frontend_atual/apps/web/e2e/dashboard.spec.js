import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const authenticateLocalTestUser = async (page) => {
  await page.addInitScript(() => {
    globalThis.localStorage.setItem('minerva_local_session', JSON.stringify({
      id: 'local:familia@example.com',
      email: 'familia@example.com',
      name: 'Família Aurora',
      collectionName: 'users',
    }));
  });
};

const mockDashboard = async (page, { guides = [], jobs = [] } = {}) => {
  await page.route('**/api/guides', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ guides }),
  }));
  await page.route('**/api/jobs', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ jobs }),
  }));
};

const assertNoHorizontalOverflow = async (page) => {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);
};

test.beforeEach(async ({ page }) => {
  await authenticateLocalTestUser(page);
});

test('dashboard presents the family library, generation progress and primary actions', async ({ page }) => {
  await mockDashboard(page, {
    guides: [
      {
        id: 'guide-paris',
        title: 'Família Aurora em Paris',
        status: 'succeeded',
        destinations: [{ place: 'Paris' }],
        created_at: '2026-08-20T10:00:00Z',
        download_url: '/download/guide-paris.pdf',
        cover_url: null,
      },
    ],
    jobs: [
      {
        id: 'job-roma',
        status: 'running',
        stage: 'generating_content',
        progress: 48,
        guide_preview: {
          title: 'Família Aurora em Roma',
          destinations: [{ place: 'Roma' }],
          approved_page_count: 6,
          page_count: 12,
          cover_url: null,
        },
      },
    ],
  });

  await page.goto('/dashboard');

  await expect(page.getByRole('heading', { name: 'Olá, Família Aurora!' })).toBeVisible();
  await expect(page.getByText('Na estante').locator('..')).toContainText('1');
  await expect(page.getByText('Em criação', { exact: true }).locator('..')).toContainText('1');
  await expect(page.getByText('Acompanhe a criação')).toBeVisible();
  await expect(page.getByRole('progressbar', { name: 'Progresso de Família Aurora em Roma' }))
    .toHaveAttribute('aria-valuenow', '48');
  await expect(page.getByRole('button', { name: 'Baixar PDF' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Criar novo guia' })).toBeVisible();
  await assertNoHorizontalOverflow(page);

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(results.violations).toEqual([]);

  const screenshotPath = test.info().outputPath(`dashboard-${test.info().project.name}.png`);
  await page.screenshot({ fullPage: true, path: screenshotPath });
  await test.info().attach(`dashboard-${test.info().project.name}`, {
    path: screenshotPath,
    contentType: 'image/png',
  });
});

test('empty dashboard explains the first step and offers a direct creation action', async ({ page }) => {
  await mockDashboard(page);

  await page.goto('/dashboard');

  await expect(page.getByRole('heading', { name: 'O livro está em branco!' })).toBeVisible();
  await expect(page.getByText('Crie o primeiro guia')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Criar meu primeiro guia' })).toBeVisible();
  await expect(page.getByText('Na estante').locator('..')).toContainText('0');
  await expect(page.getByText('Em criação', { exact: true }).locator('..')).toContainText('0');
  await assertNoHorizontalOverflow(page);
});
