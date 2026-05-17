# Multi-SIM Open Source Tools & Beeper Headless RCS — Audit Report

**Date:** 2026-05-15  
**Scope:** Audit existing open-source multi-SIM SMS/messaging tools, assess RCS extension feasibility, and analyze Beeper's headless RCS approach.

---

## Executive Summary

No existing open-source multi-SIM tool supports RCS. All major tools (smsgate, Kannel, smstools3, gammu, PlaySMS) are SMS/MMS-only and operate through AT commands over serial/USB — a protocol layer that fundamentally cannot carry RCS traffic. Extending any of these from SMS → RCS would require a complete architectural replacement of the transport layer, not a simple extension. Beeper's approach to RCS is unique: it uses an Android phone running Google Messages as a bridge, connecting via Matrix protocol through a self-hosted bridge. This can be partially replicated using Beeper's open-source mautrix bridges, but requires a physical Android phone for each RCS connection. The most practical path to a multi-SIM RCS gateway is combining an Android phone farm (for RCS modem functionality) with existing SMS gateway tooling (for SMS fallback) under a unified orchestration layer.

---

## 1. SMSgate Architecture: Multi-Modem SMS Gateway

### Overview

**SMSgate** is a Python-based open-source SMS gateway by Pentagrid AG (Swiss security company), designed for pentesting projects. It manages multiple GSM modems and SIM cards attached via USB or serial interfaces.

- **Repository:** https://github.com/pentagridsec/smsgate  
- **License:** BSD with non-military clause  
- **Language:** Python  
- **Underlying library:** `python-gsmmodem-new` (fork of `python-gsmmodem`)  
- **Blog post:** https://www.pentagrid.ch/en/blog/open-source-sms-gateway-for-pentest-projects/

### Core Architecture

```
┌───────────────────────────────────────────────┐
│                SMSgate Server                   │
│  (Python, Twisted-based)                       │
│                                                │
│  ┌─────────────┐  ┌──────────────┐             │
│  │ XML-RPC API │  │ SMTP Forward │             │
│  │ (TLS, port  │  │ (incoming   │             │
│  │  7000)      │  │  SMS→email)  │             │
│  └──────┬──────┘  └──────────────┘             │
│         │                                      │
│  ┌──────▼──────────────────────────────┐       │
│  │        Modem Pool Manager           │       │
│  │  - Per-modem SIM config             │       │
│  │  - SMS Router (prefix-based)       │       │
│  │  - Health checks per modem          │       │
│  │  - Account balance tracking         │       │
│  │  - Self-test SMS (periodic)         │       │
│  └──────┬──────────────────────────────┘       │
│         │                                      │
│  ┌──────▼──────┐  ┌──────────┐  ┌──────────┐  │
│  │  Modem [00] │  │Modem[01]│  │Modem[N]  │  │
│  │  /dev/ttyUSB│  │/dev/tty │  │/dev/tty  │  │
│  └─────────────┘  └─────────┘  └──────────┘  │
└───────────────────────────────────────────────┘
```

### How It Manages Multiple Modems/SIMs

1. **Configuration file `sim-cards.conf`:** Each modem has a dedicated INI section identified by a slot string (e.g., `[00]`, `[01]`). Each section specifies:
   - `port` — serial device path (supports wildcards like `/dev/ttyACM*`)
   - `phone_number` — the SIM's phone number (used for routing and identification)
   - `pin` — SIM PIN for unlocking
   - `imei` — modem identifier for USB re-enumeration resilience
   - `provider` — carrier name (informational)
   - `prefixes` — phone number prefixes this modem handles (E.123 international format)
   - `costs_per_sms` — cost per SMS for routing decisions
   - `ussd_account_balance` / `ussd_account_balance_regexp` — USSD code and regex for prepaid balance checking
   - `account_balance_warning` / `account_balance_critical` — balance thresholds for monitoring
   - `health_check_interval` — seconds between self-checks
   - `encoding` — SMS encoding (e.g., UCS2)

2. **SMS Router:** A cost-based routing engine that selects which modem to use for outgoing SMS based on the destination phone number prefix and the `costs_per_sms` setting. The standard router prefers low costs. If no prefix matches, the message is undeliverable.

3. **Modem identification by IMEI:** USB device paths change on reboot. SMSgate uses the IMEI to probe and identify which serial port corresponds to which modem. A `serial_ports_hint_file` caches previous associations to speed up reconnection.

4. **Health checking:** Each modem periodically performs self-checks including network connectivity, account balance (via USSD), and an optional self-test SMS (monthly/weekly/daily) to keep the SIM active.

5. **API:** XML-RPC over TLS with bcrypt-hashed API tokens for:
   - `send_sms` — send SMS via a specific modem
   - `send_ussd` — send USSD codes
   - `get_sms` — retrieve received SMS (per-modem tokens allow assigning modems to users/projects)
   - `get_health_state` — for Icinga monitoring
   - `get_stats` — for Munin monitoring

6. **SMS persistence:** **No persistence** — each SMS is kept in memory only. This is a deliberate design choice (pentesting use case: messages should not survive on disk).

### Tested Hardware
- ZTE MF 190 (USB surfstick)
- Quectel M35 modules (modem pool)
- SIM7600E modules (modem pool)

### Limitations
- SMS/MMS only — **no RCS support**
- No message persistence
- Simple cost-based routing only (no round-robin, no load balancing)
- No user management (API key-based only)
- XML-RPC API (not REST/JSON)
- Single-server architecture

---

## 2. Other Open-Source Multi-SIM SMS Tools

### 2.1 Kannel

- **URL:** https://kannel.org/  
- **Repository:** https://github.com/Ahilanen/kannel (community mirror)  
- **License:** Open source (BSD-like)  
- **Language:** C  
- **Status:** Mature, widely deployed, but development has slowed significantly

**Architecture:**
- Three core daemons: `bearerbox` (SMS center connection manager), `smsbox` (SMS routing/handling), `wapbox` (WAP gateway, legacy)
- Connects to SMSCs via SMPP, UCP/EMI, CIMD2, or GSM modems via AT commands
- HTTP-based API for sending/receiving SMS
- Supports multiple SMSC connections simultaneously
- Very high throughput (designed for carrier-scale: trillions of SMS)

**Multi-SIM support:** Kannel manages multiple SMSC/modem connections through `bearerbox` configuration. Each connection is a separate "group" in the config. Routing is by SMS center, not by SIM card.

**RCS support:** ❌ None. Kannel is SMS/WAP-only. No RCS extension exists. The Kannel architecture is deeply SMS-centric (SMPP protocol, GSM 03.40 message format). Adding RCS would require a completely new module.

**Key strength:** Carrier-grade SMS throughput. Best choice if you need to connect to telecom SMSCs directly.

---

### 2.2 SMSTools3

- **URL:** https://smstools3.kekekasvi.com/  
- **Repository:** Not on GitHub (maintained on the website)  
- **License:** GPL  
- **Language:** C  
- **Status:** Stable, last major update ~2017, still widely used

**Architecture:**
- File-based SMS gateway: send SMS by placing text files in an `outgoing/` directory; received SMS appear in `incoming/`
- Event-driven with scripts: `eventhandler` runs custom scripts on send/receive
- Each modem gets its own configuration section in `/etc/smsd.conf`
- Supports GSM modems via serial/USB (AT commands)

**Multi-SIM support:** Yes — each modem is configured as a separate device with its own queue. The daemon manages a pool of modems. Round-robin or specified-modem sending.

**RCS support:** ❌ None. AT-command-based SMS only.

**Key strength:** Dead-simple "drop a file to send SMS" interface. Extremely reliable for basic SMS. Easy to integrate with scripts.

---

### 2.3 Gammu / Gammu-SMSD

- **URL:** https://wammu.eu/  
- **Repository:** https://github.com/gammu/gammu  
- **License:** GPL  
- **Language:** C (core), Python bindings available  
- **Status:** Actively maintained, comprehensive phone/modem support

**Architecture:**
- `gammu` — CLI tool for single phone/modem operations
- `gammu-smsd` — daemon for send/receive with database backend (MySQL, PostgreSQL, SQLite, etc.)
- Multiple modem support via separate config files and separate daemon instances per modem
- `PhoneID` field in database for routing messages to specific modems

**Multi-SIM configuration:**
Each modem needs its own `gammu-smsd` instance with a separate config file. All instances can share the same database. The `PhoneID` field in the database `outbox` table routes messages to specific modems. A common pattern (documented in community guides):

```ini
# /etc/gammu-smsdrc-modem1
[gammu]
port = /dev/ttyUSB0
model = 

[smsd]
Service = sql
Driver = native_mysql
Host = localhost
User = smsd
Password = smsd
Database = smsd
PhoneID = modem1
```

Multiple instances: `gammu-smsd -c /etc/gammu-smsdrc-modem1`, `gammu-smsd -c /etc/gammu-smsdrc-modem2`, etc.

**Known issue:** Modem pools with shared IMEI (e.g., 16-port modem pool appearing as one device) require careful port mapping. GitHub issue #334 documents this: each SIM port runs its own `gammu-smsd` instance with a different serial port but the same IMEI.

**RCS support:** ❌ None. Gammu operates at the AT command level.

**Key strength:** Most comprehensive modem/phone compatibility. Active maintenance. Database-backed persistence. Python API.

---

### 2.4 PlaySMS

- **URL:** https://playsms.org/  
- **Repository:** https://github.com/antonraharja/playSMS  
- **License:** GPL  
- **Language:** PHP  
- **Status:** Actively maintained, web-based SMS gateway with GUI

**Architecture:**
- Web-based SMS gateway with user management, routing, scheduling
- Uses Gammu or Kannel as backend modem drivers
- Multi-user, multi-gateway support
- Feature-rich: SMS polling, auto-reply, forward, command execution on receive
- Web UI for administration

**Multi-SIM support:** Via gateway configuration — can manage multiple Gammu/Kannel instances through the web UI.

**RCS support:** ❌ None. Inherited from Gammu/Kannel limitations.

**Key strength:** Only tool with a proper web GUI. User management. Best for teams needing a visual admin interface.

---

### 2.5 TextBee

- **URL:** https://textbee.dev/  
- **Repository:** https://github.com/vernu/textbee  
- **License:** MIT  
- **Language:** JavaScript/TypeScript (Next.js + React Native Android app)  
- **Status:** Active development (2023+)

**Architecture:**
- Android app installed on the phone acts as the SMS gateway
- REST API exposed through a cloud relay server (or direct device access)
- Web dashboard for managing phones and sending messages
- Firebase-based real-time communication between phone and API

**Multi-SIM support:** Each Android phone is a separate gateway. Multiple phones can be registered to the same account.

**RCS support:** ❌ SMS only. Uses Android's SMS API (`SmsManager`), not RCS.

**Key strength:** Modern architecture (REST API, web UI). No GSM modem hardware needed — uses Android phones directly. Easiest to set up.

---

### 2.6 android-sms-gateway (capcom6)

- **URL:** https://github.com/capcom6/android-sms-gateway  
- **License:** Open source  
- **Language:** Kotlin (Android app), PHP/Python (server)  
- **Status:** Active development (2024+)

**Architecture:**
- Android app runs on the phone, exposing SMS send/receive via API
- Supports direct device access (local API) or cloud relay
- Privacy-focused: no registration required, no phone number collection
- Webhook support for incoming SMS notifications

**RCS support:** ❌ SMS only.

---

### 2.7 SMSsync (Ushahidi)

- **URL:** http://smssync.ushahidi.com/  
- **Repository:** https://github.com/ushahidi/SMSSync  
- **License:** GPL  
- **Language:** Java (Android)  
- **Status:** Legacy — last significant update ~2018

**Architecture:**
- Android app that forwards received SMS to a web endpoint
- Designed for data collection in developing countries
- Very simple: SMS → HTTP POST to your server

**RCS support:** ❌ SMS only. Legacy project.

---

### 2.8 Jasmin SMS Gateway

- **URL:** https://github.com/jookies/jasmin  
- **License:** Apache 2.0  
- **Language:** Python (Twisted)  
- **Status:** Active, industry-grade

**Architecture:**
- SMPP-based SMS gateway (carrier-grade)
- Connects to SMSCs, not GSM modems
- Message routing, filtering, throttling
- HTTP API for sending

**RCS support:** ❌ SMPP/SMS only. No modem support.

---

### 2.9 httpSMS

- **URL:** https://httpsms.com/  
- **Repository:** Referenced from Reddit discussions  
- **Status:** Active

**Architecture:**
- Similar to TextBee: Android phone + web relay
- Open-source

---

### Comparison Table: Open-Source Multi-SIM Tools

| Tool | Language | Multi-Modem | SMS | RCS | API Type | GUI | Persistence | Status |
|------|----------|-------------|-----|-----|----------|-----|-------------|--------|
| **smsgate** | Python | ✅ (USB modem pool) | ✅ | ❌ | XML-RPC/TLS | ❌ | In-memory | Active (pentesting) |
| **Kannel** | C | ✅ (SMSC connections) | ✅ | ❌ | HTTP | ❌ | Queued | Mature/slow |
| **smstools3** | C | ✅ (multi-config) | ✅ | ❌ | File-based | ❌ | File-based | Stable/legacy |
| **Gammu-SMSD** | C | ✅ (multi-instance) | ✅ | ❌ | DB + CLI | ❌ | Database | Active |
| **PlaySMS** | PHP | ✅ (via backends) | ✅ | ❌ | HTTP + Web | ✅ | Database | Active |
| **TextBee** | JS/TS | ✅ (multi-phone) | ✅ | ❌ | REST + Firebase | ✅ | Cloud | Active |
| **android-sms-gateway** | Kotlin | ⚠️ (per-phone) | ✅ | ❌ | REST + Webhook | ❌ | Local | Active |
| **Jasmin** | Python | ✅ (SMPP) | ✅ | ❌ | HTTP/SMPP | ❌ | Queued | Active |
| **SMSsync** | Java | ❌ (single phone) | ✅ | ❌ | HTTP POST | ❌ | None | Legacy |

---

## 3. Beeper's Headless RCS Approach

### 3.1 Overview

Beeper is a Universal Chat app (acquired by Automattic in 2024) that aggregates multiple chat networks into a single interface. It supports RCS through a Google Messages bridge.

### 3.2 Architecture: How Beeper Connects to RCS

Beeper's RCS support works through a **Google Messages bridge** that runs on the user's Android phone:

```
┌───────────────────────────────────────────────────────┐
│  Beeper Cloud (Matrix Homeserver)                     │
│  - Bridges messages between networks                  │
│  - Matrix protocol for internal routing               │
│  - Open-source bridges at github.com/beeper           │
└───────────┬───────────────────────────────────────────┘
            │ Matrix protocol
            │
┌───────────▼───────────────────────────────────────────┐
│  Beeper Android App                                   │
│  - Go-based Matrix SDK (mautrix-go)                   │
│  - Connects to Beeper Cloud as Matrix client          │
│  - Runs local bridges (Signal, Google Messages)       │
└───────────┬───────────────────────────────────────────┘
            │
┌───────────▼───────────────────────────────────────────┐
│  Google Messages Bridge (on Android phone)             │
│  - Open source: github.com/beeper/googlemessages       │
│  - Bridges SMS/RCS ↔ Matrix                          │
│  - Requires Google Messages as default SMS app        │
│  - RCS messages bridge through Google Messages app    │
└───────────┬───────────────────────────────────────────┘
            │
┌───────────▼───────────────────────────────────────────┐
│  Google Messages App (on Android phone)                │
│  - Handles actual RCS registration                    │
│  - RCS Universal Profile via Jibe/cloud IMS            │
│  - Requires physical SIM + Android OS                  │
└───────────────────────────────────────────────────────┘
```

### 3.3 Key Technical Details

**Google Messages Bridge:**
- Open-source bridge: https://github.com/mautrix/googlemessages (mautrix project)
- Written in Go (consistent with Beeper's mautrix ecosystem)
- Bridges Google Messages SMS/RCS into Matrix
- Requires an Android phone with Google Messages installed and set as default SMS app
- The bridge reads messages from Google Messages and relays them to the Matrix homeserver
- For RCS specifically: the bridge piggybacks on Google Messages' existing RCS connection — it does NOT implement RCS protocol directly

**Beeper Android Architecture (from their blog, April 2024):**
- The Beeper Android app is built on a Go-based Matrix SDK (`mautrix-go`, ~70k lines)
- Local bridges run inside the Android app itself (not on a cloud server)
- This is a shift from their original architecture (Element/Matrix client + cloud bridges)
- Local bridges preserve end-to-end encryption because encryption keys stay on the device
- BPNS (Beeper Push Notification Service) handles push notifications when the app is backgrounded — it shares only push credentials (not identity/encryption keys)

**RCS Registration:**
- RCS registration happens through Google Messages on the phone
- The phone must have a SIM card with an active plan
- Google Messages handles RCS provisioning with the carrier
- Beeper's bridge then reads/writes through Google Messages' UI/content providers
- **RCS registration requires a physical Android phone** — Beeper has not decoupled RCS from Google Messages

### 3.4 Can It Be Replicated Without Proprietary Code?

**Partially yes, but with significant limitations:**

1. **Open-source components available:**
   - Matrix homeserver: Synapse (https://github.com/element-hq/synapse)
   - Google Messages bridge: mautrix/googlemessages (https://github.com/mautrix/googlemessages)
   - mautrix-go SDK: https://github.com/mautrix/mautrix-go
   - Beeper's bridge code is open source at github.com/beeper and github.com/mautrix

2. **What you CAN replicate:**
   - Set up your own Matrix homeserver (Synapse or Conduit)
   - Run the mautrix/googlemessages bridge on an Android phone
   - Bridge SMS/RCS messages from Google Messages into Matrix
   - Access messages from any Matrix client

3. **What you CANNOT replicate:**
   - Beeper's proprietary push notification service (BPNS) — but you can use Matrix's own push notifications
   - Beeper's polished mobile app — you'd use Element or another Matrix client
   - Beeper's cloud infrastructure for managing bridges
   - A headless RCS client without an Android phone — Beeper has not achieved this either

4. **The fundamental constraint:** Beeper's RCS bridge still requires a physical Android phone running Google Messages. It does NOT solve the "headless RCS" problem. Beeper has not reverse-engineered the RCS protocol to create a standalone client — they bridge through Google Messages.

### 3.5 Beeper's iMessage Approach (Context for RCS)

Beeper Mini (their iMessage client) took a fundamentally different approach:
- **Reverse-engineered** the iMessage protocol and encryption
- Built a **standalone** Android app that connects directly to Apple's servers (APNs)
- No Mac server relay needed
- Based on open-source research: https://github.com/JJTech0130/pypush
- Messages are end-to-end encrypted, keys never leave the device

**Why hasn't Beeper done the same for RCS?**
- Google's RCS implementation (via Jibe) is far more complex than iMessage's APNs-based protocol
- RCS requires IMS AKA authentication (tied to SIM card's K key)
- Google enforces Play Integrity checks for RCS
- RCS registration is carrier-dependent with multiple provisioning paths
- No security researcher has published a clean reverse-engineering of the Jibe RCS protocol comparable to jjtech's iMessage work

---

## 4. Open Source RCS Client/Server Projects

### 4.1 rcsjta (GSMA RCS-e Reference Implementation)

- **Repository:** https://github.com/android-rcs/rcsjta  
- **Description:** GSMA RCS-e stack for Android with GSMA API  
- **Language:** Java  
- **Status:** **Inactive/legacy** — this was the GSMA reference implementation from the RCS-e (RCS "lite") era (~2012-2015). Not compatible with modern RCS Universal Profile. The code is unmaintained and predates Google Jibe.

### 4.2 free-rcs-server (FreeJoyn)

- **Repository:** https://github.com/FreeJoyn/free-rcs-server  
- **Description:** Free and open source RCS server  
- **Status:** Early/experimental. Implements RCS server-side components but is not production-ready and does not implement the full Universal Profile.

### 4.3 RCS-Server (Kamailio-based)

- **Repository:** https://github.com/jega-ms/RCS-Server  
- **Description:** RCS Server Using Kamailio  
- **Status:** Experimental. Uses Kamailio SIP server as a base for RCS server functionality. Not a complete RCS implementation.

### 4.4 rcs-fi-client (POC)

- **Repository:** https://github.com/zwyuan/rcs-fi-client  
- **Description:** POC RCS client for Google Messages service  
- **Status:** Research/proof-of-concept. Attempts to build a standalone RCS client that connects to Google's Jibe infrastructure. Early stage.

### 4.5 Google RCS Business Messaging Repositories

- **Repository:** https://github.com/orgs/rcs-business-messaging/repositories  
- **Description:** Google's official RCS Business Messaging (RBM) SDK and samples  
- **Note:** This is B2P (business-to-person) only, not P2P RCS. Requires Google partner registration.

### 4.6 microg/GmsCore

- **Repository:** https://github.com/microg/GmsCore  
- **Description:** Open-source Google Play Services implementation  
- **RCS relevance:** Community has attempted to enable RCS through microG, but RCS support is limited. Google's Carrier Services (com.google.android.ims) is required for RCS and is not fully replicated in microG. Issue #2063 tracks RCS support progress.

**Key finding:** No open-source project provides a working, modern RCS Universal Profile client. The closest is the rcs-fi-client POC, which is very early stage. The free-rcs-server and RCS-Server projects attempt server-side RCS but are not production-quality.

---

## 5. How to Extend smsgate or Similar Tools from SMS → RCS

### 5.1 What Would Need to Change

Extending any existing SMS gateway tool to support RCS requires fundamental architectural changes:

| Component | SMS Gateway (Current) | RCS Gateway (Required) |
|-----------|----------------------|----------------------|
| **Transport** | AT commands over serial/USB | IP-based (SIP/MSRP over IMS or HTTPS to Jibe) |
| **Modem interface** | Direct AT command to GSM modem | Android OS + Google Messages app |
| **Authentication** | SIM PIN only | IMS AKA (SIM K key) + Play Integrity attestation |
| **Registration** | Insert SIM, enter PIN | RCS provisioning via ACS, Jibe cloud registration |
| **Message format** | GSM 03.40 (PDU mode) | RCS Universal Profile (CPIM, MSRP) |
| **Session management** | Stateless (per-message AT commands) | Stateful (persistent SIP registration, MSRP sessions) |
| **Fallback** | N/A (SMS is baseline) | SMS fallback when RCS unavailable |
| **Read receipts** | Not supported | Integrated (is-composing, delivered, read) |
| **Rich media** | Not supported | File transfer via HTTP (FTS), rich cards |
| **E2E encryption** | Not supported | Optional (MLS in Universal Profile 3.0) |

### 5.2 Why You Can't Just "Add RCS" to smsgate

The fundamental problem: **RCS cannot be sent via AT commands.** GSM modems expose SMS through AT+CMGS, AT+CMGR, etc. There is no AT command for RCS. RCS is an IP-based application-layer protocol that requires:
1. An IP data connection (not just a cellular modem)
2. SIP registration with the carrier's IMS core (or Google Jibe)
3. IMS AKA authentication using the SIM's cryptographic key
4. A persistent MSRP session for messaging
5. Compliance with Google's Play Integrity attestation

### 5.3 Realistic Extension Path: Hybrid Architecture

Rather than extending smsgate's transport layer, the practical approach is a **hybrid architecture** that uses Android phones as "RCS modems" alongside traditional GSM modems for SMS:

```
┌──────────────────────────────────────────────────────┐
│             Unified Messaging Gateway                  │
│  (New orchestration layer, could fork smsgate)        │
│                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ SMS Router   │  │ RCS Router   │  │ Fallback    │ │
│  │ (prefix-     │  │ (phone pool  │  │ Manager     │ │
│  │  based)      │  │  assignment)  │  │ (RCS→SMS)   │ │
│  └──────┬───────┘  └──────┬───────┘  └─────────────┘ │
│         │                 │                           │
│  ┌──────▼─────────────────▼──────────────────────┐   │
│  │              Message Queue (Redis/RabbitMQ)    │   │
│  └──────┬─────────────────┬──────────────────────┘   │
│         │                 │                           │
└─────────┼─────────────────┼───────────────────────────┘
          │                 │
   ┌──────▼──────┐   ┌──────▼──────────────────────┐
   │ GSM Modem   │   │ Android Phone Farm            │
   │ Pool        │   │ (each phone = 1 RCS "modem")  │
   │ (smsgate/   │   │                               │
   │  gammu/     │   │ ┌─────┐ ┌─────┐ ┌─────┐     │
   │  smstools3) │   │ │Phone│ │Phone│ │Phone│     │
   │             │   │ │  1  │ │  2  │ │  N  │     │
   │ Quectel M35 │   │ │     │ │     │ │     │     │
   │ SIM7600E    │   │ │GM+  │ │GM+  │ │GM+  │     │
   │ via AT cmds │   │ │SIM#1│ │SIM#2│ │SIM#N│     │
   └─────────────┘   │ └─────┘ └─────┘ └─────┘     │
                     │  ADB control / Agent App      │
                     └───────────────────────────────┘
```

### 5.4 What to Reuse from smsgate

If forking smsgate as the orchestration base:
- ✅ **SMS Router** (prefix-based routing) — reuse for SMS portion
- ✅ **SIM card configuration model** — adapt for phone configuration
- ✅ **Health checking** — adapt for RCS connection status
- ✅ **API token authentication** — reuse as-is
- ✅ **USSD/account balance checking** — reuse for SMS SIMs
- ✅ **Icinga/Nagios monitoring** — extend for RCS phone health
- ❌ **Modem pool manager** — replace with phone farm manager
- ❌ **XML-RPC API** — replace with REST API
- ❌ **SMTP forwarding** — extend to support webhooks

---

## 6. Android Phones as "RCS Modems"

### 6.1 Can Android Phones Controlled via ADB/scrcpy Serve as RCS Modems?

**Yes — this is currently the only viable approach for P2P RCS from real phone numbers.**

An Android phone with an active SIM, running Google Messages with RCS registered, can function as a single "RCS modem." The phone provides:
- RCS registration with the carrier (via Google Messages)
- RCS message sending/receiving (via Google Messages)
- Read receipts, typing indicators, rich media
- E2E encryption (where supported)

### 6.2 Control Methods

| Method | Direction | Speed | Reliability | Notes |
|--------|-----------|-------|-------------|-------|
| **ADB `input tap`** | Send only | ~2-5 sec/msg | Low | Breaks on UI updates |
| **Intent `ACTION_SENDTO`** | Send (requires tap) | ~3-5 sec/msg | Medium | Pre-fills message, needs manual send |
| **ADB `service call isms`** | SMS only (NOT RCS) | ~0.5 sec/msg | High | AT-command equivalent; no RCS path |
| **Accessibility Service** | Send + Receive | ~1-2 sec/msg | Medium-High | Best UI automation approach |
| **Content Provider** (`content://mms`) | Receive only | ~1-5 sec polling | High | Reads RCS messages from MMS provider |
| **Notification Listener** | Receive only | Real-time | High | Detects incoming messages |
| **Custom Agent App** (recommended) | Bidirectional | ~1-2 sec/msg | High | Accessibility + Content Provider + WebSocket |
| **scrcpy** | Debug/monitoring | N/A | N/A | Good for development, not for production automation |
| **Appium** | Send + Receive | ~3-10 sec/msg | High | Overkill for this use case |

### 6.3 Recommended Architecture for RCS "Modem" Phones

Each phone should run a **custom Agent App** that:
1. **Monitors RCS status** — reads Google Messages settings for "Connected"/"Disconnected" state
2. **Receives RCS messages** — polls `content://mms` content provider + Notification Listener
3. **Sends RCS messages** — via Accessibility Service controlling Google Messages UI
4. **Reports to orchestrator** — via WebSocket connection to central server
5. **Auto-recovers** — detects RCS disconnection, clears cache, re-registers

### 6.4 RCS Connection Stability

| Scenario | Expected Behavior | Recovery Time |
|----------|------------------|---------------|
| Phone reboot | RCS re-registration required | 5-30 min |
| Network change (Wi-Fi ↔ LTE) | May trigger re-registration | 1-10 min |
| Google Messages app update | Likely de-registration | 5-30 min |
| SIM state change | Re-registration required | 5-30 min |
| Prolonged offline (>24hr) | RCS disconnects | 5-30 min |
| Play Integrity failure | RCS blocked entirely | May require Magisk module |

**Expected RCS uptime per phone:** 85-95% with active monitoring and auto-recovery.

---

## 7. Key GitHub Repositories

### Multi-SIM SMS Gateways

| Repository | Stars | Description |
|-----------|-------|-------------|
| https://github.com/pentagridsec/smsgate | — | Python multi-modem SMS gateway (pentesting) |
| https://github.com/gammu/gammu | 800+ | C-based GSM modem/phone tool + SMSD daemon |
| https://github.com/antonraharja/playSMS | 800+ | PHP web-based SMS gateway with GUI |
| https://github.com/vernu/textbee | 400+ | Android phone SMS gateway (modern, REST API) |
| https://github.com/capcom6/android-sms-gateway | 200+ | Kotlin Android SMS gateway app |
| https://kannel.org/ (no primary GitHub) | — | C-based carrier-grade SMS/WAP gateway |
| https://smstools3.kekekasvi.com/ | — | C-based file-system SMS gateway |

### RCS-Related

| Repository | Stars | Description |
|-----------|-------|-------------|
| https://github.com/android-rcs/rcsjta | 50+ | GSMA RCS-e reference (legacy, unmaintained) |
| https://github.com/FreeJoyn/free-rcs-server | — | Open source RCS server (experimental) |
| https://github.com/jega-ms/RCS-Server | — | RCS server using Kamailio (experimental) |
| https://github.com/zwyuan/rcs-fi-client | — | POC RCS client for Google Messages |
| https://github.com/microg/GmsCore | 7000+ | Open-source Google Play Services (partial RCS) |
| https://github.com/mautrix/googlemessages | 200+ | Matrix bridge for Google Messages (Beeper) |
| https://github.com/rcs-business-messaging | — | Google RBM SDK (B2P only) |

### Beeper Ecosystem

| Repository | Stars | Description |
|-----------|-------|-------------|
| https://github.com/mautrix/mautrix-go | 500+ | Go Matrix client library (powers Beeper) |
| https://github.com/mautrix/signal | 400+ | Matrix bridge for Signal |
| https://github.com/mautrix/googlemessages | 200+ | Matrix bridge for Google Messages |
| https://github.com/beeper/imessage | — | Go iMessage library |
| https://github.com/JJTech0130/pypush | — | Python iMessage POC (basis for Beeper Mini) |
| https://github.com/element-hq/synapse | 12000+ | Matrix homeserver |

### Android Phone Farm / SIM Research

| Repository | Stars | Description |
|-----------|-------|-------------|
| https://github.com/zhuowei/SimServerAndroid | — | HTTP API for SIM AKA authentication |
| https://github.com/fasferraz/SWu-IKEv2 | — | VoWiFi EAP-AKA' client |
| https://github.com/emanuele-f/PCAPdroid | — | No-root Android network capture |

---

## 8. Beeper's Approach: Replicability Assessment

### Can Beeper's RCS approach be replicated without proprietary code?

| Component | Open Source? | Replicable? | Notes |
|-----------|-------------|-------------|-------|
| Matrix homeserver | ✅ Yes (Synapse) | ✅ Yes | Self-host Synapse or Conduit |
| Google Messages bridge | ✅ Yes (mautrix) | ✅ Yes | github.com/mautrix/googlemessages |
| Matrix client | ✅ Yes (Element) | ✅ Yes | Multiple clients available |
| Push notifications (BPNS) | ❌ No | ⚠️ Partial | Use Matrix's own push or UnifiedPush |
| Beeper Android app | ❌ No | ⚠️ Partial | Use Element Android or Nheko |
| RCS registration | ❌ Requires phone | ❌ No | Must have Android phone with SIM |
| Headless RCS | ❌ Not achieved | ❌ No | Even Beeper needs a physical phone |

**Verdict:** You can replicate the Beeper RCS bridge architecture using entirely open-source components, but you **still need a physical Android phone with an active SIM for each RCS connection**. Beeper has not solved the headless RCS problem, and neither has anyone else in the open-source world.

### What Beeper Has NOT Done
- Built a standalone RCS client (without Google Messages dependency)
- Reverse-engineered the Jibe RCS protocol
- Created a headless RCS registration process
- Decoupled RCS from Android OS

---

## 9. Practical Recommendations

### Best Existing Tool to Fork for RCS Extension

**Recommendation: Build a new orchestration layer rather than forking any single tool.**

However, if you must pick one:

#### Option A: Fork TextBee (Recommended for Greenfield)
**Why:** Modern architecture (REST API, TypeScript, React Native, Firebase), Android-phone-based (matches RCS requirement), active development, MIT license, simplest codebase to extend.

**What to add:**
- RCS-aware phone management (RCS status tracking, auto-recovery)
- ADB/agent app integration for RCS message control
- Fallback routing (RCS → SMS)
- Multi-phone orchestration with health monitoring

**Effort:** Medium (3-6 months for MVP)

#### Option B: Fork smsgate + Build Phone Farm
**Why:** Mature multi-modem management, health checking, monitoring integration. Best if you need both GSM modem SMS AND phone-based RCS.

**What to add:**
- REST API (replace XML-RPC)
- Phone farm management alongside modem pool
- RCS router (parallel to SMS router)
- Agent app for Android phones
- Fallback management

**Effort:** High (6-12 months for MVP)

#### Option C: Build on mautrix/googlemessages (Recommended for Matrix Integration)
**Why:** Already implements the Google Messages bridge. If your target architecture uses Matrix, this is the natural starting point.

**What to add:**
- Multi-phone management (currently 1:1 bridge)
- RCS health monitoring
- Auto-recovery on RCS disconnection
- Phone provisioning automation

**Effort:** Medium (3-6 months for MVP)

### Recommended Architecture for Multi-SIM RCS Gateway

```
                    ┌─────────────────────┐
                    │   REST API Gateway   │
                    │   (FastAPI/Node.js)  │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │    Orchestrator     │
                    │    (Python/Go)      │
                    │                    │
                    │  ┌──────────────┐  │
                    │  │ RCS Router   │  │
                    │  │ (round-robin │  │
                    │  │  or prefix)  │  │
                    │  └──────┬───────┘  │
                    │         │          │
                    │  ┌──────▼───────┐  │
                    │  │ Phone Farm   │  │
                    │  │ Manager      │  │
                    │  │ - Health     │  │
                    │  │ - Assignment │  │
                    │  │ - Recovery   │  │
                    │  └──────────────┘  │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
     ┌────────▼─────┐ ┌──────▼──────┐ ┌──────▼──────┐
     │  Phone 1     │ │  Phone 2    │ │  Phone N    │
     │  Android 10+ │ │  Android 10+│ │  Android 10+│
     │  Google Msgs │ │  Google Msgs│ │  Google Msgs│
     │  Agent App   │ │  Agent App  │ │  Agent App  │
     │  SIM #1      │ │  SIM #2     │ │  SIM #N     │
     │  RCS ✅      │ │  RCS ✅     │ │  RCS ✅     │
     └──────────────┘ └─────────────┘ └─────────────┘
```

### Implementation Priorities

1. **Phase 1 (Weeks 1-4):** Build Agent App for Android phones (Accessibility Service + Content Provider reader + WebSocket client)
2. **Phase 2 (Weeks 5-8):** Build Orchestrator server (FastAPI, Redis queue, phone health monitoring)
3. **Phase 3 (Weeks 9-12):** RCS message sending via Agent App's accessibility service
4. **Phase 4 (Weeks 13-16):** Auto-recovery, RCS status monitoring, SMS fallback
5. **Phase 5 (Weeks 17-20):** Scale testing, multi-phone load balancing, dashboard

### Cost Estimate for 10-Phone RCS Farm

| Component | Cost | Notes |
|-----------|------|-------|
| 10x Cheap Android phones | $300-500 | BLU/Alcatel/Moto E ($30-50 each) |
| 2x USB hubs (20-port) | $100-160 | Anker/Sabrent data+charging |
| 1x Server | $200-500 | Linux box for orchestrator |
| SIM plans (monthly) | $50-300 | $5-30/mo per line (MVNOs) |
| **Total setup** | **~$600-1,160** | |
| **Monthly** | **$50-300** | SIM plans + electricity |

---

## 10. Summary of Key Findings

1. **No existing open-source tool supports RCS.** All multi-SIM tools (smsgate, Kannel, smstools3, gammu, PlaySMS, TextBee) are SMS/MMS-only via AT commands. RCS operates on a completely different protocol layer.

2. **smsgate** is the best-audited multi-modem SMS gateway (Python, pentesting-focused, health monitoring, prefix routing), but extending it to RCS would require replacing its entire transport layer.

3. **Beeper's RCS bridge** is not a headless RCS client — it's a Matrix bridge that runs on an Android phone and piggybacks on Google Messages' existing RCS connection. It's open-source (mautrix/googlemessages) and can be replicated, but still requires physical Android phones.

4. **Android phones are the only viable "RCS modems."** No GSM modem, SIM bank, or modem pool can send RCS messages. A phone running Google Messages with an active SIM and RCS registration is the minimum viable unit.

5. **No open-source RCS Universal Profile client exists.** The rcsjta project is legacy/unmaintained. The rcs-fi-client is an early POC. The free-rcs-server is experimental.

6. **The best path forward** is a hybrid architecture: Android phone farm for RCS + traditional GSM modem pool for SMS, unified under a new orchestration layer that handles routing, health monitoring, and RCS→SMS fallback.

7. **For forking:** TextBee (modern, Android-phone-based, REST API) is the best starting point for a greenfield RCS gateway. smsgate is best if you need to keep GSM modem SMS alongside. mautrix/googlemessages is best if you're building on Matrix.

---

*Report compiled: 2026-05-15*  
*Sources: pentagridsec/smsgate, kannel.org, smstools3.kekekasvi.com, wammu.eu/gammu, playsms.org, textbee.dev, blog.beeper.com, github.com/mautrix, github.com/android-rcs, github.com/microg, existing rcs-research reports*
