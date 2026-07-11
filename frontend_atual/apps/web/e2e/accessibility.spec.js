import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const publicRoutes = ['/', '/pricing', '/signup', '/login', '/privacy', '/terms'];
const waitForVisualState = (page) => page.waitForTimeout(900);

for (const route of publicRoutes) {
  test(`${route} has no automatically detectable WCAG A/AA violations`, async ({ page }) => {
    await page.goto(route);
    await expect(page.locator('main')).toBeVisible();
    await waitForVisualState(page);

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
      .analyze();

    expect(results.violations).toEqual([]);
    if (route === '/') {
      await test.info().attach(`home-${test.info().project.name}`, {
        body: await page.screenshot({ fullPage: true }),
        contentType: 'image/png',
      });
    }
  });
}

test('skip link is the first keyboard destination', async ({ page }) => {
  await page.goto('/');
  await page.locator('body').evaluate((body) => {
    body.tabIndex = -1;
    body.focus();
  });
  await expect(page.locator('body')).toBeFocused();
  await page.keyboard.press('Tab');

  const skipLink = page.getByRole('link', { name: 'Pular para o conteúdo principal' });
  await expect(skipLink).toBeFocused();
  await skipLink.press('Enter');
  await expect(page.locator('#main-content')).toBeFocused();
});

test('public routes have no automatic WCAG violations in dark theme', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('theme', 'dark'));

  for (const route of publicRoutes) {
    await page.goto(route);
    await expect(page.locator('html')).toHaveClass(/dark/);
    await waitForVisualState(page);
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
      .analyze();
    expect(results.violations, `dark theme ${route}`).toEqual([]);
  }
});
