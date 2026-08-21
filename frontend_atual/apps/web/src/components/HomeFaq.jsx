import React from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';
import { GuideLockup } from '@/components/GuideLockup.jsx';
import { PHRASEBOOK_COUNTRIES } from '@/utils/landmark-activities.js';

/**
 * As perguntas que decidem a compra e que ninguém conseguia responder sem
 * criar uma conta antes: como o livro chega, o que acontece com a foto da
 * família e quanto custa. O valor em si vem do catálogo do backend na página
 * de preço, para não ficar desatualizado no conteúdo estático.
 *
 * `details/summary` nativo em vez do acordeão do Radix, de propósito: um FAQ
 * estático não precisa de JavaScript nenhum. Teclado, leitor de tela e busca
 * do navegador já funcionam de fábrica, nada quebra se o bundle falhar, e o
 * pai pode abrir duas respostas ao mesmo tempo para comparar — o acordeão
 * fecharia a anterior.
 */
const QUESTIONS = [
  {
    question: 'Como o guia chega até mim?',
    answer:
      'Como um PDF em tamanho A4, para você imprimir em casa ou levar a uma gráfica e encadernar. Não enviamos nada pelo correio.',
  },
  {
    question: 'Preciso mandar uma foto da família?',
    answer: (
      <>
        Não. A foto é opcional: com ela, a família pode inspirar a capa ilustrada; sem ela,
        criamos a composição a partir do roteiro e dos destinos. Se você enviar uma foto, ela é
        processada só para gerar a ilustração, não é usada para treinar modelos e esse uso depende
        da sua autorização explícita.
        Os detalhes estão na{' '}
        <Link className="font-bold text-primary underline underline-offset-4" to="/privacy">
          política de privacidade
        </Link>
        .
      </>
    ),
  },
  {
    question: 'Serve para que idades?',
    answer:
      'As atividades começam aos 4 anos e vão até a adolescência. Você informa a idade de cada criança e a dificuldade é calibrada a partir dela — o mesmo labirinto sai maior para quem tem 11 do que para quem tem 5.',
  },
  {
    question: 'E se eu não gostar da capa?',
    answer:
      'Você pode gerar outra versão da capa antes de aprová-la. Depois da aprovação, as demais páginas são criadas em segundo plano e o guia pronto aparece na sua biblioteca e chega por e-mail.',
  },
  {
    question: 'O guia fala sobre o idioma do país?',
    answer: `Quando a atividade "Sobrevivência no idioma" é escolhida, sim: a criança leva cinco frases para pedir sozinha, no idioma do destino. Hoje cobrimos ${PHRASEBOOK_COUNTRIES.size} países.`,
  },
  {
    question: 'Quanto custa?',
    answer: (
      <>
        O valor vigente e a disponibilidade do checkout aparecem na{' '}
        <Link className="font-bold text-primary underline underline-offset-4" to="/pricing">
          página de preço
        </Link>
        . É uma compra única por guia e os dados financeiros são processados pelo Mercado Pago.
        Em ambientes de piloto, o checkout pode permanecer desativado.
      </>
    ),
  },
];

const HomeFaq = () => (
  <section className="travel-page editorial-section py-16 sm:py-20" aria-labelledby="faq-title">
    <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
      <GuideLockup id="faq-title" overline="Antes de começar" title="Perguntas que todo pai faz" />

      <div className="mt-10 overflow-hidden rounded-xl border border-secondary/15 bg-[hsl(var(--paper))]">
        {QUESTIONS.map((item) => (
          <details
            key={item.question}
            className="group border-b border-secondary/15 px-5 py-1 transition-colors last:border-b-0 open:bg-[hsl(var(--mint)/0.45)] sm:px-6"
          >
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-4 font-serif text-lg font-bold text-foreground marker:content-none">
              {item.question}
              <ChevronDown
                className="h-5 w-5 shrink-0 text-primary transition-transform duration-200 group-open:rotate-180"
                aria-hidden="true"
              />
            </summary>
            <p className="editorial-copy pb-5 pr-9 text-base text-foreground/70">
              {item.answer}
            </p>
          </details>
        ))}
      </div>
    </div>
  </section>
);

export default HomeFaq;
