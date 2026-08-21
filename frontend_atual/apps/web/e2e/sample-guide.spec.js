import { expect, test } from '@playwright/test';

test('visitor can browse every page of the sample guide', async ({ page }, testInfo) => {
  await page.goto('/');

  const guide = page.locator('#guia-exemplo');
  await guide.scrollIntoViewIfNeeded();
  await expect(guide.getByRole('heading', { name: 'Folheie a aventura antes de criar a sua' })).toBeVisible();
  // O livro já chega aberto: a vitrine é o folhear, sem clique de cortina.
  await expect(guide.getByLabel('Leitor do guia de exemplo. Use as setas esquerda e direita para folhear.')).toBeVisible();
  await expect(guide.getByText('Capa · página 1 de 19', { exact: true })).toBeVisible();
  // Recolher continua possível e volta ao leque de páginas-chave.
  await guide.getByRole('button', { name: 'Recolher guia' }).click();
  await expect(guide.getByRole('button', { name: /Abrir o guia na página/ })).toHaveCount(5);
  await guide.getByRole('button', { name: 'Abrir as 19 páginas' }).click();
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

  const guide = page.locator('#guia-exemplo');
  const reader = guide.getByLabel('Leitor do guia de exemplo. Use as setas esquerda e direita para folhear.');
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

test('activity catalogue filters real examples with age time and material metadata', async ({ page }) => {
  await page.goto('/');

  const catalogue = page.getByRole('heading', { name: '18 atividades diferentes' }).locator('..').locator('..');
  const puzzleTab = page.getByRole('tab', { name: /Quebra-cabeças 7/ });
  await puzzleTab.scrollIntoViewIfNeeded();
  await puzzleTab.click();

  await expect(puzzleTab).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('tabpanel').getByRole('heading', { name: 'Quebra-cabeças' })).toBeVisible();
  await expect(page.getByRole('tabpanel').getByText('Caça-palavras', { exact: true })).toBeVisible();
  await expect(page.getByRole('tabpanel').getByText('10–15 min', { exact: true }).first()).toBeVisible();
  await expect(catalogue).toBeVisible();
});

test('a virada gira uma folha só, sem o livro sumir nem pular', async ({ page }, testInfo) => {
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.goto('/');

  const guide = page.locator('#guia-exemplo');
  await guide.scrollIntoViewIfNeeded();
  const base = guide.locator('.sample-guide-book > .sample-guide-spread, .sample-guide-book > .sample-guide-single');
  const leaf = guide.locator('.sample-guide-leaf');

  // Medido em relacao ao proprio livro: rolagem da pagina mexe no
  // boundingBox e mascararia o que interessa.
  const posicaoNoLivro = () =>
    base.evaluate((el) => {
      const livro = el.closest('.sample-guide-book').getBoundingClientRect();
      const r = el.getBoundingClientRect();
      return { deslocamento: r.top - livro.top, altura: r.height };
    });

  await expect(base).toHaveCount(1);
  await expect(leaf).toHaveCount(0);
  const before = await posicaoNoLivro();

  await guide.getByRole('button', { name: 'Próxima', exact: true }).click();

  // A folha existe e tem as duas faces: a de cima e a que vai assentar.
  await expect(leaf).toHaveCount(1);
  await expect(leaf.locator('.sample-guide-leaf-face')).toHaveCount(2);

  // O livro embaixo nao esmaece nem se mexe. Era o defeito antigo: ele caia
  // para opacidade 0,25 e subia 14px no meio da troca.
  await expect(base).toHaveCSS('opacity', '1');
  const during = await posicaoNoLivro();
  expect(Math.abs(during.deslocamento - before.deslocamento)).toBeLessThan(2);
  expect(Math.abs(during.altura - before.altura)).toBeLessThan(2);

  // A folha tem de nascer na lombada e girar em torno dela. Montar o nome da
  // classe com template fazia o Tailwind purgar `--right`/`--left` do CSS: a
  // folha ficava sem `left` e sem `transform-origin`, girava pelo proprio
  // centro e invadia a pagina da esquerda. Purge nao aparece em revisao de
  // codigo, so aqui.
  const geometria = await leaf.evaluate((el) => {
    const livro = el.closest('.sample-guide-book').getBoundingClientRect();
    const cs = getComputedStyle(el);
    return {
      esquerdaRelativa: el.getBoundingClientRect().left - livro.left,
      lombada: livro.width / 2,
      origemX: Number.parseFloat(cs.transformOrigin.split(' ')[0]),
    };
  });
  // No spread a folha nasce na lombada; no celular, que e pagina unica, ela
  // ocupa a largura toda e gira pela borda esquerda.
  const inicioEsperado = testInfo.project.name.includes('mobile') ? 0 : geometria.lombada;
  expect(Math.abs(geometria.esquerdaRelativa - inicioEsperado)).toBeLessThan(2);
  expect(geometria.origemX).toBeLessThan(2);

  // Uma pagina em rotacao se projeta MAIOR que sua altura parada. Como o
  // palco tem `overflow: hidden`, sem folga vertical ela era fatiada no topo
  // e na base — medido, 32px para cada lado no auge do giro.
  const vazamento = await leaf.evaluate((el) => {
    const palco = el.closest('.sample-guide-stage').getBoundingClientRect();
    let pior = -Infinity;
    const original = el.style.transform;
    for (let g = -5; g >= -175; g -= 10) {
      el.style.setProperty('transform', `rotateY(${g}deg)`, 'important');
      const f = el.getBoundingClientRect();
      pior = Math.max(pior, palco.top - f.top, f.bottom - palco.bottom);
    }
    el.style.transform = original;
    return pior;
  });
  expect(vazamento).toBeLessThanOrEqual(0);

  // Quando a folha assenta ela some e o rotulo avanca.
  await expect(leaf).toHaveCount(0, { timeout: 4000 });
  const expectedLabel = testInfo.project.name.includes('mobile')
    ? 'Página 2 de 19'
    : 'Páginas 2 e 3 de 19';
  await expect(guide.getByText(expectedLabel, { exact: true })).toBeVisible();
});
