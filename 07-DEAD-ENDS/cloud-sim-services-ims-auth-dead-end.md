# Cloud SIM Services for IMS Authentication - Dead End Analysis

**Source**: Firecrawl searches + research, 2026-05-16
**Updated**: 2026-05-17

> **Also dead**: 256-SIM banks (Dinstar SIMCloud, iQsim 256 Rack) connect SIMs to GSM modems (radio layer), NOT PCSC readers. They cannot perform EAP-AKA authentication needed for ePDG/IMS. They only do SMS/voice via the modem's AT command interface. For RCS you need APDU-level SIM access (PCSC) to compute AKA vectors.

---

## 1. Executive Summary

**None of the cloud SIM services can do carrier IMS authentication for RCS.** They all operate on their own MVNO networks, not on the target carrier's IMS core.

---

## 2. Service-by-Service Analysis

### 2.1 Twilio Super SIM
- **URL**: https://www.twilio.com/super-sim
- **Type**: IoT cellular connectivity
- **What it does**: Data connectivity for IoT devices, global roaming
- **Has SMS**: NO (IoT data only - no voice/SMS on Super SIM)
- **Has IMS**: NO
- **Has EAP-AKA**: NO (not for carrier IMS auth)
- **Has RCS**: **NO**
- **API**: REST API for SIM lifecycle management (activate/deactivate/suspend)
- **Pricing**: $0.10/SIM/month + data usage
- **Verdict**: **DEAD END for RCS** - this is IoT data-only, no voice/SMS/IMS

### 2.2 Hologram.io
- **URL**: https://www.hologram.io
- **Type**: IoT cellular connectivity platform
- **What it does**: Global IoT SIM fleet management
- **Has SMS**: YES (device-to-cloud SMS)
- **Has IMS**: NO
- **Has EAP-AKA**: NO
- **Has RCS**: **NO**
- **API**: REST API for SIM management, SMS forwarding via webhook
- **Key Feature**: MFA/TOTP on SIM (multi-factor auth for IoT)
- **Pricing**: $0.40/SIM/month + data
- **Verdict**: **DEAD END for RCS** - IoT SIMs don't register on carrier IMS

### 2.3 EMnify
- **URL**: https://www.emnify.com
- **Type**: IoT connectivity platform with REST API
- **What it does**: SIM lifecycle management, data connectivity
- **Has SMS**: YES (SMS to devices)
- **Has IMS**: NO
- **Has EAP-AKA**: NO (their API auth is OAuth2/JWT, not SIM-based)
- **Has RCS**: **NO**
- **API**: Full REST API (https://cdn.emnify.net/api/doc/)
- **Pricing**: €0.30/SIM/month + data
- **Verdict**: **DEAD END for RCS** - same as all IoT SIMs, no IMS

### 2.4 Telnyx
- **Type**: CPaaS + wireless carrier (MNVO in US)
- **Has SMS**: YES (programmable SMS API)
- **Has Voice**: YES (VoIP, not carrier VoLTE)
- **Has IMS**: **Their own MVNO IMS, NOT carrier IMS**
- **Has RCS**: Only via RBM API (not carrier IMS)
- **Verdict**: Different network from Jio/Airtel - can't do carrier IMS RCS

### 2.5 esim.dog
- **Type**: eSIM provisioning API
- **Has Phone Numbers**: YES (US/UK/NL)
- **Has SMS**: YES (via webhook)
- **Has IMS**: NO (not on carrier IMS)
- **Has RCS**: **NO**
- **Verdict**: Useful for SMS verification, NOT for RCS

---

## 3. Why Cloud SIMs Can't Do Carrier IMS RCS

The fundamental problem:

```
Cloud SIM Service (Hologram, EMnify, Twilio Super SIM)
    ↓
Their own MVNO core network
    ↓
Data roaming agreements with carriers
    ↓
Internet data connectivity ONLY

Carrier IMS RCS Requires:
    ↓
Jio/Airtel SIM card
    ↓
Jio/Airtel HSS (has K+OPc)
    ↓
Jio/Airtel IMS core (P-CSCF, S-CSCF)
    ↓
SIP REGISTER → 401 → AKA challenge → SIM computes RES
    ↓
IMS registered → RCS messaging
```

Cloud SIMs are on **different networks** with **different HSS/AuC databases**. Even if they had an IMS core (they don't), it wouldn't be Jio's IMS core, so you can't send RCS messages to Jio subscribers.

---

## 4. The ONLY Way to Get Carrier IMS Auth

| Method | Works? | Details |
|--------|--------|---------|
| Physical Jio SIM in PCSC reader | **YES** | Proven (Osmocom VoWiFi guide) |
| Physical Jio SIM in Android phone | **YES** | TelephonyManager.getIccAuthentication |
| Virtual SIM with K+OPc from Jio | **THEORETICAL** | K+OPc not extractable from carrier SIM |
| Cloud SIM service | **NO** | Different network, no IMS |
| eSIM (carrier) | **YES** | Same as physical SIM, but can't scale |
| eSIM (data-only) | **NO** | No IMS, no phone number |
| eSIM (enterprise/Telnyx) | **NO** | Different network |

---

## 5. Programmable SIM Alternative

If you can't extract K+OPc from carrier SIMs, you CAN:

### 5.1 sysmoISIM-SJA2 (Programmable ISIM)
- Buy from sysmocom (~€8/SIM)
- You PROGRAM the K+OPc yourself
- You set the IMSI, ISIM parameters
- **BUT**: This only works on YOUR OWN IMS core (Open5GS)
- Jio/Airtel's HSS won't have your K+OPc → auth will fail

### 5.2 The Chicken-and-Egg Problem
- To register on Jio's IMS: Need a SIM with K+OPc that Jio's HSS knows
- Jio's HSS only knows K+OPc for SIMs they issued
- You can't read K+OPc from Jio SIMs
- Therefore: You MUST use a real Jio SIM card

---

## 6. Conclusion

**Physical SIM cards in PCSC readers remain the ONLY viable path for carrier IMS RCS.** Every cloud/remote/virtual SIM alternative fails because:
1. They're on different networks (no carrier IMS)
2. They don't have the carrier's K+OPc in their HSS
3. They can't do EAP-AKA against the carrier's AAA server

**Cost reality for India**:
- 100× Jio SIMs + plans: ₹1,499 × 100 = ₹1,49,900/yr
- 13× sysmoOCTSIM: ₹3,51,000 one-time
- OR 100× consumer CCID readers: ₹50,000 one-time
- Server + USB infrastructure: ₹30,000-50,000 one-time
- **Year 1 total**: ₹5,31,000 - ₹5,51,000
- **Year 2+**: ₹1,49,900/yr (SIM renewals only)
