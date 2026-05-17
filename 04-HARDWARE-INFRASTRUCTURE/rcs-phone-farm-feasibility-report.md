# Android Phone Farm RCS Gateway — Feasibility Report

**Date:** 2026-05-15  
**Scope:** Using multiple Android phones (each with its own SIM) running Google Messages, controlled programmatically from a server, as an RCS gateway farm.

---

## Executive Summary

An Android phone farm for RCS gateway is **technically possible but operationally challenging**. The core difficulty is that Google provides **no public API for sending/receiving person-to-person RCS messages** — RCS is locked inside Google Messages. The only reliable way to automate RCS sending is via **UI automation** (accessibility services, ADB input injection, or scrcpy screen control), which is fragile and slow. Reading incoming RCS messages is partially possible through the `content://mms` content provider. RCS connection stability is a known pain point. For production use, the **RCS Business Messaging API** or a **headless SIP/IMS client** would be far more reliable, but they serve different use cases (business-to-consumer vs. person-to-person).

---

## 1. Android Intent System & RCS

### Can Intents send RCS messages through Google Messages?

**Partially, but not for automated RCS sending.**

- **`ACTION_SENDTO` with `sms:` URI** opens Google Messages with a pre-filled recipient and body, but does **not** automatically send. The user must press the Send button:
  ```bash
  adb shell am start -a android.intent.action.SENDTO -d sms:+1234567890 --es sms_body "Test" --ez exit_on_sent false
  ```
  This pre-fills the compose screen. If RCS is enabled and the recipient supports RCS, Google Messages **will** send via RCS when the user hits Send. But there is **no intent extra to auto-send**.

- **`com.google.android.apps.messaging` intents**: Google Messages has internal intents/activities for composing messages, but none expose a "send RCS message" action that can be triggered from outside the app.

- **Hidden RCS API (XDA discovery, 2021)**: Google Messages was found to have a hidden API (`com.google.android.apps.messaging.shared RCS API`) intended for Samsung's "Call & Message Continuity" feature. This API is **Samsung-specific** and not generally accessible to third-party apps. It was never opened to the public.

- **Android RCS TestRcsApp**: Google's AOSP includes a `TestRcsApp` (`android.googlesource.com/platform/packages/services/Telephony/+/master/testapps/TestRcsApp/`) that demonstrates RCS APIs, but these are **system-level APIs** requiring platform signing and are not available to regular apps.

**Verdict:** Intents cannot programmatically send RCS messages without user interaction. No public intent-based RCS sending API exists.

---

## 2. ADB Automation for Google Messages / RCS

### Can ADB be used to automate Google Messages for RCS sending?

**Yes, via UI automation — but it's a hack, not a clean API.**

### ADB SMS Sending (NOT RCS)
ADB can send **SMS** (not RCS) directly via the `isms` service:
```bash
# Android 10+:
adb shell service call isms 5 i32 1 s16 "com.android.mms" s16 "null" s16 "+1234567890" s16 "null" s16 "Hello" s16 "null" s16 "null" i32 0 i64 0
```
- This calls `sendTextForSubscriber()` on the ISms AIDL interface.
- The method index (5, 7) changes between Android versions — must consult the AIDL.
- **This always sends as SMS, never as RCS.** The `isms` service has no RCS path.

### ADB UI Automation for RCS (the "tap the screen" approach)
To send RCS, you must:
1. Launch Google Messages to a conversation: `adb shell am start -a android.intent.action.SENDTO -d sms:+1234567890 --es sms_body "Hello"`
2. Use `adb shell input tap X Y` to tap the Send button
3. Or use `adb shell input keyevent` to press Enter/Send

This approach:
- **Works** but requires knowing screen coordinates (which vary by device/resolution)
- Is **slow** (~2-5 seconds per message due to UI rendering)
- **Breaks** if Google Messages UI changes in an update
- Requires the phone screen to be on (or use "show touches" / accessibility workarounds)
- Cannot easily distinguish whether the message went via RCS or fell back to SMS

**Verdict:** ADB can automate RCS sending through UI manipulation, but it's fragile, slow, and version-dependent.

---

## 3. Accessibility Services for RCS Automation

### Can accessibility services automate RCS message sending/receiving?

**Yes — this is the most robust UI automation approach.**

An Android Accessibility Service can:
- **Observe UI events** in Google Messages (new messages arriving, compose field state)
- **Perform actions** on UI elements (click send button, type text in compose field)
- **Read message content** from the on-screen UI tree

**Key capabilities:**
- `performGlobalAction(ACTION_CLICK)` on identified UI nodes
- `dispatchGesture()` for precise touch injection
- Read `AccessibilityNodeInfo` trees to extract message content

**Limitations:**
- Still fundamentally UI automation — breaks on Google Messages updates
- Google may restrict accessibility service access to Messages in future Android versions
- Requires user to grant accessibility permission during setup
- Cannot differentiate RCS vs SMS from the accessibility tree alone (need to check message status indicators)

**Existing tools:**
- **Tasker** + AutoInput plugin: Can automate UI interactions, but Tasker explicitly **does not support RCS events**. From Tasker's feature request tracker: "Newer Android phones have Advanced Messaging which isn't recognized as SMS or MMS messages so Tasker is not able to capture or react to these events." Tasker can only react to SMS/MMS events.
- **AutoResponder.ai**: Can forward incoming messages to Tasker, but RCS support is unclear.
- **MacroDroid**: Similar to Tasker, RCS event detection is not supported natively.

**Verdict:** A custom accessibility service is the most reliable way to automate RCS through Google Messages UI, but it's still fragile. No existing automation app (Tasker, MacroDroid) natively supports RCS event triggers.

---

## 4. Content Providers & Reading RCS Messages

### Do content providers expose RCS messages for reading?

**Partially.** This is one of the more promising aspects.

### `content://mms` (MMS Content Provider)
- On devices with Google Messages as the default SMS app, **RCS messages are stored in the MMS content provider** (`content://mms` / `Telephony.Mms.CONTENT_URI`).
- Confirmed working on Google Pixel, Xiaomi, and Samsung devices.
- Query example:
  ```java
  Cursor cursor = contentResolver.query(
      Uri.parse("content://mms"),
      new String[]{"*"},
      "thread_id = ?",
      new String[]{threadId},
      null
  );
  ```
- This works for **reading** RCS messages but **cannot be used to send** them.

### GSMA RCS Content Provider
- URI: `content://com.gsma.services.rcs.provider.chat/chatmessage`
- Requires `com.gsma.services.permission.RCS` permission
- This permission is **not grantable to third-party apps** — it's a system/signature permission
- Even declaring it in manifest doesn't help — the OS refuses to grant it
- Samsung devices have `com.sec.imsservice.WRITE_IMS_PERMISSION` — also restricted

### `content://sms` Provider
- Only stores SMS messages, not RCS
- RCS messages that fall back to SMS will appear here

**Verdict:** RCS messages can be read via `content://mms` on Google Messages devices. The GSMA RCS provider exists but is locked behind system permissions. Reading is feasible; writing/sending via content provider is not possible.

---

## 5. Detecting RCS vs SMS Fallback

### How to detect whether a message was sent via RCS vs SMS fallback?

This is a **significant challenge** for the phone farm approach:

1. **In Google Messages UI**: RCS messages show "Sent", "Delivered", "Read" indicators (similar to iMessage). SMS shows "Sent" only (no delivery/read receipts). RCS also shows a blue bubble vs green for SMS.

2. **In content providers**: There's **no standard field** that explicitly marks a message as "RCS" vs "SMS". Both are stored in the MMS provider. Some heuristics:
   - RCS messages may have different `m_type` values in the MMS table
   - RCS messages may have `msg_box` values indicating read receipts
   - The presence of delivery receipts in the MMS parts may indicate RCS

3. **Accessibility service approach**: The accessibility tree may show "RCS" labels or status text that can be parsed.

4. **Notification listener**: RCS messages may generate different notification content than SMS.

**Verdict:** There's no clean programmatic way to determine RCS vs SMS delivery status. Heuristics from the MMS content provider or UI parsing are the only options, and both are unreliable.

---

## 6. Phone Farm Feasibility: N Android Phones Controlled by 1 Server

### Architecture

```
┌─────────────────────────────────────────────┐
│              Control Server                   │
│  (Python/Node.js orchestrator)               │
│                                              │
│  - REST API for send/receive                  │
│  - ADB over USB/TCP for each phone           │
│  - Message queue (Redis/RabbitMQ)            │
│  - Phone health monitoring                   │
│  - RCS registration status tracker           │
└──────────────┬───────────────────────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
  USB Hub   USB Hub   USB Hub
  (20-port) (20-port) (20-port)
    │          │          │
  [Phone]   [Phone]   [Phone]
  [Phone]   [Phone]   [Phone]
  ...        ...       ...
```

### 10-Phone Farm
- **1 server** with 1-2 USB hubs (20-port each, ~$50-80 each)
- Each phone connected via USB for ADB + charging
- Phones on Wi-Fi (for RCS data) or USB tethering
- Control via ADB + custom Android app (accessibility service + content provider reader)
- **Estimated cost**: $500-800 for phones + $150 for server + $100 for hubs = **~$1,050**
- **Monthly SIM cost**: ~$100-300 (depending on plan, $10-30/line)

### 100-Phone Farm
- **5 servers** or 1 powerful server with multiple PCIe USB cards
- Specialized "phone farm boxes" exist (e.g., PhoneFarmBox.com 20-port units at ~$200-300 each, need 5+)
- Rack-mounted phone shelves with integrated USB + power
- **Estimated cost**: $5,000-8,000 for phones + $2,000-5,000 for infrastructure = **~$10,000-15,000**
- **Monthly SIM cost**: ~$1,000-3,000

### Control Software Options
1. **ADB + Python (adroid/adb-shell)**: Direct ADB commands, `adb shell input tap`, `adb shell am start`, etc. Most flexible, most fragile.
2. **scrcpy**: Screen mirror + control. Can be scripted with `scrcpy --no-display --record` or by injecting input events. Good for debugging but not ideal for headless automation.
3. **Appium**: Mobile test automation framework. Can automate Google Messages UI. Supports multi-device parallel execution. Heavy overhead (Appium server + WebDriverAgent per device) but production-grade.
4. **Custom Android app**: Install a custom app on each phone that:
   - Runs an accessibility service to monitor/control Google Messages
   - Reads `content://mms` for incoming RCS messages
   - Exposes a local HTTP server (on the phone) or connects to the control server via WebSocket
   - This is the **most reliable approach** for a phone farm

---

## 7. RCS Registration Stability

### Does RCS stay registered on always-on phones over days/weeks?

**No — this is a major operational challenge.**

Common issues reported by users:
- **RCS disconnects daily** for many users, requiring cache clear or app restart
- RCS gets stuck on "Setting up... Trying to verify..." after phone reboots
- RCS re-verification is triggered by: network changes, app updates, SIM state changes, prolonged offline periods
- Google Messages RCS registration binds to the **SIM + Google account + device** triple — changing any of these breaks registration
- **Carrier-dependent**: Some carriers have more stable RCS than others

### Mitigation Strategies for Phone Farm
1. **Health check loop**: Periodically check RCS status (via accessibility service reading "Connected" status in Google Messages settings, or by sending a test message and checking if it goes RCS)
2. **Auto-re-registration**: If RCS disconnects:
   - Clear Google Messages cache: `adb shell pm clear com.google.android.apps.messaging`
   - Re-open and re-register: `adb shell am start -n com.google.android.apps.messaging/.ui.ConversationListActivity`
   - Wait for re-verification (can take 5-30 minutes)
3. **Lock Google Messages version**: Disable auto-updates to prevent version-change-triggered de-registrations
4. **Stable network**: Keep phones on consistent Wi-Fi; avoid network switching
5. **Keep phones awake**: Use `adb shell settings put global stay_on_while_plugged_in 3` and `adb shell svc power stayon true`
6. **Watchdog timer**: If RCS not connected after 30 minutes of re-registration attempt, reboot phone and try again

**Expected uptime**: Realistically **85-95%** per phone with active monitoring and auto-recovery. Plan for 10-15% of phones being in re-registration state at any time.

---

## 8. Cost Analysis

### Phone Hardware
| Item | Cost | Notes |
|------|------|-------|
| Cheap Android phone | $30-50 | BLU, Alcatel, Moto E series. Must support Android 10+ for current Google Messages. Must have Wi-Fi. |
| USB cable | $1-2 | USB-C or Micro-USB depending on phone |
| USB hub (20-port) | $50-80 | Anker, Sabrent. Must support data + charging. |
| Server | $200-500 | Any Linux box with enough USB ports / PCIe USB cards |
| Phone farm box | $200-300 | Dedicated 20-port Android phone connection boxes (phonefarmbox.com) |
| Ethernet/Wi-Fi switch | $50-100 | For phone Wi-Fi connectivity |

### Recurring Costs
| Item | Monthly Cost | Notes |
|------|-------------|-------|
| SIM plan (per line) | $10-30 | T-Mobile Connect ($10), Mint Mobile ($15), Tello ($5-10), US Mobile |
| Phone data | Included | RCS uses ~1-5KB per text message, negligible |
| Electricity | $10-30 | 10 phones @ 2-5W each + server |
| Maintenance | Variable | Phone replacements, SIM swaps, human intervention |

### 10-Phone Farm Total
- **Setup**: ~$1,000-1,500
- **Monthly**: ~$150-400 (SIMs + electricity)

### 100-Phone Farm Total
- **Setup**: ~$10,000-15,000
- **Monthly**: ~$1,500-4,000

---

## 9. How to Read Incoming RCS Messages Programmatically

### Method 1: Content Provider (Best)
```java
// On the Android phone, via a custom app with READ_SMS permission
Cursor cursor = contentResolver.query(
    Uri.parse("content://mms"),
    new String[]{"_id", "thread_id", "date", "msg_box", "m_type"},
    null, null, "date DESC"
);
```
- Poll every 1-5 seconds for new messages
- RCS messages appear in the MMS provider
- Need to parse MMS parts for actual message content

### Method 2: Notification Listener Service
- Register a `NotificationListenerService` to capture Google Messages notifications
- Extract message text from notification extras
- Works for new messages but not for reading message history

### Method 3: Accessibility Service
- Monitor Google Messages UI for new message events
- Read message content from the accessibility node tree
- Most reliable for detecting new messages in real-time

### Method 4: ADB + dumpsys
```bash
adb shell content query --uri content://mms
```
- Read MMS content from command line
- Slow, not suitable for high-frequency polling

**Recommended**: Custom Android app on each phone that combines Method 1 (polling `content://mms`) + Method 2 (notification listener) and reports new messages to the control server via WebSocket.

---

## 10. Practical Architecture: 10-Phone Farm

```
                    ┌─────────────────┐
                    │  API Gateway     │
                    │  (nginx/traefik) │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Orchestrator   │
                    │  (Python FastAPI)│
                    │                 │
                    │  - Route messages│
                    │  - Phone health  │
                    │  - Queue mgmt    │
                    │  - RCS status    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───┐  ┌──────▼─────┐  ┌────▼───────┐
     │  Phone 1   │  │  Phone 2   │  │  Phone N   │
     │            │  │            │  │            │
     │ - Custom   │  │ - Custom   │  │ - Custom   │
     │   Agent App│  │   Agent App│  │   Agent App│
     │ - Google   │  │ - Google   │  │ - Google   │
     │   Messages │  │   Messages │  │   Messages │
     │ - SIM #1  │  │ - SIM #2  │  │ - SIM #N  │
     └────────────┘  └────────────┘  └────────────┘
          │                │                │
     ┌────▼────────────────▼────────────────▼────┐
     │         USB Hub (20-port)                  │
     └──────────────────┬────────────────────────┘
                        │
                 ┌──────▼──────┐
                 │   Server    │
                 │  (Linux)    │
                 └─────────────┘
```

### Agent App (installed on each phone)
- **Accessibility Service**: Monitors Google Messages UI, can auto-send by tapping Send button
- **Notification Listener**: Detects incoming messages in real-time
- **Content Provider Reader**: Polls `content://mms` for message history
- **WebSocket Client**: Connects to orchestrator server, reports messages and status
- **Health Monitor**: Reports RCS connection status, battery, network state
- **Auto-Recovery**: Detects RCS disconnection, attempts re-registration

### Orchestrator Server
- **Message Queue**: Redis or RabbitMQ for outgoing messages
- **Phone Assignment**: Routes outgoing messages to available phones (round-robin or by sender identity)
- **Health Dashboard**: Real-time status of each phone's RCS connectivity
- **REST API**: External interface for sending/receiving messages
- **ADB Manager**: Direct ADB commands for phones that need intervention (restarts, cache clears)

---

## 11. Practical Architecture: 100-Phone Farm

### Scale-up challenges
- **USB port limits**: A single server supports ~127 USB devices theoretically, but practical limits are 40-60 per PCIe USB controller. Need 3-5 PCIe USB cards or multiple servers.
- **Wi-Fi capacity**: 100 phones on one Wi-Fi network needs enterprise-grade APs (Ubiquiti, etc.). Consider VLANs.
- **ADB connection stability**: ADB connections drop periodically. Need reconnection logic.
- **Power**: 100 phones @ 5W = 500W. Plus hubs and server. Need dedicated circuit.
- **Heat**: 100 phones in close proximity generate significant heat. Need ventilation or rack with active cooling.

### Recommended Architecture
- **5 sub-farms** of 20 phones each, each with its own server
- **Central orchestrator** coordinates across sub-farms
- **Phone farm boxes** (20-port integrated USB+power units) for physical organization
- **Kubernetes** or similar for orchestrator redundancy
- **SIM management**: Use an MVNO with API for SIM provisioning (Ting, Tello) or eSIMs where possible

---

## 12. Comparison: Phone Farm vs Headless SIP Client vs RBM API

| Factor | Phone Farm | Headless SIP/IMS Client | RCS Business Messaging API |
|--------|-----------|------------------------|---------------------------|
| **RCS Type** | Person-to-person (P2P) | Person-to-person (P2P) | Business-to-person (B2P) |
| **Sender Identity** | Real phone numbers (SIM) | Real phone numbers (SIP registration) | Brand/agent identity (not a phone number) |
| **Setup Complexity** | High (hardware, SIMs, UI automation) | Very High (IMS stack implementation) | Medium (Google partner onboarding) |
| **API Quality** | None (UI scraping) | Protocol-level (SIP/MSRP/RCS) | Clean REST API |
| **Throughput** | ~1-5 msg/sec per phone (UI-limited) | Potentially high (protocol-level) | High (cloud API) |
| **Reliability** | Low-Medium (RCS drops, UI breaks) | Medium-High (if IMS stack is correct) | High (managed by Google/carrier) |
| **Cost (10 units)** | $1,000-1,500 setup + $150-400/mo | $0 hardware + SIP service $50-200/mo | Free to start, per-message fees |
| **Cost (100 units)** | $10,000-15,000 setup + $1,500-4,000/mo | $0 hardware + SIP service $500-2,000/mo | Per-message fees (~$0.01-0.05/msg) |
| **E2E Encryption** | Yes (if RCS uses it) | Depends on implementation | No (RBM doesn't support E2E encryption) |
| **Read Receipts** | Yes (via UI) | Yes (via protocol) | Yes (via API) |
| **Media Support** | Yes (via UI) | Yes (via MSRP) | Yes (rich cards, media) |
| **Legal Risk** | Medium (ToS concerns with carrier) | Low-Medium | Low (legitimate business channel) |
| **Carrier Blocking** | Possible (unusual usage patterns) | Possible | Not applicable |

### Headless SIP/IMS Client Details
- RCS is implemented on top of **SIP** (Session Initiation Protocol) and **MSRP** (Message Session Relay Protocol) over **IMS** (IP Multimedia Subsystem)
- A headless SIP client would register with the carrier's IMS server and send/receive RCS messages at the protocol level
- **Open source IMS stacks**: None that are production-ready for consumer RCS. The closest is `rcsjta` (old, unmaintained, GSMA reference implementation)
- **Challenges**: Each carrier has a different IMS configuration (different SIP servers, authentication methods, RCS profiles). You'd need to reverse-engineer each carrier's setup.
- **No existing product** does this — building a headless RCS SIP client is essentially a research project
- Would need SIM cards for IMS authentication (same as phone farm, but no phone needed)

### RCS Business Messaging (RBM) API Details
- Google's official API for businesses to send RCS messages
- **Not person-to-person** — messages come from a "brand agent", not a phone number
- Requires: Google partner registration, brand verification, carrier integration
- **Use case**: Customer service, marketing, notifications — not impersonating individual phone numbers
- Free tier available; per-message fees at scale
- **This cannot replace a phone farm if you need P2P RCS from real phone numbers**

---

## 13. Key Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Google Messages UI update breaks automation | High | Lock app version, implement UI element detection by content not coordinates, test updates before deploying |
| RCS disconnection/re-registration loops | High | Automated re-registration, health monitoring, over-provision phones by 15-20% |
| Carrier detects unusual usage and blocks SIMs | Medium | Rate limit messages, simulate human-like patterns, rotate across phones |
| Accessibility service revoked by Android update | Medium | Fallback to ADB input injection, monitor Android release notes |
| Content provider schema changes | Medium | Version detection, multiple query strategies |
| USB connection drops | Low | ADB over TCP as backup, auto-reconnect logic |
| Phone hardware failure | Low | Hot spare phones, automated provisioning |
| SIM plan costs at scale | Medium | Negotiate bulk MVNO deals, use eSIMs |

---

## 14. Recommendations

### If you need P2P RCS from real phone numbers:
1. **Start with a 5-phone pilot** to validate the approach
2. Build a **custom Android agent app** (accessibility service + content provider reader + WebSocket client)
3. Use **cheap Android 10+ phones** ($30-50) with **low-cost MVNO SIMs** ($5-15/mo)
4. Implement **robust RCS health monitoring** and auto-recovery
5. **Lock Google Messages version** and test updates before deploying
6. Plan for **85-90% uptime** per phone; over-provision by 20%
7. Budget **$500-800 setup** for 5 phones + server + hub, **$50-75/mo** for SIMs

### If you need B2P RCS (business messaging):
- **Use RCS Business Messaging API** instead — it's the proper tool for this
- No phone farm needed, clean API, managed by Google

### If you need P2P RCS at protocol level (advanced):
- Research **headless IMS/SIP client** approach — it's the "right" way but requires significant R&D
- You'd still need SIMs for IMS authentication
- No off-the-shelf solution exists; this is a 6-12 month development project

### Overall Assessment
The phone farm approach for P2P RCS is **feasible but fragile**. It works, but requires significant operational overhead for monitoring and maintenance. It's best suited for:
- Low-to-medium volume messaging (not high-throughput blast messaging)
- Scenarios where you need genuine phone number identities
- Use cases that tolerate 85-90% message delivery reliability
- Teams willing to invest in ongoing maintenance

For production-grade reliability at scale, a protocol-level IMS implementation would be the ideal solution, but the lack of open-source tooling makes this a major engineering effort.
