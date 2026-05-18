# Phase 0: RCS SIM Farm Validation Guide

**Date**: 2026-05-18
**Goal**: Prove the entire RCS SIM farm stack works end-to-end for ₹3,128
**Time**: 1-2 days
**What you'll prove**: Jio SIM + ACR39U reader → EAP-AKA auth → ePDG tunnel → IMS registration → 1 RCS message delivered

---

## 0. Why This Validation Matters

Before spending ₹3,79,900 on 13× sysmoOCTSIM boards and 100 Jio SIMs, you need to answer ONE question:

> **Can you authenticate to Jio's ePDG from an Indian IP, register on IMS, and deliver a message?**

If yes → build the farm. If no → pivot (CPaaS reselling, RBM API, or different carrier).

This guide uses **1 SIM + 1 reader** to answer that question for ₹3,128.

---

## 0.5 Critical Clarification: You NEVER Deal with pcscd Directly

**Both sysmoOCTSIM AND ACR39U use pcscd internally.** But you never touch it. Here's why:

```
What you ACTUALLY interact with:

  strongSwan ──► HTTP POST to sim-rest-server ──► {res, ck, ik}  ← YOU ONLY SEE THIS
  
What happens INSIDE sim-rest-server (invisible to you):

  sim-rest-server ──► pyscard ──► pcscd ──► libccid ──► USB ──► SIM card
  
  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  ALL OF THIS IS AUTOMATIC. You never call pcscd, never send APDU commands.
  sim-rest-server handles everything. You just call the REST API.
```

**Osmocom themselves use pcscd.** Their official CI test rig at sysmocom uses:
- 1× sysmoOCTSIM (8 slots)
- 6× **Omnikey 3121** single-slot CCID readers

Source: https://osmocom.org/projects/pysim/wiki/TestRig

The osmo-sim-auth documentation says: **"Any reader supported by pcsc-lite will work. However, a reader compatible with the USB CCID device class is much recommended."**

**ACR39U is CCID class. It's on the approved list. It works with the entire Osmocom stack.**

### Software Stack: ACR39U vs sysmoOCTSIM — IDENTICAL

| Layer | ACR39U (1 SIM) | sysmoOCTSIM (8 SIMs) | Difference? |
|-------|---------------|---------------------|-------------|
| Your code | `POST /sim-auth-api/v1/slot/0` | `POST /sim-auth-api/v1/slot/0` through `/7` | Just slot number |
| sim-rest-server | Same | Same | None |
| pyscard | Same | Same | None |
| pcscd | Same | Same | None |
| libccid | Same | Same | None |
| APDU commands | Same | Same | None |
| EAP-AKA response | Same | Same | None |
| USB CCID interface | 1 endpoint | 8 endpoints per board | Just count |

**The only difference is how many SIMs fit. The software is 100% identical.**

---

## 1. Shopping List

| Item | Model | Price | Where to Buy | Notes |
|------|-------|-------|-------------|-------|
| **Smart Card Reader** | ACS ACR39U-I1 | ₹980 | [Amazon.in](https://www.amazon.in/dp/B016IY2P7M) | CCID compliant, FIPS 201, 200K insertion rating |
| **Jio Prepaid SIM** | Any Jio 4G/5G SIM | ₹1,499 | Jio Store / Digital | Get ₹1,499/yr plan. Aadhaar eKYC required. |
| **Nano→2FF SIM Adapter** | Any brand | ₹50 | Amazon.in | Jio gives nano-SIM. Reader takes 2FF (mini-SIM). |
| **Indian VPS** | Hostinger KVM 1 | ₹599/mo | [hostinger.in](https://www.hostinger.in/vps-hosting) | 1 vCPU, 4GB RAM, Indian IP. Or use AWS Mumbai free tier. |
| | | **TOTAL** | **₹3,128** | |

### Why ACS ACR39U-I1

- **₹980 on Amazon.in** — available next-day delivery in India
- **CCID compliant** — Linux pcscd detects it automatically, zero driver install
- **ISO 7816 Class A/B/C** — supports all SIM voltages (5V, 3V, 1.8V)
- **FIPS 201 certified** — US government standard, proven reliability
- **Same APDU interface as sysmoOCTSIM** — your validation code scales directly to the farm
- **ACS (Advanced Card Systems)** — world #2 smart card reader maker, Hong Kong
- **200,000 card insertion rating** — built for 24/7 continuous use

### Osmocom Compatibility Proof

Osmocom's official pySim test rig (https://osmocom.org/projects/pysim/wiki/TestRig) uses:
- 1× sysmoOCTSIM (8 slots)
- **6× Omnikey 3121** — a standard single-slot CCID reader, just like ACR39U

The osmo-sim-auth documentation explicitly states:
> **"Any reader supported by pcsc-lite will work. However, a reader compatible with the USB CCID device class is much recommended."**

The pySim transport layer (`pySim/transport/pcsc.py`) uses **pyscard** to talk to pcscd. It calls `smartcard.System.readers()` to enumerate readers, then `createConnection()` and `transmit()` for APDU exchange. This is a **standard interface** — it works with ANY CCID reader. ACR39U is CCID. It works.

**You do NOT need sysmoOCTSIM for validation.** The ACR39U gives you the exact same APDU access, the exact same sim-rest-server API, the exact same EAP-AKA computation. The sysmoOCTSIM is only needed when you scale to 8+ SIMs and want clean hardware management.

### Alternative: ACS ACR39U-N1 PocketMate II

Same chip, same functionality, smaller form factor, ₹200-500 more expensive. Desktop ACR39U-I1 is preferred because it stays put on your desk with a SIM inserted 24/7. The PocketMate is for people who carry it in their pocket. Both work identically with pySim/sim-rest-server.

### What NOT to Buy

| Avoid | Why |
|-------|-----|
| Generic ₹300-500 CCID readers (Amazon.in) | Non-standard chips, unreliable pcscd compatibility, 10K insertion rating |
| Dinstar SIMBank / iQsim 256 Rack | Connects SIMs to GSM modems (radio), NOT PCSC. Can't do EAP-AKA. |
| Phone-based SIM access | No programmatic APDU access. Android TelephonyManager can't do full AKA. |

---

## 2. Architecture for Validation

```
┌─────────────────────────────────────────────────────────────────┐
│                   PHASE 0 VALIDATION SETUP                      │
│                                                                 │
│  ┌──────────┐    USB     ┌──────────┐                          │
│  │ Jio SIM  │───────────│ ACR39U   │                          │
│  │ (nano→2FF│   APDU    │ Reader   │                          │
│  │ adapter) │           │ ₹980     │                          │
│  └──────────┘           └────┬─────┘                          │
│                              │ USB                             │
│                              ▼                                 │
│  ┌──────────────────────────────────────────┐                 │
│  │          YOUR LAPTOP (any OS)             │                 │
│  │                                           │                 │
│  │  pcscd ──► libccid ──► ACR39U            │                 │
│  │     │                                    │                 │
│  │  sim-rest-server.py                      │                 │
│  │  (REST API on port 5000)                 │                 │
│  │  POST /sim-auth-api/v1/slot/0            │                 │
│  │  → returns RES/CK/IK                     │                 │
│  │     │                                    │                 │
│  │  WireGuard client ──────────────────┐    │                 │
│  └──────────────────────────────────────│────┘                 │
│                                         │                      │
│                              WireGuard tunnel                     │
│                                         │                      │
│  ┌──────────────────────────────────────│────┐                 │
│  │       INDIAN VPS (Hostinger ₹599/mo)│    │                 │
│  │                                     ▼    │                 │
│  │  strongSwan (EAP-AKA via sim-rest-server)│                 │
│  │     │                                   │                 │
│  │     │ IKEv2/EAP-AKA                     │                 │
│  │     ▼                                   │                 │
│  │  Jio ePDG (49.44.190.248) ──► IMS      │                 │
│  │     │                                   │                 │
│  │  PJSIP / custom SIP client              │                 │
│  │  SIP REGISTER ──► 200 OK                │                 │
│  │  SIP MESSAGE ──► delivered!             │                 │
│  └─────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

### Why Split Across Laptop + VPS?

- **SIM reader must be physically connected** to a machine via USB
- **ePDG requires Indian IP** — confirmed geoblocking (see `test-epdg-reachability.py`)
- **sim-rest-server exposes REST API** — strongSwan on VPS calls it over WireGuard tunnel
- **This is the same architecture as the 100-SIM farm** — just 1 SIM instead of 104

---

## 3. Step-by-Step Setup

### Step 1: Prepare the SIM Card (5 min)

1. Buy a Jio prepaid SIM from any Jio Store (Aadhaar eKYC, takes 15 min)
2. Activate it: make 1 phone call, send 1 SMS, wait for activation SMS
3. Insert the Jio nano-SIM into the 2FF adapter
4. Insert the adapter into the ACR39U reader's slot (chip facing up, beveled corner first)
5. Plug the ACR39U into your laptop's USB port

### Step 2: Install Software on Your Laptop (15 min)

```bash
# Install pcscd (smart card daemon)
sudo apt install pcscd libccid python3-pyscard python3-pip git -y

# Start pcscd
sudo systemctl enable pcscd
sudo systemctl start pcscd

# Verify reader is detected
pcsc_scan
# Expected output: "ACS ACR39U" or "ACS ACR39U-I1" with "Card present"
# Press Ctrl+C to exit

# Install pySim (includes sim-rest-server)
git clone https://github.com/osmocom/pysim
cd pysim
pip install -e .

# Verify SIM is readable — read the IMSI
./pySim-prog.py -p 0 --read-imsi
# Expected: IMSI: 405874... (Jio MCC=405, MNC=874)
# If you see the IMSI, the SIM and reader are working correctly

# Read full SIM info
./pySim-prog.py -p 0 --read-imsi --read-iccid --read-ki
# IMSI, ICCID should be visible. KI will NOT be readable (carrier SIMs protect it)
```

### Step 3: Start sim-rest-server (5 min)

```bash
cd pysim

# Start the REST API server
python3 sim-rest-server.py -p 5000

# In another terminal, test AKA computation:
curl -X POST http://localhost:5000/sim-auth-api/v1/slot/0 \
  -H "Content-Type: application/json" \
  -d '{
    "rand": "0123456789abcdef0123456789abcdef",
    "autn": "0123456789abcdef0123456789abcdef"
  }'

# Expected response:
# {"res": "...", "ck": "...", "ik": "...", "auts": null}
# If you get this, sim-rest-server is working and your SIM can compute AKA!
#
# If "auts" is non-null, the AUTN was rejected (SQN sync issue) — this is normal
# with a random AUTN. The important thing is that the SIM responded.
```

### Step 4: Set Up Indian VPS (15 min)

```bash
# Option A: Hostinger India VPS (₹599/mo)
# Sign up at hostinger.in, select KVM 1 plan, Mumbai datacenter

# Option B: AWS Mumbai free tier
# Sign up at aws.amazon.com, launch t2.micro in ap-south-1

# After VPS is running, SSH in:
ssh root@<VPS-IP>

# Install strongSwan
apt update && apt install -y strongswan libstrongswan-extra-plugins \
  libstrongswan-standard-plugins strongswan-libcharon \
  libcharon-extra-plugins libcharon-standard-plugins -y

# Install WireGuard
apt install -y wireguard

# Generate WireGuard keys
wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key
cat /etc/wireguard/server_public.key  # Share this with your laptop

# Configure WireGuard server
cat > /etc/wireguard/wg0.conf << 'EOF'
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = <paste server_private.key>

[Peer]
PublicKey = <paste laptop_public.key>
AllowedIPs = 10.0.0.2/32
EOF

# Start WireGuard
wg-quick up wg0
```

### Step 5: Connect Laptop to VPS via WireGuard (5 min)

```bash
# On your laptop:
sudo apt install wireguard -y

# Generate laptop keys
wg genkey | tee /tmp/laptop_private.key | wg pubkey > /tmp/laptop_public.key
cat /tmp/laptop_public.key  # Add this to VPS wg0.conf [Peer] section

# Configure WireGuard client
cat > /etc/wireguard/wg0.conf << 'EOF'
[Interface]
Address = 10.0.0.2/24
PrivateKey = <paste laptop_private.key>

[Peer]
PublicKey = <paste server_public.key>
Endpoint = <VPS-IP>:51820
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
EOF

sudo wg-quick up wg0

# Test connectivity
ping 10.0.0.1  # Should work

# Make sim-rest-server accessible from VPS
# sim-rest-server is already running on port 5000 on laptop (10.0.0.2)
# From VPS:
curl -X POST http://10.0.0.2:5000/sim-auth-api/v1/slot/0 \
  -H "Content-Type: application/json" \
  -d '{"rand":"0123456789abcdef0123456789abcdef","autn":"0123456789abcdef0123456789abcdef"}'
# Should return RES/CK/IK — VPS can now authenticate via your SIM!
```

### Step 6: Test ePDG Reachability from VPS (5 min)

```bash
# On VPS: test if Jio ePDG responds to IKEv2 from Indian IP
python3 -c "
import socket,struct
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.settimeout(5)
h=struct.pack('!II',0xDEADBEEF,0)+struct.pack('!BB',0,0x20)+struct.pack('!BB',0x22,0x08)+struct.pack('!II',0,28)
s.sendto(h,('49.44.190.248',500))
try:
 d,a=s.recvfrom(4096);print(f'REACHABLE - ePDG responded from {a}!')
except:print('BLOCKED - Indian VPS IP also blocked. Try mobile proxy.')
"

# Or use the full test script:
# Copy test-epdg-reachability.py to VPS and run:
python3 test-epdg-reachability.py
```

**If REACHABLE**: Continue to Step 7.
**If BLOCKED**: Indian DC IPs are also filtered. You need a mobile proxy:
```bash
# Subscribe to IPMunk ($27/mo) for a real Jio 4G IP
# Configure strongSwan to route through the SOCKS5 proxy
# See: 05-INDIA-OPERATIONS/indian-mobile-proxy-epdg-bypass.md
```

### Step 7: Configure strongSwan for EAP-AKA (10 min)

```bash
# On VPS: configure strongSwan to connect to Jio ePDG

# /etc/strongswan.conf — add sim-rest-server as auth backend
cat >> /etc/strongswan.conf << 'EOF'

charon {
    plugins {
        eap-aka {
            server_uri = http://10.0.0.2:5000/sim-auth-api/v1/slot/0
            next_reauth = 86400
        }
    }
}
EOF

# /etc/ipsec.conf — Jio ePDG connection
cat > /etc/ipsec.conf << 'EOF'
config setup
    strictcrlpolicy=no

conn jio-epdg
    keyexchange=ikev2
    right=49.44.190.248
    rightid=49.44.190.248
    rightauth=eap-aka
    rightsubnet=0.0.0.0/0
    leftauth=eap-aka
    leftid=405874XXXXXXXXX  # YOUR JIO IMSI (from Step 2)
    eap_identity=405874XXXXXXXXX
    auto=add
    dpdaction=restart
    dpddelay=30
EOF

# /etc/ipsec.secrets — EAP-AKA using sim-rest-server
echo "405874XXXXXXXXX : EAP-AKA" >> /etc/ipsec.secrets

# Start strongSwan
systemctl restart strongswan

# Attempt ePDG connection
ipsec up jio-epdg
# Expected: "connection 'jio-epdg' established successfully"
# If it works, you have an IPsec tunnel to Jio's IMS!
```

### Step 8: SIP REGISTER + Send Message (15 min)

```bash
# After IPsec tunnel is established, P-CSCF address is obtained from ePDG

# Install PJSIP
apt install -y libpjsip-dev pjproject-bin  # or build from source

# Use the headless RCS recipe from:
# 01-ARCHITECTURE/headless-rcs-recipe.md

# Minimal SIP REGISTER:
# 1. Discover P-CSCF from ePDG PCSCF address in IKE_AUTH response
# 2. Send SIP REGISTER to P-CSCF
# 3. Receive 401 Unauthorized with AKA challenge
# 4. Compute AKA response via sim-rest-server
# 5. Send SIP REGISTER with Authorization header
# 6. Receive 200 OK — IMS REGISTERED!
# 7. Send SIP MESSAGE to a real RCS user
# 8. Verify delivery on target phone

# Quick test with sipsimple (Python):
pip3 install sipclients
# Or use the custom SIP stack from headless-rcs-recipe.md
```

---

## 4. Success Criteria

| Step | Test | Success = | Fail = |
|------|------|-----------|--------|
| 1. SIM readable | `pcsc_scan` | Shows "Card present" + Jio SIM | SIM not seated, reader not detected |
| 2. IMSI readable | `pySim-prog.py --read-imsi` | Shows 405874... | Wrong reader, SIM not activated |
| 3. AKA works | sim-rest-server returns RES/CK/IK | Got crypto response | SIM damaged, APDU error |
| 4. ePDG reachable | `test-epdg-reachability.py` from VPS | "REACHABLE" | VPS IP blocked → need mobile proxy |
| 5. EAP-AKA auth | `ipsec up jio-epdg` | "established successfully" | IMSI rejected, wrong config |
| 6. SIP REGISTER | Send REGISTER, get 200 OK | IMS registered | Carrier rejects headless SIP UA |
| 7. Message sent | SIP MESSAGE to real user | Delivered to phone | Jio blocks non-phone IMS clients |

**Steps 1-3** are local hardware/software tests. Should work in 30 min.
**Steps 4-7** depend on Jio's network behavior. This is what you're validating.

---

## 5. Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| pcscd doesn't see reader | Wrong USB port / driver | Try `sudo pcscd --debug -f` for logs. Check `lsusb` for ACS device. |
| "Card not present" in pcsc_scan | SIM not seated properly | Reinsert SIM with adapter. Try different adapter. Clean SIM contacts. |
| pySim can't read IMSI | SIM not activated | Make a phone call from the SIM first (in a real phone). Wait for activation. |
| sim-rest-server returns error | Wrong slot number | Check `pcsc_scan` for slot index. Try slot 0, 1, 2. |
| ePDG TIMEOUT from VPS | Indian DC IP also blocked | Subscribe to IPMunk mobile proxy ($27/mo). See indian-mobile-proxy-epdg-bypass.md. |
| strongSwan AUTHENTICATION_FAILED | IMSI format wrong | Verify IMSI with `pySim-prog.py`. Use 15-digit IMSI without padding. |
| strongSwan NO_PROPOSAL_CHOSEN | Wrong cipher suite | Try adding `ike=aes256gcm16-prfsha384-ecp384!` to ipsec.conf. |
| SIP 403 Forbidden | Carrier rejects headless UA | Try adding `User-Agent: Android/14 GoogleMessages` header. |
| SIP 421 Extension Required | Missing sec-agree | Add `Security-Client` and `Proxy-Require: sec-agree` headers. |

---

## 6. Cost Breakdown

| Item | Cost | One-time or Monthly |
|------|------|-------------------|
| ACS ACR39U-I1 reader | ₹980 | One-time |
| Jio prepaid SIM (₹1,499/yr plan) | ₹1,499 | Annual |
| Nano→2FF SIM adapter | ₹50 | One-time |
| Hostinger India VPS (1 month) | ₹599 | Monthly |
| **Total to validate** | **₹3,128** | |
| If mobile proxy needed | +$27 (~₹2,250) | Monthly |

**₹3,128 to answer the most important question in this entire project.**

---

## 7. What Happens After Validation

### If ALL steps succeed

You've proven:
1. Jio ePDG accepts your Indian VPS IP
2. EAP-AKA auth works with a real Jio SIM
3. IMS registration works for a headless SIP client
4. Messages can be delivered

**Next step**: Buy 1× sysmoOCTSIM EVK (€595, ~₹55K) → scale to 8 SIMs → build MVP.

### If Steps 1-3 fail (hardware/SIM issues)

Unlikely — these are standard PCSC operations. But if:
- Try different USB port
- Try different SIM adapter
- Try a different Jio SIM (rare SIM defect)

### If Step 4 fails (VPS IP blocked by ePDG)

Indian datacenter IPs are also geoblocked. This is possible but not confirmed.
**Fix**: Subscribe to IPMunk ($27/mo) for a real Jio 4G mobile IP.
See `05-INDIA-OPERATIONS/indian-mobile-proxy-epdg-bypass.md`.

### If Step 5 fails (EAP-AKA rejected)

Jio ePDG may reject headless IKEv2 connections even with valid SIM auth.
**Fix**:
- Try Airtel ePDG instead (106.201.214.127)
- Try different strongSwan configuration (MOBIKE, NAT-T)
- Try libreswan instead of strongSwan (supports RFC 8229 IKE-over-TCP)

### If Step 6 fails (SIP REGISTER rejected)

Jio P-CSCF may reject headless SIP User Agents.
**Fix**:
- Mimic Google Messages SIP headers (User-Agent, Contact, Feature-Caps)
- Add `sec-agree` and `Security-Client` headers
- Try SMSoIP format (simpler than full RCS)
- See `01-ARCHITECTURE/headless-rcs-recipe.md` for exact SIP headers

### If Step 7 fails (message not delivered)

SIP MESSAGE sent but not received by target phone.
**Fix**:
- Try SMSoIP format (`application/vnd.3gpp.sms`) instead of RCS format
- Verify target phone has RCS enabled
- Check Jio RCS server is routing messages correctly

---

## 8. Scaling Path After Validation

| Phase | Hardware | SIMs | Cost | When |
|-------|----------|------|------|------|
| **0: Validate** (this guide) | 1× ACR39U | 1 | ₹3,128 | NOW |
| **1: MVP** | 1× sysmoOCTSIM EVK | 8 | ₹97,000 | After Phase 0 success |
| **2: Scale** | 13× sysmoOCTSIM | 104 | ₹3,79,900 | After MVP profitable |
| **3: Productize** | Same hardware | 104 | SaaS build cost | After revenue starts |

---

## 9. Quick Reference

### ACR39U Technical Specs

| Spec | Value |
|------|-------|
| Interface | USB 2.0 Full Speed |
| Smart Card Standard | ISO 7816 Class A, B, C |
| Card Type | SIM (2FF/mini-SIM) with adapter |
| Supported Protocols | T=0, T=1 |
| CCID | Yes — works with Linux pcscd |
| Card Insertion Rating | 200,000 cycles |
| Certifications | FIPS 201, CC EMV, WHQL |
| Weight | ~50g |
| Dimensions | 98mm × 65mm × 13mm |
| Manufacturer | ACS (Advanced Card Systems), Hong Kong |
| Price India | ₹980 (Amazon.in) |
| Linux Driver | Built-in via libccid (no extra install) |

### SIM Card in Reader — Adapter Guide

| SIM Size | Jio Gives You | What Reader Needs | Adapter |
|----------|---------------|-------------------|---------|
| 4FF (nano) | Yes (standard Jio SIM) | 2FF (mini-SIM) | Nano → 2FF adapter (₹50 on Amazon.in) |
| 3FF (micro) | Sometimes (older Jio SIMs) | 2FF (mini-SIM) | Micro → 2FF adapter |
| 2FF (mini) | Rare | 2FF (mini-SIM) | No adapter needed |

**Important**: Always use a rigid adapter, not a flimsy one. The SIM must sit firmly in the reader for 24/7 operation. Poor seating = intermittent APDU errors.

### ePDG Addresses (for reference)

| Carrier | FQDN | IP Addresses |
|---------|------|-------------|
| Jio | `epdg.epc.mnc856.mcc405.pub.3gppnetwork.org` | 49.44.190.248, 49.44.190.243 |
| Airtel | `epdg.epc.mnc010.mcc404.pub.3gppnetwork.org` | 106.201.214.127, 106.201.214.99, 106.201.214.117 |
| Vi | `epdg.epc.mnc002.mcc404.pub.3gppnetwork.org` | 106.201.214.113 |

### Software Stack (same for validation AND production)

| Layer | Software | Purpose |
|-------|----------|---------|
| Smart Card Daemon | pcscd + libccid | Manages USB CCID readers |
| SIM Auth REST API | sim-rest-server (pySim) | `POST /sim-auth-api/v1/slot/0` → RES/CK/IK |
| ePDG Tunnel | strongSwan (Osmocom fork) | IKEv2/EAP-AKA to carrier ePDG |
| IMS Client | PJSIP / custom SIP | SIP REGISTER + SIP MESSAGE |
| Orchestration | Python FastAPI | Health checks, message queue |
| Network Tunnel | WireGuard | Laptop ↔ Indian VPS |

---

## 10. One-Command Quick Start (for the impatient)

```bash
# On your laptop — install everything and test SIM in 5 commands:
sudo apt install -y pcscd libccid python3-pyscard python3-pip git && \
git clone https://github.com/osmocom/pysim && \
cd pysim && pip install -e . && \
pcsc_scan -n 1 && \
python3 -c "
import smartcard.System
readers = smartcard.System.readers()
print(f'Found {len(readers)} reader(s):')
for r in readers: print(f'  {r}')
print('Reader detected!' if readers else 'ERROR: No reader found. Check USB connection.')
"
```

If you see "Reader detected!" — you're ready for Step 2 onwards.
