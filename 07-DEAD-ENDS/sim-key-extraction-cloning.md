# SIM Key Extraction & Cloning: Comprehensive Research Report

## Executive Summary

This report provides an in-depth analysis of the feasibility of extracting IMS authentication keys (K, OP/OPc, AMF) from SIM cards, SIM cloning techniques for ISIM duplication, and the implications for building headless RCS clients that authenticate against carrier IMS cores. The central finding is straightforward: **K and OP/OPc cannot be extracted from commercial carrier SIMs**, but they are fully accessible on programmable SIMs (sysmoISIM-SJA2/SJA5). This creates two distinct operational paths — one requiring a physical SIM card at all times (carrier SIM path), and one enabling pure software AKA (programmable SIM path with known keys).

---

## 1. Can K/OP Be Extractacted from a Real Carrier SIM?

### Answer: NO from commercial SIMs, YES from programmable SIMs

#### 1.1 Commercial Carrier SIMs — Keys Are Locked

The secret key **K** (128-bit) and **OP/OPc** (128-bit) are the foundational secrets of the entire UMTS/LTE/5G authentication architecture. They are written into the SIM card's secure element during manufacturing at the card vendor's personalization center, and they **never leave the SIM card** under normal operation.

**Why K cannot be extracted from carrier SIMs:**

1. **Hardware secure element**: Commercial SIM cards use certified smart card chips (EAL4+ or EAL5+ certified per Common Criteria) that implement hardware-level access controls. The K key is stored in a secure memory region that is not readable via any APDU command — there is no "read K" command in the 3GPP or ETSI specifications.

2. **No standard interface**: TS 31.102 (USIM), TS 31.103 (ISIM), and TS 102 226 define the file structure and commands on the UICC. None of these specifications provide a command or file that returns the K value. The AUTHENTICATE command (INS=0x88) *uses* K internally to compute RES/CK/IK, but never *reveals* K.

3. **ADM-protected files**: Even the proprietary files on commercial SIMs that might contain key material are protected by the ADM (Administrative) PIN. The ADM key is known only to the card issuer (the carrier or their card vendor). Brute-forcing the ADM is impractical — it typically has a limited number of attempts (5-10) before the card permanently locks.

4. **GlobalPlatform card management**: Modern SIMs use GlobalPlatform secure channel protocols (SCP01/SCP02/SCP03) for over-the-air management. Even with physical access, loading or reading applets requires authentication with keys that only the card issuer possesses.

5. **Transport key distribution**: As noted by Nick vs Networking, SIM vendors often don't even send the raw Ki values to the carrier — they send encrypted "transport keys" that can only be decrypted by the carrier's HSS. This means even the carrier's ordering department doesn't see the raw K values in many cases.

**What you CAN read from a carrier SIM:**
- IMSI (EF.IMSI, FID=6F07)
- ICCID (EF.ICCID, FID=2FE2)
- MSISDN (EF.MSISDN, FID=6F40, if present)
- ISIM files: IMPI (EF.IMPI), IMPU (EF.IMPU), DOMAIN (EF.DOMAIN), P-CSCF (EF.P-CSCF)
- Authentication *results* (RES, CK, IK, Kc) via the AUTHENTICATE command — but only when presented with a valid RAND+AUTN challenge from the network
- Phonebook, SMS, etc.

**What you CANNOT read from a carrier SIM:**
- K (secret key) — never exposed by any command
- OP/OPc (operator key) — never exposed by any command
- AMF (Authentication Management Field) — embedded in AUTN computation, not readable directly
- SQN (Sequence Number) — can be inferred from AUTS re-sync behavior, but the raw value is internal
- ADM PIN — not readable, must be known or brute-forced

#### 1.2 Programmable SIMs — Keys Are Readable and Writable

**sysmoISIM-SJA2** and **sysmoISIM-SJA5** (from sysmocom) are the primary programmable SIM cards that expose K and OP/OPc through proprietary files:

- **EF.SIM_AUTH_KEY** (FID=6F20 under DF.SYSTEM) — Contains K + OP/OPc + algorithm configuration byte
- **EF.USIM_AUTH_KEY / EF.ISIM_AUTH_KEY** (FID=AF20 under ADF.USIM/ADF.ISIM) — Per-application key storage
- **EF.MILENAGE_CFG** (FID=6F21) — Milenage algorithm configuration (r1-r5, c1-c5 constants)

These files are readable and writable via standard APDU commands after verifying PIN1 (no ADM required — the card ships with PIN1= Disable, or the default PIN1/PUK is provided with the card purchase).

**EF.ISIM_AUTH_KEY structure for MILENAGE:**
```
Byte 0 (CfgByte):
  Bit 3: use_opc_instead_of_op (0=OP, 1=OPc)
  Bits 2-0: algorithm (4=MILENAGE, 5=SHA1-AKA, 6=TUAK, 15=XOR)
Bytes 1-16: K (16 bytes)
Bytes 17-32: OP or OPc (16 bytes)
```

This means on a sysmoISIM card, you can:
- **Read** the existing K and OP/OPc values
- **Write** new K and OP/OPc values
- **Change** the algorithm (MILENAGE, TUAK, SHA1-AKA, XOR)
- **Configure** Milenage parameters (r1-r5, c1-c5)
- **Reset** the SQN counter

**Critical distinction**: On a programmable SIM, you are the card issuer. You provision your own K and OP/OPc. You are not extracting anyone else's keys — you are writing your own keys and then using them.

---

## 2. SIM Cloning Feasibility

### 2.1 Cloning a Carrier SIM's ISIM onto a Blank Card

**Short answer: Not feasible without the carrier's K and OP/OPc.**

To "clone" a carrier ISIM, you would need to:
1. Extract K from the carrier SIM → **Impossible** (see Section 1.1)
2. Extract OP/OPc from the carrier SIM → **Impossible** (see Section 1.1)
3. Write the extracted K and OP/OPc to a blank programmable SIM → **Easy** (if you had the values)

Since steps 1 and 2 are impossible, the cloning path is blocked. You cannot create a functional duplicate of a carrier SIM without the carrier's cooperation (or a side-channel attack — see Section 5).

### 2.2 What "SIM Cloning" Actually Means in Practice

The term "SIM cloning" has multiple meanings:

| Cloning Type | Feasibility | Description |
|-------------|-------------|-------------|
| **2G COMP128-1 Ki extraction** | Feasible (but COMP128-1 is obsolete) | Old 2G SIMs using COMP128-1 algorithm could have Ki extracted via partitioning attacks. Modern SIMs use COMP128-2/3 or MILENAGE, which are resistant. |
| **2G COMP128-2/3 Ki extraction** | **Not feasible** | COMP128-2 and COMP128-3 algorithms are cryptographically stronger. No known practical attacks extract Ki. |
| **3G/4G/5G MILENAGE K extraction** | **Not feasible** | MILENAGE is based on AES-128. There is no known mathematical attack to recover K from observing RAND/RES/CK/IK pairs. |
| **Physical cloning** (reading all non-secret files and writing to a new card) | Partially feasible | You can copy IMSI, ICCID, ISIM files (IMPI, IMPU, DOMAIN, P-CSCF), but without K/OP, the cloned card cannot authenticate. It's a "dead clone." |
| **Forensic cloning** (MOBILedit, Cellebrite) | Different purpose | Forensic tools create copies of the *data* on a SIM (contacts, SMS, call logs) for evidence preservation. They do NOT clone the cryptographic keys. |
| **Carrier multi-SIM** | Legitimate | Many carriers offer legitimate multi-SIM (twin SIM, multi-SIM) services where two physical SIMs share the same IMSI and keys. This is carrier-authorized. |

### 2.3 Side-Channel Attack Path for Key Extraction

Side-channel attacks against SIM cards are a **theoretical but impractical** path for key extraction:

**COMP128-1 Partitioning Attack (historical):**
- Published in 2002 by Rao et al. ("Partitioning Attacks: Or How to Rapidly Clone Some GSM Cards")
- Exploited information leakage in the COMP128-1 algorithm's lookup tables
- Required ~150,000 chosen RAND challenges sent to the SIM card
- Could extract Ki in a few hours
- **Only works on COMP128-1 (2G only, deprecated since ~2004)**
- Modern SIMs do NOT use COMP128-1

**Power Analysis / EM Attacks:**
- Differential Power Analysis (DPA) and Electro-Magnetic (EM) analysis can theoretically extract AES keys from smart card chips
- A 2021 research paper from Shanghai Jiao Tong University demonstrated side-channel attacks on 3G/4G SIM cards
- Requires specialized equipment: oscilloscopes, EM probes, chip decapping tools
- Requires physical modification of the SIM card (removing epoxy, exposing the die)
- Each card requires individual analysis — not scalable
- **Not practical for production use — academic threat only**

**Fault Injection Attacks:**
- Voltage glitching or laser fault injection can bypass security checks
- Extremely hardware-intensive, low success rate, destroys cards
- Not viable for key extraction at scale

### 2.4 Rainbow Table Attack Feasibility

**Rainbow tables are NOT applicable to SIM K/OP extraction** for several reasons:

1. **MILENAGE is not a simple hash**: The MILENAGE algorithm set (f1-f5) uses AES-128 as a building block with OPc-dependent transformations. It's not a simple `hash(K || RAND)` — it involves multiple AES encryptions with different constants and OPc-derived sub-keys.

2. **128-bit key space**: K is 128 bits. The key space is 2^128 ≈ 3.4×10^38. Even with massive computing resources, building rainbow tables for this space is infeasible.

3. **Unknown OPc**: Even if you could observe many (RAND, RES, CK, IK) tuples, you don't know the OPc value. OPc acts as a second 128-bit secret, effectively making the combined key space 2^256.

4. **SQN dependence**: The MAC-A (in AUTN) depends on the SQN sequence number, which changes with each authentication. This adds another variable.

5. **Practical attack alternative**: The only practical "attack" on K is observing enough RAND/RES pairs to attempt a brute-force search, but 2^128 is beyond any feasible computation.

---

## 3. What Happens If Two Devices Register with Same IMS Credentials Simultaneously?

### 3.1 With a Carrier IMS Core

If two devices somehow had identical ISIM credentials (same K, OP/OPc, IMPI, IMPU) and both attempted to register with the carrier's IMS core:

1. **SQN desynchronization**: The SIM card's SQN counter is designed to only accept authentication challenges with a SQN within a small window. If Device A authenticates (incrementing the HSS's SQN), then Device B's next authentication attempt may fail because its SQN is now stale. This would trigger AUTS re-synchronization.

2. **Network detection**: The carrier's S-CSCF and HSS would see two devices registering with the same IMPI from different IP addresses / Contact headers. This is anomalous and may trigger:
   - Registration rejection (some carriers enforce single-registration policy)
   - Security alerts
   - Account suspension

3. **Race conditions**: Even if both devices could authenticate, they would compete for the same SIP registration binding. The last REGISTER wins — the S-CSCF replaces the previous Contact with the new one. The "losing" device stops receiving incoming SIP messages.

4. **IPSec complications**: If IPSec is required (Security-Client/Server negotiation), each registration establishes separate Security Associations with different SPIs and port pairs. The P-CSCF would need to maintain multiple SAs for the same IMPI, which may not be supported.

5. **Carrier multi-SIM services**: Legitimate multi-SIM services (e.g., Vodafone OneNumber, T-Mobile DIGITS) solve this by using different IMSIs or by routing through the carrier's application server. They do NOT use identical K/OPc on multiple physical SIMs.

### 3.2 With Your Own IMS Core (Open5GS, Kamailio, etc.)

If you provision your own IMS core with your own K/OPc (on programmable SIMs), you have full control:

1. **Multiple registrations**: Your S-CSCF can be configured to accept multiple concurrent registrations for the same IMPI.
2. **Forking**: SIP requests can be forked to all registered Contacts.
3. **No SQN issues**: Your HSS controls the SQN, so you can reset it or manage it per-device.
4. **No carrier detection**: It's your network — you set the rules.

### 3.3 Practical Implication for Headless RCS

**For carrier IMS**: You cannot have multiple headless clients authenticating with the same carrier SIM credentials simultaneously. Each SIM card is a singleton — one physical card, one registration at a time. For a phone farm, you need one SIM per slot.

**For your own IMS core**: You can provision multiple programmable SIMs with the same or different credentials, and register them all simultaneously.

---

## 4. Blank Programmable SIM Card Sources and Pricing

### 4.1 sysmocom (Primary/Recommended Source)

| Product | Apps | 3GPP Release | Unit Price | Bulk Pricing | Notes |
|---------|------|--------------|-----------|-------------|-------|
| **sysmoISIM-SJA2** | SIM+USIM+ISIM | Rel-8+ | ~€7-10/card | 10-pack: ~€60-80 | **Primary choice** — full ISIM support, well-documented, pySim-native |
| **sysmoISIM-SJA5** | SIM+USIM+ISIM+HPSIM | Rel-17 | ~€8-12/card | 10-pack: ~€70-90 | Successor — adds 5G/HPSIM/TUAK, recommended for new deployments |
| sysmoUSIM-SJS1 | SIM+USIM | Rel-8 | ~€5-7/card | 10-pack: ~€40-60 | No ISIM — cannot do IMS AKA directly |
| sysmoEUICC1 | eUICC | SGP.22 | Varies | — | eSIM, different usage pattern |

**Purchase URLs:**
- Shop: https://shop.sysmocom.de/SIM/Cards/
- SJA5 product page: https://sysmocom.de/products/sim/sysmoisim-sja5/index.html
- SJA2 product page: https://www.sysmocom.de/products/sim/sysmousim/index.html

**Key advantages of sysmocom cards:**
- Ship with ADM keys (you have full administrative access)
- pySim has native, complete support for all proprietary files
- Well-documented ATR patterns for auto-detection
- Support MILENAGE, TUAK, SHA1-AKA, and XOR algorithms
- ISIM application is fully provisioned with writable EF.ISIM_AUTH_KEY, EF.ISIM_SQN

### 4.2 Alternative Sources

| Source | Product | ISIM Support | Price | Notes |
|--------|---------|-------------|-------|-------|
| **HKCARD Electronics** | Blank writable USIM/ISIM 4G/5G | Claimed | ~$3-8/card (bulk) | Chinese manufacturer, claims ISIM support, compatibility with pySim varies |
| **XCRFID** (Amazon) | Writable Programmable Blank LTE SIM | Unclear | ~$15-25/5-pack | Amazon availability, ISIM support uncertain, may need custom provisioning |
| **Gialer** (Amazon) | Writable Programmable 4G LTE | USIM only | ~$25-35/30-pack | Very cheap, likely USIM-only (no ISIM), algorithm support unknown |
| **Bladox** (historical) | Bladox SIM cards | No ISIM | N/A | Discontinued — Bladox was known for 2G SIM tools (SIM Applications Toolkit). Not relevant for 3G/4G/5G ISIM. |

**Warning about non-sysmocom cards**: Many cheap "programmable SIM cards" on Amazon/AliExpress are:
- USIM-only (no ISIM application)
- Using proprietary programming tools (not pySim-compatible)
- Based on older chipsets without MILENAGE/TUAK support
- May require Windows-only software
- Documentation is often poor or nonexistent

**Recommendation**: For any IMS/ISIM work, use sysmoISIM-SJA2 or SJA5. The cost difference is minimal, and the compatibility with pySim is guaranteed.

### 4.3 Multi-SIM Readers

| Hardware | Slots | Price | Notes |
|----------|-------|-------|-------|
| **sysmoOCTSIM** | 8 | ~€200 | Osmocom's official multi-SIM reader, designed for phone farms |
| **sysmoOCTSIM-T1** | 8 | ~€220 | Improved thermal design |
| Omnikey 3121 | 1 | ~$20-40 | Standard single-slot CCID reader |
| SCM SCR3310 | 1 | ~$20-35 | Another standard single-slot reader |
| Springcard | 2-4 | ~$50-100 | Multi-slot alternative |

---

## 5. The Full Attack Surface: Software AKA Without sim-rest-server

### 5.1 If You KNOW K+OP+AMF, You Don't Need sim-rest-server

This is the critical insight for programmable SIM deployments:

**Current architecture (carrier SIM):**
```
SIP 401 → extract RAND/AUTN → POST to sim-rest-server → SIM card computes RES/CK/IK → compute AKA-Digest → SIP REGISTER
```

**Simplified architecture (programmable SIM with known K/OP):**
```
SIP 401 → extract RAND/AUTN → software MILENAGE(K, OPc, RAND, SQN, AMF) → RES/CK/IK → compute AKA-Digest → SIP REGISTER
```

When you provision your own programmable SIM, you choose the K, OP/OPc, and AMF values. You know them. Therefore, you can compute MILENAGE f1-f5 entirely in software — no SIM card, no PC/SC reader, no sim-rest-server required.

This eliminates:
- Physical SIM card dependency
- PC/SC reader hardware
- sim-rest-server process
- Connection latency per authentication
- Single-threaded card access bottleneck
- SQN synchronization issues (you control SQN in software)
- PIN verification complexity

### 5.2 MILENAGE Algorithm Implementation

The MILENAGE algorithm set (3GPP TS 35.206) defines five functions:

| Function | Purpose | Output |
|----------|---------|--------|
| f1 | Message authentication function | MAC-A (8 bytes) — used to compute AUTN |
| f1* | Synchronisation message authentication function | MAC-S (8 bytes) — used to compute AUTS |
| f2 | Random challenge response function | RES (4-16 bytes) — response to network challenge |
| f3 | Cipher key derivation function | CK (16 bytes) |
| f4 | Integrity key derivation function | IK (16 bytes) |
| f5 | Anonymity key derivation function | AK (6 bytes) — used to conceal SQN in AUTN |
| f5* | Synchronisation anonymity key derivation | AK (6 bytes) — for re-synchronization |

**All functions are built on AES-128** with the subscriber's K and OPc as keys.

#### 5.2.1 Python Implementations

1. **CryptoMobile** (mitshell/CryptoMobile on GitHub) — Pure Python implementation of MILENAGE with C extensions for performance:
   ```python
   from CryptoMobile.Milenage import Milenage
   m = Milenage(K=bytes.fromhex('...'), OPc=bytes.fromhex('...'))
   res, ck, ik, ak = m.f2345(rand)
   mac_a = m.f1(rand, sqn, amf)
   ```

2. **Magma** (Facebook/Magma) — Python implementation in `magma/lte/gateway/python/magma/subscriberdb/crypto/milenage.py`:
   - Production-grade, used in Magma's HSS
   - Implements all f1-f5 functions
   - Pure Python using PyCryptodome

3. **pySim** itself — Has MILENAGE implementation in `pySim/crypto.py`:
   - Used internally for test-mode authentication
   - Can be imported and used standalone

#### 5.2.2 Go Implementations

1. **wmnsk/milenage** (GitHub) — Complete Go implementation:
   ```go
   import "github.com/wmnsk/milenage"
   
   m, _ := milenage.New(opc, k)
   res, ck, ik, ak, _ := m.F2345(rand)
   macA, _ := m.F1(rand, sqn, amf)
   ```

2. **free5gc/milenage** — Part of the free5GC project:
   - Used in free5GC's UDM/AUSF
   - Production-grade

3. **emakeev/milenage** — Another Go implementation

#### 5.2.3 C Implementations

1. **Osmocom libosmocore** — C implementation used in Osmocom's HLR/HSS
2. **free5GC C library** — C-based MILENAGE for performance
3. **3GPP TS 35.206 reference code** — ETSI/3GPP publishes reference C code for MILENAGE test vectors

### 5.3 TUAK Algorithm (Alternative to MILENAGE)

TUAK is defined in 3GPP TS 35.222 and uses Keccak (SHA-3) as its building block instead of AES. It's supported on sysmoISIM-SJA5 cards.

**TUAK differences from MILENAGE:**
- Uses Keccak-p[1600] permutation instead of AES-128
- Supports 256-bit keys (K and OP/OPc can be 32 bytes)
- Configurable output sizes for RES, CK, IK
- Configurable number of Keccak iterations

**Implementations:**
- Python: `pySim` has TUAK support for SJA5 card programming
- Go: No widely-used standalone Go TUAK implementation found
- C: 3GPP TS 35.222 reference code available

**For our purposes, MILENAGE is sufficient** — it's the default algorithm on both SJA2 and SJA5, all carrier SIMs support it, and there are mature implementations in every language.

### 5.4 Pure Software AKA — "Virtual SIM"

Given that MILENAGE is implementable in pure software with known K/OPc, the concept of a "virtual SIM" is straightforward:

```python
class VirtualSIM:
    """Pure software SIM that computes AKA responses without any physical card."""
    
    def __init__(self, k_hex: str, opc_hex: str, amf_hex: str = "8000", sqn: int = 1):
        self.k = bytes.fromhex(k_hex)
        self.opc = bytes.fromhex(opc_hex)
        self.amf = bytes.fromhex(amf_hex)
        self.sqn = sqn
    
    def authenticate(self, rand_hex: str, autn_hex: str) -> dict:
        """
        Given RAND and AUTN from the network, compute RES, CK, IK.
        If MAC verification fails, return error. If SQN is out of sync, return AUTS.
        """
        from CryptoMobile.Milenage import Milenage
        rand = bytes.fromhex(rand_hex)
        autn = bytes.fromhex(autn_hex)
        
        m = Milenage(self.k, self.opc)
        
        # Compute f5 (anonymity key) to recover SQN from AUTN
        _, _, _, ak = m.f2345(rand)
        sqn_ms = bytes(a ^ b for a, b in zip(autn[:6], ak))
        
        # Verify MAC
        mac_a = m.f1(rand, sqn_ms, self.amf)
        if mac_a != autn[8:16]:
            return {"error": "MAC verification failed"}
        
        # Check SQN freshness
        sqn_int = int.from_bytes(sqn_ms, 'big')
        if sqn_int < self.sqn:  # Simplified check
            # SQN out of sync — compute AUTS
            mac_s = m.f1star(rand, self.sqn.to_bytes(6, 'big'), self.amf)
            _, _, _, ak_star = m.f5star(rand)
            sqn_ms_star = bytes(a ^ b for a, b in zip(self.sqn.to_bytes(6, 'big'), ak_star))
            auts = sqn_ms_star + mac_s
            return {"synchronisation_failure": {"auts": auts.hex()}}
        
        # Compute RES, CK, IK
        res, ck, ik, _ = m.f2345(rand)
        self.sqn = sqn_int + 1  # Increment SQN
        
        return {
            "successful_3g_authentication": {
                "res": res.hex(),
                "ck": ck.hex(),
                "ik": ik.hex(),
            }
        }
```

This replaces the entire `sim-rest-server` + PC/SC reader + physical SIM card stack with a single Python class. **The VirtualSIM is functionally equivalent to a physical ISIM** for AKA authentication purposes.

**Advantages of virtual SIM:**
- No hardware dependency
- No per-request latency (MILENAGE computation takes microseconds, vs. 100-500ms for SIM card APDU)
- Scales horizontally (run thousands of virtual SIMs on one server)
- No SQN sync issues (SQN is in software, can be persisted in a database)
- No card reader failures, no card wear, no PIN issues

**Disadvantages of virtual SIM:**
- K and OPc are in software memory — must protect against memory dumps, core dumps, and unauthorized access
- Not compliant with carrier security policies (carriers expect keys on secure elements)
- Only works on IMS cores you control (or that trust your K/OPc provisioning)

---

## 6. Practical Path: Buy Programmable SIMs, Provision Your Own IMS Core, Federate

### 6.1 The Self-Hosted IMS Core Architecture

The most practical path for headless RCS with ISIM authentication is:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SELF-HOSTED IMS + RCS CORE                   │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐          │
│  │ Open5GS HSS  │  │ Kamailio     │  │ Open5GS SMF/  │          │
│  │ (subscriber  │  │ (P/I/S-CSCF) │  │ UPF (data)    │          │
│  │  database    │  │ + IMS Registrar│ │               │          │
│  │  K, OPc, SQN)│  │              │  │               │          │
│  └──────┬───────┘  └──────┬───────┘  └───────────────┘          │
│         │                 │                                      │
│         │    ┌────────────┴──────────────┐                       │
│         │    │  RCS Application Server   │                       │
│         │    │  (Kamailio + msrp-relay)  │                       │
│         │    └───────────────────────────┘                       │
│         │                                                         │
└─────────┼─────────────────────────────────────────────────────────┘
          │
          │  Federation (SIP peering, IPX, or direct SIP trunk)
          │
┌─────────┴─────────────────────────────────────────────────────────┐
│                    CARRIER IMS CORE                               │
│  (AT&T, Verizon, Vodafone, etc.)                                  │
│  - Carrier's HSS has ITS K/OPc for carrier-issued SIMs           │
│  - Carrier's RCS AS (may be Jibe-hosted)                         │
└───────────────────────────────────────────────────────────────────┘
```

**Step-by-step deployment:**

1. **Buy sysmoISIM-SJA5 cards** (10-pack from sysmocom, ~€70-90)
2. **Buy sysmoOCTSIM** (8-slot reader, ~€200) or individual USB readers
3. **Install pySim** and provision each card with:
   - Your chosen IMSI (use a test MCC/MNC like 001/01 or 901/70)
   - Your chosen K and OPc (generate strong random values)
   - ISIM files: IMPI, IMPU, DOMAIN, P-CSCF
   - Milenage algorithm configuration
4. **Deploy Open5GS** (or srsRAN, or Magma) as your 4G/5G core with the HSS configured with the same K/OPc values
5. **Deploy Kamailio** as your P/I/S-CSCF and S-CSCF for IMS registration
6. **Deploy an RCS Application Server** (e.g., Kamailio with rls/presence modules, or a custom RCS AS)
7. **Test IMS registration** from a headless client using either:
   - Physical SIM + sim-rest-server path, or
   - VirtualSIM software path (since you know K/OPc)
8. **Federation**: Configure SIP peering with carrier networks so your RCS users can exchange messages with carrier RCS users

### 6.2 pySim-prog: Bulk Provisioning

`pySim-prog.py` is the bulk provisioning tool for sysmoISIM cards:

```bash
# Provision a single card
pySim-prog.py -p 0 \
  --type sysmoISIM-SJA5 \
  --imsi 001010000000001 \
  --ki 841EAD87BC9D974ECA1C167409357601 \
  --opc 3211CACDD64F51C3FD3013ECD9A582A0 \
  --isim-imsi 001010000000001 \
  --isim-domain ims.mnc001.mcc001.3gppnetwork.org \
  --isim-psk 841EAD87BC9D974ECA1C167409357601 \
  --isim-popc 3211CACDD64F51C3FD3013ECD9A582A0 \
  --milenage

# Bulk provisioning with CSV input
pySim-prog.py -p 0 --batch-csv subscribers.csv --type sysmoISIM-SJA5

# CSV format:
# imsi,ki,opc,iccid,isim-domain
# 001010000000001,<K_hex>,<OPc_hex>,8900100000000000001,ims.mnc001.mcc001.3gppnetwork.org
```

For the sysmoISIM-SJA5 specifically, the `sysmo-isim-tool.sja5.py` provides SJA5-specific operations:
```bash
# Read current ISIM auth key
sysmo-isim-tool.sja5.py -p 0 read-isim-auth-key

# Write ISIM auth key
sysmo-isim-tool.sja5.py -p 0 write-isim-auth-key \
  --key 841EAD87BC9D974ECA1C167409357601 \
  --opc 3211CACDD64F51C3FD3013ECD9A582A0 \
  --algorithm milenage
```

### 6.3 Can We Use Programmable SIMs on a Carrier's Network?

**No** — a programmable SIM provisioned with your own K/OPc will not work on a carrier's network because:

1. The carrier's HSS does not have your K/OPc values
2. The carrier's MME/HSS will reject the SIM's IMSI as unknown
3. Even with a valid IMSI format, the carrier's AuC cannot generate matching authentication vectors

**Exception**: If you are an MVNO or have a commercial relationship with a carrier, they may:
- Give you a range of IMSIs and their associated K/OPc values for your own SIM provisioning
- This is how MVNOs operate — they get K/OPc from the host MNO
- In this case, you CAN provision programmable SIMs with carrier-provided K/OPc and use them on the carrier's network

---

## 7. Gray Area: Extracting K/OP from a Carrier SIM You Legitimately Own

### 7.1 Legal Analysis

**Is it legal to extract K/OP from your own SIM card?**

- In most jurisdictions, you own the physical SIM card hardware
- However, the K and OPc are the carrier's cryptographic secrets, and extracting them may violate:
  - The carrier's terms of service
  - Computer fraud/misuse laws (e.g., CFAA in the US)
  - Telecom regulations (in many countries, SIM cloning is specifically criminalized)
- The 3GPP security architecture is designed with the assumption that K never leaves the SIM. Bypassing this security design may have legal implications.

### 7.2 Technical Analysis

Even if extraction were legally permissible, it remains **technically infeasible** for modern SIMs (as detailed in Section 1.1). You cannot extract K from a carrier SIM even if you own it.

### 7.3 If You Somehow Had K/OP (e.g., from carrier cooperation)

If a carrier provided you with the K and OPc for your SIM (e.g., for a legitimate multi-SIM service, or as an MVNO), you could:

1. **Build a VirtualSIM** — compute AKA responses in pure software
2. **Provision a blank programmable SIM** — write the carrier's K/OPc to a sysmoISIM card
3. **Run multiple instances** — both the physical SIM and the VirtualSIM could authenticate, but:
   - **SQN conflicts** would arise (the HSS tracks one SQN, but multiple instances would desynchronize it)
   - **The carrier's S-CSCF** may detect concurrent registrations and reject them
   - **This is essentially SIM cloning** — the carrier would consider it unauthorized

**Ethical/legal stance**: This report provides the technical analysis. The decision to extract or duplicate carrier credentials involves legal and ethical considerations that are outside the scope of this technical document.

---

## 8. Hardware Needed: Complete BOM

### 8.1 Minimum Viable Setup (Single SIM, Carrier Path)

| Item | Model | Cost | Purpose |
|------|-------|------|---------|
| PC/SC USB Reader | Omnikey 3121 or SCM SCR3310 | $20-50 | Read ISIM files + AUTHENTICATE APDU |
| Carrier SIM | Your existing carrier SIM | $0 (owned) | Authenticate against carrier IMS |
| Linux Host | Any x86/ARM | varies | Run sim-rest-server + SIP stack |

**Software**: pcsc-lite, pyscard, pySim (git), sim-rest-server.py (patched for ISIM)

### 8.2 Programmable SIM Setup (Self-Hosted IMS Path)

| Item | Model | Cost | Purpose |
|------|-------|------|---------|
| PC/SC USB Reader | Omnikey 3121 or SCM SCR3310 | $20-50 | Provision SIM cards |
| Programmable ISIM | sysmoISIM-SJA5 (single) | ~€8-12 | SIM with known K/OPc |
| Linux Host | Any x86/ARM | varies | Run IMS core + headless RCS client |

**Software**: pcsc-lite, pyscard, pySim (git), Open5GS, Kamailio, MILENAGE library

### 8.3 Phone Farm Setup (8 SIMs, Carrier Path)

| Item | Model | Cost | Purpose |
|------|-------|------|---------|
| Multi-SIM Reader | sysmoOCTSIM | ~€200 | 8 SIM slots |
| Carrier SIMs | 8x carrier SIMs | varies | Authenticate against carrier IMS |
| Linux Host | Any x86/ARM | varies | Run sim-rest-server (8 slots) + SIP stacks |

### 8.4 Virtual SIM Setup (No Physical SIMs, Self-Hosted IMS)

| Item | Model | Cost | Purpose |
|------|-------|------|---------|
| None | — | $0 | Pure software AKA computation |
| Linux Host | Any x86/ARM | varies | Run VirtualSIM + IMS core + RCS client |

**Software**: CryptoMobile (Python) or wmnsk/milenage (Go), Open5GS, Kamailio

---

## 9. Summary: Two Operational Paths

### Path A: Carrier SIM (Physical SIM Required)

```
┌──────────────┐     ┌───────────────┐     ┌──────────────┐     ┌──────────────┐
│ Carrier SIM  │────→│ sim-rest-     │────→│ AKA-Digest   │────→│ Carrier IMS  │
│ in PC/SC     │     │ server.py     │     │ Computation  │     │ Core         │
│ Reader       │     │ (REST API)    │     │ (RES→MD5)    │     │ (P/I/S-CSCF) │
│              │     │               │     │              │     │              │
│ K/OPc: UNKNOWN│    │               │     │              │     │ K/OPc: KNOWN │
│ (inside SIM)  │    │               │     │              │     │ (in HSS)     │
└──────────────┘     └───────────────┘     └──────────────┘     └──────────────┘

Requirements: 1 physical SIM per concurrent registration
Limitations: SIM must stay online, sim-rest-server latency, SQN sync issues
Advantages: Works on carrier networks, legitimate
```

### Path B: Programmable SIM or Virtual SIM (Self-Hosted IMS)

```
┌──────────────────────────────────────────┐     ┌──────────────┐
│ VirtualSIM (Software)                    │     │ Self-Hosted  │
│ OR Programmable SIM (sysmoISIM-SJA5)    │────→│ IMS Core     │
│                                          │     │ (Open5GS +   │
│ K/OPc: KNOWN (you provisioned them)      │     │  Kamailio)   │
│ MILENAGE: computed in software            │     │              │
│ No hardware dependency (virtual)         │     │ K/OPc: SAME  │
│ OR PC/SC reader (programmable SIM)       │     │ (in your HSS)│
└──────────────────────────────────────────┘     └──────────────┘

Requirements: None (virtual) or programmable SIM + reader (physical)
Limitations: Only works on your own IMS core (not carrier networks without MVNO agreement)
Advantages: No SIM hardware needed, instant scaling, full control over SQN, no sim-rest-server
```

### Path B with Federation

```
┌──────────────────┐     ┌──────────────┐     ┌──────────────┐
│ VirtualSIM /     │────→│ Self-Hosted  │────→│ Carrier IMS  │
│ Programmable SIM │     │ IMS Core     │     │ (via SIP     │
│                  │     │ + RCS AS     │     │  peering)    │
│ K/OPc: YOURS    │     │              │     │              │
└──────────────────┘     └──────────────┘     └──────────────┘

Messages flow: Your RCS client → Your IMS core → SIP peering → Carrier IMS → Recipient
This requires a SIP trunk / IPX interconnect with the carrier.
```

---

## 10. Key References

| Spec/Standard | Title | Relevance |
|--------------|-------|-----------|
| 3GPP TS 33.102 | Security Architecture | MILENAGE algorithm definition, AKA protocol |
| 3GPP TS 33.203 | IMS Security | AKAv1-MD5 for IMS registration |
| 3GPP TS 35.205-207 | MILENAGE Algorithm Set | Mathematical definition and test vectors |
| 3GPP TS 35.222 | TUAK Algorithm Set | Alternative to MILENAGE using Keccak |
| 3GPP TS 31.102 | USIM Characteristics | USIM file structure, AUTHENTICATE command |
| 3GPP TS 31.103 | ISIM Characteristics | ISIM file structure (IMPI, IMPU, DOMAIN, P-CSCF) |
| ETSI TS 102 226 | Remote APDU Structure | UICC application communication |
| RFC 3310 | AKA for HTTP Digest | AKAv1-MD5 digest computation |
| RFC 4169 | AKAv2-MD5 | Updated AKA digest (5G) |
| sysmoISIM-SJA5 Manual | sysmocom product documentation | Card-specific file structure, provisioning |
| Nick vs Networking | "HSS & USIM Authentication in LTE/NR" | OP/OPc explanation, authentication flow |
| Nick vs Networking | "Querying Auth Credentials from USIM/SIM Cards" | osmo-sim-auth usage, HSS/AuC interaction |
| Rambus Blog | "Cracking SIM cards with side-channel attacks" | Side-channel attack research summary |
| Kaspersky Blog | "SIM card cloning and security" | SIM cloning history and COMP128 attacks |
| wmnsk/milenage | GitHub repository | Go MILENAGE implementation |
| mitshell/CryptoMobile | GitHub repository | Python MILENAGE implementation |
| Magma milenage.py | Facebook/Magma repository | Python MILENAGE (production-grade) |

---

## Appendix A: MILENAGE Quick Reference (TS 35.206)

```
OPc = AES_K(OP)                    # Derive OPc from OP using K
RES, CK, IK, AK = f2_f5(RAND)      # Main authentication functions
MAC-A = f1(RAND, SQN, AMF)         # Network authentication MAC
MAC-S = f1*(RAND, SQN, AMF)        # Re-synchronization MAC

# f2: RES = AES_OPc(RAND ⊕ c2) ⊕ AES_OPc(...)
# f3: CK = AES_OPc(RAND ⊕ c3) ⊕ AES_OPc(...)
# f4: IK = AES_OPc(RAND ⊕ c4) ⊕ AES_OPc(...)
# f5: AK = AES_OPc(RAND ⊕ c5) ⊕ AES_OPc(...) [lower 6 bytes]
# f1: MAC-A derived from AES_OPc chain with SQN, AMF, RAND

# Constants (default values per TS 35.206):
c1 = 00..00 (16 bytes, all zeros)
c2 = 00..01 (15 zero bytes + 0x01)
c3 = 00..02 (15 zero bytes + 0x02)
c4 = 00..03 (15 zero bytes + 0x03)
c5 = 00..04 (15 zero bytes + 0x04)
r1 = 40 (rotation constant)
r2 = 00
r3 = 20
r4 = 40
r5 = 60
```

## Appendix B: VirtualSIM Python Implementation (Complete)

```python
#!/usr/bin/env python3
"""
VirtualSIM: Pure software ISIM AKA authentication.
No physical SIM card required — MILENAGE computed in software.
Requires: pip install pycryptodome
"""

import os
import struct
from Crypto.Cipher import AES

class Milenage:
    """MILENAGE algorithm set per 3GPP TS 35.206."""
    
    # Default constants
    C1 = b'\x00' * 16
    C2 = b'\x00' * 15 + b'\x01'
    C3 = b'\x00' * 15 + b'\x02'
    C4 = b'\x00' * 15 + b'\x03'
    C5 = b'\x00' * 15 + b'\x04'
    R1 = 64
    R2 = 0
    R3 = 32
    R4 = 64
    R5 = 96
    
    def __init__(self, k: bytes, opc: bytes):
        self.k = k
        self.opc = opc
    
    def _aes_encrypt(self, key: bytes, data: bytes) -> bytes:
        cipher = AES.new(key, AES.MODE_ECB)
        return cipher.encrypt(data)
    
    def _rotate(self, data: bytes, n: int) -> bytes:
        n = n % 128
        bit_string = int.from_bytes(data, 'big')
        rotated = ((bit_string << n) | (bit_string >> (128 - n))) & ((1 << 128) - 1)
        return rotated.to_bytes(16, 'big')
    
    def f1(self, rand: bytes, sqn: bytes, amf: bytes) -> bytes:
        """Compute MAC-A (f1)."""
        # Temp = rotate( AES_OPc(RAND ⊕ C1), r1 ) ⊕ OPc
        rand_xor_c1 = bytes(a ^ b for a, b in zip(rand, self.C1))
        temp = self._aes_encrypt(self.opc, rand_xor_c1)
        temp = self._rotate(temp, self.R1)
        temp = bytes(a ^ b for a, b in zip(temp, self.opc))
        
        # IN1 = SQN || AMF || SQN || AMF
        in1 = sqn + amf + sqn + amf
        
        # Temp2 = AES_K( Temp ⊕ IN1 )
        temp_xor_in1 = bytes(a ^ b for a, b in zip(temp, in1))
        temp2 = self._aes_encrypt(self.k, temp_xor_in1)
        
        # MAC-A = AES_OPc( rotate(Temp2, r1) ⊕ OPc )
        temp2_rot = self._rotate(temp2, self.R1)
        temp2_rot_xor_opc = bytes(a ^ b for a, b in zip(temp2_rot, self.opc))
        mac_a = self._aes_encrypt(self.opc, temp2_rot_xor_opc)
        return mac_a
    
    def f2345(self, rand: bytes):
        """Compute RES (f2), CK (f3), IK (f4), AK (f5)."""
        # Temp = rotate( AES_OPc(RAND ⊕ C2), r2 ) ⊕ OPc
        rand_xor_c2 = bytes(a ^ b for a, b in zip(rand, self.C2))
        temp = self._aes_encrypt(self.opc, rand_xor_c2)
        temp = self._rotate(temp, self.R2)
        temp = bytes(a ^ b for a, b in zip(temp, self.opc))
        
        # OUT2 = AES_K( Temp )
        out2 = self._aes_encrypt(self.k, temp)
        
        # RES = AES_OPc( rotate(OUT2, r3) ⊕ OPc ) [lower 8 bytes]
        out2_rot = self._rotate(out2, self.R3)
        res_full = self._aes_encrypt(self.opc, bytes(a ^ b for a, b in zip(out2_rot, self.opc)))
        res = res_full[8:]  # Lower 8 bytes (64-bit RES)
        
        # CK = AES_OPc( rotate(OUT2 ⊕ C3, r4) ⊕ OPc )
        out2_xor_c3 = bytes(a ^ b for a, b in zip(out2, self.C3))
        out2_c3_rot = self._rotate(out2_xor_c3, self.R4)
        ck = self._aes_encrypt(self.opc, bytes(a ^ b for a, b in zip(out2_c3_rot, self.opc)))
        
        # IK = AES_OPc( rotate(OUT2 ⊕ C4, r5) ⊕ OPc )
        out2_xor_c4 = bytes(a ^ b for a, b in zip(out2, self.C4))
        out2_c4_rot = self._rotate(out2_xor_c4, self.R5)
        ik = self._aes_encrypt(self.opc, bytes(a ^ b for a, b in zip(out2_c4_rot, self.opc)))
        
        # AK = AES_OPc( rotate(OUT2 ⊕ C5, r5) ⊕ OPc ) [lower 6 bytes]
        out2_xor_c5 = bytes(a ^ b for a, b in zip(out2, self.C5))
        out2_c5_rot = self._rotate(out2_xor_c5, self.R5)
        ak_full = self._aes_encrypt(self.opc, bytes(a ^ b for a, b in zip(out2_c5_rot, self.opc)))
        ak = ak_full[10:]  # Lower 6 bytes
        
        return res, ck, ik, ak


class VirtualSIM:
    """Pure software ISIM that computes AKA responses."""
    
    def __init__(self, k_hex: str, opc_hex: str, amf_hex: str = "8000", sqn: int = 0):
        self.k = bytes.fromhex(k_hex)
        self.opc = bytes.fromhex(opc_hex)
        self.amf = bytes.fromhex(amf_hex)
        self.sqn = sqn
        self.milenage = Milenage(self.k, self.opc)
    
    def authenticate(self, rand_hex: str, autn_hex: str) -> dict:
        rand = bytes.fromhex(rand_hex)
        autn = bytes.fromhex(autn_hex)
        
        # Compute f2-f5
        res, ck, ik, ak = self.milenage.f2345(rand)
        
        # Recover SQN from AUTN: SQN ⊕ AK = AUTN[0:6]
        sqn_ak = autn[:6]
        sqn_ms = bytes(a ^ b for a, b in zip(sqn_ak, ak))
        sqn_int = int.from_bytes(sqn_ms, 'big')
        
        # Verify MAC-A
        mac_a = self.milenage.f1(rand, sqn_ms, self.amf)
        mac_received = autn[8:16]
        
        if mac_a != mac_received:
            return {"error": "MAC verification failed", 
                    "expected_mac": mac_a.hex(), "received_mac": mac_received.hex()}
        
        # Check SQN freshness
        if sqn_int < self.sqn:
            # SQN too old — return AUTS for re-synchronization
            return {"synchronisation_failure": True,
                    "client_sqn": self.sqn, "hss_sqn": sqn_int}
        
        # Update SQN
        self.sqn = sqn_int + 1
        
        return {
            "successful_3g_authentication": {
                "res": res.hex(),
                "ck": ck.hex(),
                "ik": ik.hex(),
            }
        }


# === Usage Example ===
if __name__ == "__main__":
    # Example K and OPc (from 3GPP TS 35.207 test vectors)
    K = "465b5ce8b199b49faa5f0a2ee238a6bc"
    OPc = "cdc202d5123e20f62b2d3f7edb0b66c3"
    
    vsim = VirtualSIM(K, OPc, amf_hex="8000", sqn=0)
    
    # Simulate a network challenge
    rand = "3ce9c4e4ba887cb059b5957f9081ba68"
    autn = "8c39a4b8fb264517b7d4f62a15c1e2f1"  # Example — must match HSS
    
    result = vsim.authenticate(rand, autn)
    print(f"VirtualSIM result: {result}")
```

---

*Report generated from 15 targeted web searches, 2 URL analyses (Nick vs Networking), and 3 existing internal research documents (pysim-sim-auth-rest-audit-report.md, headless-rcs-recipe.md, rcsjta-audit-and-aka-glue-code.md).*
