# SIM Bank Hardware & Cost Analysis Report
## RCS SMS Management: SIM-Based vs RBM API vs CPaaS Providers

---

## 1. SIM Bank Hardware Comparison Table

| Product | Ports/SIM Slots | Est. Price (USD) | Interface | Remote SIM Mgmt | RCS Support | Notes |
|---------|----------------|-------------------|-----------|-----------------|-------------|-------|
| **sysmoOCTSIM** (sysmocom) | 8 | ~€300-400 (~$330-440) | USB-CCID | Via osmo-remsim + sysmoQMOD | ❌ (SIM reader only) | Hacker/researcher option. FOSS firmware. Works with pySim. PC/SC compatible. Stacks to build dense solutions. |
| **sysmoSIMBANK-96** (sysmocom) | 96 | ~€3,000+ (~$3,300+) | Network (3x GbE) | ✅ osmo-remsim REST API | ❌ (SIM reader only) | 2U rack mount. x86_64 Linux. Per-slot power cycling. FOSS software. |
| **sysmoSIMBANK-192** (sysmocom) | 192 | ~€5,000+ (~$5,500+) | Network (3x GbE) | ✅ osmo-remsim REST API | ❌ (SIM reader only) | 4U rack mount. Same architecture as 96-slot. |
| **Ejointech SIMPOOL-128** | 128 | ~$800-1,200 | IP Network | ✅ SIM Server | ❌ (SIM bank only) | Compatible with Ejoin gateways. |
| **Ejointech SIMPOOL-256** | 256 | ~$1,200-1,800 | IP Network | ✅ SIM Server | ❌ (SIM bank only) | Centralized management. |
| **Ejointech SIMPOOL-512** | 512 | ~$1,800-2,500 | IP Network | ✅ SIM Server | ❌ (SIM bank only) | Highest density consumer option. 44x40x5cm. |
| **OpenVox Simbank-64** | 64 | ~$600-800 | IP Network | ✅ Via VoxStack | ❌ (SIM bank only) | Works with OpenVox wireless gateways. |
| **OpenVox Simbank-128** | 128 | ~$1,000-1,400 | IP Network | ✅ Via VoxStack | ❌ (SIM bank only) | 2G/3G/4G compatible. |
| **OpenVox Simbank-320** | 320 | ~€2,831 (~$3,100) | IP Network | ✅ Via VoxStack | ❌ (SIM bank only) | Highest port count from OpenVox. |
| **Dinstar SIMBank-128** | 128 | ~$1,830 (AliExpress) / €2,617 (voip.world) | IP Network | ✅ SIMCloud | ❌ (SIM bank only) | 1U rack mount. Works with Dinstar gateways. |
| **Hypermedia SIM Server** | 32-128+ | Contact for quote | IP Network | ✅ Proprietary | ❌ (SIM bank only) | Israeli company. Works with Hypermedia gateways. |
| **Polygator SIM-Bank 100** | 100 | ~$800-1,200 | IP Network | ✅ SIM-Server | ❌ (SIM bank only) | x86 or ARM based. Compact. |
| **Polygator SIM-Bank 200** | 200 | ~$1,200-1,800 | IP Network | ✅ SIM-Server | ❌ (SIM bank only) | LED indication. Cooler on x86 model. |
| **DIY (Consumer USB Readers)** | 128-256 | ~$200-500 | USB hubs | ❌ Manual | ❌ | Medium article approach: stack USB CCID readers. Cheapest but labor-intensive. |

### Key Insight: sysmoOCTSIM as the Hacker/Researcher Option
- **8-slot PCBA** with USB-CCID interface — appears as standard smart card reader to OS
- **Fully FOSS firmware** (osmo-ccid-firmware on gitea.osmocom.org)
- Works with **pySim** for SIM card programming/management
- **All 8 slots fully independent** — concurrent transactions on all slots
- Stackable: 12 boards = 96 SIMs in 2U, 24 boards = 192 SIMs in 4U
- Can combine with **sysmoQMOD** (quad mPCIe modem) + **osmo-remsim** for full remote SIM system
- Best for: security research, SIM card testing, custom builds, low-volume operations

---

## 2. GSM Modem Pools for RCS

### Hardware Options

| Product | Ports | SIM Slots | Price (USD) | Network | Throughput |
|---------|-------|-----------|-------------|---------|------------|
| Ejointech ACOM608PL | 8 | 8 | $595 | 2G/3G/4G | ~680 SMS/min |
| Ejointech ACOM616L-16 | 16 | 16 | $1,125 | 2G/3G/4G | ~1,360 SMS/min |
| Ejointech ACOM616L-64 | 16 | 64 | $1,280 | 2G/3G/4G | ~1,360 SMS/min |
| Ejointech ACOM632L-32 | 32 | 32 | $2,120 | 2G/3G/4G | ~2,720 SMS/min |
| Ejointech ACOM632L-128 | 32 | 128 | $2,250 | 2G/3G/4G | ~2,720 SMS/min |
| Ejointech ACOM664L-64 | 64 | 64 | $3,480 | 2G/3G/4G | ~5,440 SMS/min |
| Ejointech ACOM664L-256 | 64 | 256 | $3,730 | 2G/3G/4G | ~5,440 SMS/min |
| Ejointech ACOM664L-512 | 64 | 512 | $4,080 | 2G/3G/4G | ~5,440 SMS/min |
| YX 8-Port 4G LTE | 8 | 8 | ~$400-500 | 4G LTE | ~680 SMS/min |
| YX 64-Port GSM | 64 | 64 | ~$2,000-3,000 | 2G | ~5,440 SMS/min |

### Critical Question: Do 4G Modem Pools Support RCS?

**Answer: NO — GSM modem pools support SMS/MMS only, NOT RCS.**

Here's why:
- **RCS is an application-layer protocol** that runs on top of IP data connections, using the RCS Universal Profile (GSMA)
- **GSM modem pools** implement SMS/MMS at the radio protocol level using AT commands (3GPP TS 27.005)
- **RCS requires**: Google Messages or Samsung Messages client, RCS Universal Profile registration with carrier infrastructure, and IP-based messaging via the RCS chat service
- **4G LTE modems** in modem pools operate as dumb SMS pipes — they send/receive SMS via the IMS or CSFB path, not via RCS
- **To get RCS on a SIM**, you'd need an Android phone running Google Messages with that SIM registered to a carrier's RCS infrastructure — there is no AT command interface for RCS
- **No commercially available modem pool** supports RCS messaging

**Workaround possibility**: One could theoretically run Android OS instances (via emulators or Android Go devices) each with a SIM, register RCS on each, and send via the RCS client. However, this is extremely fragile, unscalable, and each RCS registration is tied to a specific device/number combination.

---

## 3. RCS Registration Stability Issues

Using SIM cards for RCS is **fundamentally unstable**:

- **RCS registration is device-bound**: RCS on Google Messages registers a specific phone number + device combination. Switching SIMs or devices breaks registration.
- **Re-registration required after**: SIM swap, device change, carrier port, network change, app update, prolonged offline periods
- **Carrier infrastructure dependency**: Not all carriers support RCS; MVNOs often lack RCS support; roaming breaks RCS
- **Number verification**: Google uses SMS verification for RCS setup — each re-registration costs an SMS and takes 1-5 minutes
- **Typical re-registration frequency**: Once every few days to weeks depending on SIM cycling patterns
- **SIM cycling kills RCS**: The key advantage of SIM banks (rotating SIMs to avoid detection) is incompatible with RCS registration persistence
- **Google enforces device-level attestation**: SafetyNet/Play Integrity checks may flag non-phone devices

**Conclusion**: A SIM-based RCS approach is technically impractical at scale. The entire value proposition of SIM banks (SIM rotation/cycling) works against RCS registration stability. SIM banks are viable for SMS-only operations.

---

## 4. Cost Analysis: SIM-Based Approach

### 4.1 SIM Card Costs by Country

| Country | SIM Cost (one-time) | Monthly Plan Cost | SMS Included | Notes |
|---------|--------------------|--------------------|-------------|-------|
| **India** (Jio/Airtel/Vi) | ₹0-50 (~$0-0.60) | ₹149-299/mo (~$1.75-3.50) | 100/day unlimited | Cheapest globally. Aadhaar KYC required. |
| **India** (BSNL) | ₹20 (~$0.25) | ₹107/mo (~$1.25) | 100/day | Govt operator. Cheapest plan. |
| **USA** (T-Mobile Prepaid) | $0-10 (free w/ plan) | $15/mo (PayGo) | Unlimited | 10DLC registration needed for A2P. |
| **USA** (Mint Mobile) | $0 (w/ plan) | $15/mo (3-mo min) | Unlimited | Bulk discount: $15/mo. |
| **USA** (Ultra Mobile PayGo) | $3/mo | $3/mo | 100 SMS/mo | Cheapest US plan. Very limited SMS. |
| **UK** (Lebara/VOXI) | £0 (free SIM) | £5-10/mo (~$6-12) | Unlimited | UK SIM farms now criminalized (2025). |
| **EU** (Various) | €0-10 | €5-15/mo (~$5.50-16.50) | Varies widely | France/Spain cheapest. Germany expensive. |

### 4.2 SIM-Based Hardware Costs

| Scale | Hardware | Cost | SIM Cards | SIM Cost | Monthly Plans | Total Setup |
|-------|----------|------|-----------|----------|---------------|-------------|
| **10 SIMs** | 2x sysmoOCTSIM + USB hub | ~$800 | 10x US SIMs | $0-100 | $150/mo (US) | ~$800-900 |
| **10 SIMs** | 1x Ejointech ACOM608 (8-port) | $595 | 10x India SIMs | ~$6 | ~$30/mo (India) | ~$600 |
| **100 SIMs** | 1x SIMPOOL-128 + ACOM632L-32 | ~$3,300 | 100x US SIMs | ~$0 | ~$1,500/mo | ~$3,300 |
| **100 SIMs** | 1x SIMPOOL-128 + ACOM632L-32 | ~$3,300 | 100x India SIMs | ~$60 | ~$300/mo | ~$3,360 |
| **500 SIMs** | 1x SIMPOOL-512 + 8x ACOM632L | ~$19,000 | 500x US SIMs | ~$0 | ~$7,500/mo | ~$19,000 |
| **500 SIMs** | 1x SIMPOOL-512 + 8x ACOM632L | ~$19,000 | 500x India SIMs | ~$300 | ~$1,500/mo | ~$19,300 |

### 4.3 SIM-Based Monthly Operating Costs (at Scale)

| Cost Component | 100 SIMs (US) | 100 SIMs (India) | 500 SIMs (US) | 500 SIMs (India) |
|---------------|---------------|-----------------|---------------|-----------------|
| Monthly plans | $1,500 | $300 | $7,500 | $1,500 |
| SIM replacements (5%/mo) | $50 | $5 | $250 | $25 |
| Server hosting | $50 | $50 | $200 | $200 |
| Power & cooling | $30 | $30 | $150 | $150 |
| **Total monthly** | **$1,630** | **$385** | **$8,100** | **$1,875** |
| **Per-SIM monthly** | $16.30 | $3.85 | $16.20 | $3.75 |

### 4.4 SIM-Based SMS Throughput & Cost

- Typical throughput: ~85 SMS/min per SIM (Ejointech spec: 2,720/min ÷ 32 ports)
- Monthly capacity per SIM (24/7): ~3.6M SMS/month
- **Per-message cost (US SIMs)**: $16.30/mo ÷ 3.6M = **$0.0000045/msg** (hardware amortized)
- **Per-message cost (India SIMs)**: $3.85/mo ÷ 3.6M = **$0.0000011/msg**
- **Realistic per-message cost** (accounting for throttling, SIM blocks, 8hr/day): ~**$0.00005-0.0005/msg** for SMS

⚠️ **This is SMS only. RCS via SIM banks is NOT practically achievable.**

---

## 5. Cost Analysis: RBM API (Google RCS Business Messaging)

### Google RBM Pricing Structure

Google simplified billing in November 2025. Pricing is **carrier-determined** and varies by region.

| Agent Type | Billing Model | Typical Price (US) | Notes |
|------------|--------------|---------------------|-------|
| **Non-Conversational** (Transactional) | Per message | ~$0.01-0.03/msg | OTP, notifications, alerts |
| **Conversational** (Marketing) | Per message | ~$0.02-0.05/msg | Rich cards, carousels, interactive |
| **Basic Text** (US model) | Per message | ~$0.005-0.01/msg | US-specific simplified billing |

**Important**: Google RBM pricing is set by carriers and billed through Google's platform. Actual rates require a Google Cloud billing account and carrier agreements.

### RBM API Providers (Aggregators)

| Provider | RCS Basic (US) | RCS Rich (US) | RCS Conversation (US) | Notes |
|----------|---------------|---------------|----------------------|-------|
| **Vonage** | ~$0.005-0.01 | ~$0.01-0.02 | ~$0.02-0.05 | 3 tiers: Basic, Rich, Conversation |
| **Sinch** | ~$0.005-0.01 | ~$0.01-0.025 | ~$0.025-0.05 | Carrier-specific rates. Volume discounts. |
| **Plivo** | ~$0.005-0.008 | ~$0.01-0.02 | ~$0.02-0.04 | Competitive pricing. |
| **Bandwidth** | ~$0.005-0.01 | ~$0.01-0.02 | ~$0.02-0.05 | US-focused. |

**Key RBM Notes**:
- RBM requires agent registration with each carrier
- Google handles the RCS Universal Profile infrastructure
- Brand verification required (similar to 10DLC)
- Fallback to SMS when RCS unavailable (additional SMS cost)
- Setup fees may apply through aggregators

---

## 6. Cost Analysis: CPaaS Providers

| Provider | RCS Price (US) | SMS Price (US) | Setup/Fees | Notes |
|----------|---------------|---------------|------------|-------|
| **Twilio** | ~$0.01-0.03/msg | $0.0079/msg | No setup fee | RCS GA since 2024. 20+ countries, 55+ carriers. Pay-as-you-go. |
| **Infobip** | Custom quote | $0.005-0.01/msg | Contact sales | Usage-based. Session-based billing for conversations. |
| **Syniverse** | Custom quote | $0.005-0.01/msg | Contact sales | Enterprise-focused. Per-session pricing model. |
| **Vonage** | ~$0.005-0.05/msg | $0.0065/msg | No setup fee | 3 RCS message tiers. |
| **Sinch** | ~$0.005-0.05/msg | $0.0078/msg | No setup fee | Volume discounts available. |
| **MessageBird** | ~$0.01-0.03/msg | $0.005-0.01/msg | No setup fee | European-based. |
| **Plivo** | ~$0.005-0.04/msg | $0.0045/msg | No setup fee | Often cheapest option. |

---

## 7. Complete Cost Comparison: Per 1,000 Messages

| Approach | SMS (per 1K) | RCS (per 1K) | Notes |
|----------|-------------|-------------|-------|
| **SIM-Based (India, 100 SIMs)** | **$0.05-0.50** | ❌ Not feasible | Cheapest for SMS. Legal risk high. |
| **SIM-Based (US, 100 SIMs)** | **$0.05-0.50** | ❌ Not feasible | Legal risk in US. Carrier detection. |
| **SIM-Based (India, 500 SIMs)** | **$0.03-0.30** | ❌ Not feasible | Economies of scale. |
| **Google RBM Direct** | N/A | **$5-50** | Legitimate. Branded. Rich media. |
| **Vonage RCS API** | $6.50 | **$5-50** | Basic to Conversation tier. |
| **Sinch RCS API** | $7.80 | **$5-50** | Volume discounts. |
| **Twilio RCS** | $7.90 | **$10-30** | Easy API. Global reach. |
| **Infobip RCS** | $5-10 | **$5-30** | Enterprise pricing. |
| **Syniverse RCS** | $5-10 | **$5-30** | Session-based. |
| **Plivo RCS** | $4.50 | **$5-40** | Often cheapest API. |

### Key Comparison: SIM SMS vs API RCS

| Metric | SIM-Based SMS (India) | API-Based RCS (Twilio) | API-Based RCS (Sinch) |
|--------|----------------------|----------------------|---------------------|
| Per 1K msg cost | $0.05-0.50 | $10-30 | $5-50 |
| Legality | ⚠️ Risky (gray/illegal) | ✅ Fully legal | ✅ Fully legal |
| Rich media | ❌ SMS only | ✅ Full RCS | ✅ Full RCS |
| Branded sender | ❌ Random numbers | ✅ Verified brand | ✅ Verified brand |
| Read receipts | ❌ | ✅ | ✅ |
| SIM management | Complex | None | None |
| Scale limit | SIM blockage risk | Unlimited | Unlimited |

---

## 8. myCRMSIM Business Model Analysis

**What it is**: myCRMSIM is a SIM-based SMS service specifically designed for GoHighLevel (GHL) CRM users, offering "unlimited" SMS without per-message fees.

### How it works:
1. Customer purchases a SIM plan from myCRMSIM (~$10/month per SIM)
2. myCRMSIM ships a physical SIM card to the customer
3. SIM is inserted into myCRMSIM's infrastructure (modem pools at their data center)
4. Customer uses GHL CRM to send/receive SMS via the SIM
5. No per-message fees — only the monthly SIM plan cost

### Business Model:
- **Revenue**: ~$10-20/month per SIM plan
- **Cost**: ~$3-5/month per SIM (India/international SIMs) + infrastructure amortization
- **Margin**: ~50-70% per SIM
- **Key selling point**: Eliminates Twilio/Vonage per-message fees ($0.007-0.01/msg)
- **Break-even for customer**: At ~1,000-1,500 messages/month, myCRMSIM becomes cheaper than Twilio
- **Scale**: Targets small-to-medium agencies using GHL for CRM

### Risks:
- **Legal gray area**: SIM-based SMS businesses operate in regulatory gray zone
- **Carrier detection**: Mobile operators actively detect and block SIM farm traffic
- **SIM blocks**: SIMs get blocked by carriers, requiring constant replacement
- **Deliverability**: SIM farm messages may have lower delivery rates than legitimate A2P routes
- **UK legislation**: Crime and Policing Bill (2025) explicitly criminalizes SIM farms
- **Reputation**: Being associated with SIM farms can damage brand trust

### reachsms
- Similar SIM-based bulk SMS provider
- Offers promotional bulk SMS, transactional SMS
- Provides web panel for sending SMS from PC
- Operates in the gray-market bulk SMS space
- Australian arm (reachsms.com.au) for international customers

---

## 9. Legal Risk Assessment: SIM Farms by Jurisdiction

| Jurisdiction | Legal Status | Penalty | Notes |
|-------------|-------------|---------|-------|
| **United Kingdom** | 🚫 **Criminalized (2025)** | Up to 5 years imprisonment | Crime and Policing Bill 2025 makes possession/supply of SIM farms with no legitimate purpose illegal. Europe's first explicit SIM farm ban. |
| **European Union** | ⚠️ **Gray area / Varies** | Fines, equipment seizure | No EU-wide law. Some countries treat as telecom fraud. Germany may prosecute under telecom law. |
| **United States** | ⚠️ **Gray area** | FCC fines, carrier lawsuits | No federal SIM farm law, but FCC enforces against robocalling. FCC Traced Act. Carrier TOS violations. A2P 10DLC rules make it harder. |
| **India** | ⚠️ **Restricted** | TRAI fines, SIM deactivation | TRAI strictly regulates bulk SMS. DLT registration required. SIM farming may violate telecom license conditions. |
| **China** | 🚫 **Illegal** | Criminal penalties | SIM card registration tightly controlled. Mass SIM possession is illegal. Equipment manufacturers operate in gray zone. |
| **Australia** | ⚠️ **Gray area** | ACMA fines | Australian Communications and Media Authority regulates. SIM farms for spam can face penalties. |
| **Nigeria** | ⚠️ **Restricted** | NCC fines, SIM deactivation | NCC limits to 10 SIMs per person. Biometric registration required. |
| **UAE** | 🚫 **Illegal** | Criminal penalties | Strict telecom regulations. SIM farming is prosecuted. |
| **Russia** | ⚠️ **Gray area** | Fines | "Gray" SMS routes exist but enforcement increasing. |

### UK Specifics (Highest Risk Jurisdiction):
- **Crime and Policing Bill 2025** (Clause 80): Possession of a SIM farm with no legitimate purpose is a criminal offense
- **Definition**: "SIM farm" = device designed/used for sending/receiving large volumes of messages using multiple SIM cards
- **Defense**: Must prove "legitimate purpose" — e.g., telecom testing, R&D
- **Enforcement**: Ofcom and police can seize equipment
- **Impact**: Sets precedent for other jurisdictions to follow

### US Specifics:
- No specific SIM farm federal law
- **FCC** can pursue under Telephone Consumer Protection Act (TCPA) for unsolicited messages
- **Carrier TOS**: Violating carrier terms (using consumer SIMs for A2P) = SIM deactivation
- **10DLC Registration**: Carriers now require registration for A2P messaging, making unregistered SIM-farm traffic stand out
- **Civil risk**: Carriers can sue for tortious interference
- **Secret Service**: Has raided SIM farms in NYC (2025) as part of fraud investigations

---

## 10. Recommended Hardware Setup by Scale

### Scale: 10 SIMs (Small/Beta)

| Component | Product | Cost |
|-----------|---------|------|
| SIM Reader | 2x sysmoOCTSIM | ~$700 |
| Modems | 2x sysmoQMOD (4-modem mPCIe) | ~$600 |
| Software | osmo-remsim (FOSS) | $0 |
| SIM Cards | 10x prepaid | ~$0-100 |
| **Total Setup** | | **~$1,300-1,400** |
| **Monthly** | 10x plans | ~$30-150/mo |

**Best for**: Research, testing, low-volume SMS. Developer/hacker approach.

### Scale: 100 SIMs (Medium/Business)

| Component | Product | Cost |
|-----------|---------|------|
| SIM Bank | 1x Ejointech SIMPOOL-128 | ~$1,000 |
| Modem Pool | 1x Ejointech ACOM632L-32 | ~$2,120 |
| Server | 1U server for management | ~$500 |
| SIM Cards | 100x prepaid | ~$0-600 |
| **Total Setup** | | **~$3,620-4,220** |
| **Monthly** | 100x plans | ~$300-1,500/mo |

**Best for**: Small bulk SMS business. Cost-effective SMS at scale.

### Scale: 500 SIMs (Large/Enterprise)

| Component | Product | Cost |
|-----------|---------|------|
| SIM Bank | 1x Ejointech SIMPOOL-512 | ~$2,000 |
| Modem Pools | 8x Ejointech ACOM632L-32 | ~$16,960 |
| Server | 2U management server | ~$1,500 |
| SIM Cards | 500x prepaid | ~$0-3,000 |
| **Total Setup** | | **~$20,460-23,460** |
| **Monthly** | 500x plans | ~$1,500-7,500/mo |

**Best for**: High-volume SMS operations. Significant legal risk.

### ⚠️ Alternative: RCS at Any Scale (Recommended for Legitimate Business)

| Component | Approach | Cost |
|-----------|---------|------|
| API Provider | Twilio/Sinch/Vonage RCS | No setup fee |
| Per message | ~$0.01-0.05/msg | Variable |
| 1K messages | | $10-50 |
| 100K messages | | $1,000-5,000 |
| 1M messages | | $10,000-50,000 |

**Best for**: Legitimate business messaging. Zero legal risk. Full RCS features.

---

## 11. Break-Even Analysis: When Does SIM-Based Become Cheaper?

### Scenario: US-based operation, SMS only

| Volume (msgs/mo) | SIM-Based (100 SIMs, US) | API RCS (Twilio @ $0.01) | API SMS (Twilio @ $0.0079) | Winner |
|-------------------|--------------------------|--------------------------|---------------------------|--------|
| 10K | $1,630 | $100-300 | $79 | API |
| 50K | $1,630 | $500-1,500 | $395 | API |
| 100K | $1,630 | $1,000-3,000 | $790 | **SIM** (vs RCS), API (vs SMS) |
| 500K | $1,630 | $5,000-15,000 | $3,950 | **SIM** |
| 1M | $1,630 | $10,000-30,000 | $7,900 | **SIM** |
| 5M | $1,630 | $50,000-150,000 | $39,500 | **SIM** |

**Break-even point (SIM vs API RCS at $0.01/msg)**: ~163,000 messages/month
**Break-even point (SIM vs API SMS at $0.0079/msg)**: ~206,000 messages/month

### Scenario: India-based operation, SMS only

| Volume (msgs/mo) | SIM-Based (100 SIMs, India) | API RCS (Twilio @ $0.01) | API SMS (Plivo @ $0.0045) | Winner |
|-------------------|----------------------------|--------------------------|--------------------------|--------|
| 10K | $385 | $100-300 | $45 | API |
| 50K | $385 | $500-1,500 | $225 | **SIM** (vs RCS), API (vs SMS) |
| 100K | $385 | $1,000-3,000 | $450 | **SIM** |
| 500K | $385 | $5,000-15,000 | $2,250 | **SIM** |

**Break-even point (SIM vs API RCS at $0.01/msg)**: ~38,500 messages/month
**Break-even point (SIM vs API SMS at $0.0045/msg)**: ~85,500 messages/month

### But Remember: SIM-Based = SMS Only, No RCS

The break-even analysis only works for **SMS**. SIM banks **cannot deliver RCS messages**. If you need RCS features (rich cards, branded sender, read receipts, interactive buttons), you **must** use an API-based approach.

---

## 12. Summary & Recommendations

### Key Findings:

1. **SIM banks are SMS-only**: No commercially available SIM bank or modem pool supports RCS. RCS requires Android OS + Google Messages + carrier infrastructure, making SIM-based RCS impractical.

2. **SIM-based SMS is 10-100x cheaper** than API-based messaging at scale (especially with India SIMs), but carries significant legal risk.

3. **API-based RCS is the only viable RCS path**: Google RBM, Vonage, Sinch, and Twilio all offer legitimate, fully-featured RCS APIs at $0.005-0.05/message.

4. **Legal landscape is tightening**: UK's 2025 Crime and Policing Bill criminalizes SIM farms. US carriers are increasingly sophisticated at detecting SIM farm traffic. Global trend is toward criminalization.

5. **myCRMSIM model works for SMS**: $10/month unlimited SMS is profitable at 50-70% margins using cheap SIMs, but operates in a legal gray area and risks carrier crackdowns.

### Recommendations:

- **If you need RCS**: Use an API provider (Sinch, Vonage, or Twilio). No SIM-based alternative exists.
- **If you need cheap SMS at massive scale (500K+ msgs/mo)**: SIM-based approach in India is cost-effective but carries legal and operational risk.
- **If you need reliable, legitimate messaging**: API-based approach is the only sustainable long-term strategy.
- **For research/testing**: sysmoOCTSIM is the ideal tool — open-source, well-documented, and designed for legitimate telecom R&D.
- **Hybrid approach**: Use API-based RCS for branded/conversational messages and SIM-based SMS for high-volume notifications (where legally permitted).

---

*Report compiled: May 2026*
*Sources: sysmocom.de, ejointech.shop, openvoxtech.com, dinstar.com, polygator.com, hyperms.com, Google Developers, Vonage, Sinch, Twilio, Infobip, Syniverse, GOV.UK, FCC*
