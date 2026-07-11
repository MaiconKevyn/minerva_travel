import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import Header from '@/components/Header.jsx';
import { Airplane, Flower } from '@/components/DecorativeElements.jsx';
import { useAuth } from '@/contexts/AuthContext.jsx';
import { AlertCircle, Eye, EyeOff, KeyRound, Loader2 } from 'lucide-react';

const calculateStrength = (password) => {
  let score = 0;
  if (password.length >= 8) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/[0-9]/.test(password)) score += 1;
  return score;
};

const ResetPasswordPage = () => {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [recoveryStatus, setRecoveryStatus] = useState('checking');
  const [recoveryError, setRecoveryError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { preparePasswordRecovery, updatePassword } = useAuth();
  const navigate = useNavigate();

  const strength = calculateStrength(password);

  useEffect(() => {
    let isMounted = true;

    const prepareRecovery = async () => {
      setRecoveryStatus('checking');
      const result = await preparePasswordRecovery(window.location.href);

      if (!isMounted) {
        return;
      }

      if (result.success) {
        setRecoveryStatus('ready');
        setRecoveryError('');

        if (window.location.search || window.location.hash) {
          window.history.replaceState(window.history.state, '', '/reset-password');
        }
      } else {
        setRecoveryStatus('invalid');
        setRecoveryError(result.error || 'Link de recuperação inválido ou expirado.');
      }
    };

    prepareRecovery();

    return () => {
      isMounted = false;
    };
  }, [preparePasswordRecovery]);

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (password !== confirmPassword) {
      toast.error('As senhas não coincidem.');
      return;
    }

    if (strength < 3) {
      toast.error('A senha deve ter pelo menos 8 caracteres, uma letra maiúscula e um número.');
      return;
    }

    setIsSubmitting(true);
    const result = await updatePassword(password);

    if (result.success) {
      toast.success('Senha atualizada com sucesso.');
      navigate('/login', { replace: true });
    } else {
      toast.error(result.error || 'Não foi possível atualizar sua senha.');
    }

    setIsSubmitting(false);
  };

  return (
    <>
      <Helmet>
        <title>Redefinir Senha - Minerva Travel</title>
        <meta name="description" content="Crie uma nova senha para acessar sua conta." />
      </Helmet>

      <div className="min-h-screen bg-background flex flex-col transition-colors duration-200">
        <Header />

        <main id="main-content" tabIndex={-1} className="flex-1 flex items-center justify-center p-4 relative overflow-hidden">
          <Flower className="absolute bottom-20 left-10 w-32 h-32 text-secondary opacity-10" />
          <Airplane className="absolute top-20 right-20 w-24 h-24 text-primary opacity-10" />

          <div className="w-full max-w-md bg-card dark:bg-slate-800 rounded-[40px] p-8 md:p-10 shadow-xl border-4 border-secondary/10 dark:border-slate-700 relative z-10 transition-colors duration-200">
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-secondary/10 mb-4">
                <KeyRound className="w-8 h-8 text-secondary" />
              </div>
              <h1 className="text-3xl font-serif font-bold text-foreground mb-2">Crie uma Nova Senha</h1>
              <p className="text-muted-foreground font-medium">Use uma senha forte para proteger sua conta.</p>
            </div>

            {recoveryStatus === 'checking' && (
              <div className="rounded-3xl border border-border bg-background/70 p-6 text-center" role="status" aria-live="polite">
                <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-secondary" />
                <p className="font-bold text-foreground">Validando seu link de recuperação...</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Isso leva só alguns segundos.
                </p>
              </div>
            )}

            {recoveryStatus === 'invalid' && (
              <div className="space-y-5">
                <div className="rounded-3xl border border-destructive/20 bg-destructive/10 p-5 text-center" role="alert">
                  <AlertCircle className="mx-auto mb-3 h-9 w-9 text-destructive" />
                  <p className="font-bold text-foreground">Link inválido ou expirado</p>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                    {recoveryError}
                  </p>
                </div>
                <Button
                  asChild
                  className="w-full rounded-2xl py-6 bg-secondary hover:bg-secondary/90 text-white font-bold text-lg shadow-lg"
                >
                  <Link to="/login">Solicitar novo link</Link>
                </Button>
              </div>
            )}

            {recoveryStatus === 'ready' && (
              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label htmlFor="reset-password" className="block text-sm font-bold text-foreground mb-1">Nova Senha</label>
                  <div className="relative">
                    <input
                      id="reset-password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      required
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      aria-describedby="reset-password-help reset-password-strength"
                      className="w-full px-4 py-3 pr-14 rounded-2xl border-2 border-border bg-background focus:border-secondary focus:ring-4 focus:ring-secondary/20 outline-none transition-all text-foreground"
                      placeholder="Mínimo 8 caracteres"
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

                  {password && (
                    <div
                      id="reset-password-strength"
                      role="meter"
                      aria-label="Força da senha"
                      aria-valuemin="0"
                      aria-valuemax="3"
                      aria-valuenow={strength}
                      aria-valuetext={strength === 3 ? 'Forte' : 'Ainda não atende aos requisitos'}
                      className="mt-2 flex gap-1 h-2"
                    >
                      <div aria-hidden="true" className={`flex-1 rounded-full ${strength >= 1 ? 'bg-destructive' : 'bg-muted'}`} />
                      <div aria-hidden="true" className={`flex-1 rounded-full ${strength >= 2 ? 'bg-secondary' : 'bg-muted'}`} />
                      <div aria-hidden="true" className={`flex-1 rounded-full ${strength >= 3 ? 'bg-accent' : 'bg-muted'}`} />
                    </div>
                  )}
                  <p id="reset-password-help" className="mt-1 text-xs font-medium text-muted-foreground">
                    Use 8 ou mais caracteres, uma letra maiúscula e um número.
                  </p>
                </div>

                <div>
                  <label htmlFor="reset-confirm-password" className="block text-sm font-bold text-foreground mb-1">Confirme a Nova Senha</label>
                  <div className="relative">
                    <input
                      id="reset-confirm-password"
                      type={showConfirmPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      required
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                      className="w-full px-4 py-3 pr-14 rounded-2xl border-2 border-border bg-background focus:border-secondary focus:ring-4 focus:ring-secondary/20 outline-none transition-all text-foreground"
                      placeholder="Repita sua nova senha"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword((visible) => !visible)}
                      className="absolute right-1 top-1/2 flex min-h-11 min-w-11 -translate-y-1/2 items-center justify-center rounded-xl text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary"
                      aria-label={showConfirmPassword ? 'Ocultar confirmação da senha' : 'Mostrar confirmação da senha'}
                      aria-pressed={showConfirmPassword}
                    >
                      {showConfirmPassword ? <EyeOff aria-hidden="true" className="h-5 w-5" /> : <Eye aria-hidden="true" className="h-5 w-5" />}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full rounded-2xl py-6 bg-secondary hover:bg-secondary/90 text-white font-bold text-lg shadow-lg hover:-translate-y-1 transition-all mt-4"
                >
                  {isSubmitting ? (
                    <Loader2 className="w-6 h-6 animate-spin" />
                  ) : (
                    'Salvar Nova Senha'
                  )}
                </Button>
              </form>
            )}

            <div className="mt-8 text-center">
              <Link to="/login" className="text-secondary hover:underline font-bold">
                Voltar para o login
              </Link>
            </div>
          </div>
        </main>
      </div>
    </>
  );
};

export default ResetPasswordPage;
