# India RCS Business Messaging Pricing Deep Dive

**Source**: Firecrawl searches + page scrapes, 2026-05-16

---

## 1. Complete India RCS Provider Pricing Matrix

| Provider | RCS Text | RCS Media | RCS Carousel | Conversational | Notes |
|----------|----------|-----------|-------------|----------------|-------|
| **PRP Services** | ₹0.12 | ₹0.16 | ₹0.18 | ₹0.20 | Cheapest published |
| **Route Mobile** | ₹0.16–0.27 | - | - | - | No setup fee, free trial |
| **WABA Connect ref** | ₹0.16–0.20 | - | - | - | Basic text close to SMS |
| **mTalkz Starter** | ₹0.21 | ₹0.38 | ₹0.44 | ₹0.38 | 50K credits min |
| **mTalkz Growth** | ₹0.19 | ₹0.34 | ₹0.39 | ₹0.34 | 200K credits |
| **mTalkz Enterprise** | ₹0.115 | - | - | - | 50K SMS min |
| **Gupshup** | ₹0.35–0.65 | - | - | - | 50M+ msg/mo in India |
| **2Factor** | ₹0.30–0.50 | - | - | - | Competitive with WhatsApp |
| **Kaleyra (Tata)** | ₹0.40+ | - | - | - | Enterprise focused |
| **ValueFirst (Sinch)** | ₹0.28+ | - | - | - | High volume discounts |
| **Tanla/Karix** | ₹0.28+ | - | - | - | Enterprise |
| **JioCX** | Custom | - | - | - | Jio's own CPaaS |
| **EnableX** | - | ₹0.22 | - | ₹0.22 | API-first |
| **Bulky Marketing** | ₹10,000 reg | - | - | - | 200K+ msgs = free reg |
| **Wappie (Scribd ref)** | ₹0.14 | ₹0.18 | - | - | Very cheap |

---

## 2. Key Insights

### 2.1 Cheapest: PRP Services at ₹0.12/message for RCS text
- This is cheaper than bulk SMS (₹0.10-0.15)
- RCS text only, no media

### 2.2 Your SIM-based RCS Cost: ₹0/message
- If you register on carrier IMS with physical SIMs
- Only cost is SIM + plan (₹1,499/yr Jio)
- 100 SIMs × ₹1,499 = ₹149,900/yr = ₹12,492/mo
- At 50 msg/day/SIM: 150,000 msg/mo → ₹0.083/msg all-in
- At 100 msg/day/SIM: 300,000 msg/mo → ₹0.042/msg all-in
- At 200 msg/day/SIM: 600,000 msg/mo → ₹0.021/msg all-in

### 2.3 vs CPaaS Providers at Scale
| Volume (msg/mo) | SIM Farm (100 SIMs) | PRP @ ₹0.12 | Gupshup @ ₹0.35 |
|-----------------|---------------------|--------------|------------------|
| 150,000 | ₹0.083 | ₹18,000 | ₹52,500 |
| 300,000 | ₹0.042 | ₹36,000 | ₹105,000 |
| 600,000 | ₹0.021 | ₹72,000 | ₹210,000 |
| 1,000,000 | ₹0.012 | ₹120,000 | ₹350,000 |

**SIM farm is 2-8x cheaper than CPaaS at scale.**

---

## 3. JioCX - Jio's Own RCS CPaaS

- **URL**: https://www.jiocx.com/products/rcs-messaging-api
- **Parent**: Jio Platforms / Reliance
- **Channels**: SMS, RCS, Email, WhatsApp, Voice
- **Integration**: APIs, custom integrations
- **Pricing**: Not published (enterprise/custom)
- **Note**: This is the OFFICIAL Jio RCS business messaging platform
- **Key**: JioCX goes through the proper RBM (RCS Business Messaging) channel, NOT carrier IMS
- **Difference**: RBM = brand-to-consumer (verified sender), carrier IMS = P2P (person-to-person)

---

## 4. India Regulatory Environment

### 4.1 SIM Card Limits (Telecom Act 2023)
- **9 SIMs per person** nationwide
- **6 SIMs** in J&K, Assam, Northeast
- **First violation**: Fine up to ₹50,000
- **Subsequent violations**: Fine up to ₹2,00,000 + possible jail
- **Using fake documents**: Jail time

### 4.2 SIM Box/SIM Farm Detection
- TRAI February 2025 regulation mandates SIM Farm/SIM Box detection
- AI-powered detection by Airtel (launched Sept 2024)
- Cross-carrier reporting via GSMA SRS

### 4.3 New Messaging Regulations (Dec 2025)
- India orders messaging apps to work only with active KYC SIMs
- 6-hour logout requirement for unverified SIMs
- Directly impacts SIM farm viability - registered SIMs must stay active with KYC

### 4.4 DLT Registration
- All business messaging requires DLT (Distributed Ledger Technology) registration
- Templates must be pre-approved
- Sender IDs registered per operator

---

## 5. SIM Farm Feasibility Assessment for India

### 5.1 Can You Get 100 Jio SIMs?
- 9 per person → need 12 people's KYC
- Each person must have valid Aadhaar + photo
- SIMs must be activated with biometric verification at Jio store
- **Risk**: ₹50K-2L fine per violation if any KYC is irregular

### 5.2 SIM Box Detection Risk
- Airtel has AI-powered detection (Sept 2024)
- TRAI Feb 2025 mandates detection for all carriers
- Unusual call patterns (no incoming, all outgoing SMS) are red flags
- **Mitigation**: Simulate normal usage patterns (receive some calls, vary timing)

### 5.3 RCS-Specific Risks
- RCS over IMS doesn't generate traditional A2P SMS traffic
- Harder to detect than SIM box SMS blasting
- But: carrier can see SIP registration patterns from datacenter IPs
- **Key risk**: ePDG connections from non-phone IP ranges (AWS/GCP)

---

## 6. Competitive Landscape - Existing Players

### 6.1 No Indian startup is doing SIM-based RCS messaging
- All existing players use RBM API (Google's RCS Business Messaging)
- RBM goes through Google's Jibe hub → carrier RCS servers
- No one is doing direct carrier IMS RCS from SIMs

### 6.2 This is a genuine innovation gap
- SIM-based RCS is technically possible but no one is doing it commercially
- The legal gray area is the main deterrent
- If you can navigate the regulatory environment, you have a moat

---

## 7. Cost Comparison Summary

| Approach | Cost/Msg (India) | Scale Limit | Legal Risk |
|----------|------------------|-------------|------------|
| CPaaS (PRP) | ₹0.12 | Unlimited | None |
| CPaaS (Gupshup) | ₹0.35–0.65 | Unlimited | None |
| RBM API (Google) | $0.01–0.05 | Unlimited | None |
| SIM Farm (100 SIMs, 100 msg/day) | ₹0.042 | ~300K/mo | HIGH |
| SIM Farm (100 SIMs, 50 msg/day) | ₹0.083 | ~150K/mo | HIGH |
| JioCX (Enterprise) | Custom | Unlimited | None |
