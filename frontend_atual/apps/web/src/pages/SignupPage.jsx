
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet';
import { useAuth } from '@/contexts/AuthContext.jsx';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import AuthTravelShell from '@/components/AuthTravelShell.jsx';
import { Sparkles, ArrowRight, Eye, EyeOff, Loader2 } from 'lucide-react';

const SignupPage = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { signup } = useAuth();
  const navigate = useNavigate();

  const calculateStrength = (pwd) => {
    let score = 0;
    if (pwd.length >= 8) score += 1;
    if (/[A-Z]/.test(pwd)) score += 1;
    if (/[0-9]/.test(pwd)) score += 1;
    return score;
  };

  const strength = calculateStrength(password);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      toast.error('As senhas não coincidem!');
      return;
    }

    if (strength < 3) {
      toast.error('A senha deve ter pelo menos 8 caracteres, uma letra maiúscula e um número.');
      return;
    }

    setIsSubmitting(true);
    const result = await signup(email, password, name);

    if (result.success) {
      if (result.authenticated) {
        // Cadastro já autenticado: mandar para o login seria um passo inútil.
        toast.success('Conta criada! Vamos montar o guia da sua família.');
        navigate('/create');
      } else if (result.needsEmailConfirmation) {
        toast.success('Conta criada! Confirme o e-mail que enviamos para entrar.');
        navigate('/login', { state: { email, reason: 'confirm-email' } });
      } else {
        // Sem sessão automática: ao menos levamos o e-mail preenchido adiante.
        toast.success('Conta criada! Entre para continuar.');
        navigate('/login', { state: { email, reason: 'signed-up' } });
      }
    } else {
      toast.error(result.error);
    }
    setIsSubmitting(false);
  };

  return (
    <>
      <Helmet>
        <title>Criar Conta - Minerva Travel</title>
        <meta name="description" content="Crie sua conta para começar a escrever o livro de viagens da sua família." />
      </Helmet>

      <AuthTravelShell
        eyebrow="Criação de conta"
        title="Crie sua conta"
        description="Crie sua conta para montar o guia, guardar cada viagem e voltar às histórias quando quiser."
        note="Cada guia fica salvo na sua biblioteca e pode ser baixado com segurança."
      >
            <div className="mb-7 flex items-center gap-3 border-b border-primary/15 pb-5">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                <Sparkles className="h-6 w-6 text-primary" aria-hidden="true" />
              </div>
              <div>
                <p className="font-display text-xl font-bold text-primary">Dados da conta</p>
                <p className="font-ui text-sm text-muted-foreground">Leva menos de um minuto.</p>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label htmlFor="signup-name" className="block text-sm font-bold text-foreground mb-1">Nome da Família ou Responsável</label>
                <input
                  id="signup-name"
                  type="text"
                  autoComplete="name"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="font-ui w-full rounded-xl border border-primary/20 bg-background px-4 py-3 text-foreground outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
                  placeholder="Ex: Família Silva"
                />
              </div>

              <div>
                <label htmlFor="signup-email" className="mb-1 block text-sm font-semibold text-foreground">E-mail</label>
                <input
                  id="signup-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="font-ui w-full rounded-xl border border-primary/20 bg-background px-4 py-3 text-foreground outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
                  placeholder="seu@email.com"
                />
              </div>

              <div>
                <label htmlFor="signup-password" className="mb-1 block text-sm font-semibold text-foreground">Senha</label>
                <div className="relative">
                  <input
                    id="signup-password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    aria-describedby="signup-password-help signup-password-strength"
                    className="font-ui w-full rounded-xl border border-primary/20 bg-background px-4 py-3 pr-14 text-foreground outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
                    placeholder="Mínimo 8 caracteres"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((visible) => !visible)}
                    className="absolute right-1 top-1/2 flex min-h-11 min-w-11 -translate-y-1/2 items-center justify-center rounded-xl text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                    aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                    aria-pressed={showPassword}
                  >
                    {showPassword ? <EyeOff aria-hidden="true" className="h-5 w-5" /> : <Eye aria-hidden="true" className="h-5 w-5" />}
                  </button>
                </div>

                {password && (
                  <div
                    id="signup-password-strength"
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
                <p id="signup-password-help" className="text-xs text-muted-foreground mt-1 font-medium">
                  {strength < 3 && password ? 'A senha deve ter 8+ letras, 1 maiúscula e 1 número.' : ''}
                  {strength === 3 && 'Senha forte.'}
                </p>
              </div>

              <div>
                <label htmlFor="signup-confirm-password" className="mb-1 block text-sm font-semibold text-foreground">Confirmar senha</label>
                <div className="relative">
                  <input
                    id="signup-confirm-password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="font-ui w-full rounded-xl border border-primary/20 bg-background px-4 py-3 pr-14 text-foreground outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
                    placeholder="Repita sua senha"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword((visible) => !visible)}
                    className="absolute right-1 top-1/2 flex min-h-11 min-w-11 -translate-y-1/2 items-center justify-center rounded-xl text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
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
                className="travel-cta mt-4 w-full py-6 text-lg font-bold"
              >
                {isSubmitting ? (
                  <Loader2 className="w-6 h-6 animate-spin" />
                ) : (
                  <span className="flex items-center gap-2">
                    Criar Minha Conta <ArrowRight className="w-5 h-5" />
                  </span>
                )}
              </Button>
            </form>

            <div className="mt-8 text-center">
              <p className="text-muted-foreground font-medium">
                Já tem uma conta?{' '}
                <Link to="/login" className="text-primary hover:underline font-bold">
                  Entrar
                </Link>
              </p>
            </div>
      </AuthTravelShell>
    </>
  );
};

export default SignupPage;
