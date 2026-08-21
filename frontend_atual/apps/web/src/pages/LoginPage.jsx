
import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Helmet } from 'react-helmet';
import { useAuth } from '@/contexts/AuthContext.jsx';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import AuthTravelShell from '@/components/AuthTravelShell.jsx';
import { Eye, EyeOff, Loader2, Key } from 'lucide-react';

const LoginPage = () => {
  const location = useLocation();
  // Quem acabou de criar a conta chega com o e-mail já conhecido; refazer a
  // digitação seria fricção pura logo no primeiro contato com o produto.
  const [email, setEmail] = useState(location.state?.email || '');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  const { login, requestPasswordReset } = useAuth();
  const navigate = useNavigate();

  const from = location.state?.from?.pathname || '/dashboard';
  const signupReason = location.state?.reason;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    const result = await login(email, password);

    if (result.success) {
      toast.success('Que bom ter vocês de volta.');
      navigate(from, { replace: true });
    } else {
      toast.error(result.error || 'E-mail ou senha incorretos. Tente novamente.');
    }

    setIsSubmitting(false);
  };

  const handlePasswordReset = async () => {
    const cleanEmail = email.trim();

    if (!cleanEmail) {
      toast.error('Digite seu e-mail primeiro para recuperar a senha.');
      return;
    }

    setIsResetting(true);
    const redirectTo = `${window.location.origin}/reset-password`;
    const result = await requestPasswordReset(cleanEmail, redirectTo);

    if (result.success) {
      toast.success('Enviamos um link de recuperação para o seu e-mail.');
    } else {
      toast.error(result.error || 'Não foi possível enviar o e-mail de recuperação.');
    }

    setIsResetting(false);
  };

  return (
    <>
      <Helmet>
        <title>Entrar - Minerva Travel</title>
        <meta name="description" content="Entre para abrir a estante de guias de viagem da família." />
      </Helmet>

      <AuthTravelShell
        eyebrow="Acesso à sua conta"
        title={signupReason ? 'Sua conta está pronta!' : 'Bem-vindos de volta!'}
        description={signupReason === 'confirm-email'
          ? 'Confirme o e-mail que enviamos e entre para começar.'
          : signupReason === 'signed-up'
            ? 'Entre com a senha que você acabou de criar.'
            : 'Abra sua estante de viagens e continue de onde parou.'}
        note="Seus guias e rascunhos continuam guardados na estante de viagens."
      >
            <div className="mb-7 flex items-center gap-3 border-b border-secondary/15 pb-5">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-secondary/10">
                <Key className="h-6 w-6 text-secondary" aria-hidden="true" />
              </div>
              <div>
                <p className="font-display text-xl font-bold text-secondary">Entre na sua conta</p>
                <p className="font-ui text-sm text-muted-foreground">Seus guias ficam guardados com segurança.</p>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label htmlFor="login-email" className="mb-1 block text-sm font-semibold text-foreground">E-mail</label>
                <input
                  id="login-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="font-ui w-full rounded-xl border border-secondary/20 bg-background px-4 py-3 text-foreground outline-none transition-colors focus:border-secondary focus:ring-2 focus:ring-secondary/20"
                  placeholder="seu@email.com"
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label htmlFor="login-password" className="block text-sm font-semibold text-foreground">Senha</label>
                  <button
                    type="button"
                    onClick={handlePasswordReset}
                    disabled={isResetting}
                    className="text-xs text-secondary hover:underline font-bold disabled:opacity-60 disabled:no-underline"
                  >
                    {isResetting ? 'Enviando...' : 'Esqueceu a senha?'}
                  </button>
                </div>
                <div className="relative">
                  <input
                    id="login-password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="font-ui w-full rounded-xl border border-secondary/20 bg-background px-4 py-3 pr-14 text-foreground outline-none transition-colors focus:border-secondary focus:ring-2 focus:ring-secondary/20"
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((visible) => !visible)}
                    className="absolute right-1 top-1/2 flex min-h-11 min-w-11 -translate-y-1/2 items-center justify-center rounded-xl text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary"
                    aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                    aria-pressed={showPassword}
                  >
                    {showPassword ? <EyeOff aria-hidden="true" className="h-5 w-5" /> : <Eye aria-hidden="true" className="h-5 w-5" />}
                  </button>
                </div>
              </div>

              <Button
                type="submit"
                disabled={isSubmitting}
                className="travel-cta mt-4 w-full py-6 text-lg font-bold"
              >
                {isSubmitting ? (
                  <Loader2 className="w-6 h-6 animate-spin" />
                ) : (
                  'Entrar'
                )}
              </Button>
            </form>

            <div className="mt-8 text-center">
              <p className="text-muted-foreground font-medium">
                Primeira vez por aqui?{' '}
                <Link to="/signup" className="text-secondary hover:underline font-bold">
                  Criar Conta
                </Link>
              </p>
            </div>
      </AuthTravelShell>
    </>
  );
};

export default LoginPage;
