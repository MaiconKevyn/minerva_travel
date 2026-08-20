## 1. Change definition

- [x] 1.1 Define Checkout Pro requirements, state model, and security boundaries

## 2. Backend foundation

- [x] 2.1 Add payment configuration and Mercado Pago HTTP client
- [x] 2.2 Add SQLite payment and entitlement persistence
- [x] 2.3 Add a forward Supabase migration for payment-to-builder linkage

## 3. Payment API and enforcement

- [x] 3.1 Add product, checkout, status, and signed webhook routes
- [x] 3.2 Issue one idempotent entitlement for an approved payment
- [x] 3.3 Gate cover and full-guide generation on the builder entitlement
- [x] 3.4 Add authenticated provider reconciliation for delayed webhooks
- [x] 3.5 Gate legacy PDF delivery and revalidate entitlement in the worker

## 4. Frontend checkout

- [x] 4.1 Add payment API client functions and types
- [x] 4.2 Redirect from review to Checkout Pro and restore the builder on return
- [x] 4.3 Show paid, pending, failed, and retry states before generation
- [x] 4.4 Update product and pricing copy to match the payment-enabled behavior

## 5. Configuration and verification

- [x] 5.1 Document environment variables and safe production activation
- [x] 5.2 Add backend and frontend automated tests
- [x] 5.3 Run the focused and regression test suites
- [x] 5.4 Exercise the checkout flow directly in the application and record remaining production-only setup
