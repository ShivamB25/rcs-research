# pySim SIM Auth REST Audit Report

## Executive Summary

The Osmocom pySim ecosystem provides a complete toolchain for programmatic SIM card authentication against carrier IMS cores. The `sim-rest-server.py` exposes a REST API that bridges PC/SC card readers to remote applications needing UMTS AKA (Authentication and Key Agreement) authentication. This report details the exact API specification, the ISIM authentication flow, programmatic ISIM file access, hardware requirements, SIP REGISTER integration, and limitations.

---

## 1. REST API Specification for sim-rest-server

### Base URL
```
http://<host>:8000 (default; configurable via -H and -p flags)
```

### Endpoint 1: Authentication

**`POST /sim-auth-api/v1/slot/<SLOT_NR>`**

- `SLOT_NR` is the integer PC/SC reader slot number (0..7 for a sysmoOCTSIM board)

**Request Body** (JSON):
```json
{
    "rand": "bb685a4b2fc4d697b9d6a129dd09a091",
    "autn": "eea7906f8210000004faf4a7df279b56"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `rand` | hex string (16 bytes) | Random challenge from HSS/AuC |
| `autn` | hex string (16 bytes) | Authentication token from HSS/AuC |

**HTTP Status Codes**:

| Status | Code | Description |
|--------|------|-------------|
| 200 | OK | Successful execution (includes SIM-side errors in response body) |
| 400 | Bad Request | Request body is malformed |
| 404 | Not Found | Specified SIM slot doesn't exist |
| 410 | Gone | No SIM card inserted in slot |
| 500 | Internal Error | Protocol error or SW mismatch |

**Response Body** (JSON) — Success:
```json
{
    "successful_3g_authentication": {
        "res": "b15379540ec93985",
        "ck": "713fde72c28cbd282a4cd4565f3d6381",
        "ik": "2e641727c95781f1020d319a0594f31a",
        "kc": "771a2c995172ac42"
    }
}
```

**Response Body** (JSON) — Synchronisation Failure:
```json
{
    "synchronisation_failure": {
        "auts": "dc2a591fe072c92d7c46ecfe97e5"
    }
}
```

**Response Body** (JSON) — Auth Error (via SW codes):
- `9862` = Authentication error, incorrect MAC
- `6982` = Security status not satisfied (PIN not verified)
- `9864` = Authentication error, security context not supported
- `9865` = Key freshness failure

### Endpoint 2: Card Information

**`GET /sim-info-api/v1/slot/<SLOT_NR>`**

**Response Body** (JSON):
```json
{
    "imsi": "262012345678901",
    "iccid": "89442012345678901234"
}
```

### Critical Implementation Note

The current `sim-rest-server.py` **hardcodes** `card.select_adf_by_aid(adf='usim')` — it always authenticates against ADF.USIM. **It does NOT currently support ISIM authentication.** To authenticate against ISIM, the server code must be modified to select ADF.ISIM (`a0000000871004`) instead. The underlying `scc.authenticate()` method is the same for both USIM and ISIM — the only difference is which ADF is selected before calling AUTHENTICATE.

---

## 2. ISIM AKA Authentication — Step by Step

### 2.1 UMTS AKA Protocol Flow (RAND+AUTN → RES+CK+IK)

The ISIM authentication uses the **exact same AUTHENTICATE APDU** as USIM, but executed within the ISIM application context (ADF.ISIM). Here is the complete flow:

```
┌─────────┐          ┌──────────┐         ┌──────────┐        ┌──────────┐
│  HSS/   │          │ REST     │         │sim-rest- │        │  ISIM    │
│  AuC    │          │ Client   │         │ server   │        │  Card    │
└────┬────┘          └────┬─────┘         └────┬─────┘        └────┬─────┘
     │                    │                    │                   │
     │ 1. Generate RAND,  │                    │                   │
     │    AUTN from K,    │                    │                   │
     │    OPc, SQN, AMF   │                    │                   │
     │────────────────────>│                    │                   │
     │  (RAND, AUTN)       │                    │                   │
     │                    │ 2. POST /sim-auth-api/v1/slot/N        │
     │                    │ {rand, autn}      │                   │
     │                    │───────────────────>│                   │
     │                    │                    │ 3. SELECT ADF.ISIM │
     │                    │                    │   (AID=a0000000871004)│
     │                    │                    │──────────────────>│
     │                    │                    │                   │
     │                    │                    │ 4. AUTHENTICATE   │
     │                    │                    │   CLA=00 INS=88   │
     │                    │                    │   P1=00 P2=81     │
     │                    │                    │   Data: RAND|AUTN │
     │                    │                    │──────────────────>│
     │                    │                    │                   │
     │                    │                    │ 5. Card computes: │
     │                    │                    │   Milenage f1-f5  │
     │                    │                    │   using K, OPc    │
     │                    │                    │   → verifies MAC  │
     │                    │                    │   → derives RES,  │
     │                    │                    │     CK, IK, Kc   │
     │                    │                    │                   │
     │                    │                    │ <──────────────────│
     │                    │                    │  RES+CK+IK+Kc     │
     │                    │                    │  (or AUTS if sync │
     │                    │                    │   failure)        │
     │                    │ <──────────────────│                   │
     │                    │ {res, ck, ik, kc}  │                   │
     │ <─────────────────│                    │                   │
     │  RES, CK, IK       │                    │                   │
     │                    │                    │                   │
     │ 6. HSS compares    │                    │                   │
     │    XRES == RES     │                    │                   │
     │    → Auth success  │                    │                   │
     └────────────────────┘                    │                   │
```

### 2.2 AUTHENTICATE APDU Structure (TS 31.102 Section 7.1.2.1)

**Command APDU:**
```
CLA=00 INS=88 P1=00 P2=81 (for 3G context) or P2=80 (for 2G/GSM context)
Data: [RAND length byte][RAND 16 bytes][AUTN length byte][AUTN 16 bytes]
Le: 00
```

**Response (Success):**
```
Tag=0xDB [RES length][RES bytes][CK length][CK 16 bytes][IK length][IK 16 bytes][Kc length][Kc 8 bytes]
```

**Response (Sync Failure):**
```
Tag=0xDC [AUTS length][AUTS 14 bytes]
```

### 2.3 ISIM vs USIM Authentication Differences

| Aspect | USIM | ISIM |
|--------|------|------|
| ADF AID | `a0000000871002` | `a0000000871004` |
| AUTHENTICATE INS | `0x88` / `0x89` | `0x88` / `0x89` (same) |
| P2 byte for 3G | `0x81` | `0x81` (same) |
| Key material (K, OPc) | Stored in EF.USIM_AUTH_KEY | Stored in EF.ISIM_AUTH_KEY |
| SQN tracking | EF.USIM_SQN | EF.ISIM_SQN |
| Result fields | RES + CK + IK + Kc | RES + CK + IK (+ Kc optional) |
| Authentication purpose | Network access (EAP-AKA) | IMS services (SIP REGISTER) |
| Service table | EF.UST | EF.IST |

**The cryptographic algorithm is identical** — both use MILENAGE (or TUAK) with the same f1-f5 functions. The only difference is which ADF is selected and which key material is used.

---

## 3. Reading ISIM Files Programmatically

### 3.1 ISIM Application Files (3GPP TS 31.103)

| File | FID | SFID | Type | Description |
|------|-----|------|------|-------------|
| EF.IMPI | 6F02 | 0x02 | Transparent | IMS Private User Identity (NAI) |
| EF.DOMAIN | 6F03 | 0x05 | Transparent | Home Network Domain Name |
| EF.IMPU | 6F04 | 0x04 | Linear Fixed | IMS Public User Identity (URI) |
| EF.AD | 6FAD | 0x03 | Transparent | Administrative Data |
| EF.ARR | 6F06 | 0x06 | Linear Fixed | Access Rule Reference |
| EF.IST | 6F07 | 0x07 | Transparent | ISIM Service Table |
| EF.P-CSCF | 6F09 | - | Linear Fixed | P-CSCF Address |
| EF.GBABP | 6FD5 | - | Transparent | GBA Bootstrapping |
| EF.GBANL | 6FD7 | - | Linear Fixed | GBA NAF List |
| EF.NAFKCA | 6FDD | - | Linear Fixed | NAF Key Centre Address |
| EF.POL | 6F27 | - | - | Policy |
| EF.UICCIARI | 6FE4 | - | Linear Fixed | UICC IARI |

### 3.2 Reading ISIM Files via pySim-shell

```bash
# Start pySim-shell
pySim-shell.py -p 0

# Select ADF.ISIM
select ADF.ISIM

# Read EF.IMPI (IMS Private Identity - NAI)
select EF.IMPI
read_decoded

# Read EF.DOMAIN (Home Network Domain)
select EF.DOMAIN
read_decoded

# Read EF.IMPU (IMS Public User Identity)
select EF.IMPU
read_records_decoded

# Read EF.P-CSCF (P-CSCF address for IMS registration)
select EF.P-CSCF
read_records_decoded

# Read EF.IST (ISIM Service Table)
select EF.IST
read_decoded
```

### 3.3 Reading ISIM Files Programmatically (Python)

```python
from pySim.transport.pcsc import PcscSimLink
from pySim.commands import SimCardCommands
from pySim.cards import UiccCardBase

# Connect to card
tp = PcscSimLink(argparse.Namespace(pcsc_dev=0))
tp.connect()
scc = SimCardCommands(tp)
card = UiccCardBase(scc)
scc.cla_byte = "00"
scc.sel_ctrl = "0004"
card.read_aids()

# Select ADF.ISIM
card.select_adf_by_aid(adf='isim')

# Read EF.IMPI (FID=6F02)
impi_hex, sw = scc.read_binary('6f02')
# Decode: BER-TLV tag 0x80 contains NAI string
# e.g., "803137333830303630303030303031303140696d732e6d6e633030302e6d63633733382e336770706e6574776f726b2e6f7267"
# → "738006000000101@ims.mnc000.mcc738.3gppnetwork.org"

# Read EF.DOMAIN (FID=6F03)
domain_hex, sw = scc.read_binary('6f03')
# BER-TLV tag 0x80 → domain name like "ims.mnc000.mcc738.3gppnetwork.org"

# Read EF.IMPU (FID=6F04, linear fixed)
rec_count = scc.record_count('6f04')
for i in range(1, rec_count + 1):
    impu_hex, sw = scc.read_record('6f04', i)
    # BER-TLV tag 0x80 → SIP URI like "sip:738006000000101@ims.mnc000.mcc738.3gppnetwork.org"

# Read EF.P-CSCF (FID=6F09, linear fixed)
rec_count = scc.record_count('6f09')
for i in range(1, rec_count + 1):
    pcscf_hex, sw = scc.read_record('6f09', i)
    # BER-TLV tag 0x80 → type_of_address (0=FQDN, 1=IPv4, 2=IPv6) + address

tp.disconnect()
```

### 3.4 ISIM File Data Formats

**EF.IMPI** (IMS Private Identity):
- BER-TLV with tag 0x80: NAI (Network Access Identifier) as UTF-8
- Example: `user@ims.mnc<MNC>.mcc<MCC>.3gppnetwork.org`

**EF.DOMAIN** (Home Network Domain):
- BER-TLV with tag 0x80: Domain name as UTF-8
- Example: `ims.mnc000.mcc738.3gppnetwork.org`

**EF.IMPU** (IMS Public User Identity):
- BER-TLV with tag 0x80: SIP URI as UTF-8
- Example: `sip:user@ims.mnc000.mcc738.3gppnetwork.org`

**EF.P-CSCF** (P-CSCF Address):
- BER-TLV with tag 0x80: Struct of `type_of_address` (1 byte) + `address`
  - Type 0: FQDN (UTF-8 string)
  - Type 1: IPv4 (4 bytes)
  - Type 2: IPv6 (16 bytes)

---

## 4. Hardware Requirements

### 4.1 PC/SC Card Readers

| Hardware | Description | Slots | Notes |
|----------|-------------|-------|-------|
| Standard USB PC/SC reader | Omnikey, SCM, etc. | 1 | Common, cheap (~$20-50) |
| sysmoOCTSIM | 8-slot SIM card reader board | 8 (0..7) | Designed for batch ops, ~€200 |
| sysmoOCTSIM-T1 | Improved multi-slot board | 8 | Better thermal design |
| Springcard | Multi-slot reader | 2-4 | Alternative option |

### 4.2 Programmable SIM Cards

| Card | Form Factor | Apps | 3GPP Release | Notes |
|------|-------------|------|--------------|--------|
| **sysmoISIM-SJA2** | 2FF/3FF/4FF | SIM+USIM+ISIM | Rel-8+ | **Primary choice for IMS auth** |
| **sysmoISIM-SJA5** | 2FF/3FF/4FF | SIM+USIM+ISIM+HPSIM | Rel-17 | **Successor, adds 5G/HPSIM** |
| sysmoUSIM-SJS1 | 2FF/3FF/4FF | SIM+USIM | Rel-8 | No ISIM - can't do IMS auth directly |
| sysmoEUICC1 | - | eUICC | SGP.22 | eSIM, different usage pattern |

**Key details for sysmoISIM-SJA2:**
- ATR: `3b9f96801f878031e073fe211b674a4c753034054ba9` (or variants)
- Contains DF.SYSTEM with EF.SIM_AUTH_KEY (stores K and OPc), EF.MILENAGE_CFG
- ISIM ADF contains EF.ISIM_AUTH_KEY, EF.ISIM_SQN
- Supports MILENAGE and TUAK algorithms
- Price: ~€5-10 per card

**Key details for sysmoISIM-SJA5:**
- ATR: `3b9f96801f878031e073fe211b674a357530350251cc` (or variants)
- Same DF.SYSTEM structure as SJA2
- Adds 5G support (HPSIM, SUCI computation)
- Adds TUAK algorithm support
- Enhanced key storage with key_length and configurable sizes

### 4.3 Minimum Hardware Setup

```
[sysmoOCTSIM board with 8 SIM slots]  ←→  USB  ←→  [Linux host running sim-rest-server.py]
                                              ↕
                                    REST API on port 8000
                                              ↕
                                    [IMS client / SIP stack]
```

---

## 5. Chaining sim-rest-server → SIP REGISTER for IMS Authentication

### 5.1 IMS Registration Flow with SIM Auth

```
UE/Client                    P-CSCF                I-CSCF               S-CSCF               HSS
   │                           │                     │                    │                  │
   │ 1. SIP REGISTER           │                     │                    │                  │
   │──────────────────────────>│────────────────────>│                    │                  │
   │                           │                     │ 2. Cx: UAR        │                  │
   │                           │                     │───────────────────>│─────────────────>│
   │                           │                     │                    │ 3. Cx: UAA       │
   │                           │                     │                    │ (auth data)       │
   │                           │                     │                    │<─────────────────│
   │                           │                     │ 4. 401 Unauthorized                   │
   │                           │                     │<───────────────────│                  │
   │ 5. 401 Unauthorized       │                     │                    │                  │
   │ (WWW-Authenticate:        │                     │                    │                  │
   │  algorithm=AKAv1-MD5,     │                     │                    │                  │
   │  nonce=<base64 RAND:AUTN>)│                     │                    │                  │
   │<──────────────────────────│                     │                    │                  │
   │                           │                     │                    │                  │
   │ 6. Extract RAND, AUTN from nonce                               │                  │
   │ 7. POST /sim-auth-api/v1/slot/0  →→→  SIM Card                  │                  │
   │    {rand, autn}           │                     │   → RES, CK, IK  │                  │
   │  ← {res, ck, ik}         │                     │                    │                  │
   │                           │                     │                    │                  │
   │ 8. Compute response using RES, CK, IK                          │                  │
   │ 9. SIP REGISTER           │                     │                    │                  │
   │ (Authorization:           │                     │                    │                  │
   │  algorithm=AKAv1-MD5,     │                     │                    │                  │
   │  response=<computed>)     │                     │                    │                  │
   │──────────────────────────>│────────────────────>│──────────────────>│                  │
   │                           │                     │                    │ 10. Cx: SAR     │
   │                           │                     │                    │─────────────────>│
   │                           │                     │                    │ 11. Cx: SAA     │
   │                           │                     │                    │<─────────────────│
   │ 12. 200 OK                │                     │                    │                  │
   │<──────────────────────────│                     │                    │                  │
```

### 5.2 Code: SIP REGISTER with SIM Auth (Python Pseudocode)

```python
import requests
import hashlib
import hmac
import base64

# Configuration
SIM_REST_URL = "http://localhost:8000/sim-auth-api/v1/slot/0"
SIM_SLOT = 0
SIP_REGISTRAR = "sip:ims.mnc000.mcc738.3gppnetwork.org"
IMPI = "738006000000101@ims.mnc000.mcc738.3gppnetwork.org"  # From EF.IMPI
IMPU = "sip:738006000000101@ims.mnc000.mcc738.3gppnetwork.org"  # From EF.IMPU

# Step 1: Send initial SIP REGISTER (no auth)
# → Receives 401 with WWW-Authenticate header containing nonce

# Step 2: Parse the 401 challenge
# WWW-Authenticate: Digest algorithm=AKAv1-MD5, nonce="<base64 RAND:AUTN:...>", realm="..."

# Step 3: Extract RAND and AUTN from the nonce
# nonce = base64_decode(nonce_str)
# RAND = nonce[0:16]  (16 bytes)
# AUTN = nonce[16:32] (16 bytes)

# Step 4: Perform SIM authentication via REST API
def sim_auth(rand_hex: str, autn_hex: str) -> dict:
    """Call sim-rest-server to authenticate against the SIM card."""
    resp = requests.post(SIM_REST_URL, json={
        "rand": rand_hex,
        "autn": autn_hex
    })
    resp.raise_for_status()
    return resp.json()

auth_result = sim_auth(rand_hex, autn_hex)

if "synchronisation_failure" in auth_result:
    # Handle AUTS re-sync
    auts = auth_result["synchronisation_failure"]["auts"]
    # Need to re-request with AUTS to HSS for new RAND/AUTN
    pass
elif "successful_3g_authentication" in auth_result:
    auth_data = auth_result["successful_3g_authentication"]
    res_hex = auth_data["res"]
    ck_hex = auth_data["ck"]
    ik_hex = auth_data["ik"]

    # Step 5: Compute SIP Digest response
    # For AKAv1-MD5: response = MD5(H(A1) + ":" + nonce + ":" + H(A2))
    # where H(A1) = MD5(IMPI + ":" + realm + ":" + password)
    # For AKA: H(A1) = MD5(IMPI + ":" + realm + ":" + ":" + CK + IK)
    #          (password is derived from CK||IK, not RES)
    # H(A2) = MD5("REGISTER:" + IMPU)

    # Note: The exact AKA-Digest computation follows RFC 3310 / RFC 4169
    ck_ik = bytes.fromhex(ck_hex + ik_hex)
    ha1 = hashlib.md5((IMPI + ":" + realm + ":").encode() + ck_ik).hexdigest()
    ha2 = hashlib.md5(("REGISTER:" + IMPU).encode()).hexdigest()
    response = hashlib.md5(
        (ha1 + ":" + nonce_str + ":" + ha2).encode()
    ).hexdigest()

    # Step 6: Send authenticated SIP REGISTER
    # Authorization: Digest username="<IMPI>", realm="<realm>",
    #   nonce="<nonce>", uri="<IMPU>", response="<response>",
    #   algorithm=AKAv1-MD5
```

### 5.3 EAP-AKA (Alternative to SIP Digest AKA)

For EAP-AKA (used in some IMS deployments and WiFi offload):
```
EAP-Request/AKA-Identity → UE
EAP-Response/AKA-Identity (IMPI) → Network
EAP-Request/AKA-Challenge (RAND, AUTN, MAC) → UE
  → UE sends RAND+AUTN to sim-rest-server
  → Gets back RES, CK, IK
EAP-Response/AKA-Challenge (RES, MAC) → Network
EAP-Success (+ MSK/EMSK derived from CK/IK) → UE
```

---

## 6. Full Auth Flow Code Snippets

### 6.1 Starting sim-rest-server

```bash
# Install dependencies
pip3 install pyscard pyosmocom construct klein

# Start the REST server (listens on localhost:8000)
python3 contrib/sim-rest-server.py -H 0.0.0.0 -p 8000
```

### 6.2 Using sim-rest-client for Testing

```bash
# Test authentication with known K and OPc
python3 contrib/sim-rest-client.py \
    -H localhost -p 8000 \
    -n 0 \               # SIM slot 0
    auth \
    -c 1 \               # 1 authentication round
    -k 841EAD87BC9D974ECA1C167409357601 \  # Secret key K
    -o 3211CACDD64F51C3FD3013ECD9A582A0     # Secret OPc
```

### 6.3 Modified sim-rest-server for ISIM Authentication

```python
# PATCH: Replace the auth endpoint in SimRestServer class
# to support ISIM authentication

@app.route('/sim-auth-api/v1/slot/<int:slot>')
def auth(self, request, slot):
    """REST API endpoint for performing authentication against USIM/ISIM."""
    try:
        content = json.loads(request.content.read())
        rand = content['rand']
        autn = content['autn']
        # NEW: Support application selection via query param
        app = content.get('app', 'usim')  # 'usim' or 'isim'
    except:
        set_headers(request)
        request.setResponseCode(400)
        return str(ApiError("Malformed Request"))

    tp, scc, card = connect_to_card(slot)

    # NEW: Select ISIM or USIM ADF
    card.select_adf_by_aid(adf=app)

    res, sw = scc.authenticate(rand, autn)
    tp.disconnect()

    set_headers(request)
    return json.dumps(res, indent=4)
```

### 6.4 osmo-sim-auth.py (Direct PC/SC Authentication, No REST)

```bash
# USIM authentication (3G)
python2 osmo-sim-auth.py -r <RAND_HEX> -a <AUTN_HEX>

# SIM-only authentication (2G, no AUTN needed)
python2 osmo-sim-auth.py -s -r <RAND_HEX>

# IPSec strongswan mode (outputs triplets.dat format)
python2 osmo-sim-auth.py -s -r <RAND_HEX> -I
```

**Note:** osmo-sim-auth uses the older `pyscard`-based `card` library, not pySim. It only supports USIM/SIM, not ISIM directly.

---

## 7. eSIM and Remote SIM Access Support

### 7.1 osmo-remsim (Remote SIM Infrastructure)

Osmocom provides **osmo-remsim**, a complete remote SIM access solution:

- **osmo-remsim-server**: Central server managing SIM-to-modem mappings
- **osmo-remsim-bankd**: Bank daemon controlling a bank of physical SIM card readers
- **osmo-remsim-client**: Client daemon running alongside a modem
- **libifd_remsim_client**: PC/SC IFD handler that presents a virtual PC/SC reader

**Architecture:**
```
[pySim-shell / sim-rest-server]
         ↕ (PC/SC)
[libifd_remsim_client] ←→ [osmo-remsim-server] ←→ [osmo-remsim-bankd] ←→ [Physical SIM readers]
```

This allows pySim to access **remote SIM cards** over IP, enabling:
- SIM bank operation (many SIMs in a data center)
- Dynamic SIM-to-modem assignment
- Geographic separation of SIMs and modems

### 7.2 Android APDU Proxy

An Android app provides a bridge between a host computer and the UICC/eUICC slot of an Android phone via OMAPI (Open Mobile API, Android 8+/API 29+). Uses a VPCD server to provide a virtual PC/SC reader.

### 7.3 eSIM (eUICC) Support in pySim

pySim has extensive eUICC/eSIM support:
- **osmo-smdpp.py**: Proof-of-concept GSMA SGP.22 Consumer eSIM SM-DP+ server
- **eUICC ISD-R commands**: pySim-shell can interact with eUICC ISD-R for profile management
- **eSIM profile management**: Install, enable, disable, delete eSIM profiles
- **SCP03 secure channel**: Support for GlobalPlatform SCP03 for eUICC communication

**Important:** An eUICC with an enabled eSIM profile that contains an ISIM application behaves exactly like a physical ISIM card for authentication purposes.

---

## 8. sysmoISIM-SJA2/SJA5 Specific Support

### 8.1 Card Model Detection

pySim auto-detects these cards via ATR:

**sysmoISIM-SJA2 ATRs:**
- `3b9f96801f878031e073fe211b674a4c753034054ba9`
- `3b9f96801f878031e073fe211b674a4c7531330251b2`
- `3b9f96801f878031e073fe211b674a4c5275310451d5`

**sysmoISIM-SJA5 ATRs:**
- `3b9f96801f878031e073fe211b674a357530350251cc`
- `3b9f96801f878031e073fe211b674a357530350265f8`
- `3b9f96801f878031e073fe211b674a357530350259c4`

### 8.2 SJA2/SJA5 Proprietary Files

When an SJA2/SJA5 is detected, pySim adds proprietary files under DF.SYSTEM (FID=A515):

| File | FID | Description |
|------|-----|-------------|
| EF.CHV1 | 6F01 | PIN file |
| EF.SIM_AUTH_KEY | 6F20 | USIM/ISIM authentication key (K + OPc + algorithm config) |
| EF.MILENAGE_CFG | 6F21 | Milenage algorithm configuration (r1-r5, c1-c5) |
| EF.0348_KEY | 6F22 | TS 03.48 OTA keys |
| EF.SIM_AUTH_COUNTER | AF24 | Remaining RUN GSM ALGORITHM executions |

Additionally, within ADF.USIM and ADF.ISIM:

| File | FID | Description |
|------|-----|-------------|
| EF.USIM_AUTH_KEY / EF.ISIM_AUTH_KEY | AF20 | USIM/ISIM-specific key (K + OPc + algorithm config) |
| EF.USIM_AUTH_KEY_2G / EF.ISIM_AUTH_KEY_2G | AF22 | Key for 2G authentication context |
| EF.USIM_SQN / EF.ISIM_SQN | AF30 | SQN parameters (ind_len, delta_max, age_limit, freshness) |
| EF.GBA_SK | AF31 | GBA secret key |
| EF.GBA_REC_LIST | AF32 | GBA record list |
| EF.GBA_INT_KEY | AF33 | GBA integrity key |

### 8.3 EF.USIM_AUTH_KEY / EF.ISIM_AUTH_KEY Structure

For MILENAGE:
```
Byte 0 (CfgByte):
  - Bits 7-6: Reserved
  - Bit 5: only_4bytes_res_in_3g
  - Bit 4: sres_deriv_func_in_2g (0=func1, 1=func2)
  - Bit 3: use_opc_instead_of_op (0=OP, 1=OPc)
  - Bits 2-0: algorithm (4=MILENAGE, 5=SHA1-AKA, 6=TUAK, 15=XOR)
Bytes 1-16: K (16 bytes)
Bytes 17-32: OP or OPc (16 bytes)
```

For TUAK (SJA5):
```
Byte 0: CfgByte (algorithm=6, key_length, etc.)
Byte 1: TUAK config (ck_and_ik_size, mac_size, res_size)
Byte 2: Number of Keccak iterations
Bytes 3-34: OP/OPc (32 bytes for TUAK-256)
Bytes 35+: K (16 or 32 bytes depending on key_length)
```

### 8.4 Programming ISIM Keys via pySim-shell

```bash
# Write ISIM authentication key (K + OPc)
pySim-shell.py -p 0
select ADF.ISIM
select EF.ISIM_AUTH_KEY
# Write K and OPc for Milenage
update_binary_decoded '{"cfg": {"only_4bytes_res_in_3g": false, "sres_deriv_func_in_2g": 1, "use_opc_instead_of_op": true, "algorithm": "milenage"}, "key": "00112233445566778899aabbccddeeff", "op_opc": "aabbccddeeff00112233445566778899"}'
```

---

## 9. Limitations and Compatibility

### 9.1 SIM Card ISIM Support

| Card Type | ISIM Support | Notes |
|-----------|-------------|-------|
| sysmoISIM-SJA2 | ✅ Full | Programmable, all ISIM files writable |
| sysmoISIM-SJA5 | ✅ Full | Programmable, adds 5G/HPSIM/TUAK |
| Carrier USIM-only cards | ❌ None | Most commercial SIMs lack ISIM ADF |
| Carrier USIM+ISIM cards | ✅ Read-only | ISIM present but keys unknown, auth works if card has valid ISIM credentials |
| sysmoUSIM-SJS1 | ❌ None | USIM only, no ISIM application |
| eUICC with ISIM profile | ✅ Full | Behaves like physical ISIM once profile enabled |

### 9.2 Key Limitations

1. **sim-rest-server only does USIM auth currently**: The `auth()` endpoint hardcodes `adf='usim'`. ISIM auth requires code modification (selecting ADF.ISIM instead).

2. **PIN verification**: If the SIM card has PIN1 enabled, authentication will fail with SW `6982` ("Security status not satisfied"). The sim-rest-server does not verify PIN1 before authentication. Either:
   - Disable PIN1 on the card, or
   - Add PIN verification to the server before AUTHENTICATE

3. **Carrier SIM compatibility**: Commercial carrier SIMs contain ISIM credentials but you don't have K/OPc — you can only perform real network authentication, not test-mode authentication with known keys.

4. **SQN synchronization**: The SIM maintains an internal SQN counter. If the HSS SQN drifts too far from the SIM SQN, you'll get synchronisation_failure (AUTS). The client must handle re-sync per TS 33.102 Section 6.3.3.

5. **No ISIM-specific REST endpoint**: The current REST API doesn't distinguish between USIM and ISIM authentication. A production deployment would need an `app` parameter (see patch in section 6.3).

6. **Connection per request**: sim-rest-server opens and closes a PC/SC connection for every request. This adds latency and may not work well with high-throughput requirements. For production use, consider connection pooling.

7. **Single-threaded**: Klein (Twisted-based) handles requests, but card access is inherently serial per slot. Multiple concurrent requests to the same slot will serialize at the PC/SC layer.

### 9.3 ISIM Service Table (EF.IST) Requirements

For ISIM authentication to work, these services must be activated in EF.IST:
- **Service 1**: P-CSCF address (needed for IMS registration routing)
- **Service 9**: Communication Control for IMS by ISIM (optional, but useful)
- **Service 10**: Support of UICC access to IMS (optional)

The AUTHENTICATE command itself doesn't require a specific IST service bit — it's a fundamental ISIM function. However, the P-CSCF address (service 1) is needed for the SIP REGISTER to know where to send the request.

---

## 10. Summary of Key Findings

1. **sim-rest-server.py** provides a working REST API for remote USIM AKA authentication with RAND/AUTN → RES/CK/IK, but **currently hardcodes USIM** — ISIM support requires a trivial code change.

2. **ISIM authentication** uses the same AUTHENTICATE APDU and MILENAGE algorithm as USIM — the only difference is selecting ADF.ISIM (`a0000000871004`) before the AUTHENTICATE command.

3. **ISIM files** (IMPI, IMPU, DOMAIN, P-CSCF) are accessible via standard PC/SC commands after selecting ADF.ISIM. pySim-shell provides full read/write decode/encode support.

4. **sysmoISIM-SJA2/SJA5** cards are the recommended hardware — fully programmable, contain both USIM and ISIM, and pySim has complete support for their proprietary key storage files.

5. **SIP REGISTER integration** requires extracting RAND/AUTN from the 401 challenge, calling the REST API, and computing the AKA-Digest response using RES/CK/IK per RFC 3310/4169.

6. **Remote SIM access** is possible via osmo-remsim (RSPRO protocol), allowing SIM banks in data centers with virtual PC/SC readers on client machines.

7. **eSIM/eUICC** with enabled ISIM profiles behave identically to physical ISIM cards for authentication purposes.
