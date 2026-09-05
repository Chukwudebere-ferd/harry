# harry is a Telegram Verification API

## Overview

Telegram Verification API is a reusable authentication and notification infrastructure that allows applications to verify users through a Telegram bot.

The platform is designed as a multi-tenant API service. Multiple websites, applications, and developers can integrate with one central API to verify their users via Telegram.

The initial product focuses on **Telegram account verification without requiring users to manually copy and paste OTP codes**.

Instead of traditional verification:

```text
Website
   ↓
User enters phone number
   ↓
OTP is sent
   ↓
User copies OTP
   ↓
User enters OTP
   ↓
Verified
```

The system uses Telegram deep linking:

```text
Website
   ↓
User clicks "Verify with Telegram"
   ↓
Unique verification session is created
   ↓
User opens Telegram Bot
   ↓
Bot receives unique verification token
   ↓
Bot identifies Telegram user
   ↓
Verification session is completed
   ↓
Website automatically detects success
```

The unique verification session acts similarly to an OTP but provides a smoother user experience.

---

# Core Goals

The API should allow developers to:

* Verify users through Telegram
* Create reusable verification sessions
* Generate secure Telegram deep links
* Detect Telegram user identity
* Automatically complete verification
* Poll verification status
* Receive verification webhooks
* Send Telegram notifications after users connect
* Support multiple projects using API keys
* Track verification history
* Manage users and connected Telegram accounts

The platform should be designed for future expansion into a broader verification and notification service.

Future channels may include:

* Email
* SMS
* WhatsApp
* Push notifications
* Discord

However, the initial implementation should focus entirely on Telegram.

---

# Important Telegram Limitation

Telegram bots cannot arbitrarily send messages to users using:

* Telegram username
* Phone number
* Random Telegram account

For example, this is NOT possible:

```text
User enters: @john
        ↓
API finds Telegram account
        ↓
Bot sends OTP
```

Telegram does not expose a public Bot API endpoint for finding arbitrary users by username or phone number and messaging them.

A Telegram user must first interact with the bot.

Because of this limitation, the verification system should use a Telegram deep-link flow.

---

# Verification Architecture

The system consists of four major components:

```text
                    ┌─────────────────────┐
                    │    Client Project   │
                    │                     │
                    │ Website / Mobile App│
                    └──────────┬──────────┘
                               │
                               │ API Request
                               ▼
                    ┌─────────────────────┐
                    │                     │
                    │  Verification API   │
                    │                     │
                    │ Session Management  │
                    └──────────┬──────────┘
                               │
                               │ Telegram Deep Link
                               ▼
                    ┌─────────────────────┐
                    │                     │
                    │    Telegram Bot     │
                    │                     │
                    └──────────┬──────────┘
                               │
                               │ User Interaction
                               ▼
                    ┌─────────────────────┐
                    │                     │
                    │ Verification Engine │
                    │                     │
                    └──────────┬──────────┘
                               │
                  ┌────────────┴────────────┐
                  │                         │
                  ▼                         ▼
            Polling API                Webhook
                  │                         │
                  ▼                         ▼
             Client App                Client Backend
```

---

# Verification Flow

## Step 1: Client Creates Verification Session

A client application wants to verify one of its users.

The client sends a request to our API:

```http
POST /v1/verifications
Authorization: Bearer API_KEY
Content-Type: application/json
```

Request:

```json
{
  "external_user_id": "user_12345",
  "metadata": {
    "purpose": "account_verification"
  }
}
```

The `external_user_id` belongs to the client application.

Our API should not assume ownership of the client's user database.

---

# Step 2: Generate Verification Session

The API creates a verification session.

Example database record:

```json
{
  "id": "vrf_abc123",
  "project_id": "project_xyz",
  "external_user_id": "user_12345",
  "token": "secure_random_token",
  "status": "pending",
  "expires_at": "2026-09-05T10:30:00Z",
  "created_at": "2026-09-05T10:25:00Z"
}
```

The verification token must be cryptographically secure.

Do NOT use predictable values such as:

```text
verification_1
verification_2
verification_3
```

Instead use secure random tokens.

Example:

```text
vfy_x8Kp92LmQw71NzRt
```

The token should be:

* Cryptographically random
* Single use
* Short-lived
* Bound to a specific project
* Invalidated after successful verification

---

# Step 3: Return Verification URL

The API returns a response:

```json
{
  "id": "vrf_abc123",
  "status": "pending",
  "verification_url": "https://api.example.com/verify/vrf_abc123",
  "telegram_url": "https://t.me/ExampleVerifyBot?start=vfy_x8Kp92LmQw71NzRt",
  "expires_in": 300
}
```

The client application can either:

### Option A — Redirect directly to Telegram

```text
https://t.me/ExampleVerifyBot?start=TOKEN
```

### Option B — Use our hosted verification page

```text
https://api.example.com/verify/VERIFICATION_ID
```

The hosted verification page can display:

```text
Verify your account

Click the button below to continue.

[ Verify with Telegram ]
```

Clicking the button opens:

```text
https://t.me/ExampleVerifyBot?start=TOKEN
```

The hosted verification page is recommended because it provides a consistent user experience.

---

# Step 4: User Opens Telegram Bot

The user clicks:

```text
Verify with Telegram
```

Telegram opens the bot using the deep link:

```text
https://t.me/ExampleVerifyBot?start=vfy_x8Kp92LmQw71NzRt
```

Telegram sends an update to our bot containing something similar to:

```text
/start vfy_x8Kp92LmQw71NzRt
```

The bot receives the Telegram user's information.

Example:

```json
{
  "telegram_user_id": 123456789,
  "username": "exampleuser",
  "first_name": "John",
  "chat_id": 123456789
}
```

The important identifiers are:

```text
telegram_user_id
chat_id
```

The username should NOT be used as the primary identifier because users can change their usernames.

The Telegram User ID is the stable identifier.

---

# Step 5: Match User to Verification Session

The bot sends the deep-link token to the Verification API.

The API performs the following checks:

```text
Does token exist?
        ↓
Is token still valid?
        ↓
Has token expired?
        ↓
Has token already been used?
        ↓
Which project owns this token?
        ↓
Match Telegram user
        ↓
Mark verification successful
```

Database update:

Before:

```json
{
  "id": "vrf_abc123",
  "status": "pending",
  "telegram_user_id": null
}
```

After:

```json
{
  "id": "vrf_abc123",
  "status": "verified",
  "telegram_user_id": "123456789",
  "verified_at": "2026-09-05T10:27:00Z"
}
```

---

# Step 6: Store Telegram Connection

After successful verification, the system should store the Telegram connection.

Example:

```json
{
  "id": "tg_connection_xyz",
  "project_id": "project_xyz",
  "external_user_id": "user_12345",
  "telegram_user_id": "123456789",
  "chat_id": "123456789",
  "username": "exampleuser",
  "connected_at": "2026-09-05T10:27:00Z"
}
```

This allows future notifications.

For example, the client application can later send:

```text
Your withdrawal has been processed successfully.
```

directly to the user's Telegram account.

---

# Step 7: Notify Client Application

The client application needs to know when verification succeeds.

The API should support two primary methods:

1. Polling
2. Webhooks

---

# Method 1: Polling

The client repeatedly checks verification status.

Request:

```http
GET /v1/verifications/vrf_abc123
Authorization: Bearer API_KEY
```

Pending response:

```json
{
  "id": "vrf_abc123",
  "status": "pending"
}
```

Successful response:

```json
{
  "id": "vrf_abc123",
  "status": "verified",
  "verified_at": "2026-09-05T10:27:00Z"
}
```

Example frontend logic:

```javascript
const interval = setInterval(async () => {
  const response = await fetch(
    "/v1/verifications/vrf_abc123",
    {
      headers: {
        Authorization: `Bearer ${apiKey}`
      }
    }
  );

  const data = await response.json();

  if (data.status === "verified") {
    clearInterval(interval);

    // Continue user authentication flow
    console.log("User verified");
  }
}, 3000);
```

Recommended polling interval:

```text
2–5 seconds
```

Polling should stop when:

* Verification succeeds
* Verification expires
* User cancels

---

# Method 2: Webhooks

Clients can register a webhook URL.

Example project configuration:

```json
{
  "webhook_url": "https://clientapp.com/webhooks/telegram"
}
```

When verification succeeds, send:

```http
POST https://clientapp.com/webhooks/telegram
```

Payload:

```json
{
  "event": "verification.completed",
  "verification_id": "vrf_abc123",
  "external_user_id": "user_12345",
  "status": "verified",
  "timestamp": "2026-09-05T10:27:00Z"
}
```

Webhook events should include:

```text
verification.created
verification.completed
verification.expired
verification.failed
notification.sent
notification.failed
```

---

# Webhook Security

All webhooks must be signed.

Example headers:

```http
X-Webhook-ID: wh_evt_123
X-Webhook-Timestamp: 1725520000
X-Webhook-Signature: sha256=abc123
```

The signature should be generated using the project's webhook secret.

Example concept:

```text
signature = HMAC_SHA256(
    webhook_secret,
    timestamp + "." + raw_request_body
)
```

Clients can verify that the webhook originated from our API.

---

# API Authentication

Every client project should have its own API credentials.

Example:

```text
pk_live_xxxxxxxxxxxxx
sk_live_xxxxxxxxxxxxx
```

Recommended:

```text
Publishable Key
Secret Key
Webhook Secret
```

Secret keys must never be exposed in frontend applications.

For browser integrations, consider using:

* Backend-generated verification sessions
* Short-lived client tokens
* Verification session public IDs

Do not encourage developers to expose permanent secret API keys in frontend JavaScript.

---

# Multi-Tenant Architecture

The system must support multiple client applications.

Example:

```text
Developer A
 ├── Project A
 ├── Project B
 └── Project C

Developer B
 ├── Project X
 └── Project Y
```

Every verification session belongs to a project.

Architecture:

```text
Account
   │
   ├── Project
   │      │
   │      ├── API Keys
   │      ├── Webhook Configuration
   │      ├── Verification Sessions
   │      └── Telegram Connections
   │
   └── Project
          │
          ├── API Keys
          └── Verification Sessions
```

Never allow one project to access:

* Another project's verification sessions
* Another project's Telegram connections
* Another project's notifications

Every database query must be scoped by:

```text
project_id
```

---

# Core API Endpoints

## Create Verification

```http
POST /v1/verifications
```

Request:

```json
{
  "external_user_id": "user_12345",
  "metadata": {
    "purpose": "signup"
  }
}
```

Response:

```json
{
  "id": "vrf_abc123",
  "status": "pending",
  "verification_url": "https://api.example.com/verify/vrf_abc123",
  "telegram_url": "https://t.me/ExampleVerifyBot?start=TOKEN",
  "expires_at": "2026-09-05T10:30:00Z"
}
```

---

## Get Verification Status

```http
GET /v1/verifications/{verification_id}
```

Response:

```json
{
  "id": "vrf_abc123",
  "status": "verified",
  "external_user_id": "user_12345",
  "verified_at": "2026-09-05T10:27:00Z"
}
```

Possible statuses:

```text
pending
verified
expired
failed
cancelled
```

---

## Cancel Verification

```http
POST /v1/verifications/{verification_id}/cancel
```

Response:

```json
{
  "id": "vrf_abc123",
  "status": "cancelled"
}
```

---

## Resend / Create New Session

Do not reuse expired tokens.

Create a new verification session.

```http
POST /v1/verifications/{verification_id}/retry
```

Response:

```json
{
  "id": "vrf_new123",
  "status": "pending",
  "telegram_url": "https://t.me/ExampleVerifyBot?start=NEW_TOKEN"
}
```

---

# Telegram Connections

Once a user has successfully verified, the project has a connection to that Telegram account.

## Get Connection

```http
GET /v1/telegram/connections/{external_user_id}
```

Response:

```json
{
  "connected": true,
  "telegram_user_id": "123456789",
  "connected_at": "2026-09-05T10:27:00Z"
}
```

Do not expose unnecessary private Telegram information.

---

# Notifications API

After verification, clients should be able to send notifications.

## Send Notification

```http
POST /v1/notifications
```

Request:

```json
{
  "external_user_id": "user_12345",
  "channel": "telegram",
  "message": "Your withdrawal has been processed successfully."
}
```

API process:

```text
Receive Request
       ↓
Validate API Key
       ↓
Find Project
       ↓
Find User Telegram Connection
       ↓
Find chat_id
       ↓
Send Telegram Message
       ↓
Store Delivery Log
       ↓
Return Result
```

Response:

```json
{
  "id": "ntf_abc123",
  "status": "sent",
  "channel": "telegram"
}
```

---

# Notification Templates

In the future, support reusable templates.

Example:

```text
withdrawal_success
```

Template:

```text
Hello {{name}},

Your withdrawal of {{amount}} has been processed successfully.
```

API request:

```json
{
  "external_user_id": "user_12345",
  "template": "withdrawal_success",
  "variables": {
    "name": "John",
    "amount": "₦50,000"
  }
}
```

---

# Database Design

Recommended database: PostgreSQL.

Recommended caching/session storage: Redis.

---

## Users Table

```sql
users
```

Fields:

```text
id
email
password_hash
name
created_at
updated_at
```

This table represents API platform users/developers.

---

## Projects Table

```sql
projects
```

Fields:

```text
id
user_id
name
slug
status
created_at
updated_at
```

Example:

```text
id: project_xyz
name: My Fintech App
user_id: developer_123
```

---

## API Keys Table

```sql
api_keys
```

Fields:

```text
id
project_id
key_hash
key_prefix
type
last_used_at
expires_at
created_at
revoked_at
```

Never store raw API keys.

Store only a secure hash.

Example displayed prefix:

```text
sk_live_abc...
```

---

## Verification Sessions Table

```sql
verification_sessions
```

Fields:

```text
id
project_id
external_user_id
token_hash
status
metadata
expires_at
verified_at
created_at
updated_at
```

Recommended statuses:

```text
pending
verified
expired
failed
cancelled
```

---

## Telegram Connections Table

```sql
telegram_connections
```

Fields:

```text
id
project_id
external_user_id
telegram_user_id
chat_id
username
first_name
connected_at
last_active_at
created_at
updated_at
```

Recommended unique constraint:

```text
(project_id, external_user_id)
```

This ensures one active Telegram connection per client user.

---

## Notifications Table

```sql
notifications
```

Fields:

```text
id
project_id
external_user_id
channel
message
status
telegram_message_id
error_message
sent_at
created_at
```

Statuses:

```text
queued
processing
sent
failed
```

---

## Webhook Endpoints Table

```sql
webhook_endpoints
```

Fields:

```text
id
project_id
url
secret_hash
events
status
created_at
updated_at
```

---

## Webhook Deliveries Table

```sql
webhook_deliveries
```

Fields:

```text
id
webhook_endpoint_id
event
payload
response_status
attempt_count
status
next_retry_at
created_at
delivered_at
```

---

# Redis Usage

Redis should be used for temporary and high-frequency operations.

Recommended uses:

```text
Verification token cache
Rate limiting
Polling limits
Temporary sessions
Webhook retry queues
Distributed locks
```

Example verification session:

```text
verification:vfy_x8Kp92LmQw71
```

TTL:

```text
300 seconds
```

After successful verification:

```text
Delete Redis session
```

The permanent record remains in PostgreSQL.

---

# Telegram Bot Flow

The bot should be simple.

Primary responsibility:

```text
Receive deep-link token
        ↓
Identify Telegram user
        ↓
Send data to Verification API
        ↓
Confirm successful verification
```

Example interaction:

User opens:

```text
https://t.me/ExampleVerifyBot?start=TOKEN
```

Bot receives:

```text
/start TOKEN
```

Bot response:

```text
Verifying your account...
```

Backend validates token.

Successful response:

```text
✅ Account successfully verified.

You can return to the application.
```

The website should automatically detect success.

The user should not need to manually enter an OTP.

---

# Telegram Bot Webhook

Telegram should send bot updates to:

```text
POST /internal/telegram/webhook
```

The webhook handler should:

1. Validate incoming Telegram update
2. Detect `/start TOKEN`
3. Extract token
4. Extract Telegram user information
5. Send verification request to internal verification service
6. Mark session verified
7. Send confirmation message

Architecture:

```text
Telegram
    │
    ▼
Bot Webhook
    │
    ▼
Telegram Update Parser
    │
    ▼
Extract /start TOKEN
    │
    ▼
Verification Service
    │
    ├── Validate Token
    ├── Check Expiration
    ├── Check Usage
    ├── Identify Project
    └── Complete Verification
             │
             ▼
      Save Connection
             │
             ▼
      Trigger Webhook
```

---

# Security Requirements

Security is extremely important because this API will be responsible for authentication-related operations.

## Token Security

Verification tokens must:

* Use cryptographically secure random generation
* Be at least 128 bits of entropy
* Expire quickly
* Be single-use
* Never be predictable
* Be invalidated after success

Recommended expiration:

```text
5 minutes
```

---

## Token Storage

Do not store raw verification tokens if avoidable.

Store:

```text
SHA-256(token)
```

When the bot receives the token:

```text
Received Token
       ↓
SHA-256
       ↓
Find matching hash
```

---

## API Key Security

Never store raw secret API keys.

Generate:

```text
sk_live_random_secret
```

Store:

```text
SHA-256(secret)
```

Only show the full secret once during creation.

---

## Rate Limiting

Rate limit:

```text
Verification creation
Verification polling
Notification sending
API key authentication attempts
Webhook retries
Telegram webhook processing
```

Example:

```text
POST /verifications

20 requests / minute / project
```

Adjust limits depending on production requirements.

---

# Verification Abuse Prevention

Attackers may attempt to generate thousands of verification sessions.

Implement:

* Project-level rate limits
* IP-based limits where applicable
* Daily usage quotas
* Maximum concurrent pending sessions
* Automatic expiration
* Bot interaction monitoring

Example:

```text
Maximum pending verification sessions per project: 100
```

---

# Idempotency

Support idempotency for critical POST requests.

Client sends:

```http
Idempotency-Key: random_uuid
```

If the request is accidentally sent twice:

```text
Same request
       ↓
Same idempotency key
       ↓
Return original result
```

Do not create duplicate verification sessions.

Important endpoints:

```text
POST /verifications
POST /notifications
```

---

# Webhook Retry System

Webhook delivery may fail.

Implement retry logic.

Example:

```text
Attempt 1 → Immediately
Attempt 2 → 30 seconds
Attempt 3 → 2 minutes
Attempt 4 → 10 minutes
Attempt 5 → 1 hour
```

After maximum attempts:

```text
status = failed
```

Store all delivery attempts.

---

# Project Dashboard

The API should eventually include a developer dashboard.

Features:

## Dashboard

```text
Total Verifications
Successful Verifications
Failed Verifications
Pending Verifications
Notifications Sent
Webhook Success Rate
```

---

## Project Management

Developers can:

* Create projects
* Delete projects
* Generate API keys
* Revoke API keys
* Configure webhooks
* View usage
* View logs

---

## Verification Logs

Display:

```text
Verification ID
External User ID
Status
Created At
Verified At
Expiration
```

---

## Notification Logs

Display:

```text
Notification ID
Recipient
Channel
Status
Sent At
Error
```

---

# Suggested Technology Stack

## Backend

Recommended:

```text
Python
FastAPI
```

FastAPI is suitable because the platform is API-first and will require asynchronous processing.

---

## Database

```text
PostgreSQL
```

Use PostgreSQL for:

* Projects
* API keys
* Verification records
* Telegram connections
* Notifications
* Webhooks

---

## Cache

```text
Redis
```

Use Redis for:

* Temporary verification sessions
* Rate limiting
* Queues
* Caching
* Distributed locks

---

## Background Workers

Recommended options:

```text
Celery
ARQ
Dramatiq
```

Background jobs:

* Sending notifications
* Webhook delivery
* Webhook retries
* Session expiration cleanup
* Analytics aggregation

---

# Suggested Project Structure

```text
telegram-verification-api/
│
├── app/
│   │
│   ├── main.py
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── verifications.py
│   │       ├── notifications.py
│   │       ├── projects.py
│   │       ├── api_keys.py
│   │       └── webhooks.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── rate_limit.py
│   │   └── dependencies.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── api_key.py
│   │   ├── verification.py
│   │   ├── telegram_connection.py
│   │   ├── notification.py
│   │   └── webhook.py
│   │
│   ├── schemas/
│   │   ├── verification.py
│   │   ├── notification.py
│   │   └── webhook.py
│   │
│   ├── services/
│   │   ├── verification_service.py
│   │   ├── telegram_service.py
│   │   ├── notification_service.py
│   │   └── webhook_service.py
│   │
│   ├── repositories/
│   │   ├── verification_repository.py
│   │   └── telegram_repository.py
│   │
│   ├── workers/
│   │   ├── notification_worker.py
│   │   └── webhook_worker.py
│   │
│   └── bot/
│       ├── handler.py
│       └── commands.py
│
├── migrations/
│
├── tests/
│
├── docker/
│
├── docker-compose.yml
│
├── requirements.txt
│
└── README.md
```

---

# Internal Service Separation

Do not put all business logic directly inside API route handlers.

Bad:

```python
@app.post("/verifications")
async def create_verification():
    # Generate token
    # Insert database
    # Call Telegram
    # Send webhook
    # Everything here
```

Preferred:

```text
API Route
    ↓
Verification Service
    ↓
Repository Layer
    ↓
Database
```

The API route should primarily:

```text
Validate request
        ↓
Authenticate project
        ↓
Call service
        ↓
Return response
```

Business logic belongs inside services.

---

# Verification State Machine

Verification sessions should follow controlled state transitions.

```text
                 ┌─────────┐
                 │ Pending │
                 └────┬────┘
                      │
          ┌───────────┼───────────┐
          │           │           │
          ▼           ▼           ▼
      Verified      Expired      Cancelled
```

Optional failure state:

```text
Pending
   │
   ▼
Failed
```

Once verified:

```text
Verified
   │
   └── Cannot transition again
```

Never allow:

```text
Verified → Pending
```

---

# Important Privacy Rules

The platform should collect only necessary Telegram data.

Required:

```text
telegram_user_id
chat_id
username (optional)
first_name (optional)
```

Do NOT attempt to collect:

* Telegram passwords
* Telegram authentication codes
* Telegram session files
* Telegram API credentials from users

The system is verifying that a user controls a Telegram account interacting with the bot.

It is NOT authenticating directly into the user's Telegram account.

---

# Future Architecture

The project should be designed so Telegram is a provider rather than hardcoded everywhere.

Recommended abstraction:

```text
Verification Provider
        │
        ├── Telegram Provider
        │
        ├── Email Provider
        │
        ├── SMS Provider
        │
        └── WhatsApp Provider
```

Example interface:

```python
class VerificationProvider:

    async def start_verification(self):
        pass

    async def verify(self):
        pass

    async def send_notification(self):
        pass
```

Telegram implementation:

```python
class TelegramProvider(VerificationProvider):
    ...
```

Future:

```python
class EmailProvider(VerificationProvider):
    ...
```

This prevents rewriting the entire system when additional channels are added.

---

# API Versioning

All public endpoints should be versioned.

Example:

```text
/v1/verifications
/v1/notifications
/v1/projects
```

Future breaking changes:

```text
/v2/verifications
```

Never silently introduce breaking changes into an existing API version.

---

# Error Format

Use a consistent error format.

Example:

```json
{
  "error": {
    "code": "VERIFICATION_EXPIRED",
    "message": "This verification session has expired."
  }
}
```

Recommended error codes:

```text
INVALID_API_KEY
PROJECT_NOT_FOUND
VERIFICATION_NOT_FOUND
VERIFICATION_EXPIRED
VERIFICATION_ALREADY_USED
INVALID_VERIFICATION_TOKEN
TELEGRAM_NOT_CONNECTED
RATE_LIMIT_EXCEEDED
NOTIFICATION_FAILED
WEBHOOK_DELIVERY_FAILED
```

---

# Success Response Format

Use predictable responses.

Example:

```json
{
  "success": true,
  "data": {
    "id": "vrf_abc123",
    "status": "pending"
  }
}
```

Or use a REST-standard direct resource response.

Choose one format and remain consistent across the entire API.

---

# Development Phases

## Phase 1 — Core MVP

Build:

* User authentication
* Projects
* API keys
* Telegram bot
* Verification sessions
* Telegram deep links
* Verification status endpoint
* Basic polling
* Telegram connection storage

Goal:

```text
Any developer can create a verification session
        ↓
Receive Telegram deep link
        ↓
User opens bot
        ↓
Verification completes
        ↓
Developer detects success
```

---

## Phase 2 — Webhooks

Build:

* Webhook endpoint configuration
* Event system
* Webhook signing
* Retry system
* Delivery logs

---

## Phase 3 — Notifications

Build:

```text
POST /notifications
```

Allow projects to send messages to previously connected Telegram users.

Include:

* Delivery status
* Retry handling
* Notification logs

---

## Phase 4 — Developer Dashboard

Build:

* Authentication
* Project management
* API key management
* Webhook management
* Usage analytics
* Verification logs
* Notification logs

---

## Phase 5 — SDKs

Create official SDKs.

Priority:

```text
JavaScript / Node.js
Python
PHP
```

Example JavaScript SDK:

```javascript
const verify = new VerifyAPI({
  apiKey: process.env.VERIFY_API_KEY
});

const session = await verify.verifications.create({
  externalUserId: "user_12345"
});

console.log(session.telegramUrl);
```

---

# Complete Example Integration

## Client Backend

```javascript
const response = await fetch(
  "https://api.example.com/v1/verifications",
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.API_KEY}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      external_user_id: user.id,
      metadata: {
        purpose: "signup"
      }
    })
  }
);

const verification = await response.json();
```

Response:

```json
{
  "id": "vrf_abc123",
  "status": "pending",
  "telegram_url": "https://t.me/ExampleVerifyBot?start=TOKEN"
}
```

---

## Client Frontend

```javascript
window.location.href = verification.telegram_url;
```

Or:

```html
<a href="TELEGRAM_URL">
  Verify with Telegram
</a>
```

---

## Telegram Bot

User opens:

```text
https://t.me/ExampleVerifyBot?start=TOKEN
```

Bot receives:

```text
/start TOKEN
```

Bot calls internal verification service:

```text
complete_verification(
    token=TOKEN,
    telegram_user_id=user.id,
    chat_id=chat.id
)
```

Verification service:

```text
Validate token
      ↓
Find verification session
      ↓
Check expiry
      ↓
Check status
      ↓
Attach Telegram account
      ↓
Mark verified
      ↓
Store connection
      ↓
Trigger webhook
```

---

# Final Product Definition

The product should be understood as:

> A developer-focused verification and notification API that allows applications to connect and verify users through Telegram using secure deep-link sessions.

The primary verification flow is:

```text
CLIENT APPLICATION
        │
        │ Create Verification
        ▼
VERIFICATION API
        │
        │ Generate Secure Session
        ▼
TELEGRAM DEEP LINK
        │
        │ User Opens Bot
        ▼
TELEGRAM BOT
        │
        │ Identifies Telegram User
        ▼
VERIFICATION ENGINE
        │
        ├── Mark Verified
        ├── Save Telegram Connection
        ├── Trigger Webhook
        │
        ▼
CLIENT APPLICATION
        │
        ▼
   USER VERIFIED
```

---

# Guiding Principles

The implementation should prioritize:

1. Security
2. Multi-tenancy
3. API consistency
4. Developer experience
5. Scalability
6. Privacy
7. Provider abstraction
8. Reliable webhook delivery
9. Simple integration
10. Future extensibility

The goal is not simply to build a Telegram bot.

The goal is to build reusable infrastructure that allows **any application to use Telegram as a verification and notification channel through a simple API**.
