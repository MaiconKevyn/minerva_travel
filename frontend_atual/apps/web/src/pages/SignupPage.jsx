
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet';
import { useAuth } from '@/contexts/AuthContext.jsx';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import Header from '@/components/Header.jsx';
import { Flower, Airplane, Suitcase } from '@/components/DecorativeElements.jsx';
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
      toast.success('Conta criada com sucesso! Faça login para continuar.');
      navigate('/login');
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

      <div className="min-h-screen bg-background flex flex-col transition-colors duration-200">
        <Header />

        <main id="main-content" tabIndex={-1} className="flex-1 flex items-center justify-center p-4 relative overflow-hidden">
          <Flower className="absolute top-20 left-10 w-24 h-24 text-primary opacity-10" />
          <Airplane className="absolute bottom-20 right-10 w-32 h-32 text-secondary opacity-10" />
          <Suitcase className="absolute top-40 right-20 w-16 h-16 text-accent opacity-10" />

          <div className="w-full max-w-md bg-card dark:bg-slate-800 rounded-[40px] p-8 md:p-10 shadow-xl border-4 border-primary/10 dark:border-slate-700 relative z-10 transition-colors duration-200">
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
                <Sparkles className="w-8 h-8 text-primary" />
              </div>
              <h1 className="text-3xl font-serif font-bold text-foreground mb-2">Junte-se a Nós!</h1>
              <p className="text-muted-foreground font-medium">Crie sua conta para guardar suas histórias.</p>
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
                  className="w-full px-4 py-3 rounded-2xl border-2 border-border bg-background focus:border-primary focus:ring-4 focus:ring-primary/20 outline-none transition-all text-foreground"
                  placeholder="Ex: Família Silva"
                />
              </div>

              <div>
                <label htmlFor="signup-email" className="block text-sm font-bold text-foreground mb-1">Email Mágico</label>
                <input
                  id="signup-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-3 rounded-2xl border-2 border-border bg-background focus:border-primary focus:ring-4 focus:ring-primary/20 outline-none transition-all text-foreground"
                  placeholder="seu@email.com"
                />
              </div>

              <div>
                <label htmlFor="signup-password" className="block text-sm font-bold text-foreground mb-1">Senha Secreta</label>
                <div className="relative">
                  <input
                    id="signup-password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    aria-describedby="signup-password-help signup-password-strength"
                    className="w-full px-4 py-3 pr-14 rounded-2xl border-2 border-border bg-background focus:border-primary focus:ring-4 focus:ring-primary/20 outline-none transition-all text-foreground"
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
                  {strength === 3 && 'Senha forte! 🌟'}
                </p>
              </div>

              <div>
                <label htmlFor="signup-confirm-password" className="block text-sm font-bold text-foreground mb-1">Confirme a Senha</label>
                <div className="relative">
                  <input
                    id="signup-confirm-password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full px-4 py-3 pr-14 rounded-2xl border-2 border-border bg-background focus:border-primary focus:ring-4 focus:ring-primary/20 outline-none transition-all text-foreground"
                    placeholder="Repita sua senha secreta"
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
                className="w-full rounded-2xl py-6 bg-primary hover:bg-primary/90 text-white font-bold text-lg shadow-lg hover:-translate-y-1 transition-all mt-4"
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
                Já tem um passaporte conosco?{' '}
                <Link to="/login" className="text-primary hover:underline font-bold">
                  Entrar
                </Link>
              </p>
            </div>
          </div>
        </main>
      </div>
    </>
  );
};

export default SignupPage;
