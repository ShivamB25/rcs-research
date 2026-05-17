# RCS Messaging Protocol Mechanics: SIP MESSAGE (Pager-Mode) vs MSRP INVITE (Session-Mode)

## Research Report — 2026-05-15

---

## 1. Overview: Two Messaging Modes in RCS

RCS messaging uses two fundamentally different transport mechanisms defined by OMA CPM (Converged IP Messaging) and GSMA:

| Aspect | Pager-Mode (SIP MESSAGE) | Session-Mode (MSRP) |
|--------|--------------------------|---------------------|
| **SIP Method** | `MESSAGE` (RFC 3428) | `INVITE` → SDP negotiation → MSRP session |
| **Session** | No session; each MESSAGE is standalone | Full SIP dialog with MSRP media stream |
| **Max Size** | ~1200 bytes (message body) | Unlimited (MSRP supports chunking via Byte-Range) |
| **Delivery/Read Receipts** | Via separate SIP MESSAGE with IMDN XML | Via MSRP SEND with IMDN XML |
| **"Is Composing"** | Not supported | Supported (application/im-iscomposing+xml via MSRP SEND) |
| **Use Case** | Short standalone text messages (like SMS replacement) | Chat sessions, group chat, file transfer, large messages |
| **3GPP ICSI** | `urn:urn-7:3gpp-service.ims.icsi.oma.cpm.msg` | `urn:urn-7:3gpp-service.ims.icsi.oma.cpm.session` |
| **Content-Type** | `message/cpim` wrapping the payload | `message/cpim` wrapping the payload |
| **Routing** | Through SIP proxies hop-by-hop | Direct MSRP TCP connection after INVITE/200 OK/ACK |

---

## 2. Exact Protocol Flow for 1-1 RCS Chat

### 2A. Pager-Mode (Standalone Messaging) — SIP MESSAGE

**Flow:**
```
UA1 → SIP Proxy → UA2:    MESSAGE (carries text in CPIM body)
UA2 → SIP Proxy → UA1:    200 OK (acknowledges receipt)
UA2 → SIP Proxy → UA1:    MESSAGE (delivery notification - IMDN XML)
UA1 → SIP Proxy → UA2:    200 OK
UA2 → SIP Proxy → UA1:    MESSAGE (display/read notification - IMDN XML)
UA1 → SIP Proxy → UA2:    200 OK
```

**Complete SIP MESSAGE Format (Standalone Message):**
```
MESSAGE sip:+14448880011@example.com;user=phone SIP/2.0
P-Preferred-Service: urn:urn-7:3gpp-service.ims.icsi.oma.cpm.msg
Contribution-ID: 477b66ae9662e3ad18549bf5dabf9d26d5e707ca
Conversation-ID: 1710887c7ca47dc2c1274c11673eb0df5a604fd3
P-Preferred-Identity: <sip:310410123456789@example.com>
Request-Disposition: no-fork
CSeq: 1 MESSAGE
Max-Forwards: 70
Route: <sip:[2001:0:0:1::2]:5060;lr>
Accept-Contact: *;+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.msg"
Content-Type: message/cpim
From: <sip:310410123456789@example.com>;tag=1384874566
Call-ID: 3712948749@2001::1:88fe:fccf:2870:5dee
Contact: <sip:310410123456789@[2001::1:88fe:fccf:2870:5dee]:5060>;
    +sip.instance="<urn:gsma:imei:35469106-056673-0>"
To: <sip:+14448880011@example.com;user=phone>
Via: SIP/2.0/TCP [2001::1:88fe:fccf:2870:5dee]:5060;branch=z9hG4bK2629405539smg
Content-Length: 322

From: <sip:310410123456789@example.com>
To: <sip:+14448880011@example.com;user=phone>
DateTime: 2015-02-17T06:54:27Z
NS: imdn <urn:ietf:params:imdn>
imdn.Message-ID: PH7qAIV8cgH5
imdn.Disposition-Notification: positive-delivery, display

Content-type: text/plain;charset=UTF-8
Content-Length: 15

123456789abcdef
```

**Key Headers Explained:**
- `P-Preferred-Service: urn:urn-7:3gpp-service.ims.icsi.oma.cpm.msg` — identifies this as a CPM standalone message (pager-mode)
- `Contribution-ID` — unique ID for this specific message contribution (correlates to a single message)
- `Conversation-ID` — groups all messages in a conversation thread
- `Content-Type: message/cpim` — the SIP body is in CPIM format (RFC 3862)
- CPIM body contains `imdn.Disposition-Notification: positive-delivery, display` — requests delivery and read receipts
- Inner content is `text/plain;charset=UTF-8` with the actual message

**Delivery Notification (IMDN) sent back:**
```
MESSAGE sip:310410123456789@[UA1_IP]:5060 SIP/2.0
Content-Type: message/cpim
Contribution-ID: f415972d55
Conversation-ID: 1710887c7ca47dc2c1274c11673eb0df5a604fd3
...

From: <sip:anonymous@anonymous.invalid>
To: <sip:310410123456789@example.com>
DateTime: 2015-02-17T06:54:27.8730740Z
NS: imdn <urn:ietf:params:imdn>
imdn.Message-ID: 92c65678d0

Content-Disposition: notification
Content-Type: message/imdn+xml

<imdn xmlns="urn:ietf:params:xml:ns:imdn">
  <message-id>PH7qAIV8cgH5</message-id>
  <delivery-notification>
    <status>
      <delivered />
    </status>
  </delivery-notification>
</imdn>
```

### 2B. Session-Mode (Chat) — SIP INVITE + MSRP

**Flow:**
```
Step 1: UA1 → UA2    INVITE (SDP offer with m=message line for MSRP)
Step 2: UA2 → UA1    100 Trying
Step 3: UA2 → UA1    183 Session Progress
Step 4: UA2 → UA1    200 OK (SDP answer with MSRP path)
Step 5: UA1 → UA2    ACK
--- MSRP TCP connection established (active party connects) ---
Step 6: UA1 → UA2    MSRP SEND (e.g., "is-composing" notification)
Step 7: UA2 → UA1    MSRP 200 OK
Step 8: UA1 → UA2    MSRP SEND (actual chat message in CPIM)
Step 9: UA2 → UA1    MSRP 200 OK
Step 10: UA2 → UA1   MSRP SEND (delivery notification IMDN XML)
Step 11: UA1 → UA2   MSRP 200 OK
--- Session can stay open for more messages ---
Step N: Either side sends SIP BYE to terminate session
```

**Complete SIP INVITE for MSRP Session:**
```
INVITE sip:+14448880000@example.com;user=phone SIP/2.0
Conversation-ID: 6b79b8bc937e4985b1dffd062b687bd7
Contribution-ID: d5e4121aeec2cc59546ebaef8966ef185a2f37f0
P-Preferred-Service: urn:urn-7:3gpp-service.ims.icsi.oma.cpm.session
P-Preferred-Identity: <sip:310410123456789@example.com>
P-Early-Media: supported
Allow: INVITE,ACK,OPTIONS,CANCEL,BYE,UPDATE,INFO,REFER,NOTIFY,MESSAGE,PRACK
CSeq: 1 INVITE
Max-Forwards: 70
Route: <sip:[2001:0:0:1::2]:5060;lr>
Accept-Contact: *;+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.session"
Content-Type: application/sdp
From: <sip:310410123456789@example.com>;tag=284849603
Call-ID: 508868544@2001::1:4c16:9c0f:4986:9e6d
Contact: <sip:310410123456789@[2001::1:4c16:9c0f:4986:9e6d]:5060;transport=UDP>;
    +g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.session"
To: <sip:+14448880000@example.com;user=phone>
Via: SIP/2.0/TCP [2001::1:4c16:9c0f:4986:9e6d]:5060;branch=z9hG4bK2563646430smg
Content-Length: 363

v=0
o=TEST-IMS-UE 1234562 0 IN IP6 2001::1:4c16:9c0f:4986:9e6d
s=SS VOIP
c=IN IP6 2001::1:4c16:9c0f:4986:9e6d
t=0 0
m=message 8880 TCP/MSRP *
a=accept-types:message/cpim application/im-iscomposing+xml
a=accept-wrapped-types:text/plain message/imdn+xml
a=setup:active
a=path:msrp://[2001::1:4c16:9c0f:4986:9e6d]:8880/FmnP;tcp
a=msrp-cema
a=sendrecv
```

**Key SDP Fields:**
- `m=message 8880 TCP/MSRP *` — media type "message", port 8880, transport TCP/MSRP
- `a=accept-types:message/cpim application/im-iscomposing+xml` — supported content types
- `a=accept-wrapped-types:text/plain message/imdn+xml` — supported inner content types
- `a=setup:active` — this UA will initiate the TCP connection to the MSRP peer
- `a=path:msrp://[ip]:port/session-id;tcp` — MSRP URI identifying where to send MSRP messages
- `a=msrp-cema` — MSRP Connection-Established Media Authorization (RFC 6714)
- `a=sendrecv` — bidirectional messaging

**200 OK Answer SDP:**
```
v=0
o=- 1192 5963 IN IP6 2001:0:0:1::2
s=-
c=IN IP6 2001:0:0:1::2
m=message 16000 TCP/MSRP *
a=accept-types:message/cpim application/im-iscomposing+xml
a=accept-wrapped-types:*
a=path:msrp://[2001:0:0:1::2]:16000/558f02b9d0;tcp
a=msrp-cema
a=setup:passive
```

**MSRP SEND (Chat Message):**
```
MSRP RgGcYXJW2nHr SEND
To-Path: msrp://[2001:0:0:1::2]:16000/558f02b9d0;tcp
From-Path: msrp://[2001::1:4c16:9c0f:4986:9e6d]:8880/FmnP;tcp
Message-ID: ZNsPlykpMApIABRrejarbO37ADMMae
Success-Report: no
Failure-Report: yes
Byte-Range: 1-430/430
Content-Type: message/cpim

From: <sip:anonymous@anonymous.invalid>
To: <sip:anonymous@anonymous.invalid>
DateTime: 2015-02-24T06:48:09Z
NS: imdn <urn:ietf:params:imdn>
NS: MyFeatures <mailto:RCSFeatures@test.com>
MyFeatures.PANI: 3GPP-E-UTRAN-FDD;utran-cell-id-3gpp=31041000010000000
imdn.Message-ID: wYcJuXBbGOfCtBqIPQqz0I
imdn.Disposition-Notification: positive-delivery, display

Content-type: text/plain;charset=UTF-8
Content-Length: 5

Hello
-------RgGcYXJW2nHr$
```

**MSRP 200 OK:**
```
MSRP RgGcYXJW2nHr 200 OK
To-Path: msrp://[2001::1:4c16:9c0f:4986:9e6d]:8880/FmnP;tcp
From-Path: msrp://[2001:0:0:1::2]:16000/558f02b9d0;tcp
-------RgGcYXJW2nHr$
```

**MSRP Delivery Notification:**
```
MSRP 69172e29 SEND
To-Path: msrp://[UA1_path]
From-Path: msrp://[UA2_path]
Message-ID: fd2f8f3e7c
Byte-Range: 1-500/500
Content-Type: message/cpim

From: <sip:anonymous@anonymous.invalid>
To: <sip:anonymous@anonymous.invalid>
DateTime: 2015-02-24T06:48:10.7749079Z
NS: imdn <urn:ietf:params:imdn>
imdn.Message-ID: 2252a2757d

Content-Type: message/imdn+xml
Content-Disposition: notification

<?xml version="1.0" encoding="utf-8"?>
<imdn xmlns="urn:ietf:params:xml:ns:imdn">
  <message-id>wYcJuXBbGOfCtBqIPQqz0I</message-id>
  <delivery-notification>
    <status>
      <delivered />
    </status>
  </delivery-notification>
</imdn>
-------69172e29$
```

---

## 3. Which Universal Profile Version Uses Which Mode

| UP Version | Year | Standalone (Pager-Mode) | Chat (Session-Mode) | Notes |
|-----------|------|------------------------|--------------------|----|
| Pre-UP (RCS 1.0–5.3) | 2008–2016 | ✅ SIP MESSAGE | ✅ MSRP INVITE | Both modes always supported |
| UP 1.0 (RCC.71 v1.0) | 2016 | ✅ | ✅ | Baseline |
| UP 2.0 (RCC.71 v2.0) | 2019 | ✅ | ✅ | Both required |
| UP 2.4 | 2019 | ✅ | ✅ | |
| UP 2.5 | 2021 | ✅ | ✅ | |
| UP 2.6 | 2022 | ✅ | ✅ | |
| UP 2.7 | 2024 | ✅ | ✅ | |
| UP 3.0 | 2025 | ✅ | ✅ | New features |
| UP 3.1 | 2025 | ✅ | ✅ | Better voice messages |
| UP 4.0 | 2026 | ✅ | ✅ | Video, rich text enhancements |

**Key Point:** All Universal Profile versions support BOTH modes. The client chooses which mode to use based on:
- **Short standalone messages** → Pager-mode SIP MESSAGE (simpler, no session overhead)
- **Conversational chat / multi-message exchange** → Session-mode MSRP INVITE (enables "is-composing", large messages, persistent session)

**Important:** In GSMA terminology:
- **"Standalone Messaging"** = Pager-mode SIP MESSAGE (OMA CPM standalone message, `oma.cpm.msg` ICSI)
- **"1-1 Chat"** = Session-mode MSRP INVITE (OMA CPM session, `oma.cpm.session` ICSI)

The distinction between "Standalone Messaging" and "Chat" in GSMA specs is:
- **Standalone Messaging** is for single, self-contained messages (like SMS). No session, no "is-composing", limited size. Defined by `P-Preferred-Service: urn:urn-7:3gpp-service.ims.icsi.oma.cpm.msg`
- **Chat** is for ongoing conversational exchanges. Session established via INVITE, supports "is-composing" indications, IMDN over MSRP, large payloads. Defined by `P-Preferred-Service: urn:urn-7:3gpp-service.ims.icsi.oma.cpm.session`

---

## 4. CPIM Format (RFC 3862)

Both pager-mode and session-mode use CPIM (Common Profile for Instant Messaging) as the message wrapper format. The structure is:

```
[CPIM Headers]
From: <sip:sender@example.com>
To: <sip:recipient@example.com>
DateTime: 2015-02-17T06:54:27Z
NS: imdn <urn:ietf:params:imdn>
imdn.Message-ID: <unique-id>
imdn.Disposition-Notification: positive-delivery, display

[Inner MIME part]
Content-type: text/plain;charset=UTF-8
Content-Length: N

[actual message text]
```

The CPIM layer provides:
- Standardized From/To addressing
- Timestamps
- IMDN namespace for delivery/display notifications
- Extensibility via custom namespaces (e.g., RCS features)

---

## 5. Capability Discovery (SIP OPTIONS with Feature Tags)

RCS uses **SIP OPTIONS** for capability discovery. When a client wants to know if a remote user supports RCS features, it sends:

```
OPTIONS sip:+14448880011@example.com;user=phone SIP/2.0
From: <sip:310410123456789@example.com>;tag=xxx
To: <sip:+14448880011@example.com;user=phone>
Call-ID: xxx
CSeq: 1 OPTIONS
Accept-Contact: *;+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.msg"
Accept-Contact: *;+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.session"
...
```

The 200 OK response from the remote UE's Contact header includes feature tags indicating capabilities:

**Key RCS Feature Tags:**
| Feature Tag | Meaning |
|------------|---------|
| `+g.3gpp.icsi-ref="urn:urn-7:3gpp-service.ims.icsi.oma.cpm.msg"` | Supports standalone messaging (pager-mode) |
| `+g.3gpp.icsi-ref="urn:urn-7:3gpp-service.ims.icsi.oma.cpm.session"` | Supports chat sessions (MSRP) |
| `+g.3gpp.icsi-ref="urn:urn-7:3gpp-service.ims.icsi.oma.cpm.session.group"` | Supports group chat |
| `+g.3gpp.icsi-ref="urn:urn-7:3gpp-service.ims.icsi.oma.cpm.filetransfer"` | Supports file transfer via MSRP |
| `+g.3gpp.icsi-ref="urn:urn-7:3gpp-service.ims.icsi.oma.cpm.filetransfer.http"` | Supports HTTP file transfer |
| `+g.oma.sip-im` | OMA SIP IM support (legacy, removed in UP 2.0+) |
| `+sip.instance` | GRUU — identifies specific device |
| `urn:urn-7:3gpp-application.ims.iari.rcse.ft` | RCS-e file transfer |
| `urn:urn-7:3gpp-application.ims.iari.rcs.fthttp` | RCS-e HTTP file transfer |
| `urn:urn-7:3gpp-application.ims.iari.rcs.geolocation.push` | Geolocation push |

**OpenSIPS Implementation:** OpenSIPS 3.3+ has a dedicated RCS capabilities module that manages SIP OPTIONS-based capability discovery, caching results, and providing API for feature tag lookup. See: https://www.opensips.org/Documentation/Tutorials-RCS-Managing-Capabilities

---

## 6. How to Implement a Minimal RCS Message Sender

### Minimum Required for Standalone Messaging (Pager-Mode):

1. **SIP Stack** — Need a SIP UA that can send MESSAGE requests
2. **SIP REGISTER** — Register with IMS core (optional if server doesn't require it)
3. **SIP MESSAGE** — Send with:
   - `Content-Type: message/cpim`
   - CPIM body with From/To/DateTime/IMDN headers
   - Inner `text/plain;charset=UTF-8` content
   - `P-Preferred-Service: urn:urn-7:3gpp-service.ims.icsi.oma.cpm.msg`
   - `Contribution-ID` and `Conversation-ID` headers
   - `Request-Disposition: no-fork`

**That's it — SIP MESSAGE alone IS sufficient for basic RCS messaging.**

### For Full Chat (Session-Mode), additionally need:

4. **SIP INVITE** with SDP containing `m=message` line for MSRP
5. **MSRP client** — TCP connection, SEND method, 200 OK responses
6. **Is-composing** — MSRP SEND with `application/im-iscomposing+xml` content
7. **IMDN over MSRP** — Delivery/display notifications via MSRP SEND
8. **SIP BYE** — Session termination

### Python Implementation Approach:

```python
# Using python-sipsimple (AG Projects) — most complete RCS-capable stack
# Includes: SIP UA, MSRP stack, CPIM formatting, IMDN handling
# pip install python-sipsimple

# Or minimal approach with just pjsua:
# 1. Use pjsua2 for SIP REGISTER + MESSAGE sending
# 2. For session mode, need additional MSRP library

# Minimal pager-mode sender using pjsua:
import pjsua2

# Register with IMS
# Send MESSAGE with CPIM body
# Handle 200 OK
# Handle incoming MESSAGE (IMDN notifications)
```

---

## 7. Available MSRP Libraries

### Python:
| Library | URL | Notes |
|---------|-----|-------|
| **python-msrplib** (AG Projects) | https://github.com/AGProjects/python-msrplib | Python 2, most mature, part of SIP SIMPLE SDK |
| **python3-msrplib** (AG Projects) | https://github.com/AGProjects/python3-msrplib | Python 3 port |
| **python-sipsimple** | https://github.com/AGProjects/python-sipsimple | Complete SIP SIMPLE SDK including MSRP, CPIM, IMDN |

### Java:
| Library | URL | Notes |
|---------|-----|-------|
| **msrp-java** (MSRP-OSS) | https://github.com/MSRP-OSS/msrp-java | Open source, RFC 4975 compliant, actively maintained |

### C#:
| Library | URL | Notes |
|---------|-----|-------|
| **msrp-csharp** (MSRP-OSS) | https://github.com/MSRP-OSS/msrp-csharp | Open source, RFC 4975 compliant |

### C:
| Library | URL | Notes |
|---------|-----|-------|
| **libMSRP (Confiance)** | https://sourceforge.net/projects/libmsrp/ | C library, used in CONFIANCE IMS client |
| **MSRP for IMS** | https://sourceforge.net/projects/msrp/ | C implementation targeting IMS robustness |

### Go:
- **No native Go MSRP library found.** Would need to implement from scratch based on RFC 4975 or use CGo bindings to libMSRP.

### Server/Relay:
| Software | URL | Notes |
|----------|-----|-------|
| **msrprelay** (AG Projects) | https://github.com/AGProjects/msrprelay | MSRP Relay per RFC 4976, Python |
| **OpenSIPS msrp_relay** | https://github.com/OpenSIPS/opensips/blob/master/modules/msrp_relay/ | MSRP relay module in OpenSIPS 3.3+ |
| **OpenSIPS MSRP Gateway** | Blog: https://blog.opensips.org/2022/06/09/msrp-gateway/ | Translates between SIP MESSAGE (pager-mode) and MSRP (session-mode) |

### Key OpenSIPS 3.3 Capabilities (relevant for RCS):
- **MSRP Relay** module — relays MSRP messages between peers
- **MSRP Gateway** — bridges SIP MESSAGE (pager-mode) clients with MSRP (session-mode) servers, allowing MESSAGE-only clients to participate in MSRP chat sessions
- **RCS Capabilities Management** — handles SIP OPTIONS capability discovery and caching

---

## 8. Is SIP MESSAGE Alone Sufficient for Basic RCS Messaging?

**YES — with important caveats:**

- SIP MESSAGE (pager-mode) is sufficient for **standalone text messaging** — the core "RCS message" that replaces SMS
- It supports delivery and read receipts via IMDN
- It works through SIP proxies without requiring direct TCP connections
- **Limitations of pager-mode only:**
  - No "is-composing" (typing indicator)
  - Message size limited to ~1200 bytes
  - No multi-device/session support
  - No group chat
  - No file transfer
  - Higher per-message overhead (each message goes through full SIP proxy chain)

**For a minimal viable RCS client**, implementing just pager-mode SIP MESSAGE is the fastest path. For feature parity with consumer RCS apps (like Google Messages), session-mode MSRP is also needed.

---

## 9. Group Chat (MSRP Conference Focus)

Group chat in RCS uses a **conference focus** architecture:

1. **Conference Factory URI** — Provisioned in client config. Used to CREATE a new conference.
2. **Conference Focus** — A server-side SIP UA that acts as the MSRP switch. All participants connect to it.
3. **Flow:**
   ```
   Creator → Conference Factory: SIP INVITE (creates room, gets conference URI)
   Creator → Conference Focus: SIP INVITE + MSRP (joins the room)
   Participant → Conference Focus: SIP INVITE + MSRP (joins the room)
   Focus → All: MSRP SEND (relays messages from any participant to all others)
   ```
4. Each participant has a separate SIP dialog with the Focus
5. The Focus relays MSRP SEND messages from any participant to all other participants
6. `Contribution-ID` and `Conversation-ID` are used to correlate messages within the group
7. The Focus handles participant join/leave notifications via SIP NOTIFY (conference event package)

**Relevant RFCs:** RFC 7701 (Multi-party Chat Using MSRP), RFC 7106 (Group Text Chat Purpose for Conference)

---

## 10. File Transfer Mechanism

RCS supports two file transfer mechanisms:

### 10A. MSRP File Transfer (Pre-UP, RCS-e)
- File data sent via MSRP SEND within an existing or new MSRP session
- SIP INVITE with SDP establishing a dedicated MSRP session for file transfer
- `a=accept-types:application/octet-stream` in SDP
- Large files chunked using MSRP `Byte-Range` header
- **Disadvantage:** Keeps MSRP connection open for duration of transfer, doesn't work well for very large files

### 10B. HTTP File Transfer (Universal Profile 1.0+)
- File is uploaded to an HTTP server via **HTTP PUT**
- The HTTP URL is shared with the recipient via MSRP SEND or SIP MESSAGE
- **Flow:**
  ```
  Sender → HTTP Server:     HTTP PUT (upload file, get download URL)
  Sender → Recipient:       SIP MESSAGE or MSRP SEND (contains file metadata + HTTP download URL)
  Recipient → HTTP Server:  HTTP GET (download file from URL)
  ```
- The message body contains `application/vnd.oma.cpm.filetransfer+xml` MIME type with:
  - File name, size, content-type
  - HTTP download URL
  - File thumbnail (optional)
- **Advantage:** Works for large files, survives network disruptions, doesn't tie up MSRP session
- **Universal Profile mandates HTTP file transfer** for files above a certain threshold

### ICSI for File Transfer:
- MSRP-based: `urn:urn-7:3gpp-service.ims.icsi.oma.cpm.filetransfer`
- HTTP-based: `urn:urn-7:3gpp-service.ims.icsi.oma.cpm.filetransfer.http`

---

## 11. Summary: Protocol Decision Tree

```
Send an RCS message?
├── Short text only, single shot?
│   └── YES → SIP MESSAGE (pager-mode)
│       ├── Content-Type: message/cpim
│       ├── P-Preferred-Service: oma.cpm.msg
│       └── Max ~1200 bytes
│
├── Conversational chat / multiple messages?
│   └── SIP INVITE + MSRP session (session-mode)
│       ├── P-Preferred-Service: oma.cpm.session
│       ├── "Is-composing" via MSRP SEND
│       └── Session stays open until BYE
│
├── Group chat?
│   └── SIP INVITE to Conference Focus + MSRP
│
└── File transfer?
    ├── Small file → MSRP SEND (legacy)
    └── Large file → HTTP PUT to server, share URL via MESSAGE/MSRP
```

---

## 12. Key References

- **RFC 3428** — SIP Extension for Instant Messaging (SIP MESSAGE method)
- **RFC 3862** — CPIM: Common Profile for Instant Messaging (message format)
- **RFC 4975** — MSRP: Message Session Relay Protocol
- **RFC 4976** — MSRP Relay Extensions
- **RFC 5438** — IMDN: Instant Message Disposition Notification
- **RFC 6714** — MSRP Connection-Established Media Authorization (MSRP CEMA)
- **RFC 7701** — Multi-party Chat Using MSRP
- **RFC 7106** — Group Text Chat Purpose for Conference
- **GSMA RCC.71** — RCS Universal Profile Service Definition (current: v4.0)
- **GSMA IR.90** — RCS Interworking Guidelines
- **OMA CPM** — Converged IP Messaging specifications
- **3GPP TS 24.247** — Messaging using IP Multimedia System
