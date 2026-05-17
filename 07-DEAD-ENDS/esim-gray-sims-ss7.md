# eUICC/eSIM Abuse, Gray Market SIMs & SS7/Diameter Attack Surface for RCS

**Date:** May 2026  
**Scope:** Three-part research on (1) eUICC/eSIM programmable ISIM profiles at scale, (2) gray market bulk SIM sourcing, and (3) SS7/Diameter attack surface for RCS number hijacking.  
**Builds on:** sim-key-extraction-cloning.md, india-sim-rcs-landscape.md, carrier-ims-mapping.md

---

## Table of Contents

1. [Part 1: eUICC/eSIM for RCS](#part-1-euiccesim-for-rcs)
2. [Part 2: Gray Market SIM Sourcing](#part-2-gray-market-sim-sourcing)
3. [Part 3: SS7/Diameter for RCS](#part-3-ss7diameter-for-rcs)
4. [Summary: Attack Surface Comparison](#summary-attack-surface-comparison)

---

## Part 1: eUICC/eSIM for RCS

### 1.1 Can We Create Our Own ISIM eSIM Profiles with Custom K/OP/IMPI/IMPU?

**Answer: YES, but with significant caveats around GSMA certification and device compatibility.**

The GSMA eSIM ecosystem defines a profile package format called the **Unprotected Profile Package (UPP)** that contains all the elements of a SIM subscription — including ISIM application data. The UPP is then cryptographically protected (signed and encrypted) into a **Protected Profile Package (PPP)** before delivery to the eUICC.

A UPP can include:
- **USIM application** (mandatory for cellular connectivity) — IMSI, K, OPc, MSISDN, etc.
- **ISIM application** (optional but spec-compliant) — IMPI, IMPU, DOMAIN, P-CSCF, K_isim, OPc_isim
- **Java Card applets** (SIM Toolkit applications, etc.)
- **NAA (Network Access Application)** configuration
- **PIN/PUK** values
- **Service provider name**, icons, etc.

**Technical feasibility of ISIM in eSIM profiles:**
- The eUICC Profile Package: Interoperable Format Technical Specification (published by the Trusted Connectivity Alliance, formerly SIMalliance) explicitly defines ISIM as a supported application within a profile
- The GSMA SGP.22 RSP specification does NOT prohibit ISIM in eSIM profiles
- The SIMalliance LTE UICC Profile specification explicitly references ISIM for IMS/VoLTE/RCS
- Commercial eSIM profiles from operators that offer VoLTE routinely include ISIM applications

**The catch — GSMA PKI certification chain:**
- To load a profile onto a consumer eUICC (the chip in your phone), the SM-DP+ server must present a certificate chain signed by the **GSMA Root CA** (also called the CI — Certificate Issuer)
- The eUICC validates this certificate chain during the **Common Mutual Authentication** (CMA) handshake before accepting any profile
- Without a GSMA-signed certificate, a consumer eUICC will **reject** the profile download
- GSMA only issues SM-DP+ certificates to accredited entities (MNOs, MVNOs, and certified eSIM service providers)

**Workaround paths:**

| Path | Feasibility | Description |
|------|------------|-------------|
| **Test CI (SGP.26)** | ✅ Works for research | GSMA defines a test Certificate Issuer (CI) in SGP.26 with publicly known test keys. osmo-smdpp uses this test CI. eUICCs that accept the test CI (like sysmoEUICC1) will accept profiles from an osmo-smdpp server. Consumer phone eUICCs do NOT accept the test CI. |
| **Compromised GSMA cert** | ⚠️ Research demonstrates | Security Explorations (July 2025) demonstrated extraction of GSMA eUICC identity certificates from Kigen eUICC cards, enabling download and decryption of any MNO's eSIM profiles. This is a severe vulnerability but requires physical access to a vulnerable eUICC card. |
| **OpenRSP / uncertified SM-DP+** | ⚠️ Only on test eUICCs | Running your own SM-DP+ with self-signed certificates only works on eUICCs that don't enforce CMA (test cards, not production phone eUICCs). StackOverflow discussions confirm this limitation. |
| **MVNO agreement** | ✅ Legitimate | If you register as an MVNO and obtain a GSMA SM-DP+ certificate, you can provision your own eSIM profiles including ISIM to any consumer phone eUICC. This is the legitimate path. |

### 1.2 Open-Source SM-DP+ Server: osmo-smdpp

**osmo-smdpp** is a proof-of-concept implementation of a minimal SM-DP+ (Subscription Manager — Data Preparation Plus) as specified in GSMA SGP.21/SGP.22 for Consumer eSIM Remote SIM Provisioning.

**Source:** Part of the pySim project — `osmo-smdpp.py` in the osmocom/pysim repository  
**Documentation:** https://euicc-manual.osmocom.org/docs/rsp/sm-dp-plus/  
**Status:** Research/proof-of-concept — NOT production-grade

**What osmo-smdpp can do:**
- Implement ES20 (SM-DP+ to eUICC) interface for profile download
- Use GSMA SGP.26 test CI certificates for signing
- Generate and serve eSIM profiles to test eUICC cards
- Support the full CMA (Common Mutual Authentication) handshake
- Create UPP (Unprotected Profile Package) files and protect them for delivery

**What osmo-smdpp cannot do (currently):**
- Sign profiles with production GSMA certificates (no access to production CI private keys)
- Serve profiles to production/consumer phone eUICCs (phones enforce production CI validation)
- Scale to production volumes (it's a single-process Python application)
- Handle the full SM-DS (Discovery Server) role for automated profile discovery

**Companion tools:**
- **pySim eSIM libraries** — Implement various SGP.21/SGP.22 interfaces including ES10a/b/c (eUICC to LPA), ES8+ (LPA to SM-DP+), and interoperable profile decoding/validation
- **MiniLPA** (https://github.com/EsimMoe/MiniLPA) — Open-source Local Profile Assistant for loading eSIM profiles onto physical eUICC cards via PC/SC reader
- **sysmoEUICC1** — sysmocom's physical eUICC card in 4FF form factor that accepts test CI-signed profiles

### 1.3 How to Create a UPP (Unprotected Profile Package) with ISIM Application

The UPP is defined by the **eUICC Profile Package: Interoperable Format Technical Specification** (published by Trusted Connectivity Alliance). It's an ASN.1/DER-encoded binary blob containing:

**UPP Structure (simplified):**
```
ProfilePackage ::= SEQUENCE {
    header        ProfileHeader,
    platform      PlatformElasticity,    -- eUICC OS configuration
    telecom       TelecomElasticity,     -- USIM + ISIM applications
    non-telecom   [optional]             -- Java Card applets, etc.
}

TelecomElasticity ::= SEQUENCE {
    usim          [mandatory] USIMApplication,
    isim          [optional]  ISIMApplication,
    csim          [optional]  CSIMApplication,
    ruim          [optional]  RUIMApplication
}

ISIMApplication ::= SEQUENCE {
    pin           PINConfiguration,
    df-telecom    DFTelecom,
    df-usim       DFUSIM,         -- Shared with USIM
    df-isim       DFISIM,         -- ISIM-specific files
    apps          Applications     -- Java Card apps under ISIM
}

DFISIM ::= SEQUENCE {
    ef-impi       EF_IMPI,        -- IMS Private User Identity (e.g., user@ims.mnc001.mcc001.3gppnetwork.org)
    ef-impu       EF_IMPU,        -- IMS Public User Identity (e.g., sip:+1234567890@ims.mnc001.mcc001.3gppnetwork.org)
    ef-domain     EF_DOMAIN,      -- Home Network Domain (e.g., ims.mnc001.mcc001.3gppnetwork.org)
    ef-pcscf      EF_PCSCF,       -- P-CSCF Address (optional)
    ef-ist        EF_IST,         -- ISIM Service Table
    ef-arr        EF_ARR,         -- Access Rule Reference
    auth-key      EF_ISIM_AUTH_KEY, -- K + OPc + algorithm for ISIM AKA
    auth-counter  EF_ISIM_SQN      -- SQN counter for ISIM
}
```

**Creating a UPP with ISIM using pySim:**

pySim's eSIM library (`pySim.esim`) provides programmatic tools for constructing UPPs:

```python
# Conceptual usage based on pySim eSIM library documentation
from pySim.esim import *

# Create profile with ISIM
profile = ProfilePackage(
    iccid="8900100000000000001",
    pin1="1234",
    pin2="5678",
    adm1="00000000",
    # USIM application
    usim=USIMApplication(
        imsi="001010000000001",
        k=bytes.fromhex("841EAD87BC9D974ECA1C167409357601"),
        opc=bytes.fromhex("3211CACDD64F51C3FD3013ECD9A582A0"),
        algorithm="milenage",
        msisdn="+1234567890"
    ),
    # ISIM application (optional)
    isim=ISIMApplication(
        impi="000001@ims.mnc001.mcc001.3gppnetwork.org",
        impu=["sip:+1234567890@ims.mnc001.mcc001.3gppnetwork.org"],
        domain="ims.mnc001.mcc001.3gppnetwork.org",
        pcscf="pcscf.ims.mnc001.mcc001.3gppnetwork.org",
        k=bytes.fromhex("841EAD87BC9D974ECA1C167409357601"),  # Can be same or different from USIM K
        opc=bytes.fromhex("3211CACDD64F51C3FD3013ECD9A582A0"),
        algorithm="milenage"
    )
)

# Generate the UPP
upp = profile.to_upp()

# Protect the UPP (sign + encrypt for target eUICC)
ppp = protect_profile(upp, euicc_cert=target_euicc_cert, sm_dp_plus_key=sm_dp_key)
```

**Key considerations for ISIM in eSIM profiles:**
1. **K and OPc for ISIM can differ from USIM** — In commercial deployments, carriers often use the same K/OPc for both USIM and ISIM, but the spec allows them to be independent
2. **IMPI format** — `<user>@ims.mnc<MNC>.mcc<MCC>.3gppnetwork.org` (standard) or custom
3. **IMPU format** — SIP URI: `sip:+<MSISDN>@<domain>` or `tel:+<MSISDN>`
4. **P-CSCF** — Can be pre-populated in EF_PCSCF or left empty (discovered via PCO/DHCP at attach time)
5. **The UPP must be protected before delivery** — The protection process involves signing with the SM-DP+ private key and encrypting with the eUICC's public key

### 1.4 Cost of eSIM-Compatible Devices vs Physical SIM Card Readers

| Device | Purpose | Cost | Notes |
|--------|---------|------|-------|
| **sysmoEUICC1** (sysmocom) | Physical eUICC card (4FF) for testing | ~€10-15/card | Accepts test CI profiles, used with MiniLPA + PC/SC reader |
| **sysmoOCTSIM** | 8-slot SIM reader for phone farms | ~€200-220 | Works with sysmoEUICC1 and regular SIMs |
| **Omnikey 3121** | Single PC/SC USB reader | $20-50 | Standard reader for MiniLPA profile loading |
| **Smartphone with eSIM** | Consumer device with embedded eUICC | $150-1000+ | Production eUICC that ONLY accepts GSMA-certified profiles |
| **Pixel phone** | Best for eSIM development/testing | $350-500 | Open eSIM API access via Android EuiccService |
| **sysmoISIM-SJA5** | Programmable physical SIM (not eUICC) | ~€8-12/card | Full ISIM support, known K/OPc, pySim-native |

**Cost comparison for 100 profiles:**

| Method | Hardware Cost | Per-Profile Cost | Total (100 profiles) | Limitation |
|--------|--------------|-----------------|---------------------|------------|
| **Programmable SIM (SJA5)** | $50 (reader) | ~€8-12/card | ~$900-1300 | Only works on your own IMS core |
| **Test eUICC (sysmoEUICC1)** | $50 (reader) + MiniLPA | ~€10-15/card | ~$1100-1700 | Only accepts test CI profiles |
| **Consumer phone eSIM** | $350-500/phone | Free profile download | ~$35,000-50,000 (100 phones!) | Only accepts GSMA-certified profiles from real MNOs |
| **Virtual SIM (software)** | $0 | $0 | $0 | Only works on your own IMS core |

**Verdict:** For self-hosted IMS cores, programmable physical SIMs (sysmoISIM-SJA5) or VirtualSIMs are far more economical than eUICC-based approaches. The eUICC path only makes sense if you need to register on a carrier's IMS core — and for that, you need carrier-provided eSIM profiles, not self-created ones.

### 1.5 Can eSIM Profiles Include ISIM (Not Just USIM)?

**YES** — the GSMA eSIM specifications fully support ISIM as an optional application within a profile.

**Evidence:**
1. **eUICC Profile Package: Interoperable Format Technical Specification** defines ISIM as a standard component of the TelecomElasticity section of a profile
2. **SIMalliance LTE UICC Profile for MNOs** document explicitly references ISIM for IMS/VoLTE/RCS in eSIM profiles
3. **GSMA IMS Profile for Converged IP Communications (NG.102)** states that if the UICC contains an ISIM application, it should be used for IMS registration; if not, USIM-derived credentials are used
4. **Commercial carriers** routinely provision eSIM profiles with ISIM for VoLTE — this is standard practice for any carrier offering VoWiFi/VoLTE

**Practical reality:** Most carrier-issued eSIM profiles DO include ISIM because they need it for VoLTE and VoWiFi functionality. When you download an eSIM from T-Mobile, AT&T, Jio, etc., the profile typically includes both USIM and ISIM applications.

### 1.6 Scale: Can We Provision 100+ eSIM Profiles Programmatically?

**For test eUICCs (sysmoEUICC1):** YES, but limited by physical hardware.
- Each sysmoEUICC1 card is a physical 4FF card that needs to be loaded one at a time via PC/SC reader
- MiniLPA can automate profile loading: `minilpa download --smdp <addr> --id <match-id>`
- A script can iterate over 100+ profiles and load them sequentially onto 100 cards
- Throughput: ~2-5 minutes per profile download (CMA handshake + profile install)
- **Bottleneck: You need 100 physical sysmoEUICC1 cards** (~€1000-1500 for 100 cards)
- Each card can hold **multiple profiles** (modern eUICCs support MEP — Multiple Enabled Profiles) but only one is active at a time

**For consumer phone eUICCs:** You need GSMA-certified SM-DP+ access.
- Enterprise eSIM management platforms (WeConnect, Telnyx, Airhub, etc.) offer bulk provisioning APIs
- These platforms connect to carrier SM-DP+ servers with production certificates
- You can programmatically generate 100+ activation codes (QR codes) via API
- **But each profile must be from a real MNO** — you cannot provision custom ISIM profiles with your own K/OPc
- **Cost:** Enterprise eSIM plans vary; bulk data-only eSIMs cost $3-10 per profile

**For self-hosted IMS core (the practical path):** Use VirtualSIM or programmable physical SIMs.
- VirtualSIM: Create 100+ software instances with different K/OPc/IMPI/IMPU — **$0 hardware cost**
- Programmable SIMs: Provision 100+ sysmoISIM-SJA5 cards via pySim-prog — **~$900-1300**
- Both scale arbitrarily since you control the HSS/S-CSCF

**Enterprise eSIM Bulk Provisioning APIs (for carrier profiles):**

| Provider | API Type | Bulk Capability | Price |
|----------|----------|----------------|-------|
| **WeConnect** | REST API | QR code generation, bulk provisioning, MDM integration | Contact sales |
| **Telnyx** | REST API | eSIM-as-a-service, embedded in digital products | $1-5/eSIM activation |
| **eSIM Access** | REST API | Wholesale eSIM reseller API, 100+ countries | Per-usage |
| **Airhub** | REST API | White-label eSIM reseller, B2B wholesale | Per-usage |
| **Micro eSIM** | REST API | B2B partner platform, API-enabled delivery | Contact sales |
| **Nomad eSIM** | REST API | Enterprise & partner program | Per-usage |

**Important caveat:** These enterprise APIs give you carrier-provisioned eSIM profiles with real phone numbers. They do NOT let you specify your own K/OPc or create custom ISIM profiles. The profiles come from carrier SM-DP+ servers with production certificates.

### 1.7 Security Explorations eUICC Hack: Implications for eSIM Profile Theft

In July 2025, Security Explorations (Polish research lab) published findings of a major eUICC security breach:

**What was hacked:** Kigen eUICC card (used in billions of SIMs per Kigen's claims)
- Exploited Java Card type confusion vulnerabilities (dating back to 2019 Oracle Java Card bugs that were never properly fixed)
- Extracted GSMA eUICC identity certificate and private ECC key
- Demonstrated automatic, reliable exploitation
- Kigen confirmed the vulnerability and paid $30,000 bug bounty

**Critical implications:**

1. **Profile decryption:** With a stolen eUICC certificate, an attacker can download and **decrypt eSIM profiles from any MNO in cleartext** — including AT&T, Vodafone, O2, Orange, China Mobile, T-Mobile, etc. The profiles contain K, OPc, AMF, and all subscriber secrets.

2. **No MNO detection:** Once an eSIM profile is downloaded, the MNO has **no ability to detect that the profile has been tampered with or that its secrets have been exposed**. Modified profiles (with injected Java Card apps) were loaded into test eUICCs and worked fine for calls, SMS, etc.

3. **Cross-MNO impact:** A single compromised eUICC identity certificate can be used to peek into eSIM profiles of **any MNO** — this is an architectural weak point in the eSIM trust model.

4. **OPc and AMF exposed:** The operator's K/OPc/AMF are embedded in eSIM profiles and become accessible upon profile decryption. These are the exact keys needed for IMS AKA authentication.

5. **Backdoor feasibility:** Security Explorations demonstrated that modified profiles with custom Java Card apps work on real phones, raising the specter of eSIM-based backdoors that the carrier cannot detect or disable.

**Mitigation status:** Kigen has classified this as CVSS 6.7 (Medium) and is implementing fixes. However, the fundamental architectural issue — that one compromised eUICC cert can decrypt profiles from any MNO — remains unaddressed in the GSMA specification.

---

## Part 2: Gray Market SIM Sourcing

### 2.1 Sources for Cheap Bulk SIMs

#### Wholesale / Bulk SIM Distributors (US/EU)

| Source | Type | Cost per SIM | Minimum Order | KYC Required | Notes |
|--------|------|-------------|---------------|-------------|-------|
| **AH Wholesale** (ahwholesale.com) | US prepaid SIM distributor | $0.50-2.00 (blank) | Varies | No (for blank SIMs) | Pre-loaded with 30-day plans available |
| **MrSIMCard** (mrsimcard.com) | International SIM wholesaler | $1-5 | Varies | No (blank SIMs) | Global carrier SIMs |
| **Simple Cell Bulk** (simplecellbulk.com) | US wholesale dealer | $0.50-3.00 | Varies | No (blank SIMs) | AT&T, T-Mobile, Verizon SIMs |
| **IndiaMart** (dir.indiamart.com) | India wholesale marketplace | ₹10-50 ($0.12-0.60) | 100+ | Yes (post-Dec 2023) | Jio, Airtel, Vi, BSNL SIMs |

#### No-KYC / Anonymous SIM Providers

| Provider | Type | Cost | Payment | KYC | Notes |
|----------|------|------|---------|-----|-------|
| **Silent.link** | eSIM (data only) | ~$1.50/GB | Crypto (BTC, XMR) | **None** | 160+ countries, instant delivery, no account needed |
| **Simsup** | SIM + eSIM | Varies | Monero (XMR) | **None** | Guarantees no identity verification, accepts Monero |
| **ZeroID** | eSIM (data only) | Varies | Solana | **None** | 140+ countries, blockchain-powered |
| **encryptSIM** | eSIM (data only) | Varies | Crypto or card | **None** | Privacy-first, no contracts |
| **Bitrefill** | eSIM (data only) | Varies | BTC, ETH, USDT | **None** | 186 countries, major eSIM provider |
| **Cryptorefills** | eSIM (data only) | Varies | Crypto | **None** | Anonymous eSIM purchase with crypto |
| **eSIM.me** | Physical eSIM adapter | ~€25 (adapter) | Standard | Varies | Adapter that holds up to 15 eSIM profiles; works with any phone |

**Critical limitation:** All no-KYC eSIM providers offer **data-only** profiles. They do NOT provide:
- Phone numbers (MSISDN)
- SMS/MMS capability
- VoLTE/VoWiFi
- IMS/ISIM registration
- RCS capability

These data-only eSIMs are **not usable for RCS** — RCS requires a phone number and IMS registration.

#### Tourist / Travel SIMs

| Provider | Type | Cost | Countries | Phone Number | Notes |
|----------|------|------|-----------|-------------|-------|
| **OneSimCard** | Physical travel SIM | $30-60 + data | 200+ | Yes (multiple numbers) | Includes voice/SMS; roaming-based |
| **Orange Travel** | SIM + eSIM | €10-30 + data | Europe, global | Yes (French number) | Good for Europe |
| **Travelsim** | Physical SIM | $25-50 + data | 200+ | Yes | International roaming SIM |
| **Airalo** | eSIM (data only) | $1-5 + data | 200+ | **No** | Data only — no RCS |
| **Nomad eSIM** | eSIM (data only) | $2-10 + data | 170+ | **No** | Data only — no RCS |

**Tourist SIMs with phone numbers** can potentially be used for RCS (they have real phone numbers and can register on carrier IMS), but they are typically expensive ($30-60/SIM) and have limited validity.

#### M2M / IoT SIMs

| Provider | Cost per SIM/month | Coverage | Data | Voice/SMS | Notes |
|----------|-------------------|----------|------|-----------|-------|
| **Open M2M** | €0.99/month | Global | Low | **No** | GPS tracking, alarm systems |
| **SpeedTalk Mobile** | ~$20/year (Amazon) | US | 64kbps | **No** | IoT data only |
| **1NCE** | €0.50-1.00/month | Global (eUICC) | Low | **No** | 10-year lifetime SIMs |
| **Datablaze** | $2-5/month | US | Varies | **No** | IoT/M2M focused |
| **US Mobile IoT** | Contact sales | US | Varies | **No** | IoT platform with API |

**M2M/IoT SIMs are NOT usable for RCS** — they are data-only, often throttled to 64kbps, and have no voice/SMS/IMS capability. India's DoT specifically mandates that M2M SIMs cannot be used for P2P messaging.

#### Alibaba / China SIM Farm Hardware

| Product | Ports | Price | Notes |
|---------|-------|-------|-------|
| **GSM modem pool (32-port)** | 32 | $200-500 | 2G only, bulk SMS sending, comes with SMS caster software |
| **4G LTE modem pool (8-port)** | 8 | $150-400 | 4G capable, AT command control |
| **4G modem pool (32-port)** | 32 | $500-1200 | 4G LTE, bulk SMS gateway |
| **GSM modem pool (16-port)** | 16 | $100-300 | 2G/3G, industrial design |
| **4G modem pool (64-port)** | 64 | $1500-3000 | High-density bulk messaging |
| **SIM bank/server** | Varies | $100-500 | Remote SIM management for modem pools |

**These modem pools are the hardware backbone of SIM farms.** They accept multiple SIM cards and provide AT command interfaces for programmatic SMS/call handling. They are commonly sold on Alibaba with "bulk SMS gateway" marketing.

### 2.2 Countries with No/Weak KYC for SIM Purchase

Based on the Prepaid Data SIM Card Wiki and various research sources, as of 2026:

#### No Registration Required (Truly Anonymous)

| Country | Notes |
|---------|-------|
| **UK** | Prepaid SIMs can be purchased in shops with no ID — although the UK has considered mandatory registration multiple times, it has not implemented it as of 2026 |
| **New Zealand** | No ID required; SIMs available at airports for free |
| **Canada** | Prepaid SIMs from kiosks with no ID |
| **Chile** | Disputed — some sources say no registration, others say it was implemented |
| **Portugal** | No mandatory registration for prepaid SIMs (as of latest data) |
| **Czech Republic** | No mandatory registration (historically; may have changed) |
| **Netherlands** | No registration for prepaid SIMs |
| **Ireland** | No mandatory registration |
| **Sweden** | No mandatory registration for prepaid |
| **Finland** | No mandatory registration |
| **Thailand** | Tourist SIMs at airports with passport scan (weakly enforced) |
| **Vietnam** | Registration required but loosely enforced at small shops |
| **Myanmar** | Minimal registration enforcement |
| **Several African nations** | Variable enforcement; many countries have laws but poor enforcement |

#### Weak Registration / Easily Bypassed

| Country | Notes |
|---------|-------|
| **USA** | No federal registration law; prepaid SIMs available at convenience stores; some states have considered registration |
| **Germany** | Registration required since 2017, but can be done with a hotel address |
| **France** | Registration required since 2016, but enforcement is inconsistent for tourist SIMs |
| **Spain** | Registration required, but Orange Spain tourist packs have minimal checks |
| **Italy** | Registration required since 2009; codice fiscale needed but easily generated |

#### Strict Registration (Hard to Bypass)

| Country | Notes |
|---------|-------|
| **India** | Mandatory Aadhaar-based e-KYC with biometric authentication since Dec 2023; 9 SIM limit per person |
| **China** | Real-name registration strictly enforced; national ID required |
| **Japan** | ID verification required; foreign passports accepted |
| **South Korea** | National ID or alien registration required |
| **Saudi Arabia** | Iqama or national ID required |
| **Australia** | ID verification required for prepaid activation |

### 2.3 Cost per SIM by Source

| Source | Cost per SIM | Includes | Usable for RCS? |
|--------|-------------|----------|----------------|
| **India (Jio BSNL cheapest)** | $0.12-0.60 (blank) + $18-43/year plan | Voice, SMS, data, RCS | ✅ Yes |
| **UK (anonymous prepaid)** | $1-3 (blank) + $10-20/month plan | Voice, SMS, data | ✅ Yes |
| **US (T-Mobile/AT&T prepaid)** | $0-5 (blank) + $15-45/month plan | Voice, SMS, data, RCS | ✅ Yes |
| **Tourist SIM (international)** | $30-60 + $10-30/month | Voice, SMS, roaming data | ⚠️ Partial (roaming may block IMS) |
| **M2M/IoT SIM** | $0.50-5/month | Data only | ❌ No |
| **No-KYC eSIM (Silent.link)** | $1.50/GB (data only) | Data only | ❌ No |
| **Programmable SIM (sysmoISIM-SJA5)** | €8-12 (~$9-14) per card | Self-provisioned (your IMS core) | ⚠️ Only on your own IMS core |
| **Gray market anonymous SIM** | $5-20 | Varies | ⚠️ Unreliable |

### 2.4 India-Specific: Acquiring SIMs Despite 9-Per-Person Limit

India's Dec 2023 SIM rules impose the strictest controls of any major market:

**Current restrictions:**
- Maximum **9 SIMs per person** across all carriers nationwide (6 in J&K, Assam, NE)
- Mandatory **Aadhaar-based e-KYC** with biometric authentication for all activations
- **Bulk connections banned** — no more walking into a store and buying 50 SIMs
- SIM vendors must be verified and registered; ₹50,000 fine for violations
- SIMs unused for 90+ days are auto-deactivated
- M2M SIMs cannot be used for P2P messaging

**Workarounds (with varying legality):**

| Method | Scale | Legality | Feasibility |
|--------|-------|----------|------------|
| **Family/friends SIMs** | 9 per person × N people | ✅ Legal | Practical up to ~50-100 SIMs with extended family |
| **Corporate connections** | 20-50 SIMs per company | ✅ Legal | Requires Pvt Ltd/LLP registration, business justification, individual e-KYC for each SIM |
| **Multiple business entities** | 20-50 per entity × N entities | ⚠️ Gray area | Requires multiple company registrations; carriers may flag unusual patterns |
| **Employee SIMs** | 1 per employee | ✅ Legal | Requires real employees; each gets 9 SIMs |
| **Gray market agents** | Variable | ❌ Illegal | SIM card agents who bypass e-KYC exist but face criminal penalties; SIMs often deactivated within weeks |
| **Tourist SIMs** | N/A | ⚠️ Not for Indian residents | Tourist SIMs available at airports for foreign passport holders; not intended for bulk use |
| **Aadhaar variation** | 9 per Aadhaar | ⚠️ Gray area | Some people have multiple Aadhaar (not supposed to); UIDAI cross-references aggressively |

**Practical advice for India SIM acquisition:**
1. **For testing (10-20 SIMs):** Use 2-3 people's Aadhaar (each gets 9 SIMs); completely legal
2. **For small-scale (50-100 SIMs):** Register a company and apply for corporate connections; 3-4 weeks setup time, legitimate
3. **For medium-scale (100-500 SIMs):** Multiple companies + employee SIMs; complex but feasible
4. **For large-scale (500+ SIMs):** Not realistically achievable in India without carrier cooperation or MVNO agreement

### 2.5 eSIM Bulk Options

**Carrier-provided eSIMs with real phone numbers:**

| Provider | Type | Bulk API | Min Order | Per-eSIM Cost | Has Phone Number |
|----------|------|----------|-----------|--------------|-----------------|
| **WeConnect** | Enterprise eSIM platform | ✅ REST API | 1 | $3-10 | ✅ Yes |
| **Telnyx** | eSIM-as-a-service | ✅ REST API | 1 | $1-5 | ✅ Yes (via API) |
| **eSIM Access** | Wholesale reseller | ✅ REST API | 1 | Varies | ✅ Yes (from carrier) |
| **Airhub** | B2B wholesale | ✅ REST API | 1 | Varies | ✅ Yes |
| **Micro eSIM** | Partner platform | ✅ REST API | 10+ | Contact sales | ✅ Yes |

**These are the most promising path for RCS at scale** — you can programmatically order eSIMs with real phone numbers via API. However:
- Each eSIM must be loaded onto a physical device (phone or eUICC adapter)
- You're limited to the carrier's eSIM profile (cannot customize K/OPc/IMPI)
- Volume pricing varies significantly by carrier and provider
- eSIM profiles come with the carrier's ISIM for IMS registration

### 2.6 Typical SIM Farm Operational Security

Based on research into SIM farm operations (Infrawatch, GBHackers, GoHighLevel, etc.):

**Hardware stack of a typical SIM farm:**
```
┌─────────────────────────────────────────────────┐
│              SIM FARM ARCHITECTURE               │
│                                                   │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐    │
│  │ Modem Pool│  │ Modem Pool│  │ Modem Pool│    │
│  │ (32 SIMs) │  │ (32 SIMs) │  │ (32 SIMs) │    │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘    │
│        │              │              │            │
│  ┌─────┴──────────────┴──────────────┴─────┐     │
│  │        SIM Bank / SIM Server            │     │
│  │   (Remote SIM management, IP access)    │     │
│  └────────────────┬───────────────────────┘     │
│                   │                              │
│  ┌────────────────┴───────────────────────┐     │
│  │     Control Server (SMS caster,        │     │
│  │     API gateway, rotation logic)       │     │
│  └────────────────────────────────────────┘     │
└─────────────────────────────────────────────────┘
```

**Operational security practices observed:**

1. **SIM rotation:** SIMs are cycled through active use to avoid carrier detection. A 32-SIM pool might rotate through SIMs every few hours, keeping each SIM "cold" most of the time.

2. **Geo-distribution:** Large operations (87+ panels in the Infrawatch investigation) distribute SIMs across multiple locations to avoid concentration of traffic from one cell tower.

3. **Multi-carrier:** SIMs from different carriers are mixed to avoid single-carrier rate limiting.

4. **Registration separation:** Each SIM is registered to a different identity (family members, purchased IDs, or gray market agents).

5. **SIM banking:** Remote SIM management via "SIM bank" hardware allows SIMs to be stored in one location while modems are in another, enabling central management of distributed SIM fleets.

6. **Traffic throttling:** Each SIM sends limited messages per day (50-200) to stay under carrier spam detection thresholds.

7. **Auto-recharge:** Automated top-up systems keep SIMs active; unused SIMs are monitored for 90-day deactivation deadlines.

8. **Shared control plane:** The 2025 Infrawatch investigation found a "SIM Farm-as-a-Service" operation with 87+ panels controlled by a single shared control plane — indicating industrial-scale operations with centralized management.

**Anti-detection challenges:**
- Carriers increasingly use AI-based spam detection (Airtel-Google partnership in India)
- SIM farms generate anomalous traffic patterns (all SMS, no voice; all data, no IMSI attach/detach cycles)
- Network-side detection can identify "always-on" SIMs that never move between cell towers
- Temperature/firmware fingerprinting can identify modem pool hardware vs. real phones

---

## Part 3: SS7/Diameter for RCS

### 3.1 How SS7 Attacks Work — Technical Overview

**Signaling System No. 7 (SS7)** is the protocol suite that has powered global telecom signaling since the 1970s. It handles call setup, SMS delivery, roaming, and subscriber management between mobile network operators worldwide.

**The fundamental vulnerability:** SS7 was designed in an era when only trusted telecom operators were on the network. It has **no built-in authentication or authorization** for signaling messages. Any entity that can send SS7 messages to the global signaling network is trusted as a legitimate peer.

**SS7 network architecture:**
```
┌──────────┐     SS7     ┌──────────┐     SS7     ┌──────────┐
│ Home     │◄────────────►│ Visited  │◄────────────►│ Attacker │
│ Network  │   MAP/TCAP   │ Network  │   MAP/TCAP   │ (rogue   │
│ (HSS/HLR)│              │ (VLR/MSC)│              │  operator)│
└──────────┘              └──────────┘              └──────────┘
     │                                                    │
     │  Believes any incoming MAP request is from          │
     │  a legitimate roaming partner                      │
     │                                                    │
     ▼                                                    ▼
  Processes the request                               Gets whatever
  without question                                     was asked for
```

**Key SS7 attack primitives:**

| Attack | SS7 Message | What It Does | Impact |
|--------|------------|-------------|--------|
| **Location Tracking** | `ProvideSubscriberInfo` / `AnyTimeInterrogation` | Query a subscriber's current location (Cell ID, VLR address) | Real-time tracking of any phone number |
| **SMS Interception** | `UpdateLocation` + `SendRoutingInfoForSM` | Redirect SMS delivery to attacker's MSC, then forward to victim | Intercept 2FA codes, RCS verification SMS |
| **Call Interception** | `ProvideRoamingNumber` + routing manipulation | Redirect calls through attacker's network | Listen to calls, modify call setup |
| **DoS** | `InsertSubscriberData` / `DeleteSubscriberData` | Modify subscriber data in HLR | Disable service, change services |
| **Fraud** | `UpdateLocation` (fake roaming) | Register subscriber as roaming in attacker's network | Bypass billing, premium rate fraud |

**SMS Interception Attack Flow (most relevant for RCS):**

```
Step 1: Attacker sends UpdateLocation to victim's HLR
        → HLR believes victim is roaming on attacker's network
        → HLR cancels victim's registration in real VLR
        → Victim loses network service temporarily

Step 2: When SMS arrives for victim (e.g., RCS verification code):
        → SMSC queries HLR for routing info (SendRoutingInfoForSM)
        → HLR returns attacker's MSC address (because "victim is roaming there")
        → SMS is delivered to attacker's MSC
        → Attacker reads the SMS content (verification code)

Step 3: Attacker can optionally forward the SMS to the real victim
        → Victim gets the SMS with a delay
        → Victim is unaware of the interception
```

**This attack is well-documented and has been demonstrated publicly multiple times:**
- **2016:** Karsten Nohl (Security Research Labs) demonstrated SS7 attacks on 60 Minutes (US Congressman Ted Lieu's phone)
- **2017:** Positive Technologies demonstrated stealing Bitcoin by intercepting 2FA SMS via SS7
- **2019:** Multiple banking fraud cases across Europe using SS7 SMS interception
- **2024:** Sophisticated cybercrime group intercepted SMS from thousands of banking customers across Europe, draining millions of euros
- **2025:** SS7 0-day exploit listed on dark web for $5,000

### 3.2 Can SS7 Be Used to Intercept RCS Verification SMS?

**YES** — but with important nuances about what "RCS verification SMS" means.

**RCS registration does NOT use SMS verification codes.** RCS registers via SIP REGISTER on the carrier's IMS core using ISIM/USIM AKA authentication. There is no SMS step in the standard RCS registration process.

However, **SMS-based verification is used in several RCS-adjacent scenarios:**

| Scenario | Is SMS Used? | Can SS7 Intercept? |
|----------|-------------|-------------------|
| **RCS IMS Registration (AKA)** | No — uses ISIM AKA | N/A |
| **Google RCS initial setup** | Sometimes — Google may send an SMS to verify the phone number | ✅ Yes, if SMS is used |
| **Number verification for RCS** | Yes — some RCS implementations verify the phone number via SMS OTP | ✅ Yes |
| **Account recovery for RCS-linked services** | Yes — if RCS is linked to a Google/Samsung account that uses SMS 2FA | ✅ Yes |
| **SIM swap to take over a phone number** | Yes — if the attacker can trigger a SIM swap, they receive all future SMS | ✅ Yes, SS7 can facilitate this |

**The most relevant attack scenario for RCS:**

1. **SS7 SMS interception → Google account takeover → RCS access:**
   - Attacker intercepts Google 2FA SMS via SS7
   - Attacker gains access to the victim's Google account
   - Attacker can now modify RCS settings, change RCS registration, or de-register the victim's RCS

2. **SS7 fake roaming → IMS registration hijack (theoretical):**
   - Attacker uses `UpdateLocation` to register victim as "roaming" on attacker's network
   - If the carrier's IMS core believes the victim is roaming on the attacker's network, the attacker could potentially register a SIP session for the victim's phone number
   - This would give the attacker RCS capability using the victim's phone number
   - **Feasibility:** This depends on whether the IMS core treats SS7 roaming updates as authoritative for SIP registration. In most deployments, IMS registration is separate from SS7 roaming — the IMS core requires direct SIP REGISTER with AKA authentication, not just SS7 location updates. However, the combination of SS7 fake roaming + ePDG access could theoretically work if the attacker also has the victim's SIM credentials.

3. **SS7 SMS interception → SIM swap → full RCS takeover:**
   - Intercept the verification SMS that carriers send for SIM swap authorization
   - Complete the SIM swap with the intercepted code
   - Now the attacker has the victim's phone number on their own SIM
   - Register RCS on the new SIM — full takeover

### 3.3 Can SS7 Be Used to Register a Phone Number for RCS on a Different Device?

**Direct answer: Not directly through SS7 alone.**

SS7 can manipulate roaming state and intercept SMS, but it **cannot directly trigger IMS/SIP registration**. RCS requires:

1. A SIP REGISTER message sent to the carrier's P-CSCF
2. AKA authentication using the SIM's K/OPc (computed by the ISIM/USIM)
3. An IPSec security association with the P-CSCF
4. The carrier's S-CSCF processing the registration

SS7 operates at a different protocol layer (MAP/TCAP over MTP/SCCP) and does not interact with the IMS/SIP layer.

**However, SS7 can INDIRECTLY facilitate RCS registration on a different device through a combination attack:**

**Attack chain: SS7 + SIM credentials → RCS hijack**

```
Step 1: Obtain target phone number (MSISDN)
Step 2: Use SS7 ProvideSubscriberInfo to locate the victim
Step 3: Use SS7 UpdateLocation to fake-roam the victim to attacker's "network"
Step 4: Intercept any SMS the victim receives (including carrier verification codes)
Step 5: With intercepted SMS codes, perform SIM swap at the carrier
Step 6: Now the attacker has a working SIM with the victim's phone number
Step 7: Register RCS on the attacker's device using the new SIM
         (SIP REGISTER via ePDG/VoWiFi path works from anywhere)
Step 8: The victim's RCS is now on the attacker's device
```

**Alternative attack chain: SS7 + social engineering**

```
Step 1: Use SS7 to intercept carrier's SIM swap verification SMS
Step 2: Call the carrier posing as the victim (social engineering)
Step 3: Provide the intercepted verification code
Step 4: Complete SIM swap to attacker-controlled SIM
Step 5: Register RCS on the new SIM
```

**Feasibility assessment:**
- The SS7 + SIM swap attack chain has been demonstrated in banking fraud contexts
- It works because carriers still rely on SMS for verification of SIM swaps
- The attack requires SS7 access (which is the expensive/difficult part) plus a SIM swap (which is the easier part)
- Once the SIM swap is complete, RCS registration is trivial (just activate the SIM on a phone with Google Messages)

### 3.4 Diameter (4G/5G) Security Vulnerabilities

**Diameter** is the signaling protocol used in 4G LTE and 5G networks, replacing SS7 for signaling between network elements. It was designed as a "secure replacement" for SS7, using TCP/SCTP and IP instead of the SS7 transport, with improved authentication mechanisms.

**But Diameter has its own vulnerabilities:**

| Vulnerability | Description | Impact |
|-------------|-------------|--------|
| **Spoofed roaming** | Attacker sends `Update-Location-Request` (Diameter equivalent of SS7 UpdateLocation) posing as a roaming partner | Location tracking, SMS interception (same as SS7) |
| **Subscriber data theft** | `User-Data-Request` can retrieve subscriber profile from HSS | Expose subscriber configuration, service settings |
| **DoS via malformed AVPs** | Malformed Attribute-Value Pairs can crash DRA/HSS elements | Service disruption |
| **No mutual TLS** | Many operators accept inbound Diameter traffic over IPX without mutual TLS or AVP validation | Any IPX-connected entity can send arbitrary Diameter messages |
| **Cross-protocol attacks** | SS7-to-Diameter interworking gateways translate SS7 messages to Diameter — SS7 attacks propagate into 4G/5G networks | SS7 vulnerabilities extend into Diameter networks |
| **5G SBA risks** | 5G Service-Based Architecture uses HTTP/2 (not Diameter) for some interfaces, but Diameter persists for roaming | New attack surface via HTTP/2 APIs |

**Positive Technologies research findings:**
- 100% of tested 4G networks were vulnerable to DoS attacks via Diameter
- 80% were vulnerable to subscriber fraud via spoofed roaming
- 50% were vulnerable to location tracking via Diameter
- These vulnerabilities persist into 5G NSA (Non-Standalone) because 5G NSA uses the 4G EPC with Diameter

**Key difference from SS7:** Diameter runs over IPX (IP eXchange) — a private IP network for telecom signaling. Access to the IPX requires a commercial relationship with an IPX provider (Arelion, BICS, Syniverse, etc.). This is a higher barrier than SS7 access via SS7-over-IP (SIGTRAN) connections, which can be obtained through less rigorous vetting.

**However, the "fake roaming operator" attack is well-documented:**
- P1 Security documented "Fake Roaming Operator" case studies where attackers established apparent roaming relationships
- These fake operators can send Diameter messages to any carrier connected to the same IPX
- The attack requires establishing an IPX connection (commercial relationship with an IPX provider) — typically costs $5,000-20,000/month

### 3.5 Commercial SS7 Exploit Availability

**SS7 exploits and access are available through multiple channels:**

| Channel | Cost | Type | Reliability |
|---------|------|------|-------------|
| **Dark web exploit kits** | $5,000-20,000 | Software exploit package for SS7 access | ⚠️ Many are scams (BleepingComputer: "Most SS7 exploit service providers on dark web are scammers") |
| **SS7 access via roaming partner** | $5,000-20,000/month | Commercial roaming/SIGTRAN connectivity | ✅ Legitimate business; requires company registration |
| **SS7 access via IPX provider** | $5,000-20,000/month | IPX connectivity with signaling | ✅ Legitimate; requires MNO contract |
| **Gray market SS7 service** | $100-500/target | "SS7 as a service" — you provide a phone number, they provide location/SMS | ⚠️ Variable quality; law enforcement risk |
| **SS7 exploit kits (SigPloit)** | Free (open source) | SS7 penetration testing framework | ✅ For authorized testing only; requires SS7 access |
| **Roaming-as-a-Service platforms** | Contact sales | Commercial platforms providing SS7/Diameter connectivity | ✅ Legitimate; Arelion, BICS, Orange Wholesale |

**Practical cost of SS7 access:**

| Access Method | Setup Cost | Monthly Cost | What You Get |
|--------------|-----------|--------------|-------------|
| **Legitimate roaming relationship** | $10,000-50,000 (legal, compliance) | $5,000-20,000 | Full SS7/Diameter access to any carrier's HLR/HSS |
| **Gray market roaming connectivity** | $5,000-10,000 | $2,000-10,000 | SS7 access with less vetting; higher risk of detection |
| **Dark web SS7 exploit** | $5,000-20,000 (one-time) | $0 | Self-hosted SS7 access; many are scams |
| **SS7-as-a-Service** | $0 | $100-500/target | Pay-per-target interception/tracking |
| **Osmocom SS7 stack** | $0 (open source) | Varies | OsmoSTP, OsmoMSC, OsmoHLR — but you still need SS7 connectivity |

**The most realistic path for SS7 access is establishing a legitimate roaming relationship** with a carrier or IPX provider. This requires:
- A registered telecom company (even a small MVNO)
- Commercial contracts with an IPX provider (Arelion, BICS, Syniverse, Tata, etc.)
- GSMA membership or equivalent accreditation
- Network infrastructure (STP, DRA, or SIGTRAN gateway)

**Once SS7 access is obtained**, the SigPloit framework (open source) provides ready-to-use exploit modules for:
- Location tracking (ProvideSubscriberInfo, ATI)
- SMS interception (UpdateLocation + SendRoutingInfoForSM)
- Call interception (ProvideRoamingNumber)
- DoS attacks (InsertSubscriberData, DeleteSubscriberData)

### 3.6 Practical Feasibility and Cost of SS7 Access for RCS Hijacking

**Complete attack cost estimate (SS7 → RCS hijack):**

| Component | Cost | Notes |
|-----------|------|-------|
| SS7/Diameter connectivity | $5,000-20,000/month | Legitimate roaming relationship or IPX access |
| SS7 exploit framework | $0 (SigPloit is open source) | Alternatively, custom development |
| Target phone number | $0 | Publicly available |
| SIM swap facilitation | Varies | May require social engineering or insider access |
| ePDG connectivity for IMS registration | $0 (uses carrier's public ePDG) | See carrier-ims-mapping.md for ePDG addresses |
| SIM card + reader | $20-50 | For ePDG EAP-AKA authentication |

**Total cost for one target:** ~$5,000-20,000/month for SS7 access + minimal hardware

**Total cost for sustained RCS hijacking operation:** ~$5,000-20,000/month (SS7 access) + $50-100/SIM (per hijacked number)

**Feasibility assessment:**

| Factor | Assessment |
|--------|-----------|
| **Technical difficulty** | Medium — requires SS7 expertise but tools exist (SigPloit) |
| **Cost** | High — SS7 access is expensive ($5K-20K/month) |
| **Detection risk** | Medium — carriers are improving SS7 filtering; anomalous signaling patterns may be detected |
| **Success rate** | Variable — depends on target carrier's SS7 filtering and monitoring |
| **Legal risk** | **Very High** — SS7 exploitation is illegal in virtually all jurisdictions; criminal penalties apply |
| **Scalability** | Low — each target requires individual SS7 attack; not easily parallelized |

**Comparison: SS7 vs. SIM swap for RCS hijacking:**

| Factor | SS7 Attack | Social Engineering SIM Swap |
|--------|-----------|---------------------------|
| **Cost** | $5,000-20,000/month | $0 (just phone calls) |
| **Technical skill** | High | Low |
| **Detection risk** | Medium (carrier signaling monitoring) | High (carrier fraud teams) |
| **Success rate** | 60-80% (depending on carrier) | 30-50% (depending on carrier and social engineering skill) |
| **Scalability** | Low (one at a time) | Low (one at a time) |
| **Interception capability** | Full (can intercept any SMS) | None (only gets new SMS after swap) |
| **Stealth** | High (victim may not notice) | Low (victim loses service) |

---

## Summary: Attack Surface Comparison

### Paths to RCS Number Access

| Method | Cost | Scale | Detection Risk | Gets Real Carrier RCS? |
|--------|------|-------|---------------|----------------------|
| **Buy carrier SIMs legally** | $15-45/month per SIM | Limited (9/person in India; unlimited in US/EU with IDs) | None | ✅ Yes |
| **Gray market bulk SIMs** | $1-5/SIM + plan | Medium (50-200 SIMs) | Medium (carrier may detect anomalous usage) | ✅ Yes |
| **Enterprise eSIM API** | $3-10/eSIM | High (1000+ via API) | Low (legitimate enterprise use) | ✅ Yes (carrier profile) |
| **No-KYC eSIM** | $1.50/GB (data only) | High | Low | ❌ No (data only, no phone number) |
| **Programmable SIM (own IMS)** | €8-12/card | High (1000+ cards) | None (your own network) | ❌ No (your IMS, not carrier) |
| **VirtualSIM (own IMS)** | $0 | Unlimited | None | ❌ No (your IMS, not carrier) |
| **SS7 SMS interception** | $5K-20K/month | Low (one target at a time) | High | ⚠️ Indirect (intercepts verification codes) |
| **SS7 + SIM swap** | $5K-20K/month + social engineering | Low (one target at a time) | Very High | ✅ Yes (takes over victim's number) |
| **Diameter attack** | $5K-20K/month | Low | High | ⚠️ Similar to SS7 but for 4G/5G |
| **eUICC test CI (own profile)** | €10-15/card + reader | Low (only on test eUICCs) | None | ❌ No (test eUICCs don't work on carrier networks) |
| **eUICC compromised cert** | Research-level | Unknown | Very High | ⚠️ Theoretical — can decrypt carrier profiles |

### Key Findings

1. **eUICC/eSIM is NOT the best path for carrier RCS at scale.** While you CAN create custom ISIM eSIM profiles (UPP with ISIM application), they only work on test eUICCs that accept the test CI — not on consumer phones. To load custom profiles onto consumer phone eUICCs, you'd need GSMA production certificates, which require being an MNO/MVNO.

2. **Gray market SIMs remain the most practical path for carrier RCS at scale.** Legal bulk SIM acquisition in India is severely constrained (9-SIM limit), but in the US/UK/EU, prepaid SIMs are still readily available with minimal/no KYC. Enterprise eSIM APIs (WeConnect, Telnyx, eSIM Access) provide the most scalable path for legitimate operations.

3. **No-KYC eSIMs are useless for RCS** — they are data-only with no phone number and no IMS/ISIM capability.

4. **SS7 attacks can intercept SMS verification codes** but cannot directly register RCS. The attack chain requires SS7 access + SIM swap + physical SIM to achieve full RCS takeover. This is expensive ($5K-20K/month), targeted (not scalable), and carries severe legal risk.

5. **Diameter has similar vulnerabilities to SS7** but is harder to access (requires IPX connectivity). Cross-protocol attacks (SS7-to-Diameter gateways) extend SS7 vulnerabilities into 4G/5G networks.

6. **The Security Explorations eUICC hack (July 2025)** fundamentally challenges the eSIM trust model — a single compromised eUICC certificate can decrypt any MNO's eSIM profiles, exposing K/OPc/AMF and enabling potential IMS AKA authentication with stolen credentials. However, this requires physical access to a vulnerable Kigen eUICC card and is not yet a scalable attack.

7. **For self-hosted RCS with your own IMS core**, the cheapest and most scalable approach remains programmable SIMs (sysmoISIM-SJA5, ~€8-12 each) or VirtualSIMs ($0). This gives you full control over K/OPc/IMPI/IMPU but does NOT connect you to carrier RCS — only your own federated IMS core.

---

## References

### eUICC/eSIM
- GSMA SGP.22 v2.7 — Consumer eSIM Remote SIM Provisioning specification
- Trusted Connectivity Alliance — eUICC Profile Package: Interoperable Format Technical Specification
- osmo-smdpp documentation: https://euicc-manual.osmocom.org/docs/rsp/sm-dp-plus/
- pySim eSIM libraries: https://downloads.osmocom.org/docs/pysim/master/html/library-esim.html
- sysmoEUICC1 user manual: https://sysmocom.de/manuals/sysmoeuicc-manual.pdf
- Nick vs Networking — "Loading eSIMs onto Physical Cards": https://nickvsnetworking.com/loading-esims-onto-physical-cards/
- Security Explorations — eSIM security: https://security-explorations.com/esim-security.html
- OpenRSP: https://github.com/Blockchain-Powered-eSIM/OpenRSP
- MiniLPA: https://github.com/EsimMoe/MiniLPA
- SIMalliance LTE UICC Profile for MNOs
- GSMA NG.102 — IMS Profile for Converged IP Communications

### Gray Market SIMs
- Prepaid Data SIM Card Wiki — Registration Policies Per Country: https://prepaid-data-sim-card.fandom.com/wiki/Registration_Policies_Per_Country
- PhoneTravelWiz — SIM Card Registration Laws: https://www.phonetravelwiz.com/phone-travel-options/sim-card-registration/
- Silent.link: https://silent.link/
- Simsup: https://kycnot.me/service/simsup
- Infrawatch — "Inside the Mobile Farm": https://infrawatch.com/blog/inside-the-mobile-farm-the-oem-stack-powering-us/
- GBHackers — "SIM Farm-as-a-Service Operation": https://gbhackers.com/sim-farm-as-a-service-operation-spanning-87-panels-in-1...
- Alibaba — GSM modem pool products: https://www.alibaba.com/showroom/gsm-modem-pool.html
- India DoT — New SIM card rules Dec 2023
- WeConnect enterprise eSIM: https://weconnect.one/enterprise-esim-management/
- Telnyx eSIM-as-a-service: https://telnyx.com/products/esim

### SS7/Diameter
- P1 Security — "Understanding SS7 Attacks": https://www.p1sec.com/blog/understanding-ss7-attacks-vulnerabilities-impacts-...
- P1 Security — "Diameter Protocol Vulnerabilities": https://www.p1sec.com/blog/understanding-the-vulnerabilities-of-the-diameter-...
- P1 Security — "SS7, Diameter, GTP, IMS & 5G Vulnerabilities": https://www.p1sec.com/blog/legacy-and-modern-protocols-at-risk-ss7-diameter-g...
- Positive Technologies — "Stealthy SS7 Attacks" (BlackHat Asia 2020)
- CyberPress — "SS7 0-Day Exploit Hits Dark Web Market with $5,000 Price Tag": https://cyberpress.org/ss7-0-day-exploit-hits/
- BleepingComputer — "Most SS7 exploit service providers on dark web are scammers": https://www.bleepingcomputer.com/news/security/most-ss7-exploit-service-provi...
- Immersive Labs — "Exploiting SS7 to intercept text messages": https://www.immersivelabs.com/resources/blog/intercepting-text-messages
- WIRED — "The RCS Texting Protocol Is Way Too Easy to Hack": https://www.wired.com/story/rcs-texting-security/
- GSMA — "Securing a Legacy Protocol in a Modern Threat Landscape": https://www.gsma.com/solutions-and-impact/technologies/security/t-isac-blog/s...
- SigPloit SS7 framework: https://github.com/SigPloit/SigPloit
- Arelion (Telia Carrier) — Roaming Signaling: https://www.arelion.com/products-and-services/mobile-data-and-iot/roaming-sig...
- P1 Security — "Fake Roaming Operator Case Studies": https://www.p1sec.com/blog/fake-roaming-operator-case-studies
- Aalto University — "Security Analysis of the Consumer RSP Protocol" (2024)
- CSPS Protocol — "How to connect to SS7": https://www.cspsprotocol.com/connect-on-ss7-or-sigtran/

---

*Report generated 2026-05-16 from 32 web searches, 3 URL analyses, and 3 existing internal research documents (sim-key-extraction-cloning.md, india-sim-rcs-landscape.md, carrier-ims-mapping.md).*
