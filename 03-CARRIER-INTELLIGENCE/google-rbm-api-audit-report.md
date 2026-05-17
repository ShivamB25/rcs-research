# Google RCS Business Messaging (RBM) API — Full Audit Report

**Date:** 2026-05-15  
**Product:** RCS for Business (formerly RCS Business Messaging / RBM)  
**Platform:** Google Business Communications  
**Docs:** https://developers.google.com/business-communications/rcs-business-messaging  

---

## 1. Complete API Surface (REST Endpoints, Message Types)

### Service Endpoint
```
https://rcsbusinessmessaging.googleapis.com
```

### REST Resources & Methods

| Resource | Method | Endpoint | Description |
|----------|--------|----------|-------------|
| **v1.files** | `create` | `POST /v1/files` or `POST /upload/v1/files` | Upload a file for use in media or rich card messages |
| **v1.phones** | `getCapabilities` | `GET /v1/{name=phones/*}/capabilities` | Check if a user's device supports RCS for Business |
| **v1.phones.agentEvents** | `create` | `POST /v1/{parent=phones/*}/agentEvents` | Send an event (typing indicator, read receipt) from agent to user |
| **v1.phones.agentMessages** | `create` | `POST /v1/{parent=phones/*}/agentMessages` | Send a message from agent to user |
| **v1.phones.agentMessages** | `delete` | `DELETE /v1/{name=phones/*/agentMessages/*}` | Revoke an undelivered agent message |
| **v1.phones.dialogflowMessages** | `create` | `POST /v1/{parent=phones/*}/dialogflowMessages` | Prompt a Dialogflow agent to send messages via the RBM agent |
| **v1.users** | `batchGet` | `POST /v1/users:batchGet` | Get RCS-enabled phone numbers for a list of users |

### Message Types (Outbound from Agent)

| Message Type | Description | Key Features |
|---|---|---|
| **Standalone Rich Card** | Single card with image, title, description, and suggestions | Media, text, suggested replies, suggested actions |
| **Carousel Card** | Scrollable set of 2–10 rich cards | Multiple cards in a row, each with suggestions |
| **Rich Card + Suggestions** | Text + optional media + up to 4 suggested replies + up to 4 suggested actions | Interactive buttons, URL opens, dial actions |
| **Basic Text Message** | Plain text (≤160 chars) | Simple text with optional URL previews |
| **Single/Rich Media Message** | Text >160 chars or includes media | Full rich media support |
| **Agent Events** | Typing indicators, read receipts | User experience signals |

### Suggested Action Types
- `reply` — Suggested reply (chip)
- `openUrl` — Open URL in browser (http/https only)
- `dial` — Dial a phone number
- `shareLocation` — Request user to share location
- `openMap` — Open map to a location
- `createCalendarEvent` — Create a calendar event

### Message Size Limits
- **Overall message:** Limited by the combined size of all content
- **Text:** Up to 160 characters for Basic messages; unlimited for Single/Rich Media
- **Media files:** Must be uploaded via `/v1/files` first; typical limits apply for images (~3.8 MB)

---

## 2. Authentication Flow (Service Account → OAuth2 → API Calls)

### Step-by-Step Auth Flow

1. **Create a Google Cloud Project** with RCS for Business enabled.
2. **Create a Service Account** in the Google Cloud Console.
3. **Generate a Service Account Key** (JSON format) — download and store securely.
4. **Grant the Service Account access** to the RBM agent in the Business Communications Developer Console.
5. **Use the Service Account Key to obtain an OAuth2 Access Token:**
   - The client libraries handle JWT creation and token exchange automatically.
   - Manually: Create a signed JWT using the service account's private key, then exchange it for an access token at `https://oauth2.googleapis.com/token`.
6. **Include the OAuth2 Bearer Token** in the `Authorization` header of all API requests:
   ```
   Authorization: Bearer <access_token>
   ```

### Auth Details
- **Token lifetime:** ~1 hour; client libraries auto-refresh
- **Scopes required:** `https://www.googleapis.com/auth/rcsbusinessmessaging`
- **Key format:** JSON (RSA private key)
- **No user consent required** — service account auth is server-to-server

---

## 3. Pricing: Per-Message Costs for Conversational vs Non-Conversational Agents

### Agent Types & Billing Models

| Agent Category | Billing Model | How It Works |
|---|---|---|
| **Non-conversational Agent** (formerly Basic Message / Single Message) | **Per-message** | Each individual message is billed separately, similar to SMS. Best for one-way notifications, OTPs, alerts. |
| **Conversational Agent** | **Per 24-hour session** | A flat rate covers all messages exchanged within a 24-hour conversation window. Initiated when a user replies or the agent responds to a user message. |

### Message Type Pricing Tiers

| Message Type | US Market Name | Non-US Name | Billing (Non-Conversational) |
|---|---|---|---|
| **Tier 1: Text-only, ≤160 chars** | Rich Message | Basic Message | Lowest per-message rate |
| **Tier 2: Text >160 chars or includes media** | Rich Media Message | Single Message | Higher per-message rate (roughly 1.5–2× Tier 1) |
| **Tier 3: Conversation session** | Conversation | Conversation | Flat rate per 24-hour session (covers unlimited messages) |

### Conversational Billing Details
- **A2P Conversation:** Customer replies to your message within 24 hours → flat rate covers your original message + all messages in the 24-hour window.
- **P2A Conversation:** You reply to a customer's message within 24 hours → flat rate covers the customer's original message + all messages in the 24-hour window.
- **If no response within 24 hours:** Messages are billed individually (non-conversational rates).

### Important Pricing Notes
- **Google does NOT publish a public rate card.** Pricing is set by individual carriers and negotiated through RCS solution providers (partners).
- **Carrier-dependent:** Each carrier (AT&T, T-Mobile, Verizon, Vodafone, etc.) sets its own rates.
- **Regional variation:** US, EU, and APAC carriers price differently. No universal pricing exists.
- **Estimated US carrier rates (from third-party provider reports):**
  - Basic/Rich message: ~$0.01–$0.03 per message
  - Rich Media/Single message: ~$0.02–$0.05 per message
  - Conversational session: ~$0.05–$0.15 per 24-hour session
- **Migration note (2026):** Existing "Basic Message" and "Single Message" agents are being automatically migrated to the "Non-conversational" category by RBM Support.

### Cost per 1,000 Messages Comparison (Estimated)

| Channel | Cost per 1,000 msgs (US) |
|---|---|
| SMS (A2P 10DLC) | ~$1.50–$5.00 |
| RCS Basic/Non-conversational | ~$10–$30 |
| RCS Rich Media/Single | ~$20–$50 |
| RCS Conversational (1 session = 1 user interaction) | ~$50–$150 (but covers unlimited msgs per session) |
| WhatsApp Business (template) | ~$0.50–$5.00 |
| MMS | ~$2.00–$8.00 |

> ⚠️ **All RCS pricing is carrier-negotiated.** The above are estimates from third-party provider reports (Sinch, Plivo, Bandwidth). Actual rates require carrier contract negotiation.

---

## 4. Rate Limits and Max Throughput

### Official Documentation
Google does **not** publicly document specific rate limits for the RBM API in the official developer documentation. However, the following is known from best practices documentation and community reports:

### Known Constraints
- **Capability checks** (`getCapabilities`): Should be cached; excessive calls may be throttled.
- **Message sending:** No explicit published QPS limit, but Google enforces fair-use policies.
- **File uploads:** Standard Google Cloud upload limits apply.
- **Webhook delivery:** High message rates generate high webhook notification rates — systems must handle expected throughput.

### Best Practices for Throughput
- **Verify capabilities first** before sending to avoid 404 errors on non-RCS devices.
- **Implement exponential backoff** on 429 (rate limit) and 503 errors.
- **Use batch operations** (`users:batchGet`) for bulk capability checks.
- **Design webhook handlers for async processing** — return 200 OK within 5 seconds, process in background.
- **Webhook retry behavior:** Failed webhook deliveries use backoff retry up to 10-minute intervals, retrying for up to 7 days before permanent deletion.

### Approximate Practical Throughput (from third-party reports)
- Typical: **10–50 messages/second per agent** (varies by carrier and use case)
- High-volume campaigns: May need to coordinate with Google/carrier for increased limits
- Contact Google RBM support for specific throughput requirements

---

## 5. Webhook Setup for Inbound Messages

### Architecture
```
User → RCS App → Google RBM Platform → HTTPS POST → Partner Webhook → Agent Backend
```

### Webhook Configuration

**Two levels of webhooks:**
1. **Partner Webhook** — Applies to ALL agents under the partner account. Configure during partner account setup.
2. **Agent Webhook** — Per-agent override. Takes precedence over the partner webhook for that specific agent.

### Setup Steps
1. Open the [Business Communications Developer Console](https://business-communications.cloud.google.com/).
2. Navigate to agent → **Integrations** → **Webhook** → **Configure**.
3. Enter the webhook URL (must begin with `https://`).
4. Note the `clientToken` value (used for message verification).
5. Configure webhook to accept a `POST` request with `clientToken` and `secret`, return `200 OK` with `secret` as body.
6. Click **Verify** in the Developer Console.

### Message Verification
- Every inbound message includes an `X-Goog-Signature` header.
- Verify by: Base64-decode the payload → SHA512 HMAC using `clientToken` as key → Base64-encode → Compare with `X-Goog-Signature`.
- **Do NOT use IP allowlisting** — Google uses dynamic anycast IPs. Use Reverse DNS or signature verification instead.

### Critical Webhook Best Practices
- **Return 200 OK within 5 seconds** — always.
- **Process events asynchronously** — store in local queue, return 200 immediately.
- **Use separate accounts** for production vs. test agents (test failures can block the shared partner queue).
- **Failed deliveries** trigger backoff retries (up to 10-min intervals, 7-day max) that can block ALL agents on the shared Pub/Sub queue.

---

## 6. RBM Management API for Programmatic Agent Creation

### Overview
The **RBM Management API** replicates the capabilities of the RBM Developer Console. It is exposed as RCS extensions to Google's Business Communications API.

### Capabilities
- **Create and edit RBM agents** programmatically
- **Upload assets** (logos, images)
- **Submit agents for verification and launch**
- **Manage tester devices**
- **Configure webhooks**

### API Endpoint
Part of the Business Communications API:
```
https://businesscommunications.googleapis.com
```

### Use Cases
- **Aggregators/Partners** managing many brand agents at scale
- **Automated agent provisioning** workflows
- **CI/CD integration** for agent configuration

### Agent Lifecycle
```
Pending → Launched (if approved) 
           ↗ Rejected
           → Suspended → Reactivated
           → Terminated
```

### Note
- **Agents cannot be deleted** (for security reasons) — only suspended/terminated.
- **Brand verification** is required before launch — the brand point of contact must respond to a Google approval email.

---

## 7. Available SDKs with GitHub Links

### Official Client Libraries

| Language | Package | Repository / Source | Package Manager |
|---|---|---|---|
| **Node.js** | `@google/rcsbusinessmessaging` | [npm](https://www.npmjs.com/package/@google/rcsbusinessmessaging) | `npm install @google/rcsbusinessmessaging` |
| **Java** | `com.google.rbm:rbm-api-helper` (or `rcsbusinessmessaging`) | [Maven Central](https://central.sonatype.com/artifact/com.google.rbm/rcsbusinessmessaging) | Maven/Gradle |
| **Python** | Part of RBM samples | [GitHub samples](https://github.com/google-business-communications/) | pip (via samples) |
| **C# / .NET** | Part of RBM samples | [GitHub samples](https://github.com/google-business-communications/) | NuGet (via samples) |

### GitHub Repositories

| Repo | Description |
|---|---|
| [google-business-communications/rbm-java-client-v1](https://github.com/google-business-communications/rbm-java-client-v1) | Java SDK sample — send and receive messages |
| [google-business-communications/rbm-nodejs-client-v1](https://github.com/google-business-communications/rbm-nodejs-client-v1) | Node.js SDK sample — send and receive messages |
| [google-business-communications/rbm-java-kitchen-sink-agent](https://github.com/google-business-communications/rbm-java-kitchen-sink-agent) | Interactive Java sample exploring all RBM features |
| [google-business-communications/rbm-java-cap-check](https://github.com/google-business-communications/rbm-java-cap-check) | Java bulk capability check tool |
| [rcs-business-messaging/rbm-api-examples](https://github.com/rcs-business-messaging/rbm-api-examples) | Official open-source API examples (all languages) |
| [google-business-communications](https://github.com/google-business-communications) | Parent org — all Business Communications repos |

### Node.js Setup
```json
// package.json
"dependencies": {
  "@google/rcsbusinessmessaging": "^1.0.7"
}
```
```js
const rbmApiHelper = require('@google/rcsbusinessmessaging');
```

### Java Setup
```xml
<!-- pom.xml -->
<dependency>
  <groupId>com.google.rbm</groupId>
  <artifactId>rbm-api-helper</artifactId>
  <version>1.0.0</version>
</dependency>
```
```java
import com.google.rbm.RbmApiHelper;
```

---

## 8. SMS Fallback Mechanism

### How Fallback Works
1. Agent sends a message via the RBM API.
2. If the user's device **does not support RCS**, the API returns a **`404 Not Found`** error.
3. The agent **must implement its own fallback logic** to send via SMS or another channel.

### Key Points
- **RCS for Business does NOT automatically fall back to SMS.** The developer must implement the fallback.
- **Third-party providers** (Sinch, Bandwidth, Plivo, Vonage) offer managed RCS APIs that **do** include automatic SMS fallback — they handle the 404 → SMS relay internally.
- **Capability pre-check:** Use `phones.getCapabilities` to proactively determine if a device is RCS-capable before attempting to send.

### Fallback Flow (self-managed)
```
Send via RBM API → 200 OK → Delivered via RCS
                  → 404 → Send via SMS (your implementation)
                  → 403/other → Handle error
```

---

## 9. Geographic Availability

### Supported Countries (Primary Countries of Operation)
Per the partner registration form, the following countries are explicitly listed:

| Region | Countries |
|---|---|
| **Americas** | United States, Canada, Mexico, Brazil |
| **Europe, Middle East & Africa** | United Kingdom, France, Germany, Italy, Spain, Netherlands |
| **Asia Pacific** | India, Singapore |

### Carrier Support
- **US:** AT&T, T-Mobile, Verizon (major carriers)
- **UK/EU:** Vodafone, Orange, Deutsche Telekom, Telecom Italia, others
- **India:** Jio, Airtel, Vi (low-reputation promotional agents require user consent confirmation as of 2026)
- **Apple iOS:** iOS 26+ supports RCS, significantly expanding reach

### Partner Regions
- Americas
- Asia Pacific
- Europe, Middle East & Africa (EMEA)

### Reach Note
- RCS reach depends on carrier enablement. Not all carriers in all countries support RCS for Business.
- The `carriers` section of Google's docs provides an Admin Console for carrier-side management.
- Use `users:batchGet` to check which phone numbers are RCS-enabled in bulk.

---

## 10. Time from Signup to Production

### Registration & Launch Timeline

| Step | Estimated Time |
|---|---|
| **1. Submit Partner Interest Form** | Immediate |
| **2. Google Review & Approval** | **1–4 weeks** (varies; Google contacts you if qualified) |
| **3. Set up Partner Account** | 1–2 days (create service account, configure webhook, add testers) |
| **4. Build & Test Agent** | Days to weeks (depends on complexity) |
| **5. Brand Verification** (Google-managed launch) | **1–2 weeks** (requires brand POC to respond to approval email) |
| **6. Carrier Launch Approval** | **1–6 weeks** (varies by carrier; some carriers are faster) |
| **7. Agent goes live** | Immediate after approval |

### Total Estimated Time: **2–12 weeks**
- **Best case (US, simple agent):** ~2–3 weeks
- **Typical case:** 4–8 weeks
- **Worst case (international, complex brand verification):** 8–12+ weeks

### Key Delay Factors
- Brand POC not responding to verification email
- Carrier-specific review processes
- Complexity of agent (conversational agents may need more review)
- Multiple country launches require per-carrier approval

### Agent Status Flow
```
Pending → (Brand Verification) → (Carrier Review) → Launched
                                                        → Rejected
                                                        → Suspended → Reactivated
                                                        → Terminated
```

### Important Notes
- Agents **cannot be deleted** — only suspended or terminated.
- Test agents can be used immediately during the partner account setup phase (no launch approval needed for testing).
- Reddit/community reports indicate Italian launches can take 2+ months; US launches are typically faster.

---

## 11. Cost per 1,000 Messages — Summary Comparison

| Message Type | Est. Cost per 1,000 msgs (US) | Notes |
|---|---|---|
| RCS Basic/Non-conversational (text ≤160 chars) | **$10–$30** | Carrier-negotiated; similar tier to premium SMS |
| RCS Rich Media/Single (media or >160 chars) | **$20–$50** | Higher due to rich content |
| RCS Conversational (24-hour session) | **$50–$150** | Flat rate per session; covers unlimited messages |
| SMS (A2P 10DLC, US) | $1.50–$5.00 | Cheapest but least engaging |
| MMS (US) | $2.00–$8.00 | Media support but no branding/interactivity |
| WhatsApp Business (template msg) | $0.50–$5.00 | Varies by country; requires opt-in |
| WhatsApp Business (session msg) | $0.01–$0.10 | Within 24-hour customer-initiated window |

> ⚠️ All RCS costs are **carrier-specific and negotiable**. Contact your RCS solution provider or carrier for exact pricing.

---

## 12. Encryption & Security

- Messages are **encrypted in transit** between agents ↔ Google servers ↔ user devices.
- Partners **cannot use their own encryption keys** — Google needs to scan messages for malicious content.
- Google scans messages for **malicious content** to protect users and businesses.
- Webhook verification uses **SHA512 HMAC** with clientToken.
- **No IP allowlisting** recommended (Google uses dynamic anycast IPs).

---

## 13. Key Recent Changes (2025–2026)

| Date | Change |
|---|---|
| 2026-03 | Product renamed from "RCS Business Messaging (RBM)" to "RCS for Business" (no technical changes) |
| 2026-02 | Billing FAQ updated — Basic Message and Single Message agents migrating to "Non-conversational" category |
| 2026-05 | User consent confirmation required for low-reputation promotional agents in India |
| 2025 | `OpenUrlAction` restricted to http/https schemes only |
| 2025 | iOS 26+ RCS support broadens addressable user base significantly |

---

## 14. Third-Party RCS API Providers (Alternatives to Direct Google Integration)

These providers wrap the Google RBM API and add features like automatic SMS fallback, simplified onboarding, and consolidated billing:

| Provider | Key Differentiator | URL |
|---|---|---|
| **Sinch** | Global carrier relationships, Conversation API | https://sinch.com/messaging/rcs-for-business-api/ |
| **Bandwidth** | US-focused, direct carrier connections | https://www.bandwidth.com/products/rcs/ |
| **Plivo** | Pay-as-you-go pricing, AI Agent integration | https://www.plivo.com/rcs/ |
| **Vonage** | RCS API with unified messaging platform | https://developer.vonage.com/en/messages/concepts/rcs |
| **2Factor** | India-focused, enterprise RCS API | https://2factor.in/ |
| **Syniverse** | Global carrier, SDC documentation | https://sdcdocumentation.syniverse.com/ |

### Benefits of Using a Provider vs. Direct Google API
- **Automatic SMS fallback** (no 404 handling needed)
- **Simplified onboarding** (provider handles carrier negotiations)
- **Consolidated billing** across carriers
- **Unified API** across SMS, MMS, RCS, WhatsApp, etc.
- **Higher cost** per message vs. direct Google API access

---

## Sources

1. Google Developers — RCS for Business Documentation: https://developers.google.com/business-communications/rcs-business-messaging
2. Google Developers — RBM REST API Reference: https://developers.google.com/business-communications/rcs-business-messaging/reference/rest
3. Google Developers — Webhooks Guide: https://developers.google.com/business-communications/rcs-business-messaging/guides/integrate/webhooks
4. Google Developers — Client Libraries: https://developers.google.com/business-communications/rcs-business-messaging/reference/libraries
5. Google Developers — How RCS for Business Works: https://developers.google.com/business-communications/rcs-business-messaging/guides/get-started/how-it-works
6. Google Developers — Partner Registration: https://developers.google.com/business-communications/rcs-business-messaging/guides/get-started/register-partner
7. Sinch — RCS Business Message Types: https://sinch.com/blog/rcs-business-message-types/
8. Plivo — RCS Pricing Guide: https://www.plivo.com/blog/how-rcs-pricing-works/
9. GitHub — google-business-communications org: https://github.com/google-business-communications
10. GitHub — rcs-business-messaging org: https://github.com/rcs-business-messaging
