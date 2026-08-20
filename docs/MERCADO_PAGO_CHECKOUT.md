# Checkout Pro do Mercado Pago

O Minerva Travel usa compra única por guia com Checkout Pro hospedado. O
navegador nunca envia preço e nunca recebe o Access Token. O backend cria a
preferência, o Mercado Pago coleta cartão/Pix e a compra só é confirmada após
consulta e validação no provedor, antes de liberar a geração.

## Fluxo

1. A família termina o roteiro e o backend salva uma sessão do guia.
2. `POST /api/payments/checkout` cria ou reutiliza um pedido pendente ligado à
   sessão e devolve a URL hospedada do Mercado Pago.
3. O navegador sai para o Checkout Pro e volta para `/create` com os IDs locais.
4. A URL de retorno restaura a tela e pode acionar `POST
   /api/payments/{id-local}/refresh`. O backend não confia no status da URL:
   consulta `/v1/payments/{id-provider}` e confere valor, moeda e
   `external_reference` antes de atualizar o pedido.
5. Em paralelo, o Mercado Pago chama `POST /api/webhooks/mercado-pago`.
6. O backend valida `x-signature`, consulta novamente o pagamento no provedor
   e faz as mesmas conferências. As duas rotas são idempotentes.
7. Um único entitlement é emitido e vinculado à sessão. Só então a capa e o
   guia completo podem usar os provedores de geração.

## Ambiente de teste

Configure os valores abaixo apenas no secret store do backend ou no `.env`
local ignorado pelo Git:

```dotenv
APP_ENV=development
PAYMENTS_ENABLED=true
MERCADO_PAGO_ENVIRONMENT=test
MERCADO_PAGO_ACCESS_TOKEN=<access-token-de-teste>
MERCADO_PAGO_WEBHOOK_SECRET=<assinatura-webhook-de-teste>
MERCADO_PAGO_WEBHOOK_URL=https://<api-publica>/api/webhooks/mercado-pago
FRONTEND_BASE_URL=https://<frontend-publico>
GUIDE_PRODUCT_PRICE_MINOR=100
GUIDE_PRODUCT_CURRENCY=BRL
```

Use R$ 1,00 apenas no sandbox. O Mercado Pago não aceita `localhost` ou
`127.0.0.1` nas `back_urls`; para uma preferência real de teste, use o domínio
público do frontend ou um domínio HTTPS temporário. Nunca copie credenciais para arquivos
versionados, logs, frontend ou mensagens. A conta compradora de teste deve ser
diferente da conta vendedora de teste fornecida pelo Mercado Pago.

Sem uma URL HTTPS pública, é possível testar criação/redirecionamento do
checkout e testar o webhook localmente com payload assinado, mas a notificação
real do Mercado Pago não alcançará `localhost`.

## Ativação de produção

O preço comercial aprovado em 19 de agosto de 2026 é **R$ 19,99** por guia;
configure `GUIDE_PRODUCT_PRICE_MINOR=1999`. O valor de R$ 1,00 acima é exclusivo
do sandbox.

1. Defina e aprove o preço comercial e os termos/reembolso.
2. Aplique as migrações antes do backend novo.
3. Cadastre no painel a URL HTTPS exata do webhook e copie seu segredo para o
   secret store do backend.
4. Configure credenciais de produção e `MERCADO_PAGO_ENVIRONMENT=production`.
5. Faça deploy ainda com `PAYMENTS_ENABLED=false` e execute o smoke test.
6. Ative `PAYMENTS_ENABLED=true` e faça uma compra real de baixo valor.
7. Confirme pagamento, geração, download e reembolso/revogação do entitlement.

`APP_ENV=production` falha fechado se ambiente, token, segredo ou URL do webhook
estiverem incompletos. A ativação das credenciais e uma cobrança real são ações
operacionais deliberadas e não fazem parte do teste local.

## Diagnóstico seguro

- `GET /api/products/guide`: disponibilidade e preço público do servidor.
- `GET /api/payments/by-builder/{session_id}`: estado local para o dono.
- `POST /api/payments/{payment_id}/refresh`: reconciliação autenticada após o
  retorno; o ID recebido do navegador só é aceito depois da consulta e das
  validações no provedor.
- `402 guide_payment_required`: tentativa de geração ainda não liberada.
- `401 invalid_webhook_signature`: assinatura, request ID, data ID ou segredo
  não correspondem.
- `409 payment_confirmation_mismatch`: valor, moeda, referência ou vínculo do
  pagamento não correspondem ao pedido local.

Não registre o corpo completo da resposta do provider: ele pode conter dados do
pagador. Eventos do aplicativo usam apenas IDs pseudonimizados e estados.
