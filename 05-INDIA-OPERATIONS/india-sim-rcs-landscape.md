# India SIM+RCS + DLT Landscape Report

**Date:** May 2026  
**Scope:** India-specific research for SIM-based RCS/SMS business — cheap SIMs, DLT registration, RCS carrier availability, regulatory practicalities, and cost comparisons with US/EU.

---

## 1. Cost of Prepaid SIMs in India

India has the cheapest mobile data in the world. SIM cards are effectively free (or ~₹10-50 for the physical SIM), with the cost being the recharge plan. Below are the cheapest prepaid plans from each major carrier as of early 2026:

### Jio (Reliance Jio) — Market Leader ~45% share
| Plan (₹) | Validity | Data | SMS | Voice |
|-----------|----------|------|-----|-------|
| ₹149 | 24 days | 1GB/day | 100/day | Unlimited |
| ₹199 | 23 days | 1.5GB/day | 100/day | Unlimited |
| ₹249 | 23 days | 2GB/day | 100/day | Unlimited |
| ₹449 | 56 days | 2GB/day | 100/day | Unlimited |
| ₹666 | 84 days | 1.5GB/day | 100/day | Unlimited |
| ₹2,999 | 365 days | 2.5GB/day + 50GB | 100/day | Unlimited |

**Minimum recharge to keep SIM active:** ₹149/24 days = ~₹6.2/day

### Airtel — ~30% market share
| Plan (₹) | Validity | Data | SMS | Voice |
|-----------|----------|------|-----|-------|
| ₹199 | 24 days | 1GB/day | 100/day | Unlimited |
| ₹265 | 28 days | 1GB/day | 100/day | Unlimited |
| ₹299 | 28 days | 1.5GB/day | 100/day | Unlimited |
| ₹3,599 | 365 days | 2GB/day | 100/day | Unlimited |

**Minimum recharge:** ₹199/24 days = ~₹8.3/day

### Vi (Vodafone Idea) — ~18% share
| Plan (₹) | Validity | Data | SMS | Voice |
|-----------|----------|------|-----|-------|
| ₹199 | 24 days | 1GB/day | 100/day | Unlimited |
| ₹299 | 28 days | 1.5GB/day | 100/day | Unlimited |
| ₹3,099 | 365 days | 1.5GB/day | 100/day | Unlimited |

**Minimum recharge:** ₹199/24 days = ~₹8.3/day

### BSNL (Government) — ~7% share, cheapest for bare minimum
| Plan (₹) | Validity | Data | SMS | Voice |
|-----------|----------|------|-----|-------|
| ₹107 | 23 days | 1GB/day | 100/day | Unlimited |
| ₹187 | 28 days | 2GB/day | 100/day | Unlimited |
| ₹1,499 | 365 days | 2GB/day | 100/day | Unlimited |

**Minimum recharge:** ₹107/23 days = ~₹4.7/day (cheapest in India)

### Cost Summary (Annual)
| Carrier | Cheapest Annual Cost | Notes |
|---------|---------------------|-------|
| BSNL | ~₹1,499/year (~$18/year) | Cheapest, but coverage gaps in cities |
| Jio | ~₹2,999/year (~$36/year) | Best 4G/5G coverage, best value |
| Airtel | ~₹3,599/year (~$43/year) | Premium network quality |
| Vi | ~₹3,099/year (~$37/year) | Weakest coverage |

**US/EU Comparison:** US prepaid SIMs cost $15-45/month ($180-540/year). India SIMs cost $1.5-3.5/month. India is **10-30x cheaper** for mobile connectivity.

---

## 2. RCS Carrier Support in India (Google Messages)

### Status as of May 2026

**All three major private carriers now support RCS via Google Messages:**

| Carrier | RCS Status | RCS Backend | Notes |
|---------|-----------|-------------|-------|
| **Jio** | ✅ Active (since ~2019) | Google Jibe (carrier-integrated) | First Indian carrier to support RCS. Full chat features, read receipts, typing indicators. |
| **Vi (Vodafone Idea)** | ✅ Active (since ~2021) | Google Jibe | Was second to adopt RCS in India. |
| **Airtel** | ✅ Active (since Dec 2025) | Google Jibe (carrier-integrated) | Was the last holdout among private carriers. Partnered with Google specifically for RCS + AI spam filtering. |
| **BSNL** | ⚠️ Partial | Google Guest fallback | BSNL users can access RCS via Google Guest mode (Google Jibe-hosted, not carrier-integrated). |

### Key Developments
- **Dec 2025:** Airtel partnered with Google to launch RCS, completing carrier coverage across all major Indian operators. Airtel specifically negotiated integration of its AI spam filter into the RCS pipeline.
- **Mar 2026:** Airtel + Google announced deeper integration for carrier-backed spam-free RCS, combining Airtel's network-level safeguards with Google's spam detection.
- **Google Guest mode** provides RCS fallback for any Android user on any carrier that doesn't natively support RCS (including BSNL).

### RCS Registration/Provisioning for SIM-based Phones
- On Jio, Vi, Airtel: RCS auto-provisions when Google Messages is set as default SMS app on Android. The phone registers with the carrier's IMS/RCS infrastructure (or Google Jibe) and gets RCS capabilities.
- iPhones: Apple adopted RCS (as RCS Universal Profile) in iOS 18+ (late 2024), but it's carrier-agnostic in India. RCS on iPhone works through the carrier network, not Google Jibe.
- **P2P RCS is free** — person-to-person RCS messages use data, not per-message billing.

### RCS Business Messaging (RBM) in India
- Google RCS Business Messaging (RBM) is available in India through multiple providers.
- All major carriers support RBM delivery to their subscribers.
- **Consent requirements (2026):** Google Messages now shows explicit consent prompts for low-reputation promotional RCS agents in India, to enhance channel trust and combat spam.

---

## 3. DLT Registration Process (Legal SMS/RCS Sending)

### What is DLT?
DLT (Distributed Ledger Technology) is a **blockchain-based platform mandated by TRAI** (Telecom Regulatory Authority of India) under the TCCCPR 2018 (Telecom Commercial Communications Customer Preference Regulations). It tracks all commercial communications (SMS and RCS) to curb spam and fraud.

**DLT registration is MANDATORY** for anyone sending commercial SMS or RCS messages to Indian phone numbers. No DLT registration = no message delivery.

### DLT Registration Steps

#### Step 1: Entity (Principal Entity) Registration
- **Who:** Any business/organization that wants to send commercial messages
- **Where:** Register on any one of the operator DLT platforms:
  - Jio DLT: https://trueconnect.jio.com
  - Airtel DLT: https://dlt.airtel.in
  - Vi DLT: https://www.vzdltpanel.in
  - BSNL DLT: https://bsnl.ui.dlt.gov.in
  - Smartping DLT (third-party): https://smartping.in
- **Cost:** ₹0-₹5,000 depending on operator (some operators offer free entity registration to encourage adoption)
- **Documents Required:**
  - PAN Card (for business/entity)
  - GST Certificate or CIN (Certificate of Incorporation)
  - Authorization letter
  - Business proof (shop act, trade license, etc.)
  - Bank account details
- **Time:** 3-7 working days for approval
- **Note:** Must register with at least one operator, but messages will be delivered across all networks

#### Step 2: Telemarketer Registration (if using a third-party SMS provider)
- **Who:** Any telemarketer/reseller who sends messages on behalf of entities
- **Cost:** ₹0-₹10,000 (varies by operator; some free)
- **Same documents** as entity registration plus additional telemarketer-specific forms
- **Time:** 3-7 working days

#### Step 3: Header (Sender ID) Registration
- **What:** Register your 6-character alphanumeric sender ID (e.g., "MYCOMP")
- **Cost:** ₹0-₹1,000 per header (some operators free)
- **Time:** 1-3 working days
- **Format:** 6 characters, alphanumeric. Promotional headers start with a different prefix than transactional.

#### Step 4: Content Template Registration
- **What:** Every message you send must match a pre-registered template on DLT
- **Cost:** ₹0 per template (free on most operators)
- **Time:** 1-7 working days for approval
- **Requirements:**
  - Must specify message type (Promotional or Transactional)
  - Template must include variable placeholders where dynamic content goes
  - Template text is immutable once approved — only variable values change
  - **Consent templates** must also be registered if sending promotional messages

### DLT Cost Summary
| Item | Cost Range (₹) | Time |
|------|----------------|------|
| Entity Registration | ₹0 - ₹5,000 | 3-7 days |
| Telemarketer Registration | ₹0 - ₹10,000 | 3-7 days |
| Header (Sender ID) | ₹0 - ₹1,000 each | 1-3 days |
| Content Template | ₹0 each | 1-7 days |
| **Total to get started** | **₹0 - ₹15,000** | **1-2 weeks** |

**Note:** Many bulk SMS providers offer to handle DLT registration for you as part of their onboarding, sometimes waiving the fees.

---

## 4. India-Specific RCS API Providers and Pricing

### RCS Business Messaging (RBM) Pricing in India (2026)

| Provider | Per-Message Cost (₹) | Bot Setup Fee | Volume Discounts | Notes |
|----------|---------------------|---------------|------------------|-------|
| MSG91 | ₹0.11 - ₹0.18 | ₹500 - ₹1,000 | Yes (50L+ volume) | India-based, strong DLT support |
| 2Factor | ₹0.16 - ₹0.20 | ₹500 | Yes | Popular for OTP/transactional |
| Mtalkz | ₹0.12 - ₹0.20 | ₹500 - ₹1,000 | Yes | Multi-carrier RCS delivery |
| JioCX (Jio's CPaaS) | ₹0.11 - ₹0.15 | Contact sales | Enterprise deals | Jio's own CPaaS platform, carrier-grade |
| Fast2SMS | ₹0.10 - ₹0.18 | ₹0 | Yes | Budget-friendly |
| GreenAds Global | ₹0.12 - ₹0.20 | ₹500 | Yes | RCS specialist |
| Sinch (India) | ₹0.15 - ₹0.25 | Contact sales | Enterprise | Global player with India presence |
| Infobip | ₹0.15 - ₹0.25 | Contact sales | Enterprise | Global CPaaS leader |
| Webxion | ₹0.12 - ₹0.18 | ₹500 | Yes | India-focused |
| MessageBot | ₹0.12 - ₹0.20 | ₹500 | Yes | TRAI compliant |

**Typical RCS pricing range:** ₹0.10-₹0.25 per message (~$0.0012 - $0.003/message)

### Airtel Business RCS
- Airtel partnered with Google for RCS in Dec 2025
- Airtel's per-message business RCS rate: **₹0.11** (as reported in news coverage)
- API access through Airtel's B2B SMS/RCS platform

### JioCX (Jio's RCS Platform)
- **JioCX** is Jio's CPaaS (Communications Platform as a Service) offering
- Provides RCS messaging API, SMS, WhatsApp, email under one platform
- Has a **Jio RCS Accelerator** program for businesses
- API endpoint: https://www.jiocx.com/products/rcs-messaging-api
- Jio also offers **Messaging as a Service (MaaS)** — a cloud-native A2P platform

### Google RBM API (Direct)
- Available via Google's RCS Business Messaging API
- Google's developer portal: https://developers.google.com/business-communications/rcs-business-messaging/
- Direct API access requires Google Cloud project setup
- Google does not charge directly for RBM; you pay through your chosen RCS provider/aggregator

---

## 5. SIM-Based RCS Viability in India

### The Core Question: Can you put Indian SIMs in phones and send RCS messages?

**Short answer: Yes for P2P, extremely challenging for bulk/business use.**

### P2P RCS (Person-to-Person)
- ✅ Fully works on all carriers via Google Messages
- Auto-provisioning on Android when Google Messages is default
- Uses data (not per-message billing) — effectively **free** on unlimited data plans
- RCS chat features: read receipts, typing indicators, high-res media, group chats
- **If your use case is sending individual RCS messages from phone-to-phone, this works perfectly**

### A2P RCS (Application-to-Person) via SIM
- ⚠️ **Problem:** A2P RCS through SIM-based phones is not the same as P2P
- Google Messages treats SIM-originated messages as P2P, but:
  - **Rate limits:** Carriers/Google may flag accounts sending hundreds of messages/day as spam
  - **Consent requirements (2026):** Google Messages now prompts recipients to confirm/decline messages from "low reputation promotional agents" in India
  - **No sender verification:** P2P RCS doesn't give you branded/verified sender identity — your messages appear from a phone number, not a brand
  - **Spam filtering:** Airtel-Google partnership specifically targets RCS spam with AI filtering. Jio also has anti-spam measures.

### RCS Registration Success Rate
- Carrier-integrated RCS (Jio, Vi, Airtel): **~80-90%** success rate for RCS provisioning on supported Android devices
- Google Guest fallback: **~95%+** (works on any Android with Google Messages + data)
- **Key blocker:** Many Indian Android phones ship with OEM messaging apps (Samsung Messages, Xiaomi Messages, etc.) as default, not Google Messages. Users must switch to Google Messages to get RCS.

---

## 6. TRAI Regulations on Promotional Messaging

### TCCCPR 2018 Framework (Still Governing in 2026)

**Two categories of commercial messages:**

#### Transactional Messages
- **Definition:** Messages facilitating a transaction the recipient has already initiated (OTP, order confirmations, delivery updates, account alerts)
- **Sender ID format:** 6-character alphabetic header (e.g., "HDFCBK")
- **Delivery window:** 24/7 (no restrictions)
- **NDNC:** Can be sent to NDNC-registered numbers
- **Template requirement:** Must match DLT-registered template exactly
- **Content:** Must not contain any promotional content

#### Promotional Messages
- **Definition:** Messages with marketing/promotional content (offers, discounts, new product info)
- **Sender ID format:** Starts with numeric prefix indicating category (e.g., "140XXX" or specific 6-char ID)
- **Delivery window:** **10:00 AM to 8:00 PM only** (9 hours/day)
- **NDNC:** **Cannot** be sent to numbers on the National Do Not Call (NDNC) registry
- **Consent required:** Must have explicit opt-in consent from the recipient via DLT consent framework
- **Template requirement:** Must match DLT-registered template
- **SMS suffix:** TRAI mandates specific message suffixes (added 2025) to identify message category

### Key Regulatory Points
- **NDNC Registry:** ~500M+ numbers registered. Sending promotional messages to NDNC numbers = violation.
- **Penalties:** Up to ₹2,75,000 per violation for repeated offenses. Carriers can face fines up to ₹50 lakh/quarter.
- **Consent Management:** Promotional messages require documented consent stored on DLT. Recipients can withdraw consent anytime.
- **Scrubbing:** Before sending promotional messages, you must scrub your list against the NDNC registry (most providers do this automatically).
- **RCS is also regulated under DLT:** TRAI's DLT framework applies to both SMS and RCS messages to Indian numbers.

### Timeline Restrictions
| Message Type | Allowed Hours | Days |
|-------------|---------------|------|
| Transactional | 24 hours | All days |
| Promotional | 10 AM - 8 PM IST | All days |
| OTP/Service | 24 hours | All days |

---

## 7. Cost Comparison: India SIM-Based SMS vs API-Based RCS

### SIM-Based SMS/RCS Cost (Per SIM)

| Component | Monthly Cost (₹) | Monthly Cost ($) | Annual Cost ($) |
|-----------|-------------------|------------------|-----------------|
| Cheapest plan (Jio ₹149/24 days) | ~₹186 | ~$2.25 | ~$27 |
| Phone (cheap Android, amortized) | ~₹100 | ~$1.20 | ~$14 |
| Power/infrastructure | ~₹50 | ~$0.60 | ~$7 |
| **Total per SIM per month** | **~₹336** | **~$4.05** | **~$48** |

**Messages per SIM per day (realistic P2P):** 50-200 (manual/slow automated)  
**Messages per SIM per month:** 1,500-6,000  
**Cost per message (SIM-based RCS):** ~₹0.06 - ₹0.22 ($0.0007 - $0.003)

### API-Based Bulk SMS Cost (India)

| Type | Per-Message Cost (₹) | Per-Message Cost ($) |
|------|----------------------|---------------------|
| Promotional SMS (bulk) | ₹0.07 - ₹0.15 | $0.0008 - $0.0018 |
| Transactional SMS | ₹0.10 - ₹0.20 | $0.0012 - $0.0024 |
| OTP SMS | ₹0.12 - ₹0.25 | $0.0014 - $0.003 |
| RCS (API-based) | ₹0.10 - ₹0.25 | $0.0012 - $0.003 |

### Head-to-Head Comparison

| Factor | SIM-Based RCS | API-Based SMS | API-Based RCS |
|--------|--------------|---------------|---------------|
| Cost per message | ₹0.06-0.22 | ₹0.07-0.20 | ₹0.10-0.25 |
| Setup cost | ₹500/phone + SIM | ₹0 (just API) | ₹0 + bot setup ₹500 |
| DLT compliance | Not applicable (P2P) | Required | Required |
| Sender identity | Personal phone number | Branded 6-char ID | Verified brand profile |
| Volume scaling | Linear (1 SIM = limited msgs) | Unlimited | Unlimited |
| Rich media | Yes (RCS) | No (text only) | Yes (RCS) |
| Read receipts | Yes (P2P) | No | Yes |
| Legal risk | HIGH (spam, ToS violation) | Low (compliant) | Low (compliant) |
| Carrier filtering | Aggressive anti-spam | DLT-approved routes | DLT-approved routes |
| Rate limiting | Very strict per-SIM | High volume OK | High volume OK |

---

## 8. Practical Steps to Set Up a SIM-Based Messaging Operation in India

### ⚠️ Major Regulatory Obstacle: Dec 2023 SIM Rules

**The Department of Telecommunications (DoT) implemented new rules effective December 1, 2023 that severely restrict bulk SIM operations:**

1. **Bulk connections BANNED:** The provision for bulk SIM connections has been scrapped. You can no longer walk into a store and buy 50-100 SIMs at once.
2. **Mandatory e-KYC:** All SIM activations require individual Aadhaar-based e-KYC verification with biometric authentication.
3. **Per-person SIM limit:** Maximum 9 SIMs per person across all carriers (reduced from 18 earlier for some categories).
4. **SIM vendor verification:** All SIM card sellers must be verified and registered.
5. **Corporate connections:** Companies purchasing corporate SIMs face e-verification at multiple stages. No more unlimited corporate SIMs.
6. **Penalties for misuse:** ₹50,000 fine for SIM dealers issuing SIMs without proper verification. Criminal penalties for SIMs used in fraud.
7. **Deactivation:** SIMs unused for 90+ days get auto-deactivated by carriers.
8. **M2M SIMs:** Machine-to-machine SIMs must be registered under a separate service class (cannot be used for P2P messaging).

### If You Still Want to Proceed (Legal Path)

#### Option A: Corporate SIM Connection Route
1. **Register a company** in India (Pvt Ltd or LLP) — cost ₹5,000-15,000
2. **Apply for corporate connections** with Jio/Airtel/Vi — requires:
   - Company PAN and CIN
   - Authorization letter from company director
   - Individual e-KYC for each SIM
   - Business justification for each SIM
3. **Limit:** Corporate plans now have caps; expect 20-50 SIMs max for legitimate business use
4. **Cost per corporate SIM:** ₹199-499/month on corporate plans
5. **Compliance:** Each SIM must be traceable to an employee/purpose

#### Option B: DLT-Registered Bulk SMS/RCS (Recommended)
1. **Register entity on DLT** — ₹0-5,000, 3-7 days
2. **Register as telemarketer** (if reselling) — ₹0-10,000, 3-7 days
3. **Register sender IDs** — ₹0-1,000 each
4. **Register content templates** — free, 1-7 days each
5. **Choose a bulk SMS/RCS provider** (MSG91, 2Factor, JioCX, etc.)
6. **Integrate their API** into your application
7. **Start sending** at ₹0.07-0.25 per message
8. **No SIM hardware needed** — everything goes through API

#### Option C: SIM-Based (Small Scale, P2P Only)
1. **Get up to 9 SIMs per person** (across all carriers)
2. **Use cheap Android phones** (₹4,000-7,000 each for basic 4G Android)
3. **Install Google Messages** as default messaging app
4. **Enable RCS** in Google Messages settings
5. **Send P2P RCS/SMS** — rate limited to avoid spam detection
6. **Scale with multiple people** — each can hold 9 SIMs
7. **Annual cost per SIM:** ~₹2,000-3,000 (plan + amortized phone)

---

## 9. Key Differences: India vs US/EU Landscape

| Factor | India | US | EU |
|--------|-------|-----|-----|
| **SIM cost (annual)** | $18-43 | $180-540 | $60-240 |
| **Data per ₹/$** | 1GB/₹1.5 | 1GB/$1-3 | 1GB/€1-3 |
| **SMS included** | 100/day on most plans | Often unlimited | Varies, often 100-500/mo |
| **RCS carrier support** | All 4 carriers (2025-26) | All major (via Google/Jibe) | Patchy, country-dependent |
| **RCS business messaging** | Available, growing fast | Mature (Google RBM) | Limited availability |
| **Regulatory framework** | Strict DLT + TRAI oversight | TCPA + carrier rules | GDPR + ePrivacy + carrier rules |
| **Bulk SIM access** | **SEVERELY RESTRICTED** (Dec 2023 rules) | Possible with business ID | Varies by country |
| **Per-SIM limit** | 9 per person | No federal limit | Varies |
| **Spam enforcement** | Aggressive (₹50K-2.75L fines) | TCPA ($500-1500/msg) | GDPR (€20M+ fines) |
| **Message template mandate** | Yes (DLT template registration) | No | No (but consent required) |
| **Promotional message hours** | 10AM-8PM only | Reasonable hours (state laws) | Business hours recommended |
| **NDNC/DNC registry** | ~500M+ numbers registered | ~230M numbers (US) | Varies by country |
| **Bulk SMS API cost/msg** | ₹0.07-0.20 ($0.0008-0.002) | $0.005-0.02 | €0.005-0.02 |
| **RCS API cost/msg** | ₹0.10-0.25 ($0.001-0.003) | $0.01-0.05 | €0.01-0.05 |
| **Cheapest per-message route** | API-based SMS (₹0.07) | API-based SMS ($0.005) | API-based SMS (€0.005) |

### Critical India-Specific Factors

1. **SIMs are cheap but tightly regulated:** The low cost of Indian SIMs is offset by the Dec 2023 rules making bulk SIM acquisition nearly impossible legally. The 9-SIM-per-person limit is a hard constraint.

2. **DLT is mandatory and unique to India:** No other major market has a blockchain-based mandatory template registration system. This adds 1-2 weeks of setup time but creates a high compliance barrier that reduces spam competition.

3. **RCS spam is a real battle:** India is the #1 market for RCS spam concerns. Google's 2026 partnership with Airtel specifically targets RCS spam. This means SIM-based bulk RCS will face increasingly aggressive filtering.

4. **WhatsApp dominance:** India has 500M+ WhatsApp users. Most businesses prefer WhatsApp Business API over SMS/RCS for customer communication. WhatsApp made utility/business messages free in Nov 2024, directly challenging SMS economics.

5. **Extremely cheap API-based SMS:** At ₹0.07/msg ($0.0008), Indian bulk SMS is among the cheapest in the world. This makes SIM-based SMS/RCS economically marginal — the savings from SIM-based P2P are small compared to the compliance/legal risks.

6. **Corporate SIMs are the viable path:** If you need 20-50 SIMs for legitimate business use, the corporate connection route with proper e-KYC is the only legal way. It's slower but sustainable.

---

## 10. Recommendations

### For a SIM-based messaging business targeting India:

1. **Do NOT attempt bulk SIM farms in India.** The Dec 2023 rules, biometric e-KYC, 9-SIM limit, and criminal penalties make this operationally and legally infeasible at scale.

2. **Go API-first for business messaging.** At ₹0.07-0.20 per SMS and ₹0.10-0.25 per RCS message, Indian API-based messaging is incredibly cheap. The SIM cost savings don't justify the compliance risk.

3. **Consider corporate SIMs for small-scale P2P RCS testing.** If you need to validate RCS deliverability or test SIM-based RCS behavior, 9-18 SIMs (1-2 people) is feasible for testing purposes.

4. **DLT registration is non-negotiable.** Budget 1-2 weeks and ₹0-15,000 for DLT setup. Most bulk SMS providers will assist with this.

5. **RCS is viable and growing rapidly in India.** All carriers are now on board. The Airtel partnership (Dec 2025) was the final piece. RCS business messaging adoption is accelerating.

6. **Watch WhatsApp as the real competitor.** With 500M+ Indian users and free utility messages (since Nov 2024), WhatsApp may eat into both SMS and RCS market share. Consider a dual WhatsApp + RCS strategy.

7. **If operating from outside India:** You must still register on DLT to send messages to Indian numbers. Use an India-based provider (MSG91, JioCX, 2Factor) who can handle DLT compliance for you.

---

## Sources

- Times of India: Airtel RCS partnership with Google (Dec 2025)
- Gadgets360: Airtel RCS messaging launch (Dec 2025)
- TechCrunch: Google tackles RCS spam in India (Mar 2026)
- TelecomTalk: Airtel-Google carrier-backed RCS (Mar 2026)
- 2Factor.in: RCS pricing India 2026
- MSG91: RCS messaging pricing India
- Mtalkz: RCS business messaging India
- JioCX: Jio CPaaS platform for RCS
- TRAI/DLT portal: Registration guidelines
- DoT: New SIM card rules Dec 2023
- India.com/Business Standard: Bulk SIM ban details
- Multiple bulk SMS provider pricing pages (MessageBot, Webxion, SpringEdge, etc.)
- Angel One: Airtel ₹0.11/msg RCS rate
