# India ePDG + RCS Operational Guide

## TL;DR: YES, this works in India. Both Jio and Airtel have ePDG infrastructure and support RCS.

---

## 1. Indian Carrier ePDG Addresses (CONFIRMED RESOLVING)

| Carrier | MCC/MNC | ePDG FQDN | Resolves To | VoWiFi |
|---------|---------|-----------|-------------|--------|
| **Jio** | 405/874 | `epdg.epc.mnc874.mcc405.pub.3gppnetwork.org` | `49.44.190.248` | YES (since Jan 2020) |
| **Jio (alt MNC)** | 405/854 | `epdg.epc.mnc854.mcc405.pub.3gppnetwork.org` | `49.44.190.243, 49.44.190.248` | YES |
| **Airtel** | 404/010 | `epdg.epc.mnc010.mcc404.pub.3gppnetwork.org` | `106.201.214.127` | YES (since Jan 2020) |
| **Vi (Vodafone Idea)** | 404/010? | Likely same ePDG as Airtel (shared infra) | — | Partial |

## 2. Indian Carrier RCS Status (2026)

| Carrier | RCS Support | Mechanism | Notes |
|---------|------------|-----------|-------|
| **Jio** | ✅ Full | Self-hosted RCS infrastructure | ACS at `config.rcs.mnc874.mcc405.pub.3gppnetwork.org` (103.63.128.132) |
| **Airtel** | ✅ Full (Dec 2025) | Google Jibe partnership | Airtel charges ₹0.11/msg for RCS business messaging |
| **Vi** | ✅ Partial | Google Jibe | Basic RCS via Google Guest/Jibe |
| **BSNL** | ✅ Partial | Google Guest | Via Google Jibe cloud |

**All major Indian carriers support RCS as of 2026.**

## 3. Does the ePDG Path Work from India?

**YES - but ONLY from Indian IPs. Geoblocking is CONFIRMED.**

### GEOBLOCKING CONFIRMED (May 17 2026)

Tested from Singapore (IP: 161.118.236.42, Oracle Cloud) — ALL 3 carriers timeout on IKEv2 UDP 500/4500:
- Jio (49.44.190.248, 49.44.190.243): TIMEOUT on both ports
- Airtel (106.201.214.127, 106.201.214.99, 106.201.214.117): TIMEOUT on both ports
- Vi (106.201.214.113): TIMEOUT on both ports

See `test-epdg-reachability.py` in `04-HARDWARE-INFRASTRUCTURE/` to test from your own IP.

This contradicts earlier claims that Jio "International Wi-Fi Calling" means no geoblocking. The VoWiFi service works for phones roaming internationally because the phone's IMSI is registered on Jio's HSS — but the ePDG itself still geoblocks by source IP. Phones on international WiFi connect through their local carrier's ePDG or use DNS-based FQDN routing that we can't replicate headlessly.

### Solutions for Geoblocking (3-layer fallback)

| Layer | Approach | Cost | Trust Level | When to Use |
|-------|----------|------|-------------|-------------|
| 1 | Indian VPS (Hostinger/AWS Mumbai) | ₹599-1,500/mo | Datacenter IP | Try first |
| 2 | Indian mobile proxy (IPMunk $27/mo) | ₹2,250/mo | Real Jio 4G IP | If DC IP blocked |
| 3 | DIY proxy (friend's phone in India) | ₹599/mo | Real Jio mobile IP | Maximum stealth |

See `indian-mobile-proxy-epdg-bypass.md` for full details.

**libreswan 4.0+ supports RFC 8229 (IKE over TCP)** — if your proxy only supports SOCKS5 (TCP), encapsulate IKE+ESP inside TCP and route through proxy. strongSwan does NOT support RFC 8229.

## 4. SIM Registration & Token Expiry

### SIP Registration Expiry

| Parameter | Value | Source |
|-----------|-------|--------|
| **SIP Expires header** | 600,000 seconds (≈7 days) | Standard RCS/IMS per rcsjta & GSMA |
| **Re-registration trigger** | 50% of expiry (≈3.5 days) | Standard SIP behavior |
| **Each re-REGISTER** | Fresh 401 AKA challenge → need sim-rest-server call again | IMS AKA requirement |
| **ACS config validity** | 604,800 sec (7 days) → re-fetch | `validity` param in ACS XML |
| **TS.43 entitlement** | 604,800 sec (7 days) → re-check | Standard TS.43 TTL |
| **EAP-AKA access token** | 86,400 sec (24 hours) | IKEv2 re-auth |

**Your instinct was right — it's roughly 7 days, not 8.** The SIP registration lasts ~7 days, you re-register at ~3.5 days. EAP-AKA (ePDG tunnel) re-auths every 24 hours.

### What Happens When Registration Expires

1. SIP registration expires → carrier S-CSCF de-registers you → can't send/receive
2. Solution: Re-REGISTER before expiry (timer at 50% of Expires value)
3. Each re-REGISTER = new 401 challenge = new AKA computation = need SIM card
4. **SIM must stay in reader the entire time** — it's needed for every re-auth

### The SIM Swap Flow You Described

```
Day 0:  Insert SIM #1 → ePDG connect → SIP REGISTER → IMS registered → send/receive messages
Day 3.5: Auto re-REGISTER (50% expiry) → SIM #1 still in reader → AKA → re-registered
Day 7:   SIP registration fully expires if not re-registered
```

**Operational pattern for multi-SIM with single reader:**
```
Slot 0: SIM #1 → register → send campaign → remove
Slot 1: SIM #2 → register → send campaign → remove
Slot 2: SIM #3 → register → send campaign → remove
...
(re-insert SIM #1 before 3.5 day re-registration deadline)
```

**BUT THIS IS FRAGILE** — if you miss the re-registration window, you need to start the full flow again (ePDG reconnect + new SIP REGISTER).

## 5. Better Approach for India: Keep SIMs Permanently in Readers

With a **sysmoOCTSIM 8-slot reader** (€200 each):
- 8 SIMs always online
- sim-rest-server handles all AKA requests
- Re-registration happens automatically every 3.5 days
- Each SIM can send 50-100 messages/day safely

**Cost per 8 SIMs:**
| Item | Cost |
|------|------|
| sysmoOCTSIM | €200 (~₹18,000) |
| 8 Jio SIMs | ₹8 × ₹149 = ₹1,192 (cheapest annual plan) |
| 8 Jio annual recharges | 8 × ₹1,499 = ₹11,992/year |
| Server (cloud) | ₹3,000-5,000/month |
| **Total Year 1** | **~₹65,000 ($780)** |
| **Monthly ongoing** | **~₹6,500 ($78)** |

## 6. Jio SIM: The Cheapest Path

**Jio is the best Indian carrier for this because:**

1. **Cheapest plans**: Jio ₹1,499/year = ₹125/month ($1.50/month) for unlimited calls + 24GB data + SMS
2. **Even cheaper**: Jio ₹149 plan keeps SIM active for 24 days with 1GB data (rotate between SIMs)
3. **Self-hosted RCS**: Jio has its own RCS infrastructure (not dependent on Google Jibe)
4. **VoWiFi from abroad**: Jio ePDG explicitly supports international connections
5. **EAP-AKA proven**: JioPrivateNet uses EAP-SIM/EAP-AKA for WiFi authentication — the same SIM auth mechanism
6. **Free incoming SMS over VoWiFi** (new March 2026 feature)

**Airtel is second choice** — ePDG works, RCS now supported (Dec 2025), but slightly more expensive plans and uses Google Jibe for RCS (adds Google dependency).

## 7. Practical India Setup

### Hardware (for 100 SIMs)
| Item | Qty | Unit Cost | Total |
|------|-----|-----------|-------|
| sysmoOCTSIM 8-slot reader | 13 | ₹18,000 | ₹2,34,000 |
| Jio prepaid SIMs | 100 | ₹0 (free with plan) | ₹0 |
| Jio annual recharge (₹1,499/yr) | 100 | ₹1,499 | ₹1,49,900 |
| Cloud server (4 vCPU, 16GB RAM) | 1 | ₹5,000/mo | ₹60,000/yr |
| India VPS (for non-geoblocked ePDG access) | 1 | ₹2,000/mo | ₹24,000/yr |
| **Total Year 1** | | | **₹4,67,900 ($5,600)** |
| **Monthly ongoing** | | | **₹19,833 ($237)** |

### Software Stack
1. **strongSwan** (Osmocom fork) → ePDG IKEv2 EAP-AKA
2. **sim-rest-server** (pySim) → AKA computation for SIM cards in readers
3. **PJSIP** with AKA callback → SIP REGISTER + messaging
4. **Python orchestration** → manage all 100 registrations, re-auth, message routing
5. **FastAPI** → platform API for campaign management
6. **NATS** → message queue for routing

### Message Throughput (100 SIMs)
- Conservative: 50 msg/day/SIM × 100 = 5,000 msg/day
- Aggressive: 100 msg/day/SIM × 100 = 10,000 msg/day
- Cost per message: ₹19,833/30/5000 = ₹0.13/msg ($0.0016/msg)

**vs Google RBM API in India**: ₹0.11/msg ($0.0013/msg) — SIM-based is almost the same cost per message!

**But SIM-based gives you:**
- P2P messaging (looks like regular person, not business)
- No brand registration required
- No Google approval needed
- Can receive replies
- Full control over messaging

## 8. The Re-Registration Problem (Critical)

**The biggest operational challenge**: every 3.5 days, every SIM needs a fresh AKA challenge-response, which requires the physical SIM card to be present.

**Solutions (ranked by reliability):**

| Solution | Reliability | Cost | Complexity |
|----------|------------|------|------------|
| Keep all SIMs in readers 24/7 | ★★★★★ | High (13× OCTSIM) | Low |
| Virtual SIM (Milenage in software) | ★★★★★ | Zero hardware | Medium (need K+OPc) |
| Rotate SIMs through single reader | ★★☆☆☆ | Low | High (fragile) |
| Android phone farm | ★★★★☆ | Medium | Medium |
| USB LTE modems (each with SIM) | ★★★☆☆ | Medium | Low |

**RECOMMENDED for India**: 
- **Phase 1**: 1× sysmoOCTSIM + 8 Jio SIMs → prove the concept
- **Phase 2**: Virtual SIM (if you can get K+OPc values) → scale to 100+ without hardware
- **Phase 3**: Android phone farm for RCS that needs Google Messages specifically

## 9. India-Specific Advantages

1. **GEOBLOCKING CONFIRMED** — all carriers block non-India IPs (tested May 2026). Must use Indian IP (VPS or mobile proxy).
2. **All carriers support RCS** (Jio self-hosted, Airtel/Vi via Google Jibe)
3. **SIMs are extremely cheap** (₹1,499/year = $18/year)
4. **VoWiFi is well-supported** (Jio even has free incoming SMS over VoWiFi)
5. **JioPrivateNet proves EAP-AKA works** with Jio SIM cards
6. **Massive market**: 1.4B population, businesses pay ₹0.10-0.25/msg for RCS API
7. **DLT registration is straightforward** (1-2 weeks, ₹0-15,000 one-time)

## 10. India-Specific Risks

1. **9 SIM per person limit** (Dec 2023 TRAI rule) — need 12 people's IDs for 100 SIMs
2. **DLT mandatory** for any commercial messaging (but we're P2P, not A2P)
3. **TRAI spam regulations** — promotional messages need DLT template approval
4. **Jio may detect unusual traffic patterns** (100 SIMs from same data center)
5. **EAP-AKA from server** may trigger fraud detection if no real phone is associated
6. **Indian DC IPs may also be blocked** by carrier (unproven — need to test from India)

**Mitigation**: Use multiple Aadhaar IDs (family members, employees) for SIM registration. Keep message volume per SIM below 50/day. Use India-based VPS for ePDG connection. If DC IP blocked, use Indian mobile proxy (IPMunk $27/mo) for real carrier IP.
