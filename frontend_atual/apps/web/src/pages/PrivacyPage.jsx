import React from 'react';
import { Helmet } from 'react-helmet';
import { Link } from 'react-router-dom';
import Header from '@/components/Header.jsx';

const Section = ({ title, children }) => (
  <section className="space-y-3">
    <h2 className="text-2xl font-serif font-bold text-foreground">{title}</h2>
    <div className="space-y-3 leading-7 text-muted-foreground">{children}</div>
  </section>
);

const PrivacyPage = () => (
  <>
    <Helmet>
      <title>Política de Privacidade - Minerva Travel</title>
      <meta
        name="description"
        content="Como a Minerva Travel trata dados de conta, roteiro e foto familiar no piloto."
      />
    </Helmet>
    <div className="min-h-screen bg-background text-foreground">
      <Header />
      <main id="main-content" tabIndex={-1} className="mx-auto max-w-3xl space-y-10 px-5 py-12 sm:px-8">
        <div className="space-y-4">
          <p className="text-sm font-bold uppercase tracking-widest text-primary">
            Versão 2026-07-10 · piloto controlado
          </p>
          <h1 className="text-4xl font-serif font-bold sm:text-5xl">
            Política de Privacidade
          </h1>
          <p className="text-lg leading-8 text-muted-foreground">
            Esta página descreve o tratamento técnico já implementado. O produto não deve
            receber fotos reais de crianças fora de um piloto autorizado enquanto retenção,
            limpeza automática e revisão jurídica do mercado não estiverem concluídas.
          </p>
        </div>

        <Section title="Dados e finalidade">
          <p>
            Tratamos dados da conta (identificador, nome e e-mail), roteiro, nomes e idades
            informados pela família, uma foto de capa, artefatos gerados e eventos técnicos sem
            texto livre. Esses dados servem para autenticar, montar, proteger, disponibilizar e
            excluir o guia solicitado.
          </p>
        </Section>

        <Section title="Foto familiar e crianças">
          <p>
            A foto é opcional somente quando a interface oferecer alternativa sem foto; no fluxo
            atual ela é usada para a capa. O responsável deve ter autorização para enviá-la. O
            arquivo é validado, reencodado e tem EXIF/GPS removidos antes do processamento.
          </p>
          <p>
            A Minerva Travel não usa fotos ou textos para treinamento próprio. Qualquer uso para
            treinamento exigiria uma autorização separada e destacada.
          </p>
        </Section>

        <Section title="Serviços que podem receber dados">
          <p>
            Conforme a configuração do ambiente, usamos Supabase para identidade e persistência,
            OpenAI para interpretar texto, Google Maps/Places para localizar atrações, um provedor
            de imagem como Replicate para ilustração e Wikimedia Commons para imagens licenciadas.
            Apenas o dado necessário à etapa é enviado; fallbacks locais evitam chamadas quando o
            serviço não é necessário ou não está habilitado.
          </p>
        </Section>

        <Section title="Retenção, acesso e exclusão">
          <p>
            Guias recebem expiração padrão de 30 dias e rascunhos de 14 dias, ambos configuráveis
            pelo operador. Rascunhos são salvos no servidor somente para a conta autenticada e não
            incluem a foto: ela precisa ser reenviada antes da geração. O painel permite baixar e
            excluir cada guia; também há exportação e exclusão completa dos dados da conta.
          </p>
        </Section>

        <Section title="Segurança e seus direitos">
          <p>
            Downloads exigem autenticação e owner, uploads têm limites e o renderer de PDF não pode
            acessar a rede ou arquivos fora das raízes aprovadas. Durante o piloto, solicitações de
            acesso, correção, portabilidade ou exclusão devem ser tratadas pelo responsável que
            concedeu o acesso ao ambiente.
          </p>
        </Section>

        <p className="rounded-2xl border border-border bg-card p-5 text-sm text-muted-foreground">
          Consulte também os <Link className="font-bold text-primary underline" to="/terms">Termos de Uso</Link>.
          Esta política deverá passar por revisão jurídica antes de cobrança ou tráfego público.
        </p>
      </main>
    </div>
  </>
);

export default PrivacyPage;
