import assert from 'node:assert/strict';
import test from 'node:test';

import { resolveInitialTheme } from './theme.js';

test('a marca abre no tema claro quando não há preferência salva', () => {
  // A identidade é um livro em aquarela sobre papel creme: seguir o modo
  // escuro do sistema descaracterizava a primeira impressão do produto.
  assert.equal(resolveInitialTheme(null), 'light');
  assert.equal(resolveInitialTheme(undefined), 'light');
  assert.equal(resolveInitialTheme(''), 'light');
  assert.equal(resolveInitialTheme('valor-invalido'), 'light');
});

test('a escolha explícita do usuário continua sendo respeitada', () => {
  assert.equal(resolveInitialTheme('dark'), 'dark');
  assert.equal(resolveInitialTheme('light'), 'light');
});
