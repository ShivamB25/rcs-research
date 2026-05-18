# RCS Research

Complete research dump for building a carrier-IMS-based RCS messaging system using real SIM cards.

**39 reports. 25,000+ lines. One mission: send RCS at ₹0/message.**

---

## Quick Start

Read these first, in order:

1. [`00-MASTER/CROSS-COMPARISON-DEFINITIVE.md`](00-MASTER/CROSS-COMPARISON-DEFINITIVE.md) — **Start here.** Everything from the entire research synthesized into one cross-comparison. What works, what doesn't, costs, risks, the build plan.
2. [`00-MASTER/MEGA-PROMPT-v2.md`](00-MASTER/MEGA-PROMPT-v2.md) — The self-contained build prompt. 6 architecture paths, full technical reference, starter code, carrier data.
3. [`04-HARDWARE-INFRASTRUCTURE/sysmoOCTSIM-deep-dive.md`](04-HARDWARE-INFRASTRUCTURE/sysmoOCTSIM-deep-dive.md) — Hardware decision: why sysmoOCTSIM beats consumer readers.

---

## Folder Structure

### `00-MASTER/`
The executive files. Start here.

| File | Lines | What It Is |
|------|-------|------------|
| `CROSS-COMPARISON-DEFINITIVE.md` | 280 | **THE master document.** All research synthesized. Paths, costs, risks, build plan. |
| `MEGA-PROMPT-v2.md` | 1,458 | Self-contained build prompt. 6 architecture paths, full technical reference, starter code, carrier data, business model. |
| `firecrawl-aggressive-research-summary.md` | 180 | Latest Firecrawl findings: geoblocking, proven implementations, cost models, market intel. |

### `01-ARCHITECTURE/`
How to actually build the thing.

| File | Lines | What You'll Learn |
|------|-------|-------------------|
| `headless-rcs-recipe.md` | 1,510 | 9-step recipe: ISIM read → P-CSCF discover → SIP REGISTER → 401 → SIM auth → AKA-Digest → authenticated REGISTER → presence → messaging. The definitive build guide. |
| `100-sim-farm-build-guide.md` | 1,915 | Three approaches (Headless SIP+SIM, Phone Farm, Hybrid). Full BOMs, code, cost breakdowns. Phase 1-5 build plan. |
| `epdg-vowifi-rcs-prototype.md` | 1,057 | Full stack: strongSwan + sim-rest-server + PJSIP. 8-13 day build estimate. |
| `rcsjta-audit-and-aka-glue-code.md` | 1,710 | RCSJTA source audit + 6 working Python functions for IMS AKA auth. |
| `smsoip-and-ad-platform.md` | 1,991 | SMSoIP (simplest MVP) format + RCS advertising SaaS platform design with pricing tiers. |
| `beeper-bridge-virtual-sim.md` | 1,397 | mautrix/gmessages bridge architecture + Milenage Python for VirtualSIM. |

### `02-PROTOCOL-DEEP-DIVES/`
How the protocols actually work.

| File | Lines | What You'll Learn |
|------|-------|-------------------|
| `rcs-sip-message-msrp-research-report.md` | 547 | SIP MESSAGE pager-mode + MSRP session-mode. SIP MESSAGE alone sufficient for basic RCS. |
| `rcs_acs_provisioning_report.md` | 753 | Full ACS XML parameter reference with actual HTTP request/response formats. |
| `pysim-sim-auth-rest-audit-report.md` | 709 | sim-rest-server REST API: `POST /sim-auth-api/v1/slot/N`. The critical bridge. |
| `ts43-entitlement-eapaka.md` | 789 | TS.43 entitlement bypass with sim-rest-server. |
| `aosp-rcs-ims-audit-report.md` | 380 | ImsService is system API. Cannot be implemented by third-party apps. |
| `google-messages-reverse-engineering.md` | 740 | Proprietary SIP stack. Play Integrity is main blocker. |
| `rcs-credential-extraction-research.md` | 398 | TelephonyManager.getIccAuthentication() as SIM AKA oracle. |
| `open5gs-ims-rcs-analysis-report.md` | 564 | No open-source RCS AS. 4-8 weeks for minimal RCS on self-hosted IMS. |

### `03-CARRIER-INTELLIGENCE/`
What carriers actually do, and how to reach them.

| File | Lines | What You'll Learn |
|------|-------|-------------------|
| `carrier-ims-mapping.md` | 836 | ePDG addresses for 16+ carriers with actual DNS query results. Jio: 49.44.190.248, Airtel: 106.201.214.127. |
| `carrier-ims-registration-testing.md` | 853 | Path A (direct SIP) fails. Path B (ePDG/VoWiFi) works. Proven. |
| `carrier-anti-abuse-rcs-spam.md` | 834 | Safe ceiling ~50-100 msg/day/number. 7-14 day warm-up. GSMA SRS cross-carrier reporting. |
| `jibe-ott-direct-registration.md` | 784 | DEAD. Google shutting down Google Guest Aug-Sep 2025. |
| `jibe-rcs-cloud-protocol-research.md` | 294 | Two paths: carrier-Jibe (standard SIP) and Google Guest (proprietary, shutting down). |
| `google-rbm-api-audit-report.md` | 431 | 7 REST endpoints. Carrier-negotiated pricing ~$0.01-0.05/msg. |

### `04-HARDWARE-INFRASTRUCTURE/`
What to buy and how to plug it in.

| File | Lines | What You'll Learn |
|------|-------|-------------------|
| `sysmoOCTSIM-deep-dive.md` | 583 | **THE hardware decision.** Full specs, PCSC scaling, pricing, 13-board build plan. Verdict: use this, not consumer readers. |
| `consumer-ccid-readers-deep-dive.md` | 400+ | Why 100 consumer readers fail: XHCI 96-endpoint limit, unstable naming, 4x PCIe cards needed. |
| `test-epdg-reachability.py` | 100 | **Run this first.** Python script to test if Indian carrier ePDGs respond to IKEv2 from your IP. If TIMEOUT = you need Indian IP. |
| `sim_bank_hardware_cost_analysis.md` | 389 | sysmoOCTSIM $330-440, Ejointech SIMPOOL-512 $800-2500. |
| `rcs-phone-farm-feasibility-report.md` | 457 | Android phone farm: $30-50/phone, 85-90% RCS uptime. |
| `multisim-opensource-tools.md` | 786 | smsgate, Beeper, TextBee audit. No existing tool supports RCS. |
| `osmo-remsim-remote-sim-for-rcs.md` | 174 | osmo-remsim does NOT reduce SIM count. Only useful for geographic distribution. |
| `commercial-sim-infrastructure-for-rcs.md` | 145 | Cisco SIM Import API, iQsim 256 Rack, Dinstar SIMCloud (human behavior simulation). |

### `05-INDIA-OPERATIONS/`
India-specific: the primary target market.

| File | Lines | What You'll Learn |
|------|-------|-------------------|
| `indian-mobile-proxy-epdg-bypass.md` | 140 | **Indian mobile proxy for ePDG bypass.** IPMunk $27/mo real Jio IP, Coronium.io, SOAX UDP. 3-layer fallback: VPS → mobile proxy → DIY. RFC 8229 (IKE over TCP) via libreswan. |
| `india-epdg-rcs-operational-guide.md` | 194 | Jio/Airtel ePDG addresses, ₹1,499/yr Jio plan, 100-SIM cost ~₹4.7L Year 1. |
| `india-telecom-infrastructure-deep-dive.md` | 143 | **Geoblocking confirmed.** Jio/Airtel block non-India IPs. Must host in India. Corporate postpaid for bulk SIMs. 850% RCS growth in 2024. |
| `india-rcs-pricing-competitive-deep-dive.md` | 122 | PRP Services ₹0.12/msg cheapest CPaaS. SIM farm ₹0.046/msg at scale — 2-8x cheaper. |
| `india-sim-rcs-landscape.md` | 422 | All Indian carriers support RCS. 9-SIM/person limit. DLT mandatory. |

### `06-BUSINESS-COMPETITIVE/`
Market, pricing, and how to make money.

| File | Lines | What You'll Learn |
|------|-------|-------------------|
| `rcs-market-intelligence-competitive-landscape.md` | 132 | Smobi (YC) = RCS via Vonage at ₹0.50-1.00/msg. India 850% growth. 21B A2P messages by 2029. Your advantage: 10-20x cheaper. |
| `rcs-pricing-comparison.md` | 183 | Plivo ~$0.01-0.04/msg cheapest globally. India ₹0.10-0.25/msg. |
| `sim-auth-bypass-virtual-sim-research.md` | 174 | K extraction via DPA (10-80 min). Cisco SIM Import API. osmo-remsim shared mode. Amarisoft software USIM. |

### `07-DEAD-ENDS/`
Things that don't work. Save time by reading these.

| File | Lines | What's Dead |
|------|-------|------------|
| `cloud-sim-services-ims-auth-dead-end.md` | 107 | Twilio Super SIM, Hologram, EMnify, Telnyx, esim.dog — NONE can do carrier IMS. Different networks. |
| `esim-gray-sims-ss7.md` | 818 | eUICC profiles, gray market SIMs, SS7. GSMA PKI blocks consumer eUICCs. |
| `sim-key-extraction-cloning.md` | 856 | K cannot be extracted from carrier SIMs. Programmable SIMs allow VirtualSIM on your own IMS only. |

### `08-RAW-FIRECRAWL/`
Raw agent outputs from Firecrawl deep research.

| File | Lines | Source |
|------|-------|--------|
| `firecrawl-headless-rcs-client-research.md` | 134 | Agent 1: Proven implementations (Osmocom VoWiFi, strongSwan-ePDG, SWu-IKEv2, CryptoMobile). |

### `09-VALIDATION/`
Phase 0 validation — prove it works for ₹3,128 before building the farm.

| File | Lines | What It Is |
|------|-------|------------|
| `phase0-validation-guide.md` | 590 | **DO THIS FIRST.** 1× ACR39U (₹980) + 1× Jio SIM → sim-rest-server → strongSwan → ePDG → IMS → 1 message. Full step-by-step. Osmocom compatibility proof included. |

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Cost per RCS message (SIM farm, 200 msg/day/SIM, Year 2+) | **₹0.046** |
| Cost per RCS message (SIM farm, 100 msg/day/SIM, Year 2+) | **₹0.092** |
| Cost per RCS message (cheapest CPaaS: PRP Services) | ₹0.12 |
| Cost per RCS message (Gupshup) | ₹0.35 |
| Cost per RCS message (Smobi/YC via Vonage) | ₹0.50-1.00 |
| **SIM farm advantage (realistic 100 msg/day)** | **1.3-2x cheaper** |
| **SIM farm advantage (aggressive 200 msg/day)** | **2.6-7x cheaper** |
| ePDG geoblocking | **CONFIRMED** (all 3 Indian carriers, tested May 2026) |
| India RCS growth (2024) | 850% |
| India RCS-enabled users | 200M+ |
| India A2P RCS messages (2029 projected) | 21 billion |
| 100-SIM farm Year 1 cost (prepaid, India) | ₹3,79,900 |
| 100-SIM farm Year 2+ cost (prepaid, India) | ₹3,29,900/yr |

---

## Architecture at a Glance

```
SIM Cards (Jio/Airtel) → sysmoOCTSIM (13 boards, 104 slots)
    → sim-rest-server (pySim REST API for AKA auth)
    → strongSwan-ePDG (IKEv2/EAP-AKA to carrier ePDG)
    → IPsec tunnel → P-CSCF → S-CSCF (carrier IMS core)
    → SIP REGISTER → 401 challenge → SIM computes RES → 200 OK
    → SIP MESSAGE → RCS messaging at ₹0/msg
```

**Must host in India** — Jio and Airtel geoblock ePDG from non-India IPs.

---

## Critical Gotchas

1. **pcscd default limit = 16 readers** — must recompile with `MAX_READERS_CONTEXTS=128`
2. **strongSwan eap-sim-pcsc does NOT support EAP-AKA** — only EAP-SIM. Use sim-rest-server instead.
3. **libccid serializes multi-slot access** — sysmoOCTSIM hardware supports 8 concurrent but driver does 1-at-a-time per board. Fine for RCS.
4. **Consumer USB readers need 4+ PCIe USB cards** — XHCI endpoint limit of 96 per Intel controller, each reader uses 3 endpoints.
5. **Reader names are unstable on consumer readers** — sysmoOCTSIM is stable (serial+slot index).
6. **Jibe OTT is DEAD** — Google shut it down Aug 2025. Carrier IMS is the only path.
7. **Direct SIP to P-CSCF doesn't work** — must go through ePDG IPsec tunnel.
8. **K/OPc cannot be extracted from carrier SIMs** — you need the physical SIM for auth.
9. **ALL Indian carriers geoblock ePDG (CONFIRMED)** — tested May 2026. Jio, Airtel, Vi all timeout from non-India IPs. Server must have Indian IP (VPS or mobile proxy).
10. **9 SIM/person limit in India** — corporate postpaid (₹499/mo) is the legal path but kills economics. Hybrid: 20 corp + 80 prepaid.
11. **Cost advantage is 1.3-2x at realistic volumes** — NOT 10-20x. Break-even at ~60 msg/day/SIM.
12. **256-SIM banks (Dinstar/iQsim) cannot do RCS** — they connect SIMs to GSM modems, not PCSC. Can't do EAP-AKA.
13. **libreswan supports RFC 8229 (IKE over TCP)** — strongSwan doesn't. Use libreswan if you need to route IKEv2 through SOCKS5 proxy.

---

## Research Methodology

- **Phase 1**: Web research on RCS protocol, GSMA specs, open-source implementations, RBM API
- **Phase 2**: 6 parallel worker subagents for deep codebase audits (rcsjta, pySim, AOSP, Open5GS, ACS, SIM banks)
- **Phase 3**: Sequential deep research on 11 topics (SIM key extraction, Google Messages RE, carrier IMS mapping, eUICC/gray SIMs, 100-SIM farm build, Beeper bridge, SMSoIP, carrier IMS testing, ePDG prototype, Jibe OTT, carrier anti-abuse)
- **Phase 4**: India-specific deep research (ePDG addresses, Jio/Airtel VoWiFi, SIM costs, DLT regulations)
- **Phase 5**: 3 Firecrawl agents + 15+ parallel searches (headless RCS client, India telecom, SIM auth bypass)
- **Phase 6**: Hardware deep dives (sysmoOCTSIM vs consumer CCID readers, both with dedicated worker agents using sequential thinking + Context7)
- **Phase 7**: Cross-comparison synthesis + Indian mobile proxy research + ePDG reachability test (CONFIRMED geoblocking)

**Total**: 42+ files, ~28,000 lines, organized in 8-folder structure.

---

## License

This research is provided as-is for educational and research purposes. The authors make no recommendation to violate any laws or carrier terms of service.
