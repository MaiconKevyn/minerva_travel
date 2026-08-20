import React from 'react';
import { Helmet } from 'react-helmet';
import { Link } from 'react-router-dom';
import Header from '@/components/Header.jsx';

const TermsPage = () => (
  <>
    <Helmet>
      <title>Termos de Uso - Minerva Travel</title>
    </Helmet>
    <div className="min-h-screen bg-background text-foreground">
      <Header />
      <main id="main-content" tabIndex={-1} className="mx-auto max-w-3xl space-y-8 px-5 py-12 sm:px-8">
        <div className="space-y-4">
          <p className="text-sm font-bold uppercase tracking-widest text-primary">
            Versão 2026-08-19
          </p>
          <h1 className="text-4xl font-serif font-bold sm:text-5xl">Termos de Uso</h1>
          <p className="text-lg leading-8 text-muted-foreground">
            A Minerva Travel gera um diário de atividades infantil em PDF A4 a partir de dados
            confirmados pela família. O serviço não vende reservas, ingressos ou disponibilidade em
            tempo real.
          </p>
        </div>

        <section className="space-y-3 leading-7 text-muted-foreground">
          <h2 className="text-2xl font-serif font-bold text-foreground">Uso responsável</h2>
          <p>
            A conta deve ser usada por um adulto responsável. Quem envia nomes, idades ou foto
            declara possuir autorização para esse uso e não deve enviar conteúdo ilegal, abusivo ou
            que exponha crianças indevidamente.
          </p>
        </section>

        <section className="space-y-3 leading-7 text-muted-foreground">
          <h2 className="text-2xl font-serif font-bold text-foreground">Escopo e limitações</h2>
          <p>
            Sugestões de roteiro são material de planejamento e precisam de confirmação humana.
            Horários, preços, acessibilidade, segurança e regras locais podem mudar; confirme-os nas
            fontes oficiais antes da viagem. O PDF é voltado inicialmente a crianças de 3 a 12 anos.
          </p>
        </section>

        <section className="space-y-3 leading-7 text-muted-foreground">
          <h2 className="text-2xl font-serif font-bold text-foreground">Imagens e licenças</h2>
          <p>
            Fotos de atrações devem vir de fontes licenciadas e os créditos aplicáveis aparecem no
            guia. A foto familiar continua pertencendo à família e é processada apenas para entregar
            o guia solicitado, conforme a Política de Privacidade.
          </p>
        </section>

        <section className="space-y-3 leading-7 text-muted-foreground">
          <h2 className="text-2xl font-serif font-bold text-foreground">Cobrança e suporte</h2>
          <p>
            Quando o checkout estiver ativo, o preço total é exibido antes da compra e corresponde a
            um único guia personalizado. O pagamento é processado pelo Mercado Pago; a Minerva Travel
            não recebe os dados completos do cartão. Reembolsos e demais direitos obrigatórios seguem
            a legislação aplicável e o estado do pedido registrado no serviço.
          </p>
        </section>

        <p className="rounded-2xl border border-border bg-card p-5 text-sm text-muted-foreground">
          Leia a <Link className="font-bold text-primary underline" to="/privacy">Política de Privacidade</Link>.
          Estes termos devem ser revisados novamente antes da ativação das credenciais de produção.
        </p>
      </main>
    </div>
  </>
);

export default TermsPage;
