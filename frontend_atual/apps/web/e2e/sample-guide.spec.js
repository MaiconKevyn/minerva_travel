import { expect, test } from '@playwright/test';

test('visitor can browse every page of the sample guide', async ({ page }, testInfo) => {
  await page.goto('/');

  const guide = page.locator('#guia-exemplo');
  await guide.scrollIntoViewIfNeeded();
  await expect(guide.getByRole('heading', { name: 'Folheie a aventura antes de criar a sua' })).toBeVisible();
  await expect(guide.getByText('Capa · página 1 de 19', { exact: true })).toBeVisible();
  await expect(guide.getByAltText(/Página 1 do guia de exemplo: Capa da Família Knopp/)).toBeVisible();

  await guide.getByRole('button', { name: 'Próxima', exact: true }).click();
  if (testInfo.project.name.includes('mobile')) {
    await expect(guide.getByText('Página 2 de 19', { exact: true })).toBeVisible();
  } else {
    await expect(guide.getByText('Páginas 2 e 3 de 19', { exact: true })).toBeVisible();
    await expect(guide.getByAltText(/Página 3 do guia de exemplo: Descubra Paris/)).toBeVisible();
  }
  await expect(guide.getByAltText(/Página 2 do guia de exemplo: Nosso roteiro/)).toBeVisible();

  await guide.getByRole('button', { name: 'Ir para a página 19: Hora de voltar para casa' }).click();
  if (testInfo.project.name.includes('mobile')) {
    await expect(guide.getByText('Página 19 de 19', { exact: true })).toBeVisible();
  } else {
    await expect(guide.getByText('Páginas 18 e 19 de 19', { exact: true })).toBeVisible();
  }
  await expect(guide.getByAltText(/Página 19 do guia de exemplo: Hora de voltar para casa/)).toBeVisible();
  await expect(guide.getByRole('button', { name: 'Próxima', exact: true })).toBeDisabled();

  await guide.getByRole('button', { name: 'Ampliar' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('heading', { name: 'Guia demonstrativo completo' })).toBeVisible();
  await expect(dialog.getByAltText(/Página 19 do guia de exemplo: Hora de voltar para casa/)).toBeVisible();
});

test('sample guide supports keyboard paging and links to creation', async ({ page }, testInfo) => {
  await page.goto('/');

  const reader = page.getByLabel('Leitor do guia de exemplo. Use as setas esquerda e direita para folhear.');
  await reader.scrollIntoViewIfNeeded();
  await reader.focus();
  await reader.press('ArrowRight');

  const expectedLabel = testInfo.project.name.includes('mobile')
    ? 'Página 2 de 19'
    : 'Páginas 2 e 3 de 19';
  await expect(reader.getByText(expectedLabel, { exact: true })).toBeVisible();

  await reader.press('Home');
  await expect(reader.getByText('Capa · página 1 de 19', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Criar o guia da minha família' }).last()).toHaveAttribute('href', '/create');
});
