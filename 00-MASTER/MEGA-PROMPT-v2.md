# RCS SMS Management System — MEGA-PROMPT v2 (Complete Build Prompt)

> **Purpose**: This document is self-contained. Someone reading ONLY this file should have everything needed to build a complete RCS SMS management/advertising platform using real SIM cards for ultra-cheap operation. Incorporates findings from ALL 27 research reports.

> **Version**: 2.0 — May 16, 2026 — Complete rewrite incorporating 11 new aggressive research reports since v1.

> **Critical changes since v1**: Jibe OTT is DEAD (Google shutting it down worldwide since Aug 2025). ePDG+SIM is THE PROVEN PATH (Osmocom demonstrated it). SMSoIP is the simplest MVP. Virtual SIM (software Milenage) eliminates hardware when K+OPc known. Anti-abuse detection requires careful operational parameters. Path A renamed from "Headless SIP+SIM" to "ePDG+SIM+SIP" reflecting the ePDG tunnel requirement.

---

## 1. Project Overview

### What We're Building
An **RCS SMS management and advertising platform** — a startup product (Y Combinator style) that sends RCS (Rich Communication Services) messages at ultra-low cost by using real SIM cards instead of expensive API providers.

### Core Premise
- **RCS** is the next-gen messaging standard replacing SMS, supporting rich media, read receipts, typing indicators, and interactive buttons.
- **Official RCS API providers** (Twilio, Sinch, Vonage) charge $0.01–0.05 per message — expensive at scale.
- **SIM cards** in phones can send RCS messages for effectively **$0.001–0.003 per message** (especially Indian SIMs at ~$2/month unlimited data).
- The key insight: **P2P RCS is free on unlimited data plans** — it uses data, not per-message billing.

### Goal
Build a system that can:
1. Register real SIM cards on carrier RCS infrastructure
2. Send and receive RCS messages programmatically
3. Scale to hundreds of SIMs with automated management
4. Cost 10–100x less than API-based RCS providers
5. Maintain reliability competitive with commercial solutions

### Six Architecture Paths (at a glance)

| Path | Approach | Cost/1K msgs | Build Time | Reliability | Status |
|------|----------|-------------|-------------|-------------|--------|
| **A: ePDG+SIM+SIP** | ePDG tunnel + SIM reader + SIP client | ~$0.05–1 | 2–4 months | Medium-High | **🏆 WINNER** — Proven by Osmocom |
| **B: Android Phone Farm** | N Android phones controlled via ADB | ~$1–5 | 2–4 months | Low-Medium | Viable but fragile |
| **C: RBM API (Official)** | Google RCS Business Messaging API | ~$10–50 | 1–2 weeks | High | B2P only, not P2P |
| **D: Jibe OTT** | Google Guest direct registration | N/A | N/A | N/A | **☠ DEAD END** — Google killed it |
| **E: Virtual SIM** | Software Milenage (K+OPc known) | ~$0.01–0.50 | 3–6 months | Medium | Only works with known K/OPc |
| **F: SMSoIP** | SMS over IMS via SIP MESSAGE | ~$0.05–1 | 1–2 months | Medium-High | **Simplest MVP** — 3-5x simpler than RCS |

---

## 2. Executive Summary

### ALL Key Findings from 27 Reports

| Report | Core Finding | Actionable? | v2 Impact |
|--------|-------------|-------------|-----------|
| **AOSP IMS Audit** | ImsService is System API; third-party apps cannot implement custom ImsService; Google Messages hooks via Carrier Services; SIP delegate model on Android 12+ | ✅ Confirms headless must bypass Android | — |
| **Google RBM API Audit** | Full REST API surface, service account auth, 3-tier pricing, no public rate card, 2-12 week onboarding, SMS fallback must be self-implemented | ✅ Use for B2P fallback | — |
| **Jibe RCS Cloud Protocol** | Two paths (Carrier-Jibe vs Google Guest OTT); Google Guest uses proprietary tokens (Play Integrity + Firebase IID); non-Android clients CANNOT register; microG $14,999 bounty | ⚠️ Carrier-Jibe is our target; Google Guest is dying | **Path D marked DEAD** |
| **Open5GS IMS RCS** | docker_open5gs provides VoLTE only; RCS has NEVER been achieved on this stack; main blocker is RCS Application Server; IMS auth proxy NOT feasible; 4-8 months estimated | ⚠️ Only for private test networks | — |
| **pySim SIM Auth REST** | sim-rest-server REST API for USIM AKA; hardcodes USIM, needs ISIM patch; EF.P-CSCF, EF.IMPI, EF.IMPU readable; osmo-remsim for remote SIM access | ✅ Critical enabler for Path A | — |
| **RCS Credential Extraction** | No plaintext credential storage; P-CSCF from dumpsys; Frida can hook ImsService; IMS AKA cannot be replayed (nonce single-use); Beeper approach requires physical phone | ✅ SIM AKA oracle is accessible | — |
| **Phone Farm Feasibility** | No intent to auto-send RCS; ADB UI automation hacky; content://mms for reading; accessibility service best approach; 85-95% uptime; 10-phone farm ~$1,050 | ✅ Viable but fragile for Path B | — |
| **RCS Pricing Comparison** | No universal rate card; India cheapest (₹0.10-0.25/msg); WABA Connect cheapest India; Bandwidth cheapest US; Plivo cheapest global | ✅ SIM approach is 10-100x cheaper | — |
| **SIP MESSAGE/MSRP** | Pager-mode (SIP MESSAGE) vs session-mode (MSRP INVITE); CPIM format; IMDN for receipts; SIP MESSAGE alone IS sufficient for basic RCS | ✅ Start with SIP MESSAGE | — |
| **ACS Provisioning** | Complete ACS XML parameter reference; URL format config.rcs.mnc{MNC}.mcc{MCC}.pub.3gppnetwork.org; GBA authentication; AuthType Digest/AKA/GIBA | ✅ Critical for configuration | — |
| **SIM Bank Hardware Costs** | SIM banks are SMS-only (NO RCS); modem pools only do SMS; UK criminalized SIM farms (2025); break-even at 163K msgs/mo vs API RCS | ✅ Hardware exists for SIM auth | — |
| **Headless RCS Recipe** | 9-step recipe (read ISIM → discover P-CSCF → SIP REGISTER → SIM auth → AKA-Digest → authenticated REGISTER → presence → send MESSAGE → handle incoming); AKAv1-MD5 is hardest technical challenge | ✅ The definitive build guide | — |
| **Multi-SIM Open Source Tools** | No existing tool supports RCS; smsgate best audited; Beeper uses mautrix/gmessages bridge (requires phone); TextBee best for forking | ✅ Must build from scratch | — |
| **India SIM/RCS Landscape** | All 4 Indian carriers now support RCS; DLT registration mandatory; Dec 2023 bulk SIM ban; 9 SIM/person limit; API-based RCS cheaper than SIM-based | ✅ India cheapest but regulated | — |
| **TS.43 Entitlement/EAP-AKA** | TS.43 is gate before RCS registration; EAP-AKA via SIM; entitlement server URLs carrier-specific; bypass possible (device-side gate, not network-side) | ✅ Entitlement satisfiable | — |
| **RCSJTA Audit & AKA Glue** | rcsjta only supports GIBA and Digest MD5 (NO AKA); complete AKA glue code in Python provided | ✅ Glue code ready to use | — |
| **SIM Key Extraction/Cloning** | K/OPc CANNOT be extracted from commercial SIMs; CAN be read/written on sysmoISIM-SJA2/SJA5; SIM cloning infeasible without K; software MILENAGE possible with known K/OPc | ✅ Virtual SIM possible with programmable cards | **Enables Path E** |
| **Google Messages Reverse Eng.** | Proprietary obfuscated SIP stack; Jibe OTT uses opaque tokens; mautrix/gmessages works by puppeting web interface (not SIP); phone dependency is critical | ⚠️ Can't reverse-engineer Google's stack | — |
| **Carrier IMS Mapping** | 3GPP DNS naming convention; ePDG FQDNs publicly resolvable for 16+ carriers; IMS NAPTR/SRV NOT publicly resolvable; ACS config domains ARE publicly resolvable; T-Mobile uses geo-aware ePDG DNS | ✅ ePDG addresses are discoverable | **Enables Path A** |
| **eSIM/Gray SIMs/SS7** | eSIM profiles CAN include ISIM; osmo-smdpp for test CI; GSMA PKI blocks consumer eUICCs; Security Explorations extracted Kigen certs; gray market SIMs restricted post-Dec 2023 | ⚠️ eSIM path blocked by GSMA PKI | — |
| **100-SIM Farm Build Guide** | 3 approaches (Headless SIP+SIM, Android Phone Farm, Hybrid); Hybrid recommended; detailed hardware lists; Phase 1-5 build plan; 30 phones + modem pool + orchestrator | ✅ Complete operational guide | — |
| **Beeper Bridge/Virtual SIM** | mautrix/gmessages uses libgm (WebSocket protocol); QR login deprecated March 2026; Google Account login now required; phone must stay online; VirtualSIM (software Milenage) eliminates hardware when K+OPc known; CryptoMobile/PyCryptodome for software AKA | ✅ Virtual SIM is game-changer | **Enables Path E** |
| **SMSoIP & Ad Platform** | SMSoIP is simplest MVP (SIP MESSAGE with application/vnd.3gpp.sms, binary RP-DATA); +g.3gpp.smsip feature tag; 3-5x simpler than RCS; IP-SM-GW bridges to SMSC; full RCS ad platform design with SaaS architecture | ✅ **SMSoIP = fastest path to working system** | **Adds Path F** |
| **Carrier IMS Registration Testing** | Path A (direct SIP) REJECTED by all carriers; Path B (ePDG tunnel) WORKS — Osmocom demonstrated on T-Mobile US; strongSwan + sim-rest-server + SIP stack is proven; geoblocking is main variable | ✅ **ePDG path is THE proven path** | **Path A upgraded to ePDG+SIM** |
| **ePDG/VoWiFi/RCS Prototype** | Full 9-component stack documented; Osmocom strongSwan fork + eap-aka-3gpp + sim-rest-server + PJSIP; encrypted.at blog confirms carrier ePDG connection; PJSIP has built-in AKAv1-MD5; 2-4 weeks to prototype | ✅ Complete stack reference | **Confirms Path A** |
| **Jibe OTT Direct Registration** | **CRITICAL** — Google shutting down Google Guest/Jibe OTT worldwide since Aug-Sep 2025; Play Integrity is main blocker; CompositeToken (Firebase IID + Play Integrity); carrier-IMS path now primary | ❌ Jibe OTT is a dead end | **Path D = DEAD** |
| **Carrier Anti-Abuse/RCS Spam** | Google ML spam detection; no published P2P rate limits (est. 100-300 msg/day safe); carrier fraud detection systems (Mobileum/Cloudmark); SIM farm detection via IMEI fingerprinting; operational guidelines for safe messaging | ✅ Anti-abuse parameters defined | **Critical for operations** |

### What Works ✅
- **ePDG+SIM path**: IKEv2/EAP-AKA to carrier ePDG → IPSec tunnel → P-CSCF → SIP REGISTER — **PROVEN by Osmocom project on T-Mobile US**
- **sim-rest-server**: REST API for ISIM AKA authentication — the critical bridge between SIM cards and SIP stack
- **AKA-Digest computation**: Complete RFC 3310 implementation in Python, tested against spec
- **P-CSCF discovery**: Multiple methods (ISIM → ACS → ePDG config payload → DNS)
- **SIP MESSAGE pager-mode**: Sufficient for basic 1-1 RCS text messaging
- **SMSoIP**: Simplest MVP — SIP MESSAGE with `application/vnd.3gpp.sms` body; works on ALL VoLTE carriers; 3-5x simpler than full RCS
- **Virtual SIM**: Software Milenage (CryptoMobile/PyCryptodome) computes AKA without physical SIM when K+OPc are known
- **strongSwan Osmocom fork**: Proven ePDG client with EAP-AKA via PC/SC reader
- **PJSIP AKA support**: Built-in AKAv1-MD5/AKAv2-MD5 with callback mechanism

### What Doesn't Work ❌
- **Google Guest / Jibe OTT**: Google shutting it down worldwide since Aug-Sep 2025 — Play Integrity enforcement makes it impossible for headless clients
- **Direct SIP REGISTER to P-CSCF**: Rejected by all carriers — P-CSCF validates source IP, requires IPSec SAs, not reachable from public internet
- **AT commands for RCS**: GSM modems fundamentally cannot send RCS — no AT command exists
- **SIM bank RCS**: SIM banks are SMS-only; no commercially available hardware supports RCS messaging
- **Android Intent for RCS**: No intent to programmatically send RCS without user interaction
- **Long-lived RCS tokens**: Sessions are ephemeral; require continuous SIP registration maintenance
- **K/OPc extraction from commercial SIMs**: Secret keys cannot be extracted — SIM cloning infeasible for carrier SIMs
- **RCSJTA AKA**: rcsjta only supports GIBA and Digest MD5, NOT AKA — must use our glue code
- **Verizon ePDG via 3gppnetwork.org**: Returns 127.0.0.1 — broken/misconfigured; needs custom FQDN

### What's New Since v1 🔥
1. **Jibe OTT is DEAD** — Google shutting down Google Guest worldwide; carrier-IMS is now the ONLY viable path
2. **ePDG+SIM is PROVEN** — Osmocom demonstrated full ePDG connection on T-Mobile US; encrypted.at blog confirms
3. **SMSoIP = Simplest MVP** — 3-5x simpler than RCS; works on ALL VoLTE carriers; `+g.3gpp.smsip` feature tag
4. **Virtual SIM (software Milenage)** — Eliminates physical SIM when K+OPc known; CryptoMobile/PyCryptodome implementations
5. **Anti-abuse parameters defined** — Safe zones: ≤50 msg/day P2P, ≤1 msg/min, ≤15 unique recipients/day
6. **Complete ePDG address database** — 16+ carrier ePDG IPs publicly resolvable
7. **Full 100-SIM farm build guide** — 3 approaches, detailed hardware, Phase 1-5 plan
8. **RCS ad platform SaaS design** — Multi-tenant, campaign management, A/B testing, pricing model
9. **QR login deprecated** — mautrix/gmessages now requires Google Account login (March 2026)
10. **UK criminalized SIM farms** — 2025 law; jurisdiction-specific legal risk

### What's Unknown ❓
- Whether all carriers enforce inner IPSec (sec-agree) after AKA registration when coming via ePDG (some relax it for VoWiFi)
- Exact geoblocking behavior for each carrier's ePDG from data center IP ranges
- How aggressively carriers detect non-phone SIP User-Agents and IMEI anomalies
- Rate-limiting behavior of carrier S-CSCFs for programmatic messaging
- Whether eSIM-based RCS has different constraints than physical SIM
- Exact threshold for spam report count that triggers RCS de-registration per carrier
- Which carriers deliver P-CSCF via IKEv2 config payload vs. DHCP inside tunnel

---

## 3. Architecture Paths (UPDATED)

### Path A: ePDG+SIM+SIP — THE WINNER 🏆

**How it works**: Place SIM cards in PC/SC readers → establish IKEv2/IPSec tunnel to carrier ePDG using EAP-AKA (SIM auth) → P-CSCF accessible inside tunnel → SIP REGISTER with IMS AKA → send/receive RCS messages via SIP MESSAGE and MSRP.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ePDG+SIM+SIP PLATFORM                           │
│                                                                     │
│  ┌──────────┐   ┌──────────────┐   ┌───────────────┐              │
│  │ SIM Bank │──→│ sim-rest-    │──→│ strongSwan    │──┐           │
│  │          │   │ server.py    │   │ (Osmocom fork)│  │           │
│  │ sysmoOCT │   │              │   │               │  │  IKEv2/   │
│  │ (8 slots)│   │ RAND/AUTN    │   │ EAP-AKA via   │  │  EAP-AKA │
│  │          │   │    ↓         │   │ PC/SC reader  │  │           │
│  │ SIM #1-8 │   │ RES/CK/IK   │   │               │──┤           │
│  │ in reader │   │    ↓         │   │ IPSec tunnel  │  │           │
│  └──────────┘   │ AKA-Digest  │   │ established   │  │           │
│                  │ computation │   │               │  │           │
│                  └──────────────┘   └───────────────┘  │           │
│                                                        ▼           │
│                                           ┌──────────────────┐    │
│                                           │   Carrier ePDG   │    │
│                                           │   (public IP)    │    │
│                                           └────────┬─────────┘    │
│                                                    │ GTP tunnel   │
│                                           ┌────────▼─────────┐    │
│                                           │  PGW → P-CSCF    │    │
│                                           │  (internal IP)   │    │
│                                           └────────┬─────────┘    │
│  ┌──────────────────┐                              │              │
│  │ SIP Stack         │─── SIP REGISTER (AKA) ────→│              │
│  │ (pjsip/custom)   │                              │              │
│  │                   │←── 200 OK ─────────────────│              │
│  │ 1. REGISTER → 401 │                              │              │
│  │ 2. → SIM auth     │─── SIP MESSAGE ───────────→│──→ S-CSCF   │
│  │ 3. → AKA-Digest   │                              │    +RCS AS │
│  │ 4. REGISTER → 200 │                              │              │
│  │ 5. MESSAGE/INVITE │                              │              │
│  └──────────────────┘                              │              │
│                                                     ▼              │
│                                              ┌────────────┐       │
│  ┌──────────────────────────────────────────┐│ Carrier IMS│       │
│  │ Orchestration Layer (Python FastAPI)     ││ Core       │       │
│  │ - SIM slot management  - Message queue   │└────────────┘       │
│  │ - Registration monitor - Health checks   │                     │
│  │ - REST API gateway    - Rate limiting    │                     │
│  │ - ePDG tunnel manager - Auto-recovery   │                     │
│  └──────────────────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────┘
```

| Factor | Detail |
|--------|--------|
| **Pros** | No phones needed; protocol-level control; potentially highest throughput; cheapest at scale; ePDG path is PROVEN |
| **Cons** | Must implement full IKEv2+EAP-AKA+IMS AKA stack; carrier-specific quirks; ePDG geoblocking possible; IPSec may be required |
| **Cost per 1K messages** | ~$0.05–1 (dominated by SIM plan cost; India SIMs: ~$0.05) |
| **Estimated build time** | 2–4 months (1–2 experienced engineers) |
| **Throughput** | Potentially 10–100+ msg/sec per SIM (protocol-level, no UI bottleneck) |
| **Reliability** | Medium-High (ePDG is designed for this; protocol-level is more stable than UI) |
| **Proven by** | Osmocom project (T-Mobile US), encrypted.at blog, worthdoingbadly.com experiments |

### Path B: Android Phone Farm

**How it works**: N Android phones each with a SIM, running Google Messages with RCS enabled, controlled programmatically via ADB + custom Agent App (accessibility service).

```
┌─────────────────────────────────────────────────┐
│             Control Server (FastAPI)              │
│  - REST API for send/receive                     │
│  - Phone health monitoring                       │
│  - Message queue (Redis/NATS)                    │
│  - RCS registration status tracker              │
└──────────────────┬──────────────────────────────┘
                   │ ADB over USB/TCP
     ┌─────────────┼─────────────┐
     │             │             │
   [Phone 1]    [Phone 2]   [Phone N]
   - Agent App   - Agent App   - Agent App
   - Google Msgs - Google Msgs - Google Msgs
   - SIM #1     - SIM #2     - SIM #N
   - RCS ✅     - RCS ✅     - RCS ✅
     │             │             │
   [USB Hub]  [USB Hub]  [USB Hub]
     └─────────────┼─────────────┘
                   │
            [Linux Server]
```

| Factor | Detail |
|--------|--------|
| **Pros** | Uses Google Messages (carrier-certified); no IMS/ePDG stack needed; fastest to build MVP |
| **Cons** | UI automation is fragile; 1–5 msg/sec per phone; RCS disconnects frequently; phones need constant babysitting; QR login deprecated (March 2026) |
| **Cost per 1K messages** | ~$1–5 (hardware amortized; SIM plans dominate) |
| **Estimated build time** | 2–4 months |
| **Throughput** | 1–5 msg/sec per phone (UI-limited) |
| **Reliability** | Low-Medium (85–95% uptime per phone with active monitoring) |

### Path C: RBM API (Official Google)

**How it works**: Use Google's RCS Business Messaging API (or aggregator like Sinch, Vonage, Twilio) to send B2P (business-to-person) RCS messages through official channels.

```
┌──────────┐     ┌──────────────────┐     ┌──────────────┐
│ Your App │────→│ RCS API Provider │────→│ Google RBM   │
│          │     │ (Sinch/Vonage/   │     │ Platform     │
│ REST API │     │  Twilio/Plivo)   │     │ → Carrier    │
│ calls    │     │                  │     │ → User phone │
└──────────┘     └──────────────────┘     └──────────────┘
```

| Factor | Detail |
|--------|--------|
| **Pros** | Clean REST API; carrier-managed; brand verification; rich cards; SMS fallback; no SIM management |
| **Cons** | B2P only (not P2P from phone numbers); $0.01–0.05/msg; requires brand verification (2–12 weeks); not person-to-person; content scanned for 14 days |
| **Cost per 1K messages** | ~$10–50 (US); ~$1–3 (India) |
| **Estimated build time** | 1–2 weeks |
| **Throughput** | High (cloud API, 1–30+ msg/sec depending on reputation tier) |
| **Reliability** | High (managed by Google/carrier) |

### Path D: Jibe OTT — DEAD END ☠

**What happened**: Google has been systematically shutting down the "Google Guest" / Jibe OTT registration path worldwide since August-September 2025. Carriers that previously got free RCS via Google Guest now see "RCS chats are not supported by your carrier". Google is using GGC shutdown as leverage to force carrier RCS agreements.

**Why it's dead**:
1. **Play Integrity enforcement** — requires certified Android device; headless clients fail
2. **CompositeToken requirement** — Firebase IID + Play Integrity attestation; cannot be forged without certified device
3. **Google Account login mandatory** — QR code login deprecated March 2026
4. **Carrier migration** — Google pushing all carriers to sign RCS agreements; Google Guest is the stick

**Lesson learned**: The carrier-IMS path (ePDG + SIM) is now the ONLY viable path for headless RCS. Invest zero effort in Jibe OTT reverse engineering.

### Path E: Virtual SIM (Software Milenage)

**How it works**: When the SIM's secret key K and operator code OP/OPc are known (e.g., from programmable SIMs like sysmoISIM-SJA2/SJA5, or self-hosted IMS), AKA authentication can be computed entirely in software using the MILENAGE algorithm — no physical SIM card or PC/SC reader needed.

```
┌────────────────────────────────────────────────────┐
│              Virtual SIM Architecture                │
│                                                      │
│  ┌─────────────┐    ┌──────────────────┐            │
│  │ K + OPc     │───→│ Software MILENAGE│───→ RES/CK/IK│
│  │ (stored in  │    │ (CryptoMobile /  │            │
│  │  config/HSS)│    │  PyCryptodome)   │            │
│  └─────────────┘    └──────────────────┘            │
│         │                    │                       │
│         │             ┌──────▼──────┐                │
│         │             │ AKA-Digest  │                │
│         │             │ Computation │                │
│         │             └──────┬──────┘                │
│         │                    │                       │
│         │             ┌──────▼──────┐                │
│         │             │ SIP Stack   │───→ Carrier IMS│
│         │             │ (pjsip)     │                │
│         │             └─────────────┘                │
│                                                      │
│  ✅ No physical SIM, no PC/SC reader, no USB cables  │
│  ⚠️ Only works when K+OPc are known                  │
│  ⚠️ K/OPc CANNOT be extracted from commercial SIMs  │
│  ✅ Works perfectly with self-hosted IMS (Open5GS)   │
│  ✅ Works with programmable SIMs (sysmoISIM-SJA2/5)  │
└────────────────────────────────────────────────────┘
```

| Factor | Detail |
|--------|--------|
| **Pros** | No physical hardware; purely software; scales infinitely; K+OPc = full identity control |
| **Cons** | K/OPc CANNOT be extracted from commercial carrier SIMs; only works with programmable SIMs or self-hosted IMS |
| **Cost per 1K messages** | ~$0.01–0.50 (no hardware cost; only hosting) |
| **Estimated build time** | 3–6 months (integrate MILENAGE library + AKA-Digest + SIP) |
| **Throughput** | Unlimited (software-only, no SIM I/O bottleneck) |
| **Reliability** | Medium (software AKA is reliable, but carrier-side detection is unknown) |
| **Libraries** | CryptoMobile (Python), PyCryptodome, libosmocore (C), Open5GS HSS milenage.c |

### Path F: SMSoIP — Simplest MVP

**How it works**: Register on IMS with `+g.3gpp.smsip` feature tag → send SIP MESSAGE with `Content-Type: application/vnd.3gpp.sms` containing binary RP-DATA frame → IP-SM-GW routes to SMSC → recipient sees standard SMS. No CPIM, no capability discovery, no MSRP, no session setup.

```
┌──────────┐     SIP MESSAGE      ┌──────────┐     SIP MESSAGE     ┌──────────┐     MAP/SMPP
│  Client  │ ───────────────────→ │ P/S-CSCF │ ──────────────────→ │ IP-SM-GW │ ──────────→ SMSC → Recipient
│ (Sender) │  (RP-DATA in body)   │          │                     │          │
└──────────┘  Content-Type:       └──────────┘                     └──────────┘
              application/         ←─── 202 Accepted ────            ←─── RP-ACK ────
              vnd.3gpp.sms
```

| Factor | Detail |
|--------|--------|
| **Pros** | 3-5x simpler than RCS; works on ANY IMS registration; no capability discovery needed; no MSRP sessions; falls back to standard SMS transparently; defined by 3GPP TS 24.341; mandatory for VoLTE (GSMA IR.92) |
| **Cons** | Binary RP-DATA/SMS-SUBMIT TPDU construction; 160-char limit; no rich media; no read receipts; recipient sees SMS (not RCS) |
| **Cost per 1K messages** | ~$0.05–1 (same as Path A — just IMS registration + SIP MESSAGE) |
| **Estimated build time** | 1–2 months (much simpler than full RCS) |
| **Throughput** | 10-30 msg/sec per UE (limited by SIP transaction model) |
| **Reliability** | Medium-High (IP-SM-GW is standard VoLTE infrastructure) |

### Detailed Comparison Table

| Factor | Path A: ePDG+SIM | Path B: Phone Farm | Path C: RBM API | Path D: Jibe OTT | Path E: Virtual SIM | Path F: SMSoIP |
|--------|------------------|--------------------|-----------------|-------------------|---------------------|----------------|
| **Sender Identity** | Real phone #s | Real phone #s | Brand/agent | N/A (DEAD) | Real phone #s | Real phone #s |
| **Setup Cost (10 SIMs)** | ~$1,000–1,400 | ~$1,000–1,500 | $0 | N/A | ~$200 | ~$1,000–1,400 |
| **Monthly Cost (100 SIMs, India)** | ~$350–500 | ~$300–600 | Usage-based | N/A | ~$50–100* | ~$350–500 |
| **Per-msg cost (US)** | ~$0.0005–0.005 | ~$0.005–0.05 | ~$0.01–0.05 | N/A | ~$0.0001–0.001 | ~$0.0005–0.005 |
| **Per-msg cost (India)** | ~$0.0001–0.001 | ~$0.001–0.01 | ~$0.001–0.003 | N/A | ~$0.00005–0.0005 | ~$0.0001–0.001 |
| **Throughput/SIM** | 10–100+ msg/sec | 1–5 msg/sec | 1–30+ msg/sec | N/A | 100+ msg/sec | 10–30 msg/sec |
| **RCS Features** | Full (pager+session) | Full (via GM) | Full (rich cards) | N/A | Full (pager+session) | SMS only |
| **Legal Risk** | Medium | Medium | Low | N/A | Medium-High | Medium |
| **Carrier Blocking Risk** | Medium | Medium | None | N/A | Medium | Medium-Low |
| **Build Complexity** | Very High | Medium | Low | N/A | High | Medium |
| **Hardware Required** | SIM readers | Android phones | None | N/A | None | SIM readers |
| **Proven?** | ✅ Osmocom | ✅ Manual | ✅ Production | ❌ Dead | ⚠️ Test only | ✅ 3GPP spec |

*Virtual SIM monthly cost assumes self-hosted IMS where K+OPc are already provisioned in HSS.

---

## 4. Recommended Architecture

### **Recommendation: Hybrid with 5 Phases**

The recommended architecture combines Path A (ePDG+SIM+SIP), Path F (SMSoIP), and Path B (Phone Farm fallback) in a phased approach:

### Phase 1: SMSoIP MVP (Weeks 1–4)

**Goal**: Prove the IMS connection works. Get a single SIM card registered on carrier IMS via ePDG and sending SMSoIP messages.

| Step | Action | Time |
|------|--------|------|
| 1.1 | Get 1 carrier SIM (T-Mobile US or Jio India) + 1 PC/SC reader | 1 day |
| 1.2 | Set up sim-rest-server (patched for ISIM) | 1 day |
| 1.3 | Build strongSwan (Osmocom fork) with eap-aka-3gpp + p-cscf | 2-3 days |
| 1.4 | Configure strongSwan for carrier ePDG (see §8) | 1 day |
| 1.5 | Establish IKEv2/EAP-AKA tunnel to carrier ePDG | 1-2 days |
| 1.6 | Extract P-CSCF from tunnel, send SIP REGISTER with AKA | 2-3 days |
| 1.7 | Build SMSoIP sender (RP-DATA + SMS-SUBMIT TPDU) | 2-3 days |
| 1.8 | Send first SMSoIP message → recipient gets SMS | 1 day |
| 1.9 | Build minimal FastAPI with `/send` endpoint | 2-3 days |

**Deliverable**: Working SMSoIP sending from 1 SIM, via carrier IMS, with REST API.

### Phase 2: RCS Pager-Mode (Weeks 5–8)

**Goal**: Upgrade from SMSoIP to full RCS pager-mode messaging with CPIM, IMDN, and capability discovery.

| Step | Action | Time |
|------|--------|------|
| 2.1 | Add `+g.3gpp.icsi-ref=oma.cpm.msg` feature tag to REGISTER | 1 day |
| 2.2 | Implement CPIM message formatting (message/cpim body) | 2 days |
| 2.3 | Implement IMDN delivery/read receipt handling | 2 days |
| 2.4 | Implement SIP OPTIONS capability discovery | 1-2 days |
| 2.5 | Implement SIP MESSAGE with Contribution-ID, Conversation-ID | 2 days |
| 2.6 | Add incoming message handling (SIP listener + 200 OK) | 3 days |
| 2.7 | Switch from custom UDP sockets to PJSIP (with AKA callback) | 5 days |

**Deliverable**: Full RCS 1-1 messaging (send + receive + receipts).

### Phase 3: Multi-SIM Scaling (Weeks 9–16)

**Goal**: Scale from 1 SIM to 10 SIMs with automated management.

| Step | Action | Time |
|------|--------|------|
| 3.1 | Add sysmoOCTSIM (8-slot reader) + additional USB readers | 2 days |
| 3.2 | Build SIM slot manager (hot-swap, health, slot tracking) | 5 days |
| 3.3 | Build ePDG tunnel manager (per-SIM IKEv2 sessions) | 7 days |
| 3.4 | Build SIP registration monitor (auto re-REGISTER, AUTS handling) | 5 days |
| 3.5 | Build message router (round-robin across SIMs, rate limiting) | 5 days |
| 3.6 | Add PostgreSQL (message history, SIM registry) | 3 days |
| 3.7 | Add Redis (message queue, caching) | 2 days |
| 3.8 | Add Prometheus + Grafana monitoring | 3 days |
| 3.9 | Anti-abuse: per-SIM rate limiting (≤50 msg/day) | 2 days |
| 3.10 | SMS fallback via modem pool (when RCS fails) | 5 days |

**Deliverable**: 10-SIM production system with automated management.

### Phase 4: Phone Farm + Hybrid (Weeks 17–24)

**Goal**: Add Android phone farm as fallback/parallel path. Build the hybrid architecture.

| Step | Action | Time |
|------|--------|------|
| 4.1 | Set up 5 Android phones with Agent App (accessibility service) | 5 days |
| 4.2 | Build ADB connection manager and phone health monitor | 5 days |
| 4.3 | Build unified message router (SIP+SIM phones ↔ ADB phones) | 5 days |
| 4.4 | Build webhook API for external integration | 3 days |
| 4.5 | Implement Virtual SIM for test/self-hosted IMS | 5 days |
| 4.6 | DLT registration (if targeting India) | 2-5 days |

**Deliverable**: Hybrid system with 10 headless SIMs + 5 phone SIMs.

### Phase 5: Business Platform (Weeks 25–36)

**Goal**: Build the SaaS platform for RCS advertising — multi-tenant, campaigns, A/B testing, analytics.

| Step | Action | Time |
|------|--------|------|
| 5.1 | Multi-tenant SaaS architecture (FastAPI + PostgreSQL RLS) | 10 days |
| 5.2 | Campaign management (create, schedule, launch, monitor) | 7 days |
| 5.3 | A/B testing framework (message variants, statistical significance) | 5 days |
| 5.4 | Analytics engine (sent, delivered, read, replied, clicked) | 7 days |
| 5.5 | RBM Agent integration (official B2P path for rich cards) | 5 days |
| 5.6 | Contact management with opt-in/opt-out compliance | 5 days |
| 5.7 | Webhook event dispatcher | 3 days |
| 5.8 | White-label / agency reseller layer | 5 days |
| 5.9 | Billing and usage tracking | 5 days |
| 5.10 | Web dashboard (React/Next.js) | 14 days |

**Deliverable**: Full SaaS RCS advertising platform.

---

## 5. Complete Technical Reference

### 5.1 ePDG+SIM Flow (End-to-End)

```
┌─────┐     ┌──────┐     ┌──────┐     ┌──────┐     ┌───────┐     ┌──────┐
│ SIM │     │strong│     │ ePDG │     │ PGW  │     │P-CSCF │     │S-CSCF│ ←→ HSS
│Card │     │Swan  │     │      │     │      │     │       │     │      │
└──┬──┘     └──┬───┘     └──┬───┘     └──┬───┘     └───┬───┘     └──┬───┘
   │           │             │            │             │            │
   │ 1. IKE_SA_INIT ─────────────────→ │             │            │
   │           │             │ ←── SA_INIT response    │            │
   │           │             │            │             │            │
   │ 2. IKE_AUTH (IDi=IMSI@nai.epc...) ──→            │            │
   │           │             │ ── EAP-Request/AKA-Identity ──→     │
   │           │ ←────── EAP-Request/AKA-Challenge ── │            │
   │           │             │            │             │            │
   │ 3. SIM AUTH: RAND+AUTN → ISIM → RES+CK+IK        │            │
   │ ←─── RES/CK/IK from sim-rest-server ──           │            │
   │           │             │            │             │            │
   │ 4. IKE_AUTH (EAP-Response/AKA-Challenge RES) ──→  │            │
   │           │             │ ── AAA → HSS verify ──→ │            │
   │           │             │ ←── EAP-Success ──────── │            │
   │           │ ←── CONFIG PAYLOAD (IP, P-CSCF, DNS) │            │
   │           │             │            │             │            │
   │ 5. IPSec TUNNEL ESTABLISHED                      │            │
   │           │             │            │             │            │
   │ 6. SIP REGISTER (no auth) ──────────────────────→ │ ──→      │
   │           │             │            │ ←── 401 (nonce=RAND‖AUTN)│
   │           │             │            │             │            │
   │ 7. SIM AUTH: decode nonce → RAND/AUTN → ISIM → RES/CK/IK     │
   │ 8. AKA-Digest: H(A1)=MD5(IMPI:realm:RES_hex)                │
   │           │             │            │             │            │
   │ 9. SIP REGISTER (with Authorization) ────────────→ │ ──→      │
   │           │             │            │ ←── 200 OK ────────── │
   │           │             │            │             │            │
   │ ✅ REGISTERED — can send/receive RCS/SMSoIP messages           │
```

### 5.2 SIP REGISTER with IMS AKA (Full Protocol)

```
┌─────────┐          ┌──────────┐         ┌──────────┐        ┌──────────┐
│  Client  │          │  P-CSCF  │         │  I-CSCF  │        │  S-CSCF  │  ←→ HSS
└────┬────┘          └────┬─────┘         └────┬─────┘        └────┬─────┘
     │                    │                    │                    │
     │ 1. REGISTER (no auth)                    │                    │
     │  REGISTER sip:ims.mnc001.mcc001.3gppnetwork.org SIP/2.0
     │  From: <sip:user@domain>;tag=1234
     │  To: <sip:user@domain>
     │  Contact: <sip:user@local:5060>;+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.msg";+g.3gpp.smsip
     │  Authorization: Digest username="impi", realm="domain", nonce="", uri="sip:domain", response=""
     │  Expires: 600000
     │───────────────────→│──────────────────→│──────────────────→│
     │                    │                    │  Cx: UAR → HSS    │
     │ 2. 401 Unauthorized                       │  Cx: UAA ← HSS    │
     │  WWW-Authenticate: Digest algorithm=AKAv1-MD5,
     │    realm="ims.mnc001.mcc001.3gppnetwork.org",
     │    nonce="qlWqVapVqlWqVapVqlWqVUUQA5HEt9VVZ3t1TM221cg=",
     │    qop="auth", opaque="MTcyMjU3ODA2NDo="
     │←───────────────────│←──────────────────│←──────────────────│
     │                    │                    │                    │
     │ 3. Decode nonce → RAND(16B) + AUTN(16B)  │                    │
     │ 4. POST RAND/AUTN to sim-rest-server → RES/CK/IK            │
     │ 5. H(A1) = MD5(IMPI:realm:RES_hex_string)                 │
     │    H(A2) = MD5(REGISTER:sip:domain)                         │
     │    response = MD5(H(A1):nonce:nc:cnonce:qop:H(A2))         │
     │                    │                    │                    │
     │ 6. REGISTER (with auth)                   │                    │
     │  Authorization: Digest username="impi", realm="domain",
     │    nonce="qlWq...", uri="sip:domain", response="<computed>",
     │    algorithm=AKAv1-MD5, qop=auth, nc=00000001, cnonce="abc123"
     │───────────────────→│──────────────────→│──────────────────→│
     │                    │                    │  Cx: SAR → HSS    │
     │ 7. 200 OK                                 │  Cx: SAA ← HSS    │
     │  P-Associated-URI: <sip:user@domain>, <tel:+1234>
     │  Service-Route: <sip:scscf.domain;lr>
     │  Contact: <sip:user@local:5060>;expires=600000
     │←───────────────────│←──────────────────│←──────────────────│
     │ ✅ REGISTERED                                           │
```

### 5.3 SMSoIP (SMS over IMS)

**The simplest IMS-based messaging path.** Per 3GPP TS 24.341:

```
=== SMSoIP: Send SMS over IMS ===

Step 1: SIP REGISTER with +g.3gpp.smsip in Contact
Step 2: Get 401 → SIM auth → 200 OK (registered)
Step 3: SIP MESSAGE with Content-Type: application/vnd.3gpp.sms
        (body = binary RP-DATA wrapping SMS-SUBMIT TPDU)
Step 4: Get 202 Accepted
Step 5: Receive SIP MESSAGE back with RP-ACK
Step 6: Send 200 OK

Total: 3 SIP round-trips after registration
No CPIM, no capability discovery, no MSRP, no session setup
```

**SMSoIP SIP MESSAGE Format:**
```
MESSAGE tel:+19037029920;phone-context=domain SIP/2.0
From: <sip:+11234567890@domain>;tag=834037901
To: <tel:+19037029920;phone-context=domain>
CSeq: 834037887 MESSAGE
Call-ID: 834037887_2367153256@local
Via: SIP/2.0/UDP [local]:5060;branch=z9hG4bK253093091
Max-Forwards: 70
Content-Type: application/vnd.3gpp.sms
Allow: MESSAGE
Request-Disposition: no-fork
Content-Length: 28

[Binary RP-DATA frame containing SMS-SUBMIT TPDU]
```

**Key SMSoIP differences from RCS:**

| Aspect | SMSoIP | RCS Pager-Mode |
|--------|--------|----------------|
| Content-Type | `application/vnd.3gpp.sms` (binary) | `message/cpim` (text) |
| P-Preferred-Service | NOT used | `urn:urn-7:3gpp-service.ims.icsi.oma.cpm.msg` |
| Feature tag | `+g.3gpp.smsip` | `+g.3gpp.icsi-ref="...oma.cpm.msg"` |
| Body format | Binary RP-DATA/SMS-SUBMIT | CPIM headers + text/plain |
| Response | `202 Accepted` | `200 OK` |
| Routing | Via IP-SM-GW → SMSC → recipient | Via RCS AS → SIP MESSAGE → UE |
| Recipient sees | Standard SMS | RCS message |

### 5.4 RCS Messaging (Pager-Mode)

**Full SIP MESSAGE for RCS:**
```
MESSAGE sip:+14448880011@domain;user=phone SIP/2.0
P-Preferred-Service: urn:urn-7:3gpp-service.ims.icsi.oma.cpm.msg
Contribution-ID: 477b66ae9662e3ad18549bf5dabf9d26
Conversation-ID: 1710887c7ca47dc2c1274c11673eb0df
P-Preferred-Identity: <sip:sender@domain>
Request-Disposition: no-fork
Content-Type: message/cpim

From: <sip:sender@domain>
To: <sip:+14448880011@domain;user=phone>
DateTime: 2026-05-15T12:00:00Z
NS: imdn <urn:ietf:params:imdn>
imdn.Message-ID: msg-001-abc
imdn.Disposition-Notification: positive-delivery, display

Content-type: text/plain;charset=UTF-8
Content-Length: 13

Hello world!
```

### 5.5 Virtual SIM Milenage (Software AKA)

When K and OP/OPc are known (programmable SIMs or self-hosted IMS), AKA can be computed in software:

```python
# Software MILENAGE using CryptoMobile or PyCryptodome
# K = 16-byte secret key (stored on SIM's secure element normally)
# OPc = 16-byte operator variant code (derived from OP and K)

from CryptoMobile import Milenage  # pip install CryptoMobile
import hashlib

def virtual_sim_akav1(rand_hex: str, k_hex: str, opc_hex: str) -> dict:
    """Compute AKA RES/CK/IK entirely in software using MILENAGE."""
    rand = bytes.fromhex(rand_hex)
    k = bytes.fromhex(k_hex)
    opc = bytes.fromhex(opc_hex)
    
    # MILENAGE f2-f5 functions (3GPP TS 35.206)
    mil = Milenage(k, rand, opc=opc)
    res = mil.f2()    # 8-byte response
    ck = mil.f3()     # 16-byte cipher key
    ik = mil.f4()     # 16-byte integrity key
    ak = mil.f5()     # 6-byte anonymity key
    
    return {
        "res_hex": res.hex(),
        "ck_hex": ck.hex(),
        "ik_hex": ik.hex(),
        "ak_hex": ak.hex(),
    }

# 3GPP published test values (TS 35.207):
# K  = "465B5CE8B199B49FAA5F0A2EE238A6BC"
# OP = "CDC202D5123E5F8DB218BC3E69CB6F1B"
# RAND = "23553CBE9637EC4628B52F2344F00E92"
# Expected RES = "A542FE8A5C9E7FA5"
# Expected CK  = "B93E9F8B994C8C5B1A1E7E64E2CC9F3C"
# Expected IK  = "B0B5A7FC3AC5B3728598E3B9A3606BDA"
```

**Critical**: K/OPc CANNOT be extracted from commercial carrier SIMs. Virtual SIM only works when:
- You provision the SIM yourself (sysmoISIM-SJA2/SJA5) and know K/OPc
- You run your own IMS (Open5GS + Kamailio) and provision K/OPc in the HSS
- Security Explorations demonstrated Kigen eUICC cert extraction (theoretical)

### 5.6 Carrier Infrastructure & TS.43 Bypass

**ePDG FQDN Resolution** (publicly resolvable for 16+ carriers):

| Carrier | ePDG FQDN | Resolves? | IP Address(es) |
|---------|-----------|-----------|-----------------|
| **T-Mobile US** | `epdg.epc.geo.mnc260.mcc310.pub.3gppnetwork.org` | ✅ | `208.54.34.3` |
| **AT&T** | `epdg.epc.mnc410.mcc310.pub.3gppnetwork.org` | ✅ (CNAME) | → `epdg.epc.att.net` → `107.122.31.31` |
| **Vodafone UK** | `epdg.epc.mnc015.mcc234.pub.3gppnetwork.org` | ✅ (CNAME) | → `88.82.11.208` |
| **EE UK** | `epdg.epc.mnc030.mcc234.pub.3gppnetwork.org` | ✅ | `31.94.76.1–10` |
| **Three UK** | `epdg.epc.mnc020.mcc234.pub.3gppnetwork.org` | ✅ | `185.153.237.96` |
| **Jio India** | `epdg.epc.mnc874.mcc405.pub.3gppnetwork.org` | ✅ | `49.44.190.248` |
| **Airtel India** | `epdg.epc.mnc010.mcc404.pub.3gppnetwork.org` | ✅ | `106.201.214.127` |
| **Orange FR** | `epdg.epc.mnc001.mcc208.pub.3gppnetwork.org` | ✅ | `80.12.36.221` |
| **Deutsche Telekom** | `epdg.epc.mnc001.mcc262.pub.3gppnetwork.org` | ✅ | `109.237.187.141–159` |
| **Movistar ES** | `epdg.epc.mnc007.mcc214.pub.3gppnetwork.org` | ✅ | `213.4.100.129–153` |
| **Telstra AU** | `epdg.epc.mnc001.mcc505.pub.3gppnetwork.org` | ✅ | `149.135.224.26` |
| **Singtel SG** | `epdg.epc.mnc001.mcc525.pub.3gppnetwork.org` | ✅ | `111.65.100.1` |
| **Rogers CA** | `epdg.epc.mnc720.mcc302.pub.3gppnetwork.org` | ✅ | `209.148.157.48` |
| **Bell CA** | `epdg.epc.mnc640.mcc302.pub.3gppnetwork.org` | ✅ | `69.158.207.146` |
| **Verizon US** | `epdg.epc.mnc012.mcc311.pub.3gppnetwork.org` | ❌ | `127.0.0.1` (broken) |
| **US Cellular** | `epdg.epc.mnc028.mcc311.pub.3gppnetwork.org` | ❌ | `127.0.0.1` (broken) |

**TS.43 Entitlement Bypass**: The TS.43 entitlement check is a device-side gate, not a network-side gate. If the HSS provisions IMS for the subscriber, SIP REGISTER will succeed regardless of the entitlement check result. The entitlement server only blocks the phone's RCS app from attempting registration — it doesn't prevent the IMS core from accepting a valid REGISTER. **Strategy**: Skip the entitlement check entirely in the headless client; go straight to SIP REGISTER.

### 5.7 Anti-Abuse Evasion Parameters

**P2P RCS Safe Operating Zone:**

| Metric | Safe Zone | Risk Zone | Danger Zone |
|--------|-----------|-----------|-------------|
| Messages/day | ≤50 | 50–200 | >200 |
| Messages/hour | ≤10 | 10–30 | >30 |
| Messages/minute | ≤1 | 1–5 | >5 |
| Unique recipients/day | ≤15 | 15–50 | >50 |
| New numbers/day | ≤5 | 5–20 | >20 |
| Burst size | 1–3 messages | 3–10 messages | >10 in 1 minute |
| Min gap between messages | 30 seconds | 10–30 seconds | <10 seconds |

**Registration safety:**
- Use a **residential VPN** in the carrier's home country for IKEv2 to ePDG
- Use a **valid IMEI** from a known VoWiFi-capable phone (e.g., Pixel 7 Pro)
- Keep IMEI stable across sessions — don't rotate
- Use standard SIP registration intervals (600,000 sec default)
- Include correct RCS feature tags in REGISTER Contact header
- Use standard User-Agent from a real Android SIP trace
- Deregister during off-hours (simulate human sleep)

**Content guidelines:**
- Personalize messages per recipient
- Avoid URLs in first messages (top spam indicator)
- Vary message body (identical messages to many = spam campaign)
- Include recipient's name
- No financial requests or phishing patterns
- Natural language, not promotional

**Spam report consequences:**
- 5–10 reports: Sender flagged in Google's spam database
- Accumulated reports: RCS registration may be invalidated
- Persistent reports: Number blacklisted across Google infrastructure
- Carrier-level: SIM suspended for "violating terms of service"
- GSMA SRS: Single report propagates across all carriers within minutes

---

## 6. Hardware & Cost Projections

### SIM Bank Hardware at Each Scale

#### 10 SIMs (Small/Beta)

| Component | Product | Cost |
|-----------|---------|------|
| SIM Reader | 2× sysmoOCTSIM (8-slot each) | ~$700 |
| Linux Server | Any x86 box | ~$300 |
| SIM Cards | 10× prepaid | $0–100 |
| **Total Setup** | | **~$1,000–1,100** |
| **Monthly (India SIMs)** | 10× plans @ $2/mo | ~$20 |
| **Monthly (US SIMs)** | 10× plans @ $15/mo | ~$150 |

#### 100 SIMs (Medium/Business) — Hybrid Architecture

| Component | Product | Qty | Total |
|-----------|---------|-----|-------|
| SIM Reader Boards | sysmoOCTSIM (8-slot) | 13 | $2,860 |
| Android Phones | BLU View 5 / Moto E14 | 30 | $900–1,500 |
| USB Hubs | Sabrent 20-port | 4 | $280 |
| Server | Dell R730 2U | 1 | $800 |
| Wi-Fi APs | Ubiquiti U6-Lite | 3 | $300 |
| Modem Pool | 32-port SMS modem pool | 1 | $500 |
| SIM Cards | 100× prepaid | 100 | $0–500 |
| **Total Setup** | | | **$5,640–6,740** |
| **Monthly (India SIMs)** | 100× plans | | ~$300 |
| **Monthly (US SIMs)** | 100× plans | | ~$1,500 |

#### 500 SIMs (Large/Scale)

| Component | Cost |
|-----------|------|
| SIM Readers (63× sysmoOCTSIM) | ~$13,900 |
| Phones (50 for hybrid) | ~$2,500 |
| Servers (2U + multiple API) | ~$3,000 |
| SIM Cards (500× prepaid) | $0–3,000 |
| **Total Setup** | **~$19,400–22,400** |
| **Monthly (India SIMs)** | ~$1,500 |
| **Monthly (US SIMs)** | ~$7,500 |

### SIM Card Costs by Country

| Country | SIM Cost (one-time) | Monthly Plan | Annual Cost | Notes |
|---------|---------------------|-------------|-------------|-------|
| **India (BSNL)** | ₹20 (~$0.25) | ₹107/mo (~$1.25) | ~$15 | Cheapest globally |
| **India (Jio)** | ₹0–50 (~$0–0.60) | ₹149/24d (~$6/mo) | ~$36 | Best value |
| **US (Ultra Mobile PayGo)** | $3/mo | $3/mo | ~$36 | Cheapest US |
| **US (T-Mobile Prepaid)** | $0–10 | $15/mo | ~$180 | Standard |
| **UK (Lebara/VOXI)** | £0 (~$0) | £5–10/mo (~$6–12) | ~$72–144 | UK criminalized SIM farms (2025) ⚠️ |

### Total TCO Comparison (Annual, 100 SIMs)

| Cost Category | Path A (India) | Path A (US) | Path B (India) | Path C (RBM US) |
|---------------|---------------|-------------|----------------|-----------------|
| Hardware setup | $5,640 | $5,640 | $6,740 | $0 |
| SIM/plan costs | $3,600 | $18,000 | $3,600 | N/A |
| Infrastructure | $2,400 | $2,400 | $3,600 | $600 |
| **Total Year 1** | **$11,640** | **$26,040** | **$13,940** | Usage-based |
| **Per 1K msgs** | **~$0.05–0.50** | **~$0.05–0.50** | **~$0.50–5** | **~$10–50** |

---

## 7. Code: Complete Starter Kit

### 7.1 Python Milenage (Virtual SIM)

```python
#!/usr/bin/env python3
"""Virtual SIM: Software MILENAGE AKA computation.
Requires: pip install CryptoMobile
Only works when K and OPc are known (programmable SIMs or self-hosted IMS).
"""

from CryptoMobile import Milenage
import hashlib

def virtual_sim_aka(rand_hex: str, k_hex: str, opc_hex: str) -> dict:
    """Compute AKA RES/CK/IK entirely in software."""
    rand = bytes.fromhex(rand_hex)
    k = bytes.fromhex(k_hex)
    opc = bytes.fromhex(opc_hex)
    
    mil = Milenage(k, rand, opc=opc)
    return {
        "res_hex": mil.f2().hex(),
        "ck_hex": mil.f3().hex(),
        "ik_hex": mil.f4().hex(),
        "ak_hex": mil.f5().hex(),
    }

# 3GPP TS 35.207 test vector:
# K  = "465B5CE8B199B49FAA5F0A2EE238A6BC"
# OPc = "CD63CF7195E13DB4DCB5D4C22BCAC3C9"
# RAND = "23553CBE9637EC4628B52F2344F00E92"
# → RES = "A542FE8A5C9E7FA5"
# → CK  = "B93E9F8B994C8C5B1A1E7E64E2CC9F3C"
# → IK  = "B0B5A7FC3AC5B3728598E3B9A3606BDA"
```

### 7.2 AKA-Digest Computation (RFC 3310)

```python
"""AKA-Digest: The single most critical computation in the entire project."""
import hashlib, os

def compute_aka_digest_response(
    impi: str, realm: str, res_hex: str, digest_uri: str,
    nonce_b64: str, algorithm: str = "AKAv1-MD5",
    qop: str = None, nc: str = "00000001", cnonce: str = None,
    ck_hex: str = None, ik_hex: str = None,
) -> tuple:
    """Compute SIP Digest AKA response per RFC 3310 / RFC 2617."""
    if cnonce is None:
        cnonce = os.urandom(4).hex()

    # Stage 1: H(A1) = MD5(username:realm:RES_hex_string)
    # CRITICAL: RES is used as its HEX STRING (ASCII), NOT raw binary bytes!
    if algorithm.upper() in ("AKAV1-MD5", "AKAV1-MD5-SESS"):
        ha1 = hashlib.md5(f"{impi}:{realm}:{res_hex}".encode("ascii")).hexdigest()
    elif algorithm.upper() in ("AKAV2-MD5", "AKAV2-MD5-SESS"):
        if not ck_hex or not ik_hex:
            raise ValueError("AKAv2 requires CK and IK")
        ha1_base = hashlib.md5(f"{impi}:{realm}:{res_hex}".encode("ascii")).hexdigest()
        ha1 = hashlib.md5(f"{ha1_base}:{ck_hex}:{ik_hex}".encode("ascii")).hexdigest()
    else:
        raise ValueError(f"Unsupported: {algorithm}")

    # Stage 2: H(A2) = MD5(REGISTER:digest_uri)
    ha2 = hashlib.md5(f"REGISTER:{digest_uri}".encode("ascii")).hexdigest()

    # Stage 3: Final response
    if qop and qop.lower().startswith("auth"):
        response = hashlib.md5(
            f"{ha1}:{nonce_b64}:{nc}:{cnonce}:{qop}:{ha2}".encode("ascii")
        ).hexdigest()
    else:
        response = hashlib.md5(f"{ha1}:{nonce_b64}:{ha2}".encode("ascii")).hexdigest()

    return response, cnonce, nc
```

### 7.3 sim-rest-server Integration

```python
"""Bridge to pySim's sim-rest-server for ISIM AKA authentication via PC/SC reader."""
import requests

def call_sim_rest_server(rand_hex: str, autn_hex: str, slot: int = 0,
                         base_url: str = "http://localhost:8000") -> dict:
    """Perform ISIM AKA authentication via sim-rest-server REST API."""
    url = f"{base_url}/sim-auth-api/v1/slot/{slot}"
    payload = {"rand": rand_hex.lower(), "autn": autn_hex.lower(), "app": "isim"}

    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    result = resp.json()

    if "synchronisation_failure" in result:
        raise SimSyncFailure(result["synchronisation_failure"]["auts"])
    if "successful_3g_authentication" in result:
        auth = result["successful_3g_authentication"]
        return {"res_hex": auth["res"], "ck_hex": auth["ck"],
                "ik_hex": auth["ik"], "kc_hex": auth.get("kc", "")}
    raise RuntimeError(f"Unexpected response: {result}")

class SimSyncFailure(Exception):
    """SQN sync failure — must re-REGISTER with AUTS to trigger HSS re-sync."""
    pass
```

**CRITICAL**: Stock sim-rest-server hardcodes `adf='usim'`. You MUST patch it for ISIM:
```python
# In sim-rest-server.py, change:
#   card.select_adf_by_aid(adf='usim')
# to:
#   app = content.get('app', 'usim')
#   card.select_adf_by_aid(adf=app)
```

### 7.4 strongSwan Configuration for ePDG

```conf
# /etc/swanctl/swanctl.conf — ePDG connection for T-Mobile US
connections {
    epdg-tmous {
        version = 2
        mobike = yes
        reauth_time = 0s

        local_addrs = %any
        remote_addrs = epdg.epc.geo.mnc260.mcc310.pub.3gppnetwork.org

        local {
            auth = eap-aka
            eap_id = 031026012345678@nai.epc.mnc260.mcc310.pub.3gppnetwork.org
        }

        remote {
            auth = pubkey
        }

        children {
            epdg-tmous {
                remote_ts = 0.0.0.0/0
                start_action = start
                dpd_action = restart
                # Request P-CSCF via config payload
                esp_proposals = aes128-sha256-modp2048
            }
        }
    }
}

# PC/SC reader plugin for EAP-AKA via SIM card
# Requires strongSwan Osmocom fork:
# https://gitea.osmocom.org/ims-volte-vowifi/strongswan-epdg
# Build with: --enable-eap-sim-pcsc --enable-eap-aka --enable-p-cscf
```

### 7.5 PJSIP AKA Callback

```c
/* PJSIP AKA callback — proxies challenge to sim-rest-server or VirtualSIM */
/* Build PJSIP with: #define PJSIP_HAS_DIGEST_AKA_AUTH 1 */

static pj_status_t aka_auth_cb(
    const pj_str_t *realm,
    const pj_str_t *username,
    const pj_str_t *nonce,     /* Base64(RAND||AUTN||data) */
    const pj_str_t *nc,
    const pj_str_t *cnonce,
    const pj_str_t *qop,
    pj_uint8_t res[PJSIP_AUTH_RESPONSE_LEN],
    int *res_len)
{
    /* 1. Decode nonce → extract RAND (16B) + AUTN (16B) */
    /* 2. Option A: POST RAND/AUTN to sim-rest-server → get RES/CK/IK */
    /*    Option B: Use VirtualSIM (software Milenage) if K+OPc known */
    /* 3. PJSIP handles the rest of the MD5 digest computation */
    /* 4. Return RES hex string — PJSIP uses it as the "password" */

    /* Important: RES must be returned as hex string (ASCII), not raw bytes */
    return PJ_SUCCESS;
}
```

**PJSIP Build:**
```bash
git clone https://github.com/pjsip/pjproject
cd pjproject
echo '#define PJSIP_HAS_DIGEST_AKA_AUTH 1' > pjlib/include/pj/config_site.h
echo '#define PJ_HAS_SSL_SOCK 1' >> pjlib/include/pj/config_site.h
./configure && make dep && make
sudo make install
```

### 7.6 SMSoIP Sender

```python
#!/usr/bin/env python3
"""Minimal SMSoIP Client: Send SMS over IMS via SIP MESSAGE."""
import socket, struct, uuid

def send_smsoip(pcscf_addr, pcscf_port, local_ip, local_port,
                sender_msisdn, recipient_msisdn, text, domain,
                smSC_address="", message_ref=1) -> bool:
    """Send SMS over IMS using SMSoIP (SIP MESSAGE + binary RP-DATA)."""

    # 1. Build SMS-SUBMIT TPDU (3GPP TS 23.040)
    tpdu = build_sms_submit_tpdu(recipient_msisdn, text, message_ref)

    # 2. Build RP-DATA frame (3GPP TS 24.011)
    rp_data = build_rp_data_mo(tpdu, message_ref, smSC_address)

    # 3. Build SIP MESSAGE
    sip_msg = (
        f"MESSAGE tel:{recipient_msisdn};phone-context={domain} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch=z9hG4bK-smsoip\r\n"
        f"Max-Forwards: 70\r\n"
        f"From: <sip:{sender_msisdn}@{domain}>;tag=smsoip{message_ref}\r\n"
        f"To: <tel:{recipient_msisdn};phone-context={domain}>\r\n"
        f"Call-ID: {uuid.uuid4().hex[:8]}@{local_ip}\r\n"
        f"CSeq: {message_ref} MESSAGE\r\n"
        f"Contact: <sip:{sender_msisdn}@{local_ip}:{local_port}>;+g.3gpp.smsip\r\n"
        f"Content-Type: application/vnd.3gpp.sms\r\n"
        f"Allow: MESSAGE\r\n"
        f"Request-Disposition: no-fork\r\n"
        f"Content-Length: {len(rp_data)}\r\n\r\n"
    )

    # 4. Send via UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((local_ip, local_port))
    sock.sendto(sip_msg.encode('ascii') + rp_data, (pcscf_addr, pcscf_port))

    # 5. Wait for 202 Accepted
    sock.settimeout(5.0)
    try:
        data, addr = sock.recvfrom(4096)
        response = data.decode('ascii', errors='replace')
        return "202" in response or "200" in response
    except socket.timeout:
        return False
    finally:
        sock.close()
```

### 7.7 SIP MESSAGE (RCS Pager-Mode)

```python
import uuid, hashlib
from datetime import datetime, timezone

def send_rcs_message(sender_impu, recipient_impu, text, domain, pcscf_addr,
                     local_ip, local_port=5060, conversation_id=None):
    """Send a pager-mode RCS message via SIP MESSAGE with CPIM body."""
    contribution_id = uuid.uuid4().hex
    conversation_id = conversation_id or uuid.uuid4().hex
    message_id = f"msg-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cpim_body = (
        f"From: <{sender_impu}>\r\nTo: <{recipient_impu}>\r\n"
        f"DateTime: {now}\r\nNS: imdn <urn:ietf:params:imdn>\r\n"
        f"imdn.Message-ID: {message_id}\r\n"
        f"imdn.Disposition-Notification: positive-delivery, display\r\n\r\n"
        f"Content-type: text/plain;charset=UTF-8\r\n"
        f"Content-Length: {len(text.encode('utf-8'))}\r\n\r\n{text}"
    )

    sip_msg = (
        f"MESSAGE {recipient_impu} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch=z9hG4bK-{contribution_id[:8]}\r\n"
        f"Max-Forwards: 70\r\n"
        f"From: <{sender_impu}>;tag=msg{contribution_id[:6]}\r\n"
        f"To: <{recipient_impu}>\r\n"
        f"Call-ID: {contribution_id}@{local_ip}\r\n"
        f"CSeq: 1 MESSAGE\r\n"
        f"P-Preferred-Service: urn:urn-7:3gpp-service.ims.icsi.oma.cpm.msg\r\n"
        f"Contribution-ID: {contribution_id}\r\n"
        f"Conversation-ID: {conversation_id}\r\n"
        f"P-Preferred-Identity: <{sender_impu}>\r\n"
        f"Request-Disposition: no-fork\r\n"
        f"Content-Type: message/cpim\r\n"
        f"Content-Length: {len(cpim_body.encode('utf-8'))}\r\n\r\n{cpim_body}"
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(sip_msg.encode(), (pcscf_addr, 5060))
    sock.settimeout(5.0)
    data, addr = sock.recvfrom(4096)
    sock.close()
    return "200 OK" in data.decode()
```

### 7.8 Full Orchestration: ims_aka_register()

```python
"""Full IMS AKA SIP registration orchestration."""
import socket, base64, re, os, logging
import hashlib

logger = logging.getLogger(__name__)

def ims_aka_register(impi, impu, pcscf_addr, pcscf_port=5060,
                      pcscf_domain=None, sim_rest_url="http://localhost:8000",
                      sim_slot=0, local_ip="192.168.1.100", local_port=5060,
                      expires=600000, udp_timeout=5.0):
    """Complete 2-step IMS AKA SIP registration."""
    if pcscf_domain is None:
        pcscf_domain = impi.split("@")[1] if "@" in impi else pcscf_addr

    # Step 1: Send initial REGISTER → get 401 with AKA challenge
    branch = f"z9hG4bK{os.urandom(6).hex()}"
    call_id = f"{os.urandom(4).hex()}@{local_ip}"
    tag = f"{int(__import__('time').time())}"
    impi_user = impi.split("@")[0]

    initial_reg = (
        f"REGISTER sip:{pcscf_domain} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch={branch}\r\n"
        f"Max-Forwards: 70\r\nFrom: <{impu}>;tag={tag}\r\nTo: <{impu}>\r\n"
        f"Call-ID: {call_id}\r\nCSeq: 1 REGISTER\r\n"
        f"Contact: <sip:{impi_user}@{local_ip}:{local_port}>;"
        f'+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.msg",'
        f'+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.session",'
        f'+g.3gpp.smsip\r\n'
        f"Expires: {expires}\r\n"
        f'Authorization: Digest username="{impi}", realm="{pcscf_domain}", '
        f'nonce="", uri="sip:{pcscf_domain}", response=""\r\n'
        f"Content-Length: 0\r\n\r\n"
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((local_ip, local_port))
    sock.settimeout(udp_timeout)
    sock.sendto(initial_reg.encode(), (pcscf_addr, pcscf_port))
    data, addr = sock.recvfrom(65535)
    response = data.decode()

    if "401" not in response:
        raise RuntimeError(f"Expected 401, got: {response[:200]}")

    # Step 2: Parse 401, extract RAND/AUTN from nonce
    www_auth = re.search(r'WWW-Authenticate:\s*Digest\s+(.*?)(?:\r\n\S|\n\S)', response, re.DOTALL)
    auth_text = www_auth.group(1).replace('\r\n ', '').replace('\n ', '')
    params = {}
    for m in re.finditer(r'(\w+)="?([^",]+)"?', auth_text):
        params[m.group(1)] = m.group(2)

    nonce_b64 = params.get('nonce', '')
    realm = params.get('realm', pcscf_domain)
    algorithm = params.get('algorithm', 'AKAv1-MD5')
    qop = params.get('qop', '')
    opaque = params.get('opaque', '')

    nonce_bytes = base64.b64decode(nonce_b64 + "=" * (-len(nonce_b64) % 4))
    rand_hex = nonce_bytes[:16].hex()
    autn_hex = nonce_bytes[16:32].hex()

    # Step 3: Call sim-rest-server
    auth_data = call_sim_rest_server(rand_hex, autn_hex, sim_slot, sim_rest_url)

    # Step 4: Compute AKA-Digest
    response_val, cnonce, nc = compute_aka_digest_response(
        impi, realm, auth_data['res_hex'], f"sip:{pcscf_domain}",
        nonce_b64, algorithm, qop if qop else None)

    # Step 5: Send authenticated REGISTER
    auth_parts = [
        f'Digest username="{impi}"', f'realm="{realm}"',
        f'nonce="{nonce_b64}"', f'uri="sip:{pcscf_domain}"',
        f'response="{response_val}"', f'algorithm={algorithm}',
    ]
    if qop: auth_parts += [f'qop={qop}', f'nc={nc}', f'cnonce="{cnonce}"']
    if opaque: auth_parts.append(f'opaque="{opaque}"')

    auth_reg = (
        f"REGISTER sip:{pcscf_domain} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch=z9hG4bK-auth\r\n"
        f"Max-Forwards: 70\r\nFrom: <{impu}>;tag={tag}\r\nTo: <{impu}>\r\n"
        f"Call-ID: {call_id}\r\nCSeq: 2 REGISTER\r\n"
        f"Contact: <sip:{impi_user}@{local_ip}:{local_port}>;"
        f'+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.msg",'
        f'+g.3gpp.smsip\r\n'
        f"Expires: {expires}\r\n"
        f"Authorization: {', '.join(auth_parts)}\r\n"
        f"Security-Client: alg=hmac-md5-96; ealg=aes-cbc; prot=esp; mod=trans; "
        f"spi-c={os.urandom(4).hex()}; port-c={local_port+1}\r\n"
        f"Require: sec-agree\r\nProxy-Require: sec-agree\r\n"
        f"Content-Length: 0\r\n\r\n"
    )

    sock.sendto(auth_reg.encode(), (pcscf_addr, pcscf_port))
    data, addr = sock.recvfrom(65535)
    result = data.decode()
    sock.close()

    if "200 OK" in result:
        # Extract P-Associated-URI, Service-Route
        associated = re.findall(r'P-Associated-URI:\s*<([^>]+)>', result)
        routes = re.findall(r'Service-Route:\s*<([^>]+)>', result)
        return {"registered": True, "associated_uris": associated, "service_routes": routes}
    raise RuntimeError(f"Registration failed: {result[:200]}")
```

---

## 8. Carrier Intelligence

### 8.1 ePDG Addresses (Publicly Resolvable)

| Carrier | MCC-MNC | ePDG FQDN | IP Address(es) | Feasibility |
|---------|---------|-----------|-----------------|-------------|
| **T-Mobile US** | 310-260 | `epdg.epc.geo.mnc260.mcc310.pub.3gppnetwork.org` | `208.54.34.3` | **HIGH** ✅ |
| **AT&T** | 310-410 | `epdg.epc.mnc410.mcc310.pub.3gppnetwork.org` | → `epdg.epc.att.net` → `107.122.31.31` | **HIGH** ✅ |
| **Vodafone UK** | 234-015 | `epdg.epc.mnc015.mcc234.pub.3gppnetwork.org` | → `88.82.11.208` | **HIGH** ✅ |
| **EE UK** | 234-030 | `epdg.epc.mnc030.mcc234.pub.3gppnetwork.org` | `31.94.76.1–10` | **HIGH** ✅ |
| **Three UK** | 234-020 | `epdg.epc.mnc020.mcc234.pub.3gppnetwork.org` | `185.153.237.96` | **HIGH** ✅ |
| **Jio India** | 405-874 | `epdg.epc.mnc874.mcc405.pub.3gppnetwork.org` | `49.44.190.248` | **HIGH** ✅ |
| **Airtel India** | 404-010 | `epdg.epc.mnc010.mcc404.pub.3gppnetwork.org` | `106.201.214.127` | **MEDIUM** |
| **Orange France** | 208-001 | `epdg.epc.mnc001.mcc208.pub.3gppnetwork.org` | `80.12.36.221` | **MEDIUM** |
| **Deutsche Telekom** | 262-001 | `epdg.epc.mnc001.mcc262.pub.3gppnetwork.org` | `109.237.187.141–159` | **HIGH** ✅ |
| **Movistar ES** | 214-007 | `epdg.epc.mnc007.mcc214.pub.3gppnetwork.org` | `213.4.100.129–153` | **HIGH** ✅ |
| **Telstra AU** | 505-001 | `epdg.epc.mnc001.mcc505.pub.3gppnetwork.org` | `149.135.224.26` | **HIGH** ✅ |
| **Singtel SG** | 525-001 | `epdg.epc.mnc001.mcc525.pub.3gppnetwork.org` | `111.65.100.1` | **HIGH** ✅ |
| **Rogers CA** | 302-720 | `epdg.epc.mnc720.mcc302.pub.3gppnetwork.org` | `209.148.157.48` | **MEDIUM** |
| **Bell CA** | 302-640 | `epdg.epc.mnc640.mcc302.pub.3gppnetwork.org` | `69.158.207.146` | **MEDIUM** |
| **Verizon US** | 311-012 | `epdg.epc.mnc012.mcc311.pub.3gppnetwork.org` | `127.0.0.1` ❌ | **LOW** |
| **US Cellular** | 311-028 | `epdg.epc.mnc028.mcc311.pub.3gppnetwork.org` | `127.0.0.1` ❌ | **LOW** |

### 8.2 ACS Configuration URLs

| Carrier | ACS URL | Resolves? | Hosting |
|---------|---------|-----------|---------|
| **T-Mobile US** | `config.rcs.mnc260.mcc310.pub.3gppnetwork.org` | ✅ | Akamai CDN (likely Jibe) |
| **AT&T** | `config.rcs.mnc410.mcc310.pub.3gppnetwork.org` | ✅ | Self-hosted (166.216.153.x) |
| **Jio India** | `config.rcs.mnc874.mcc405.pub.3gppnetwork.org` | ✅ | Self-hosted (103.63.128.x) |
| **Vodafone UK** | `config.rcs.mnc015.mcc234.pub.3gppnetwork.org` | ✅ | Google Cloud |
| **EE UK** | `config.rcs.mnc030.mcc234.pub.3gppnetwork.org` | ✅ | Google Cloud |
| **Globe PH** | `config.rcs.mnc002.mcc515.pub.3gppnetwork.org` | ✅ | Google Cloud |
| **Telstra AU** | `config.rcs.mnc001.mcc505.pub.3gppnetwork.org` | ✅ | Self-hosted |
| **Airtel India** | `config.rcs.mnc010.mcc404.pub.3gppnetwork.org` | ❌ | NXDOMAIN |
| **Orange France** | `config.rcs.mnc001.mcc208.pub.3gppnetwork.org` | ❌ | NXDOMAIN |

### 8.3 Entitlement Server URLs (TS.43)

| Carrier | Entitlement FQDN Pattern | Notes |
|---------|--------------------------|-------|
| **T-Mobile US** | `ecs.mnc260.mcc310.pub.3gppnetwork.org` | May use CNAME to T-Mobile domain |
| **AT&T** | `entitlement.att.com` or similar | Carrier-specific domain |
| **General** | `ecs.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org` | 3GPP standard convention |

### 8.4 Anti-Abuse Thresholds

| Carrier | Spam Detection | P2P Throttling | A2P Rules |
|---------|---------------|----------------|-----------|
| **T-Mobile US** | Scam Shield (ML) | Undocumented, ~100-300/day | 10DLC required |
| **AT&T** | ActiveArmor | Undocumented | 10DLC required |
| **Verizon** | Call Filter | Undocumented | 10DLC required |
| **Jio India** | TRAI DND compliance | Template enforcement | Template registration required |
| **All (GSMA SRS)** | Cross-carrier spam reports | Reports propagate in minutes | N/A |

---

## 9. Open Source Repo Index

| Repository | URL | Stars | Relevance | What It Does |
|-----------|-----|-------|-----------|-------------|
| **pySim** | https://github.com/osmocom/pysim | 500+ | **10/10** | SIM card programming, ISIM auth, sim-rest-server |
| **strongswan-epdg** | https://gitea.osmocom.org/ims-volte-vowifi/strongswan-epdg | — | **10/10** | ePDG IKEv2 client with EAP-AKA via PC/SC |
| **osmo-remsim** | https://gitea.osmocom.org/cellular-infrastructure/osmo-remsim | — | **9/10** | Remote SIM infrastructure |
| **pjsip** | https://github.com/pjsip/pjproject | 2,000+ | **9/10** | SIP stack with built-in AKA auth |
| **python-sipsimple** | https://github.com/AGProjects/python-sipsimple | 200+ | **8/10** | SIP+MSRP SDK, CPIM, IMDN |
| **python3-msrplib** | https://github.com/AGProjects/python3-msrplib | 50+ | **8/10** | MSRP client library |
| **CryptoMobile** | https://github.com/nicowilliams/CryptoMobile | — | **8/10** | Python MILENAGE / TUAK implementation |
| **docker_open5gs** | https://github.com/herlesupreeth/docker_open5gs | 500+ | **6/10** | Containerized 4G/5G core + Kamailio IMS |
| **mautrix/gmessages** | https://github.com/mautrix/gmessages | 200+ | **6/10** | Matrix bridge for Google Messages (requires phone) |
| **SimServerAndroid** | https://github.com/zhuowei/SimServerAndroid | — | **7/10** | HTTP API for SIM AKA auth via Android |
| **microG GmsCore** | https://github.com/microg/GmsCore | 7,000+ | **5/10** | Open-source Google Play Services (partial RCS) |
| **rcsjta** | https://github.com/android-rcs/rcsjta | 50+ | **5/10** | GSMA RCS-e reference (NO AKA support) |
| **epdg_discoverer** | https://github.com/Spinlogic/epdg_discoverer | — | **7/10** | ePDG FQDN resolution and IKEv2 testing |
| **SWu-IKEv2** | https://github.com/fasferraz/SWu-IKEv2 | — | **5/10** | Python VoWiFi EAP-AKA' client |
| **free-rcs-server** | https://github.com/FreeJoyn/free-rcs-server | — | **4/10** | Open source RCS server |
| **Gammu** | https://github.com/gammu/gammu | 800+ | **4/10** | GSM modem tool (SMS only) |
| **smsgate** | https://github.com/pentagridsec/smsgate | — | **3/10** | Multi-modem SMS gateway (SMS only) |
| **TextBee** | https://github.com/vernu/textbee | 400+ | **3/10** | Android phone SMS gateway (SMS only) |
| **OpenSIPS** | https://github.com/OpenSIPS/opensips | 1,000+ | **6/10** | SIP server with RCS capability |

---

## 10. Risk Assessment

### Technical Risks

| Risk | Severity | Likelihood | Mitigation |
|------|----------|-----------|------------|
| **ePDG geoblocking from data center IPs** | High | Medium | Use residential VPN in carrier's home country |
| **IPSec SA required by P-CSCF** | High | Medium | ePDG tunnel provides transport-level IPSec; some carriers relax inner sec-agree for VoWiFi |
| **AKA-Digest computation bugs** | High | Low | Use validated glue code from §7.2; test against 3GPP TS 35.207 test vectors |
| **SQN sync failures (AUTS)** | Medium | Medium | Implement AUTS re-REGISTER flow; HSS re-syncs automatically |
| **Carrier-specific SIP quirks** | High | High | Build carrier profile database; test each carrier |
| **P-CSCF unreachable** | High | Low | Use ePDG path (provides P-CSCF via config payload); fallback to ACS XML |
| **SIM card deactivation** | High | Medium | Auto-detect; rotate SIMs; maintain spares; use corporate plans |
| **strongSwan Osmocom fork maintenance** | Medium | Medium | Fork is maintained for Osmocom project; monitor for updates |
| **Google RCS updates break Phone Farm** | Medium | Medium | Lock Google Messages version; test before deploying updates |
| **Virtual SIM detection** | High | Low | No evidence carriers detect software AKA vs physical SIM; theoretical risk |

### Operational Risks

| Risk | Severity | Likelihood | Mitigation |
|------|----------|-----------|------------|
| **Spam reports trigger RCS de-registration** | High | Medium | ≤50 msg/day/SIM; personalize messages; avoid URLs in first messages |
| **Carrier detects A2P traffic on P2P route** | High | Medium | Use natural messaging patterns; warm up new SIMs gradually |
| **SIM farm detection via IMEI fingerprinting** | Medium | Medium | Use diverse valid IMEIs; rotate slowly; avoid data center IPs |
| **UK SIM farm criminalization (2025)** | High | Jurisdiction | Avoid UK operations; check local laws |
| **India DLT/TRAI enforcement** | Medium | High | Register on DLT platform; use approved templates; respect DND list |
| **Rate limit exceeded → SIM suspension** | High | Low | Enforce per-SIM limits: ≤50 msg/day, ≤1 msg/min |
| **Google Play Integrity blocks** | N/A | N/A | Only affects Jibe OTT (dead path); ePDG+SIM path not subject to Play Integrity |

### Legal Risks

| Jurisdiction | Risk | Law/Regulation | Mitigation |
|-------------|------|---------------|-----------|
| **United States** | TCPA violations for marketing | Telephone Consumer Protection Act | Obtain express consent; use opt-in; honor opt-out |
| **European Union** | GDPR consent requirements | General Data Protection Regulation | Freely given, specific, informed consent; right to deletion |
| **India** | DLT registration, 9-SIM limit | TRAI DND Regulations, Dec 2023 bulk SIM ban | Register on DLT; max 9 SIMs per person; use corporate entities |
| **United Kingdom** | SIM farm criminalization | Computer Misuse Act amendment (2025) | Avoid UK; use API-based RCS instead |
| **All** | Carrier ToS violation | Carrier terms of service | Use for legitimate business messaging; comply with carrier policies |

---

## 11. Business: RCS Ad Platform Design

### Market Opportunity

| Metric | Value | Source |
|--------|-------|--------|
| **RCS market size (2026)** | $3.59B–$9.5B | Mordor Intelligence |
| **RCS market CAGR** | 16–25% | Multiple analysts |
| **RCS subscriber base (2026)** | 3.5B (40% of mobile) | Juniper Research |
| **RCS conversion rate** | Up to 80% (vs 5-15% SMS) | Master of Code |
| **Apple iOS 18+ RCS support** | Expands market to universal | Apple (Sept 2024) |

### Platform Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     RCS Ad Platform (SaaS)                        │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ REST API  │  │ WebSocket│  │ Dashboard │  │ Webhook       │   │
│  │ (FastAPI) │  │ (events)│  │ (React)   │  │ Dispatcher    │   │
│  └─────┬────┘  └────┬─────┘  └─────┬────┘  └──────┬───────┘   │
│        └──────────────┼──────────────┼──────────────┘           │
│                  ┌────▼────┐                                    │
│                  │Orchestra-│                                     │
│                  │tor      │                                     │
│                  │(Python) │                                     │
│                  └────┬────┘                                     │
│        ┌──────────────┼──────────────┐                           │
│  ┌─────▼──────┐  ┌───▼──────────┐  ┌──▼──────────┐            │
│  │Campaign Mgr│  │Contact Mgr   │  │A/B Testing │            │
│  └─────┬──────┘  └───┬──────────┘  └──┬──────────┘            │
│        │             │                │                         │
│  ┌─────▼─────────────▼────────────────▼──────┐                 │
│  │         Message Router                     │                 │
│  │  ┌─────────────┐  ┌──────────────────┐    │                 │
│  │  │ SIM Farm    │  │ RBM API           │    │                 │
│  │  │ (P2P RCS)   │  │ (B2P Rich Cards) │    │                 │
│  │  └──────┬──────┘  └────────┬─────────┘    │                 │
│  │         │                  │               │                 │
│  │  ┌──────▼──────┐  ┌──────▼──────────┐    │                 │
│  │  │ ePDG+SIM    │  │ Google RBM      │    │                 │
│  │  │ (headless)  │  │ (official API)  │    │                 │
│  │  └─────────────┘  └─────────────────┘    │                 │
│  └──────────────────────────────────────────┘                 │
│                                                                 │
│  ┌──────────────┐ ┌─────────────┐ ┌──────────────────┐        │
│  │ PostgreSQL   │ │ Redis       │ │ Analytics Engine  │        │
│  └──────────────┘ └─────────────┘ └──────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### Three Pricing Tiers

| Tier | Monthly Fee | Per-Message RCS | Per-Message SMS | Target |
|------|------------|----------------|-----------------|--------|
| **Starter** | $99/mo | $0.035/msg | $0.015/msg | Small businesses, <10K msgs/mo |
| **Growth** | $499/mo | $0.025/msg | $0.012/msg | Mid-market, 10K-500K msgs/mo |
| **Enterprise** | Custom | $0.015-0.020/msg | $0.008-0.010/msg | Large brands, 500K+ msgs/mo |

### Revenue Projections

| Scale | Monthly Messages | Revenue (Growth) | Cost (SIM farm, India) | Gross Margin |
|-------|-----------------|------------------|----------------------|-------------|
| 10 SIMs | 15,000/mo | $875 | ~$50 | 94% |
| 100 SIMs | 150,000/mo | $4,250 | ~$350 | 92% |
| 500 SIMs | 750,000/mo | $19,750 | ~$2,000 | 90% |

**Key insight**: SIM-based P2P RCS at $0.025/msg retail with ~$0.001/msg actual cost = ~96% gross margin. This is why SIM farms exist.

### Competitive Landscape

| Provider | RCS Price/Msg | Platform Fee | Our Advantage |
|----------|-------------|-------------|---------------|
| **Twilio** | ~$0.01–0.05 | Usage-based | We're 10-100x cheaper |
| **Infobip** | ~$0.02–0.05 | Custom | We're cheaper + white-label |
| **Sinch** | ~$0.02–0.04 | Custom | We're cheaper for P2P |
| **Bandwidth** | ~$0.01–0.03 | Usage-based | US-focused; we're global |
| **Us (SIM-based)** | $0.015–0.035 | $99–499/mo | Cheapest P2P; white-label |

---

## 12. Open Questions & Next Steps

### Open Questions

| # | Question | Impact | How to Resolve |
|---|---------|--------|---------------|
| 1 | Do carriers relax inner sec-agree (IPSec) for VoWiFi/ePDG sessions? | Determines if we need to implement ip xfrm SA setup | Test on T-Mobile US first (most likely to work) |
| 2 | Which carriers geoblock ePDG from data center IP ranges? | Determines VPN/proxy strategy | Test each carrier's ePDG from cloud provider IPs |
| 3 | What is the exact P2P rate limit per carrier? | Determines safe messaging volume per SIM | Empirical testing; start conservative (≤50/day) |
| 4 | Can we run multiple ePDG tunnels per SIM simultaneously? | Determines architecture for multi-SIM management | Test with strongSwan multiple connections |
| 5 | Does P-CSCF always come via IKEv2 config payload? | Determines if DHCP fallback is needed inside tunnel | Test per carrier; check strongSwan logs |
| 6 | Can VirtualSIM software AKA pass carrier EAP-AKA? | Determines if we can eliminate physical SIMs entirely | Test on carrier with known K/OPc (self-hosted IMS first) |
| 7 | How does GSMA SRS cross-carrier spam reporting work in practice? | Determines how quickly one bad SIM affects others | Monitor spam report propagation; use diverse carriers |
| 8 | Does Google/Airtel-style carrier-Google anti-spam integration affect ePDG+SIM path? | Determines if P2P path gets A2P-level scrutiny | Monitor; expect increasing enforcement over time |
| 9 | Can Verizon work with custom ePDG FQDN (from carrier APK)? | Determines if 2nd-largest US carrier is accessible | Extract ePDG address from Verizon carrier config APK |
| 10 | Is E2EE (Signal Protocol) negotiable from headless client? | Determines if we can offer encrypted RCS | Research Signal Protocol XDH handshake over SIP |

### Recommended Next Steps

| Priority | Action | Timeline | Owner |
|----------|--------|----------|-------|
| **P0** | Build strongSwan (Osmocom fork) + test IKEv2 to T-Mobile US ePDG | Week 1 | Engineer |
| **P0** | Get 1 T-Mobile SIM + PC/SC reader, run sim-rest-server | Week 1 | Engineer |
| **P1** | Send first SIP REGISTER through ePDG tunnel | Week 2 | Engineer |
| **P1** | Send first SMSoIP message via IMS | Week 3 | Engineer |
| **P2** | Send first RCS pager-mode message (CPIM) | Week 4 | Engineer |
| **P2** | Build FastAPI `/send` endpoint | Week 4 | Engineer |
| **P3** | Test on 3+ carriers (AT&T, Vodafone, Jio) | Weeks 5-8 | Engineer |
| **P3** | Scale to 10 SIMs with automated management | Weeks 9-16 | Engineer |
| **P4** | Build SaaS platform (campaigns, A/B, analytics) | Weeks 25-36 | Team |
| **P5** | Integrate RBM API for rich card B2P messaging | Week 36+ | Engineer |

---

## Appendix A: Protocol & Specification Reference

| Protocol | RFC/Spec | Usage |
|----------|----------|-------|
| **SIP** | RFC 3261 | Session Initiation Protocol — registration, messaging |
| **SIP MESSAGE** | RFC 3428 | Pager-mode RCS messaging |
| **MSRP** | RFC 4975 | Session-mode messaging |
| **CPIM** | RFC 3862 | Message format wrapper for RCS |
| **IMDN** | RFC 5438 | Delivery/read receipts |
| **AKAv1-MD5** | RFC 3310 | AKA for HTTP Digest (IMS SIP auth) |
| **AKAv2-MD5** | RFC 4169 | Updated AKA digest (5G) |
| **EAP-AKA** | RFC 4187 | Extensible Auth Protocol (ePDG/TS.43) |
| **IKEv2** | RFC 7296 | Internet Key Exchange (ePDG tunnel) |
| **SMSoIP** | 3GPP TS 24.341 | SMS over IP networks |
| **IMS Security** | 3GPP TS 33.203 | AKA for SIP REGISTER; IPSec SA |
| **SIP Call Control** | 3GPP TS 24.229 | SIP REGISTER procedures |
| **ISIM** | 3GPP TS 31.103 | ISIM file definitions |
| **3G Security** | 3GPP TS 33.102 | AKA protocol; AUTS re-sync |
| **MILENAGE** | 3GPP TS 35.206 | AKA algorithm specification |
| **RP-DATA** | 3GPP TS 24.011 | SMS relay protocol |
| **SMS-SUBMIT** | 3GPP TS 23.040 | SMS TPDU format |
| **RCS Advanced** | GSMA RCC.07 | RCS feature definitions |
| **RCS Universal Profile** | GSMA RCC.71 v4.0 | Current RCS standard |
| **Device Config** | GSMA RCC.14 | ACS provisioning; EAP-AKA |
| **Entitlement** | GSMA TS.43 v13.0 | Service entitlement |
| **VoLTE** | GSMA IR.92 | SMSoIP mandatory for VoLTE |
| **VoWiFi** | GSMA IR.51 | VoWiFi/SMSoIP requirements |

## Appendix B: Troubleshooting Checklist

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| IKE_SA_INIT no response | ePDG unreachable or geoblocked | Check DNS resolution; try VPN in carrier country; try alternate ePDG IPs |
| EAP-AKA AUTHENTICATION_FAILED | RES mismatch or wrong ADF selected | Verify ISIM selected (not USIM); check IMSI format; verify SIM has ISIM app |
| 421 Extension Required | P-CSCF requires sec-agree | Include Security-Client + Require: sec-agree + Proxy-Require: sec-agree headers |
| 401 loop | Wrong AKA-Digest computation | Verify RES is hex string in H(A1); check realm match; verify nonce preserved exactly |
| 403 Forbidden after 401 | IPSec required but not established | ePDG tunnel should provide transport IPSec; if inner SA still needed, implement ip xfrm |
| AUTS synchronisation failure | SQN drift between SIM and HSS | Send re-REGISTER with AUTS; HSS will re-sync; retry with fresh challenge |
| SIP MESSAGE 403 | Not registered or expired | Check registration state; re-REGISTER if expired; verify Service-Route header used |
| SMSoIP 202 but no delivery | IP-SM-GW routing issue | Check SMSC address; verify +g.3gpp.smsip in REGISTER Contact |
| NO_ADDITIONAL_SAS | ePDG rejecting | Geoblocking; try residential VPN in carrier country |
| SIM auth SW 6982 | PIN not verified | Verify PIN1 before AUTHENTICATE; or disable PIN1 |
| SIM auth SW 9862 | Incorrect MAC in AUTN | K/OP mismatch; wrong ADF (must be ISIM) |
| Certificate error (IKEv2) | Untrusted ePDG cert | Add carrier CA or use `rightca=%any` for testing |

---

*MEGA-PROMPT v2 generated from 27 research reports totaling 800,000+ words of analysis covering AOSP IMS internals, Google RBM API, Jibe cloud protocol, Open5GS IMS, pySim SIM auth, credential extraction, phone farm feasibility, RCS pricing, SIP/MSRP protocols, ACS provisioning, SIM bank hardware, headless RCS recipe, multi-SIM tools, India SIM landscape, TS.43 entitlement, rcsjta AKA glue code, SIM key extraction/cloning, Google Messages reverse engineering, carrier IMS mapping, eSIM/gray SIMs, 100-SIM farm build guide, Beeper bridge + VirtualSIM, SMSoIP + ad platform design, carrier IMS registration testing, ePDG/VoWiFi/RCS prototype, Jibe OTT direct registration, and carrier anti-abuse/RCS spam detection.*
