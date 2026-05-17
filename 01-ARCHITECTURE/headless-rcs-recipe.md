# Headless RCS Client: SIP+SIM Technical Recipe

## Executive Summary

This document is the definitive step-by-step recipe for building a headless RCS (Rich Communication Services) client that uses real SIM cards to authenticate against carrier IMS infrastructure and send/receive RCS messages. The client operates without a phone — it places a SIM card in a PC/SC reader, reads ISIM credentials, performs IMS AKA authentication via the SIM's cryptographic processor, registers with the carrier's IMS core, and exchanges RCS messages using SIP/MSRP protocols.

**Target audience:** Engineers building SIM-backed RCS automation, phone farms, or testing infrastructure.

**Prerequisite reading:**
- `pysim-sim-auth-rest-audit-report.md` — pySim REST API for ISIM AKA auth
- `rcs_acs_provisioning_report.md` — ACS XML provisioning and P-CSCF discovery
- `rcs-sip-message-msrp-research-report.md` — SIP MESSAGE vs MSRP protocols
- `rcs-credential-extraction-research.md` — credential extraction from Android
- `jibe-rcs-cloud-protocol-research.md` — Google Jibe RCS internals
- `open5gs-ims-rcs-analysis-report.md` — self-hosted IMS stack
- `aosp-rcs-ims-audit-report.md` — Android ImsService API

---

## Step 1: SIM Card in PC/SC Reader → Read ISIM Files

### Goal
Extract the IMS identities and configuration from the ISIM application on the SIM card: IMPI, IMPU, home domain, and P-CSCF address.

### Hardware Required
| Item | Model | Cost | Notes |
|------|-------|------|-------|
| PC/SC USB reader | Omnikey 3121, SCM SCR3310 | $20–50 | Standard CCID reader |
| Multi-SIM reader | sysmoOCTSIM | ~€200 | 8 slots, for phone farms |
| Programmable ISIM | sysmoISIM-SJA2 or SJA5 | ~€5–10 | Only if self-provisioning |

### ISIM File Map (3GPP TS 31.103)

| File | FID | Type | Contains |
|------|-----|------|----------|
| EF.IMPI | 6F02 | Transparent | IMS Private User Identity (NAI) |
| EF.DOMAIN | 6F03 | Transparent | Home Network Domain Name |
| EF.IMPU | 6F04 | Linear Fixed | IMS Public User Identity (SIP URI) |
| EF.P-CSCF | 6F09 | Linear Fixed | P-CSCF Address |
| EF.IST | 6F07 | Transparent | ISIM Service Table |

### Code: Reading ISIM Files with pySim

```python
#!/usr/bin/env python3
"""Step 1: Read ISIM files from SIM card via PC/SC reader."""
import argparse
from pySim.transport.pcsc import PcscSimLink
from pySim.commands import SimCardCommands
from pySim.cards import UiccCardBase
from pySim.utils import h2b, b2h

def read_isim(slot: int = 0) -> dict:
    """Read all ISIM files from SIM card in PC/SC reader slot."""
    result = {}

    # Connect to card
    tp = PcscSimLink(argparse.Namespace(pcsc_dev=slot))
    tp.connect()
    scc = SimCardCommands(tp)
    card = UiccCardBase(scc)
    scc.cla_byte = "00"
    scc.sel_ctrl = "0004"
    card.read_aids()

    # Select ADF.ISIM (AID = A0000000871004)
    card.select_adf_by_aid(adf='isim')

    # Read EF.IMPI — IMS Private Identity (NAI)
    # BER-TLV tag 0x80 = NAI string (UTF-8)
    impi_hex, sw = scc.read_binary('6f02')
    # Decode: strip BER-TLV wrapper, extract NAI
    # e.g. "001010123456789@ims.mnc001.mcc001.3gppnetwork.org"
    result['impi'] = decode_ber_tlv_80(impi_hex)
    print(f"  IMPI: {result['impi']}")

    # Read EF.DOMAIN — Home Network Domain
    domain_hex, sw = scc.read_binary('6f03')
    result['domain'] = decode_ber_tlv_80(domain_hex)
    print(f"  Domain: {result['domain']}")

    # Read EF.IMPU — IMS Public User Identity (one or more records)
    impu_list = []
    rec_count = scc.record_count('6f04')
    for i in range(1, rec_count + 1):
        rec_hex, sw = scc.read_record('6f04', i)
        impu = decode_ber_tlv_80(rec_hex)
        if impu:
            impu_list.append(impu)
            print(f"  IMPU[{i}]: {impu}")
    result['impu_list'] = impu_list
    result['impu'] = impu_list[0] if impu_list else None  # Primary IMPU

    # Read EF.P-CSCF — P-CSCF Address (may be empty on some SIMs)
    pcscf_list = []
    try:
        rec_count = scc.record_count('6f09')
        for i in range(1, rec_count + 1):
            rec_hex, sw = scc.read_record('6f09', i)
            addr = decode_pcscf_record(rec_hex)
            if addr:
                pcscf_list.append(addr)
                print(f"  P-CSCF[{i}]: {addr}")
    except Exception as e:
        print(f"  P-CSCF: not available ({e})")
    result['pcscf_list'] = pcscf_list

    tp.disconnect()
    return result

def decode_ber_tlv_80(hex_str: str) -> str:
    """Decode BER-TLV with tag 0x80: extract UTF-8 string value."""
    raw = h2b(hex_str)
    if len(raw) < 2 or raw[0] != 0x80:
        return hex_str  # fallback
    length = raw[1]
    value = raw[2:2+length]
    return value.decode('utf-8', errors='replace')

def decode_pcscf_record(hex_str: str) -> str:
    """Decode EF.P-CSCF record: BER-TLV 0x80 containing type + address."""
    raw = h2b(hex_str)
    if len(raw) < 3 or raw[0] != 0x80:
        return None
    length = raw[1]
    value = raw[2:2+length]
    addr_type = value[0]
    addr_data = value[1:]
    if addr_type == 0:    # FQDN
        return addr_data.decode('utf-8', errors='replace')
    elif addr_type == 1:  # IPv4
        return '.'.join(str(b) for b in addr_data)
    elif addr_type == 2:  # IPv6
        import ipaddress
        return str(ipaddress.IPv6Address(addr_data))
    return None

if __name__ == '__main__':
    isim_data = read_isim(slot=0)
    print(f"\nExtracted ISIM data: {isim_data}")
```

### Notes
- **Carrier SIMs**: Most modern carrier SIMs include an ISIM application. If EF.P-CSCF is empty, use Step 2 fallback methods.
- **PIN verification**: If the SIM has PIN1 enabled, you must verify it before reading files. Use `scc.verify_chv(1, pin)` or disable PIN1 on the card.
- **Programmable SIMs** (sysmoISIM-SJA2/SJA5): You write the ISIM files yourself via `pySim-shell` or `pySim-prog.py`. This is for test networks only.

---

## Step 2: Discover P-CSCF Address

### Goal
Determine the SIP proxy (P-CSCF) to send the SIP REGISTER to. This is discovered via a priority chain of methods.

### Discovery Methods (Priority Order)

| Priority | Method | Source | Reliability |
|----------|--------|--------|-------------|
| 1 | ISIM EF.P-CSCF | SIM card | ✅ Best — carrier-provisioned |
| 2 | ACS XML `LBO_P-CSCF_Address` | HTTP provisioning | ✅ Good — if ACS reachable |
| 3 | PDP Context PCO | Cellular attach | ⚠️ Only on cellular modem |
| 4 | DHCP option (IMS APN) | DHCP server | ⚠️ Network-dependent |
| 5 | DNS NAPTR/SRV | DNS lookup | ⚠️ Fallback |

### Method 1: ISIM EF.P-CSCF (from Step 1)
Already extracted in Step 1. If the list is non-empty, use the first entry.

### Method 2: ACS XML Provisioning
Retrieve RCS configuration from the carrier's Auto Configuration Server:

```python
def discover_pcscf_via_acs(mcc: str, mnc: str, imsi: str, imei: str) -> str:
    """Discover P-CSCF via ACS XML provisioning."""
    import requests
    import xml.etree.ElementTree as ET

    # Construct ACS URL from MCC/MNC (GSMA convention)
    acs_url = f"https://config.rcs.mnc{mnc}.mcc{mcc}.pub.3gppnetwork.org/"
    params = {
        'IMSI': imsi,
        'IMEI': imei,
        'rcs_version': '5.1B',
        'rcs_profile': 'up_2.4',
        'client_version': 'headless-rcs-1.0',
        'client_vendor': 'test',
        'terminal_vendor': 'pcsc-reader',
        'terminal_model': 'headless',
        'terminal_sw_version': '1.0',
    }

    try:
        resp = requests.get(acs_url, params=params, timeout=10)
        if resp.status_code != 200:
            return None

        # Parse OMA CP XML
        root = ET.fromstring(resp.text)
        # Look for LBO_P-CSCF_Address characteristic
        for char in root.iter('characteristic'):
            if char.get('type') == 'LBO_P-CSCF_Address':
                for parm in char.findall('parm'):
                    if parm.get('name') == 'Address':
                        return parm.get('value')
    except Exception as e:
        print(f"  ACS lookup failed: {e}")
    return None
```

### Method 3: DNS NAPTR/SRV Discovery

```python
def discover_pcscf_via_dns(domain: str) -> str:
    """Discover P-CSCF via DNS NAPTR + SRV records."""
    import dns.resolver

    # Step 1: NAPTR lookup on the IMS domain
    try:
        naptrs = dns.resolver.resolve(domain, 'NAPTR')
        for naptr in naptrs:
            # Look for sip+D2U or sip+D2T service field
            service = str(naptr.service)
            if 'sip' in service.lower():
                replacement = str(naptr.replacement).rstrip('.')
                # Step 2: SRV lookup on the replacement
                srvs = dns.resolver.resolve(replacement, 'SRV')
                for srv in srvs:
                    target = str(srv.target).rstrip('.')
                    port = srv.port
                    return f"{target}:{port}"
    except Exception as e:
        print(f"  DNS discovery failed: {e}")
    return None

# Example:
# domain = "ims.mnc001.mcc001.3gppnetwork.org"
# pcscf = discover_pcscf_via_dns(domain)
```

### Full Discovery Chain

```python
def discover_pcscf(isim_data: dict, mcc: str, mnc: str,
                   imsi: str, imei: str) -> str:
    """Try all P-CSCF discovery methods in priority order."""
    # 1. From ISIM
    if isim_data.get('pcscf_list'):
        return isim_data['pcscf_list'][0]

    # 2. From ACS
    pcscf = discover_pcscf_via_acs(mcc, mnc, imsi, imei)
    if pcscf:
        return pcscf

    # 3. From DNS
    domain = isim_data.get('domain', f'ims.mnc{mnc}.mcc{mcc}.3gppnetwork.org')
    pcscf = discover_pcscf_via_dns(domain)
    if pcscf:
        return pcscf

    raise RuntimeError("Cannot discover P-CSCF via any method")
```

### Notes
- The ACS URL format `config.rcs.mnc{MNC}.mcc{MCC}.pub.3gppnetwork.org` may not resolve for all carriers. Some use a different subdomain convention.
- DNS NAPTR/SRV requires the carrier to publish these records. Many don't.
- **For Google Jibe (carrier RCS)**: The P-CSCF address comes from the carrier's ACS, which may redirect to a Jibe-hosted endpoint. The SIP stack still works the same way.
- **For Google Guest (OTT)**: There is no standard P-CSCF — Google's proprietary flow is used instead. This recipe does NOT cover Google Guest.

---

## Step 3: SIP REGISTER → Get 401 Challenge

### Goal
Send an initial SIP REGISTER (without credentials) to the P-CSCF. The S-CSCF responds with a `401 Unauthorized` containing a `WWW-Authenticate` header with the AKA challenge (RAND + AUTN encoded in the nonce).

### SIP REGISTER Format

```
REGISTER sip:ims.mnc001.mcc001.3gppnetwork.org SIP/2.0
Via: SIP/2.0/UDP 192.168.1.100:5060;branch=z9hG4bK776asdhds
Max-Forwards: 70
From: <sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org>;tag=1731906
To: <sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org>
Call-ID: 1731906@192.168.1.100
CSeq: 1 REGISTER
Contact: <sip:001010123456789@192.168.1.100:5060>;
  +sip.instance="<urn:gsma:imei:35469106-056673-0>";
  +g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.msg",
  +g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.session"
Expires: 600000
Authorization: Digest username="001010123456789@ims.mnc001.mcc001.3gppnetwork.org",
  realm="ims.mnc001.mcc001.3gppnetwork.org",
  nonce="",
  uri="sip:ims.mnc001.mcc001.3gppnetwork.org",
  response=""
Content-Length: 0
```

### Expected 401 Response

```
SIP/2.0 401 Unauthorized
Via: SIP/2.0/UDP 192.168.1.100:5060;branch=z9hG4bK776asdhds
From: <sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org>;tag=1731906
To: <sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org>;tag=T3E04A4B5
Call-ID: 1731906@192.168.1.100
CSeq: 1 REGISTER
WWW-Authenticate: Digest realm="ims.mnc001.mcc001.3gppnetwork.org",
  nonce="qlWqVapVqlWqVapVqlWqVUUQA5HEt9VVZ3t1TM221cg=",
  qop="auth",
  opaque="MTcyMjU3ODA2NDo=SU1TLVNJUCBTZXJ2ZXI=",
  algorithm=AKAv1-MD5
Content-Length: 0
```

### Code: Send Initial REGISTER and Parse 401

```python
import socket
import re
import base64

def send_register_and_get_challenge(impi: str, impu: str, domain: str,
                                     pcscf_addr: str, pcscf_port: int = 5060,
                                     local_ip: str = "192.168.1.100",
                                     local_port: int = 5060) -> dict:
    """Send initial SIP REGISTER, receive 401, extract RAND/AUTN from nonce."""
    branch = "z9hG4bK776asdhds"
    call_id = "1731906@" + local_ip
    tag = "1731906"

    register_msg = (
        f"REGISTER sip:{domain} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch={branch}\r\n"
        f"Max-Forwards: 70\r\n"
        f"From: <sip:{impi.split('@')[0]}@{domain}>;tag={tag}\r\n"
        f"To: <sip:{impi.split('@')[0]}@{domain}>\r\n"
        f"Call-ID: {call_id}\r\n"
        f"CSeq: 1 REGISTER\r\n"
        f"Contact: <sip:{impi.split('@')[0]}@{local_ip}:{local_port}>\r\n"
        f"Expires: 600000\r\n"
        f"Authorization: Digest username=\"{impi}\", realm=\"{domain}\", "
        f"nonce=\"\", uri=\"sip:{domain}\", response=\"\"\r\n"
        f"Content-Length: 0\r\n\r\n"
    )

    # Send via UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((local_ip, local_port))
    sock.sendto(register_msg.encode(), (pcscf_addr, pcscf_port))

    # Receive response
    sock.settimeout(5.0)
    data, addr = sock.recvfrom(4096)
    response = data.decode()

    # Parse 401 Unauthorized
    if "401" not in response and "407" not in response:
        raise RuntimeError(f"Expected 401, got: {response[:200]}")

    # Extract WWW-Authenticate header parameters
    www_auth = re.search(r'WWW-Authenticate:\s*Digest\s+(.*?)(?:\r\n|\n)',
                         response, re.DOTALL)
    if not www_auth:
        raise RuntimeError("No WWW-Authenticate header found")

    auth_params = {}
    # Multi-line header continuation — join lines
    auth_text = www_auth.group(1).replace('\r\n ', '').replace('\n ', '')
    for match in re.finditer(r'(\w+)="?([^",]+)"?', auth_text):
        auth_params[match.group(1)] = match.group(2)

    # Decode nonce to extract RAND and AUTN
    nonce_b64 = auth_params.get('nonce', '')
    nonce_bytes = base64.b64decode(nonce_b64)

    # Per RFC 3310 Figure 1: nonce = Base64(RAND || AUTN || server_data)
    # RAND = 16 bytes, AUTN = 16 bytes
    rand_bytes = nonce_bytes[:16]
    autn_bytes = nonce_bytes[16:32]

    challenge = {
        'nonce': nonce_b64,
        'realm': auth_params.get('realm', domain),
        'algorithm': auth_params.get('algorithm', 'AKAv1-MD5'),
        'qop': auth_params.get('qop', 'auth'),
        'opaque': auth_params.get('opaque', ''),
        'rand_hex': rand_bytes.hex(),
        'autn_hex': autn_bytes.hex(),
    }

    print(f"  Algorithm: {challenge['algorithm']}")
    print(f"  RAND: {challenge['rand_hex']}")
    print(f"  AUTN: {challenge['autn_hex']}")

    sock.close()
    return challenge
```

### Important Notes on the Nonce
- Per RFC 3310 Section 3.2, the nonce is `Base64(RAND || AUTN || optional_server_data)`.
- RAND is always 16 bytes. AUTN is always 16 bytes.
- Some carriers include additional server-specific data after the first 32 bytes. This is opaque to the client.
- The `opaque` parameter in the 401 response is separate from the nonce and MUST be echoed back in the REGISTER.
- If `qop="auth"` is present, you MUST include `cnonce` and `nc` fields in the Authorization header.

---

## Step 4: POST RAND+AUTN to sim-rest-server → Get RES+CK+IK

### Goal
Send the RAND and AUTN from the 401 challenge to the pySim `sim-rest-server`, which runs the AUTHENTICATE APDU against the physical SIM card's ISIM application. The card computes RES, CK, and IK using its secret key K and the MILENAGE algorithm.

### Starting sim-rest-server

```bash
# Install dependencies
pip3 install pyscard pyosmocom construct klein

# CRITICAL: Patch sim-rest-server.py to select ISIM instead of USIM
# In the auth() method, change:
#   card.select_adf_by_aid(adf='usim')
# to:
#   app = content.get('app', 'usim')  # Support 'isim' via query
#   card.select_adf_by_aid(adf=app)
#
# Then start with:
python3 contrib/sim-rest-server.py -H 0.0.0.0 -p 8000
```

**CRITICAL**: The stock `sim-rest-server.py` hardcodes `adf='usim'`. You MUST patch it to select ADF.ISIM (`a0000000871004`) for IMS AKA authentication. See `pysim-sim-auth-rest-audit-report.md` Section 6.3 for the exact patch.

### Code: Call sim-rest-server

```python
import requests

SIM_REST_URL = "http://localhost:8000/sim-auth-api/v1/slot/0"

def sim_auth_akav1(rand_hex: str, autn_hex: str, slot: int = 0) -> dict:
    """
    Authenticate RAND+AUTN against the ISIM on the SIM card
    via pySim's sim-rest-server REST API.

    Returns: {res, ck, ik, kc} on success, or {auts} on sync failure.
    """
    url = f"http://localhost:8000/sim-auth-api/v1/slot/{slot}"
    payload = {
        "rand": rand_hex,
        "autn": autn_hex,
        "app": "isim"  # Requires patched sim-rest-server
    }

    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    result = resp.json()

    if "synchronisation_failure" in result:
        auts = result["synchronisation_failure"]["auts"]
        print(f"  ⚠ SQN sync failure! AUTS={auts}")
        # Must re-REGISTER with AUTS to trigger HSS re-sync
        # (The S-CSCF will generate new RAND/AUTN with updated SQN)
        return {"sync_failure": True, "auts": auts}

    if "successful_3g_authentication" in result:
        auth = result["successful_3g_authentication"]
        print(f"  ✅ AKA auth success!")
        print(f"     RES: {auth['res']}")
        print(f"     CK:  {auth['ck']}")
        print(f"     IK:  {auth['ik']}")
        if 'kc' in auth:
            print(f"     Kc:  {auth['kc']}")
        return {
            "res_hex": auth["res"],
            "ck_hex":  auth["ck"],
            "ik_hex":  auth["ik"],
            "kc_hex":  auth.get("kc"),
        }

    raise RuntimeError(f"Unexpected SIM auth response: {result}")
```

### Handling Synchronisation Failure

If the HSS's SQN has drifted too far from the SIM's SQN, the SIM returns AUTS instead of RES. Handle this by:

1. Sending a new REGISTER with `Authorization: ... auts=<AUTS>` to the P-CSCF.
2. The S-CSCF forwards AUTS to the HSS.
3. The HSS resynchronizes its SQN and generates fresh RAND/AUTN.
4. The S-CSCF sends a new 401 with the fresh challenge.
5. Retry from Step 3.

```python
def build_auts_register(impi, domain, nonce, realm, auts_hex, opaque,
                        cnonce, nc, call_id, local_ip, local_port, tag):
    """Build SIP REGISTER with AUTS for SQN re-synchronisation."""
    # Similar to the authenticated REGISTER below, but with auts parameter
    # instead of response. The S-CSCF will re-challenge with fresh RAND/AUTN.
    return (
        f"REGISTER sip:{domain} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch=z9hG4bK-auts\r\n"
        f"Max-Forwards: 70\r\n"
        f"From: <sip:{impi.split('@')[0]}@{domain}>;tag={tag}\r\n"
        f"To: <sip:{impi.split('@')[0]}@{domain}>\r\n"
        f"Call-ID: {call_id}\r\n"
        f"CSeq: 2 REGISTER\r\n"
        f"Authorization: Digest username=\"{impi}\", realm=\"{realm}\", "
        f"nonce=\"{nonce}\", uri=\"sip:{domain}\", "
        f"auts=\"{auts_hex}\", algorithm=AKAv1-MD5, "
        f"opaque=\"{opaque}\"\r\n"
        f"Content-Length: 0\r\n\r\n"
    )
```

---

## Step 5: Compute AKA-Digest Response per RFC 3310

### Goal
Compute the SIP digest `response` value from RES, CK, and IK using the AKAv1-MD5 algorithm specified in RFC 3310 and RFC 2617.

### The AKAv1-MD5 Algorithm (Step by Step)

This is the **single most critical computation** in the entire recipe. Getting it wrong means registration failure.

**Per RFC 3310 Section 3.3:**
> The resulting AKA RES parameter is treated as a "password" when calculating the response directive of RFC 2617.

**The computation has three stages:**

#### Stage 1: H(A1)
```
H(A1) = MD5( username ":" realm ":" RES )
```
Where:
- `username` = the IMPI (e.g., `001010123456789@ims.mnc001.mcc001.3gppnetwork.org`)
- `realm` = from the 401 challenge (e.g., `ims.mnc001.mcc001.3gppnetwork.org`)
- `RES` = the raw RES bytes from the SIM card, treated as the "password"

**CRITICAL**: RES is a binary/hex value. When computing H(A1), RES is used as its **hex string representation** (ASCII), not the raw binary bytes. This is a common source of bugs.

#### Stage 2: H(A2)
```
H(A2) = MD5( "REGISTER" ":" digest-uri )
```
Where:
- `"REGISTER"` = the SIP method (literal string)
- `digest-uri` = the `uri` parameter from the Authorization header (e.g., `sip:ims.mnc001.mcc001.3gppnetwork.org`)

#### Stage 3: Final Response
**Without qop:**
```
response = MD5( H(A1) ":" nonce ":" H(A2) )
```

**With qop="auth":**
```
response = MD5( H(A1) ":" nonce ":" nc ":" cnonce ":" qop ":" H(A2) )
```
Where:
- `nonce` = from the 401 challenge (the Base64 string as-is, including `=` padding)
- `nc` = nonce count (8 hex digits, starts at `00000001`)
- `cnonce` = client nonce (random hex string, typically 8 chars)
- `qop` = `"auth"` (from the 401 challenge)

### Code: Compute AKA-Digest Response

```python
import hashlib
import os

def compute_aka_digest_response(
    impi: str,
    realm: str,
    res_hex: str,
    digest_uri: str,
    nonce_b64: str,
    algorithm: str = "AKAv1-MD5",
    qop: str = None,
    nc: str = "00000001",
    cnonce: str = None,
) -> str:
    """
    Compute the SIP Digest AKA response per RFC 3310 / RFC 2617.

    Args:
        impi: IMS Private Identity (username for auth)
        realm: Authentication realm from 401 challenge
        res_hex: RES value from SIM auth (hex string)
        digest_uri: SIP URI from Authorization header
        nonce_b64: Base64-encoded nonce from 401 challenge
        algorithm: AKAv1-MD5 or AKAv2-MD5
        qop: Quality of Protection ("auth" or None)
        nc: Nonce count (8 hex digits)
        cnonce: Client nonce (random hex string)

    Returns:
        32-char lowercase hex MD5 digest string (the "response" value)
    """
    if cnonce is None:
        cnonce = os.urandom(4).hex()  # 8 hex chars

    # Stage 1: H(A1) = MD5(username:realm:RES)
    # RES is treated as "password" — use the hex string as ASCII
    a1_str = f"{impi}:{realm}:{res_hex}"
    ha1 = hashlib.md5(a1_str.encode('ascii')).hexdigest()
    print(f"  H(A1) = MD5({a1_str[:60]}...) = {ha1}")

    # Stage 2: H(A2) = MD5(REGISTER:digest-uri)
    a2_str = f"REGISTER:{digest_uri}"
    ha2 = hashlib.md5(a2_str.encode('ascii')).hexdigest()
    print(f"  H(A2) = MD5({a2_str}) = {ha2}")

    # Stage 3: Final response
    if qop and qop.lower() == "auth":
        response_str = f"{ha1}:{nonce_b64}:{nc}:{cnonce}:{qop}:{ha2}"
    else:
        response_str = f"{ha1}:{nonce_b64}:{ha2}"

    response = hashlib.md5(response_str.encode('ascii')).hexdigest()
    print(f"  response = MD5({response_str[:80]}...) = {response}")

    return response, cnonce, nc
```

### Common Pitfalls in AKA-Digest Computation

| Pitfall | Wrong | Right |
|---------|-------|-------|
| RES encoding | Using raw binary RES bytes | Using hex string of RES as ASCII |
| Username format | Using IMPU (sip:...) | Using IMPI (NAI without sip: prefix) |
| Realm mismatch | Different realm in H(A1) vs 401 | Must match the realm from 401 exactly |
| Nonce padding | Stripping `=` from Base64 | Preserve the Base64 nonce exactly as-is |
| Case sensitivity | Uppercase hex in response | Lowercase hex MD5 output |
| qop absent but nc/cnonce included | Including nc/cnonce when no qop | Omit nc/cnonce if qop is not present |

### AKAv2-MD5 Difference

AKAv2-MD5 (RFC 4169) differs only in how H(A1) is computed:

```
# AKAv2-MD5:
H(A1) = MD5( MD5(username:realm:RES) ":" CK ":" IK )
```

For AKAv2, concatenate the hex of H(A1_base) + CK + IK, then MD5 that.
Most carriers use AKAv1-MD5. AKAv2 is used in some 5G deployments.

---

## Step 6: Send Authenticated SIP REGISTER → 200 OK

### Goal
Send the second SIP REGISTER with the computed AKA-Digest response in the `Authorization` header. On success, receive `200 OK`.

### Code: Build and Send Authenticated REGISTER

```python
def send_authenticated_register(
    impi: str, impu: str, domain: str,
    pcscf_addr: str, pcscf_port: int,
    local_ip: str, local_port: int,
    challenge: dict,
    auth_data: dict,
    call_id: str, tag: str,
) -> dict:
    """Send SIP REGISTER with AKA-Digest authentication."""
    response, cnonce, nc = compute_aka_digest_response(
        impi=impi,
        realm=challenge['realm'],
        res_hex=auth_data['res_hex'],
        digest_uri=f"sip:{domain}",
        nonce_b64=challenge['nonce'],
        algorithm=challenge['algorithm'],
        qop=challenge.get('qop'),
    )

    # Build Authorization header
    auth_header_parts = [
        f'Digest username="{impi}"',
        f'realm="{challenge["realm"]}"',
        f'nonce="{challenge["nonce"]}"',
        f'uri="sip:{domain}"',
        f'response="{response}"',
        f'algorithm={challenge["algorithm"]}',
    ]
    if challenge.get('qop'):
        auth_header_parts.append(f'qop={challenge["qop"]}')
        auth_header_parts.append(f'nc={nc}')
        auth_header_parts.append(f'cnonce="{cnonce}"')
    if challenge.get('opaque'):
        auth_header_parts.append(f'opaque="{challenge["opaque"]}"')

    auth_header = ", ".join(auth_header_parts)

    # Build full REGISTER message
    register_msg = (
        f"REGISTER sip:{domain} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch=z9hG4bK-auth1\r\n"
        f"Max-Forwards: 70\r\n"
        f"From: <{impu}>;tag={tag}\r\n"
        f"To: <{impu}>\r\n"
        f"Call-ID: {call_id}\r\n"
        f"CSeq: 2 REGISTER\r\n"
        f"Contact: <sip:{impi.split('@')[0]}@{local_ip}:{local_port}>;"
        f'+sip.instance="<urn:gsma:imei:00000000-000000-0>";'
        f'+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.msg",'
        f'+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.session"\r\n'
        f"Expires: 600000\r\n"
        f"Authorization: {auth_header}\r\n"
        f"Content-Length: 0\r\n\r\n"
    )

    # Send via UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((local_ip, local_port + 1))  # Use different port for 2nd REGISTER
    sock.sendto(register_msg.encode(), (pcscf_addr, pcscf_port))
    sock.settimeout(5.0)

    data, addr = sock.recvfrom(4096)
    response_text = data.decode()
    sock.close()

    # Parse 200 OK
    if "200 OK" in response_text:
        print("  ✅ IMS Registration successful!")
        # Extract important headers from 200 OK
        result = {'registered': True}

        # P-Associated-URI: lists all registered IMPUs
        associated = re.findall(r'P-Associated-URI:\s*<([^>]+)>', response_text)
        result['associated_uris'] = associated

        # Service-Route: route for subsequent requests
        routes = re.findall(r'Service-Route:\s*<([^>]+)>', response_text)
        result['service_routes'] = routes

        # Expires from Contact header
        expire_match = re.search(r'expires\s*=\s*(\d+)', response_text, re.IGNORECASE)
        if expire_match:
            result['expires'] = int(expire_match.group(1))

        print(f"  Associated URIs: {associated}")
        print(f"  Service-Route: {routes}")
        return result
    else:
        print(f"  ❌ Registration failed: {response_text[:200]}")
        return {'registered': False, 'response': response_text}
```

### Using PJSIP for IMS Registration (Recommended Alternative)

Writing a raw SIP stack is error-prone. **PJSIP** (C library with Python bindings via `pjsua2`) has built-in AKAv1-MD5 / AKAv2-MD5 support:

```python
# PJSIP approach (requires building with PJSIP_HAS_DIGEST_AKA_AUTH=1)
# The AKA callback computes RES/CK/IK from the challenge
# and returns them to PJSIP which handles the digest computation

import pjsua2

class RcsAccount(pjsua2.Account):
    def __init__(self):
        super().__init__()

    def onRegStarted(self, param):
        print(f"Registration started: {param.statusText}")

    def onRegState(self, param):
        print(f"Registration state: code={param.code}, reason={param.reason}")

# Configure account with AKA credentials
acc_cfg = pjsua2.AccountConfig()
acc_cfg.idUri = "sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org"
acc_cfg.regConfig.registrarUri = "sip:pcscf.ims.mnc001.mcc001.3gppnetwork.org"

# AKA credential
cred = pjsua2.AuthCredInfo()
cred.scheme = "digest"
cred.realm = "*"
cred.username = "001010123456789@ims.mnc001.mcc001.3gppnetwork.org"
cred.dataType = pjsua2.PJSIP_CRED_DATA_PLAIN_PASSWD | pjsua2.PJSIP_CRED_DATA_EXT_AKA
cred.akaK = "841EAD87BC9D974ECA1C167409357601"  # K (secret key)
cred.akaOp = "3211CACDD64F51C3FD3013ECD9A582A0"  # OP
cred.akaAmf = "8000"  # AMF
acc_cfg.sipConfig.authCreds.append(cred)

# Note: If using a real SIM card (not known K/OP), you need the
# AKA callback to proxy the challenge to sim-rest-server.
# PJSIP's AKA callback model requires implementing pjsip_auth_aka_cb.
```

**Important**: PJSIP's AKA support requires the SIM's secret key K and OP/OPc to be provided directly. If you're using a real carrier SIM (where K/OP are unknown), you need to implement the AKA callback that proxies the RAND/AUTN challenge to sim-rest-server and returns RES/CK/IK.

---

## Step 7: SUBSCRIBE Presence, PUBLISH Capabilities

### Goal
After successful registration, announce the client's RCS capabilities and subscribe to other users' presence/capabilities.

### SUBSCRIBE for Presence (RCS-e / Legacy)

```
SUBSCRIBE sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org SIP/2.0
From: <sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org>;tag=xxx
To: <sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org>
Call-ID: sub-pres-001@192.168.1.100
CSeq: 1 SUBSCRIBE
Contact: <sip:001010123456789@192.168.1.100:5060>
Event: presence
Accept: application/pidf+xml, application/rlmi+xml
Expires: 3600
Content-Length: 0
```

### PUBLISH Capabilities (Feature Tags)

```
PUBLISH sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org SIP/2.0
From: <sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org>;tag=xxx
To: <sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org>
Call-ID: pub-cap-001@192.168.1.100
CSeq: 1 PUBLISH
Event: presence
Content-Type: application/pidf+xml
Expires: 3600
Content-Length: ...

<?xml version="1.0" encoding="UTF-8"?>
<presence xmlns="urn:ietf:params:xml:ns:pidf"
          entity="sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org">
  <tuple id="rcs">
    <status><basic>open</basic></status>
    <contact>sip:001010123456789@192.168.1.100:5060</contact>
    <note>Available</note>
  </tuple>
</presence>
```

### Universal Profile: SIP OPTIONS for Capability Discovery

Modern RCS (UP 2.0+) uses SIP OPTIONS instead of presence:

```python
def send_capability_query(target_impu: str, my_impu: str, domain: str,
                          service_route: str, local_ip: str, local_port: int):
    """Query a contact's RCS capabilities via SIP OPTIONS."""
    options_msg = (
        f"OPTIONS {target_impu} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch=z9hG4bK-cap1\r\n"
        f"Max-Forwards: 70\r\n"
        f"From: <{my_impu}>;tag=capq\r\n"
        f"To: <{target_impu}>\r\n"
        f"Call-ID: capq-{os.urandom(4).hex()}@{local_ip}\r\n"
        f"CSeq: 1 OPTIONS\r\n"
        f"Accept-Contact: *;+g.3gpp.icsi-ref="
        f'"urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.msg"\r\n'
        f"Accept-Contact: *;+g.3gpp.icsi-ref="
        f'"urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.session"\r\n'
        f"Content-Length: 0\r\n\r\n"
    )
    # Send via service-route path...
```

The 200 OK response's `Contact` header contains feature tags indicating the target's capabilities (e.g., `+g.3gpp.icsi-ref`, `+g.3gpp.iari-ref`).

---

## Step 8: Send SIP MESSAGE (Pager-Mode) for 1-1 Chat

### Goal
Send a standalone RCS text message using SIP MESSAGE (pager-mode). This is the simplest messaging mode — no session setup required.

### Message Format

```
MESSAGE sip:+14448880011@ims.mnc001.mcc001.3gppnetwork.org;user=phone SIP/2.0
P-Preferred-Service: urn:urn-7:3gpp-service.ims.icsi.oma.cpm.msg
Contribution-ID: 477b66ae9662e3ad18549bf5dabf9d26d5e707ca
Conversation-ID: 1710887c7ca47dc2c1274c11673eb0df5a604fd3
P-Preferred-Identity: <sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org>
Request-Disposition: no-fork
CSeq: 1 MESSAGE
Max-Forwards: 70
Route: <sip:pcscf.ims.mnc001.mcc001.3gppnetwork.org;lr>
Accept-Contact: *;+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.msg"
Content-Type: message/cpim
From: <sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org>;tag=msg1
Call-ID: msg1@192.168.1.100
To: <sip:+14448880011@ims.mnc001.mcc001.3gppnetwork.org;user=phone>
Via: SIP/2.0/UDP 192.168.1.100:5060;branch=z9hG4bK-msg1
Content-Length: 322

From: <sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org>
To: <sip:+14448880011@ims.mnc001.mcc001.3gppnetwork.org;user=phone>
DateTime: 2026-05-15T12:00:00Z
NS: imdn <urn:ietf:params:imdn>
imdn.Message-ID: msg-001-abc
imdn.Disposition-Notification: positive-delivery, display

Content-type: text/plain;charset=UTF-8
Content-Length: 13

Hello world!
```

### Code: Send RCS Message

```python
import uuid
from datetime import datetime, timezone

def send_rcs_message(
    sender_impu: str,
    recipient_impu: str,
    text: str,
    domain: str,
    pcscf_addr: str,
    local_ip: str,
    local_port: int = 5060,
    conversation_id: str = None,
) -> str:
    """Send a pager-mode RCS message via SIP MESSAGE."""
    contribution_id = uuid.uuid4().hex
    if not conversation_id:
        conversation_id = uuid.uuid4().hex
    message_id = f"msg-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build CPIM body (inner message)
    cpim_body = (
        f"From: <{sender_impu}>\r\n"
        f"To: <{recipient_impu}>\r\n"
        f"DateTime: {now}\r\n"
        f"NS: imdn <urn:ietf:params:imdn>\r\n"
        f"imdn.Message-ID: {message_id}\r\n"
        f"imdn.Disposition-Notification: positive-delivery, display\r\n"
        f"\r\n"
        f"Content-type: text/plain;charset=UTF-8\r\n"
        f"Content-Length: {len(text.encode('utf-8'))}\r\n"
        f"\r\n"
        f"{text}"
    )

    # Build SIP MESSAGE
    sip_msg = (
        f"MESSAGE {recipient_impu} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch=z9hG4bK-{contribution_id[:8]}\r\n"
        f"Max-Forwards: 70\r\n"
        f"From: <{sender_impu}>;tag=msg{contribution_id[:6]}\r\n"
        f"To: <{recipient_impu}>\r\n"
        f"Call-ID: {contribution_id}@{local_ip}\r\n"
        f"CSeq: 1 MESSAGE\r\n"
        f"Contact: <sip:{sender_impu.split('@')[0]}@{local_ip}:{local_port}>\r\n"
        f"P-Preferred-Service: urn:urn-7:3gpp-service.ims.icsi.oma.cpm.msg\r\n"
        f"Contribution-ID: {contribution_id}\r\n"
        f"Conversation-ID: {conversation_id}\r\n"
        f"P-Preferred-Identity: <{sender_impu}>\r\n"
        f"Request-Disposition: no-fork\r\n"
        f"Accept-Contact: *;+g.3gpp.icsi-ref="
        f'"urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.msg"\r\n'
        f"Content-Type: message/cpim\r\n"
        f"Content-Length: {len(cpim_body.encode('utf-8'))}\r\n"
        f"\r\n"
        f"{cpim_body}"
    )

    # Send via UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(sip_msg.encode(), (pcscf_addr, 5060))
    sock.settimeout(5.0)
    data, addr = sock.recvfrom(4096)
    response = data.decode()
    sock.close()

    if "200 OK" in response:
        print(f"  ✅ Message sent! Contribution-ID: {contribution_id}")
        return contribution_id
    else:
        print(f"  ❌ Message failed: {response[:200]}")
        return None
```

### Key SIP Headers for RCS Messaging

| Header | Value | Purpose |
|--------|-------|---------|
| `P-Preferred-Service` | `urn:urn-7:3gpp-service.ims.icsi.oma.cpm.msg` | Identifies as RCS standalone message |
| `Contribution-ID` | UUID | Unique per message; correlates to a single contribution |
| `Conversation-ID` | UUID | Groups messages in a conversation thread |
| `Request-Disposition: no-fork` | Prevents forking to multiple devices | Standard for 1-1 messages |
| `Content-Type: message/cpim` | CPIM format | Required wrapper for RCS messages |
| `imdn.Disposition-Notification` | `positive-delivery, display` | Requests delivery and read receipts |

---

## Step 9: Handle Incoming SIP MESSAGE / MSRP INVITE

### Goal
Listen for and process incoming RCS messages — both pager-mode SIP MESSAGE and session-mode MSRP INVITE.

### Listening for Incoming Messages

```python
import select

class SipListener:
    """Simple SIP listener that receives incoming SIP messages."""

    def __init__(self, local_ip: str, local_port: int = 5060):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((local_ip, local_port))
        self.sock.setblocking(False)
        self.local_ip = local_ip
        self.local_port = local_port

    def listen(self, timeout: float = 1.0) -> list:
        """Poll for incoming SIP messages. Returns list of (method, msg_text)."""
        messages = []
        while True:
            ready = select.select([self.sock], [], [], timeout)
            if not ready[0]:
                break
            data, addr = self.sock.recvfrom(65535)
            msg = data.decode('utf-8', errors='replace')
            method = self._extract_method(msg)
            messages.append((method, msg, addr))
        return messages

    def _extract_method(self, msg: str) -> str:
        """Extract SIP method from request line or status code from response."""
        first_line = msg.split('\r\n')[0] if '\r\n' in msg else msg.split('\n')[0]
        parts = first_line.split()
        if parts[0].startswith('SIP/'):
            return f"Response_{parts[1]}"  # e.g., "Response_200"
        return parts[0]  # e.g., "MESSAGE", "INVITE", "OPTIONS"

    def respond_200_ok(self, msg_text: str, addr: tuple):
        """Send 200 OK response to a SIP request."""
        # Extract Via, From, To, Call-ID, CSeq from the request
        via = self._extract_header(msg_text, 'Via')
        from_hdr = self._extract_header(msg_text, 'From')
        to_hdr = self._extract_header(msg_text, 'To')
        call_id = self._extract_header(msg_text, 'Call-ID')
        cseq = self._extract_header(msg_text, 'CSeq')

        # Add tag to To header if not present
        if ';tag=' not in to_hdr:
            to_hdr += ';tag=resp'

        response = (
            f"SIP/2.0 200 OK\r\n"
            f"Via: {via}\r\n"
            f"From: {from_hdr}\r\n"
            f"To: {to_hdr}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq}\r\n"
            f"Content-Length: 0\r\n\r\n"
        )
        self.sock.sendto(response.encode(), addr)

    def _extract_header(self, msg: str, header_name: str) -> str:
        """Extract a SIP header value (handles line folding)."""
        pattern = rf'^{header_name}:\s*(.*?)(?=\r\n\S|\r\n$|\r\n\r\n|$)'
        match = re.search(pattern, msg, re.MULTILINE | re.DOTALL)
        if match:
            return match.group(1).replace('\r\n ', '').replace('\n ', '').strip()
        return ""
```

### Handling Incoming SIP MESSAGE (Pager-Mode)

```python
def handle_incoming_message(msg_text: str, sender_addr: tuple,
                            listener: SipListener):
    """Process an incoming SIP MESSAGE (RCS standalone message)."""
    # 1. Send 200 OK immediately
    listener.respond_200_ok(msg_text, sender_addr)

    # 2. Parse CPIM body
    content_type = listener._extract_header(msg_text, 'Content-Type')
    if 'message/cpim' not in content_type.lower():
        print(f"  ⚠ Non-CPIM message: {content_type}")
        return

    # Split SIP headers from body
    body_start = msg_text.find('\r\n\r\n')
    if body_start == -1:
        return
    cpim_body = msg_text[body_start + 4:]

    # Parse CPIM headers and inner content
    cpim_parts = cpim_body.split('\r\n\r\n', 1)
    cpim_headers = cpim_parts[0]
    inner_content = cpim_parts[1] if len(cpim_parts) > 1 else ""

    # Extract IMDN info
    imdn_msg_id = None
    for line in cpim_headers.split('\r\n'):
        if line.startswith('imdn.Message-ID:'):
            imdn_msg_id = line.split(':', 1)[1].strip()
        elif line.startswith('Content-Disposition: notification'):
            # This is a delivery/read receipt
            print(f"  📩 IMDN notification received!")
            parse_imdn_notification(inner_content)
            return

    # Extract actual text
    text = inner_content.split('\r\n\r\n', 1)[-1].strip() if '\r\n\r\n' in inner_content else inner_content.strip()
    print(f"  📨 RCS message: {text}")
    print(f"     IMDN Message-ID: {imdn_msg_id}")

    # 3. Send delivery receipt (IMDN)
    if imdn_msg_id:
        send_delivery_receipt(imdn_msg_id, sender_addr, listener)

def send_delivery_receipt(imdn_msg_id: str, original_sender: str,
                          listener: SipListener):
    """Send IMDN delivery notification back to the sender."""
    imdn_xml = (
        f'<?xml version="1.0" encoding="utf-8"?>\r\n'
        f'<imdn xmlns="urn:ietf:params:xml:ns:imdn">\r\n'
        f'  <message-id>{imdn_msg_id}</message-id>\r\n'
        f'  <delivery-notification>\r\n'
        f'    <status><delivered /></status>\r\n'
        f'  </delivery-notification>\r\n'
        f'</imdn>'
    )
    # Build CPIM + SIP MESSAGE for the receipt
    # (Similar to Step 8 but with Content-Disposition: notification
    #  and Content-Type: message/imdn+xml)
    # ... (omitted for brevity, follows same pattern)
```

### Handling Incoming MSRP INVITE (Session-Mode)

For session-mode chat, you receive a SIP INVITE with SDP offering an MSRP session:

```python
def handle_incoming_invite(msg_text: str, sender_addr: tuple,
                           listener: SipListener):
    """Process incoming SIP INVITE for MSRP chat session."""
    # 1. Send 200 OK with SDP answer
    # Parse SDP offer to get remote MSRP path
    body_start = msg_text.find('\r\n\r\n')
    sdp_offer = msg_text[body_start + 4:] if body_start != -1 else ""

    # Extract remote MSRP path from SDP a=path line
    msrp_path_match = re.search(r'a=path:(msrp://[^\s]+)', sdp_offer)

    # Build SDP answer with local MSRP endpoint
    local_msrp_port = 8880
    local_msrp_session = uuid.uuid4().hex[:8]
    sdp_answer = (
        f"v=0\r\n"
        f"o=- 1192 5963 IN IP4 {listener.local_ip}\r\n"
        f"s=-\r\n"
        f"c=IN IP4 {listener.local_ip}\r\n"
        f"t=0 0\r\n"
        f"m=message {local_msrp_port} TCP/MSRP *\r\n"
        f"a=accept-types:message/cpim application/im-iscomposing+xml\r\n"
        f"a=accept-wrapped-types:text/plain message/imdn+xml\r\n"
        f"a=path:msrp://{listener.local_ip}:{local_msrp_port}/{local_msrp_session};tcp\r\n"
        f"a=msrp-cema\r\n"
        f"a=setup:passive\r\n"
    )

    # Send 200 OK with SDP answer
    # (Build response with SDP answer, extract headers from INVITE)
    # ...

    # 2. Listen on local_msrp_port for TCP/MSRP connection
    # 3. Accept MSRP SEND messages from the remote party
    # 4. Send MSRP 200 OK for each received SEND
```

**Note**: Full MSRP handling requires a TCP listener for the MSRP media path, separate from the SIP signaling path. This is where libraries like `python3-msrplib` or a custom MSRP implementation are needed.

---

## Complete Libraries and Tools Table

### Required Software Stack

| Component | Library/Tool | Version | Language | Purpose |
|-----------|-------------|---------|----------|---------|
| **SIM Card Access** | `pysim` (pySim) | latest (git) | Python | PC/SC reader → ISIM file access + AKA auth |
| **SIM Auth REST API** | `sim-rest-server.py` | (pysim contrib) | Python | REST bridge for remote SIM auth |
| **PC/SC Driver** | `pcsc-lite` | 1.9+ | C | Linux PC/SC daemon |
| **SIP Stack (Option A)** | `pjsip` / `pjsua2` | 2.15+ | C/Python | Full SIP with built-in AKA auth |
| **SIP Stack (Option B)** | `python-sipsimple` | 0.8+ | Python | SIP+MSRP SDK, CPIM, IMDN |
| **SIP Stack (Option C)** | Custom (as shown above) | — | Python | Raw UDP SIP for learning/testing |
| **MSRP Stack** | `python3-msrplib` | latest | Python | MSRP session-mode messaging |
| **DNS Resolution** | `dnspython` | 2.4+ | Python | NAPTR/SRV DNS queries |
| **ACS HTTP Client** | `requests` | 2.31+ | Python | Fetch ACS XML config |
| **Cryptography** | `hashlib` (stdlib) | — | Python | MD5 for AKA-Digest |

### Hardware

| Component | Model | Cost | Purpose |
|-----------|-------|------|---------|
| PC/SC Reader | Omnikey 3121 / SCM SCR3310 | $20–50 | Single SIM access |
| Multi-Reader | sysmoOCTSIM | ~€200 | 8 SIM slots for farm |
| Programmable ISIM | sysmoISIM-SJA2 | ~€5–10/card | Self-provisioned test SIMs |
| Linux Host | Any x86/ARM | varies | Runs the headless client |

### PJSIP Build with AKA Support

```bash
# Build PJSIP with AKA authentication enabled
git clone https://github.com/pjsip/pjproject.git
cd pjproject

# Create config_site.h with AKA enabled
cat > pjlib/include/pj/config_site.h << 'EOF'
#define PJSIP_HAS_DIGEST_AKA_AUTH 1
#define PJ_HAS_SSL_SOCK 1
EOF

# Build
./configure && make dep && make
```

---

## The Single Hardest Technical Challenge: AKAv1-MD5 Digest Computation with Real SIM Cards

### The Problem

The AKA-Digest response computation (Step 5) is the **single hardest technical challenge** in building a headless RCS client. Here's why:

1. **No standard library implements it**: There is no Python library that takes a RAND/AUTN challenge from a SIP 401, proxies it to a SIM card, gets back RES/CK/IK, and computes the AKA-Digest response. You must assemble this pipeline yourself from three separate components (SIM auth, RFC 3310 digest, SIP stack).

2. **The SIM card is the only source of truth**: For real carrier SIMs, the secret key K and OP/OPc are **never exposed** outside the SIM's secure element. You cannot compute RES, CK, or IK without the SIM card performing the AUTHENTICATE APDU. This means the SIM card **must be online and accessible** for every re-registration.

3. **Nonce encoding pitfalls**: The nonce in the 401 challenge is Base64(RAND ‖ AUTN ‖ server_data). Decoding and splitting at the correct boundary (exactly 16 + 16 bytes) requires careful handling. Some carriers include extra server data after the first 32 bytes.

4. **RES encoding in H(A1)**: RFC 3310 states that RES is used as the "password" in the RFC 2617 digest formula. But RES is a hex value — should you hash the ASCII hex representation or the raw binary bytes? **Answer: the ASCII hex representation** (per 3GPP TS 33.203 and practical testing). Getting this wrong produces a wrong H(A1) and a wrong response.

5. **SQN synchronization**: The SIM's SQN counter must stay in sync with the HSS. If they drift apart, you get synchronisation failure (AUTS) and must handle the re-sync flow before you can register.

6. **IPSec SA establishment**: After successful AKA authentication, the P-CSCF and UE are supposed to establish IPSec Security Associations using CK and IK. Many carrier P-CSCFs **require** IPSec on the SIP signaling path. Without implementing the IPSec tunnel (using `Security-Client` / `Security-Server` header negotiation), some carriers will reject your registration.

### The Solution

**For the digest computation itself**, the code in Step 5 above is the complete solution. The critical insight is:

```
H(A1) = MD5(IMPI + ":" + realm + ":" + RES_hex_string)
```

Where `RES_hex_string` is the hex representation of RES as an ASCII string (not the binary bytes).

**For the SIM-OR-SIM challenge**, the architecture is:

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐     ┌─────────┐
│  SIP Stack   │────→│  AKA-Digest      │────→│sim-rest-     │────→│  ISIM   │
│  (pjsip or   │     │  Computation     │     │server.py     │     │  Card   │
│  raw socket) │←────│  (Step 5 code)   │←────│(POST RAND/   │←────│(AUTHEN- │
│              │     │                  │     │ AUTN → RES/  │     │ TICATE  │
│              │     │                  │     │ CK/IK)       │     │ APDU)   │
└─────────────┘     └──────────────────┘     └──────────────┘     └─────────┘
```

**For IPSec**, you have two options:

1. **Skip IPSec** (works on some carriers): Send `Require: sec-agree` and `Proxy-Require: sec-agree` in REGISTER, but don't actually establish IPSec. Some P-CSCFs will accept this for testing.

2. **Implement IPSec** (required for production carriers): Use `strongSwan` or Linux `ip xfrm` to establish IPSec SAs using CK and IK as key material. The `Security-Client` and `Security-Server` headers negotiate the algorithm and SPI values.

```bash
# IPSec SA using ip xfrm (Linux kernel)
# After getting CK and IK from SIM auth:
# CK + IK = 32 bytes of key material
# Split into encryption key and integrity key per negotiated algorithm

# Example for HMAC-MD5-96 + AES-CBC:
SPI_C=<from Security-Client>
SPI_S=<from Security-Server>
PORT_C=<client protected port>
PORT_S=<server protected port>

# Add inbound SA
ip xfrm state add src $P_CSCF_IP dst $LOCAL_IP proto esp spi $SPI_C \
  mode transport auth hmac(md5) $IK_HEX enc aes $CK_HEX

# Add outbound SA
ip xfrm state add src $LOCAL_IP dst $P_CSCF_IP proto esp spi $SPI_S \
  mode transport auth hmac(md5) $IK_HEX enc aes $CK_HEX

# Add SPs to filter port pairs
ip xfrm policy add src $LOCAL_IP dst $P_CSCF_IP sport $PORT_C dport $PORT_S \
  dir out tmpl proto esp mode transport
ip xfrm policy add src $P_CSCF_IP dst $LOCAL_IP sport $PORT_S dport $PORT_C \
  dir in tmpl proto esp mode transport
```

### Recommended Architecture for Production

For a production headless RCS system, use **PJSIP** with its AKA callback mechanism and route the AKA challenge through `sim-rest-server`:

```c
/* PJSIP AKA callback — proxies challenge to sim-rest-server */
static pj_status_t aka_compute_response(
    const pj_str_t *realm,
    const pj_str_t *username,
    const pj_str_t *nonce,      /* Base64(RAND||AUTN||data) */
    const pj_str_t *nc,
    const pj_str_t *cnonce,
    const pj_str_t *qop,
    pj_uint8_t res[PJSIP_AUTH_RESPONSE_LEN],
    int *res_len)
{
    /* 1. Decode nonce → extract RAND and AUTN */
    /* 2. HTTP POST to sim-rest-server with RAND, AUTN */
    /* 3. Parse response: get RES, CK, IK */
    /* 4. Compute H(A1) = MD5(username:realm:RES_hex) */
    /* 5. Compute H(A2) = MD5(REGISTER:uri) */
    /* 6. Compute response = MD5(H(A1):nonce:nc:cnonce:qop:H(A2)) */
    /* 7. Return response in res[] */
}
```

This gives you the reliability of PJSIP's SIP state machine with the flexibility of SIM-backed authentication.

---

## End-to-End Flow Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                    HEADLESS RCS CLIENT                               │
│                                                                      │
│  ┌─────┐   ┌──────────┐   ┌──────────┐   ┌─────────────────────┐   │
│  │ SIM │──→│ pySim    │──→│ sim-rest │──→│ SIP Stack (pjsip/   │   │
│  │ Card│   │ (PC/SC)  │   │ server   │   │ raw/custom)         │   │
│  │ in  │   │          │   │          │   │                     │   │
│  │Reader│  │ Read:    │   │ RAND/AUTN│   │ 1. REGISTER → 401  │   │
│  └─────┘   │ - IMPI   │   │    ↓     │   │ 2. → SIM auth      │   │
│            │ - IMPU   │   │ RES/CK/IK│   │ 3. → AKA-Digest    │   │
│            │ - Domain │   │    ↓     │   │ 4. REGISTER → 200  │   │
│            │ - P-CSCF │   │          │   │ 5. MESSAGE/INVITE  │   │
│            └──────────┘   └──────────┘   │ 6. SUBSCRIBE/PUBLISH│   │
│                                          └─────────────────────┘   │
│                                                      ↕              │
│                                            ┌──────────────────┐     │
│                                            │ Carrier IMS Core │     │
│                                            │ (P/I/S-CSCF)    │     │
│                                            │ + RCS AS         │     │
│                                            └──────────────────┘     │
└──────────────────────────────────────────────────────────────────────┘
```

### Sequence: First Registration to First Message

```
1.  [Reader] ← Insert SIM card
2.  [pySim]  → Read EF.IMPI, EF.IMPU, EF.DOMAIN, EF.P-CSCF
3.  [Client] → Discover P-CSCF (ISIM → ACS → DNS)
4.  [SIP]    → REGISTER (no auth) → P-CSCF
5.  [P-CSCF] → 401 Unauthorized (nonce = Base64(RAND‖AUTN))
6.  [Client] → Decode nonce → extract RAND, AUTN
7.  [Client] → POST RAND, AUTN to sim-rest-server
8.  [SIM]    → AUTHENTICATE APDU → compute RES, CK, IK
9.  [Client] ← Receive RES, CK, IK from sim-rest-server
10. [Client] → Compute AKA-Digest response (MD5 chain)
11. [SIP]    → REGISTER (with Authorization header) → P-CSCF
12. [P-CSCF] → 200 OK (registration successful)
13. [SIP]    → SUBSCRIBE presence / PUBLISH capabilities
14. [SIP]    → MESSAGE (CPIM body, IMDN headers) → recipient
15. [SIP]    ← 200 OK (message delivered)
16. [SIP]    ← MESSAGE (IMDN delivery notification from recipient)
```

---

## Appendix A: Full Python Main Script (Pseudocode)

```python
#!/usr/bin/env python3
"""
Headless RCS Client — Main Orchestrator
Connects SIM card → IMS registration → sends/receives RCS messages
"""
import time
import os

def main():
    # ── Step 1: Read ISIM data ──
    print("Step 1: Reading ISIM files from SIM card...")
    isim = read_isim(slot=0)
    impi = isim['impi']
    impu = isim['impu']
    domain = isim['domain']

    # ── Step 2: Discover P-CSCF ──
    print("\nStep 2: Discovering P-CSCF...")
    mcc = extract_mcc(impi)  # Parse from IMPI domain
    mnc = extract_mnc(impi)
    pcscf = discover_pcscf(isim, mcc, mnc, imsi="...", imei="...")
    print(f"  P-CSCF: {pcscf}")

    # ── Step 3: SIP REGISTER → get 401 challenge ──
    print("\nStep 3: Sending initial SIP REGISTER...")
    challenge = send_register_and_get_challenge(
        impi, impu, domain, pcscf)

    # ── Step 4: SIM authentication ──
    print("\nStep 4: Authenticating via SIM card...")
    auth_data = sim_auth_akav1(
        challenge['rand_hex'], challenge['autn_hex'])

    if auth_data.get('sync_failure'):
        # Handle AUTS re-sync
        print("  Handling SQN sync failure...")
        # ... re-REGISTER with AUTS, get new challenge, retry

    # ── Step 5: Compute AKA-Digest response ──
    print("\nStep 5: Computing AKA-Digest response...")
    # (Done inside Step 6 function)

    # ── Step 6: Authenticated REGISTER ──
    print("\nStep 6: Sending authenticated SIP REGISTER...")
    reg_result = send_authenticated_register(
        impi, impu, domain, pcscf, 5060,
        "192.168.1.100", 5060,
        challenge, auth_data,
        call_id="...", tag="...")

    if not reg_result.get('registered'):
        print("Registration FAILED!")
        return

    # ── Step 7: Presence and capabilities ──
    print("\nStep 7: Subscribing presence / publishing capabilities...")
    # SUBSCRIBE, PUBLISH, or OPTIONS-based capability exchange

    # ── Step 8: Send a message ──
    print("\nStep 8: Sending RCS message...")
    send_rcs_message(
        sender_impu=impu,
        recipient_impu="sip:+14448880011@ims.mnc001.mcc001.3gppnetwork.org;user=phone",
        text="Hello from headless RCS!",
        domain=domain,
        pcscf_addr=pcscf)

    # ── Step 9: Listen for incoming messages ──
    print("\nStep 9: Listening for incoming messages...")
    listener = SipListener("192.168.1.100", 5060)
    while True:
        messages = listener.listen(timeout=5.0)
        for method, msg, addr in messages:
            if method == "MESSAGE":
                handle_incoming_message(msg, addr, listener)
            elif method == "INVITE":
                handle_incoming_invite(msg, addr, listener)
            elif method == "OPTIONS":
                listener.respond_200_ok(msg, addr)

        # Re-registration before expiry
        # (check timer, re-REGISTER if needed)

if __name__ == '__main__':
    main()
```

---

## Appendix B: Key RFCs and Specifications

| Spec | Title | Relevance |
|------|-------|-----------|
| **RFC 3310** | AKA for HTTP Digest | AKAv1-MD5 digest computation |
| **RFC 4169** | AKAv2-MD5 for HTTP Digest | Updated AKA digest (5G) |
| **RFC 2617** | HTTP Authentication (Digest) | Base digest auth formula |
| **RFC 3261** | SIP: Session Initiation Protocol | Core SIP specification |
| **RFC 3428** | SIP Extension for Instant Messaging | SIP MESSAGE method |
| **RFC 3862** | CPIM: Common Profile for IM | Message format wrapper |
| **RFC 4975** | MSRP: Message Session Relay Protocol | Session-mode messaging |
| **RFC 5438** | IMDN: Message Disposition Notification | Delivery/read receipts |
| **RFC 6714** | MSRP CEMA | Connection-established media auth |
| **3GPP TS 33.203** | IMS Security | AKA for IMS registration |
| **3GPP TS 31.103** | ISIM characteristics | ISIM file definitions |
| **3GPP TS 24.229** | SIP Call Control for IMS | SIP procedures in IMS |
| **GSMA RCC.07** | RCS Advanced Communications | RCS feature definitions |
| **GSMA RCC.71** | RCS Universal Profile | Current RCS standard |
| **GSMA RCC.14** | Service Provider Device Config | ACS provisioning spec |

---

## Appendix C: Troubleshooting Checklist

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| 401 loop (repeated challenges) | Wrong AKA-Digest computation | Verify RES is hex-string in H(A1), check realm match |
| `synchronisation_failure` (AUTS) | SQN drift between SIM and HSS | Send AUTS in re-REGISTER, get fresh challenge |
| 403 Forbidden after 401 | IPSec required but not established | Implement Security-Client/Server negotiation + IPSec SA |
| No response to REGISTER | P-CSCF unreachable | Verify P-CSCF address, check routing, try DNS discovery |
| 403 + "not supported" | Wrong algorithm or auth type | Check if carrier uses AKAv1-MD5 vs AKAv2-MD5 vs Digest |
| SIM auth returns SW 6982 | PIN not verified | Verify PIN1 before AUTHENTICATE, or disable PIN1 |
| SIM auth returns SW 9862 | Incorrect MAC in AUTN | K/OP mismatch, or wrong ADF selected (must be ISIM) |
| Message 403 Forbidden | Not registered or expired | Check registration state, re-REGISTER if expired |
| Message timeout (no 200 OK) | Recipient not RCS-capable | Try SIP OPTIONS capability query first |
| `gmscore_instance_id_token` error | Google Guest mode, not carrier IMS | This recipe only works with carrier IMS, not Google OTT |

---

*Recipe document generated from analysis of 7 internal research reports + 10 targeted web searches covering RFC 3310, pjsip AKA API, Spirent IMS AKA debug methodology, ShareTechnote IMS registration traces, P-CSCF discovery procedures, and python-sipsimple IMS registration patterns.*
