# RCS Credential Extraction from Android — Research Report

## Executive Summary

Extracting RCS registration credentials from a live Android phone for reuse in a headless client is technically feasible but highly constrained. Google's RCS implementation (via Jibe) uses a proprietary OTT (over-the-top) SIP/IMS stack that does not expose credentials through standard Android APIs. The carrier-native IMS path (where SIP credentials derive from the SIM's ISIM/USIM) is more accessible but harder to repurpose because authentication is bound to the SIM card's K key via IMS AKA. This report covers all known attack surfaces, storage locations, interception methods, and practical feasibility.

---

## 1. Where Google Messages Stores RCS Config/Provisioning Data on Disk (Root Required)

### Key Paths (root required)

| Path | Contents |
|------|----------|
| `/data/data/com.google.android.apps.messaging/` | Google Messages app-private data |
| `/data/data/com.google.android.apps.messaging/databases/` | SQLite databases including RCS message store, chat participants, and potentially registration state |
| `/data/data/com.google.android.apps.messaging/shared_prefs/` | SharedPreferences XML files — may contain RCS feature flags, registration status, Jibe server URLs, auth tokens |
| `/data/data/com.google.android.apps.messaging/files/` | Miscellaneous cached data |
| `/data/user_de/0/com.google.android.apps.messaging/` | Device-encrypted variant of the above (accessible after first unlock) |

### Carrier Services (com.google.android.ims) — The Core RCS Engine

| Path | Contents |
|------|----------|
| `/data/data/com.google.android.ims/` | Carrier Services — the IMS stack that Google Messages delegates to |
| `/data/data/com.google.android.ims/shared_prefs/` | **High-value target**: likely contains SIP registration state, P-CSCF addresses, IMS credentials/tokens, provisioning XML fragments |
| `/data/data/com.google.android.ims/databases/` | Internal databases for IMS state tracking |
| `/data/data/com.google.android.ims/files/` | Provisioning data, possibly ACS response XML |

### Key Observations
- **RCS messages themselves** are stored in the Google Messages SQLite database under the standard `content://mms-sms/` or a proprietary RCS content provider. The `DatabaseHelper.java` from AOSP's messaging app shows the schema.
- **Registration credentials** are not stored in plaintext in SharedPreferences in most cases. The Carrier Services IMS stack holds registration state in memory and in obfuscated/persisted form. The SIP `Security-Server` header parameters (digest realm, nonce algorithm) are transient.
- **Google Messages RCS is NOT carrier-IMS-based** for most users. Google operates Jibe as an OTT RCS hub, which uses a proprietary SIP/MSRP stack within Carrier Services that connects to Google's cloud infrastructure rather than the carrier's IMS core. This means the traditional IMS AKA path may not apply.

---

## 2. Where Carrier Services Stores SIP Credentials and Registration State

### Architecture (Android 12+ IMS Single Registration)

Starting with Android 12, the platform supports an **IMS Single Registration** model:
- The `ImsService` (implemented by Carrier Services: `com.google.android.ims`) manages a single SIP registration to the carrier's IMS core.
- RCS applications (like Google Messages) request a `SipDelegate` from the framework's `SipDelegateManager` to send/receive SIP messages over the already-established registration.
- The `ImsService` holds the SIP registration state, including the registration timer, contact URI, and associated feature tags (`+g.3gpp.icsi-ref`, `+g.3gpp.iari-ref`, etc.).

### Storage Locations

| Component | Where | What's Stored |
|-----------|-------|---------------|
| Carrier Services IMS stack | `/data/data/com.google.android.ims/shared_prefs/` | Likely: P-CSCF address, IMS APN config, auth realm, SIP URI (IMPI/IMPU), registration expiry, possibly session tokens |
| Android Telephony Framework | In-memory + `dumpsys` output | P-CSCF addresses (obtainable via `dumpsys telephony.registry` → `PcscfAddresses`), IMS registration state |
| ISIM/USIM on SIM card | SIM filesystem (EF_IMS, EF_DOMAIN, EF_PCSCF) | IMPI, IMPU, P-CSCF addresses, DNS addresses — accessible via `adb shell dumpsys isub` or TelephonyManager APIs |
| CarrierConfig | `/vendor/etc/` or CarrierConfigManager defaults | IMS feature flags, VoLTE/VoWiFi/RCS provisioning URLs, ePDG addresses |

### How to Extract via dumpsys (no root, but requires shell/ADB)

```bash
# P-CSCF addresses — the SIP server the phone registers to
adb shell dumpsys telephony registry | grep -i pcscf

# IMS subscription info (IMPI, IMPU from ISIM)
adb shell dumpsys isub

# IMS registration state
adb shell dumpsys ims

# Carrier configuration (RCS/IMS settings)
adb shell dumpsys carrier_config

# Full telephony state
adb shell dumpsys phone
```

**Critical insight from zhuowei's VoWiFi research**: The P-CSCF address is typically a private IPv6 address (e.g., `fd00:1234:5678:1234::1`) allocated over the carrier's IMS APN, making it only reachable from the device's cellular data connection or Wi-Fi tethering from the same device.

---

## 3. How to Capture SIP REGISTER Traffic on Android

### Method A: tcpdump (requires root)

```bash
# On the Android device (root shell):
tcpdump -i any -s 0 -w /sdcard/rcs_capture.pcap port 5060 or port 5061

# For IMS traffic over the ims APN, filter by the P-CSCF address:
tcpdump -i any -s 0 -w /sdcard/rcs_capture.pcp host <P-CSCF-IP>
```

- Pre-built tcpdump binaries for Android are available at androidtcpdump.com
- SIP runs on port 5060 (UDP/TCP) or 5061 (TLS). IMS typically uses port 5060 over the cellular IMS bearer or over VoWiFi's IPSec tunnel.
- **Limitation**: For Google Jibe RCS, traffic goes over HTTPS to Google's servers, not raw SIP to a P-CSCF. tcpdump will show encrypted TLS streams, not cleartext SIP.

### Method B: PCAPdroid (no root)

- GitHub: `emanuele-f/PCAPdroid` — a no-root Android VPN-based network capture app
- Creates a local VPN, captures all traffic, can export as PCAP
- Can capture and display SIP/HTTP traffic in real-time
- **Limitation**: Cannot decrypt TLS traffic by default (see mitmproxy below)

### Method C: Wireshark + Android Hotspot

- Configure the Android device as a Wi-Fi hotspot
- Connect a laptop running Wireshark to the hotspot
- Capture all traffic on the hotspot interface
- Wireshark's SIP dissector can parse SIP REGISTER, 401 Unauthorized, and 200 OK messages
- **Limitation**: This only works if the SIP traffic is not encrypted. Modern IMS uses IPSec or TLS, making this method less useful for encrypted IMS traffic.

### Method D: adb logcat (radio buffer)

```bash
# Radio logs often contain IMS/SIP debug info
adb logcat -b radio | grep -iE "SIP|IMS|REGISTER|P-CSCF|AKA|401|Unauthorized"

# Carrier Services debug logging
adb logcat -s "ImsService" "ImsResolver" "SipDelegate" "RcsService"
```

- Radio buffer logs (`-b radio`) frequently show IMS registration events, SIP error codes, and authentication challenges
- The level of detail depends on the device and Carrier Services build
- **Key filter**: `adb logcat -b radio -s ImsService` shows IMS registration state transitions

### Google Messages Debug Logging

- In Google Messages settings: Settings → Advanced → Enable debug logging
- This enables verbose RCS/Jibe connection logging visible in logcat
- Reddit user discussions confirm this shows provisioning request/response details

---

## 4. Whether Frida/Xposed Can Hook ImsService to Extract Auth Credentials Mid-Registration

### Feasibility: **Yes, theoretically possible but complex**

**Frida Approach**:
- Attach to the `com.google.android.ims` process (Carrier Services)
- Hook key methods in the IMS stack:
  - `ImsService.registerForImsRegistrationStateChange()` — captures registration state transitions
  - SIP stack internals that process the 401 Unauthorized challenge
  - Methods that handle the `WWW-Authenticate` / `Authorization` headers
  - Any method that receives IK/CK key material from the SIM via `getIccAuthentication()`

**Key Android API to hook**: `TelephonyManager.getIccAuthentication(int appType, int authType, String data)` — this is the method that sends RAND/AUTN to the SIM and receives RES/IK/CK back. Available on Android 10+ (even from ADB shell). This is the single most valuable interception point.

**Practical challenges**:
1. Carrier Services (`com.google.android.ims`) is heavily obfuscated — method names are scrambled
2. The SIP stack implementation is closed-source and proprietary
3. Google's RCS/Jibe path may NOT use traditional IMS AKA at all — it may use Google's own OAuth2-based authentication against Jibe servers
4. Frida itself is detected by Google Play Integrity checks, which Google Messages now requires for RCS

**Xposed/LSPosed Approach**:
- Can hook system-level IMS framework classes without Frida
- Module could intercept `ImsService` callbacks, `SipDelegate` message events
- Less likely to be detected by Play Integrity than Frida
- Requires Magisk + LSPosed framework

### Existing Frida Hook Resources
- `antojoseph/frida-android-hooks` — generic Android method hooking
- `noobpk/frida-android-hook` — tool for easy Frida on Android
- `FrenchYeti/android-file-system-access-hook` — filesystem access hooking via Frida
- No existing Frida scripts specifically targeting IMS/RCS credential extraction were found

---

## 5. How to Intercept the ACS HTTPS Provisioning Response

### What is ACS?
- **Application Configuration Server (ACS)** — part of the RCS provisioning flow (GSMA RCC.07)
- The device sends an HTTPS GET/POST to the ACS to retrieve its RCS configuration XML
- The response contains: P-CSCF address, SIP credentials, feature authorization, service profile, and auth configuration

### Interception Methods

**Method 1: mitmproxy (requires root for system CA injection)**
1. Set up mitmproxy on a machine
2. Install mitmproxy's CA certificate as a system-trusted cert on the Android device:
   - Root required: `adb push mitmproxy-ca-cert.cer /system/etc/security/cacerts/`
   - On Android 14+, this requires additional work due to certificate trust changes
3. Configure Wi-Fi proxy to point to mitmproxy
4. Watch for HTTPS requests to the ACS endpoint (typically `rcs.acs.<carrier>.<tld>` or Google's ACS servers)
5. The ACS XML response will be visible in cleartext

**Method 2: PCAPdroid + mitmproxy integration**
- PCAPdroid supports integration with mitmproxy for TLS decryption on non-rooted devices (using its built-in mitmproxy addon)
- This avoids needing to install system CAs manually

**Method 3: Frida SSL unpinning**
- Use Frida to bypass SSL certificate pinning in Carrier Services
- Hook `SSLContext`, `TrustManager`, or OkHttp's certificate pinner
- Combined with mitmproxy proxy, this allows TLS interception even if the app pins certificates

**Key challenge for Google Jibe RCS**: The provisioning may not use traditional carrier ACS at all. Google Messages connects to Google's Jibe cloud (`jibe.google.com` or similar), and the provisioning happens over Google's proprietary HTTPS APIs, which are likely certificate-pinned and authenticated via Google OAuth tokens.

---

## 6. Whether the IMS AKA Challenge/Response Can Be Captured and Replayed

### IMS AKA Authentication Flow (Carrier IMS Path)

1. Phone sends SIP REGISTER to P-CSCF
2. P-CSCF forwards to I-CSCF → S-CSCF
3. S-CSCF queries HSS for authentication vectors (RAND, AUTN, XRES, IK, CK)
4. S-CSCF returns **401 Unauthorized** with `WWW-Authenticate: Digest algorithm=AKAv1-MD5, nonce=<base64(RAND||AUTN||...)>`
5. Phone's ISIM processes RAND + AUTN → generates RES, IK, CK
6. Phone sends new REGISTER with `Authorization: Digest response=<computed from RES/IK/CK>`
7. S-CSCF compares RES with XRES — if match, 200 OK

### Can this be captured?

**Yes, if you can observe the SIP traffic**:
- The 401 Unauthorized response contains the nonce (which encodes RAND + AUTN + network-specific data)
- The subsequent REGISTER request contains the digest response
- Both are visible in cleartext SIP (if not over IPSec/TLS)

### Can it be replayed?

**No, not directly**, for these reasons:

1. **Nonce is single-use**: Each registration uses a fresh RAND/AUTN challenge. The nonce from a captured exchange cannot be reused for a new registration.
2. **RES is bound to RAND**: The response value depends on the specific RAND challenge. You can't use a captured RES with a different nonce.
3. **IK/CK are session keys**: The integrity key (IK) and cipher key (CK) derived from AKA are used for IPSec SAs that protect subsequent SIP signaling. They are ephemeral and bound to the specific registration.
4. **Sequence numbers prevent replay**: The AUTN contains a sequence number (SQN) that the SIM tracks. A replayed AUTN with an old SQN will be rejected by the SIM.

**However**, if you have **access to the SIM card** (physical or via `getIccAuthentication()` API), you can:
- Generate fresh AKA responses for any challenge
- This is the approach used by zhuowei's `SimServerAndroid` app, which exposes `TelephonyManager.getIccAuthentication()` as an HTTP API
- This allows an external client to authenticate to the IMS core using the phone's SIM card as an oracle

### ISIM vs USIM

- **ISIM** (IP Multimedia Services Identity Module): Dedicated SIM application with IMS-specific keys (K_ISIM). Found on some modern SIMs.
- **USIM**: The standard SIM application can also support IMS AKA using the same K key but a different key derivation.
- Most carriers use USIM-based IMS AKA, not a separate ISIM.

---

## 7. Existing Tools/Projects for Android RCS Credential Extraction

### Directly Relevant

| Project | Description | Status |
|---------|-------------|--------|
| **android-rcs/rcsjta** | GSMA RCS-e stack for Android (open source reference implementation) | Inactive — legacy code from GSMA RCS-e era |
| **biddyweb/android-rcs-ims-stack** | RCS/IMS stack for Android (from Google Code archive) | Abandoned |
| **altanai/Android-SIP-IMS-RCS-WebRTC** | Collection of Android SIP/IMS/RCS/WebRTC resources | Reference only |
| **zhuowei/SimServerAndroid** | HTTP API for SIM card AKA authentication via `getIccAuthentication()` | Working on Android 10+ |
| **fasferraz/SWu-IKEv2** | IKEv2/IPSec client implementing EAP-AKA' for VoWiFi | Partially working |
| **Beeper** | Commercial — reverse-engineered Google Messages RCS bridge | Working (SaaS) |
| **microg/GmsCore** | Open-source Google Play Services implementation — includes RCS reverse engineering efforts | Partially working (RCS support is limited) |

### Network Capture Tools

| Tool | Description |
|------|-------------|
| **PCAPdroid** | No-root Android network capture (VPN-based) with mitmproxy integration |
| **androidtcpdump** | Pre-built tcpdump for Android (requires root) |
| **mitmproxy** | HTTPS proxy for intercepting and decrypting TLS traffic |

### IMS/Telecom Testing Tools

| Tool | Description |
|------|-------------|
| **Open5GS** | Open-source 5G core + IMS (OpenIMS) — for building test networks |
| **Kamailio** | SIP server with IMS module — can act as P-CSCF/I-CSCF/S-CSCF |
| **PyHSS** | Python HSS implementation with AKA support |
| **sipp** | SIP traffic generator for testing |

### Key Finding: Beeper's Approach

Beeper successfully implemented a Google Messages RCS bridge. Their approach (from their blog):
- Beeper connects to Google's Jibe RCS infrastructure
- It acts as an RCS client that registers the phone number
- The specific protocol and authentication details are proprietary to Beeper
- Their Google Messages integration works by connecting as an RCS client on the user's behalf, likely using OAuth tokens obtained through the standard Google Messages setup flow
- This is the closest thing to a working "headless RCS client" that exists today

---

## 8. Practical Attack Surface: What Can Be Extracted Without Root vs With Root

### Without Root (ADB shell access only)

| Data | Method | Feasibility |
|------|--------|-------------|
| P-CSCF addresses | `dumpsys telephony registry` | ✅ Easy |
| IMS registration state | `dumpsys ims` | ✅ Easy |
| ISIM/USIM data (IMPI, IMPU) | `dumpsys isub` or TelephonyManager APIs | ✅ Easy |
| Carrier config (RCS/IMS settings) | `dumpsys carrier_config` | ✅ Easy |
| SIM AKA authentication oracle | `TelephonyManager.getIccAuthentication()` via ADB (Android 10+) | ✅ Easy — this is the most powerful non-root capability |
| Network traffic (PCAP) | PCAPdroid (no-root VPN capture) | ⚠️ Partial — can't decrypt TLS |
| Radio logcat (IMS debug info) | `adb logcat -b radio` | ✅ Easy |
| RCS message content | ContentProvider API (`content://mms-sms/`) | ✅ With READ_SMS permission |
| Google Messages debug logs | Enable in app settings + logcat | ⚠️ Limited detail |

### With Root

| Data | Method | Feasibility |
|------|--------|-------------|
| Carrier Services shared_prefs | Direct file read from `/data/data/com.google.android.ims/shared_prefs/` | ✅ Easy — most likely contains auth tokens, server URLs |
| Carrier Services databases | SQLite read from `/data/data/com.google.android.ims/databases/` | ✅ Easy |
| Google Messages shared_prefs | Direct file read | ✅ Easy — likely contains RCS registration state |
| Google Messages databases | SQLite read | ✅ Easy — contains message history and possibly SIP session data |
| Full traffic capture + decryption | tcpdump + system CA injection for mitmproxy | ✅ Easy |
| Frida hooking of IMS stack | Dynamic instrumentation | ⚠️ Complex — requires reverse engineering obfuscated code |
| Extract ISIM keys from SIM | Direct SIM file access (EF_IMS, etc.) | ⚠️ Requires SIM PIN + carrier-specific access conditions |
| Bypass Play Integrity for RCS | Magisk + Play Integrity Fix module | ⚠️ Cat-and-mouse game with Google |

### Without Any ADB/Shell Access

| Data | Method | Feasibility |
|------|--------|-------------|
| Network traffic (encrypted) | Wi-Fi monitoring / hotspot capture | ❌ Cannot decrypt TLS/IPSec |
| IMSI (via fake ePDG) | Fake Wi-Fi calling server + DNS hijack | ✅ Shown by zhuowei — IMSI leaks during VoWiFi handshake |
| SIP traffic (carrier IMS) | tcpdump on same network | ⚠️ Only if SIP is unencrypted and on same L2 |

---

## 9. How Long RCS Tokens/Sessions Last Before Re-Registration Is Needed

### SIP Registration Lifetime (Carrier IMS Path)

- **SIP REGISTER `Expires` header**: Typically 600,000 seconds (≈7 days) per 3GPP TS 24.229, though carriers configure this differently
- **Common values seen in practice**: 3600s (1 hour) to 600,000s (7 days)
- **Re-registration triggered by**:
  - Expiry of the registration timer (device must re-REGISTER before `Expires` elapses)
  - Network change (LTE → Wi-Fi → VoWiFi handover)
  - SIP 403/401 from S-CSCF (re-authentication required)
  - Device reboot
  - SIM change
  - Carrier-initiated de-registration (via SIP NOTIFY with `registration` event)

### Google Jibe RCS Token Lifetime

- **Google's RCS (Jibe) operates differently from carrier IMS**:
  - Registration is maintained via persistent HTTPS/WebSocket connections to Google's Jibe servers
  - The phone periodically sends "keepalive" messages
  - If the connection drops, the phone must re-register from scratch
  - RCS "Connected" / "Verifying" / "Disconnected" states are visible in Google Messages settings
  - Based on community reports, RCS registration can persist for weeks/months if the app stays active, but can be lost on app updates, reboots, or Play Integrity failures

### Practical Implications for a Headless Client

- **Carrier IMS path**: A captured SIP registration (Call-ID, contact, auth credentials) is valid only until the registration expires or the carrier de-registers. Typical SIP registrations last 1 hour to 7 days. You would need to continuously re-REGISTER with fresh AKA challenges.
- **Google Jibe path**: There is no long-lived "token" to extract. The RCS session is maintained via a persistent connection. To build a headless client, you would need to:
  1. Either maintain an active connection to Jibe servers (like Beeper does)
  2. Or re-register the phone number each time (requires the SIM's AKA capability or Google auth)

---

## 10. Summary and Recommended Approach

### Most Viable Path for a Headless RCS Client

**Option A: SIM-Backed IMS Client (Carrier IMS path)**
1. Use `TelephonyManager.getIccAuthentication()` (available without root on Android 10+) as a SIM AKA oracle
2. Build a SIP stack that performs IMS AKA registration against the carrier's P-CSCF (discoverable via `dumpsys`)
3. Implement the full SIP REGISTER flow with AKAv1-MD5 digest authentication
4. Challenge: P-CSCF is typically only reachable over the carrier's IMS APN — you'd need to route traffic through the phone (VPN/tethering)
5. This is essentially what zhuowei attempted with SWu-IKEv2 + SimServerAndroid — it partially worked but the IKEv2/SIP handshake had compatibility issues

**Option B: Google Jibe RCS Client (OTT path)**
1. Reverse-engineer the Jibe protocol used by Carrier Services (`com.google.android.ims`)
2. Extract the authentication tokens/flow used by Google Messages (likely OAuth2-based)
3. Implement a headless Jibe client
4. Challenge: Google actively blocks third-party RCS clients, requires Play Integrity, and the protocol is proprietary
5. This is essentially what Beeper has done commercially — their approach is the most proven

**Option C: Data Extraction + Session Cloning (requires root)**
1. Root the phone
2. Extract shared_prefs and databases from both `com.google.android.ims` and `com.google.android.apps.messaging`
3. Extract whatever tokens, session cookies, or auth data exists
4. Attempt to clone the session on a different device
5. Challenge: Tokens are likely bound to device identifiers, Google account, and Play Integrity attestation — cloning may not work

### Key Blockers

1. **Play Integrity**: Google now requires Play Integrity attestation for RCS. Rooted devices and emulators fail this check. Workarounds (Magisk modules) exist but are in a constant cat-and-mouse race.
2. **Proprietary Protocol**: Google's Jibe RCS stack is closed-source and obfuscated. No public documentation exists for the Jibe SIP/MSRP extensions.
3. **SIM Binding**: Carrier IMS AKA is cryptographically bound to the SIM's K key. Without physical SIM access (or the `getIccAuthentication()` oracle), you cannot authenticate.
4. **Ephemeral Sessions**: There are no long-lived "RCS tokens" that can be simply extracted and reused. The session requires continuous active maintenance.

---

## Key References

- **zhuowei's VoWiFi research**: https://worthdoingbadly.com/vowifi/ — demonstrates SIM AKA oracle via Android API, fake ePDG for IMSI capture
- **AOSP IMS Single Registration**: https://source.android.com/docs/core/connect/ims-single-registration — architecture of Android 12+ IMS
- **AOSP IMS Implementation**: https://source.android.com/docs/core/connect/ims — ImsService API reference
- **IMS AKA Authentication**: https://nickvsnetworking.com/all-about-ims-authentication-akav1-md5-in-volte-networks/ — detailed AKAv1-MD5 flow
- **Securing the Google SIP Stack**: https://blog.hansenpartnership.com/securing-the-google-sip-stack/ — shows Android SIP stack insecurity
- **Beeper Mini**: https://blog.beeper.com/2023/12/05/how-beeper-mini-works/ — commercial RCS reverse engineering
- **microg/GmsCore RCS Issue**: https://github.com/microg/GmsCore/issues/2063 — community RCS experimentation on non-Google devices
- **SimServerAndroid**: https://github.com/zhuowei/SimServerAndroid — SIM AKA oracle as HTTP API
- **SWu-IKEv2**: https://github.com/fasferraz/SWu-IKEv2 — VoWiFi EAP-AKA' client
- **rcsjta**: https://github.com/android-rcs/rcsjta — open-source RCS-e stack
- **PCAPdroid**: https://github.com/emanuele-f/PCAPdroid — no-root Android network monitor
- **PyHSS**: https://gitlab.com/nickvsnetworking/pyhss — Python HSS with IMS AKA
- **Beekman AKA vulnerabilities paper**: https://www.usenix.org/system/files/conference/woot13/woot13-beekman_0.pdf — security analysis of AKA, IMS, and Android
