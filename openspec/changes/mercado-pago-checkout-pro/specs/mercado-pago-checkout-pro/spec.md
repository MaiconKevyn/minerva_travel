## ADDED Requirements

### Requirement: Server-authoritative guide product

The system SHALL derive the guide product code, currency, title, and payable amount exclusively from backend configuration.

#### Scenario: Client attempts to choose an amount

- **WHEN** an authenticated client requests checkout for a builder session
- **THEN** the server ignores any client price and uses its configured product catalog

### Requirement: Authenticated checkout bound to a builder

The system SHALL create or reuse a Checkout Pro preference only for a builder session owned by the authenticated user.

#### Scenario: Owner starts checkout

- **WHEN** the builder owner requests checkout for an unpaid builder
- **THEN** the backend creates a local pending payment and returns a Mercado Pago hosted checkout URL

#### Scenario: Another user targets the builder

- **WHEN** an authenticated user requests checkout or status for a builder owned by someone else
- **THEN** the system returns not found or forbidden without disclosing payment data

### Requirement: Hosted Mercado Pago checkout

The system SHALL collect card, Pix, and other enabled payment details only on Mercado Pago's hosted Checkout Pro experience.

#### Scenario: Customer has no Mercado Pago account

- **WHEN** Mercado Pago allows guest checkout for the selected method
- **THEN** the customer can pay without Minerva Travel requiring a Mercado Pago account

### Requirement: Verified payment confirmation

The system SHALL confirm payment only after provider-side payment retrieval and local amount, currency, and external-reference validation, initiated either by a valid webhook or an authenticated owner recovery request.

#### Scenario: Browser returns approved status

- **WHEN** the browser return URL claims that payment was approved
- **THEN** the claim alone cannot update local state and the server retrieves and validates the payment with the provider before any entitlement is issued

#### Scenario: Notification is repeated

- **WHEN** Mercado Pago delivers the same approved payment more than once
- **THEN** the system keeps one paid payment and one entitlement

### Requirement: Paid entitlement gates generation

The system SHALL require an entitlement bound to the builder before starting cover generation, full-guide generation, PDF assembly, or final delivery when payments are enabled. The worker SHALL revalidate that entitlement while processing so a refund revokes unfinished delivery.

#### Scenario: Unpaid builder requests generation

- **WHEN** an unpaid builder requests a cover attempt or full-guide generation
- **THEN** the server rejects the operation without calling the generation provider

#### Scenario: Paid builder retries generation

- **WHEN** a paid builder retries or generates subsequent pages for the same guide
- **THEN** the claimed entitlement remains valid for that builder

#### Scenario: Payment is refunded before delivery finishes

- **WHEN** Mercado Pago reports a refund while a guide is still being processed
- **THEN** the entitlement is revoked and subsequent generation or final delivery is rejected

### Requirement: Checkout recovery

The system SHALL preserve the builder across checkout and expose an authenticated local payment status for return, refresh, and retry flows.

#### Scenario: Pix remains pending

- **WHEN** the customer returns before Pix confirmation
- **THEN** the application shows a pending state and can refresh local status without trusting query parameters

#### Scenario: Webhook is delayed

- **WHEN** the owner returns with a provider payment identifier before the webhook arrives
- **THEN** the server verifies that payment directly with Mercado Pago and confirms it only when its external reference, amount, and currency match the owner's local order

### Requirement: Safe activation

The system SHALL keep payment enforcement disabled unless explicitly enabled and SHALL distinguish sandbox and production checkout URLs.

#### Scenario: Credentials are absent

- **WHEN** payments are disabled or required credentials are missing
- **THEN** existing non-payment pilot behavior remains available in disabled mode and enabled mode fails closed with a configuration error
