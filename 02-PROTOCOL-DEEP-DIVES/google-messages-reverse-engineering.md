# Google Messages (com.google.android.apps.messaging) & Carrier Services (com.google.android.ims) Reverse Engineering Report

## Executive Summary

Google Messages' RCS stack is a **proprietary, heavily obfuscated, closed-source implementation** that wraps Google's Jibe RCS platform. It does NOT use a standard open-source SIP stack. The registration protocol splits into two paths: **carrier-native IMS AKA** (spec-compliant) and **"Google Guest" OTT** (proprietary, requiring Play Integrity + Firebase tokens). The mautrix/gmessages bridge works by puppeting the **Google Messages web interface** (messages.google.com), NOT by implementing the RCS SIP protocol directly. Replicating the bridge without a phone requires a running Google Messages app (or its web session token). Frida can intercept SIP REGISTER and extract auth credentials mid-flight on a rooted phone, but the Jibe OTT path uses opaque tokens rather than standard SIP digest auth, making direct protocol replay infeasible. The most viable attack path is: root phone → Frida → dump full RCS registration flow → replicate the Jibe OTT HTTPS/WebSocket API in Python.

---

## 1. Google Messages' Internal RCS Stack: Proprietary SIP? Jibe SDK? Something Else?

### Architecture

Google Messages uses a **multi-layered RCS architecture**:

| Layer | Component | Description |
|-------|-----------|-------------|
| **App Layer** | `com.google.android.apps.messaging` (Google Messages) | UI, message storage, debug menus, RCS settings |
| **IMS/RCS Engine** | `com.google.android.ims` (Carrier Services) | **Primary RCS engine** — implements ImsService API, handles SIP REGISTER, provisioning, UCE |
| **Framework Layer** | Android IMS framework (`ImsService`, `SipDelegateManager`, `RcsFeature`) | System APIs for IMS single registration (Android 12+) |
| **GMS Integration** | Google Play Services (`IAsterismApiService`, `Constellation`, Firebase IID) | Phone verification, Play Integrity attestation, push notifications |
| **Transport** | Jibe Cloud (proprietary HTTPS + SIP/MSRP) | Google's RCS backend — both carrier-hosted and OTT |

### SIP Stack: Proprietary, Not Open Source

- **Carrier Services (`com.google.android.ims`)** contains the actual SIP stack implementation
- The code is **heavily obfuscated** (ProGuard/R8) — class names like `a.b.c.d.e` with no debug symbols
- It is **NOT** based on JAIN-SIP, MJSIP, or any known open-source SIP stack
- Analysis from the [Google SIP Stack security review](https://blog.hansenpartnership.com/securing-the-google-sip-stack/) confirms Android's built-in SIP stack (android.net.sip) is a separate, older implementation unrelated to the Carrier Services SIP stack
- Samsung's IMS implementation has **unstripped symbols** and is a better target for reverse engineering than Google's obfuscated code (per benwaffle in microG #2994)

### Dual Registration Mode

Google Messages supports two registration modes (visible in logcat as `RcsEngineImpl[DUAL_REG]`):

1. **Carrier IMS path** — Uses the device's ImsService for standard SIP REGISTER with IMS AKA authentication
2. **Jibe OTT path** — Direct HTTPS/WebSocket connection to Google's Jibe servers, bypassing carrier IMS entirely

When Carrier Services is unavailable, Google Messages falls back to its **built-in Jibe RCS client** (`BugleRcsEngine`).

### Key Internal Components (from decompilation attempts & logcat analysis)

| Component | Role | Identifiable From |
|-----------|------|-------------------|
| `BugleRcsEngine` / `RcsEngineImpl` | RCS engine lifecycle management | Logcat tags |
| `RcsProvisioningManager` | RCS provisioning, SIM ID mapping, phone number retrieval | Logcat, decompiled class names |
| `BugleSelfIdentity` | Self-identity / RCS availability checks | Logcat |
| `ImsService` (in Carrier Services) | Full IMS stack: SIP REGISTER, MmTelFeature, RcsFeature | Android framework binding |
| `IRcsService` AIDL | RCS service interface Google Messages expects from GMS | microG reverse engineering |
| `IAsterismApiService` AIDL | Play Integrity attestation for RCS | microG #2994 |
| `Constellation` API | Phone number verification (EAP-AKA-like flow) | microG #2994 |

---

## 2. Where RCS State/Tokens Are Stored on Disk (Root Required)

### Google Messages (`com.google.android.apps.messaging`)

| Path | Contents | Value |
|------|----------|-------|
| `/data/data/com.google.android.apps.messaging/shared_prefs/` | SharedPreferences XML — **likely contains**: RCS feature flags, registration status, Jibe server URLs, auth tokens, phone number verification state | **HIGH** |
| `/data/data/com.google.android.apps.messaging/databases/` | SQLite databases — RCS message store, chat participants, possibly registration state | **MEDIUM** |
| `/data/data/com.google.android.apps.messaging/files/` | Cached data, possibly provisioning XML | **LOW-MEDIUM** |
| `/data/user_de/0/com.google.android.apps.messaging/` | Device-encrypted variant (accessible after first unlock) | Same as above |

### Carrier Services (`com.google.android.ims`) — The Core RCS Engine

| Path | Contents | Value |
|------|----------|-------|
| `/data/data/com.google.android.ims/shared_prefs/` | **HIGH-VALUE TARGET**: likely contains SIP registration state, P-CSCF addresses, IMS credentials/tokens, provisioning XML fragments, auth realm, SIP URI (IMPI/IMPU), registration expiry | **CRITICAL** |
| `/data/data/com.google.android.ims/databases/` | Internal databases for IMS state tracking | **HIGH** |
| `/data/data/com.google.android.ims/files/` | Provisioning data, possibly ACS response XML | **MEDIUM** |

### Android Telephony Framework (accessible via `dumpsys` without root)

| Data | Method | Feasibility |
|------|--------|-------------|
| P-CSCF addresses | `adb shell dumpsys telephony registry \| grep -i pcscf` | ✅ Easy |
| IMS registration state | `adb shell dumpsys ims` | ✅ Easy |
| ISIM/USIM data (IMPI, IMPU) | `adb shell dumpsys isub` | ✅ Easy |
| Carrier config (RCS/IMS settings) | `adb shell dumpsys carrier_config` | ✅ Easy |
| SIM AKA authentication oracle | `TelephonyManager.getIccAuthentication()` via ADB (Android 10+) | ✅ Most powerful non-root capability |

### Key Observations

- **RCS registration credentials are NOT stored in plaintext** in SharedPreferences in most cases
- Carrier Services holds registration state **in memory and in obfuscated/persisted form**
- The SIP `Security-Server` header parameters (digest realm, nonce algorithm) are **transient**
- For the Jibe OTT path, tokens are likely stored as **opaque encrypted blobs** tied to the device's hardware keystore

---

## 3. How to Capture RCS SIP Traffic

### Method A: tcpdump (requires root) — Carrier IMS Path Only

```bash
# On rooted Android device:
tcpdump -i any -s 0 -w /sdcard/rcs_capture.pcap port 5060 or port 5061

# Filter by P-CSCF address (obtain from dumpsys):
tcpdump -i any -s 0 -w /sdcard/rcs_capture.pcap host <P-CSCF-IP>
```

**Limitation**: For Google Jibe RCS (OTT path), traffic goes over **HTTPS to Google's servers**, not raw SIP to a P-CSCF. tcpdump will show encrypted TLS streams only.

### Method B: PCAPdroid (no root)

- GitHub: `emanuele-f/PCAPdroid` — VPN-based network capture
- Can capture and display SIP/HTTP traffic in real-time
- Can export as PCAP for Wireshark analysis
- **Cannot decrypt TLS** by default (see mitmproxy integration below)

### Method C: Wireshark + Android Hotspot

- Configure Android as Wi-Fi hotspot, connect laptop running Wireshark
- Wireshark's SIP dissector can parse SIP REGISTER, 401, 200 OK
- **Only works for unencrypted SIP** — modern IMS uses TLS/IPSec

### Method D: adb logcat (radio + debug buffer) — The Most Practical Approach

```bash
# Radio logs — IMS registration events, SIP error codes
adb logcat -b radio | grep -iE "SIP|IMS|REGISTER|P-CSCF|AKA|401|Unauthorized"

# Carrier Services debug logging
adb logcat -s "ImsService" "ImsResolver" "SipDelegate" "RcsService" "BugleRcsEngine"

# Google Messages debug logging (after enabling debug menu)
adb logcat -s "BugleRcsEngine" "RcsProvisioningManager" "BugleSelfIdentity"
```

### Method E: Frida + TLS Key Extraction (see Section 8)

---

## 4. How to Enable Verbose RCS Debug Logging on Android

### Google Messages Debug Menu

1. Open Google Messages
2. Type `*xyzzy*` (the cheat code from Road Rash) in the **search field**
3. This adds two additional items to the Settings menu and debug options to the dropdown menu
4. Source: [TestingCatalog](https://www.testingcatalog.com/how-to-enable-debug-menu-in-google-messages-for-android/)

### Debug Menu Features

- Enable/disable RCS debug logging
- View RCS connection state and provisioning details
- Access internal flags and settings
- Trigger manual RCS re-registration

### Full Debug Logging Setup (per Google's own RCS Business Messaging docs)

1. Enable Developer Options: Settings → About Phone → tap Build Number 7 times
2. Enable USB Debugging
3. Maximize logger buffer size: Settings → Developer Options → Logger buffer sizes → set to maximum (16 MB)
4. Force stop Messages, then start logging:
```bash
adb logcat -b radio -b main -b system -v threadtime > rcs-debug.log
```
5. Reproduce the RCS registration issue
6. Generate bug report: `adb bugreport rcs-bugreport.zip`

### Radio Buffer Logs

Radio buffer logs (`-b radio`) frequently show:
- IMS registration state transitions
- SIP error codes (401, 403, 408, 500)
- Authentication challenge details
- P-CSCF connection attempts

### Key Logcat Filter Tags

| Tag | What It Shows |
|-----|---------------|
| `ImsService` | IMS registration state, feature creation |
| `ImsResolver` | ImsService binding/discovery |
| `SipDelegate` | SIP delegate creation, message routing |
| `RcsService` | RCS feature availability |
| `BugleRcsEngine` / `RcsEngineImpl` | Google Messages RCS engine lifecycle |
| `RcsProvisioningManager` | Provisioning status, SIM ID mapping |
| `BugleSelfIdentity` | RCS availability, identity verification |
| `DUAL_REG` | Dual registration mode transitions |

---

## 5. Is the Jibe Protocol Standard SIP or Proprietary?

### Answer: **Both**, depending on the registration path

### Carrier-Jibe RCS (Standard SIP)

- **Standard SIP REGISTER** per GSMA RCS Universal Profile (RCC.07)
- Authentication via **IMS AKA** (using SIM credentials) or SIP digest auth
- Uses SIP over TCP/TLS to the carrier's IMS core (Jibe-hosted)
- **Fully spec-compliant** — Apple's iOS RCS implementation uses this same path
- Feature tags follow GSMA standards (`+g.3gpp.icsi-ref`, `+g.3gpp.iari-ref`)

### Jibe "Google Guest" OTT RCS (Proprietary)

- The SIP REGISTER itself may follow standard format, but the **authentication mechanism is proprietary**
- The `Authorization` header contains an **opaque token** derived from Google's proprietary phone verification and Play Integrity attestation flow
- This is **NOT** standard IMS AKA or SIP digest auth
- The SIP domain used is Google's own (not a carrier IMS domain)
- The token is generated via:
  1. **Phone number verification** — silent SMS via GMS `Constellation` service
  2. **Play Integrity attestation** — device integrity check via `IAsterismApiService`
  3. **Firebase Instance ID token** — for push notification registration
  4. The composite token is sent as `gmscore_instance_id_token` header (protobuf `CompositeToken` with `iid_token` + `pia_token`)

### Token Structure (from benwaffle's analysis in microG #2994)

```protobuf
message CompositeToken {
  string iid_token = 1;  // Firebase Instance ID token
  string pia_token = 2;  // Play Integrity Attestation token
}
```

Sent as: `gmscore_instance_id_token: base64(CompositeToken.toByteArray(), NO_WRAP | URL_SAFE)`

### Key Protocol Differences

| Aspect | Carrier-Jibe | Jibe OTT ("Google Guest") |
|--------|-------------|---------------------------|
| SIP REGISTER | Standard (RCC.07) | Non-standard auth in standard SIP frame |
| Authentication | IMS AKA (SIM) | Proprietary opaque token (Play Integrity + Firebase IID) |
| Transport | SIP/TCP/TLS to P-CSCF | HTTPS/WebSocket to Jibe cloud |
| Server | Carrier IMS core (Jibe-hosted) | Google's proprietary Jibe servers |
| Third-party access | ✅ Spec-compliant clients can connect | ❌ Google explicitly refuses access |
| iOS support | ✅ (Apple uses this path) | ❌ (Only Google Messages uses this) |

---

## 6. The mautrix/gmessages Bridge: How It Works

### Overview

[mautrix/gmessages](https://github.com/mautrix/gmessages) is a **Matrix-Google Messages puppeting bridge** written in Go. It bridges Google Messages (both SMS and RCS) to Matrix.

### How It Works: Web Interface Puppeting

**The bridge does NOT implement the RCS SIP protocol directly.** Instead, it works by:

1. **Connecting to Google Messages' web interface** (messages.google.com/web)
2. The web interface uses a **proprietary WebSocket-based protocol** (not SIP/MSRP)
3. The bridge uses a Go library called **`libgm`** that implements this web protocol
4. Authentication is via **QR code scanning** — the same way you pair messages.google.com/web with your phone
5. The bridge acts as a "puppet" — it controls your Google Messages account through the web interface

### libgm: The Core Library

- Located in the bridge at `libgm/` directory
- Contains a **manualdecrypt** tool for reverse-engineering the protocol
- Implements the binary message format used by the Google Messages web WebSocket API
- Handles authentication, message sending/receiving, media upload/download
- The protocol is **binary and proprietary** — not based on any standard

### Authentication Flow

1. User scans QR code from messages.google.com/web
2. Bridge receives a session token (similar to a web browser session)
3. Bridge maintains a persistent WebSocket connection to Google's servers
4. All messages (SMS and RCS) are routed through this WebSocket
5. The phone must remain powered on and connected (it acts as the "real" RCS client)

### Key Limitation: Phone Dependency

- **The phone MUST remain active and connected to the internet** — the bridge is just a puppet
- If the phone's RCS registration drops, the bridge loses RCS message capability
- The bridge does NOT independently register with Jibe or any RCS server
- It piggybacks on the phone's existing RCS registration

### Beeper's Implementation

Beeper (the commercial product) uses the same mautrix/gmessages bridge. Per Beeper's blog post on "How Beeper Android Works":
- Beeper's Google Messages integration uses the **web interface bridge** approach
- It connects to the web version of Google Messages, similar to how WhatsApp Web works
- This is why Beeper requires the Google Messages app to remain installed on the phone

---

## 7. Can We Replicate the Bridge's Approach Without an Actual Phone?

### Short Answer: **No, not directly**

The mautrix/gmessages bridge requires:
1. An active Google Messages installation on an Android phone
2. The phone to be powered on and connected to the internet
3. A QR code pairing step (which requires a running Google Messages app)

### Why It Can't Work Without a Phone

- The web interface (messages.google.com/web) is a **companion** to the phone app, not a standalone client
- The phone does the actual RCS registration (SIP REGISTER to Jibe/IMS)
- The web interface just mirrors what the phone does via a proprietary WebSocket protocol
- If the phone disconnects, the web session also breaks

### What Would Be Needed for a Phone-Free Solution

To build a standalone RCS client, you would need to:
1. **Reverse-engineer the Jibe OTT registration protocol** (proprietary token-based auth)
2. **Implement the Jibe SIP/MSRP stack** (or whatever transport Jibe actually uses for message delivery)
3. **Handle Play Integrity attestation** without an Android device
4. **Implement Firebase Cloud Messaging** for push notifications
5. **Manage the proprietary phone verification** (SMS-based) flow

This is essentially what **Beeper Mini** attempted for iMessage, and Google responded aggressively. Google has explicitly stated they will **not** open access to the Jibe OTT backend for third-party clients.

---

## 8. Frida Hooks to Intercept SIP REGISTER and Extract Auth Credentials

### Attaching to Carrier Services

```javascript
// Attach to the Carrier Services process (the actual IMS/RCS engine)
Java.perform(function() {
    // Hook TelephonyManager.getIccAuthentication() — the SIM AKA oracle
    var TelephonyManager = Java.use("android.telephony.TelephonyManager");
    TelephonyManager.getIccAuthentication.overload('int', 'int', 'java.lang.String')
    .implementation = function(appType, authType, data) {
        var result = this.getIccAuthentication(appType, authType, data);
        console.log("[+] getIccAuthentication called");
        console.log("    appType: " + appType);
        console.log("    authType: " + authType);
        console.log("    data (RAND/AUTN): " + data);
        console.log("    result (RES/IK/CK): " + result);
        return result;
    };
});
```

### Hooking SIP Registration State Changes

```javascript
Java.perform(function() {
    // Hook ImsService registration callbacks
    var ImsRegistrationCallback = Java.use("android.telephony.ims.ImsMmTelManager$RegistrationCallback");
    // Note: actual class names in Carrier Services are obfuscated
    
    // Hook ProvisioningManager for RCS provisioning status
    var ProvisioningManager = Java.use("android.telephony.ims.ProvisioningManager");
});
```

### Hooking the 401 Unauthorized Challenge Processing

Since Carrier Services is obfuscated, you need to find the SIP auth processing classes by:
1. **String search**: Look for "REGISTER", "Authorization", "WWW-Authenticate", "AKAv1-MD5" in the APK
2. **Method profiling**: Use Frida's `Stalker` to trace code execution during registration
3. **Class enumeration**: List all loaded classes in the `com.google.android.ims` process during registration

```javascript
Java.perform(function() {
    // Enumerate all classes related to SIP/IMS in Carrier Services
    Java.enumerateLoadedClasses({
        onMatch: function(className) {
            if (className.toLowerCase().indexOf("sip") !== -1 || 
                className.toLowerCase().indexOf("register") !== -1 ||
                className.toLowerCase().indexOf("auth") !== -1) {
                console.log("[*] Found class: " + className);
            }
        },
        onComplete: function() {
            console.log("[*] Class enumeration complete");
        }
    });
});
```

### Hooking OkHttp for HTTPS Traffic Interception

```javascript
Java.perform(function() {
    // Hook OkHttp3 for all HTTP traffic from Carrier Services
    var OkHttpClient = Java.use("okhttp3.OkHttpClient");
    var Request = Java.use("okhttp3.Request");
    var RealCall = Java.use("okhttp3.internal.connection.RealCall");
    
    RealCall.execute.implementation = function() {
        var request = this.request();
        console.log("[HTTP] " + request.method() + " " + request.url().toString());
        var headers = request.headers();
        for (var i = 0; i < headers.size(); i++) {
            console.log("  " + headers.name(i) + ": " + headers.value(i));
        }
        return this.execute();
    };
});
```

### Hooking the gmscore_instance_id_token Header

```javascript
Java.perform(function() {
    // Hook the protobuf CompositeToken construction
    // Search for classes that build the gmscore_instance_id_token header
    Java.enumerateLoadedClasses({
        onMatch: function(className) {
            if (className.indexOf("Asterism") !== -1 || 
                className.indexOf("asterism") !== -1 ||
                className.indexOf("CompositeToken") !== -1) {
                console.log("[*] Asterism class: " + className);
            }
        },
        onComplete: function() {}
    });
});
```

### Critical Challenge: Frida Detection

- **Google Play Integrity** detects Frida (rooted device, debugging enabled)
- Magisk modules like "Play Integrity Fix" + "TrickyStore" are needed to pass device integrity checks
- This is a **cat-and-mouse game** — Google regularly updates their detection
- LSPosed/Xposed may be less detectable than Frida for some checks

---

## 9. Whether We Can MITM the TLS Connection to Jibe Cloud

### Assessment: **Extremely difficult but theoretically possible**

### Method 1: mitmproxy + System CA Injection (root required)

1. Install mitmproxy on a computer
2. Install mitmproxy's CA certificate as a **system-trusted cert** on the Android device:
   ```bash
   # Root required (Android 13+ requires additional steps)
   adb push mitmproxy-ca-cert.cer /system/etc/security/cacerts/
   ```
3. On **Android 14+**, certificate trust changes require additional work:
   - Use Magisk module `Move Certificates` to inject CAs
   - Or use `adb root` + `mount -o rw,remount /system`
4. Configure Wi-Fi proxy to point to mitmproxy
5. Watch for HTTPS requests to Jibe servers

**Key challenge**: Google's apps likely use **certificate pinning** (checking specific certificate fingerprints). mitmproxy alone won't work if pins are enforced.

### Method 2: Frida SSL Unpinning

```javascript
// Universal SSL unpinning for Android
Java.perform(function() {
    // Hook SSLContext to bypass certificate verification
    var SSLContext = Java.use("javax.net.ssl.SSLContext");
    
    // Hook OkHttp CertificatePinner
    try {
        var CertificatePinner = Java.use("okhttp3.CertificatePinner");
        CertificatePinner.check.overload('java.lang.String', 'java.util.List')
        .implementation = function(hostname, peerCertificates) {
            console.log("[SSL] Certificate pin check bypassed for: " + hostname);
            // Don't actually check — just return
        };
    } catch(e) {
        console.log("[SSL] CertificatePinner not found (different OkHttp version)");
    }
    
    // Hook TrustManager
    var X509TrustManager = Java.use("javax.net.ssl.X509TrustManager");
    // ... implement custom trust manager that accepts all certs
});
```

### Method 3: PCAPdroid + mitmproxy Integration (no root, limited)

- PCAPdroid supports mitmproxy integration for TLS decryption on non-rooted devices
- Uses its built-in mitmproxy addon
- Avoids needing to install system CAs manually
- **Limitation**: May not work with certificate-pinned apps

### Method 4: Extract TLS Keys via Frida + Decrypt in Wireshark

Based on [pentest-tools.com research](https://pentest-tools.com/blog/extract-tls-secrets):

1. Use Frida to hook `SSL_write` / `SSL_read` in the app's process
2. Extract TLS session keys (pre-master secrets)
3. Export keys in NSS Key Log format
4. Load keys into Wireshark (Edit → Preferences → Protocols → TLS → Pre-Master-Secret log file)
5. Wireshark can now decrypt all TLS traffic from the capture

### What You'll See After Decryption

For the **Jibe OTT path**, expect:
- HTTPS requests to `jibe.google.com` or similar Google domains
- Protobuf-encoded request/response bodies
- Bearer tokens or opaque auth tokens in headers
- WebSocket connections for message delivery

For the **carrier IMS path**, expect:
- SIP REGISTER to the carrier's P-CSCF (or Jibe-hosted P-CSCF)
- SIP 401 Unauthorized with RAND/AUTN challenge
- SIP REGISTER with AKAv1-MD5 Authorization header
- SIP 200 OK establishing registration
- SIP MESSAGE for chat, MSRP for file transfer

---

## 10. Complete Attack Plan: Root Phone → Frida → Dump Full RCS Registration Flow → Replicate in Python

### Phase 1: Preparation (1-2 days)

1. **Obtain a rooted Android device** (Pixel with Magisk recommended)
2. **Install prerequisite tools**:
   - Magisk + Play Integrity Fix module + TrickyStore
   - Frida Server (`frida-server` matching device architecture)
   - mitmproxy on a laptop
   - Wireshark on a laptop
   - adb + fastboot
   - JADX (for APK decompilation on a PC)
3. **Install Google Messages + Carrier Services** from Play Store
4. **Verify RCS works normally** before instrumenting
5. **Enable debug menu** in Google Messages (type `*xyzzy*` in search)
6. **Maximize logcat buffer** and set up persistent logging

### Phase 2: Static Analysis (2-3 days)

1. **Download APKs**:
   ```bash
   # From APKMirror or device pull
   adb pull /data/app/com.google.android.apps.messaging/ /tmp/messaging-apk/
   adb pull /data/app/com.google.android.ims/ /tmp/carrier-services-apk/
   ```

2. **Decompile with JADX**:
   ```bash
   jadx -d /tmp/messaging-decompiled/ messaging.apk
   jadx -d /tmp/carrier-services-decompiled/ carrier-services.apk
   ```

3. **String analysis** — Search for:
   - SIP-related: `"REGISTER"`, `"SIP/2.0"`, `"Authorization"`, `"AKAv1-MD5"`, `"WWW-Authenticate"`, `"jibe"`
   - HTTPS endpoints: `"jibe.google.com"`, `"rcs-acs"`, `"gmscore_instance_id_token"`, `"asterism"`
   - Auth tokens: `"Bearer"`, `"pia_token"`, `"iid_token"`, `"CompositeToken"`
   - Protobuf definitions: Search for `.proto` files or protobuf field names

4. **Shared Preferences analysis** (root):
   ```bash
   adb pull /data/data/com.google.android.ims/shared_prefs/ /tmp/ims-prefs/
   adb pull /data/data/com.google.android.apps.messaging/shared_prefs/ /tmp/messaging-prefs/
   # Examine XML files for RCS tokens, server URLs, registration state
   ```

5. **Database analysis** (root):
   ```bash
   adb pull /data/data/com.google.android.ims/databases/ /tmp/ims-db/
   sqlite3 /tmp/ims-db/*.db ".tables"
   sqlite3 /tmp/ims-db/*.db ".schema"
   ```

### Phase 3: Dynamic Instrumentation (3-5 days)

1. **Start Frida server** on the device:
   ```bash
   adb shell su -c ./frida-server &
   ```

2. **Capture baseline**: Force RCS re-registration and capture logcat:
   ```bash
   adb logcat -b radio -b main -b system -v threadtime > /tmp/rcs-baseline.log
   # Force stop Messages, then reopen to trigger registration
   adb shell am force-stop com.google.android.apps.messaging
   ```

3. **Attach Frida to Carrier Services**:
   ```bash
   frida -U com.google.android.ims -l rcs-hooks.js
   ```

4. **Hook key APIs** (in order of priority):
   a. `TelephonyManager.getIccAuthentication()` — SIM AKA oracle
   b. OkHttp request/response — HTTPS traffic to Jibe
   c. SSLContext / CertificatePinner — TLS unpinning
   d. SharedPreferences write operations — capture stored tokens
   e. Protobuf serialization — capture `CompositeToken` construction
   f. SIP message construction (if applicable — class names will be obfuscated)

5. **TLS key extraction**: Hook `SSL_*` functions to extract pre-master secrets, feed to Wireshark

6. **Network capture**: Run tcpdump simultaneously:
   ```bash
   adb shell su -c tcpdump -i any -s 0 -w /sdcard/rcs-full.pcap
   ```

7. **mitmproxy capture**: Route traffic through mitmproxy with Frida SSL unpinning

### Phase 4: Protocol Analysis (3-5 days)

1. **Analyze captured SIP traffic** (carrier IMS path):
   - Extract SIP REGISTER / 401 / 200 OK exchange
   - Document AKAv1-MD5 digest auth parameters
   - Map feature tags and contact headers
   - Identify registration expiry timer

2. **Analyze captured HTTPS traffic** (Jibe OTT path):
   - Identify Jibe server endpoints (URLs, methods, headers)
   - Decode protobuf request/response bodies
   - Extract token structure and lifecycle
   - Document the phone verification flow
   - Map WebSocket message protocol (if applicable)

3. **Analyze stored credentials**:
   - Document all SharedPreferences keys related to RCS
   - Extract and decode any encrypted token blobs
   - Map token refresh/renewal patterns

4. **Map the complete registration flow**:
   ```
   Step 1: Google Messages starts → detects carrier config
   Step 2: Determines registration path (carrier IMS vs Jibe OTT)
   Step 3a (carrier): SIP REGISTER → 401 → AKAv1-MD5 auth → 200 OK
   Step 3b (Jibe OTT): HTTPS to Jibe provisioning → phone verification → token exchange → WebSocket connect
   Step 4: FCM registration for push notifications
   Step 5: RCS "Connected" state
   ```

### Phase 5: Python Replication (5-10 days)

1. **Implement the Jibe OTT client** (most practical for our use case):
   - HTTP client for Jibe provisioning endpoints
   - Protobuf message serialization/deserialization
   - WebSocket client for real-time message delivery
   - Token management (refresh, storage)
   - FCM integration (or alternative notification mechanism)

2. **OR implement the carrier IMS client** (if targeting a specific carrier):
   - SIP stack (use `pjsua2` or `baresip` Python bindings)
   - IMS AKA authentication (use SIM as oracle via `SimServerAndroid`)
   - MSRP client for file transfer
   - UCE (capability exchange) client

3. **Handle Play Integrity** (hardest part):
   - Option A: Use a real Android device as a "token generator" (run a thin helper app)
   - Option B: Spoof Play Integrity responses (requires leaked keybox — cat-and-mouse)
   - Option C: Find a carrier that doesn't require Play Integrity for RCS

### Phase 6: Hardening & Maintenance (ongoing)

- Google updates the protocol regularly — expect breaking changes
- Play Integrity detection evolves — need continuous bypass updates
- Token formats and endpoints may change between app versions
- Monitor microG issue #2994 for community progress ($14,999 bounty)

---

## 11. Existing Reverse Engineering Work & Community Efforts

### Active Projects

| Project | Status | What They've Found |
|---------|--------|--------------------|
| **microG GmsCore** (#2994, $14,999 bounty) | Active | Identified `CompositeToken` protobuf, `IAsterismApiService`, `Constellation` API, confirmed Jibe OTT bypasses carrier IMS |
| **mautrix/gmessages** | Working | Web interface puppeting bridge (not direct RCS protocol) |
| **zwyuan/rcs-fi-client** | POC | Google Fi RCS client POC — limited details |
| **phhusson's Python script** | Working | Retrieves SIP config, tokens, and full RCS config from carrier ACS servers |
| **benwaffle's analysis** | Key findings | Samsung also uses Play Integrity; Samsung IMS has unstripped symbols (better RE target) |
| **iOS RCS captures** | Detailed | Full RCC.14-compliant flow documented: `client_certificate_upload`, `client_authenticity_support`, EAP-AKA `as_temp_token` |
| **GrapheneOS community** | Partially working | RCS works on many carriers with sandboxed Play Services, fails on T-Mobile/AT&T due to privileged access |

### Key Community Findings

1. **Google's Jibe platform bypasses carrier IMS entirely** for the OTT path (confirmed by unpluggederan in microG #2994)
2. **Carrier Services (`com.google.android.ims`) is Google's proprietary ImsService** — it implements the full ImsService API including MmTelFeature and RcsFeature
3. **Play Integrity attestation is required** for the Jibe OTT path — this is the primary blocker for microG
4. **Samsung Messages also uses Play Integrity** — the `gmscore_instance_id_token` header with `CompositeToken` protobuf is used by both Google and Samsung
5. **The ACS provisioning flow follows GSMA RCC.14** — but with vendor-specific extensions for client certificate upload and client authenticity
6. **iOS uses `eas3.msg.t-mobile.com`** while Google Messages uses `ts43.eas3.msg.t-mobile.com` — same carrier, different endpoints
7. **RCS hubbing between Jibe and non-Jibe carriers has largely died off** — the CCMI in North America was killed
8. **phhusson confirmed**: "Google Messages acts as a RCS client when your operator supports RCS, and goes to Google's proprietary network otherwise"
9. **nift4 confirmed**: "Google has stated they do not wish to open access to that proprietary backend for third party apps"
10. **Google's RCS works without strong device integrity** on some carriers — GrapheneOS users have reported success with just basic integrity

### Key Blockers Identified by Community

1. **Phone number verification**: microG doesn't fully implement the GMS APIs Google Messages depends on for phone number verification
2. **Carrier Services integration**: Even with the RCS service stub implemented, the actual Jibe protocol communication needs to work
3. **Play Integrity**: Required for Jibe OTT path; requires device attestation that microG/graphene can't provide natively
4. **No RCS hubbing**: Can't route between Google's proprietary network and independent carrier RCS networks

---

## 12. Jibe Documentation Access

- **docs.jibemobile.com** — Requires approved partner domain account (login-gated)
- **jibe.google.com** — Marketing page only
- **GSMA PathFinder API** — Used by Jibe Hub for number-to-server discovery (partner access only)
- The Jibe architecture diagram from the [white paper](https://docs.jibemobile.com/static/images/rcs-architecture.png) shows the hub interconnection model

---

## 13. Summary of Attack Surfaces and Feasibility

| Attack Surface | Feasibility | Root Required | What You Get |
|----------------|------------|---------------|--------------|
| Extract shared_prefs/databases | ✅ Easy | Yes | RCS tokens, server URLs, registration state |
| `dumpsys` telephony/IMS data | ✅ Easy | No (ADB) | P-CSCF, IMS state, carrier config |
| `TelephonyManager.getIccAuthentication()` | ✅ Easy | No (ADB, Android 10+) | SIM AKA oracle — can compute auth responses |
| tcpdump SIP capture | ⚠️ Partial | Yes | Only carrier IMS path; Jibe OTT is encrypted |
| adb logcat debug logging | ✅ Easy | No (ADB) | Registration events, error codes, provisioning state |
| Frida hook on Carrier Services | ⚠️ Complex | Yes | Full SIP/HTTPS traffic, auth credentials, tokens |
| mitmproxy TLS interception | ⚠️ Complex | Yes | HTTPS request/response bodies (with SSL unpinning) |
| Frida TLS key extraction → Wireshark | ⚠️ Complex | Yes | Decrypted TLS traffic in Wireshark |
| Replicate mautrix/gmessages bridge | ✅ Possible | No (but needs phone) | Web interface puppeting (not direct RCS protocol) |
| Build standalone Jibe OTT client | ❌ Very Hard | N/A | Requires reverse-engineering proprietary protocol + Play Integrity bypass |
| Build carrier IMS RCS client | ⚠️ Hard | N/A | Spec-compliant but needs SIM + carrier cooperation + AKA |

---

## 14. Recommended Priority Order for Our Project

1. **HIGH PRIORITY**: Root phone → extract shared_prefs + databases from both `com.google.android.ims` and `com.google.android.apps.messaging` — this gives us the current token/registration state
2. **HIGH PRIORITY**: Frida hook on `TelephonyManager.getIccAuthentication()` + OkHttp traffic — this captures the live auth flow
3. **MEDIUM PRIORITY**: mitmproxy + Frida SSL unpinning — capture Jibe OTT HTTPS protocol
4. **MEDIUM PRIORITY**: Static analysis of decompiled Carrier Services APK — identify class names for SIP stack
5. **LOW PRIORITY**: Attempt to replicate mautrix/gmessages approach for initial testing (phone-dependent but quick to prototype)
6. **FUTURE**: Build Python Jibe OTT client once protocol is fully reverse-engineered

---

## Sources & References

- **microG GmsCore Issue #2994**: https://github.com/microg/GmsCore/issues/2994 ($14,999 bounty, extensive community research)
- **microG GmsCore Issue #2063**: https://github.com/microg/GmsCore/issues/2063 (original RCS on microG discussion)
- **mautrix/gmessages**: https://github.com/mautrix/gmessages (Matrix-Google Messages bridge)
- **zwyuan/rcs-fi-client**: https://github.com/zwyuan/rcs-fi-client (Google Fi RCS POC)
- **AOSP IMS Single Registration**: https://source.android.com/docs/core/connect/ims-single-registration
- **AOSP ImsService**: https://android.googlesource.com/platform/frameworks/base/+/master/telephony/java/android/telephony/ims/ImsService.java
- **Jibe Platform docs**: https://docs.jibemobile.com/ (partner login required)
- **Beeper Blog - How Beeper Android Works**: https://blog.beeper.com/2024/04/09/how-beeper-android-works/
- **Google Messages Debug Menu**: https://www.testingcatalog.com/how-to-enable-debug-menu-in-google-messages-for-android/
- **XDA - Hidden RCS API**: https://www.xda-developers.com/google-messages-rcs-api-third-party-apps/
- **Frida TLS Key Extraction**: https://pentest-tools.com/blog/extract-tls-secrets
- **Securing the Google SIP Stack**: https://blog.hansenpartnership.com/securing-the-google-sip-stack/
- **GrapheneOS RCS Discussion**: https://discuss.grapheneos.org/d/1353-using-rcs-with-google-messages-on-grapheneos
- **AOSP Service Entitlement Library**: https://cs.android.com/android/platform/superproject/+/android-latest-release:frameworks/libs/service_entitlement/
- **zhuowei/SimServerAndroid**: https://github.com/zhuowei/SimServerAndroid (SIM AKA oracle)
- **Google Issue Tracker #408010447**: Google's refusal to open Jibe OTT to third-party clients
- **Google RCS for Web**: https://messages.google.com/web/authentication
