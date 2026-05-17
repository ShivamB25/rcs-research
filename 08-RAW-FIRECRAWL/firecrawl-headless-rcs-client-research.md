# Firecrawl Deep Research: Headless RCS Client on Carrier IMS

**Source**: Firecrawl Agent (019e3190-cd70-7688-8a6a-42f5d8e3b9f2)
**Date**: 2026-05-16
**Updated**: 2026-05-17 — added geoblocking confirmation, auth clarification, RFC 8229

> **CRITICAL UPDATE (May 17 2026)**: ePDG geoblocking is CONFIRMED. All Indian carriers (Jio, Airtel, Vi) block IKEv2 from non-India IPs. Tested from Singapore — all timeout. Server MUST have Indian IP. See `test-epdg-reachability.py` and `indian-mobile-proxy-epdg-bypass.md`. Also: strongSwan eap-sim-pcsc does NOT support EAP-AKA (only EAP-SIM). Use sim-rest-server instead. For IKE over TCP through SOCKS5 proxies, use libreswan 4.0+ (RFC 8229) — strongSwan doesn't support it.

---

## 1. Proven ePDG/VoWiFi + SIM Implementations

### 1.1 Osmocom VoWiFi with Asterisk (FULLY WORKING)
- **URL**: https://osmocom.org/projects/foss-ims-client/wiki/VoWiFi_with_Asterisk
- **Status**: PROVEN WORKING with real carrier networks (Vodafone, T-Mobile)
- **Stack**: strongSwan-epdg (Osmocom fork) + PCSC card reader + Asterisk + ami_usim.py
- **Auth Flow**:
  1. SIP REGISTER → 401 challenge
  2. AMI reads RAND/AUTN from IMS → calculates response via SIM
  3. Sends RES → 200 OK
- **Key**: Uses network namespace to isolate IPsec tunnel traffic
- **Vodafone note**: Requires SIP UPDATE delay in configuration

### 1.2 strongSwan-ePDG with ADF.USIM (T-Mobile SUCCESS)
- **URL**: https://discourse.osmocom.org/t/strongswan-epdg-with-adf-usim/2185
- **Code**: https://github.com/DentonGentry/strongswan-epdg
- **Status**: Successfully connected to T-Mobile ePDG
- **Key Innovation**: Modified eap_sim_pcsc plugin to read IMSI from ADF.USIM path (newer SIMs)
- **Result**: Reached P-CSCF, received SIP 401 Unauthorized with auth params

### 1.3 fasferraz SWu-IKEv2 (Python ePDG Client)
- **URL**: https://github.com/fasferraz/SWu-IKEv2
- **Language**: Python 3
- **Auth Methods**:
  - USB modem (AT+CSIM)
  - SmartCard reader (pyscard)
  - Remote HTTPS server
  - Software Milenage (Ki+OP/OPC)
- **Tested**: Works with Open5GS, designed for real carrier ePDGs
- **Speed**: "Decent IPSec speeds" even on limited hardware

### 1.4 worthdoingbadly.com VoWiFi Research (Partial Success)
- **URL**: https://worthdoingbadly.com/vowifi/
- **What Worked**: Android TelephonyManager.getIccAuthentication API for EAP-AKA'
- **What Failed**: Full ePDG connection to Mint Mobile (IKE_SA_AUTH error 24)
- **What Failed**: Direct SIP REGISTER to P-CSCF (421 Extension Required - missing sec-agree)
- **What Succeeded**: Captured IMSIs by spoofing ePDG with StrongSwan

---

## 2. RCS Messaging After IMS Registration

### 2.1 SIP MESSAGE (Pager Mode)
- Short messages sent directly in SIP MESSAGE requests
- No session establishment needed
- Per RCS 5.2 spec
- **This is sufficient for basic RCS text messaging**

### 2.2 MSRP (Session Mode)
- For larger content (images, video, carousels)
- SIP INVITE → SDP with MSRP parameters → MSRP session → content delivery
- **Note**: Some carriers have disabled MSRP in favor of HTTP file transfers (per rust-rcs-client)

### 2.3 RCS Procedures After Registration
1. SUBSCRIBE/NOTIFY for presence
2. PUBLISH for RCS capabilities
3. SIP MESSAGE for text messages
4. SIP INVITE + MSRP for rich content

---

## 3. Open Source RCS Application Servers

| Project | Type | Capabilities | Limitation |
|---------|------|-------------|------------|
| rcsjta | Client | GSMA Blackbird, TAPI 1.5/1.6, NIST-SIP | Android only, not headless |
| jega-ms/RCS-Server (Kamailio) | Server | Auth, Presence, XCAP, MSRP | Limited docs |
| OpenSIPS 3.3 | Component | Native MSRP relay, RCS capabilities | Component only |
| Kamailio IMS modules | Component | MSRP relay, GSMA RCS protocols | Component only |
| rust-rcs-client | Client | Auto-config, messaging, chatbot | Mobile arch only |
| zwyuan/rcs-fi-client | Client | Google Jibe SIP messaging | Google infra only |

---

## 4. Software AKA Computation (NO physical SIM needed if K+OPc known)

### 4.1 CryptoMobile (Python) - PROVEN
- **URL**: https://github.com/mitshell/CryptoMobile
- Pure Python Milenage implementation
- Computes f1, f2, f3, f4, f5 functions
- **API**: `Milenage(OP).f1(key, rand, SQN, AMF)` and `.f2345(key, rand)`
- Used in SWu-IKEv2 for software-based auth

### 4.2 osmo-auc-gen (Command Line)
- Osmocom command-line tool
- `osmo-auc-gen --3g --algorithm MILENAGE --key [K] --opc [OPC] --rand [RAND]`
- Outputs: AUTN, IK, CK, RES
- Used in production testing

### 4.3 PyHSS (Python HSS)
- **URL**: https://github.com/nickvsnetworking/pyhss
- Full HSS/AuC implementation
- Generates auth vectors from K+OPc stored in DB

### 4.4 Key Requirements for Software Auth
| Input | Description | Source |
|-------|-------------|--------|
| K (Ki) | 128-bit secret key | SIM provisioning data |
| OPc | 128-bit operator key | SIM provisioning data (or derive from OP) |
| RAND | 128-bit random challenge | Provided by network in 401 |
| SQN | Sequence number | For anti-replay |
| AMF | Auth Management Field | Typically 0x8000 |

| Output | Description |
|--------|-------------|
| RES | Authentication response |
| CK | Ciphering Key (128 bits) |
| IK | Integrity Key (128 bits) |
| AK | Anonymity Key (48 bits) |
| MAC-A | Message Authentication Code |

---

## 5. Scaling to 10+ SIMs

### 5.1 Physical SIM Approach
- Multiple PCSC card readers on USB hubs
- Parallel strongSwan instances with unique network namespaces
- Separate Asterisk instances per SIM or custom multi-registration SIP client
- **Complexity**: High hardware requirements, USB bandwidth limits

### 5.2 Software Auth Approach (BEST if K+OPc available)
- Obtain K+OPc for all SIMs from provisioning/manufacturing data
- Use CryptoMobile to compute AKA responses in pure software
- **No physical SIM cards needed**
- Can scale to 100+ registrations on single server
- **Limitation**: K+OPc not extractable from carrier SIMs

### 5.3 Hybrid Approach
- Extract K+OPc from programmable test SIMs once
- Use software authentication for all subsequent operations
- Most practical for testing/development

---

## 6. Practical Implementation Stack

### Proven Working Stack (Osmocom)
```
strongSwan-epdg + PCSC reader + Asterisk + ami_usim.py
```

### Alternative Stack (Python-first)
```
SWu-IKEv2 + software Milenage + custom SIP/RCS client
```

### Full Architecture for RCS Messaging
1. ePDG/IPsec: strongSwan-epdg OR SWu-IKEv2
2. SIM Auth: PCSC reader + EAP-AKA OR software Milenage
3. IMS Client: Asterisk with PJSIP OR custom SIP client
4. RCS Messaging: SIP MESSAGE (pager) OR SIP INVITE + MSRP (session)
5. Automation: AMI script or custom SIP stack

---

## 7. Key Resources
- VoWiFi with Asterisk: https://osmocom.org/projects/foss-ims-client/wiki/VoWiFi_with_Asterisk
- SWu-IKEv2: https://github.com/fasferraz/SWu-IKEv2
- strongSwan-epdg (Osmocom fork): https://gitea.osmocom.org/ims-volte-vowifi/strongswan-epdg
- CryptoMobile: https://github.com/mitshell/CryptoMobile
- Open5GS + Kamailio IMS Docker: https://github.com/herlesupreeth/docker_open5gs
- Nick vs Networking: https://nickvsnetworking.com/
