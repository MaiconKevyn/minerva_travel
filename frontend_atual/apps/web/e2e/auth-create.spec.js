import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test('a family can sign up, log in and reach the accessible create wizard', async ({ page }) => {
  await page.route('**/api/guides', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{"guides":[]}' });
  });
  await page.route('**/api/drafts/current', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{"draft":null}' });
  });

  const email = `familia-${test.info().project.name}@example.test`;
  const password = 'Aventura2026';

  await page.goto('/signup');
  await page.getByLabel('Nome da Família ou Responsável').fill('Família Teste');
  await page.getByLabel('Email Mágico').fill(email);
  await page.getByLabel('Senha Secreta', { exact: true }).fill(password);
  await page.getByLabel('Confirme a Senha').fill(password);
  await page.getByRole('button', { name: 'Criar Minha Conta' }).click();

  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel('Email Mágico').fill(email);
  await page.getByLabel('Senha Secreta').fill(password);
  await page.getByRole('button', { name: 'Entrar na Aventura' }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await page.goto('/create');
  await expect(page.getByRole('heading', { name: 'Para onde vai ser a aventura?' })).toBeVisible();
  await page.waitForTimeout(900);

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(results.violations).toEqual([]);
  await test.info().attach(`create-wizard-${test.info().project.name}`, {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  });
});
