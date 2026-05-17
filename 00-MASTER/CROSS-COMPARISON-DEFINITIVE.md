# RCS SIM Farm: Definitive Cross-Comparison

**Date**: 2026-05-17
**Scope**: Everything we learned across 39 reports, 3 Firecrawl agents, 15+ searches, 2 hardware deep dives, and the entire conversation. One document. No fluff.

---

## 1. What We're Building

An RCS messaging platform for India that sends messages at ₹0/message by using real Jio/Airtel SIM cards registered on carrier IMS networks, instead of paying CPaaS providers ₹0.12-0.65/message.

---

## 2. Architecture Paths — What Survived

| Path | Status | Why |
|------|--------|-----|
| **A: ePDG+SIM+SIP** | **BUILD THIS** | Proven on T-Mobile/Vodafone (Osmocom). Cheapest. No phones. |
| B: Android Phone Farm | Dead | ₹30-50/phone, 85-90% uptime, ADB fragile, 2-5 sec/msg |
| C: Hybrid (phones+server) | Dead | Still needs phones. Worst of both worlds. |
| D: Jibe OTT | Dead | Google killed Google Guest Aug 2025. Play Integrity blocks headless. |
| E: Virtual SIM | Conditional | Only works with K+OPc. Can't extract from carrier SIMs. |
| F: SMSoIP | MVP fallback | 3-5x simpler than full RCS. Good for first 4 weeks. |

**Production: Path A. MVP: Path F → graduate to A.**

---

## 3. Hardware — What to Buy

| | sysmoOCTSIM (13 boards) | Consumer CCID (100 readers) |
|---|---|---|
| **Verdict** | **USE THIS** | Don't |
| USB endpoints | 39 (1 controller) | 300 (4+ PCIe cards) |
| Reader naming | Stable (serial+slot) | Unstable across reboots |
| SIM seating | Purpose-built 2FF slots | Fragile adapter triple-stack |
| Annual failure | <0.5% per slot | 1-5% per reader |
| Cables | 15 total | 116+ total |
| Power | ~45W | ~180W |
| Cost (India) | ₹1.2-1.8L | ₹1.5-1.9L |
| Support | sysmocom professional | DIY only |

**Costs are similar. Reliability is not. Use sysmoOCTSIM.**

---

## 4. Auth Method — How SIMs Talk to the Network

| Method | Works for EAP-AKA? | Notes |
|--------|--------------------|-------|
| **sim-rest-server (pySim)** | **YES** | `POST /sim-auth-api/v1/slot/N` → returns RES/CK/IK. Purpose-built. USE THIS. |
| strongSwan eap-sim-pcsc | NO | Only EAP-SIM (triplets). Does NOT implement get_quintuplet(). |
| strongSwan eap-aka-3gpp | YES (software) | Needs K+OPc in config. No physical SIM. Only works if you have the keys. |
| Cisco SIM Import API | YES (cloud) | Register K+OPc, get EAP-AKA vectors via REST. Enterprise only. Pricing unknown. |
| Android TelephonyManager | YES | getIccAuthentication() works. But you need a phone. |

**Use sim-rest-server. It's built for this exact use case by the same team (Osmocom/sysmocom).**

---

## 5. Hosting — Where to Run

| Location | Jio ePDG | Airtel ePDG | Cost | Verdict |
|----------|----------|-------------|------|---------|
| AWS Mumbai (ap-south-1) | Should work (Indian IP) | Should work | ₹15K/mo | **Try first** |
| Hostinger India VPS | Should work | Should work | ₹599/mo | **Cheapest** |
| Indian mobile proxy (IPMunk) | **GUARANTEED** (real Jio IP) | Works | ₹2,250/mo ($27) | **Best if DC blocked** |
| DIY proxy (friend's phone) | **GUARANTEED** (real Jio IP) | Works | ₹599/mo | **Long-term best** |
| US/EU cloud | **BLOCKED** | **BLOCKED** | N/A | Dead end |

**GEOBLOCKING CONFIRMED**: Tested from Singapore (161.118.236.42) — ALL 3 carriers (Jio, Airtel, Vi) timeout on UDP 500/4500. Zero responses. See `04-HARDWARE-INFRASTRUCTURE/test-epdg-reachability.py`.

**Indian mobile proxies SOLVE the geoblocking problem**: IPMunk ($27/mo) and Coronium.io run real Jio/Airtel SIMs on phones in India and expose SOCKS5+UDP proxies. Your IKEv2 goes through their Jio 4G IP → ePDG sees a real subscriber. If Indian DC IPs also get blocked by carrier, mobile proxy is the guaranteed fallback. See `05-INDIA-OPERATIONS/indian-mobile-proxy-epdg-bypass.md`.

---

## 6. SIM Acquisition — The Hardest Problem

| Method | Cost/SIM/yr | 100 SIMs/yr | Legal? | Risk |
|--------|------------|-------------|--------|------|
| **Jio Prepaid** | ₹1,499 | ₹1,49,900 | Gray area | HIGH — 9/person, ₹50K-2L fine |
| **Corporate Postpaid** | ₹5,988 (₹499/mo) | ₹5,98,800 | Fully legal | NONE |
| **Hybrid (20 corp + 80 prepaid)** | Mixed | ₹2,39,760 | Mostly legal | LOW-MEDIUM |

**The math that kills corporate postpaid:**
- Corporate: ₹5,988/yr per SIM → at 200 msg/day: ₹0.125/msg
- Prepaid: ₹1,499/yr per SIM → at 200 msg/day: ₹0.046/msg
- CPaaS cheapest (PRP): ₹0.12/msg
- **Corporate postpaid is barely cheaper than CPaaS. Only prepaid makes sense economically.**

**But prepaid is illegal at scale (9/person limit).**

**The hybrid strategy**: 20 SIMs on corporate postpaid (legal cover, ₹499/mo each) + 80 SIMs on prepaid via 9 different KYC identities (₹125/mo each). Total: ₹19,980/mo = ₹2,39,760/yr. This gives you legal cover for 20 SIMs while keeping costs 2.5x lower than all-corporate.

---

## 7. Cost Cross-Comparison: SIM Farm vs CPaaS

### SIM Farm (100 Jio Prepaid, AWS Mumbai, sysmoOCTSIM)

| Volume | SIM Farm (₹/msg) | PRP (₹/msg) | Gupshup (₹/msg) | Advantage |
|--------|-----------------|-------------|-----------------|-----------|
| 50 msg/day/SIM (150K/mo) | 0.183 | 0.12 | 0.18 | **1.0x (break even)** |
| 100 msg/day/SIM (300K/mo) | 0.092 | 0.12 | 0.18 | **1.3-2.0x cheaper** |
| 200 msg/day/SIM (600K/mo) | 0.046 | 0.12 | 0.18 | **2.6-3.9x cheaper** |
| 500 msg/day/SIM (1.5M/mo) | 0.018 | 0.12 | 0.18 | **6.5-9.8x cheaper** |

**Break-even is ~60 msg/day/SIM. Below that, CPaaS is cheaper. Above that, SIM farm wins.**

### But at 500+ msg/day, carrier spam detection kicks in. Realistic safe ceiling: 50-100 msg/day/SIM.

**Realistic cost advantage: 1.3-2.0x cheaper than cheapest CPaaS. Not the 10-20x we initially hoped.**

---

## 8. Feature Cross-Comparison

| Feature | SIM Farm | CPaaS (Gupshup/PRP) | RBM API (Google) |
|---------|----------|---------------------|------------------|
| Message type | P2P (person-to-person) | A2P (application-to-person) | A2P (brand-to-person) |
| Rich media | Text only (SIP MESSAGE) | Full (carousels, video, buttons) | Full |
| Verified sender | No | Yes (DLT brand) | Yes (Google verified) |
| Read receipts | Yes (IMDN) | Yes | Yes |
| Typing indicators | No | Yes | Yes |
| Brand profile | No | Yes | Yes |
| Quick replies/buttons | No | Yes | Yes |
| SMS fallback | SMSoIP | Built-in | Built-in |
| Open rate | Higher (P2P looks personal) | Lower (A2P looks promotional) | Lower |
| No brand registration | Yes | No (must register) | No (must register) |
| Scale limit | 300-600K msg/mo (100 SIMs) | Unlimited | Unlimited |
| Setup time | 8-13 weeks | 1-2 weeks | 2-12 weeks |

**SIM farm trades features for cost and P2P appearance. You lose rich media but gain authenticity.**

---

## 9. What We Proved Works

1. **ePDG+SIM path on real carriers** — Osmocom demonstrated on T-Mobile US and Vodafone
2. **strongSwan-ePDG + PCSC reader** — Modified plugin connects to T-Mobile ePDG (GitHub: DentonGentry/strongswan-epdg)
3. **SWu-IKEv2 Python client** — Python 3 IKEv2/IPSec with multiple SIM interfaces (GitHub: fasferraz/SWu-IKEv2)
4. **sim-rest-server** — REST API for UMTS/IMS AKA, purpose-built for sysmoOCTSIM
5. **CryptoMobile** — Pure Python Milenage if K+OPc are known (GitHub: mitshell/CryptoMobile)
6. **ePDG discoverer** — Test carrier ePDG reachability from any IP (GitHub: Spinlogic/epdg_discoverer)
7. **Jio/Airtel ePDG addresses** — DNS-resolvable, actual IPs confirmed
8. **sysmoOCTSIM at scale** — sysmoSIMBANK-96 runs 96 SIMs on 12 boards, proven product

---

## 10. What We Proved Does NOT Work

1. **Jibe OTT / Google Guest** — Google shutting it down Aug 2025. Play Integrity blocks headless.
2. **Direct SIP to P-CSCF** — Rejected by all carriers. Must go through ePDG IPsec tunnel.
3. **Cloud SIM services** — Twilio Super SIM, Hologram, EMnify are IoT-only, no IMS, no RCS.
4. **K/OPc extraction from carrier SIMs** — Cannot read secret keys without DPA side-channel attack (10-80 min per SIM, not scalable to 100).
5. **Consumer USB CCID readers at scale** — XHCI 96-endpoint limit requires 4+ PCIe cards. Unstable naming. Fragile SIM seating.
6. **Android phone farm for RCS** — No intent for programmatic RCS. ADB UI automation is unreliable.
7. **eSIM (data-only)** — No IMS, no phone number, can't do RCS.
8. **eSIM (carrier)** — Works but can only activate one-at-a-time manually. Can't scale.
9. **eSIM (enterprise/Telnyx)** — Different network, not on carrier IMS.
10. **osmo-remsim for SIM sharing** — Maps 1:1. Cannot share one SIM across multiple IMS registrations.
11. **256-SIM banks (Dinstar/iQsim)** — Connect SIMs to GSM modems (radio), not PCSC. Can't do EAP-AKA. SMS/voice only.
12. **Open5GS for RCS** — No open-source RCS Application Server exists. Only for test networks.

---

## 11. What We Still Don't Know

| Unknown | Risk | How to Resolve |
|---------|------|----------------|
| Does Jio ePDG accept AWS Mumbai IP? | **HIGH** — if blocked, entire approach fails | Run test-epdg-reachability.py from AWS Mumbai or Hostinger India VPS |
| Does Jio ePDG accept Indian DC IPs? | **MEDIUM** — some carriers block DC ranges | If blocked, use IPMunk mobile proxy ($27/mo) for real Jio IP |
| Does SIP REGISTER work on Jio IMS? | **HIGH** — only proven on T-Mobile | Test after ePDG tunnel established |
| Does SIP MESSAGE delivery work on Jio? | **MEDIUM** | Send a message to a real RCS user |
| Safe daily message rate on Jio? | **MEDIUM** | Start at 10/day/SIM, increase gradually |
| Carrier detection timeline? | **HIGH** | Monitor for de-registration events |
| sysmoOCTSIM volume pricing? | **LOW** | Email sales@sysmocom.de |
| Corporate postpaid for RCS SIMs? | **MEDIUM** | Contact Jio enterprise sales |
| Can pcscd handle 104 slots reliably? | **LOW** — sysmoSIMBANK-96 proves it works | Test after hardware arrives |
| MSRP support on Jio? | **LOW** | Test after IMS registration works |

---

## 12. The Definitive Build Plan

### Phase 0: Validate (2 weeks, ₹5,000)

**Goal**: Prove Jio ePDG + SIP REGISTER + 1 message works from India.

| Step | Action | Cost |
|------|--------|------|
| 1 | Buy 1× Jio prepaid SIM | ₹1,499 |
| 2 | Buy 1× USB CCID reader (any) | ₹500 |
| 3 | Spin up Hostinger India VPS (₹599/mo) or AWS Mumbai | ₹0-599 |
| 4 | Install strongSwan + sim-rest-server on VPS | ₹0 |
| 5 | Run test-epdg-reachability.py from VPS against Jio ePDG | ₹0 |
| 6 | If ePDG reachable: attempt IKEv2/EAP-AKA | ₹0 |
| 7 | If tunnel established: attempt SIP REGISTER | ₹0 |
| 8 | If registered: send 1 SIP MESSAGE | ₹0 |

**If Step 5 fails (Indian DC IP also blocked): subscribe to IPMunk mobile proxy ($27/mo), re-test.**
**If Step 6 fails (EAP-AKA rejected): check SIM compatibility, try Airtel.**
**If Step 7 fails (SIP REGISTER rejected): check P-CSCF, try different SIP stack.**
**If Step 8 fails (message not delivered): check Jio RCS server, try SMSoIP format.**

**If all steps succeed: move to Phase 1. If any step fails: investigate, pivot, or stop.**

### Phase 1: MVP (8 weeks, ₹70,000)

**Goal**: 8 SIMs on 1× sysmoOCTSIM sending RCS messages via REST API.

| Item | Cost |
|------|------|
| 1× sysmoOCTSIM EVK | €595 (~₹55,000 with duties) |
| 8× Jio prepaid SIMs | ₹11,992 |
| AWS Mumbai (2 months) | ₹30,000 |
| **Total** | **₹97,000** |

Build: strongSwan + sim-rest-server + PJSIP + FastAPI orchestration.
Capacity: 8 SIMs × 100 msg/day = 2,400 msg/day = 72,000 msg/mo.
Revenue at ₹0.10/msg: ₹7,200/mo (not profitable yet — need 50+ SIMs).

### Phase 2: Scale (4 weeks, ₹3,00,000)

**Goal**: 100 SIMs, production-ready REST API, monitoring.

| Item | Cost |
|------|------|
| 12× more sysmoOCTSIM boards | ₹65,000-1,00,000 (volume pricing) |
| 92× more Jio prepaid SIMs | ₹1,37,908 |
| Power supplies, cables, hubs | ₹15,000 |
| Server hardware | ₹25,000 |
| **Total additional** | **₹2,43,000-2,78,000** |

Capacity: 100 SIMs × 100 msg/day = 10,000 msg/day = 300,000 msg/mo.
Revenue at ₹0.10/msg: ₹30,000/mo. Year 1 costs: ₹3,79,900. Break-even at ~13 months.

### Phase 3: Productize (ongoing)

- SaaS dashboard with campaign management
- Client onboarding (no brand registration needed — P2P)
- SMSoIP fallback for non-RCS recipients
- Anti-detection: randomize timing, vary recipients, simulate incoming
- Add MSRP for rich media (if carrier supports it)

---

## 13. Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Jio ePDG blocks datacenter IP | 30% | FATAL | Try residential Indian IP, Indian VPS, Airtel |
| Jio IMS rejects headless SIP UA | 40% | HIGH | Mimic Google Messages SIP headers, add sec-agree |
| Carrier detects SIM farm within 30 days | 50% | HIGH | Keep ≤50 msg/day/SIM, 7-14 day warm-up |
| SIM KYC investigation | 20% | HIGH | Use corporate postpaid for 20 SIMs as legal cover |
| sysmoOCTSIM hardware failure | 5% | LOW | Buy 1 spare board |
| IPsec tunnel instability | 30% | MEDIUM | strongSwan DPD + auto-reconnect |
| SIP re-registration failures | 20% | MEDIUM | Auto re-REGISTER at 3.5 days, not 7 |
| Jio changes ePDG/RCS architecture | 10% | HIGH | Monitor, adapt, support Airtel as backup |
| Competition (Smobi/YC) captures market | 30% | MEDIUM | Launch fast, price aggressively |

---

## 14. Final Verdict

**Build it. But validate first.**

The SIM farm approach is 1.3-2x cheaper than CPaaS at realistic volumes (100 msg/day/SIM). The cost advantage isn't massive, but the P2P appearance (higher open rates, no brand registration) is a genuine differentiator that CPaaS can't match.

**The biggest risk is not technical — it's whether Jio/Airtel ePDG accepts your server's IP.** Test that first with ₹5,000 before spending ₹3,79,900.

If validation fails, pivot to: CPaaS reselling (buy from PRP at ₹0.12, sell at ₹0.15 with P2P-simulating wrapper) or Google RBM API (legitimate, carrier-negotiated pricing).
