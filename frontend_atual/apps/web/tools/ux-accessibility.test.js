import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const readProjectFile = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');

test('document language identifies Brazilian Portuguese content', () => {
  const html = readProjectFile('index.html');

  assert.match(html, /<html lang="pt-BR">/);
});

test('header exposes an accessible logo and mobile navigation state', () => {
  const header = readProjectFile('src/components/Header.jsx');
  const themeToggle = readProjectFile('src/components/ThemeToggle.jsx');

  assert.match(header, /aria-label="Minerva Travel — página inicial"/);
  assert.match(header, /aria-label=\{mobileMenuOpen \? 'Fechar menu principal' : 'Abrir menu principal'\}/);
  assert.match(header, /aria-expanded=\{mobileMenuOpen\}/);
  assert.match(header, /aria-controls=\{mobileMenuId\}/);
  assert.match(header, /id=\{mobileMenuId\}/);
  assert.match(header, /aria-current=\{isActive\(link\.path\) \? 'page' : undefined\}/);
  assert.match(themeToggle, /Ativar tema escuro/);
  assert.match(themeToggle, /Ativar tema claro/);
});

test('family validation uses the mounted Sonner toaster and accessible inline feedback', () => {
  const app = readProjectFile('src/App.jsx');
  const familyStep = readProjectFile('src/components/EnhancedStep5FamilyDetails.jsx');

  assert.match(app, /import \{ Toaster \} from 'sonner';/);
  assert.match(app, /<Toaster/);
  assert.match(familyStep, /import \{ toast \} from 'sonner';/);
  assert.doesNotMatch(familyStep, /useToast/);
  assert.match(familyStep, /MAX_GUIDE_PARENTS/);
  assert.match(familyStep, /parents\.length >= MAX_GUIDE_PARENTS/);
  assert.match(familyStep, /role="alert"/);
  assert.match(familyStep, /aria-live="assertive"/);
  assert.match(familyStep, /aria-describedby=/);
  assert.match(familyStep, /document\.getElementById\(focusTargetId\)\?\.focus\(\)/);
});

test('destination additions no longer derive IDs from the current list length', () => {
  const destinationStep = readProjectFile('src/components/Step3Destination.jsx');

  assert.match(destinationStep, /createGuideDestination\(\)/);
  assert.doesNotMatch(destinationStep, /createGuideDestination\(prev\.length\)/);
  assert.match(destinationStep, /pendingFocusDestinationId/);
});

test('authentication forms expose labels, autocomplete and accessible password controls', () => {
  const login = readProjectFile('src/pages/LoginPage.jsx');
  const signup = readProjectFile('src/pages/SignupPage.jsx');
  const reset = readProjectFile('src/pages/ResetPasswordPage.jsx');

  assert.match(login, /htmlFor="login-email"/);
  assert.match(login, /id="login-email"/);
  assert.match(login, /autoComplete="email"/);
  assert.match(login, /autoComplete="current-password"/);
  assert.match(login, /aria-label=\{showPassword \? 'Ocultar senha' : 'Mostrar senha'\}/);

  assert.match(signup, /htmlFor="signup-name"/);
  assert.match(signup, /autoComplete="name"/);
  assert.match(signup, /autoComplete="new-password"/);
  assert.match(signup, /role="meter"/);
  assert.match(signup, /aria-valuetext=/);

  assert.match(reset, /htmlFor="reset-password"/);
  assert.match(reset, /htmlFor="reset-confirm-password"/);
  assert.match(reset, /role="status"/);
  assert.match(reset, /role="alert"/);
  assert.match(reset, /role="meter"/);
});
