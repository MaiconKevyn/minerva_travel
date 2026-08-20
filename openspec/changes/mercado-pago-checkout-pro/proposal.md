# Change: Add Mercado Pago Checkout Pro payments

## Why

Minerva Travel currently allows guide generation without a real checkout. The product needs a secure one-time purchase flow for Brazilian customers before any paid AI generation is started.

## What Changes

- Add a server-owned guide product and price configuration.
- Create Mercado Pago Checkout Pro preferences from the authenticated backend.
- Persist payments and guide-generation entitlements with idempotent state transitions.
- Accept and validate Mercado Pago webhooks before confirming payment.
- Require a paid entitlement before cover or full-guide generation.
- Redirect the customer to hosted Checkout Pro and restore the guide after returning.
- Keep production charging disabled until production credentials, price, and webhook are explicitly configured.

## Impact

- Backend configuration, API routes, persistence, and Mercado Pago client.
- Frontend review, checkout, return, and payment-status experience.
- SQLite runtime schema and Supabase migration.
- Environment documentation and automated tests.

## Non-goals

- Subscriptions or recurring billing.
- A custom card form hosted by Minerva Travel.
- Automatic activation of Mercado Pago production credentials.
- Choosing the final commercial price without an explicit product decision.

