# Design: Mercado Pago Checkout Pro

## Context

The guide builder stores the uploaded photo and form before image generation. That makes the builder session the stable object to bind to a one-time purchase. Checkout Pro keeps card and Pix collection on Mercado Pago's hosted page, while Minerva Travel remains responsible for product price, order ownership, webhook validation, and entitlement enforcement.

## Decisions

### Create the builder before checkout

The frontend checkpoints a builder session first, then asks the backend for a checkout tied to that session. No paid provider generation is performed before checkout.

### Keep price and identity on the server

The checkout request contains only the builder session identifier. The backend derives the authenticated user, product code, currency, title, and amount from configuration. The browser never supplies a payable amount.

### Treat Mercado Pago as payment truth

Return URL query parameters never update local state by themselves. A payment becomes paid only after the corresponding payment is fetched from Mercado Pago and its amount, currency, external reference, and ownership are checked. This verification is normally initiated by a signed webhook; an authenticated owner return can initiate the same provider verification to recover when the webhook is delayed.

### Make state transitions idempotent

Payments have a local UUID used as Mercado Pago's external reference. Provider payment identifiers are unique, and one payment can issue at most one entitlement. Repeated notifications and checkout retries reuse safe local state.

### Bind one entitlement to one builder

An approved purchase creates an active guide-generation entitlement for its builder session. The first paid generation claims it; retries and subsequent pages for the same builder remain allowed, while another builder cannot reuse it.

### Separate test and production

Payments are disabled by default. Test credentials choose the sandbox checkout URL. Production activation requires explicit environment configuration and is not part of local implementation.

## Failure and recovery

- If preference creation fails, the local payment is marked failed and the user can retry.
- Pending payments are shown as pending and can be refreshed after a Pix payment.
- A delayed webhook can be recovered from the browser return without trusting
  the browser-reported status or amount.
- Cancelled or failed checkout returns to the same persisted builder and offers another attempt.
- Webhook retries are safe and do not duplicate entitlements.
- A paid entitlement remains recoverable after browser refresh or another authenticated device session.

## Security

- Access tokens and webhook secrets exist only on the backend.
- Checkout and status routes enforce builder/payment ownership.
- Webhook signatures use constant-time HMAC comparison.
- Logs and API responses never expose credentials or full provider payloads.
- Generation endpoints enforce entitlement server-side; the frontend button is only a convenience control.
