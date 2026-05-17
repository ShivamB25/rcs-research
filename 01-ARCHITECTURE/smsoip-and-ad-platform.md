# SMSoIP (SMS over IMS) & RCS Advertising Platform Design

**Date:** 2026-05-16  
**Scope:** Two-part deep research report covering (1) SMS over IMS (SMSoIP) via SIP MESSAGE as a simpler alternative to full RCS, and (2) RCS advertising platform product/business design.  
**Prerequisite Context:** 22 existing reports in `/home/ubuntu/rcs-research/`

---

## Table of Contents

### PART 1: SMSoIP — SMS over IMS via SIP MESSAGE
1. [Executive Summary](#1-executive-summary-smsoip)
2. [What Is SMSoIP?](#2-what-is-smsoip)
3. [Specification Landscape](#3-specification-landscape)
4. [SMSoIP vs RCS Messaging: Side-by-Side](#4-smsoip-vs-rcs-messaging-side-by-side)
5. [The Key Insight: +g.3gpp.smsip Feature Tag](#5-the-key-insight-g3gppsmsip-feature-tag)
6. [Exact SIP MESSAGE Format for SMSoIP](#6-exact-sip-message-format-for-smsoip)
7. [SMSoIP Protocol Flow: MO-SMS](#7-smsoip-protocol-flow-mo-sms)
8. [SMSoIP Protocol Flow: MT-SMS](#8-smsoip-protocol-flow-mt-sms)
9. [RP-DATA / RP-ACK Internal Structure](#9-rp-data--rp-ack-internal-structure)
10. [Does SMSoIP Work on Carrier IMS?](#10-does-smsoip-work-on-carrier-ims)
11. [Self-Hosted IMS: SMSoIP Is Trivial](#11-self-hosted-ims-smsoip-is-trivial)
12. [Throughput Analysis](#12-throughput-analysis)
13. [What Does the Receiving Side See?](#13-what-does-the-receiving-side-see)
14. [Google Messages and SMSoIP](#14-google-messages-and-smsoip)
15. [SMSoIP as Minimum Viable Product](#15-smsoip-as-minimum-viable-product)
16. [Implementation Guide: SMSoIP Sender](#16-implementation-guide-smsoip-sender)
17. [Limitations and Risks](#17-limitations-and-risks)

### PART 2: RCS Advertising Platform Design
18. [Market Opportunity](#18-market-opportunity)
19. [Platform Architecture Overview](#19-platform-architecture-overview)
20. [Multi-Tenant SaaS Design](#20-multi-tenant-saas-design)
21. [Campaign Management](#21-campaign-management)
22. [AB Testing Framework](#22-ab-testing-framework)
23. [Analytics and Reporting](#23-analytics-and-reporting)
24. [Inbox Management: Conversational Messaging](#24-inbox-management-conversational-messaging)
25. [Contact Management and Compliance](#25-contact-management-and-compliance)
26. [Pricing Model](#26-pricing-model)
27. [White-Label / Agency Reseller](#27-white-label--agency-reseller)
28. [REST API Design](#28-rest-api-design)
29. [Webhook Event Notifications](#29-webhook-event-notifications)
30. [Google RBM Agent Registration Flow](#30-google-rbm-agent-registration-flow)
31. [Technology Stack](#31-technology-stack)
32. [Database Schema](#32-database-schema)
33. [Competitive Landscape](#33-competitive-landscape)
34. [Revenue Projections](#34-revenue-projections)
35. [Roadmap](#35-roadmap)

---

# PART 1: SMSoIP — SMS over IMS via SIP MESSAGE

## 1. Executive Summary (SMSoIP)

**The core finding:** When a phone registers on IMS, it can send SMS over IP (SMSoIP) using the SIP MESSAGE method with `Content-Type: application/vnd.3gpp.sms`. This is fundamentally simpler than full RCS because:

- **No capability discovery needed** — No SIP OPTIONS, no feature tag negotiation
- **No MSRP sessions needed** — Just SIP MESSAGE, no INVITE/SDP/TCP dance
- **No CPIM wrapping** — The body is raw binary RP-DATA, not `message/cpim`
- **Works on ANY IMS registration** — Only requires the `+g.3gpp.smsip` feature tag in REGISTER
- **Falls back transparently to SMS** — The receiving side sees a standard SMS, delivered via IP-SM-GW to the SMS center
- **Defined by 3GPP TS 24.341** — Not a hack; it's the official standard for SMS over IP

**This could be the MINIMUM VIABLE PRODUCT for IMS-based messaging:** Register on IMS → send SMSoIP → no RCS complexity needed.

However, SMSoIP has a critical constraint: **the message body is not plain text** — it's a binary RP-DATA frame (defined in 3GPP TS 24.011) encapsulating a GSM SMS-SUBMIT TPDU (defined in 3GPP TS 23.040). You must construct this binary frame yourself; you cannot just put `text/plain` in a SIP MESSAGE body and expect it to work as SMSoIP.

---

## 2. What Is SMSoIP?

SMSoIP (SMS over IP) is the 3GPP-standardized mechanism for transmitting SMS messages over the IMS infrastructure using the SIP MESSAGE method. It is defined in:

| Specification | Title | Relevance |
|--------------|-------|-----------|
| **3GPP TS 24.341** | Support of SMS over IP networks; Stage 3 | **Primary spec** — protocol details |
| **3GPP TS 23.204** | SMS over IP networks; Stage 2 | Architecture and capabilities |
| **3GPP TS 24.011** | SMS on the radio interface | RP-DATA/RP-ACK frame format |
| **3GPP TS 23.040** | SMS technical realization | SMS-SUBMIT/DELIVER TPDU format |
| **GSMA IR.92** | IMS Profile for Voice and SMS | Feature tag requirements |
| **RFC 3428** | SIP Extension for Instant Messaging | SIP MESSAGE method |

### Architecture

SMSoIP introduces an **IP-SM-GW** (IP Short Message Gateway) into the IMS architecture:

```
┌──────────┐     SIP MESSAGE      ┌──────────┐     SIP MESSAGE     ┌──────────┐
│  UE A    │ ───────────────────→ │ P/S-CSCF │ ──────────────────→ │ IP-SM-GW │
│ (Sender) │  (RP-DATA in body)   │          │                     │          │
└──────────┘                      └──────────┘                     └────┬─────┘
                                                                       │ MAP/SMPP
                                                                       ▼
                                                                ┌──────────────┐
                                                                │   SMS Center  │
                                                                │   (SMSC)      │
                                                                └──────┬───────┘
                                                                       │
                                                                       ▼
                                                                ┌──────────────┐
                                                                │   UE B        │
                                                                │ (Receiver)   │
                                                                │ Sees standard │
                                                                │   SMS         │
                                                                └──────────────┘
```

The IP-SM-GW is the critical interworking function:
- Receives SMSoIP SIP MESSAGE from the IMS core
- Extracts the RP-DATA from the SIP body
- Extracts the SMS-SUBMIT TPDU from inside the RP-DATA
- Forwards the SMS to the SMSC via MAP (SS7) or SMPP
- The SMSC delivers the SMS to the recipient using standard SMS delivery mechanisms

**Key point:** The recipient does NOT need to be registered on IMS. The IP-SM-GW handles the bridge to the traditional SMS world.

---

## 3. Specification Landscape

### 3GPP TS 24.341 — The Definitive SMSoIP Spec

Per TS 24.341, the protocol details for SMS over IP include:

**Section 5.3.2.2 — Capability indication in REGISTER:**
> "On sending a REGISTER request, the SM-over-IP receiver shall indicate its capability to receive traditional short messages over IMS network by including a '+g.3gpp.smsip' parameter into the Contact header according to RFC 3840."

**Section 5.3.2.3 — Sending an MO SMS:**
> "The SM-over-IP sender shall generate an RP-DATA message (RPDU encapsulating TPDU data string), containing all the information to be sent to the SC, as defined in 3GPP TS 24.011. The SM-over-IP sender shall encapsulate the RP-DATA message into a SIP MESSAGE request as described in clause 5.3.2.3."

**Content-Type requirement:**
> The SIP MESSAGE body MUST use `Content-Type: application/vnd.3gpp.sms` — this is the binary RPDU encapsulation format, NOT `text/plain` or `message/cpim`.

**Content-Transfer-Encoding:**
> "The SM-over-IP sender will use content transfer encoding of type 'binary' for the encoding of the SM in the body of the SIP MESSAGE request."

### Key Differences from RCS Standalone Messaging (SIP MESSAGE with CPIM)

| Aspect | SMSoIP | RCS Standalone (Pager-Mode) |
|--------|--------|---------------------------|
| **SIP body Content-Type** | `application/vnd.3gpp.sms` (binary RPDU) | `message/cpim` (text-based wrapper) |
| **Message encoding** | Binary RP-DATA frame with SMS-SUBMIT TPDU | CPIM headers + text/plain body |
| **Feature tag in REGISTER** | `+g.3gpp.smsip` | `+g.3gpp.icsi-ref="urn:urn-7:3gpp-service.ims.icsi.oma.cpm.msg"` |
| **Routing** | Via IP-SM-GW → SMSC → recipient (SMS path) | Via RCS AS → SIP MESSAGE to recipient's UE |
| **Recipient sees** | Standard SMS in their SMS inbox | RCS message in their messaging app |
| **Read receipts** | SMS delivery report (RP-ACK with SMS-DELIVER-REPORT) | IMDN (message/imdn+xml) |
| **Max message size** | Standard SMS: 160 chars (or concatenated SMS) | ~1200 bytes per SIP MESSAGE |
| **Rich media** | No — text only (GSM 7-bit or UCS-2) | Yes — text, but could be extended |
| **Typing indicators** | No | No (pager-mode doesn't support it either) |
| **Capability discovery** | Not needed — SMS always works | SIP OPTIONS recommended |
| **Gateway** | IP-SM-GW (mandatory) | RCS Application Server (may or may not be needed) |

---

## 4. SMSoIP vs RCS Messaging: Side-by-Side

### The Simplicity Argument

```
=== SMSoIP: Send an SMS over IMS ===

Step 1: SIP REGISTER with +g.3gpp.smsip in Contact
Step 2: Get 401 → SIM auth → 200 OK (registered)
Step 3: SIP MESSAGE with application/vnd.3gpp.sms body
        (contains binary RP-DATA wrapping SMS-SUBMIT TPDU)
Step 4: Get 202 Accepted
Step 5: Receive SIP MESSAGE back with RP-ACK
Step 6: Send 200 OK

Total: 3 SIP round-trips after registration
No CPIM, no capability discovery, no MSRP, no session setup


=== RCS Standalone: Send an RCS message ===

Step 1: SIP REGISTER with +g.3gpp.icsi-ref=oma.cpm.msg in Contact
Step 2: Get 401 → SIM auth → 200 OK (registered)
Step 3: (Optional) SIP OPTIONS to discover recipient's RCS capabilities
Step 4: SIP MESSAGE with message/cpim body
        (contains CPIM headers + IMDN headers + text/plain)
Step 5: Get 200 OK
Step 6: Receive SIP MESSAGE with IMDN delivery notification
Step 7: Send 200 OK
Step 8: (Possibly) Receive SIP MESSAGE with IMDN display notification
Step 9: Send 200 OK

Total: 3-5 SIP round-trips after registration
Plus CPIM formatting, IMDN namespace, Conversation-ID, Contribution-ID


=== RCS Chat (Session-Mode): Full complexity ===

Step 1: SIP REGISTER with session feature tags
Step 2: Get 401 → SIM auth → 200 OK (registered)
Step 3: SIP OPTIONS for capability discovery
Step 4: SIP INVITE with SDP (m=message for MSRP)
Step 5: 100 Trying → 183 Session Progress → 200 OK
Step 6: ACK
Step 7: MSRP TCP connection establishment
Step 8: MSRP SEND messages (actual content)
Step 9: MSRP 200 OK responses
Step 10: MSRP SEND for IMDN delivery notification
Step 11: MSRP SEND for is-composing indication
Step 12: SIP BYE to close session

Total: 10+ round-trips, TCP connection, MSRP protocol
```

**SMSoIP is 3-5x simpler than RCS standalone and 10x simpler than RCS session-mode.**

---

## 5. The Key Insight: +g.3gpp.smsip Feature Tag

The `+g.3gpp.smsip` feature tag is the ONLY thing that distinguishes an SMSoIP-capable IMS registration from a regular VoLTE registration.

### How It Works

Per GSMA IR.92 and 3GPP TS 24.341:

1. The UE includes `+g.3gpp.smsip` in the Contact header of SIP REGISTER
2. The S-CSCF stores this as part of the registration
3. When an incoming SMS arrives at the IP-SM-GW for this subscriber, the IP-SM-GW queries the S-CSCF and sees the `+g.3gpp.smsip` tag
4. The IP-SM-GW routes the SMS via SIP MESSAGE to the registered UE instead of falling back to the CS domain
5. For outgoing SMS, the UE simply sends a SIP MESSAGE with `Content-Type: application/vnd.3gpp.sms` through the IMS core

### CRITICAL: The SMS_Over_IP_Networks_Indication Parameter

Per GSMA resolution (GSMA #70, 2019), the UE must only include `+g.3gpp.smsip` when the **SMS_Over_IP_Networks_Indication** configuration parameter is set to indicate SMSoIP is being used. This parameter is stored:

- On the ISIM: In EF.IMSConfigData (if present)
- On the USIM: In EF.UST (USIM Service Table) bit for "SMS over IP"
- In device configuration: Set by the carrier's ACS XML or device provisioning

**For a headless client on a self-hosted IMS:** You control this — always include `+g.3gpp.smsip`.

**For a headless client on carrier IMS:** This is carrier-dependent. If the carrier supports SMSoIP (most do for VoLTE), you include the tag.

### REGISTER with SMSoIP Feature Tag

```
REGISTER sip:ims.mnc001.mcc001.3gppnetwork.org SIP/2.0
Via: SIP/2.0/UDP 192.168.1.100:5060;branch=z9hG4bK-reg1
Max-Forwards: 70
From: <sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org>;tag=reg1
To: <sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org>
Call-ID: reg1@192.168.1.100
CSeq: 1 REGISTER
Contact: <sip:001010123456789@192.168.1.100:5060>;
  +g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.mmtel";
  +g.3gpp.smsip;
  +sip.instance="<urn:gsma:imei:35469106-056673-0>"
Authorization: Digest username="001010123456789@ims.mnc001.mcc001.3gppnetwork.org",
  realm="ims.mnc001.mcc001.3gppnetwork.org",
  nonce="",
  uri="sip:ims.mnc001.mcc001.3gppnetwork.org",
  response=""
Content-Length: 0
```

**Note:** You can include BOTH `+g.3gpp.smsip` AND RCS feature tags (`+g.3gpp.icsi-ref="urn:urn-7:3gpp-service.ims.icsi.oma.cpm.msg"`) in the same REGISTER. This enables both SMSoIP and RCS capabilities simultaneously.

---

## 6. Exact SIP MESSAGE Format for SMSoIP

### MO-SMS: Mobile-Originated SMS over IMS

```
MESSAGE tel:+19037029920;phone-context=TestIMS.com SIP/2.0
From: "Test" <sip:+11234567890@test.3gpp.com>;tag=834037901
To: <tel:+19037029920;phone-context=TestIMS.com>
CSeq: 834037887 MESSAGE
Call-ID: 834037887_2367153256@2001:0:0:1::1
Via: SIP/2.0/UDP [2001:0:0:1::1]:5060;branch=z9hG4bK253093091
Max-Forwards: 70
Route: <sip:[2001:0:0:1::2]:5060;lr>
Content-Type: application/vnd.3gpp.sms
Allow: MESSAGE
Request-Disposition: no-fork
Content-Length: 28

[Binary RP-DATA frame containing SMS-SUBMIT TPDU]
```

**Key differences from RCS SIP MESSAGE:**

| Header/Aspect | SMSoIP | RCS Pager-Mode |
|---------------|--------|----------------|
| **Content-Type** | `application/vnd.3gpp.sms` | `message/cpim` |
| **P-Preferred-Service** | NOT used (or omitted) | `urn:urn-7:3gpp-service.ims.icsi.oma.cpm.msg` |
| **Contribution-ID** | NOT used | Required (UUID) |
| **Conversation-ID** | NOT used | Required (UUID) |
| **Body format** | Binary RP-DATA (3GPP TS 24.011) | CPIM text headers + inner text/plain |
| **Request-URI** | `tel:` URI with phone-context | `sip:` URI |
| **Response** | `202 Accepted` (not 200 OK!) | `200 OK` |

**Critical: SMSoIP uses `202 Accepted`, not `200 OK` for the initial MESSAGE.** The `202` means "your message was accepted for delivery" but doesn't confirm final delivery. The actual delivery confirmation comes later via a separate SIP MESSAGE containing RP-ACK.

### The Binary RP-DATA Body

The SIP MESSAGE body for SMSoIP is NOT plain text. It's a binary frame defined in 3GPP TS 24.011:

```
┌─────────────────────────────────────────────────┐
│ RP-DATA (MS to Network)                         │
│ ┌─────────────────────────────────────────────┐ │
│ │ RP-Message Type: 0x00 (RP-DATA MO)          │ │
│ │ RP-Message Reference: 0x05 (sequence)       │ │
│ │ RP-Origination Address: (empty, implied)    │ │
│ │ RP-Destination Address: SMSC address        │ │
│ │ RP-User Data:                               │ │
│ │ ┌─────────────────────────────────────────┐ │ │
│ │ │ SMS-SUBMIT TPDU (3GPP TS 23.040):        │ │ │
│ │ │ TP-MTI: 01 (SMS-SUBMIT)                  │ │ │
│ │ │ TP-RD: 0 (accept duplicates)             │ │ │
│ │ │ TP-VPF: 10 (relative validity)           │ │ │
│ │ │ TP-SRR: 0 (no status report)            │ │ │
│ │ │ TP-UDHI: 0 (no user data header)         │ │ │
│ │ │ TP-RP: 0 (no reply path)                 │ │ │
│ │ │ TP-MR: 88 (message reference)             │ │ │
│ │ │ TP-DA: +19037029920 (dest address)        │ │ │
│ │ │ TP-PID: 0 (default)                      │ │ │
│ │ │ TP-DCS: 0 (GSM 7-bit default alphabet)   │ │ │
│ │ │ TP-VP: 167 (validity period)              │ │ │
│ │ │ TP-UDL: 5 (user data length)             │ │ │
│ │ │ TP-UD: "Hello" (GSM 7-bit encoded)       │ │ │
│ │ └─────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

---

## 7. SMSoIP Protocol Flow: MO-SMS

Per 3GPP TS 24.341 B.5, the complete flow for a mobile-originated SMS over IP:

```
┌──────┐           ┌─────────┐           ┌──────────┐           ┌──────────┐
│ UE A │           │ P-CSCF  │           │ S-CSCF   │           │ IP-SM-GW │
│(SMSoIP│          │         │           │          │           │          │
│sender)│           │         │           │          │           │          │
└──┬───┘           └────┬────┘           └────┬─────┘           └────┬─────┘
   │                    │                    │                      │
   │ SIP MESSAGE        │                    │                      │
   │ (RP-DATA MO)       │                    │                      │
   │ Content-Type:      │                    │                      │
   │ application/       │                    │                      │
   │ vnd.3gpp.sms       │                    │                      │
   │───────────────────→│───────────────────→│──────────────────────→│
   │                    │                    │                      │
   │ SIP 202 Accepted   │                    │                      │
   │←───────────────────│←───────────────────│←──────────────────────│
   │                    │                    │                      │
   │                    │                    │     IP-SM-GW extracts│
   │                    │                    │     TPDU, routes to  │
   │                    │                    │     SMSC via MAP/SMPP│
   │                    │                    │                      │
   │ SIP MESSAGE        │                    │                      │
   │ (RP-ACK from       │                    │                      │
   │  IP-SM-GW)         │                    │                      │
   │←───────────────────│←───────────────────│←──────────────────────│
   │                    │                    │                      │
   │ SIP 200 OK         │                    │                      │
   │───────────────────→│───────────────────→│──────────────────────→│
   │                    │                    │                      │
```

**Step-by-step:**
1. **UE → P-CSCF**: SIP MESSAGE with `Content-Type: application/vnd.3gpp.sms`, body = binary RP-DATA(MO) containing SMS-SUBMIT TPDU
2. **P-CSCF → S-CSCF → IP-SM-GW**: Message is routed via standard SIP routing (based on iFC — Initial Filter Criteria — which triggers the IP-SM-GW as an application server for SMS traffic)
3. **IP-SM-GW → UE**: SIP `202 Accepted` — message was accepted for delivery to the SMSC
4. **IP-SM-GW → SMSC**: Extracted SMS-SUBMIT TPDU forwarded via MAP/SMPP
5. **SMSC → Recipient**: Standard SMS delivery
6. **IP-SM-GW → UE**: SIP MESSAGE containing RP-ACK (delivery confirmation from the SMSC, wrapped in binary format)
7. **UE → IP-SM-GW**: SIP `200 OK` acknowledging the RP-ACK

---

## 8. SMSoIP Protocol Flow: MT-SMS

When someone sends an SMS TO a UE that is registered on IMS with `+g.3gpp.smsip`:

```
┌──────┐     ┌──────┐     ┌──────────┐     ┌─────────┐     ┌─────────┐
│ SMSC │     │IP-SM-│     │ S-CSCF   │     │ P-CSCF  │     │  UE B   │
│      │     │  GW  │     │          │     │         │     │(SMSoIP  │
│      │     │      │     │          │     │         │     │receiver)│
└──┬───┘     └───┬──┘     └────┬─────┘     └────┬────┘     └────┬────┘
   │             │              │                │               │
   │ MAP forward │              │                │               │
   │────────────→│              │                │               │
   │             │ SIP MESSAGE  │                │               │
   │             │ (RP-DATA MT) │                │               │
   │             │ Content-Type:│                │               │
   │             │ vnd.3gpp.sms │                │               │
   │             │─────────────→│───────────────→│──────────────→│
   │             │              │                │               │
   │             │              │                │ SIP 200 OK    │
   │             │              │                │←──────────────│
   │             │              │                │               │
   │             │              │   UE processes RP-DATA,       │
   │             │              │   extracts SMS-DELIVER TPDU,  │
   │             │              │   displays to user             │
   │             │              │                │               │
   │             │ SIP MESSAGE  │                │               │
   │             │ (RP-ACK)     │                │               │
   │             │←─────────────│←───────────────│←──────────────│
   │             │              │                │               │
   │             │ SIP 200 OK   │                │               │
   │             │─────────────→│───────────────→│──────────────→│
   │             │              │                │               │
```

The IP-SM-GW checks the S-CSCF for the `+g.3gpp.smsip` registration:
- If the UE is registered with SMSoIP → sends via SIP MESSAGE
- If the UE is NOT registered or not SMSoIP-capable → falls back to CS delivery (paging the UE on the radio interface)

---

## 9. RP-DATA / RP-ACK Internal Structure

### RP-DATA (MS to Network) — MO-SMS

Per 3GPP TS 24.011 Section 7.3.1:

```
Byte 0:    Message Type = 0x00 (RP-DATA MS→Network)
Byte 1:    Message Reference (1 byte, sequential)
Byte 2+:   RP-Originator Address (length 0 for MO — implied from registration)
Bytes N+:  RP-Destination Address (SMSC address)
Bytes M+:  RP-User Data:
           - IE Identifier: 0x41 (RP-User-Data)
           - IE Length: variable
           - SMS-SUBMIT TPDU (3GPP TS 23.040)
```

### SMS-SUBMIT TPDU (inside RP-DATA)

Per 3GPP TS 23.040 Section 9.2.2.2:

```
Byte 0:    TP-MTI=01 (SMS-SUBMIT), TP-RD, TP-VPF, TP-SRR, TP-UDHI, TP-RP
Byte 1:    TP-MR (Message Reference, 0-255)
Bytes 2+:  TP-Destination Address (length + type + digits)
Byte N:    TP-PID (Protocol Identifier, 0x00 = default)
Byte N+1:  TP-DCS (Data Coding Scheme, 0x00 = GSM 7-bit, 0x08 = UCS-2)
Byte N+2:  TP-VP (Validity Period, if TP-VPF set)
Byte N+3:  TP-UDL (User Data Length)
Bytes N+4: TP-UD (User Data — the actual SMS text, GSM 7-bit or UCS-2 encoded)
```

### RP-ACK (Network to MS) — Delivery Confirmation

```
Byte 0:    Message Type = 0x01 (RP-ACK Network→MS)
Byte 1:    Message Reference (same as in the RP-DATA)
Bytes 2+:  RP-User Data (optional, contains SMS-DELIVER-REPORT TPDU)
```

### Python: Constructing the SMSoIP Binary Body

```python
import struct

def build_sms_submit_tpdu(dest_address: str, text: str, 
                          message_ref: int = 0,
                          dcs: int = 0x00,  # 0=GSM 7-bit, 0x08=UCS-2
                          validity_period: int = 167,  # 24 hours
                          request_status_report: bool = False) -> bytes:
    """Build SMS-SUBMIT TPDU per 3GPP TS 23.040 Section 9.2.2.2."""
    
    # TP-MTI=01 (SUBMIT), TP-RD=0, TP-VPF=10 (relative), 
    # TP-SRR=0/1, TP-UDHI=0, TP-RP=0
    byte0 = 0x01  # TP-MTI = 01 (SMS-SUBMIT)
    byte0 |= (0x02 << 3)  # TP-VPF = 10 (relative format) → bits 4-3
    if request_status_report:
        byte0 |= 0x20  # TP-SRR = 1
    # TP-RD=0, TP-UDHI=0, TP-RP=0 (all zero)
    
    # TP-MR
    tp_mr = struct.pack('B', message_ref)
    
    # TP-DA (Destination Address)
    tp_da = encode_address(dest_address)
    
    # TP-PID (default)
    tp_pid = struct.pack('B', 0x00)
    
    # TP-DCS
    tp_dcs = struct.pack('B', dcs)
    
    # TP-VP (relative validity)
    tp_vp = struct.pack('B', validity_period)
    
    # TP-UD (User Data)
    if dcs == 0x08:
        # UCS-2 encoding
        ud = text.encode('utf-16-be')
        tp_udl = struct.pack('B', len(ud) // 2)  # in septets for UCS-2, it's bytes/2
    else:
        # GSM 7-bit encoding
        ud = encode_gsm7bit(text)
        tp_udl = struct.pack('B', len(text))  # number of septets
    
    # Assemble TPDU
    tpdu = struct.pack('B', byte0) + tp_mr + tp_da + tp_pid + tp_dcs + tp_vp + tp_udl + ud
    return tpdu

def build_rp_data_mo(tpdu: bytes, message_ref: int, smSC_address: str = "") -> bytes:
    """Build RP-DATA (MS to Network) frame per 3GPP TS 24.011."""
    # Message Type: 0x00 (RP-DATA MS→Network)
    msg_type = struct.pack('B', 0x00)
    
    # Message Reference
    msg_ref = struct.pack('B', message_ref)
    
    # RP-Originator Address (empty for MO — length=0)
    rp_orig = struct.pack('B', 0)  # Length = 0
    
    # RP-Destination Address (SMSC — if empty, use default from SIM)
    if smSC_address:
        rp_dest = encode_address(smSC_address)
    else:
        rp_dest = struct.pack('B', 0)  # Length = 0 (use default SMSC)
    
    # RP-User Data (IE: id=0x41, length, TPDU)
    rp_user_data = struct.pack('B', 0x41)  # IE Identifier
    rp_user_data += struct.pack('B', len(tpdu))  # IE Length
    rp_user_data += tpdu  # The actual TPDU
    
    return msg_type + msg_ref + rp_orig + rp_dest + rp_user_data

def encode_address(address: str) -> bytes:
    """Encode a phone number address per 3GPP TS 24.011 / TS 23.040."""
    # Simple implementation for numeric addresses
    digits = ''.join(c for c in address if c.isdigit() or c == '+')
    is_international = digits.startswith('+')
    if is_international:
        digits = digits[1:]
    
    # Type of Address byte
    toa = 0x81 if is_international else 0x81  # Type=International, Plan=E.164
    # Actually: 1... .... = no extension, .000 .... = Unknown/International, .... 0001 = ISDN
    toa = 0x91 if is_international else 0x81
    
    # BCD encode digits (2 digits per byte, fill with 0xF if odd)
    bcd = bytearray()
    for i in range(0, len(digits), 2):
        if i + 1 < len(digits):
            bcd.append(int(digits[i+1]) * 16 + int(digits[i]))
        else:
            bcd.append(0xF0 + int(digits[i]))
    
    # Length = number of useful semi-octets (digits)
    length = len(digits)
    
    return struct.pack('B', length) + struct.pack('B', toa) + bytes(bcd)

# Simplified GSM 7-bit encoding (real implementation needs lookup table)
GSM7_BASIC = {
    '@': 0x00, '£': 0x01, '$': 0x02, '¥': 0x03, 'è': 0x04, 'é': 0x05,
    'ù': 0x06, 'ì': 0x07, 'ò': 0x08, 'Ç': 0x09, '\n': 0x0A, 'Ø': 0x0B,
    'ø': 0x0C, '\r': 0x0D, 'Å': 0x0E, 'å': 0x0F,
    # ... full table in 3GPP TS 23.038
}
for c in range(ord('A'), ord('Z') + 1):
    GSM7_BASIC[chr(c)] = c - ord('A') + 0x21  # offset for capital letters
for c in range(ord('a'), ord('z') + 1):
    GSM7_BASIC[chr(c)] = c - ord('a') + 0x41  # offset for lowercase letters  
for c in range(ord('0'), ord('9') + 1):
    GSM7_BASIC[chr(c)] = c - ord('0') + 0x10  # offset for digits

def encode_gsm7bit(text: str) -> bytes:
    """Encode text in GSM 7-bit default alphabet (simplified)."""
    # For production, use a complete GSM 7-bit lookup table
    # This simplified version handles basic ASCII
    septets = []
    for char in text:
        if char in '0123456789':
            septets.append(ord(char) - ord('0') + 0x10)
        elif char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            septets.append(ord(char) - ord('A') + 0x21)
        elif char in 'abcdefghijklmnopqrstuvwxyz':
            septets.append(ord(char) - ord('a') + 0x41)
        elif char == ' ':
            septets.append(0x20)
        elif char == '!':
            septets.append(0x61)
        elif char == '?':
            septets.append(0x63)
        elif char == '.':
            septets.append(0x2E)
        else:
            septets.append(0x20)  # replace unknown with space
    
    # Pack septets into bytes (7 bits per character)
    result = bytearray()
    i = 0
    bit_buffer = 0
    bits_in_buffer = 0
    
    for septet in septets:
        bit_buffer |= (septet & 0x7F) << bits_in_buffer
        bits_in_buffer += 7
        while bits_in_buffer >= 8:
            result.append(bit_buffer & 0xFF)
            bit_buffer >>= 8
            bits_in_buffer -= 8
    
    if bits_in_buffer > 0:
        result.append(bit_buffer & 0xFF)
    
    return bytes(result)
```

---

## 10. Does SMSoIP Work on Carrier IMS?

### Yes — With Caveats

| Carrier | SMSoIP Supported? | Notes |
|---------|-------------------|-------|
| **T-Mobile US** | ✅ Yes | Full VoLTE + SMSoIP support; Wi-Fi Calling uses SMSoIP |
| **AT&T** | ✅ Yes | VoLTE with SMS over IMS |
| **Verizon** | ✅ Yes | VoLTE + SMSoIP; critical since CDMA sunset |
| **Jio India** | ✅ Yes | Full IMS with VoLTE and SMSoIP |
| **Airtel India** | ✅ Yes | VoLTE + SMSoIP |
| **Vodafone UK** | ✅ Yes | VoLTE + VoWiFi + SMSoIP |
| **EE UK** | ✅ Yes | Full IMS services |
| **Most modern carriers** | ✅ Yes | SMSoIP is mandatory for VoLTE (GSMA IR.92) |

### Why SMSoIP Is Mandatory for VoLTE

**GSMA IR.92 (IMS Profile for Voice and SMS)** mandates SMSoIP for all VoLTE deployments. When 2G/3G networks are sunset (as has happened in the US, Australia, and other countries), SMS can ONLY be delivered via SMSoIP over the IMS infrastructure. There is no CS (circuit-switched) fallback.

This means:
- **All US carriers** must support SMSoIP because 2G/3G is gone
- **All VoLTE devices** include SMSoIP support
- **All IP-SM-GW equipment** in carrier networks supports SMSoIP routing
- **Wi-Fi Calling (VoWiFi)** also uses SMSoIP — when you're on Wi-Fi and send an SMS, it goes through the ePDG tunnel via SMSoIP

### Requirements for a Headless SMSoIP Client

| Requirement | Detail | Difficulty |
|-------------|--------|-----------|
| **SIP REGISTER on IMS** | Must include `+g.3gpp.smsip` in Contact | Easy |
| **AKAv1-MD5 authentication** | SIM-based IMS AKA | Hard (see headless-rcs-recipe.md) |
| **IPSec SA** | Required by most carrier P-CSCFs | Hard |
| **ePDG tunnel** (for data center access) | IKEv2 + EAP-AKA | Hard |
| **RP-DATA construction** | Binary frame per TS 24.011 | Medium |
| **SMS-SUBMIT TPDU construction** | Binary frame per TS 23.040 | Medium |
| **GSM 7-bit encoding** | Text must be GSM 7-bit encoded | Medium |
| **SMSC address** | Must know the carrier's SMSC number | Easy (from SIM or well-known) |
| **IP-SM-GW routing** | The S-CSCF's iFC handles this automatically | Easy (no client action needed) |

---

## 11. Self-Hosted IMS: SMSoIP Is Trivial

If you run your own IMS core (Open5GS + Kamailio), SMSoIP is significantly easier than on carrier IMS:

### Why It's Trivial

1. **No IPSec required** — Your own P-CSCF, your rules
2. **No ePDG needed** — Direct SIP from data center to P-CSCF
3. **K known** — You provision the K/OPc in the HSS, so VirtualSIM works
4. **IP-SM-GW is Open5GS SMS module** — Open5GS has built-in SMS support via the SMSF (SMS Function) in 5G, or via the SMSC component
5. **No geoblocking** — Your network, your rules

### Open5GS SMSoIP Configuration

Open5GS supports SMS natively in its 5G core (SMSF). For 4G/EPC, you need to configure the SMS path:

```yaml
# Open5GS configuration for SMS over IMS
# The MME/AMF routes SMS via SGs interface (4G) or via SMSF (5G)
# For IMS-based SMSoIP, the S-CSCF must have iFC rules to route
# application/vnd.3gpp.sms messages to the SMS application server
```

### Kamailio S-CSCF Configuration for SMSoIP

In a Kamailio-based IMS core, you configure iFC (Initial Filter Criteria) to route SMSoIP traffic:

```kamailio
# Route SMS over IP messages to the SMS Application Server
if (is_method("MESSAGE") && $hdr(Content-Type) =~ "application/vnd.3gpp.sms") {
    # Route to IP-SM-GW or local SMS handler
    route_to_sms_as();
}
```

---

## 12. Throughput Analysis

### SMSoIP Throughput (SIP MESSAGE-based)

| Factor | Value | Notes |
|--------|-------|-------|
| **SIP MESSAGE processing time** | 5-20ms per message | Server-side processing at P-CSCF + IP-SM-GW |
| **SMSC forwarding time** | 10-50ms per message | Depends on SMSC load |
| **End-to-end latency (MO)** | 50-200ms | From send to SMSC acceptance |
| **End-to-end latency (full delivery)** | 1-10 seconds | Until recipient gets the SMS |
| **Messages per second (single UE)** | 10-30 msg/sec | Limited by SIP transaction timers + SMSC |
| **Messages per second (100 UEs)** | 1,000-3,000 msg/sec | Parallel SIP MESSAGE flows |
| **Messages per second (1000 UEs)** | 10,000-30,000 msg/sec | With proper S-CSCF scaling |

### Comparison: SMSoIP vs RCS vs SMPP

| Metric | SMSoIP | RCS Pager-Mode | SMPP (direct to SMSC) |
|--------|--------|-----------------|------------------------|
| **Messages/second (single session)** | 10-30 | 5-15 | 1,000-10,000 |
| **Setup overhead** | IMS registration | IMS registration + capability disc. | SMPP BIND (1 round-trip) |
| **Per-message overhead** | 1 SIP round-trip | 1 SIP round-trip + CPIM | 1 SMPP SUBMIT_SM |
| **Latency (send to accept)** | 50-200ms | 50-200ms | 10-50ms |
| **Scalability** | Horizontal (more UEs) | Horizontal (more UEs) | Vertical (more binds) |
| **Rich media** | None | Text, links | None |
| **Delivery confirmation** | RP-ACK | IMDN | SMPP DELIVER_SM receipt |

**SMSoIP throughput is limited by the SIP transaction model** — each MESSAGE is a complete SIP transaction with its own Via branch, CSeq, and Call-ID. The P-CSCF and S-CSCF must process each transaction independently. For high-volume sending, SMPP directly to an SMSC is far more efficient.

However, **for a P2P messaging use case with ~100 SIMs, SMSoIP at 10-30 msg/sec per UE is more than sufficient.** At 100 UEs × 20 msg/sec = 2,000 messages/second = 172.8M messages/day.

---

## 13. What Does the Receiving Side See?

**The recipient sees a standard SMS — nothing more, nothing less.**

SMSoIP is transparent to the receiving UE:

1. The SMSC receives the SMS-SUBMIT TPDU from the IP-SM-GW
2. The SMSC stores the message and attempts delivery to the recipient
3. If the recipient is on a cellular network, the SMSC sends SMS-DELIVER via the radio interface
4. If the recipient is also registered on IMS with `+g.3gpp.smsip`, the IP-SM-GW can deliver via SIP MESSAGE directly
5. The recipient's phone shows the SMS in the standard messaging inbox

**There is NO indication to the recipient that the SMS was sent over IMS.** It looks identical to a regular SMS sent from the cellular radio interface.

This is a **major advantage** for reachability — you don't need the recipient to support RCS, SMSoIP, or anything special. Standard SMS delivery.

---

## 14. Google Messages and SMSoIP

### Does Google Messages Support SMSoIP?

**Yes, implicitly.** Google Messages uses the Android ImsService framework for IMS registration. When a phone registers on IMS via VoLTE/VoWiFi, the ImsService includes `+g.3gpp.smsip` in the Contact header as part of standard VoLTE registration per GSMA IR.92. All SMS messages sent while on VoLTE or VoWiFi use SMSoIP under the hood.

### When RCS Is Unavailable

When Google Messages cannot establish RCS (e.g., no data, RCS registration failed, recipient not RCS-capable), it **falls back to SMS/MMS**. The SMS fallback path on VoLTE/VoWiFi uses SMSoIP automatically — the user doesn't know or care.

The flow:
1. Google Messages tries RCS → fails
2. Google Messages sends via SMS
3. The Android ImsService detects the phone is on IMS (VoLTE/VoWiFi)
4. The SMS is sent via SMSoIP (SIP MESSAGE with `application/vnd.3gpp.sms`)
5. If SMSoIP also fails (no IMS registration), falls back to CS SMS over the radio interface

### For a Headless Client

A headless SMSoIP client does NOT need Google Messages. It directly constructs the SIP MESSAGE with the binary RP-DATA body and sends it through the IMS core. This bypasses the entire Google Messages / Jibe ecosystem.

---

## 15. SMSoIP as Minimum Viable Product

### The MVP Argument

For an IMS-based messaging system, the simplest viable product is:

```
Register on IMS (with +g.3gpp.smsip)
     → Send SMSoIP (SIP MESSAGE + binary RP-DATA)
     → Recipient gets standard SMS
     → Done.
```

**No RCS complexity needed.** No capability discovery, no MSRP, no CPIM, no IMDN, no Conversation-ID, no Contribution-ID, no feature tag negotiation.

### What You Get with SMSoIP MVP

| Feature | SMSoIP MVP | Full RCS |
|---------|-----------|----------|
| **Send text messages** | ✅ Yes (160 chars) | ✅ Yes (longer) |
| **Receive messages** | ✅ Yes | ✅ Yes |
| **Delivery confirmation** | ✅ RP-ACK | ✅ IMDN |
| **Read receipts** | ❌ No | ✅ Yes |
| **Typing indicators** | ❌ No | ⚠️ Session-mode only |
| **Rich media** | ❌ No | ✅ Yes |
| **Group chat** | ❌ No | ✅ Yes |
| **Works without RCS on recipient** | ✅ Yes | ❌ No |
| **Works on any IMS registration** | ✅ Yes | ❌ Needs RCS feature tags |
| **Implementation complexity** | Low | High |
| **Carrier compatibility** | Universal (all VoLTE) | Varies |

### Recommended Phased Approach

1. **Phase 1: SMSoIP MVP** — IMS registration + SMSoIP sending. Get to market fast. Prove the IMS connection works.
2. **Phase 2: Add RCS pager-mode** — After SMSoIP works, add `message/cpim` body format with RCS feature tags for RCS-to-RCS messaging.
3. **Phase 3: Add RCS session-mode** — For conversational chat with typing indicators, add MSRP.
4. **Phase 4: Rich media** — HTTP file transfer, rich cards via RCS.

---

## 16. Implementation Guide: SMSoIP Sender

### Minimal Python SMSoIP Client

```python
#!/usr/bin/env python3
"""
Minimal SMSoIP Client: Send SMS over IMS via SIP MESSAGE.
Requires: IMS registration (see headless-rcs-recipe.md)
"""
import socket
import struct
import uuid

def send_smsoip(
    pcscf_addr: str,
    pcscf_port: int,
    local_ip: str,
    local_port: int,
    sender_msisdn: str,
    recipient_msisdn: str,
    text: str,
    sender_sip_uri: str,
    domain: str,
    smSC_address: str = "",
    message_ref: int = 1,
) -> bool:
    """Send an SMS over IMS using SMSoIP (SIP MESSAGE with RP-DATA)."""
    
    # 1. Build the SMS-SUBMIT TPDU
    tpdu = build_sms_submit_tpdu(
        dest_address=recipient_msisdn,
        text=text,
        message_ref=message_ref,
        dcs=0x00,  # GSM 7-bit
        validity_period=167,  # 24 hours
    )
    
    # 2. Build the RP-DATA frame
    rp_data = build_rp_data_mo(tpdu, message_ref, smSC_address)
    
    # 3. Build the SIP MESSAGE
    call_id = f"{uuid.uuid4().hex[:8]}@{local_ip}"
    branch = f"z9hG4bK-{uuid.uuid4().hex[:8]}"
    tag = f"smsoip{message_ref}"
    cseq = message_ref
    
    sip_message = (
        f"MESSAGE tel:{recipient_msisdn};phone-context={domain} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch={branch}\r\n"
        f"Max-Forwards: 70\r\n"
        f"From: <sip:{sender_msisdn}@{domain}>;tag={tag}\r\n"
        f"To: <tel:{recipient_msisdn};phone-context={domain}>\r\n"
        f"Call-ID: {call_id}\r\n"
        f"CSeq: {cseq} MESSAGE\r\n"
        f"Contact: <sip:{sender_msisdn}@{local_ip}:{local_port}>;"
        f"+g.3gpp.smsip\r\n"
        f"Content-Type: application/vnd.3gpp.sms\r\n"
        f"Allow: MESSAGE\r\n"
        f"Request-Disposition: no-fork\r\n"
        f"Content-Length: {len(rp_data)}\r\n"
        f"\r\n"
    )
    
    # Send via UDP (binary body appended after SIP headers)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((local_ip, local_port))
    message_bytes = sip_message.encode('ascii') + rp_data
    sock.sendto(message_bytes, (pcscf_addr, pcscf_port))
    
    # Wait for 202 Accepted
    sock.settimeout(5.0)
    try:
        data, addr = sock.recvfrom(4096)
        response = data.decode('ascii', errors='replace')
        if "202" in response:
            print(f"✅ SMSoIP accepted (202) for {recipient_msisdn}")
            return True
        elif "200" in response:
            print(f"✅ SMSoIP accepted (200) for {recipient_msisdn}")
            return True
        else:
            print(f"❌ SMSoIP failed: {response[:200]}")
            return False
    except socket.timeout:
        print(f"❌ SMSoIP timeout for {recipient_msisdn}")
        return False
    finally:
        sock.close()
```

### Handling the RP-ACK (Delivery Confirmation)

After sending the MO-SMS, you'll receive a SIP MESSAGE back from the IP-SM-GW containing the RP-ACK:

```python
def handle_rp_ack_message(sip_message: bytes):
    """Handle incoming SIP MESSAGE containing RP-ACK from IP-SM-GW."""
    # The body will be application/vnd.3gpp.sms containing RP-ACK
    body_start = sip_message.find(b'\r\n\r\n')
    if body_start == -1:
        return
    
    rp_body = sip_message[body_start + 4:]
    
    # Parse RP-ACK
    msg_type = rp_body[0]
    if msg_type == 0x01:
        msg_ref = rp_body[1]
        print(f"✅ RP-ACK received for message reference {msg_ref}")
        # The SMS was accepted by the SMSC
    elif msg_type == 0x04:
        # RP-ERROR — SMS delivery failed
        print(f"❌ RP-ERROR received — SMS delivery failed")
    
    # Send 200 OK for the RP-ACK SIP MESSAGE
    # (must send 200 OK back to acknowledge receipt of the RP-ACK)
```

---

## 17. Limitations and Risks

### Technical Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|-----------|
| **Binary RP-DATA construction** | Must build GSM 03.40/03.11 binary frames | Use a TPDU library (python-gsm or custom) |
| **160-character limit** | GSM 7-bit: 160 chars; UCS-2: 70 chars | Use concatenated SMS (TP-UDHI + UDH) for longer messages |
| **No rich media** | Only text, no images/cards/buttons | Layer RCS on top when needed |
| **No read receipts** | Only delivery confirmation (RP-ACK) | Use RCS IMDN when RCS is available |
| **SIP transaction overhead** | Each SMS is a separate SIP transaction | Batch sending, connection reuse |
| **IPSec requirement on carriers** | Must establish IPSec SAs for P-CSCF access | Use ePDG tunnel (provides IPSec) or self-hosted IMS |

### Legal and Operational Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **Carrier fraud detection** | High | Rate-limit per SIM, rotate SIMs, vary timing |
| **SIM deactivation** | Medium | Use prepaid SIMs from multiple carriers |
| **IPSec non-compliance** | Medium | Self-hosted IMS avoids this; ePDG provides it |
| **SMSC rate limiting** | Low | Most SMSCs handle high volume; spread across multiple SMSCs |
| **UK SIM farm ban (2025)** | Jurisdiction-specific | Avoid UK operations; check local laws |

---

# PART 2: RCS Advertising Platform Design

## 18. Market Opportunity

### Market Size and Growth

| Metric | Value | Source |
|--------|-------|--------|
| **RCS market size (2026)** | $3.59B - $9.5B | Mordor Intelligence / Business Research Insights |
| **RCS market CAGR** | 16-25% | Multiple analysts |
| **Projected market (2031)** | $10.9B | Mordor Intelligence |
| **Projected market (2035)** | $36.08B | Business Research Insights |
| **Business RCS traffic (2026)** | 200+ billion messages | Juniper Research |
| **RCS subscriber base (2026)** | 3.5B (40% of mobile subscribers) | Juniper Research |
| **RCS Business messaging growth** | 111% YoY usage increase | Master of Code |

### Why Now?

1. **Apple iOS 18+ supports RCS** — As of iOS 18 (Sept 2024), iPhones support RCS, expanding the addressable market from Android-only to universal
2. **2G/3G sunset** — SMS fallback is less reliable as CS networks shut down; RCS is the future
3. **Google RBM maturity** — Google's RCS Business Messaging (RBM) platform is stable and widely deployed
4. **CPaaS market growth** — Communications Platform as a Service is a $15B+ market, with RCS as the fastest-growing channel
5. **Conversion rate advantage** — RCS drives 6.2x ROI and up to 80% conversion rates vs. SMS at ~5-15% (Master of Code, 2026)
6. **End-to-end encryption** — iOS 26.5 (May 2026) adds E2EE for RCS, increasing consumer trust

### RCS vs SMS Conversion Benchmarks

| Metric | SMS | RCS | Improvement |
|--------|-----|-----|------------|
| **Open rate** | 82-98% | 82-98% | Same (both to messaging inbox) |
| **Click-through rate** | 5-10% | 15-35% | 2-5x |
| **Conversion rate** | 5-15% | 20-80% | 3-8x |
| **Read receipts** | No | Yes | ✅ |
| **Brand verification** | No (spoofable) | Yes (verified sender) | ✅ |
| **Rich media** | No | Yes (cards, carousels, video) | ✅ |
| **Interactive buttons** | No (reply only) | Yes (up to 11 buttons) | ✅ |
| **Cost per message** | $0.003-0.02 | $0.01-0.05 | 2-5x more expensive |

---

## 19. Platform Architecture Overview

### High-Level Architecture

```
                        ┌─────────────────────────┐
                        │   External API Users     │
                        │   (brands, agencies)     │
                        └───────────┬─────────────┘
                                    │ HTTPS
                        ┌───────────▼─────────────┐
                        │   API Gateway / Load      │
                        │   Balancer (nginx/Traefik)│
                        └───────────┬─────────────┘
                                    │
             ┌──────────────────────▼──────────────────────┐
             │          FastAPI Application Server          │
             │                                              │
             │  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
             │  │ Campaign  │ │ Contact  │ │ Analytics│    │
             │  │ Manager   │ │ Manager  │ │ Engine   │    │
             │  └─────┬────┘ └─────┬────┘ └─────┬────┘    │
             │        │            │             │          │
             │  ┌─────▼────────────▼─────────────▼────┐   │
             │  │         Message Router               │   │
             │  │  (RCS → RBM API / SMS → SMPP)        │   │
             │  └─────┬──────────────┬──────────────┘   │
             │        │              │                    │
             │  ┌─────▼──────┐  ┌───▼──────────┐        │
             │  │ RBM Agent   │  │ SMPP Client  │        │
             │  │ Manager     │  │ (SMS fallback)│       │
             │  └─────┬──────┘  └───┬──────────┘        │
             │        │              │                    │
             │  ┌─────▼──────┐  ┌───▼──────────┐        │
             │  │ Google RBM  │  │ SMSC / CPaaS │        │
             │  │ API         │  │ (Twilio/Info) │       │
             │  └────────────┘  └────────────┘        │
             │                                              │
             │  ┌──────────────┐ ┌─────────────────────┐  │
             │  │ PostgreSQL   │ │ Redis (queues/caches)│  │
             │  └──────────────┘ └─────────────────────┘  │
             │  ┌──────────────┐ ┌─────────────────────┐  │
             │  │ Webhook      │ │ A/B Testing Engine   │  │
             │  │ Dispatcher   │ │                      │  │
             │  └──────────────┘ └─────────────────────┘  │
             └──────────────────────────────────────────────┘
```

---

## 20. Multi-Tenant SaaS Design

### Tenant Model

Each **tenant** is a brand or organization. Each tenant can have:

| Entity | Description | Per-tenant? |
|--------|-------------|-------------|
| **Brand** | Legal entity (verified with Google) | Yes, 1:1 with tenant |
| **RBM Agent(s)** | Messaging agents (e.g., "Support", "Marketing", "Sales") | Yes, 1:N |
| **Contacts** | Audience segments, opt-in lists | Yes |
| **Campaigns** | Message campaigns with scheduling | Yes |
| **Templates** | Message templates (rich cards, text) | Yes |
| **API Keys** | REST API credentials | Yes |
| **Webhooks** | Event notification endpoints | Yes |
| **Users** | Platform users (marketers, admins) | Yes |
| **Billing** | Usage tracking, invoices | Yes |

### Data Isolation Strategy

```
┌──────────────────────────────────────┐
│          PostgreSQL Database          │
│                                      │
│  Schema: public                      │
│  ├── tenants (id, name, settings)    │
│  ├── users (id, tenant_id, ...)     │
│  ├── agents (id, tenant_id, ...)     │
│  ├── contacts (id, tenant_id, ...)   │
│  ├── campaigns (id, tenant_id, ...)  │
│  ├── messages (id, tenant_id, ...)   │
│  ├── templates (id, tenant_id, ...)  │
│  ├── analytics (id, tenant_id, ...)  │
│  └── webhooks (id, tenant_id, ...)   │
│                                      │
│  All queries filtered by tenant_id   │
│  Row-Level Security (RLS) enforced   │
└──────────────────────────────────────┘
```

Use **shared database, shared schema** with `tenant_id` on every table and PostgreSQL Row-Level Security (RLS) for isolation. This is the most cost-effective approach for a SaaS with thousands of tenants.

---

## 21. Campaign Management

### Campaign Entity

```python
class Campaign:
    id: UUID
    tenant_id: UUID
    name: str
    status: str  # draft, scheduled, running, paused, completed, archived
    agent_id: UUID  # Which RBM agent sends the messages
    
    # Targeting
    contact_list_ids: List[UUID]  # Which contact lists
    segment_filter: dict  # Dynamic segment rules
    
    # Scheduling
    schedule_type: str  # immediate, scheduled, drip
    scheduled_at: datetime  # For scheduled campaigns
    timezone: str  # User timezone for scheduling
    
    # Message content
    message_variants: List[MessageVariant]  # For A/B testing
    
    # Throttling
    messages_per_second: int  # Rate limit (default: 10)
    daily_limit: int  # Max messages per day
    quiet_hours_start: time  # No sending during quiet hours
    quiet_hours_end: time
    
    # Fallback
    sms_fallback: bool  # Fall back to SMS if RCS unavailable
    sms_fallback_text: str  # Shorter text for SMS fallback
    
    # Metadata
    created_by: UUID
    created_at: datetime
    updated_at: datetime
```

### Campaign Workflow

```
Create Campaign (draft)
    → Define audience (contact lists / segments)
    → Create message variants (for A/B testing)
    → Set schedule (immediate / scheduled / drip)
    → Configure throttling & quiet hours
    → Review & approve
    → Launch
    → Monitor (real-time analytics)
    → Complete / Pause / Archive
```

### Campaign State Machine

```
draft → scheduled → running → completed
                    ↓
                   paused → running
                            ↓
                          archived
```

---

## 22. A/B Testing Framework

### Message Variants

Each campaign can have multiple message variants for A/B testing:

| Variant Type | Description | Example |
|-------------|-------------|---------|
| **Text vs Rich Card** | Plain text vs. rich card with image | "Sale!" text vs. card with product image |
| **Different copy** | Different text versions | "Save 20%" vs. "Get 20% off today" |
| **Different CTA buttons** | Different button labels/URLs | "Shop Now" vs. "Browse Deals" |
| **Carousel vs Single Card** | Multiple cards vs. one card | 4-product carousel vs. featured product |
| **With/without suggested replies** | Quick reply chips vs. no chips | "Yes/No" chips vs. open-ended |
| **Timing** | Same content, different send times | Morning vs. evening |

### A/B Test Configuration

```python
class ABTest:
    id: UUID
    campaign_id: UUID
    name: str
    
    # Split
    traffic_split: dict  # {"variant_a": 50, "variant_b": 50}
    
    # Goal
    primary_metric: str  # "click_rate", "reply_rate", "conversion_rate"
    
    # Statistical settings
    confidence_level: float  # 0.95 (95% confidence)
    minimum_sample_size: int  # 1000 per variant
    
    # Auto-optimization
    auto_winner: bool  # Automatically send winner to remaining audience
    winner_threshold: float  # p-value < 0.05
    
    status: str  # running, winner_found, concluded
    winning_variant_id: UUID  # Set when winner found
```

### A/B Test Execution

```python
async def assign_variant(test: ABTest, contact_id: UUID) -> UUID:
    """Assign a contact to a variant using consistent hashing."""
    # Deterministic assignment: same contact always gets same variant
    # (prevents a contact from receiving multiple variants)
    hash_val = hash(f"{test.id}:{contact_id}") % 100
    
    cumulative = 0
    for variant_id, percentage in test.traffic_split.items():
        cumulative += percentage
        if hash_val < cumulative:
            return variant_id
    
    # Fallback to first variant
    return list(test.traffic_split.keys())[0]
```

---

## 23. Analytics and Reporting

### Key Metrics

| Metric | Definition | Collection Method |
|--------|-----------|-------------------|
| **Sent** | Messages dispatched to RBM/SMSC | Internal counter |
| **Delivered** | Messages received on device | RBM delivery event / SMPP DLR |
| **Read** | Messages displayed to user | RBM read event |
| **Replied** | User responded to message | RBM reply event |
| **Clicked** | User clicked a button/link | RBM button click event |
| **Converted** | User completed desired action | Postback / webhook attribution |
| **Opted Out** | User unsubscribed | RBM opt-out event |
| **Bounced** | Message not deliverable | RBM error / SMPP error |
| **Fallback Rate** | % sent via SMS instead of RCS | Internal tracking |

### Real-Time Analytics Pipeline

```
RBM Event Webhook → FastAPI endpoint → Redis Stream → 
    → Analytics Worker (aggregate) → PostgreSQL (time-series)
    → Webhook Dispatcher (forward to tenant)
    → Dashboard (WebSocket push)
```

### Dashboard Metrics

```python
class CampaignAnalytics:
    campaign_id: UUID
    date: date
    
    # Volume
    sent_count: int
    delivered_count: int
    read_count: int
    replied_count: int
    clicked_count: int
    opted_out_count: int
    bounced_count: int
    fallback_count: int
    
    # Rates
    delivery_rate: float  # delivered / sent
    read_rate: float  # read / delivered
    reply_rate: float  # replied / delivered
    click_rate: float  # clicked / delivered
    opt_out_rate: float  # opted_out / delivered
    bounce_rate: float  # bounced / sent
    
    # Per-variant (for A/B testing)
    variant_metrics: Dict[str, VariantMetrics]
```

---

## 24. Inbox Management: Conversational Messaging

### Why Inbox Matters

RCS Business Messaging supports **two-way conversations**. When a customer replies to an RCS message, the brand needs to handle that reply. This is different from traditional SMS marketing (one-way blast).

### Inbox Architecture

```
┌─────────────────────────────────────────────┐
│              Inbox Manager                    │
│                                              │
│  ┌───────────────┐  ┌────────────────────┐  │
│  │ Conversation  │  │ Auto-Response      │  │
│  │ List          │  │ Rules Engine       │  │
│  │ (per agent)   │  │ (keyword matching, │  │
│  │               │  │  AI chatbot hook)  │  │
│  └───────┬───────┘  └────────┬───────────┘  │
│          │                    │              │
│  ┌───────▼────────────────────▼───────────┐  │
│  │          Agent Assignment             │  │
│  │  (route to human agent or chatbot)     │  │
│  └───────────────────────────────────────┘  │
│                                              │
│  ┌───────────────┐  ┌────────────────────┐  │
│  │ Human Agent   │  │ Chatbot / AI       │  │
│  │ Dashboard     │  │ Integration        │  │
│  │ (WebSocket)   │  │ (OpenAI, Dialogflow)│  │
│  └───────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────┘
```

### Conversation Model

```python
class Conversation:
    id: UUID
    tenant_id: UUID
    agent_id: UUID
    contact_id: UUID
    contact_phone: str
    status: str  # open, closed, escalated
    
    # Routing
    assigned_to: UUID  # Human agent ID or null (chatbot)
    routing_rule: str  # "chatbot", "human", "round_robin", "skill_based"
    
    # Context
    last_message_at: datetime
    last_message_text: str
    unread_count: int
    
    # Metadata
    created_at: datetime
    tags: List[str]  # ["support", "billing", "vip"]
```

---

## 25. Contact Management and Compliance

### Contact Model

```python
class Contact:
    id: UUID
    tenant_id: UUID
    phone_number: str  # E.164 format
    first_name: str
    last_name: str
    email: str
    
    # Opt-in/Opt-out status
    rcs_opted_in: bool
    sms_opted_in: bool
    opted_out: bool
    opt_out_date: datetime
    opt_in_source: str  # "web_form", "keyword", "import", "api"
    opt_in_date: datetime
    
    # Segmentation
    lists: List[UUID]  # Contact list memberships
    tags: List[str]  # Arbitrary tags
    custom_fields: dict  # {"city": "NYC", "vip": true}
    
    # Engagement history
    last_message_at: datetime
    total_messages_received: int
    total_messages_replied: int
    
    # RCS capability
    rcs_capable: bool  # Detected via RBM capability check
    last_capability_check: datetime
```

### Compliance Features

| Feature | Description | Implementation |
|---------|-------------|----------------|
| **Opt-in management** | Track and enforce opt-in consent | Database field + API enforcement |
| **Opt-out handling** | Honor STOP/UNSUBSCRIBE keywords automatically | Keyword detection → set opted_out flag |
| **TCPA compliance** | Time-of-day restrictions, consent records | Quiet hours + opt-in audit trail |
| **10DLC registration** | A2P 10DLC brand/campaign registration | Integration with The Campaign Registry (TCR) |
| **RCS brand verification** | Google brand verification for RBM agents | Google Business Communications API |
| **Data retention** | Configurable retention periods | TTL on analytics + GDPR right-to-deletion |
| **Suppression list** | Global do-not-send list | Cross-tenant suppression (phone number hash) |

---

## 26. Pricing Model

### Three Pricing Tiers

| Tier | Monthly Fee | Per-Message RCS | Per-Message SMS (fallback) | Target |
|------|------------|----------------|---------------------------|--------|
| **Starter** | $99/mo | $0.035/msg | $0.015/msg | Small businesses, <10K msgs/mo |
| **Growth** | $499/mo | $0.025/msg | $0.012/msg | Mid-market, 10K-500K msgs/mo |
| **Enterprise** | Custom | $0.015-0.020/msg | $0.008-0.010/msg | Large brands, 500K+ msgs/mo |

### Revenue Per Message: Margin Analysis

| Cost Component | RCS | SMS |
|---------------|-----|-----|
| **Carrier/carriage fee** | $0.005-0.015 | $0.003-0.008 |
| **Google RBM fee** | $0.001-0.003 | N/A |
| **CPaaS aggregator markup** | $0.003-0.008 | $0.002-0.005 |
| **Our cost** | $0.010-0.025 | $0.005-0.013 |
| **Our price (Growth tier)** | $0.025 | $0.012 |
| **Our gross margin** | $0.005-0.015 (20-60%) | $0.002-0.007 (15-55%) |

### Pricing Strategy

**Hybrid model: Monthly subscription + per-message usage.**

- **Monthly subscription** covers platform access, agent management, analytics dashboard, API access
- **Per-message fees** cover the variable cost of message delivery + margin
- **Volume discounts** at Enterprise tier incentivize scale
- **White-label surcharge** for agencies: +30-50% markup on per-message fees

### Comparison with Competitors

| Provider | RCS Price/Msg | Platform Fee | Notes |
|----------|-------------|-------------|-------|
| **Twilio** | ~$0.01-0.05 | Usage-based only | Largest CPaaS, good API |
| **Infobip** | ~$0.02-0.05 | Custom pricing | Full-stack, global reach |
| **Sinch** | ~$0.02-0.04 | Custom pricing | Strong carrier relationships |
| **Vonage** | ~$0.02-0.04 | Usage-based | Part of Nexmo/Mapon acquisition |
| **Bandwidth** | ~$0.01-0.03 | Usage-based | US-focused, own network |
| **Our platform** | $0.015-0.035 | $99-499/mo | Competitive, white-label option |

---

## 27. White-Label / Agency Reseller

### White-Label Architecture

```
┌──────────────────────────────────────────────────┐
│                White-Label Layer                   │
│                                                    │
│  ┌──────────────┐  ┌──────────────┐              │
│  │ Agency A     │  │ Agency B     │              │
│  │ Portal       │  │ Portal       │              │
│  │ (branding A) │  │ (branding B) │              │
│  └──────┬───────┘  └──────┬───────┘              │
│         │                  │                      │
│  ┌──────▼──────────────────▼──────────────────┐   │
│  │         Core Platform (same codebase)       │   │
│  │  with per-reseller branding config           │   │
│  │  (logo, colors, domain, email templates)    │   │
│  └──────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

### Reseller Features

| Feature | Description |
|---------|-------------|
| **Custom branding** | Logo, colors, favicon, domain (CNAME) |
| **Custom pricing** | Reseller sets their own markup |
| **Multi-brand management** | Reseller manages multiple brand tenants |
| **Separate billing** | Reseller bills their clients directly |
| **API access** | Reseller gets master API key for all tenants |
| **White-label support** | Support emails from reseller's domain |
| **Custom domain** | `rcs.agency.com` instead of `platform.com` |

---

## 28. REST API Design

### Core Endpoints

```yaml
# Authentication
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
DELETE /api/v1/auth/logout

# Agents (RBM Agent Management)
GET    /api/v1/agents
POST   /api/v1/agents
GET    /api/v1/agents/{agent_id}
PATCH  /api/v1/agents/{agent_id}
POST   /api/v1/agents/{agent_id}/launch  # Submit for Google verification

# Contacts
GET    /api/v1/contacts
POST   /api/v1/contacts
POST   /api/v1/contacts/import  # CSV/bulk import
GET    /api/v1/contacts/{contact_id}
PATCH  /api/v1/contacts/{contact_id}
DELETE /api/v1/contacts/{contact_id}
POST   /api/v1/contacts/check-capability  # Check RCS capability

# Contact Lists
GET    /api/v1/lists
POST   /api/v1/lists
GET    /api/v1/lists/{list_id}
PATCH  /api/v1/lists/{list_id}
POST   /api/v1/lists/{list_id}/add
POST   /api/v1/lists/{list_id}/remove

# Campaigns
GET    /api/v1/campaigns
POST   /api/v1/campaigns
GET    /api/v1/campaigns/{campaign_id}
PATCH  /api/v1/campaigns/{campaign_id}
POST   /api/v1/campaigns/{campaign_id}/launch
POST   /api/v1/campaigns/{campaign_id}/pause
POST   /api/v1/campaigns/{campaign_id}/resume

# Templates
GET    /api/v1/templates
POST   /api/v1/templates
GET    /api/v1/templates/{template_id}
PATCH  /api/v1/templates/{template_id}
DELETE /api/v1/templates/{template_id}

# Messages (Programmatic sending)
POST   /api/v1/messages/send         # Send single message
POST   /api/v1/messages/send/bulk    # Send bulk messages
GET    /api/v1/messages/{message_id}  # Get message status

# Conversations (Inbox)
GET    /api/v1/conversations
GET    /api/v1/conversations/{conversation_id}
POST   /api/v1/conversations/{conversation_id}/reply
POST   /api/v1/conversations/{conversation_id}/close

# Analytics
GET    /api/v1/analytics/campaigns/{campaign_id}
GET    /api/v1/analytics/dashboard
GET    /api/v1/analytics/agents/{agent_id}
POST   /api/v1/analytics/export  # CSV/PDF export

# Webhooks
GET    /api/v1/webhooks
POST   /api/v1/webhooks
PATCH  /api/v1/webhooks/{webhook_id}
DELETE /api/v1/webhooks/{webhook_id}
POST   /api/v1/webhooks/{webhook_id}/test

# A/B Tests
GET    /api/v1/campaigns/{campaign_id}/ab-tests
POST   /api/v1/campaigns/{campaign_id}/ab-tests
GET    /api/v1/campaigns/{campaign_id}/ab-tests/{test_id}/results
```

### Send Message API Example

```json
POST /api/v1/messages/send
Authorization: Bearer sk_live_xxx
Content-Type: application/json

{
  "agent_id": "agent_abc123",
  "to": "+14155551234",
  "content": {
    "type": "rich_card",
    "title": "Summer Sale! 🌞",
    "description": "Get 30% off all summer items this weekend only.",
    "media": {
      "url": "https://cdn.brand.com/summer-sale.jpg",
      "height": "medium"
    },
    "suggestions": [
      {
        "reply": {"text": "Show me deals", "postback": "show_deals"}
      },
      {
        "action": {
          "text": "Shop Now",
          "url": "https://shop.brand.com/sale",
          "postback": "shop_now_click"
        }
      }
    ]
  },
  "fallback_sms_text": "Summer Sale! 30% off this weekend. Shop: https://shop.brand.com/sale",
  "metadata": {
    "campaign_id": "camp_xyz",
    "variant": "A"
  }
}
```

---

## 29. Webhook Event Notifications

### Supported Events

| Event | Trigger | Payload |
|-------|---------|---------|
| `message.sent` | Message dispatched | message_id, agent_id, to, timestamp |
| `message.delivered` | Message received on device | message_id, device_timestamp |
| `message.read` | Message displayed to user | message_id, read_timestamp |
| `message.failed` | Delivery failed | message_id, error_code, error_description |
| `message.replied` | User replied to message | message_id, reply_text, reply_timestamp |
| `message.button_clicked` | User clicked a button | message_id, button_id, postback_data |
| `contact.opted_in` | Contact opted in | contact_id, phone, source |
| `contact.opted_out` | Contact opted out (STOP) | contact_id, phone, opt_out_keyword |
| `contact.rcs_capability` | RCS capability detected | contact_id, phone, rcs_capable |
| `agent.verified` | RBM agent verified by Google | agent_id, carrier_networks |
| `campaign.completed` | Campaign finished sending | campaign_id, stats_summary |
| `ab_test.winner` | A/B test found statistical winner | test_id, winning_variant_id, confidence |

### Webhook Payload Format

```json
POST https://tenant.example.com/webhooks/rcs
X-Webhook-Signature: sha256=abc123...
X-Webhook-Event: message.delivered
Content-Type: application/json

{
  "id": "evt_abc123",
  "event": "message.delivered",
  "timestamp": "2026-05-16T14:30:00Z",
  "data": {
    "message_id": "msg_xyz789",
    "agent_id": "agent_abc123",
    "contact_phone": "+14155551234",
    "delivered_at": "2026-05-16T14:30:01Z"
  },
  "metadata": {
    "campaign_id": "camp_001",
    "variant": "A",
    "custom": {"user_id": "usr_456"}
  }
}
```

### Webhook Security

- **HMAC-SHA256 signature** in `X-Webhook-Signature` header
- **Retry with exponential backoff** (up to 5 attempts over 24 hours)
- **Idempotency key** in each event to prevent duplicate processing
- **Event log** stored for 30 days for debugging

---

## 30. Google RBM Agent Registration Flow

### Step-by-Step Process

```
1. Register as Google RBM Partner
   → https://developers.google.com/business-communications/rcs-business-messaging
   → Sign up with Google account
   → Complete partner profile

2. Create a Brand
   → In the RBM Developer Console
   → Brand name, logo, website, description
   → Brand point of contact (email, phone)
   → Category (e.g., "Retail", "Banking")

3. Create an RBM Agent
   → Agent name, description, logo
   → Agent color (branding)
   → Agent phone number (sender ID)
   → Landing page URL
   → Privacy policy URL
   → Agent capabilities (rich cards, suggested replies, etc.)

4. Brand Verification
   → Google sends a verification email to the brand's point of contact
   → Brand contact must respond to confirm
   → Google reviews the agent for policy compliance
   → Processing time: 1-5 business days

5. Carrier Launch
   → Submit agent to specific carrier networks
   → Each carrier reviews independently
   → Carrier approval times vary (1-14 business days)
   → US carriers (T-Mobile, AT&T, Verizon) are typically fastest

6. Agent Goes Live
   → Agent is active on approved carrier networks
   → Can send RBM messages to subscribers on those networks
   → Capability check: GET /v1/phones/{phone}/capabilities
```

### Automation for Multi-Tenant Platform

For a multi-tenant SaaS, you need to automate or semi-automate the RBM agent creation:

| Step | Automated? | Method |
|------|-----------|--------|
| **Partner registration** | ❌ Manual (one-time) | Console setup |
| **Brand creation** | ✅ Semi-auto | RBM Management API (brands.create) |
| **Agent creation** | ✅ Automated | RBM Management API (agents.create) |
| **Brand verification** | ❌ Manual | Brand contact must respond to email |
| **Carrier launch** | ✅ Automated | RBM Management API (agents.launch) |
| **Capability check** | ✅ Automated | RBM API (phones.getCapabilities) |

### RBM Management API for Automation

```python
import google.auth
from google.oauth2 import service_account

async def create_rbm_agent(brand_id: str, agent_config: dict) -> str:
    """Create an RBM agent via the Google Business Communications API."""
    from googleapiclient.discovery import build
    
    credentials = service_account.Credentials.from_service_account_file(
        'service-account.json',
        scopes=['https://www.googleapis.com/auth/businesscommunications']
    )
    service = build('businesscommunications', 'v1', credentials=credentials)
    
    agent = {
        'displayName': agent_config['name'],
        'brandId': brand_id,
        'description': agent_config['description'],
        'logoUrl': agent_config['logo_url'],
        'phoneNumber': agent_config['phone_number'],
        'landingPageUrl': agent_config['landing_page_url'],
        'capabilities': {
            'richCard': True,
            'suggestedReplies': True,
            'suggestedActions': True,
        }
    }
    
    result = service.brands().agents().create(
        parent=f'brands/{brand_id}',
        body=agent
    ).execute()
    
    return result['name']  # Agent resource name
```

---

## 31. Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **API Framework** | FastAPI (Python 3.12+) | Async, auto-docs, type-safe |
| **Database** | PostgreSQL 16 | RLS for multi-tenancy, JSONB for flexibility |
| **Cache/Queue** | Redis 7+ | Pub/Sub for webhooks, caching, session management |
| **Task Queue** | Celery + Redis | Campaign sending, webhook dispatch |
| **Message Routing** | Google RBM API + SMPP | RBM for RCS, SMPP for SMS fallback |
| **Auth** | JWT + OAuth2 | Standard token-based auth |
| **Monitoring** | Prometheus + Grafana | Industry standard |
| **CI/CD** | GitHub Actions | Standard |
| **Infrastructure** | AWS / GCP (Kubernetes) | Scale horizontally |
| **Frontend** | React + Next.js | Dashboard for campaign management |
| **Real-time** | WebSocket (FastAPI) | Live campaign monitoring, inbox |

---

## 32. Database Schema

### Core Tables

```sql
-- Tenants
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'starter',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RBM Agents
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    brand_id VARCHAR(255),  -- Google RBM brand ID
    agent_id VARCHAR(255) UNIQUE,  -- Google RBM agent ID
    name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20),
    status VARCHAR(50) DEFAULT 'pending',  -- pending, verified, active, suspended
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Contacts
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    phone_number VARCHAR(20) NOT NULL,  -- E.164
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    email VARCHAR(255),
    rcs_opted_in BOOLEAN DEFAULT FALSE,
    sms_opted_in BOOLEAN DEFAULT FALSE,
    opted_out BOOLEAN DEFAULT FALSE,
    rcs_capable BOOLEAN,
    custom_fields JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, phone_number)
);

-- Contact Lists
CREATE TABLE contact_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    contact_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE contact_list_members (
    list_id UUID NOT NULL REFERENCES contact_lists(id) ON DELETE CASCADE,
    contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (list_id, contact_id)
);

-- Campaigns
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    agent_id UUID NOT NULL REFERENCES agents(id),
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft',
    schedule_type VARCHAR(50) DEFAULT 'immediate',
    scheduled_at TIMESTAMPTZ,
    sms_fallback BOOLEAN DEFAULT TRUE,
    sms_fallback_text TEXT,
    throttling JSONB DEFAULT '{"mps": 10, "daily_limit": 10000}',
    quiet_hours JSONB DEFAULT '{"start": "21:00", "end": "08:00", "timezone": "America/New_York"}',
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Messages
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    campaign_id UUID REFERENCES campaigns(id),
    agent_id UUID NOT NULL REFERENCES agents(id),
    contact_id UUID NOT NULL REFERENCES contacts(id),
    phone_number VARCHAR(20) NOT NULL,
    direction VARCHAR(10) DEFAULT 'outbound',  -- inbound, outbound
    channel VARCHAR(10) DEFAULT 'rcs',  -- rcs, sms
    status VARCHAR(50) DEFAULT 'queued',  -- queued, sent, delivered, read, failed
    content JSONB NOT NULL,  -- Message content (rich card, text, etc.)
    variant_id UUID,  -- For A/B testing
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    replied_at TIMESTAMPTZ,
    error_code VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Row-Level Security
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON contacts USING (tenant_id = current_setting('app.tenant_id')::UUID);

-- Indexes for performance
CREATE INDEX idx_messages_tenant_status ON messages(tenant_id, status);
CREATE INDEX idx_messages_campaign ON messages(campaign_id);
CREATE INDEX idx_contacts_tenant_phone ON contacts(tenant_id, phone_number);
CREATE INDEX idx_messages_created_at ON messages(created_at);
```

---

## 33. Competitive Landscape

### Major RCS Platform Providers

| Provider | Type | Strengths | Weaknesses |
|----------|------|-----------|-----------|
| **Infobip** | CPaaS | Global reach, full-stack, Moments platform | Expensive, complex pricing |
| **Twilio** | CPaaS | Best API, largest ecosystem, simple pricing | RCS is new to them, limited carrier direct |
| **Sinch** | CPaaS | Strong carrier relationships, good delivery | Brand verification can be slow |
| **Vonage** | CPaaS | Unified messaging API, SMS+RCS | Weaker RCS-specific features |
| **Bandwidth** | Carrier/CPaaS | Own US network, great pricing | US-focused, limited international |
| **nativeMsg** | RCS specialist | Best RCS-specific platform, A/B testing | Smaller scale, limited CPaaS |
| **OneSignal** | Push/RCS | Multi-channel (push+RCS), easy setup | RCS is secondary to push |
| **Klaviyo** | Marketing automation | Email+SMS+RCS, great analytics | Expensive at scale, RCS is add-on |
| **Attentive** | SMS marketing | Best SMS marketing platform, 8K+ brands | RCS is new addition |

### Our Differentiation

| Differentiator | How We Stand Out |
|---------------|-----------------|
| **SMSoIP + RCS dual path** | Native IMS SMSoIP for P2P SMS + RCS Business Messaging for A2P |
| **White-label for agencies** | Most competitors don't offer true white-label |
| **Transparent pricing** | No hidden carrier fees, real-time cost tracking |
| **Programmable messaging** | Full REST API + webhooks, not just campaign blasts |
| **Self-hosted option** | Enterprises can run on-premise with their own IMS core |
| **Conversational AI integration** | Native chatbot hooks (OpenAI, Dialogflow) |

---

## 34. Revenue Projections

### Year 1-3 Projections

| Metric | Year 1 | Year 2 | Year 3 |
|--------|--------|--------|--------|
| **Paying tenants** | 50 | 300 | 1,500 |
| **Avg msgs/tenant/mo** | 5,000 | 15,000 | 50,000 |
| **Total msgs/mo** | 250K | 4.5M | 75M |
| **Avg revenue/msg** | $0.025 | $0.022 | $0.018 |
| **Message revenue/mo** | $6,250 | $99,000 | $1,350,000 |
| **Subscription revenue/mo** | $7,500 | $90,000 | $450,000 |
| **Total MRR** | $13,750 | $189,000 | $1,800,000 |
| **Annual Revenue** | $165K | $2.27M | $21.6M |
| **COGS (carrier fees)** | $100K | $1.8M | $15M |
| **Gross Margin** | 39% | 21% | 30% |
| **Operating Expenses** | $500K | $1.5M | $5M |
| **Net Income** | -$435K | -$230K | $+5.6M |

**Break-even at ~Month 24-30** assuming efficient growth.

---

## 35. Roadmap

### Q3 2026 — MVP Launch
- Multi-tenant SaaS core (auth, contacts, campaigns)
- Google RBM agent management + verification
- Simple campaign sending (text + rich cards)
- SMS fallback via Twilio/SMPP
- Basic analytics dashboard
- REST API (send, status, contacts)

### Q4 2026 — Growth Features
- A/B testing framework
- Conversational inbox (two-way messaging)
- Webhook event notifications
- Contact segmentation + dynamic lists
- White-label for first agency partners

### Q1 2027 — Scale
- Auto-response rules engine
- Chatbot/AI integration (OpenAI, Dialogflow)
- Advanced analytics (cohort analysis, attribution)
- International carrier expansion (EU, APAC)
- Compliance suite (TCPA, GDPR, 10DLC)
- Self-hosted / on-premise option

### Q2 2027 — Differentiation
- SMSoIP native messaging (IMS-based P2P)
- WhatsApp Business integration (multi-channel)
- AI-powered content generation (auto-generate rich cards)
- Predictive analytics (send-time optimization)
- Carrier-direct connections (bypass CPaaS aggregators)

---

## Key References

### Part 1: SMSoIP

| Resource | URL |
|----------|-----|
| 3GPP TS 24.341 | https://www.etsi.org/deliver/etsi_ts/124300_124399/124341/ |
| 3GPP TS 24.011 | SMS on the radio interface (RP-DATA format) |
| 3GPP TS 23.040 | SMS technical realization (TPDU format) |
| ShareTechnote SMS over IMS | https://www.sharetechnote.com/html/IMS_SIP_SMSoverIMS.html |
| Nick vs Networking MO SMS | https://nickvsnetworking.com/the-surprisingly-complicated-world-of-mo-sms-in-ims volte/ |
| GSMA IR.92 | IMS Profile for Voice and SMS |
| Stack Overflow: SMS over IMS importance | https://stackoverflow.com/questions/72043231/is-sms-over-ims-that-important |
| Kamailio SMS over IP | https://kamailio.org/mailman3/hyperkitty/list/sr-users@lists.kamailio.org/ |
| Akaki.io: SMS over IMS | https://akaki.io/2023/decision_procedure_for_originating_numbers_in_sms_over_ims |
| imsdroid Binary SMS RPDATA | https://github.com/DoubangoTelecom/imsdroid/blob/master/Binary_SMS_RPDATA.md |
| Slicce Short Message IWF | https://www.slicce.co/products/interworking-functions/short-message-iwf |
| GSMA +g.3gpp.smsip feature tag | https://www.gsma.com/solutions-and-impact/technologies/networks/resolution_ce... |

### Part 2: RCS Advertising Platform

| Resource | URL |
|----------|-----|
| Google RBM Developer Docs | https://developers.google.com/business-communications/rcs-business-messaging/ |
| Google RBM Get Started | https://rcsforbusiness.google/get-started/ |
| Infobip RCS Statistics 2026 | https://www.infobip.com/blog/rcs-statistics |
| Juniper Research RCS Forecast | https://www.juniperresearch.com/press/business-rcs-traffic-to-surpass-200-bil... |
| Mordor Intelligence RCS Market | https://www.mordorintelligence.com/industry-reports/rich-communications-services-market |
| Business Research Insights RCS | https://www.businessresearchinsights.com/market-reports/rich-communication-services-market |
| Master of Code RCS ROI | https://masterofcode.com/blog/rcs-messaging-guide |
| Bandwidth A/B Testing RCS | https://www.bandwidth.com/blog/how-to-a-b-test-rcs-vs-sms-without-losing-your... |
| MarTech RCS Marketing | https://martech.org/mobile-marketing-with-rcs-what-you-need-to-know/ |
| BuSoftTech Multi-Tenant RCS | https://busofttech.com/blog/rcs-implementation-multi-tenant-saas-messaging-pl... |
| AWS RCS Billing | https://docs.aws.amazon.com/sms-voice/latest/userguide/rcs-billing.html |
| Prelude RCS Providers 2026 | https://prelude.so/blog/10-best-rcs-providers |

---

*Report generated 2026-05-16 from 20 targeted web searches, analysis of 22 existing research reports, 3GPP specification review, and architectural design work.*
