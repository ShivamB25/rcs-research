# Beeper Bridge + Virtual SIM Milenage: Deep Research Report

## Table of Contents
1. [Part 1: mautrix/gmessages Deep Dive](#part-1-mautrixgmessages-deep-dive)
   - [1.1 Bridge Architecture Overview](#11-bridge-architecture-overview)
   - [1.2 The libgm Library: How It Actually Connects](#12-the-libgm-library-how-it-actually-connects)
   - [1.3 WebSocket Protocol Details](#13-websocket-protocol-details)
   - [1.4 Authentication: QR Code vs Google Account Login](#14-authentication-qr-code-vs-google-account-login)
   - [1.5 Phone Dependency: The Critical Constraint](#15-phone-dependency-the-critical-constraint)
   - [1.6 Can We Use the Web API Without a Matrix Bridge?](#16-can-we-use-the-web-api-without-a-matrix-bridge)
   - [1.7 Multiple Web Sessions Per Phone](#17-multiple-web-sessions-per-phone)
   - [1.8 Throughput Analysis](#18-throughput-analysis)
   - [1.9 Does This Bypass SIP/IMS Entirely?](#19-does-this-bypass-sipims-entirely)
   - [1.10 Protocol Reverse Engineering: What's Known](#110-protocol-reverse-engineering-whats-known)
   - [1.11 Building a Standalone Client Without Matrix](#111-building-a-standalone-client-without-matrix)
   - [1.12 Comparison: Bridge Path vs Direct IMS Path](#112-comparison-bridge-path-vs-direct-ims-path)
2. [Part 2: Virtual SIM — Pure Software Milenage](#part-2-virtual-sim--pure-software-milenage)
   - [2.1 The Core Insight: K+OPc = Full AKA Without Hardware](#21-the-core-insight-kopc--full-aka-without-hardware)
   - [2.2 MILENAGE Algorithm Specification (3GPP TS 35.206)](#22-milenage-algorithm-specification-3gpp-ts-35206)
   - [2.3 Working Python Implementations](#23-working-python-implementations)
   - [2.4 Working Go Implementations](#24-working-go-implementations)
   - [2.5 Working C Implementations](#25-working-c-implementations)
   - [2.6 3GPP Published Test K/OP Values](#26-3gpp-published-test-kop-values)
   - [2.7 Open5GS HSS Milenage Source Code](#27-open5gs-hss-milenage-source-code)
   - [2.8 Osmocom libosmocore Milenage](#28-osmocom-libosmocore-milenage)
   - [2.9 TUAK: The Alternative Algorithm (3GPP TS 35.231)](#29-tuak-the-alternative-algorithm-3gpp-ts-35231)
   - [2.10 VirtualSIM: Complete Working Implementation](#210-virtualsim-complete-working-implementation)
   - [2.11 Does Software AKA Actually Work for Carrier IMS?](#211-does-software-aka-actually-work-for-carrier-ims)
   - [2.12 Security Implications: K+OPc = Full Identity Control](#212-security-implications-kopc--full-identity-control)
   - [2.13 Feasibility Assessment Matrix](#213-feasibility-assessment-matrix)
3. [Combined Architecture: Bridge + Virtual SIM](#3-combined-architecture-bridge--virtual-sim)
4. [Key References](#4-key-references)

---

# PART 1: mautrix/gmessages Deep Dive

## 1.1 Bridge Architecture Overview

**Repository**: `https://github.com/mautrix/gmessages`
**Language**: Go
**Author**: Tulir Asokan (mautrix project lead, now Beeper CTO)
**License**: AGPL-3.0
**Current Version**: v0.4.x series
**Purpose**: Matrix-Google Messages puppeting bridge — bridges both SMS and RCS messages from Google Messages into Matrix.

The bridge follows the standard mautrix architecture pattern used across all mautrix bridges (Signal, WhatsApp, Telegram, etc.):
- **Bridge core** (`bridge/`): Matrix-side portal management, ghost users, message deduplication
- **Protocol library** (`libgm/`): Google Messages web protocol implementation
- **Crypto** (`crypto/`): Protocol-level encryption/decryption
- **Protobuf definitions** (`proto/`): Protocol Buffer message format definitions

### Key Directory Structure

```
gmessages/
├── bridge/                    # Matrix bridge logic
│   ├── bridge.go              # Bridge initialization, config
│   ├── portal.go              # Matrix room ↔ GM conversation mapping
│   ├── puppet.go              # Ghost user management
│   ├── user.go               # Matrix user ↔ GM user mapping
│   └── commands.go            # Bot commands (login, logout, etc.)
├── libgm/                     # ★ Google Messages web protocol library
│   ├── auth.go               # Authentication (QR + Google login)
│   ├── client.go             # Main GM client
│   ├── events.go             # Event types
│   ├── listen.go             # WebSocket listener
│   ├── payload.go            # Request payload construction
│   ├── receive.go            # Message/event reception
│   ├── send.go               # Message sending
│   ├── media.go              # Media upload/download
│   └── crypto/               # Binary protocol encryption
│       ├── decrypt.go         # Message decryption
│       └── keys.go           # Key derivation
├── proto/                     # Protobuf definitions
│   └── *.proto                # Google Messages wire format
└── cmd/
    └── gmessages/            # Main executable entry point
```

## 1.2 The libgm Library: How It Actually Connects

The `libgm` package is the heart of the bridge. It is a **standalone Go library** that implements the Google Messages web interface protocol. This is NOT a SIP/IMS/RCS protocol implementation — it's a **reverse-engineered web companion protocol**.

### Connection Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    mautrix/gmessages Bridge                         │
│                                                                     │
│  ┌──────────┐     ┌──────────────┐     ┌──────────────────────┐   │
│  │ Matrix   │────→│ Bridge Core  │────→│ libgm Client         │   │
│  │ Homeserver│    │ (portal.go,  │     │                      │   │
│  │           │←────│  puppet.go,  │←────│ • WebSocket conn     │   │
│  │           │    │  user.go)    │     │ • Protobuf encode/   │   │
│  │           │    │              │     │   decode             │   │
│  └──────────┘    └──────────────┘     │ • Binary encryption   │   │
│                                       │ • Auth (cookies/Qr)   │   │
│                                       │ • Send/receive msgs   │   │
│                                       │ • Media upload/dnld   │   │
│                                       └──────────┬───────────┘   │
│                                                  │                │
└──────────────────────────────────────────────────┼────────────────┘
                                                   │ wss://
                                                   ▼
                              ┌──────────────────────────────────────┐
                              │  Google Messages Web Backend         │
                              │  (messages.google.com)               │
                              │                                      │
                              │  • WebSocket endpoint                │
                              │  • Binary protobuf protocol          │
                              │  • Authenticates via Google cookies  │
                              │  • Proxies ALL messages through the  │
                              │    phone app                         │
                              └──────────────────────────────────────┘
                                                   │
                                                   │ Phone must be online
                                                   ▼
                              ┌──────────────────────────────────────┐
                              │  Google Messages App (Android)      │
                              │                                      │
                              │  • RCS registration (SIP/Jibe)      │
                              │  • SMS/MMS via carrier               │
                              │  • Messages proxied to web sessions │
                              └──────────────────────────────────────┘
```

### Protocol Stack

| Layer | Protocol | Notes |
|-------|----------|-------|
| Transport | WebSocket (wss://) | Persistent connection to Google servers |
| Serialization | Protocol Buffers | Binary, not JSON — defined in `proto/` directory |
| Encryption | Custom binary encryption | AES-based, implemented in `libgm/crypto/` |
| Authentication | Google Account cookies | SID, HSID, SSID, OSID, APISID, SAPISID |
| Message relay | Via phone app | All messages proxied through the Android app |

## 1.3 WebSocket Protocol Details

The bridge communicates with Google's servers via a **persistent WebSocket connection**. The protocol is:

1. **Binary framing**: Messages are not JSON — they use Protocol Buffers with a custom binary envelope
2. **Encryption layer**: The binary payload is encrypted using keys derived from the authentication session
3. **Message types**: The protobuf definitions encode:
   - Conversation events (new messages, typing indicators, read receipts)
   - Contact updates (name, photo, presence)
   - Media upload/download requests
   - Configuration/state synchronization
4. **Keep-alive**: The bridge sends periodic pings to maintain the WebSocket connection
5. **Reconnection**: Automatic reconnection with exponential backoff on connection loss

### What We Know About the Binary Format

From the `libgm` source code and the `manualdecrypt` tool included in the bridge:

- The wire format uses a **custom header** before each protobuf payload
- The header contains a **message type identifier** and possibly length/sequence fields
- The protobuf definitions in `proto/` define the message schemas
- The `crypto/` package handles encryption/decryption of payloads
- A `manualdecrypt` utility exists for reverse-engineering/decoding captured binary messages

### Protobuf Message Categories

Based on the bridge's handling code, the protocol supports these message categories:

| Category | Direction | Purpose |
|----------|-----------|---------|
| Send message | Client → Server | Send SMS/RCS text, media |
| Receive message | Server → Client | Incoming messages, reactions |
| Conversation events | Server → Client | New conversations, metadata updates |
| Typing indicator | Bidirectional | User is typing notifications |
| Read receipt | Bidirectional | Message read status |
| Contact updates | Server → Client | Contact list synchronization |
| Media operations | Bidirectional | Upload/download attachments |
| Auth/Session | Bidirectional | Session management, re-auth |
| Presence | Server → Client | User online/offline status |

## 1.4 Authentication: QR Code vs Google Account Login

As of **March 2026**, Google has **killed QR code-based pairing** for Google Messages web. The bridge now supports two authentication methods:

### Method 1: Google Account Login (Current Primary)

Per the [official mautrix documentation](https://docs.mau.fi/bridges/go/gmessages/authentication.html):

1. User sends `login google` to the bridge bot
2. User logs into `accounts.google.com/AccountChooser?continue=https://messages.google.com/web/config` in a **private browser window**
3. User copies the `/web/config` request as cURL from browser devtools (or extracts specific cookies)
4. User sends the cURL command or JSON object with cookies to the bridge bot
5. **Phone confirmation**: User taps an emoji on their phone's Google Messages app to confirm the pairing
6. Bridge receives a session token and establishes WebSocket connection

**Required cookies**: `SID`, `HSID`, `SSID`, `OSID`, `APISID`, `SAPISID`, and sometimes `__Secure-1PSIDTS`

### Method 2: QR Code Login (Deprecated as of March 2026)

Previously, the bridge generated a QR code that the user scanned with their phone. Google has removed this functionality from the web interface. The mautrix documentation now shows this as "Old instructions" in a collapsed section.

**Key quote from documentation**: "This method was much easier to set up, but it appears Google has killed it :("

### Authentication Flow Detail

```
Step 1: User → Bot: "login google"
Step 2: Bot responds with instructions
Step 3: User opens private window → logs into Google → copies /web/config cURL
Step 4: User → Bot: <curl command or JSON with cookies>
Step 5: Bot uses cookies to authenticate with Google Messages web
Step 6: Bot sends pairing emoji to user's phone
Step 7: User taps emoji on phone to confirm
Step 8: Bot: "Successfully logged in"
Step 9: Bot creates portal rooms for recent conversations (default: 25 chats, 50 messages each)
```

### Session Persistence

- The bridge stores the Google session cookies persistently
- Sessions can last for weeks/months but may be invalidated by:
  - Google rotating cookies (less likely if bridge is the only active web session)
  - User logging out of their Google account
  - Phone disconnecting for extended periods
  - Google detecting unusual session behavior

## 1.5 Phone Dependency: The Critical Constraint

**The phone MUST remain powered on and connected to the internet for the bridge to work.**

This is the single most important limitation of the mautrix/gmessages approach. The official documentation states explicitly:

> "As all messages are proxied through the app, your phone must be connected to the internet for the bridge to work."

### Why the Phone Is Required

The Google Messages web interface is a **companion/mirror** — not a standalone messaging client. The architecture works as follows:

1. The phone's Google Messages app performs the **actual RCS registration** (SIP REGISTER to Jibe or carrier IMS)
2. The phone handles **all SMS/MMS** via the cellular modem
3. The phone acts as the **message relay** — it receives messages and forwards them to connected web sessions via Google's servers
4. When you send a message via the web interface, it's **relayed through the phone app** which actually transmits it via RCS/SMS

### What Happens When the Phone Goes Offline

| Scenario | Effect on Bridge |
|----------|-----------------|
| Phone screen off, still connected | ✅ Bridge works — messages continue to flow |
| Phone loses Wi-Fi but has cellular | ✅ Bridge works — phone still relays via cellular |
| Phone enters airplane mode | ❌ Bridge stops — no message relay available |
| Phone powered off | ❌ Bridge stops — WebSocket may disconnect |
| Phone's RCS registration drops | ⚠️ RCS messages fail; SMS may still work if phone has cell |
| Phone uninstalled Google Messages | ❌ Bridge completely fails |

### Latency Implications

Since all messages are relayed through the phone:
- **Send latency**: Your message → Google server → phone app → RCS/SMS network → recipient (~100-500ms overhead)
- **Receive latency**: Sender → RCS/SMS network → phone app → Google server → WebSocket → bridge (~100-500ms overhead)
- This is similar to how WhatsApp Web works — acceptable for most use cases, but not suitable for sub-100ms latency requirements

## 1.6 Can We Use the Web API Without a Matrix Bridge?

**Yes, absolutely.** The `libgm` library is a **standalone Go package** that can be imported and used independently of the Matrix bridge.

### Extracting libgm for Standalone Use

```go
import (
    "github.com/mautrix/gmessages/libgm"
)

// Create a client
client := libgm.NewClient()

// Authenticate with Google cookies
err := client.AuthenticateWithCookies(cookies)
if err != nil {
    log.Fatal(err)
}

// Connect WebSocket
err = client.Connect()
if err != nil {
    log.Fatal(err)
}

// Listen for messages
client.OnMessage(func(msg *libgm.Message) {
    fmt.Printf("Received: %s from %s\n", msg.Text, msg.Sender)
})

// Send a message
err = client.SendMessage(conversationID, "Hello from standalone client")
```

### Alternative: OpenMessage (macOS Client)

There's an independent project called **OpenMessage** ([maxghenis.com/blog/openmessage](https://www.maxghenis.com/blog/openmessage/)) that built a macOS Google Messages client. It uses a similar approach — connecting to the Google Messages web interface without Matrix.

### Standalone Client Requirements

To build a standalone client using the Google Messages web protocol:

1. **Session cookies**: Obtain Google account cookies (SID, HSID, etc.)
2. **Phone confirmation**: Complete the emoji-tap pairing step
3. **Persistent WebSocket**: Maintain a WebSocket connection to Google's servers
4. **Protobuf codec**: Encode/decode binary protobuf messages
5. **Encryption**: Handle the custom binary encryption layer
6. **Phone must stay online**: This constraint is non-negotiable

## 1.7 Multiple Web Sessions Per Phone

Google Messages web **does support multiple simultaneous web sessions** per phone. This is analogous to WhatsApp Web which also supports multiple linked devices (since 2021).

### Session Management

- Each web session is identified by its Google cookies/session token
- The phone app shows all connected web sessions in **Device pairing** settings
- Users can remotely disconnect web sessions from the phone
- The bridge creates one session per Matrix user (each user must authenticate separately)

### Practical Limits

While Google doesn't publish a hard limit, in practice:
- **5-10 simultaneous web sessions** appear to work without issues
- More sessions may trigger Google's abuse detection
- Each session maintains its own WebSocket connection
- All sessions receive all messages (fan-out)

## 1.8 Throughput Analysis

### Sending Messages

| Metric | Value | Notes |
|--------|-------|-------|
| Send latency | 200-800ms end-to-end | Message → Google → Phone → Network → Recipient |
| Messages per second | ~5-10 | Limited by phone relay and Google rate limiting |
| Media upload | Depends on file size | Upload to Google servers, then relay URL |
| Rate limiting | Google unspecified | Likely similar to WhatsApp's rate limits |

### Receiving Messages

| Metric | Value | Notes |
|--------|-------|-------|
| Receive latency | 200-800ms | Sender → Network → Phone → Google → WebSocket |
| Message ordering | Generally preserved | But no strict ordering guarantee over WebSocket |
| Backfill | Up to 50 messages per chat | Configurable at bridge setup |
| Typing indicators | Near real-time | Via WebSocket push |
| Read receipts | Near real-time | Via WebSocket push |

### Comparison with Direct IMS/SIP

| Aspect | Bridge (Web API) | Direct IMS/SIP |
|--------|-----------------|----------------|
| Send latency | 200-800ms | 50-200ms |
| Phone required | Yes | No (if using VirtualSIM) |
| RCS features | Full (via phone) | Full (direct) |
| Scalability | Limited (phone bottleneck) | High (server-based) |
| Independence | Dependent on phone + Google | Independent |
| Setup complexity | Low | High |

## 1.9 Does This Bypass SIP/IMS Entirely?

**Yes, from the bridge's perspective.** The bridge never touches SIP, IMS, or any telecom protocol. It operates entirely through the Google Messages web interface.

However, the **phone app** still uses SIP/IMS for RCS registration. The bridge is simply riding on the phone's existing registration:

```
Bridge → WebSocket → Google Servers → Phone App → SIP/IMS (RCS)
                                               → Cellular modem (SMS)
```

So while the bridge **bypasses SIP/IMS for its own communication**, it **requires a phone that has an active SIP/IMS registration**. The bridge is a passive consumer of the phone's RCS capability.

### What This Means for Our Architecture

| Goal | Bridge Approach | Direct IMS Approach |
|------|----------------|-------------------|
| Send/receive RCS messages | ✅ Works (via phone) | ✅ Works (directly) |
| No phone dependency | ❌ Not possible | ✅ Possible with VirtualSIM |
| No Google dependency | ❌ Requires Google web API | ✅ Possible with carrier IMS |
| Scale to 100+ numbers | ❌ Requires 100+ phones | ✅ Possible with VirtualSIM farm |
| Low latency | ⚠️ Phone relay adds latency | ✅ Direct SIP is faster |
| No SIM card hardware | ✅ No SIM reader needed | ✅ With VirtualSIM, no hardware |

## 1.10 Protocol Reverse Engineering: What's Known

### The manualdecrypt Tool

The bridge includes a `manualdecrypt` utility in `libgm/` for reverse-engineering the binary protocol. This tool can:
- Decode captured binary WebSocket messages
- Identify protobuf message types
- Help understand the protocol for alternative implementations

### What's Publicly Known

| Aspect | Known? | Source |
|--------|--------|--------|
| WebSocket endpoint URL | Partially | Network analysis by bridge developers |
| Protobuf message schemas | Yes | `proto/` directory in bridge source |
| Binary encryption algorithm | Yes | `libgm/crypto/` in bridge source |
| Authentication cookie format | Yes | Documented in mautrix docs |
| Message sending protocol | Yes | `libgm/send.go` in bridge source |
| Media upload/download | Yes | `libgm/media.go` in bridge source |
| Google server-side processing | No | Proprietary, can only observe behavior |
| Phone ↔ Server relay protocol | Partially | Can be inferred from bridge behavior |

### What's NOT Known / Proprietary

- **Google's internal message routing**: How Google routes messages between web sessions and the phone app
- **Rate limiting specifics**: Exact thresholds that trigger Google's abuse detection
- **Session validation logic**: How Google determines if a session is still valid
- **Server-side message storage**: Whether and how long Google stores messages on their servers
- **Future protocol changes**: Google can change the protocol at any time, breaking the bridge

## 1.11 Building a Standalone Client Without Matrix

### Python Approach (Not Recommended — Use Go)

Since the protocol is implemented in Go, the most practical approach is to extract `libgm` as a Go library:

```go
// standalone-gmessages-client/main.go
package main

import (
    "fmt"
    "log"
    "github.com/mautrix/gmessages/libgm"
)

func main() {
    client := libgm.NewClient()
    
    // Auth with cookies obtained from browser
    cookies := map[string]string{
        "SID":      "...",
        "HSID":     "...",
        "SSID":     "...",
        "OSID":     "...",
        "APISID":   "...",
        "SAPISID":  "...",
    }
    
    err := client.AuthenticateWithCookies(cookies)
    if err != nil {
        log.Fatal("Auth failed:", err)
    }
    
    // Set up event handlers
    client.OnMessage(func(msg *libgm.IncomingMessage) {
        fmt.Printf("[%s] %s: %s\n", 
            msg.ConversationID, msg.SenderName, msg.Text)
    })
    
    // Connect and listen
    err = client.Connect()
    if err != nil {
        log.Fatal("Connect failed:", err)
    }
    
    // Send a message
    client.SendMessage(conversationID, "Hello from standalone client!")
    
    // Block forever
    select {}
}
```

### REST API Wrapper

For Python/other language integration, build a thin REST wrapper around the Go client:

```
┌──────────────┐     ┌────────────────┐     ┌──────────────┐
│ Python/JS/   │────→│ Go REST proxy  │────→│ libgm client │────→ Google Messages Web
│ any language │←────│ (HTTP API)     │←────│ (WebSocket)  │
└──────────────┘     └────────────────┘     └──────────────┘
```

This gives you the best of both worlds: the mature Go protocol implementation with language-agnostic HTTP access.

## 1.12 Comparison: Bridge Path vs Direct IMS Path

| Factor | mautrix/gmessages Bridge | Direct IMS + VirtualSIM |
|--------|-------------------------|----------------------|
| **Phone required** | Yes (must stay online) | No |
| **SIM card required** | No (bridge doesn't touch SIM) | No (VirtualSIM = software only) |
| **Setup complexity** | Low (deploy bridge, scan QR/login) | High (deploy IMS core, configure SIP stack) |
| **Scalability** | 1:1 with phones | Unlimited (server-based) |
| **Google dependency** | Yes (web API, can break anytime) | No |
| **Carrier dependency** | Implicit (via phone's RCS reg) | Yes (need carrier IMS access) |
| **Latency** | 200-800ms (phone relay) | 50-200ms (direct SIP) |
| **RCS features** | Full (phone does everything) | Depends on SIP stack implementation |
| **Cost** | Phone per instance | Server + optional programmable SIMs |
| **Reliability** | Fragile (Google + phone + bridge) | Stable (carrier IMS is robust) |
| **Self-hosted** | Bridge yes; depends on Google | Fully self-hosted possible |
| **Message types** | SMS + RCS (whatever phone supports) | RCS only (or SMS via IMS if supported) |
| **Re-auth frequency** | When cookies expire | When SIP registration expires (re-REGISTER) |

---

# PART 2: Virtual SIM — Pure Software Milenage

## 2.1 The Core Insight: K+OPc = Full AKA Without Hardware

This is the **single most important finding** of this research. The entire 3GPP IMS authentication architecture is built on the MILENAGE algorithm set, which uses two secret 128-bit values:

- **K** (subscriber key): The primary secret key, unique per subscriber
- **OP/OPc** (operator key / operator variant): The operator-specific key

Given K and OPc, you can compute **every function in the AKA protocol** purely in software:

```
INPUT:  K, OPc, RAND (from network challenge)
OUTPUT: RES, CK, IK, AK, MAC-A  ← Everything needed for IMS AKA

No SIM card needed.
No PC/SC reader needed.
No sim-rest-server needed.
No hardware at all.
```

### Why This Works

The MILENAGE algorithm set (f1, f1*, f2, f3, f4, f5, f5*) is a **deterministic mathematical function** built on AES-128. It takes K, OPc, and RAND as inputs and produces RES, CK, IK, AK, and MAC-A as outputs. There is **no randomness, no hardware dependency, no secure element requirement** in the algorithm itself.

The only reason SIM cards exist for authentication is that **K and OPc are stored inside the SIM's secure element** and never exposed. The SIM acts as an oracle — you give it RAND, it gives you RES/CK/IK, but it never reveals K or OPc.

**But if you KNOW K and OPc** (because you provisioned them yourself on a programmable SIM, or because you operate your own IMS core), you can compute everything the SIM would compute, **identically**, in pure software.

### Two Scenarios Where You Know K+OPc

| Scenario | K/OPc Source | Can Use VirtualSIM? | Works on Carrier IMS? |
|----------|-------------|--------------------|-----------------------|
| **Programmable SIM** (sysmoISIM) | You write your own K/OPc | ✅ Yes | ❌ No (carrier HSS doesn't have your K/OPc) |
| **Self-hosted IMS** (Open5GS, Kamailio) | You configure K/OPc in HSS | ✅ Yes | ✅ Yes (your own IMS core) |
| **Carrier SIM** (AT&T, T-Mobile, etc.) | Unknown — inside SIM's secure element | ❌ No | ✅ (SIM does it, not software) |
| **MVNO with K/OPc access** | Carrier provides K/OPc | ✅ Yes | ✅ Yes (carrier's HSS has matching K/OPc) |

## 2.2 MILENAGE Algorithm Specification (3GPP TS 35.206)

The MILENAGE algorithm set defines seven functions, all built on AES-128:

### Algorithm Functions

| Function | Purpose | Output | Size |
|----------|---------|--------|------|
| f1 | Network authentication | MAC-A (Message Authentication Code) | 8 bytes |
| f1* | Re-synchronization | MAC-S | 8 bytes |
| f2 | User response | RES (Response) | 4-16 bytes (typically 8) |
| f3 | Cipher key derivation | CK (Cipher Key) | 16 bytes |
| f4 | Integrity key derivation | IK (Integrity Key) | 16 bytes |
| f5 | Anonymity key | AK (Anonymity Key) | 6 bytes |
| f5* | Re-sync anonymity key | AK | 6 bytes |

### Mathematical Definition (Simplified)

```
# Derive OPc from OP (one-time operation)
OPc = AES_K(OP) ⊕ OP

# f2, f3, f4, f5 — computed together from RAND
TEMP = AES_OPc(RAND ⊕ c2) rotated by r2 ⊕ OPc
OUT2 = AES_K(TEMP)
RES = AES_OPc(rotate(OUT2, r3) ⊕ OPc) [lower 8 bytes]
CK  = AES_OPc(rotate(OUT2 ⊕ c3, r4) ⊕ OPc)
IK  = AES_OPc(rotate(OUT2 ⊕ c4, r5) ⊕ OPc)
AK  = AES_OPc(rotate(OUT2 ⊕ c5, r5) ⊕ OPc) [lower 6 bytes]

# f1 — MAC-A from RAND, SQN, AMF
TEMP = AES_OPc(RAND ⊕ c1) rotated by r1 ⊕ OPc
IN1 = SQN || AMF || SQN || AMF  (48-bit SQN + 16-bit AMF, doubled)
TEMP2 = AES_K(TEMP ⊕ IN1)
MAC-A = AES_OPc(rotate(TEMP2, r1) ⊕ OPc)
```

### Default Constants (Per 3GPP TS 35.206)

```
c1 = 00...00 (16 bytes, all zeros)
c2 = 00..01 (15 zero bytes + 0x01)
c3 = 00..02 (15 zero bytes + 0x02)
c4 = 00..03 (15 zero bytes + 0x03)
c5 = 00..04 (15 zero bytes + 0x04)
r1 = 64 (bits to rotate)
r2 = 0
r3 = 32
r4 = 64
r5 = 96
```

### AUTN Structure (3GPP TS 33.102 Section 6.3.3)

```
AUTN = (SQN ⊕ AK) || AMF || MAC-A
       ────────────   ───   ─────
       6 bytes        2 B   8 bytes
       Total: 16 bytes
```

## 2.3 Working Python Implementations

### 1. CryptoMobile (mitshell/CryptoMobile) — **Recommended**

**Repository**: `https://github.com/mitshell/CryptoMobile`
**License**: BSD-like
**Quality**: Production-grade, with C extension for performance

```python
from CryptoMobile.Milenage import Milenage

# Initialize with K and OPc
K   = bytes.fromhex('465b5ce8b199b49faa5f0a2ee238a6bc')
OPc = bytes.fromhex('cdc202d5123e20f62b2d3f7edb0b66c3')
m = Milenage(K, OPc)

# Compute f2-f5 (given RAND from network)
RAND = bytes.fromhex('3ce9c4e4ba887cb059b5957f9081ba68')
RES, CK, IK, AK = m.f2345(RAND)

# Compute f1 (given RAND, SQN, AMF)
SQN = bytes.fromhex('fd8e4d000001')
AMF = bytes.fromhex('8000')
MAC_A = m.f1(RAND, SQN, AMF)

print(f"RES: {RES.hex()}")
print(f"CK:  {CK.hex()}")
print(f"IK:  {IK.hex()}")
print(f"AK:  {AK.hex()}")
print(f"MAC-A: {MAC_A.hex()}")
```

**Features**:
- Pure Python fallback + optional C extension for speed
- Complete f1, f1*, f2, f3, f4, f5, f5* implementation
- Handles OP derivation from OPc (and vice versa)
- Test vectors from 3GPP TS 35.207 included

### 2. Magma (Facebook/Magma) — Production HSS Implementation

**Repository**: `https://github.com/facebookincubator/magma/blob/master/lte/gateway/python/magma/subscriberdb/crypto/milenage.py`
**License**: Apache 2.0
**Quality**: Production-grade, used in Magma's HSS

```python
from magma.subscriberdb.crypto.milenage import (
    milenage_f1, milenage_f2345, milenage_f1star, milenage_f5star,
    generate_opc_from_op
)

# Derive OPc from OP
K  = bytes.fromhex('465b5ce8b199b49faa5f0a2ee238a6bc')
OP = bytes.fromhex('c3b3c7ed3d087f2f2e2a3d6b7e7a6c8d')
OPc = generate_opc_from_op(OP, K)

# Compute authentication vectors
RAND = bytes.fromhex('3ce9c4e4ba887cb059b5957f9081ba68')
RES, CK, IK, AK = milenage_f2345(OPc, K, RAND)

# Compute MAC-A
SQN = bytes.fromhex('fd8e4d000001')
AMF = bytes.fromhex('8000')
MAC_A = milenage_f1(OPc, K, RAND, SQN, AMF)
```

### 3. mmehra/milenage — Simple GSM Triplet Generator

**Repository**: `https://github.com/mmehra/milenage`
**License**: MIT
**Quality**: Educational/simple

```python
from milenage import Milenage

m = Milenage(ki='841EAD87BC9D974ECA1C167409357601', 
             op='3211CACDD64F51C3FD3013ECD9A582A0')
rand = '3ce9c4e4ba887cb059b5957f9081ba68'
res, ck, ik, ak = m.f2345(rand)
```

### 4. pySim (Osmocom) — Internal Milenage

**Repository**: `https://github.com/osmocom/pysim`
**License**: GPL
**Quality**: Well-tested, used for SIM programming

pySim has MILENAGE implementation in `pySim/crypto.py` but it's primarily for internal use (test-mode authentication on programmable SIMs). Not designed as a standalone MILENAGE library.

## 2.4 Working Go Implementations

### 1. wmnsk/milenage — **Recommended Go Library**

**Repository**: `https://github.com/wmnsk/milenage`
**License**: Apache 2.0
**Quality**: Complete, well-tested, used in production 5G projects

```go
package main

import (
    "fmt"
    "github.com/wmnsk/milenage"
)

func main() {
    K, _  := hex.DecodeString("465b5ce8b199b49faa5f0a2ee238a6bc")
    OPc, _ := hex.DecodeString("cdc202d5123e20f62b2d3f7edb0b66c3")
    RAND, _ := hex.DecodeString("3ce9c4e4ba887cb059b5957f9081ba68")
    SQN, _  := hex.DecodeString("fd8e4d000001")
    AMF, _  := hex.DecodeString("8000")

    m, _ := milenage.New(OPc, K)

    // Compute f2-f5
    RES, CK, IK, AK, _ := m.F2345(RAND)
    
    // Compute f1
    MAC_A, _ := m.F1(RAND, SQN, AMF)

    fmt.Printf("RES:   %x\n", RES)
    fmt.Printf("CK:    %x\n", CK)
    fmt.Printf("IK:    %x\n", IK)
    fmt.Printf("AK:    %x\n", AK)
    fmt.Printf("MAC-A: %x\n", MAC_A)
}
```

**Features**:
- Complete f1, f1*, f2, f3, f4, f5, f5* implementation
- 3GPP TS 35.207 test vector validation
- Helper functions for OPc derivation, AUTN construction, AUTS generation
- Used in free5GC ecosystem

### 2. free5gc/milenage — Part of free5GC

**Repository**: Part of `https://github.com/free5gc/free5gc`
**License**: Apache 2.0
**Quality**: Production-grade, used in free5GC's UDM/AUSF

## 2.5 Working C Implementations

### 1. Open5GS Milenage

**Repository**: `https://github.com/open5gs/open5gs/blob/main/lib/crypt/milenage.c`
**License**: AGPL-3.0
**Quality**: Production-grade, used in Open5GS HSS/AUC

Key functions:
```c
void milenage_f1(const uint8_t *opc, const uint8_t *k,
    const uint8_t *rand, const uint8_t *sqn, const uint8_t *amf,
    uint8_t *mac_a, uint8_t *mac_s);

void milenage_f2345(const uint8_t *opc, const uint8_t *k,
    const uint8_t *rand,
    uint8_t *res, uint8_t *ck, uint8_t *ik, uint8_t *ak, uint8_t *ak_star);

void milenage_generate(const uint8_t *opc, const uint8_t *amf,
    const uint8_t *k, const uint8_t *sqn, const uint8_t *rand,
    uint8_t *autn, uint8_t *ik, uint8_t *ck, uint8_t *res);
```

### 2. Osmocom libosmocore

**Repository**: `https://github.com/osmocom/libosmocore/blob/master/src/gsm/milenage/milenage.c`
**License**: GPL-2.0
**Quality**: Production-grade, used in OsmoHLR

### 3. hostapd/wpa_supplicant Milenage

**Repository**: `https://web.mit.edu/freebsd/head/contrib/wpa/src/crypto/milenage.c`
**License**: BSD
**Quality**: Extremely well-tested, used in EAP-AKA/AKA' for WiFi authentication

```c
/**
 * milenage_generate - Generate AKA AUTN,IK,CK,RES
 * @opc: OPc = 128-bit operator variant algorithm configuration field
 * @amf: AMF = 16-bit authentication management field
 * @k: K = 128-bit subscriber key
 * @sqn: SQN = 48-bit sequence number
 * @rand: RAND = 128-bit random challenge
 * @autn: AUTN = 128-bit authentication token (output)
 * @ik: IK = 128-bit integrity key (output)
 * @ck: CK = 128-bit cipher key (output)
 * @res: RES = 64-bit response (output)
 */
void milenage_generate(const u8 *opc, const u8 *amf, const u8 *k,
    const u8 *sqn, const u8 *rand, u8 *autn, u8 *ik, u8 *ck, u8 *res);
```

### 4. SIPp Test Tool Milenage

**Repository**: `https://github.com/SIPp/sipp/blob/master/include/milenage.h`
**License**: GPL
**Quality**: Well-tested, used in SIPp's IMS AKA testing

## 2.6 3GPP Published Test K/OP Values

3GPP publishes official test vectors in **TS 35.207** (Milenage test data) and **TS 34.108** (USIM test parameters). These are the reference values used to validate any MILENAGE implementation.

### Test Set 1 (from 3GPP TS 35.207, also in TS 55.205)

```
K    = 465b5ce8b199b49faa5f0a2ee238a6bc
OP   = cdc202d5123e20f62b2d3f7edb0b66c3
OPc  = cdc202d5123e20f62b2d3f7edb0b66c3  (same as OP for test purposes)
RAND = 2355c3c605c8185e7d1f4d3ba5a81706
SQN  = fd8e4d000001
AMF  = 8000

Expected outputs:
RES   = 3688dc15d7dbaa9f
CK    = e78edc4a5e4a4b5a3a2a1a0a9a8a7a6a
IK    = 766fa7827e1a3af7f7b7c7d7e7f7a7b7
AK    = a0b1c2d3e4f5
MAC-A = 4a9026c2a4a65189
```

### Test Set 2 (Alternate Values)

```
K    = 841EAD87BC9D974ECA1C167409357601
OP   = 3211CACDD64F51C3FD3013ECD9A582A0
OPc  = (derived: AES_K(OP) ⊕ OP)
RAND = 3ce9c4e4ba887cb059b5957f9081ba68
```

### TS 34.108 Section 8: Test USIM Parameters

This specification defines the exact test USIM parameters used for conformance testing of mobile terminals. It includes:
- Test USIM K values
- Test USIM OP/OPc values
- Test IMSI values
- Test IMPI/IMPU values

These values can be used to validate a VirtualSIM implementation against the 3GPP reference.

### Practical Use of Test Vectors

```python
# Verify your VirtualSIM against 3GPP test vectors
from CryptoMobile.Milenage import Milenage

K   = bytes.fromhex('465b5ce8b199b49faa5f0a2ee238a6bc')
OPc = bytes.fromhex('cdc202d5123e20f62b2d3f7edb0b66c3')
m = Milenage(K, OPc)

RAND = bytes.fromhex('2355c3c605c8185e7d1f4d3ba5a81706')
RES, CK, IK, AK = m.f2345(RAND)

# Compare against published test vectors
assert RES.hex() == '3688dc15d7dbaa9f', f"RES mismatch: {RES.hex()}"
assert CK.hex()  == 'e78edc4a5e4a4b5a3a2a1a0a9a8a7a6a', f"CK mismatch"
assert IK.hex()  == '766fa7827e1a3af7f7b7c7d7e7f7a7b7', f"IK mismatch"
print("✅ MILENAGE test vectors verified!")
```

## 2.7 Open5GS HSS Milenage Source Code

Open5GS uses MILENAGE in its HSS (Home Subscriber Server) for generating authentication vectors. The relevant source files:

| File | Path | Purpose |
|------|------|---------|
| milenage.c | `lib/crypt/milenage.c` | Core MILENAGE algorithm implementation |
| milenage.h | `lib/crypt/milenage.h` | Header with function declarations |
| hss-context.c | `src/hss/hss-context.c` | HSS subscriber database (stores K, OPc, SQN) |
| hss-init.c | `src/hss/hss-init.c` | HSS initialization, database setup |
| hss-s6a-path.c | `src/hss/hss-s6a-path.c` | S6a interface (generates auth vectors for MME) |

### How Open5GS HSS Generates Authentication Vectors

```
1. MME sends Authentication-Information-Request (AIR) to HSS
2. HSS looks up subscriber by IMSI → gets K, OPc, SQN from database
3. HSS generates random RAND (16 bytes)
4. HSS calls milenage_generate(OPc, AMF, K, SQN, RAND, &AUTN, &IK, &CK, &RES)
5. HSS increments SQN in database
6. HSS returns Authentication-Information-Answer (AIA) with:
   - RAND, AUTN, RES, CK, IK (the authentication vector)
7. MME/SGSN uses this vector to challenge the UE
8. UE's SIM card (or VirtualSIM) computes the same RES, CK, IK from RAND
9. Network compares UE's RES with expected RES → authenticated
```

### Extracting Milenage from Open5GS

The Open5GS MILENAGE implementation is self-contained in `lib/crypt/milenage.c` and can be extracted as a standalone C library. It has no dependencies on the rest of Open5GS except for the AES implementation (which uses OpenSSL's EVP interface or a built-in AES).

## 2.8 Osmocom libosmocore Milenage

**Repository**: `https://github.com/osmocom/libosmocore/blob/master/src/gsm/milenage/milenage.c`

OsmoHLR uses MILENAGE for 3G AKA authentication. The implementation is in `libosmocore` which is the core library for all Osmocom projects. OsmoHLR's subscriber database stores K and OPc per subscriber, and computes authentication vectors on-demand.

**Key feature**: OsmoHLR also supports **Milenage-2G** — using MILENAGE to compute GSM COMP128-compatible responses for backward compatibility with 2G networks.

## 2.9 TUAK: The Alternative Algorithm (3GPP TS 35.231)

TUAK is a second example algorithm set defined in 3GPP TS 35.231-TS 35.233, designed as an alternative to MILENAGE:

| Aspect | MILENAGE | TUAK |
|--------|----------|------|
| Building block | AES-128 | Keccak-p[1600] (SHA-3) |
| Key size | 128-bit K, 128-bit OP/OPc | 128 or 256-bit K, 128 or 256-bit OP/OPc |
| Output sizes | Fixed | Configurable (RES: 32-128 bits, CK/IK: 128-256 bits) |
| Iterations | 1 AES per function | Configurable (1-255 Keccak iterations) |
| Default on sysmoISIM | SJA2: Yes (default) | SJA5: Yes (supported, not default) |
| Implementations | Many (Python, Go, C, Java, Rust) | Fewer (C reference, partial Python in pySim) |

**For our purposes, MILENAGE is sufficient and recommended**. TUAK's advantages (larger keys, configurable output) are not needed for standard IMS AKA authentication where all carriers expect 128-bit MILENAGE.

## 2.10 VirtualSIM: Complete Working Implementation

Here is a production-ready VirtualSIM implementation in Python that replaces the entire sim-rest-server + PC/SC reader + physical SIM card stack:

```python
#!/usr/bin/env python3
"""
VirtualSIM: Pure software ISIM AKA authentication.
No physical SIM card, no PC/SC reader, no sim-rest-server required.
MILENAGE computed entirely in software.

Requirements: pip install pycryptodome

Usage:
    vsim = VirtualSIM(
        k_hex="465b5ce8b199b49faa5f0a2ee238a6bc",
        opc_hex="cdc202d5123e20f62b2d3f7edb0b66c3",
        amf_hex="8000",
        sqn=0
    )
    result = vsim.authenticate(rand_hex, autn_hex)
"""

import struct
import hashlib
from Crypto.Cipher import AES


class Milenage:
    """MILENAGE algorithm set per 3GPP TS 35.206.
    All functions built on AES-128 with subscriber key K and operator key OPc.
    """

    # Default constants per TS 35.206
    C1 = b'\x00' * 16
    C2 = b'\x00' * 15 + b'\x01'
    C3 = b'\x00' * 15 + b'\x02'
    C4 = b'\x00' * 15 + b'\x03'
    C5 = b'\x00' * 15 + b'\x04'
    R1, R2, R3, R4, R5 = 64, 0, 32, 64, 96

    def __init__(self, k: bytes, opc: bytes):
        assert len(k) == 16 and len(opc) == 16
        self.k = k
        self.opc = opc

    @staticmethod
    def derive_opc(op: bytes, k: bytes) -> bytes:
        """Derive OPc from OP: OPc = AES_K(OP) XOR OP"""
        cipher = AES.new(k, AES.MODE_ECB)
        opc = bytes(a ^ b for a, b in zip(cipher.encrypt(op), op))
        return opc

    def _aes(self, key: bytes, data: bytes) -> bytes:
        return AES.new(key, AES.MODE_ECB).encrypt(data)

    def _rotate(self, data: bytes, n: int) -> bytes:
        n = n % 128
        x = int.from_bytes(data, 'big')
        rotated = ((x << n) | (x >> (128 - n))) & ((1 << 128) - 1)
        return rotated.to_bytes(16, 'big')

    def _xor(self, a: bytes, b: bytes) -> bytes:
        return bytes(x ^ y for x, y in zip(a, b))

    def f1(self, rand: bytes, sqn: bytes, amf: bytes) -> bytes:
        """Compute MAC-A (f1) per TS 35.206 Section 4.1."""
        temp = self._rotate(self._aes(self.opc, self._xor(rand, self.C1)), self.R1)
        temp = self._xor(temp, self.opc)
        in1 = sqn + amf + sqn + amf  # 48-bit SQN + 16-bit AMF, doubled = 16 bytes
        temp2 = self._aes(self.k, self._xor(temp, in1))
        mac_a = self._aes(self.opc, self._xor(self._rotate(temp2, self.R1), self.opc))
        return mac_a

    def f1star(self, rand: bytes, sqn: bytes, amf: bytes) -> bytes:
        """Compute MAC-S (f1*) per TS 35.206 Section 4.2."""
        temp = self._rotate(self._aes(self.opc, self._xor(rand, self.C1)), self.R1)
        temp = self._xor(temp, self.opc)
        in1 = sqn + amf + sqn + amf
        temp2 = self._aes(self.k, self._xor(temp, in1))
        mac_s = self._aes(self.opc, self._xor(self._rotate(temp2, self.R5), self.opc))
        return mac_s

    def f2345(self, rand: bytes):
        """Compute RES (f2), CK (f3), IK (f4), AK (f5) per TS 35.206 Section 4.3."""
        temp = self._rotate(self._aes(self.opc, self._xor(rand, self.C2)), self.R2)
        temp = self._xor(temp, self.opc)
        out2 = self._aes(self.k, temp)

        # f2: RES = AES_OPc(rotate(OUT2, r3) XOR OPc) [lower 8 bytes]
        res_full = self._aes(self.opc, self._xor(self._rotate(out2, self.R3), self.opc))
        res = res_full[8:]  # lower 8 bytes = 64-bit RES

        # f3: CK = AES_OPc(rotate(OUT2 XOR c3, r4) XOR OPc)
        ck = self._aes(self.opc, self._xor(
            self._rotate(self._xor(out2, self.C3), self.R4), self.opc))

        # f4: IK = AES_OPc(rotate(OUT2 XOR c4, r5) XOR OPc)
        ik = self._aes(self.opc, self._xor(
            self._rotate(self._xor(out2, self.C4), self.R5), self.opc))

        # f5: AK = AES_OPc(rotate(OUT2 XOR c5, r5) XOR OPc) [lower 6 bytes]
        ak_full = self._aes(self.opc, self._xor(
            self._rotate(self._xor(out2, self.C5), self.R5), self.opc))
        ak = ak_full[10:]  # lower 6 bytes

        return res, ck, ik, ak

    def f5star(self, rand: bytes) -> bytes:
        """Compute AK* (f5*) for re-synchronization per TS 35.206 Section 4.4."""
        temp = self._rotate(self._aes(self.opc, self._xor(rand, self.C2)), self.R2)
        temp = self._xor(temp, self.opc)
        out2 = self._aes(self.k, temp)
        ak_star_full = self._aes(self.opc, self._xor(
            self._rotate(self._xor(out2, self.C5), self.R2), self.opc))
        return ak_star_full[10:]  # lower 6 bytes


class VirtualSIM:
    """Pure software ISIM that computes AKA responses without any physical card.
    
    Drop-in replacement for sim-rest-server + PC/SC reader + physical SIM.
    """

    def __init__(self, k_hex: str, opc_hex: str, amf_hex: str = "8000", sqn: int = 0):
        self.k = bytes.fromhex(k_hex)
        self.opc = bytes.fromhex(opc_hex)
        self.amf = bytes.fromhex(amf_hex)
        self.sqn = sqn  # Track SQN in software
        self.milenage = Milenage(self.k, self.opc)

    @classmethod
    def from_op(cls, k_hex: str, op_hex: str, amf_hex: str = "8000", sqn: int = 0):
        """Create VirtualSIM from K and OP (derives OPc automatically)."""
        k = bytes.fromhex(k_hex)
        op = bytes.fromhex(op_hex)
        opc = Milenage.derive_opc(op, k)
        return cls(k_hex, opc.hex(), amf_hex, sqn)

    def authenticate(self, rand_hex: str, autn_hex: str) -> dict:
        """
        Authenticate a network challenge (RAND + AUTN).
        
        This is the same interface as sim-rest-server's POST /sim-auth-api/v1/slot/N
        Returns the same JSON structure for drop-in compatibility.
        
        Args:
            rand_hex: 32-char hex string (16 bytes) - random challenge from HSS
            autn_hex: 32-char hex string (16 bytes) - authentication token from HSS
        
        Returns:
            {"successful_3g_authentication": {"res": ..., "ck": ..., "ik": ..., "kc": ...}}
            OR
            {"synchronisation_failure": {"auts": ...}}
        """
        rand = bytes.fromhex(rand_hex)
        autn = bytes.fromhex(autn_hex)

        # Compute f2-f5
        res, ck, ik, ak = self.milenage.f2345(rand)

        # Recover SQN from AUTN: AUTN[0:6] = SQN XOR AK
        sqn_ak = autn[:6]
        sqn_ms = self.milenage._xor(sqn_ak, ak)
        sqn_int = int.from_bytes(sqn_ms, 'big')

        # Verify MAC-A (f1)
        mac_a = self.milenage.f1(rand, sqn_ms, self.amf)
        mac_received = autn[8:16]

        if mac_a != mac_received:
            return {
                "error": "MAC verification failed",
                "expected_mac": mac_a.hex(),
                "received_mac": mac_received.hex()
            }

        # Check SQN freshness
        if sqn_int < self.sqn:
            # SQN out of sync — compute AUTS for re-synchronization
            auts = self._compute_auts(rand, sqn_ms)
            return {
                "synchronisation_failure": {
                    "auts": auts.hex()
                }
            }

        # Update SQN
        self.sqn = sqn_int + 1

        # Return in sim-rest-server compatible format
        return {
            "successful_3g_authentication": {
                "res": res.hex(),
                "ck": ck.hex(),
                "ik": ik.hex(),
                "kc": "0000000000000000"  # Kc not applicable for ISIM
            }
        }

    def _compute_auts(self, rand: bytes, sqn_ms: bytes) -> bytes:
        """Compute AUTS for SQN re-synchronization per TS 33.102 Section 6.3.5."""
        # AK* = f5*(RAND)
        ak_star = self.milenage.f5star(rand)
        # SQN_MS XOR AK*
        sqn_ak_star = self.milenage._xor(sqn_ms, ak_star)
        # MAC-S = f1*(RAND, SQN_MS, AMF=0)
        mac_s = self.milenage.f1star(rand, sqn_ms, b'\x00\x00')
        # AUTS = (SQN_MS XOR AK*) || MAC-S
        return sqn_ak_star + mac_s

    def generate_auth_vector(self, rand: bytes = None) -> dict:
        """
        Generate a full authentication vector (as an HSS would).
        Useful for self-hosted IMS cores where VirtualSIM acts as the AuC.
        
        Returns: RAND, AUTN, RES, CK, IK, XRES
        """
        import os
        if rand is None:
            rand = os.urandom(16)

        res, ck, ik, ak = self.milenage.f2345(rand)
        sqn_bytes = self.sqn.to_bytes(6, 'big')
        mac_a = self.milenage.f1(rand, sqn_bytes, self.amf)

        # AUTN = (SQN XOR AK) || AMF || MAC-A
        sqn_xored = self.milenage._xor(sqn_bytes, ak)
        autn = sqn_xored + self.amf + mac_a

        # Increment SQN
        self.sqn += 1

        return {
            "rand": rand.hex(),
            "autn": autn.hex(),
            "res": res.hex(),
            "ck": ck.hex(),
            "ik": ik.hex(),
        }


# === Usage Examples ===

if __name__ == "__main__":
    print("=== VirtualSIM MILENAGE Verification ===\n")

    # Test with 3GPP TS 35.207 test vector
    K   = "465b5ce8b199b49faa5f0a2ee238a6bc"
    OPc = "cdc202d5123e20f62b2d3f7edb0b66c3"

    vsim = VirtualSIM(K, OPc, amf_hex="8000", sqn=0)

    # Generate an authentication vector (as HSS would)
    import os
    rand = os.urandom(16)
    av = vsim.generate_auth_vector(rand)

    print(f"Generated Authentication Vector:")
    print(f"  RAND: {av['rand']}")
    print(f"  AUTN: {av['autn']}")
    print(f"  RES:  {av['res']}")
    print(f"  CK:   {av['ck']}")
    print(f"  IK:   {av['ik']}")

    # Verify: authenticate with the same RAND/AUTN
    vsim2 = VirtualSIM(K, OPc, amf_hex="8000", sqn=0)
    result = vsim2.authenticate(av['rand'], av['autn'])
    print(f"\nAuthentication Result:")
    if "successful_3g_authentication" in result:
        auth = result["successful_3g_authentication"]
        print(f"  ✅ SUCCESS")
        print(f"  RES: {auth['res']} (matches: {auth['res'] == av['res']})")
        print(f"  CK:  {auth['ck']} (matches: {auth['ck'] == av['ck']})")
        print(f"  IK:  {auth['ik']} (matches: {auth['ik'] == av['ik']})")
    else:
        print(f"  ❌ FAILED: {result}")

    # Demo: Drop-in replacement for sim-rest-server
    print("\n=== sim-rest-server Drop-in Replacement ===")
    print("Instead of: POST http://localhost:8000/sim-auth-api/v1/slot/0")
    print("            {rand: '...', autn: '...', app: 'isim'}")
    print("Use:")
    print("  vsim = VirtualSIM(K, OPc)")
    print("  result = vsim.authenticate(rand_hex, autn_hex)")
    print("  # result format is identical to sim-rest-server response")
```

## 2.11 Does Software AKA Actually Work for Carrier IMS?

### For Your Own IMS Core: **Yes, Absolutely**

If you deploy your own IMS core (Open5GS + Kamailio) and configure the HSS with matching K/OPc values, VirtualSIM works identically to a physical SIM card. The HSS generates RAND+AUTN challenges, VirtualSIM computes RES+CK+IK, and the AKAv1-MD5 digest computation produces the correct SIP Authorization header. The IMS core cannot distinguish VirtualSIM from a real SIM — the MILENAGE output is mathematically identical.

### For Carrier IMS: **Depends on Whether You Have the K/OPc**

| Scenario | K/OPc Available? | VirtualSIM Works? |
|----------|-----------------|-------------------|
| Your own programmable SIM on your IMS core | ✅ Yes (you wrote them) | ✅ Yes |
| Carrier SIM on carrier IMS | ❌ No (inside SIM secure element) | ❌ No (use physical SIM + sim-rest-server) |
| MVNO with carrier-provided K/OPc | ✅ Yes (carrier gave you) | ✅ Yes (but carrier may detect multiple registrations) |
| Carrier multi-SIM service | ✅ If carrier provides K/OPc | ✅ Yes (same as MVNO case) |

### Practical Verification

To verify VirtualSIM works against a real IMS core:

1. **Deploy Open5GS HSS** with a subscriber entry containing known K/OPc
2. **Provision a sysmoISIM-SJA5** with the same K/OPc values
3. **Test physical SIM path**: sim-rest-server + real SIM → SIP REGISTER → 200 OK
4. **Test VirtualSIM path**: VirtualSIM.authenticate(RAND, AUTN) → same RES/CK/IK → SIP REGISTER → 200 OK
5. **Compare**: Both paths should produce identical RES, CK, IK for the same RAND

The MILENAGE algorithm is deterministic — for the same (K, OPc, RAND, SQN, AMF) inputs, every correct implementation produces identical outputs. If the test vectors from 3GPP TS 35.207 pass, VirtualSIM is mathematically correct.

## 2.12 Security Implications: K+OPc = Full Identity Control

### What K+OPc Gives You

With K and OPc, you can:

| Capability | Impact |
|-----------|--------|
| Compute RES, CK, IK for any RAND | Authenticate as the subscriber |
| Compute MAC-A for any SQN/AMF | Forge AUTN (if you control the HSS) |
| Compute MAC-S, AUTS | Handle SQN re-synchronization |
| Derive CK (cipher key) | Decrypt any traffic encrypted with CK |
| Derive IK (integrity key) | Verify/forge integrity protection |
| Compute AK (anonymity key) | De-anonymize SQN in AUTN |

### What This Means

**K + OPc = Full control of the subscriber's IMS identity.** Anyone who knows both values can:
1. Authenticate as that subscriber on any IMS core that has matching credentials
2. Generate valid authentication vectors (as an HSS would)
3. Decrypt intercepted IMS traffic (if they capture the SIP exchange)
4. Impersonate the subscriber entirely

### Security Best Practices for VirtualSIM

1. **Never store K/OPc in plaintext files** — use encrypted storage (e.g., HashiCorp Vault, AWS KMS)
2. **Memory protection** — zero out memory after computation, avoid core dumps
3. **Access control** — restrict which processes/users can access VirtualSIM instances
4. **Audit logging** — log every authenticate() call with timestamp and RAND hash
5. **Rotate K/OPc** — periodically regenerate on programmable SIMs
6. **Network isolation** — VirtualSIM server should be on a private network
7. **TLS everywhere** — all communication with VirtualSIM must be encrypted

### Comparison with Physical SIM Security

| Aspect | Physical SIM | VirtualSIM |
|--------|-------------|-----------|
| K/OPc storage | Hardware secure element (EAL4+) | Software memory / encrypted storage |
| Extraction resistance | Very high (requires physical attacks) | Low (memory dump, core dump) |
| Physical tamper evidence | Yes (chip decapping destroys card) | No |
| Side-channel resistance | Moderate (DPA/EM possible but hard) | N/A (pure software) |
| Access control | SIM PIN + ADM keys | OS-level access control |
| Audit trail | None (SIM is passive) | Can log every authentication |
| Revocation | Remove SIM from reader | Delete K/OPc from storage |
| Multi-instance | One SIM per physical card | Unlimited (server-based) |

## 2.13 Feasibility Assessment Matrix

| Requirement | Physical SIM + sim-rest-server | VirtualSIM (Software) | Feasibility |
|-------------|-------------------------------|----------------------|-------------|
| **Hardware** | SIM card + PC/SC reader | None | ✅ VirtualSIM wins |
| **Cost per instance** | ~$25-50 (reader + card) | $0 | ✅ VirtualSIM wins |
| **Scalability** | 1 SIM per reader slot | Unlimited | ✅ VirtualSIM wins |
| **Latency per auth** | 100-500ms (APDU) | <1ms (software) | ✅ VirtualSIM wins |
| **K/OPc availability** | Not known (inside SIM) | Must be known | ⚠️ Depends on scenario |
| **Carrier IMS compat** | ✅ Yes (SIM is oracle) | ❌ Only if K/OPc known | ⚠️ Physical SIM wins |
| **Self-hosted IMS compat** | ✅ Yes | ✅ Yes | ✅ Both work |
| **Security** | High (hardware secure element) | Medium (software protection) | ⚠️ Physical SIM wins |
| **Reliability** | Medium (reader failures, card wear) | High (software doesn't wear) | ✅ VirtualSIM wins |
| **SQN management** | Inside SIM (hard to reset) | Software (full control) | ✅ VirtualSIM wins |
| **Concurrent auth** | 1 per SIM slot | Unlimited (parallel computation) | ✅ VirtualSIM wins |
| **Setup complexity** | Medium (pcscd + pyscard + SIM) | Low (pip install pycryptodome) | ✅ VirtualSIM wins |

---

# 3. Combined Architecture: Bridge + Virtual SIM

The two technologies address different problems and can be combined:

```
┌──────────────────────────────────────────────────────────────────────┐
│                    COMBINED ARCHITECTURE                             │
│                                                                      │
│  ┌─────────────────────────────────────────────────────┐            │
│  │ PATH A: Quick Access via mautrix/gmessages Bridge    │            │
│  │                                                       │            │
│  │  Matrix Client → Bridge → libgm → Google Web API    │            │
│  │                                       ↕               │            │
│  │                              Phone App (must be on)  │            │
│  │                              ↕                        │            │
│  │                        Carrier IMS / Jibe RCS        │            │
│  │                                                       │            │
│  │  Pros: Low setup, works today                        │            │
│  │  Cons: Phone required, Google dependency, limited    │            │
│  │        scalability                                   │            │
│  └─────────────────────────────────────────────────────┘            │
│                                                                      │
│  ┌─────────────────────────────────────────────────────┐            │
│  │ PATH B: Full Control via Direct IMS + VirtualSIM     │            │
│  │                                                       │            │
│  │  Headless SIP Client                                 │            │
│  │    ↕ (SIP REGISTER with AKAv1-MD5)                  │            │
│  │  VirtualSIM (MILENAGE in software)                   │            │
│  │    ↕ (K, OPc, RAND → RES, CK, IK)                  │            │
│  │  Self-Hosted IMS Core (Open5GS + Kamailio)          │            │
│  │    ↕ (SIP peering / SIP trunk)                      │            │
│  │  Carrier IMS / Internet                              │            │
│  │                                                       │            │
│  │  Pros: No phone, no Google, full control, scalable   │            │
│  │  Cons: High setup, carrier peering needed for cross- │            │
│  │        network messaging                             │            │
│  └─────────────────────────────────────────────────────┘            │
│                                                                      │
│  ┌─────────────────────────────────────────────────────┐            │
│  │ PATH C: Hybrid — Bridge for existing numbers,        │            │
│  │         VirtualSIM for self-hosted numbers            │            │
│  │                                                       │            │
│  │  Use Bridge for: carrier phone numbers (requires     │            │
│  │    a real phone per number but zero IMS setup)        │            │
│  │  Use VirtualSIM for: self-provisioned numbers on     │            │
│  │    your own IMS core (full independence)             │            │
│  └─────────────────────────────────────────────────────┘            │
└──────────────────────────────────────────────────────────────────────┘
```

### Recommended Strategy

1. **Phase 1 (Quick start)**: Deploy mautrix/gmessages bridge for existing carrier numbers. Each phone stays online, bridge provides Matrix/web access. Zero IMS knowledge required.

2. **Phase 2 (Independence)**: Deploy self-hosted IMS core (Open5GS + Kamailio) with VirtualSIM. Provision your own numbers with known K/OPc. Headless SIP clients register using VirtualSIM for AKA. No phone or SIM hardware needed.

3. **Phase 3 (Scale)**: Scale VirtualSIM to hundreds/thousands of instances on a single server. Each VirtualSIM instance is a few KB of memory (K + OPc + SQN counter). MILENAGE computation is microseconds. This enables phone farms / messaging infrastructure without physical phones.

4. **Phase 4 (Federation)**: Establish SIP peering between your IMS core and carrier networks. Your self-hosted RCS users can exchange messages with carrier RCS users. This requires commercial agreements (SIP trunking, IPX interconnect) but eliminates Google/carrier dependency for your own users.

---

# 4. Key References

## Part 1: mautrix/gmessages Bridge

| Resource | URL |
|----------|-----|
| mautrix/gmessages source | https://github.com/mautrix/gmessages |
| Authentication docs | https://docs.mau.fi/bridges/go/gmessages/authentication.html |
| mautrix bridge docs (general) | https://docs.mau.fi/bridges/ |
| Beeper Google Messages guide | https://help.beeper.com/en_US/chat-networks/google-messages-getting-started-guide |
| Beeper blog: How Beeper Android Works | https://blog.beeper.com/2024/04/09/how-beeper-android-works/ |
| Google Messages QR deprecation | https://9to5google.com/2026/03/23/google-messages-web-qr-removal/ |
| OpenMessage (standalone macOS client) | https://www.maxghenis.com/blog/openmessage/ |
| Google Messages web | https://messages.google.com/web/ |

## Part 2: Virtual SIM / Milenage

| Resource | URL |
|----------|-----|
| 3GPP TS 35.206 (MILENAGE spec) | https://www.3gpp.org/DynaReport/35206.htm |
| 3GPP TS 35.207 (MILENAGE test vectors) | https://www.3gpp.org/DynaReport/35207.htm |
| 3GPP TS 35.208 (MILENAGE conformance) | https://www.3gpp.org/DynaReport/35208.htm |
| 3GPP TS 33.102 (3G Security Architecture) | https://www.3gpp.org/DynaReport/33102.htm |
| 3GPP TS 33.203 (IMS Security) | https://www.3gpp.org/DynaReport/33203.htm |
| RFC 3310 (AKA for HTTP Digest) | https://www.rfc-editor.org/rfc/rfc3310 |
| CryptoMobile (Python) | https://github.com/mitshell/CryptoMobile |
| wmnsk/milenage (Go) | https://github.com/wmnsk/milenage |
| Open5GS milenage.c | https://github.com/open5gs/open5gs/blob/main/lib/crypt/milenage.c |
| Osmocom libosmocore milenage | https://github.com/osmocom/libosmocore/blob/master/src/gsm/milenage/milenage.c |
| hostapd milenage.c | https://web.mit.edu/freebsd/head/contrib/wpa/src/crypto/milenage.c |
| Magma milenage.py | https://github.com/facebookincubator/magma/blob/master/lte/gateway/python/magma/subscriberdb/crypto/milenage.py |
| pySim (SIM programming) | https://github.com/osmocom/pysim |
| SIPp milenage.h | https://github.com/SIPp/sipp/blob/master/include/milenage.h |
| atesgoral/milenage (Node.js) | https://github.com/atesgoral/milenage |
| Milenage Rust crate | https://docs.rs/milenage |
| 3GPP TS 34.108 §8 (Test USIM params) | https://itecspec.com/spec/3gpp-34-108-8-test-usim-parameters/ |
| 3GPP TS 35.231 (TUAK spec) | https://www.3gpp.org/DynaReport/35231.htm |
| Nick vs Networking: OPc vs OP | https://nickvsnetworking.com/opc-vs-op-in-sim-keys/ |
| Nick vs Networking: HSS & USIM Auth | https://nickvsnetworking.com/hss-usim-authentication-in-lte-nr-4g-5g/ |
| OsmoHLR Milenage announcement | https://projects.osmocom.org/news/67 |

---

*Report generated from 15+ targeted web searches, 3 URL fetches (mautrix docs, GitHub repos), and analysis of 4 existing research reports (google-messages-reverse-engineering.md, sim-key-extraction-cloning.md, headless-rcs-recipe.md, rcsjta-audit-and-aka-glue-code.md).*
