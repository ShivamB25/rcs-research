# RCS API Provider Pricing Comparison — Comprehensive Report

**Date:** 2026-05-15  
**Scope:** Global RCS business messaging API providers, with India-specific deep-dive

---

## Executive Summary

RCS pricing is **not standardized** — it varies by carrier, region, message type, and volume. There is no universal rate card. The 3-tier pricing architecture (Basic → Single/Rich → Conversational) is common across all providers, dictated by Google's RBM platform and mobile carrier agreements. The cheapest path depends heavily on your geography, message volume, and whether you need 1-way alerts or 2-way conversations.

---

## 1. RCS Pricing Tiers (Universal Architecture)

All major providers follow Google's 3-tier billing model:

| Tier | Type | Description | Billing |
|------|------|-------------|---------|
| **1. Basic** | Text-only, ≤160 chars | SMS-like with branded profile & verification | Per message |
| **2. Single/Rich** | Rich cards, media, >160 chars | Product images, carousels, buttons, video | Per message (non-conversational) |
| **3. Conversational** | 2-way session, 24hr window | Customer support, interactive flows | Per conversation (A2P or P2A) |

- **A2P conversation** = business initiates, customer replies within 24hrs → flat session fee
- **P2A conversation** = customer initiates → flat session fee for 24hrs of unlimited messages
- If customer does NOT reply → individual message charges apply

---

## 2. Provider Comparison Table

### 2A. Global/US-Focused Providers

| Provider | Basic Msg (1-way text) | Rich/Single Msg | Conversation (24hr) | Min Monthly Spend | Setup Fees | SMS Fallback | Brand Registration Fees | Rate Limits/Throughput | Geo Coverage |
|----------|----------------------|------------------|---------------------|-------------------|------------|--------------|------------------------|----------------------|--------------|
| **AWS End User Messaging** | ~$0.01–0.03/segment + carrier fee | Same (Rich RCS, per 160-char segment) | Carrier-dependent (session-based) | None (pay-as-you-go) | One-time agent setup + annual brand vetting + monthly agent maintenance (all carrier pass-through) | Included; charged only for SMS if RCS fails | Yes (carrier pass-through, ~$15–50 setup, ~$5–15/mo maintenance) | Default AWS quotas (increasable) | US, Canada (expanding) |
| **Twilio** | ~$0.01–0.05/msg (pay-as-you-go) | ~$0.03–0.08/msg | Conversational pricing TBD | None | None (GA since Aug 2025) | Included (automatic fallback) | Carrier pass-through fees apply | High (enterprise-grade) | US, EU, select markets |
| **Sinch** | $0.01–0.05/msg (varies by carrier) | $0.03–0.10/msg | Per-conversation available | None (pay-as-you-go) | Custom (contact sales) | Included | Carrier-dependent | Enterprise-grade | 100+ countries via carrier aggregation |
| **Infobip** | $0.01–0.06/msg (region-dependent) | $0.03–0.12/msg | Per-conversation (A2P/P2A) | Custom plans available | Custom (free trial credits) | Included | Carrier pass-through | High | 190+ countries, 800+ carrier connections |
| **Vonage** | $0.01–0.05/msg | $0.03–0.10/msg | Per-conversation available | None (pay-as-you-go) | None | Included (Messages API) | Carrier-dependent | Medium-High | 200+ countries |
| **Plivo** | $0.01–0.04/msg (competitive) | $0.03–0.08/msg | Per-conversation (3-tier model) | None ($10 free trial) | None | Included | Carrier pass-through | High | 200+ countries |
| **Bandwidth** | ~$0.004–0.01/msg (SMS-like base) + carrier surcharges | Carrier surcharge applies | Session-based available | Volume-based pricing | Custom | Native US carrier — fallback built-in | Carrier pass-through surcharges | Very high (own US carrier network) | US-focused, expanding |
| **Syniverse** | Custom quote (carrier-dependent) | Custom quote | Per-delivered or 24hr session | Custom (enterprise) | Custom (enterprise contracts) | Included | Carrier-dependent | Enterprise-grade | 200+ countries (carrier settlement hub) |
| **Decision Telecom** | $0.01–0.05/msg | $0.03–0.10/msg | Per-conversation | Pay-as-you-go or volume tiers | None | Included | Carrier-dependent | Medium-High | Global via carrier aggregation |
| **TXTImpact** | ~$0.02–0.05/msg | ~$0.04–0.10/msg | Per-conversation available | No contract required | No setup fee | Included | None (managed) | Medium | US, Canada, UK, India |

### 2B. India-Focused Providers (DLT-Compliant)

| Provider | Price/Msg (Basic) | Price/Msg (Rich) | Setup Cost | Min Commitment | SMS Fallback | DLT Compliant | Notes |
|-----------|-------------------|------------------|-----------|---------------|--------------|---------------|-------|
| **WABA Connect** | ₹0.10 | ₹0.12 | None (demo + volume pricing) | None | Yes | Yes | Cheapest listed price; Google/Meta partner |
| **MSG91** | ₹0.12 (promo/txn) | ₹0.14 (rich template) | ₹2,000/mo min plan | ₹2,000/mo | Yes | Yes | Very competitive; wallet-based |
| **2Factor** | ₹0.16–0.20 | ₹0.20+ | ₹500 bot setup | None | Yes | Yes | Simple pricing, good for OTP/txn |
| **SMSGatewayHub** | ₹0.18–0.40 (volume-based) | Volume-based | None (pay-as-you-go) | None | Yes | Yes | True pay-as-you-go, transparent |
| **Botsense** | ₹0.30 | ₹0.35+ | ₹14,999/yr platform fee | Annual commitment | Yes | Yes | Higher but includes chatbot platform |
| **Gupshup** | ₹0.25–0.50 | ₹0.35–0.60 | Custom | Volume-based | Yes | Yes | Enterprise-focused, wide RCS reach |
| **ValueFirst** | ₹0.20–0.50 | ₹0.30–0.60 | Custom | Custom | Yes | Yes | Good for mid-market |
| **Route Mobile** | ₹0.15–0.40 | ₹0.25–0.50 | Custom | Volume tiers | Yes | Yes | Global carrier agreements |
| **Tanla/Karix** | ₹0.20–0.45 | ₹0.30–0.55 | Custom | Custom | Yes | Yes | Listed company, enterprise-grade |
| **Netcore Cloud** | ₹0.20–0.60 | ₹0.30–0.70 | Custom | Custom | Yes | Yes | Marketing automation + RCS |

**India RCS Pricing Range:** ₹0.10–0.80/msg (retail CPaaS), carrier-level pricing ₹0.10–0.15/msg  
**DLT Registration:** Mandatory for all Indian RCS sending (~₹5,000–25,000 depending on entity type)

---

## 3. RCS vs SMS vs MMS vs OTT Cost Comparison

| Channel | Per Message Cost | Features | Engagement | Delivery Rate |
|---------|-----------------|----------|------------|--------------|
| **SMS** | $0.01–0.05 | Text only, 160 chars | Low (~5% CTR) | ~95% |
| **MMS** | $0.05–0.15 | Image + text, 160 chars | Medium | ~90% |
| **RCS** | $0.01–0.10 (basic), $0.03–0.12 (rich) | Rich media, buttons, verified brand, read receipts | High (~15–35% CTR) | ~85% (RCS-enabled devices) |
| **WhatsApp** | $0.01–0.04 (session), $0.005–0.09 (template) | Rich media, end-to-end encrypted | Very High | ~99% |
| **OTT (FB Messenger, etc.)** | $0.00–0.04 | Rich, platform-dependent | Varies | Platform-dependent |

**Key insight:** RCS costs 20–50% more per message than SMS but delivers 3–7x higher engagement rates. The ROI is positive when conversion value exceeds the incremental cost.

---

## 4. Total Cost Estimates by Volume

### 4A. US/Global (Basic Text-Only Messages)

| Volume/mo | AWS | Twilio | Sinch | Infobip | Plivo | Bandwidth |
|-----------|-----|--------|-------|---------|-------|-----------|
| **10K** | ~$100–300 | ~$100–500 | ~$100–500 | ~$100–600 | ~$100–400 | ~$40–100 |
| **100K** | ~$1,000–3,000 | ~$1,000–5,000 | ~$1,000–5,000 | ~$1,000–6,000 | ~$1,000–4,000 | ~$400–1,000 |
| **1M** | ~$10,000–30,000 | ~$10,000–50,000 | ~$10,000–50,000 | ~$10,000–60,000 | ~$10,000–40,000 | ~$4,000–10,000 |

*Note: Volume discounts of 20–40% typical at 100K+ and 40–60% at 1M+ monthly volumes. Prices include carrier pass-through fees which dominate at scale.*

### 4B. India (Basic Text Messages, DLT-Registered)

| Volume/mo | WABA Connect | MSG91 | SMSGatewayHub | 2Factor | Route Mobile |
|-----------|-------------|-------|--------------|---------|--------------|
| **10K** | ₹1,000 | ₹1,200 + ₹2,000 plan | ₹1,800–4,000 | ₹1,600–2,000 | ₹1,500–4,000 |
| **100K** | ₹10,000 | ₹12,000 + ₹2,000 plan | ₹18,000–40,000 | ₹16,000–20,000 | ₹15,000–40,000 |
| **1M** | ₹100,000 | ₹120,000 + ₹2,000 plan | ₹180K–400K | ₹160K–200K | ₹150K–400K |

*Volume discounts bring India prices down to ₹0.10–0.15/msg at 1M+ volumes.*

---

## 5. Key Findings & Winner Analysis

### Cheapest Path for 1-Way Text-Only RCS (Scale):

| Region | Cheapest Provider | Price | Why |
|--------|-------------------|-------|-----|
| **India** | **WABA Connect** | ₹0.10/msg (~$0.0012) | Lowest listed price, no setup fee, DLT-compliant |
| **US** | **Bandwidth** | ~$0.004–0.01/msg + carrier fees | Own carrier network = lowest transport cost |
| **US** | **AWS End User Messaging** | ~$0.01/segment + carrier fee | Only charged for delivered messages, transparent billing |
| **Global** | **Plivo** | ~$0.01–0.04/msg | Competitive pay-as-you-go with $10 free trial |
| **Enterprise Global** | **Infobip/Sinch** | Custom volume pricing | Best at 1M+/mo with negotiated discounts |

### Cheapest Path for Rich/Interactive Messages:

| Region | Cheapest Provider | Price | Why |
|--------|-------------------|-------|-----|
| **India** | **WABA Connect** | ₹0.12/rich msg | Cheapest rich template price |
| **India** | **MSG91** | ₹0.14/rich msg | Close second with good platform |
| **US** | **AWS / Plivo** | ~$0.03–0.08/msg | Competitive + transparent fees |
| **Global** | **Sinch / Plivo** | ~$0.03–0.08/msg | Volume discounts available |

### Cheapest Path for 2-Way Conversations:

- **Conversational pricing is best** when you expect replies → pay one session fee for unlimited 24hr messages
- **Infobip** and **Sinch** have the most mature conversational billing implementations globally
- **AWS** offers session-based pricing (carrier-dependent) with delivered-message-only billing
- In India, **WABA Connect**, **MSG91**, and **Gupshup** support conversational billing

---

## 6. Hidden Costs to Watch For

| Cost Item | Typical Range | Who Charges It |
|-----------|--------------|----------------|
| **Carrier pass-through fees** | $0.005–0.05/msg | All providers (carrier-imposed) |
| **Brand vetting / registration** | $15–75 one-time | Carrier/Google |
| **Monthly agent maintenance** | $5–25/mo | Carrier (via provider) |
| **DLT registration (India)** | ₹5,000–25,000 | Indian telecom operators |
| **SMS fallback charges** | Standard SMS rate (~$0.01–0.05) | All providers |
| **Setup / platform fees** | $0–15,000/yr | Provider-dependent |
| **GST/taxes (India)** | 18% | Government |
| **Content violation penalties** | $50–500/incident | Carriers |

---

## 7. Bottom Line Recommendations

| Use Case | Recommended Provider | Reasoning |
|----------|---------------------|----------|
| **Cheapest RCS at scale globally** | **Plivo** or **AWS** | Lowest base rates, pay-as-you-go, transparent carrier fees, no minimums |
| **Cheapest RCS in India** | **WABA Connect** or **MSG91** | ₹0.10–0.14/msg, no/low setup fees, DLT-compliant |
| **Best US carrier-integrated** | **Bandwidth** | Own CLEC network = lowest transport cost, native fallback |
| **Best for enterprise/managed** | **Infobip** or **Sinch** | Widest carrier coverage, managed onboarding, SLA guarantees |
| **Best for developer-first** | **Twilio** or **AWS** | Familiar APIs, GA RCS (2025), transparent billing |
| **Best free trial / low-risk entry** | **Plivo** ($10 free) or **TXTImpact** (free trial, no CC) | Zero commitment to start testing |
| **Best for India high-volume OTP/txn** | **2Factor** | ₹0.16–0.20/msg, simple pricing, ₹500 bot setup |

---

## 8. Data Sources & Notes

- **Sinch RCS Pricing Guide** (sinch.com/blog/rcs-pricing-explained) — general pricing frameworks
- **Google RBM Billing FAQ** (developers.google.com) — 3-tier architecture & carrier model
- **AWS End User Messaging** RCS billing docs (docs.aws.amazon.com) — detailed fee structure
- **Infobip RCS Billing Types** (infobip.com/docs) — A2P/P2A conversation billing
- **Plivo RCS Pricing Guide** (plivo.com/blog) — 3-tier cost breakdown
- **Decision Telecom** RCS cost analysis (decisiontele.com) — cost ranges $0.01–0.10/msg
- **WABA Connect** India provider comparison (wabaconnect.com) — India-specific pricing
- **2Factor** India pricing (2factor.in) — ₹0.16–0.20/msg
- **Bandwidth** carrier surcharge documentation (bandwidth.com)
- **TXTImpact** RCS provider comparison (txtimpact.com)

**Important caveats:**
1. RCS pricing is **not publicly listed** by most providers — you must request quotes
2. Carrier pass-through fees vary by recipient carrier and can change
3. Volume discounts are negotiable and not reflected in list prices
4. India DLT registration is mandatory and adds cost/friction
5. RCS device coverage is ~85–96% in developed markets, lower in emerging markets
6. "Cheapest" per-message price doesn't always = lowest total cost (consider fallback rates, setup fees, support quality)
