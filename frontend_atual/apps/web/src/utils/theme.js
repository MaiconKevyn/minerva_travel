export const THEME_STORAGE_KEY = 'theme';

export const VALID_THEMES = ['light', 'dark'];

/**
 * O guia é um livro em aquarela sobre papel creme. Herdar o modo escuro do
 * sistema fazia a primeira impressão do produto parecer um SaaS genérico,
 * então o claro é o padrão da marca. A escolha explícita do usuário continua
 * sendo respeitada nas próximas visitas.
 */
export const resolveInitialTheme = (savedTheme) =>
  VALID_THEMES.includes(savedTheme) ? savedTheme : 'light';
