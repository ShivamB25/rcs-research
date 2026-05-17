# RCS Market Intelligence & Competitive Landscape

**Source**: Firecrawl searches, 2026-05-16

---

## 1. SMOBI - YC-Backed RCS Messaging Startup (YOUR COMPETITOR)

### 1.1 Company Info
- **Name**: Smobi
- **YC Page**: https://www.ycombinator.com/companies/smobi
- **Website**: https://www.smobi.com/
- **Tagline**: "Send texts your customers actually want over RCS"
- **Model**: AI-powered platform for branded, interactive business messaging, starting with RCS
- **Claim**: 5x engagement with interactive & conversational texts over RCS
- **Backend**: Uses **Vonage API** (not SIM-based)
- **Features**: Drag-and-drop builder, API access, built-in compliance
- **Channels**: SMS + RCS

### 1.2 What Smobi Does
- AI-driven SMS & RCS agents without coding
- Drag-and-drop builder for message flows
- Appointment reminders, videos, surveys, carousels, order updates
- Uses **Vonage CPaaS** (pays per-message API fees)
- **NOT SIM-based** - goes through standard RBM/CPaaS channel

### 1.3 Your Advantage vs Smobi
| Factor | Smobi (Vonage) | Your SIM Farm |
|--------|----------------|---------------|
| Cost/msg | ₹0.50-1.00 (Vonage pricing) | ₹0.046 (Year 2+) |
| Scalability | Unlimited (API) | 100 SIMs = 300K-600K msg/mo |
| Legal | 100% legal | Gray area |
| Rich media | Full RBM support | SIP MESSAGE (text only, or MSRP) |
| Verified sender | Yes (RBM brand verification) | No (appears as P2P message) |
| Setup time | Minutes | Weeks (hardware + code) |
| Anti-spam | Built-in (RBM compliance) | Must manage carefully |

### 1.4 Key Insight
**Smobi proves the RCS business messaging market is YC-viable.** But Smobi pays 10-20x more per message than a SIM farm. If you can solve the legal/scaling problems, your cost advantage is massive.

---

## 2. INDIA RCS MARKET - 850% GROWTH IN 2024

### 2.1 Key Statistics
- **850% year-on-year surge** in RCS interactions in India (2024) - Infobip report
- India + China = **30% of global RCS business messages** (2025)
- By 2029: India alone generates **21 billion A2P RCS messages**
- By 2029: RCS = **18% of global operator business messaging revenue** (6x from 3% in 2024)
- 200M+ RCS-enabled users in India (2026)
- Apple adopted RCS in 2024 → massive Android+iPhone interoperability

### 2.2 Jio's Own Data
From Jio's blog: "In 2024, RCS interactions in India surged by a massive 850%. By 2029, India alone is expected to generate 21 billion A2P messages."

### 2.3 Market Implication
- This is the **fastest-growing RCS market in the world**
- 850% growth means the market is still early - perfect for a startup
- CPaaS pricing hasn't compressed yet → SIM farm has maximum cost advantage NOW
- As CPaaS prices drop (competition), SIM farm advantage narrows
- **Window of opportunity: 12-24 months before CPaaS prices compress significantly**

---

## 3. ePDG DISCOVERER TOOL

### 3.1 Spinlogic/epdg_discoverer
- **URL**: https://github.com/Spinlogic/epdg_discoverer
- **Language**: Python
- **What it does**:
  - Resolves ePDG IP addresses from **most mobile operators in the world**
  - Checks if each ePDG responds to ICMP
  - Checks if each ePDG **accepts IKEv2 connection**
- **Also**: https://github.com/francozamp2/epdg_n3iwf_discoverer (fork with 5G N3IWF support)

### 3.2 Use for RCS Farm
- Run this tool to discover Jio/Airtel ePDG addresses automatically
- Test whether IKEv2 is accepted from your Indian datacenter IP
- **Critical for testing before investing in hardware**
- Run from AWS Mumbai to check if Jio/Airtel ePDG accepts your IP

---

## 4. COMPETITIVE POSITIONING

### 4.1 Your Startup vs Existing Players

| Player | Approach | Cost/Msg (India) | Scale | Moat |
|--------|----------|------------------|-------|------|
| Gupshup | CPaaS RBM | ₹0.16-0.65 | Unlimited | 50M+ msg/mo, brand |
| Smobi (YC) | CPaaS Vonage | ₹0.50-1.00 | Unlimited | AI agents, no-code |
| JioCX | Carrier CPaaS | Custom | Unlimited | Jio ecosystem |
| Route Mobile | CPaaS RBM | ₹0.16-0.27 | Unlimited | Enterprise sales |
| **Your SIM Farm** | **Carrier IMS** | **₹0.046** | **600K/mo (100 SIMs)** | **Cost, P2P appearance** |

### 4.2 Your Unique Value Proposition
1. **10-20x cheaper** than any CPaaS provider
2. Messages appear as **P2P (person-to-person)**, not A2P → higher open rates
3. No brand verification needed → faster onboarding
4. Can send from **real Indian mobile numbers** → better deliverability
5. **Anti-spam advantage**: CPaaS RBM messages get filtered; P2P RCS doesn't

### 4.3 Your Risks
1. **Illegal** (SIM farm without proper KYC) - unless corporate postpaid
2. **Limited scale** - 100 SIMs = 300K-600K msg/mo max
3. **No rich media** initially (SIP MESSAGE = text only)
4. **Carrier detection** - Airtel AI, TRAI mandates
5. **Single point of failure** - ePDG/IPsec/SIM management is complex

### 4.4 Recommended Positioning
**"India's cheapest RCS messaging API at ₹0.05/message"**

Position as:
- Alternative to CPaaS for cost-sensitive Indian businesses
- P2P RCS (not RBM) - higher engagement, no brand verification needed
- Simple REST API wrapping the SIM farm complexity
- Target: D2C brands, e-commerce, fintech sending OTP/updates via RCS

---

## 5. IMMEDIATE NEXT STEPS TO VALIDATE

1. **Test ePDG connectivity from AWS Mumbai**
   - Deploy Spinlogic/epdg_discoverer on AWS ap-south-1
   - Run against Jio and Airtel ePDG domains
   - Verify IKEv2 acceptance from Indian datacenter IP

2. **Get 1 Jio SIM + 1 PCSC reader**
   - Buy 1 Jio prepaid SIM (₹1,499/yr)
   - Buy 1 PCSC USB reader (₹500)
   - Install strongSwan-epdg on AWS Mumbai
   - Try EAP-AKA auth to Jio ePDG

3. **If ePDG works → try SIP REGISTER**
   - After IPsec tunnel established
   - Use PJSIP or custom SIP client
   - Send SIP REGISTER to P-CSCF (obtained from ePDG)
   - Handle 401 challenge via sim-rest-server

4. **If SIP REGISTER works → send SIP MESSAGE**
   - After IMS registration (200 OK)
   - Send SIP MESSAGE to another RCS user
   - Verify delivery on target phone

5. **If all works → build MVP with 8 SIMs on 1× sysmoOCTSIM**
   - Cost: ₹27,000 (reader) + ₹11,992 (8 SIMs) + ₹15,000/mo (server)
   - Total: ~₹54,000 + ₹15,000/mo
   - Capacity: 8 SIMs × 100 msg/day = 24,000 msg/mo
   - Revenue at ₹0.10/msg: ₹2,400/mo (not profitable at 8 SIMs)
   - Need 50+ SIMs to break even
