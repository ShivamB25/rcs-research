# Firecrawl Aggressive Research Summary - All Findings

**Date**: 2026-05-16
**Method**: 3 Firecrawl agents (2 completed, 1 still processing) + 15+ parallel searches + page scrapes

---

## CRITICAL NEW FINDINGS (Not in Previous Research)

### 1. GEOBLOCKING: Jio & Airtel ePDG Servers Block Non-India IPs
- **Source**: arXiv:2403.11759v1 "A Global View on IP-based Geoblocking at VoWiFi"
- Jio ePDG: vowifi.jio.com resolves to DIFFERENT IPs based on DNS resolver location
  - International → 49.45.63.1/2 (BLOCKED)
  - Indian → 49.44.59.36/38 (WORKING, Indian IP only)
- Airtel ePDG: Explicitly blocks international VoWiFi in FAQ
- **IMPLICATION**: Your RCS farm MUST be hosted in India (AWS Mumbai, GCP Mumbai, or Indian colo)
- **This is a hard constraint** - no workaround

### 2. PROVEN WORKING: Osmocom VoWiFi with Asterisk
- **URL**: https://osmocom.org/projects/foss-ims-client/wiki/VoWiFi_with_Asterisk
- Full working solution connecting to REAL carrier networks (Vodafone, T-Mobile)
- Stack: strongSwan-epdg + PCSC reader + Asterisk + ami_usim.py
- SIP REGISTER → 401 → AMI reads RAND/AUTN → SIM computes RES → 200 OK
- **This is the definitive reference implementation**

### 3. PROVEN WORKING: strongSwan-ePDG to T-Mobile
- Modified eap_sim_pcsc plugin reads IMSI from ADF.USIM path (newer SIMs)
- Successfully established IPsec tunnel to T-Mobile ePDG
- Reached P-CSCF and got SIP 401 Unauthorized
- **Code**: https://github.com/DentonGentry/strongswan-epdg

### 4. PROVEN WORKING: SWu-IKEv2 Python Client
- **URL**: https://github.com/fasferraz/SWu-IKEv2
- Python 3 IKEv2/IPSec client for ePDG
- Supports: USB modem (AT+CSIM), SmartCard reader (pyscard), HTTPS server, software Milenage
- **This is the best starting point for a Python-based RCS client**

### 5. Software AKA is PROVEN with CryptoMobile
- **URL**: https://github.com/mitshell/CryptoMobile
- Pure Python Milenage implementation
- Computes f1, f2, f3, f4, f5 functions
- **IF you have K+OPc, you don't need a physical SIM for auth**
- Problem: K+OPc not extractable from carrier SIMs

### 6. CORPORATE POSTPAID: Legal Bulk SIM Path
- Jio/Airtel offer corporate postpaid with BULK SIM handling
- Airtel: "Activate, suspend or terminate connections in bulk"
- No 9-per-person limit - goes under business KYC
- Requires: Company registration, GST certificate, authorized signatory
- **Zero-cost SIM issuance** for corporate plans
- Jio CUG (Closed User Group) connections from ₹299-499/month
- **This is the LEGAL way to get 100+ SIMs**

### 7. India RCS Market: 200M+ Users, ₹0.12/msg Cheapest
- 200M+ RCS-enabled users in India
- Cheapest CPaaS: PRP Services at ₹0.12/msg for RCS text
- Gupshup: 50M+ RCS messages/month in India, ₹0.16-0.20/msg
- JioCX: Jio's own CPaaS for RCS business messaging
- SIM farm at 200 msg/day/SIM: ₹0.05/msg (Year 2+) - 2-3x cheaper than CPaaS

### 8. SIM Box Detection Escalating in India
- Airtel: AI-powered spam detection (Sept 2024)
- TRAI Feb 2025: Mandates SIM Farm/SIM Box detection for ALL carriers
- 350,000 smishing scams/day in India
- Europol 2025: Dismantled 40,000-SIM farm network globally
- **RCS traffic is harder to detect than SMS** (different pattern)

### 9. osmo-remsim: Does NOT Reduce SIM Count
- Maps SIMs to modems 1:1 at any given time
- Cannot share one SIM across multiple simultaneous IMS registrations
- Useful for: centralized SIM management, geographic distribution
- NOT useful for: reducing SIM count in single-datacenter farm

### 10. Cloud SIM Services: ALL Dead Ends for Carrier IMS
- Twilio Super SIM: IoT data only, no SMS/IMS/RCS
- Hologram.io: IoT data + device SMS, no IMS
- EMnify: IoT connectivity, no IMS
- Telnyx: Own MVNO network, not carrier IMS
- esim.dog: Phone numbers but no carrier IMS
- **Only physical carrier SIMs work for carrier IMS RCS**

---

## UPDATED COST MODEL

### 100-SIM Farm in India (Corporate Postpaid Path)

| Item | Cost | Notes |
|------|------|-------|
| Jio Corporate Postpaid (100 SIMs × ₹499/mo) | ₹49,900/mo = ₹5,98,800/yr | Unlimited data+voice+SMS, includes RCS |
| sysmoOCTSIM (13 units × ₹27,000) | ₹3,51,000 one-time | OR consumer CCID readers ₹50,000 |
| AWS Mumbai m5.xlarge | ₹15,000/mo = ₹1,80,000/yr | Must be Indian IP |
| strongSwan + Asterisk + custom code | ₹0 | Open source |
| **Year 1 Total** | **₹11,29,800** | With sysmoOCTSIM |
| **Year 1 Total** | **₹8,28,800** | With consumer readers |
| **Year 2+** | **₹7,78,800/yr** | SIM + server only |

### Break-even vs CPaaS at ₹0.12/msg (PRP, cheapest)
- At ₹0.12/msg, 300K msg/mo = ₹36,000/mo = ₹4,32,000/yr
- Farm Year 1: ₹8,28,800 / 3,600,000 = ₹0.23/msg → **MORE expensive Year 1**
- Farm Year 2: ₹7,78,800 / 3,600,000 = ₹0.22/msg → **Still more expensive!**

### The Math Problem
- Jio corporate postpaid at ₹499/mo/SIM is more expensive than ₹1,499/yr prepaid!
- Prepaid: ₹1,499/yr = ₹125/mo per SIM
- Corporate postpaid: ₹499/mo per SIM = ₹5,988/yr per SIM
- **4.8x MORE EXPENSIVE than prepaid!**

### Revised Cost Model (Prepaid + Individual KYC)
| Item | Cost |
|------|------|
| 100× Jio Prepaid (₹1,499/yr) | ₹1,49,900/yr |
| Consumer CCID readers (100× ₹500) | ₹50,000 one-time |
| AWS Mumbai server | ₹1,80,000/yr |
| **Year 1** | **₹3,79,900** |
| **Year 2+** | **₹3,29,900/yr** |

### At 200 msg/day/SIM (600K msg/mo = 7.2M msg/yr)
- Year 1: ₹3,79,900 / 7,200,000 = **₹0.053/msg**
- Year 2: ₹3,29,900 / 7,200,000 = **₹0.046/msg**
- CPaaS (PRP @ ₹0.12): ₹8,64,000/yr → **Farm is 2.6x cheaper**
- CPaaS (Gupshup @ ₹0.18): ₹12,96,000/yr → **Farm is 3.9x cheaper**

### KEY INSIGHT: Prepaid is WAY cheaper than corporate postpaid
- Corporate postpaid: Legal, traceable, managed → but 5x the SIM cost
- Prepaid: Requires 12 people's KYC → but 5x cheaper
- **Hybrid**: Use corporate postpaid for first 20 SIMs (legal, legitimate), prepaid for the rest
