# Indian Mobile Proxy Research for ePDG Bypass

**Date**: 2026-05-17
**Status**: RESEARCHED — protocol problem SOLVABLE, providers identified
**Priority**: HIGH — this is the fallback if Indian VPS DC IP also gets blocked

---

## The Problem

Indian carriers (Jio, Airtel, Vi) **geoblock ePDG to Indian IPs only**. Confirmed by:
- arXiv paper (2403.11759v2): "A Global View on IP-based Geoblocking at VoWiFi"
- Our own test from Singapore (161.118.236.42): ALL 3 carriers → TIMEOUT on UDP 500/4500

If you host outside India, you MUST get an Indian IP to reach ePDG.

---

## The Protocol Problem (SOLVED)

IKEv2/IPsec uses:
- **UDP port 500** (IKE)
- **UDP port 4500** (NAT traversal, ESP-in-UDP)
- **IP protocol 50** (ESP) — not TCP, not UDP

Standard SOCKS5/HTTP proxies only forward **TCP**. You can't send IKEv2 UDP through them.

### Solution 1: UDP-Supporting Mobile Proxies

Several Indian mobile proxy providers support **UDP forwarding**:

| Provider | Price | IP Source | UDP? | Protocol | Notes |
|----------|-------|-----------|------|----------|-------|
| **IPMunk** | $27/mo | Jio/Airtel 4G SIMs | YES | SOCKS5 + UDP | Dedicated proxy, unlimited BW |
| **Coronium.io** | ~$30-50/mo | Jio/Airtel/Vi SIMs | YES | HTTP + SOCKS5 | Android-to-proxy software, 99.8% uptime |
| **SOAX** | $2/GB | Jio/Airtel/BSNL | YES (UDP/QUIC) | HTTP + SOCKS5 | Pay per GB, 5.1M+ Indian IPs |
| **NodeMaven** | ~$5/GB | Static residential | YES | HTTP + SOCKS5 | Sticky sessions |

**How it works**: Your IKEv2 UDP packets → SOCKS5 UDP relay → proxy provider's phone in India (on Jio 4G) → Jio ePDG. The ePDG sees a real Jio mobile subscriber IP.

### Solution 2: libreswan with RFC 8229 (IKE over TCP)

If UDP proxy doesn't work or isn't available:
- **libreswan 4.0+** supports [RFC 8229](https://datatracker.ietf.org/doc/html/rfc8229) — TCP Encapsulation of IKE and IPsec Packets
- strongSwan does NOT support this yet (issue [#2189](https://wiki.strongswan.org/issues/2189) open since 2020)
- With RFC 8229, IKE+ESP goes inside TCP → TCP goes through ANY SOCKS5 proxy

**Architecture**:
```
libreswan (RFC 8229 enabled) → TCP to ePDG:4500
  → through SOCKS5 proxy (Indian mobile proxy)
  → proxy forwards TCP to ePDG
  → ePDG sees connection from Jio mobile IP
```

### Solution 3: WireGuard Tunnel to Indian VPS (simplest)

Don't use a proxy at all. Just host in India:
- Rent Indian VPS (₹599/mo Hostinger, or AWS Mumbai free tier)
- Run strongSwan + PJSIP on the VPS
- SIM readers connect to VPS via sim-rest-server REST API (over WireGuard tunnel)
- VPS has Indian IP → ePDG accepts connection

**But**: If Jio blocks Indian datacenter IPs too (not just foreign), you fall back to Solutions 1/2.

---

## Recommended Architecture

### Layer 1: Indian VPS (try first, cheapest)

```
[Your machine, anywhere]
  ├── sysmoOCTSIM (SIM readers)
  ├── sim-rest-server (exposes REST API)
  └── WireGuard tunnel ─────► [Indian VPS - ₹599/mo]
                                 ├── strongSwan (EAP-AKA via sim-rest-server REST)
                                 ├── PJSIP (SIP MESSAGE)
                                 └── FastAPI orchestration
                                    │
                                    ▼
                              [Jio ePDG] → [IMS] → RCS delivered
```

- **Cost**: ₹599/mo (Hostinger) or ₹0 (AWS free tier)
- **Risk**: Jio may block datacenter IP ranges
- **If blocked**: move to Layer 2

### Layer 2: Indian Mobile Proxy (if DC IP blocked)

```
[Your machine, anywhere]
  ├── sysmoOCTSIM + sim-rest-server
  └── libreswan (RFC 8229) ──► [SOCKS5: Indian mobile proxy - $27/mo]
                                   │ (real Jio 4G IP)
                                   ▼
                              [Jio ePDG] → [IMS] → RCS delivered
```

- **Cost**: $27/mo (~₹2,250/mo) per proxy instance
- **Risk**: proxy uptime 95-99%, provider reliability
- **Advantage**: ePDG sees REAL Jio mobile subscriber IP — maximum trust

### Layer 3: DIY Mobile Proxy (maximum control, cheapest long-term)

```
[India: Friend's house/office]
  └── Android phone + Jio SIM (₹5,000 one-time)
      └── Socseeds/Proxidize proxy app
         └── WireGuard/Shadowsocks server
            │
            ▼ (accessible from anywhere)
[Your machine, anywhere]
  ├── sysmoOCTSIM + sim-rest-server
  └── strongSwan → WireGuard → [DIY proxy in India] → Jio ePDG
```

- **Cost**: ₹5,000 one-time + ₹599/mo Jio recharge
- **Risk**: phone uptime (90-95%), physical access needed for issues
- **Advantage**: full control, real Jio IP, cheapest monthly cost

---

## Cost Comparison: Hosting Approaches

| Approach | Monthly Cost | IP Type | ePDG Trust Level | Uptime | Setup |
|----------|-------------|---------|-------------------|--------|-------|
| AWS Mumbai | ₹0-1,500 | Cloud DC | Low (if DC blocked) | 99.99% | Easy |
| Hostinger India VPS | ₹599 | Indian DC | Low-Medium | 99.9% | Easy |
| IPMunk mobile proxy | ₹2,250 ($27) | Real Jio 4G | **HIGH** | 95-99% | Easy |
| Coronium.io proxy | ₹2,500-4,000 | Real Jio/Airtel | **HIGH** | 95-99% | Easy |
| SOAX (pay/GB) | ₹160/GB | Real Jio/Airtel | **HIGH** | 99% | Easy |
| DIY proxy (friend) | ₹599 | Real Jio 4G | **HIGHEST** | 90-95% | Medium |

---

## ePDG IPs (Resolved via DNS)

| Carrier | FQDN | IPs |
|---------|------|-----|
| Jio | `epdg.epc.mnc856.mcc405.pub.3gppnetwork.org` | 49.44.190.248, 49.44.190.243 |
| Airtel | `epdg.epc.mnc010.mcc404.pub.3gppnetwork.org` | 106.201.214.127, 106.201.214.99, 106.201.214.117 |
| Vi | `epdg.epc.mnc002.mcc404.pub.3gppnetwork.org` | 106.201.214.113 |

**All 7 IPs confirmed BLOCKED from Singapore (161.118.236.42) on ports 500 & 4500.**

---

## Quick Test Command

From any server, test if you can reach Jio ePDG:

```bash
# Simple curl won't work (IKEv2 is UDP), use our Python tester:
python3 test-epdg-reachability.py

# Or raw Python one-liner:
python3 -c "
import socket, struct
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.settimeout(5)
h=struct.pack('!IIBBII',0xDEADBEEF,0,0x20,0x22,0x08,28)[:28]
# Fix: proper IKE header
h=struct.pack('!II',0xDEADBEEF,0)+struct.pack('!BB',0,0x20)+struct.pack('!BB',0x22,0x08)+struct.pack('!II',0,28)
s.sendto(h,('49.44.190.248',500))
try:
 d,a=s.recvfrom(4096);print(f'REACHABLE: {len(d)}B from {a}')
except:print('BLOCKED: no response (need Indian IP)')
"
```

---

## What to Do Next

1. **Spin up an Indian VPS** (Hostinger ₹599/mo or AWS Mumbai free tier)
2. **Run the reachability test FROM the Indian VPS**: `python3 test-epdg-reachability.py`
3. **If REACHABLE from Indian VPS**: You're done. Layer 1 works.
4. **If still BLOCKED**: Indian DC IPs also filtered. Move to Layer 2 (IPMunk mobile proxy).
5. **If Layer 2 works**: You have a real Jio mobile IP. Maximum stealth.

The proxy approach gives you a **real carrier mobile IP** that ePDG inherently trusts. This is strictly better than any datacenter IP.
