# Jibe OTT Direct Registration — Deep Research Report

## Executive Summary

**CRITICAL UPDATE (2025-2026): Google has been systematically shutting down the "Google Guest" / Jibe OTT registration path worldwide.** Starting around August-September 2025, Google began requiring that RCS be provided through carrier agreements rather than via the free Google Guest fallback. This was first observed when AT&T, then carriers in Africa, Asia, and Latin America lost Google Guest access. Users on non-RCS-supporting carriers now see "RCS chats are not supported by your carrier" instead of getting automatic Google Guest registration.

**Before the shutdown**, the Jibe OTT ("Google Guest") path was the EASIEST way to get RCS because it completely bypassed carrier IMS infrastructure. A phone on any carrier, in any country, could register directly with Google's Jibe cloud — no SIM authentication, no IMS AKA, no ePDG tunnel required. The only requirement was Google Play Services (for Firebase IID tokens and Play Integrity attestation).

**For our project**, this means:
1. **The Jibe OTT path is dying or dead for new registrations** — Google is migrating to carrier-only RCS
2. **For carriers that use Jibe Cloud SaaS**, standard GSMA RCS registration still works (carrier-Jibe path)
3. **Reverse engineering the Jibe OTT protocol remains valuable** for understanding Google's RCS infrastructure and potential future use, but the window is closing
4. **The carrier IMS path (ePDG + SIM)** from our carrier-ims-registration-testing.md remains viable and is now the primary path for headless RCS

---

## 1. What Is Jibe OTT / "Google Guest"?

### Definition

**Jibe OTT** (Over-The-Top) is Google's proprietary RCS registration mode that enables RCS on Google Messages for users whose carriers do NOT natively support RCS. It was branded as the **"Google Guest"** program, launched in 2019.

### Key Characteristics

| Attribute | Details |
|-----------|---------|
| **Launched** | 2019 (alongside broader Google RCS push) |
| **Purpose** | Provide RCS to users on carriers that don't support it |
| **Infrastructure** | Google Jibe cloud (not carrier IMS) |
| **Authentication** | Phone number SMS verification + Play Integrity + Firebase IID (NOT IMS AKA) |
| **Transport** | HTTPS/WebSocket to Google servers (NOT SIP to carrier P-CSCF) |
| **Requirements** | Google Messages + Google Play Services + Android with Play Integrity |
| **Status (2026)** | **Being shut down globally** — carriers now must sign RCS agreements with Google |

### How It Differs From Carrier-Jibe RCS

| Aspect | Carrier-Jibe (SaaS) | Jibe OTT ("Google Guest") |
|--------|---------------------|---------------------------|
| **Who pays** | Carrier pays Google for Jibe SaaS | Google provides free to end users |
| **Authentication** | IMS AKA (SIM-based) | Proprietary (Play Integrity + Firebase IID) |
| **Protocol** | Standard SIP REGISTER per GSMA RCC.07 | Proprietary HTTPS/WebSocket to Jibe |
| **Third-party access** | Spec-compliant clients can connect | Google explicitly refuses access |
| **Carrier involvement** | Carrier configures and manages | Carrier not involved at all |
| **iOS support** | Yes (Apple uses carrier-Jibe path) | No (only Google Messages) |
| **Business messaging** | Yes (RCS for Business / RBM) | No (GGC is P2P only) |

### Google Guest Cloud (GGC) — Business Definition

Per Vonage/Sinch documentation: "Google Guest Cloud (GGC) is a solution designed to facilitate the management and monetization of RCS traffic on networks where carriers have not yet signed agreements with Google." When a carrier signs a Google RCS agreement, GGC traffic transitions to managed carrier RCS.

Per Openmind Networks (Dec 2025): "Following the suspension of Google's free RCS guest services, local operators [in Africa] must now decide whether to claim the secure, profitable future of Rich Business Messaging before the opportunity is lost."

This confirms Google is using GGC shutdown as leverage to force carrier RCS agreements.

---

## 2. The Jibe OTT Registration Flow (Step by Step)

### Complete Registration Sequence

Based on analysis of microG issue #2994, microG issue #2063, benwaffle's research, and GrapheneOS debugging:

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Carrier RCS Detection                                  │
│  ──────────────────────────────                                  │
│  Google Messages (via Carrier Services) checks:                  │
│  • CarrierConfig for RCS/IMS settings                           │
│  • TS.43 service entitlement query to carrier                   │
│  • GMS RCS configuration lookup                                 │
│  Result: "Carrier does NOT support RCS" → Fallback to Jibe OTT  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: Play Integrity Attestation                             │
│  ─────────────────────────────                                  │
│  Google Messages requests attestation via GMS:                  │
│  • Calls IAsterismApiService.getAsterismConsent()               │
│  • Play Integrity API returns device attestation token           │
│  • Token includes: device integrity verdict, app integrity,     │
│    licensing verdict                                            │
│  • REQUIRED: At least "MEETS_DEVICE_INTEGRITY" verdict          │
│  • On rooted/custom ROMs: verdict fails → RCS blocked           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: Firebase Instance ID Token Generation                  │
│  ──────────────────────────────────                              │
│  Google Messages requests FCM registration:                     │
│  • FirebaseInstanceId.getInstance().getToken()                   │
│  • Returns a Firebase IID token (identifies app instance)       │
│  • Token is tied to the device + app + Google project           │
│  • Required for push notification delivery (new RCS messages)   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: CompositeToken Assembly                                │
│  ─────────────────────────                                       │
│  The two tokens are combined into a protobuf CompositeToken:    │
│                                                                 │
│  message CompositeToken {                                       │
│    string iid_token = 1;  // Firebase Instance ID token         │
│    string pia_token = 2;  // Play Integrity Attestation token   │
│  }                                                              │
│                                                                 │
│  Encoded as: base64(CompositeToken.toByteArray(),              │
│                      NO_WRAP | URL_SAFE)                        │
│  Sent as HTTP header: gmscore_instance_id_token: <encoded>      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: Phone Number Verification                             │
│  ─────────────────────────────                                  │
│  Google verifies the phone number via GMS Constellation API:    │
│  • Option A: Silent SMS — Google sends a silent SMS to the      │
│    device; if received, number is verified                      │
│  • Option B: SMS OTP — Google sends a visible SMS with a code;  │
│    user may not see it (auto-verified) or may need to enter it  │
│  • Option C: EAP-AKA-like flow using SIM — per RCC.14 sec C.3  │
│  • The verification binds the phone number to the device        │
│  • This is separate from carrier IMS AKA authentication         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 6: Jibe Provisioning Request                             │
│  ──────────────────────────────                                 │
│  Google Messages sends HTTPS request to Jibe provisioning:      │
│  • Endpoint: Likely rcs-acs-prod-us.google.com or similar      │
│  • Headers include:                                             │
│    - gmscore_instance_id_token (CompositeToken)                 │
│    - Authorization: Bearer <opaque_token_from_verification>     │
│    - User-Agent: Google Messages version string                 │
│  • Body: Protobuf-encoded registration request                  │
│  • Response: RCS configuration (SIP domain, server addresses,   │
│    feature capabilities, registration expiry)                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 7: SIP REGISTER to Jibe (or WebSocket Connect)            │
│  ─────────────────────────────────────────────                   │
│  Two possible transport paths:                                   │
│                                                                 │
│  Path A: SIP REGISTER                                           │
│  • Standard SIP REGISTER to Jibe's SIP server                   │
│  • Auth header contains opaque bearer token (NOT IMS AKA)       │
│  • SIP domain is Google's (e.g., jibe.google.com)               │
│  • Feature tags follow GSMA standards                           │
│                                                                 │
│  Path B: WebSocket Connection                                   │
│  • Direct WebSocket to Jibe's cloud messaging server             │
│  • Binary protocol (protobuf-encoded messages)                  │
│  • Auth via session token from provisioning step                │
│  • This is the more likely path for Jibe OTT (not carrier SIP)  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 8: FCM Push Notification Registration                     │
│  ──────────────────────────────────                              │
│  • Device registers with Firebase Cloud Messaging               │
│  • Jibe server uses FCM to push "new message" notifications     │
│  • When notification received, device polls/fetches messages     │
│  • This replaces the SIP SUBSCRIBE/NOTIFY mechanism used in    │
│    carrier IMS                                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 9: RCS "Connected" Status                                 │
│  ──────────────────────                                          │
│  • Google Messages shows "Connected" in chat features settings  │
│  • User can now send/receive RCS messages                       │
│  • Status may show "Connected" with "Google Guest" label       │
│  • Messages are routed through Google's Jibe infrastructure     │
│  • E2EE (Signal Protocol) may be negotiated directly between    │
│    devices, independent of the transport layer                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Insight: Jibe OTT May NOT Use SIP at All

From the microG research and analysis of Google Messages' architecture, the Jibe OTT path may use **proprietary HTTPS/WebSocket transport** rather than standard SIP. The carrier-Jibe path uses SIP because it must interoperate with GSMA-compliant carrier IMS cores, but the Google Guest path only needs to communicate between Google Messages and Google's own Jibe cloud — there's no requirement for SIP interoperability.

Evidence:
- Google Messages' internal `BugleRcsEngine` handles both paths (DUAL_REG mode)
- When Carrier Services is unavailable, Messages falls back to its built-in Jibe client
- The Jibe client likely uses a WebSocket-based binary protocol (similar to the web interface protocol used by mautrix/gmessages)
- Network captures of Jibe OTT traffic would show HTTPS to Google domains, not raw SIP to a P-CSCF

---

## 3. The CompositeToken Protobuf Format

### Structure (from benwaffle's analysis in microG #2994)

```protobuf
message CompositeToken {
  string iid_token = 1;  // Firebase Instance ID token
  string pia_token = 2;  // Play Integrity Attestation token
}
```

### Encoding

The CompositeToken is:
1. Serialized to binary protobuf (`.toByteArray()`)
2. Base64-encoded with `NO_WRAP | URL_SAFE` flags
3. Sent as the `gmscore_instance_id_token` HTTP header in Jibe provisioning requests

### Component Details

**iid_token (Firebase Instance ID token)**:
- Generated by `FirebaseInstanceId.getInstance().getToken()`
- Identifies the specific app installation on the specific device
- Format: Long encoded string (e.g., `f...-...-...`)
- Tied to: app package name, device, Google project (sender ID)
- Can be refreshed by the FCM SDK; old tokens become invalid
- microG implements Firebase IID but tokens may not be accepted by Google's servers

**pia_token (Play Integrity Attestation token)**:
- Generated by `IntegrityTokenProvider.getToken()`
- Contains a signed JWT/encrypted blob with:
  - Device integrity verdict (MEETS_BASIC_INTEGRITY, MEETS_DEVICE_INTEGRITY, MEETS_STRONG_INTEGRITY)
  - App integrity (app was installed from Play Store, not sideloaded)
  - Licensing verdict (app was legitimately licensed)
- Format: Long encrypted string
- Short-lived: typically valid for minutes to a few hours
- Verified server-side by Google
- microG's implementation returns fake tokens that Google's server rejects

### Can We Forge a CompositeToken?

**Short answer: No, not without a real Android device passing Play Integrity.**

**iid_token**: microG can generate Firebase IID tokens that are structurally valid, but Google's Jibe server validates them against Google's FCM infrastructure. A token generated by microG's IID implementation may not be recognized as valid by Google's servers.

**pia_token**: This is the main blocker. Play Integrity tokens are:
- Signed by Google's infrastructure using keys that are not extractable
- Verified server-side by Google's Play Integrity API
- Time-limited and nonce-bound
- Include device attestation from the device's Trusted Execution Environment (TEE)
- microG's Play Integrity implementation generates fake tokens that fail server-side verification

**Conclusion**: Forging a valid CompositeToken requires:
1. A real Android device with Google Play Services
2. The device must pass Play Integrity checks (not rooted, certified)
3. Both tokens must be generated on the same device at approximately the same time

---

## 4. Play Integrity: The Main Blocker

### How Play Integrity Blocks Jibe OTT Registration

Play Integrity is the **primary gatekeeper** for Jibe OTT RCS. Without a valid Play Integrity attestation, the Jibe provisioning server rejects the registration request.

### Play Integrity Verdicts

| Verdict | What It Means | Required for Jibe OTT? |
|---------|--------------|----------------------|
| **MEETS_BASIC_INTEGRITY** | App is running on a real device (not emulator), no tampering detected | Possibly sufficient for some carriers |
| **MEETS_DEVICE_INTEGRITY** | Device is certified by Google (passes CTS), Play Store installed | **Required** for most Jibe OTT paths |
| **MEETS_STRONG_INTEGRITY** | Device has a strong hardware-backed keystore | Required by some stricter checks |

### Evidence That Play Integrity Is Required

1. **Rooted phones lose RCS** (March 2024): Google Messages started blocking RCS on rooted devices. Users with Magisk who previously had working RCS found it broken. Even with Play Integrity Fix (PIF) module, some users still couldn't get RCS.

2. **GrapheneOS RCS failures** (Sept 2025): GrapheneOS users lost RCS after server-side Google changes. The error is "Not Supported: Device does not meet security requirements" (Play Integrity failure).

3. **microG can't generate valid tokens**: microG's Play Integrity implementation returns locally-generated tokens that fail Google's server-side verification. The $14,999 bounty on microG issue #2994 is primarily about this problem.

4. **Samsung Messages also uses Play Integrity**: benwaffle discovered that Samsung's RCS implementation also sends `gmscore_instance_id_token` with the same CompositeToken format. This means Google has made Play Integrity a requirement for ALL RCS clients on Android, not just Google Messages.

5. **Google Messages diagnostic button** (Aug 2025): Google Messages beta added a "Details" button that shows why RCS failed. For custom ROMs, it displays "Device integrity check failed" — confirming Play Integrity is the blocker.

### Bypassing Play Integrity

| Method | Status | Details |
|--------|--------|---------|
| **Magisk + Play Integrity Fix (PIF)** | Cat-and-mouse | Works intermittently; Google updates detection regularly |
| **TrickyStore** | Works with PIF | Spoofs KeyStore to pass device integrity; needs keybox leaks |
| **microG Play Integrity** | Not working | Fake tokens rejected by Google's servers |
| **Emulator** | Very hard | Emulators typically fail basic integrity; GCE-based approaches may work |
| **Cloud Android** (Android in the cloud) | Experimental | Could potentially generate valid tokens but expensive/complex |
| **Leaked keybox** | Temporary | When a valid keybox is leaked, TrickyStore can pass strong integrity until Google revokes the keybox |

---

## 5. Can We Get Firebase IID + Play Integrity Tokens from an Emulated Device?

### Firebase IID from Emulator

**Feasibility: Medium**

- Firebase IID tokens can be generated on an Android emulator if:
  - The emulator has Google Play Services (AVD with Play Store)
  - The Firebase SDK is properly initialized
  - The emulator has a Google account signed in
- **Challenge**: Google's FCM infrastructure may detect emulator-based tokens and reject them
- The Firebase Instance ID API is documented and relatively simple

### Play Integrity from Emulator

**Feasibility: Very Low**

- The Play Integrity API explicitly checks for emulator/non-certified device environments
- Standard Android emulators (AVD) fail the device integrity check
- The integrity verdict includes `"deviceRecognitionVerdict": ["MEETS_BASIC_INTEGRITY"]` without `MEETS_DEVICE_INTEGRITY` on emulators
- Some users have reported that specific cloud Android providers (e.g., AWS Device Farm) can pass device integrity, but this is not publicly documented

### Practical Approach: "Token Generator" Device

The most practical approach is to use a **real, certified Android device** as a "token generator":
1. Install a helper app on a Pixel (or other certified device)
2. The helper app generates CompositeTokens on demand
3. Tokens are exported to the server via a REST API or other channel
4. The server uses these tokens for Jibe OTT registration

**Limitation**: Tokens are short-lived (especially Play Integrity tokens), so the token generator must produce fresh tokens frequently. Play Integrity tokens are typically valid for minutes to hours.

---

## 6. Can microG Generate Valid Enough Tokens for Jibe OTT?

### Current microG Status

**Short answer: No.**

microG's Play Integrity implementation generates **locally-signed tokens** that are not accepted by Google's server-side verification. The tokens are syntactically correct but cryptographically invalid because microG doesn't have access to Google's signing infrastructure.

### microG RCS Support PR (#2995)

PR #2995 (by aybanda) implements:
- `RcsService` and `RcsServiceImpl` — the AIDL interface Google Messages expects
- Required SMS permissions
- Service registration in manifest

This enables Google Messages to **connect to microG's RCS service**, but it does NOT solve the fundamental problem of **generating valid CompositeTokens** that Google's Jibe servers will accept.

### What microG Would Need for Working RCS

1. **Valid Play Integrity tokens** — the hardest problem
2. **Valid Firebase IID tokens** — easier but still requires Google server acceptance
3. **Proper IAsterismApiService implementation** — for attestation consent flow
4. **Constellation API implementation** — for phone number verification
5. **The actual Jibe protocol communication** — once tokens are valid, Messages would handle this via Carrier Services

---

## 7. How Many Devices Can Register on Jibe OTT Per Phone Number?

### Observations from Community Reports

- **One device per number at a time**: If you register a phone number on a new device, the old device's RCS registration is typically invalidated
- **Device transfer**: Google Messages supports transferring RCS registration between devices (via account backup), but the old device loses RCS
- **Multiple registrations not supported**: Unlike carrier IMS (which can have multiple SIP bindings per IMPI), Google Guest appears to enforce single-device registration per phone number
- **Shadow banning**: Users report that attempting RCS registration too many times (especially from non-standard devices) can result in the phone number being "shadow banned" — RCS registration silently fails with no error message

---

## 8. Does Jibe OTT Require Google Play Services?

**Yes, absolutely.**

The Jibe OTT path has hard dependencies on Google Play Services:

| GMS Service | Purpose | Required? |
|-------------|---------|-----------|
| **Play Integrity API** | Device attestation for Jibe provisioning | **YES** — hard blocker |
| **Firebase IID** | App instance identification for push notifications | **YES** — hard blocker |
| **Constellation API** | Phone number verification | **YES** — needed for number binding |
| **IAsterismApiService** | Play Integrity consent flow | **YES** — needed for attestation |
| **FCM (Firebase Cloud Messaging)** | Push notification delivery | **YES** — needed for new message alerts |
| **Google Account** | Identity binding | **YES** — RCS is tied to Google account |

This is why GrapheneOS (with sandboxed Play Services) and microG have such difficulty with RCS — they can't fully replicate all these GMS services.

---

## 9. Can We Bypass Play Integrity Verification?

### Assessment of Bypass Methods

| Method | Feasibility | Duration | Risk |
|--------|------------|----------|------|
| **Magisk + PIF module** | Works currently | Until Google updates detection | Low (personal use) |
| **TrickyStore + leaked keybox** | Works currently | Until keybox revoked (weeks-months) | Medium (keybox leak is illegal in some jurisdictions) |
| **Cloud Android (certified)** | Possible | Ongoing (if certified instance) | High (cost, complexity) |
| **Frida hook to intercept/modify tokens** | Theoretically possible | Until app update | High (Frida is detected by Play Integrity) |
| **Server-side token generation** | Not possible | N/A | N/A — Google's signing infrastructure is not accessible |
| **Android in Docker/VM with certified Play** | Unlikely | N/A | Google detects virtual environments |

### The Fundamental Problem

Play Integrity is designed specifically to prevent what we're trying to do — register with Google's services from an unverified/non-certified environment. The attestation chain goes:

```
Device TEE (hardware) → Android Keystore → Play Integrity API → Google Server Verification
```

Breaking this chain requires either:
1. **Compromising the TEE** (extremely difficult, hardware-specific)
2. **Leaked keybox** (temporary, gets revoked)
3. **Using a certified device** (defeats the purpose of headless operation)
4. **Finding a Google service bug** (unlikely, high-security target)

---

## 10. What's the Jibe OTT Server Endpoint URL?

### Known Endpoints

| Endpoint | Purpose | Status |
|----------|---------|--------|
| `rcs-acs-prod-us.google.com` | Legacy ACS provisioning (used in 2019 hack) | Likely updated/changed |
| `rcs-acs-prod-eu.google.com` | European ACS provisioning | Likely updated/changed |
| `jibe.google.com` | Marketing/info page (not API) | Public |
| `docs.jibemobile.com` | Jibe documentation | Partner login required |
| `rcsbusinessmessaging.googleapis.com` | Business messaging API (NOT consumer RCS) | Public API |
| `messages.google.com` | Web interface (WebSocket-based) | Public |

### What We Don't Know

- The **exact Jibe OTT provisioning endpoint** URL is not publicly documented
- The endpoint is likely discovered dynamically via GMS configuration (not hardcoded in the app)
- The endpoint may differ by region (US, EU, APAC)
- Google has changed these endpoints over time (the 2019 ACS URL hack was patched)
- The Jibe SIP domain (for SIP REGISTER) is also not publicly known for the OTT path

### How to Discover the Endpoint

1. **Frida hook on OkHttp** — intercept all HTTPS requests from `com.google.android.ims` during RCS registration
2. **MITM with SSL unpinning** — decrypt HTTPS traffic to Jibe servers
3. **Static analysis** — search decompiled Carrier Services APK for URL patterns
4. **Logcat analysis** — Google Messages debug logs may reveal server URLs
5. **DNS analysis** — monitor DNS queries during registration to discover Jibe server domains

---

## 11. How Long Does Jibe OTT Registration Last Before Re-Auth Needed?

### Token/Session Lifetimes

| Component | Lifetime | Renewal Trigger |
|-----------|----------|-----------------|
| **SIP Registration** | ~3600 seconds (1 hour) per GSMA spec | Re-REGISTER before 50% expiry |
| **Firebase IID Token** | Days to weeks | App update, FCM SDK refresh, server-side rotation |
| **Play Integrity Token** | Minutes to hours | Fresh attestation needed for each registration attempt |
| **Phone Number Verification** | Once (long-lived) | App reinstall, SIM change, device change, periodic re-verification |
| **Bearer/Opaque Auth Token** | Hours to days | Token rotation by Jibe server |
| **RCS Session** | Persistent while registered | Registration lapse, app kill, network change |

### Re-Authentication Triggers

- **App update**: Google Messages update may trigger re-verification
- **SIM change**: Changing SIM card invalidates registration
- **Device reboot**: May require re-attestation
- **Periodic Play Integrity check**: Google Messages may re-check integrity periodically
- **Carrier change**: Switching carriers triggers full re-provisioning
- **Google account change**: Different Google account requires new registration
- **Server-side revocation**: Google can remotely revoke RCS registration

---

## 12. Google Guest Shutdown Timeline (2025-2026)

### Key Events

| Date | Event | Impact |
|------|-------|--------|
| **2019** | Google Guest program launched | RCS available on any carrier via Google's cloud |
| **2023** | Major US carriers move to Jibe SaaS | T-Mobile, AT&T, Verizon all on Jibe (carrier path) |
| **Mar 2024** | Google starts blocking RCS on rooted devices | Play Integrity enforcement begins |
| **Aug-Sep 2025** | Google Guest RCS starts disappearing globally | Users see "carrier not supported" instead of Google Guest |
| **Sep 2025** | AT&T users get "RCS messaging is now provided by your carrier" notice | Carrier-only RCS on AT&T |
| **Oct 2025** | Reddit reports: "RCS must be provided through carrier now?" | Multiple carriers affected |
| **Dec 2025** | Openmind Networks: "suspension of Google's free RCS guest services" in Africa | African carriers lose Google Guest |
| **2026** | Google Guest largely deprecated worldwide | RCS only available through carrier agreements |

### Why Google Is Shutting Down Google Guest

1. **Monetization**: Google wants carriers to sign RCS agreements (and pay for Jibe SaaS)
2. **Spam prevention**: Free Google Guest was being abused for spam
3. **Control**: Carrier-managed RCS gives Google more leverage over the ecosystem
4. **Business messaging**: RCS for Business requires carrier agreements; Google Guest doesn't support RBM
5. **Infrastructure cost**: Running free RCS for billions of users is expensive

### Impact on Our Project

**The Jibe OTT path is no longer a reliable registration method.** Even if we reverse-engineer the protocol perfectly, Google is actively preventing new Google Guest registrations. The path forward is:

1. **Carrier-Jibe RCS** (via ePDG + SIM) — the primary viable path
2. **Google Messages web interface puppeting** (mautrix/gmessages approach) — requires a phone
3. **Wait for Google to stabilize the new carrier-only RCS ecosystem** and find new attack surfaces

---

## 13. Is Play Integrity the Main Blocker?

### Yes — With Caveats

Play Integrity is the **primary technical blocker** for Jibe OTT registration from a non-standard environment. However, there are additional blockers:

| Blocker | Severity | Details |
|---------|----------|---------|
| **Play Integrity** | **CRITICAL** | Cannot generate valid attestation tokens without certified Android |
| **Firebase IID** | **HIGH** | Tokens may be rejected if not from genuine Play Services |
| **Constellation API** | **MEDIUM** | Phone number verification flow requires GMS integration |
| **Jibe protocol** | **MEDIUM** | Proprietary provisioning/registration protocol not fully documented |
| **Google Guest shutdown** | **CRITICAL** | Server-side blocks new Google Guest registrations regardless of token validity |
| **Certificate pinning** | **MEDIUM** | Jibe HTTPS endpoints likely use certificate pinning |

The Google Guest shutdown is actually a **bigger blocker** than Play Integrity — even with valid tokens, the server may reject the registration because Google Guest is being phased out.

---

## 14. GrapheneOS RCS Experience — What It Tells Us

### Current Status (2026)

GrapheneOS has **working RCS on some carriers** but **broken on others**:

- **Working**: Verizon-based carriers, many international carriers
- **Broken**: T-Mobile, AT&T (require "privileged access")
- **Intermittent**: Some carriers work then break after periodic checks

### What GrapheneOS Proves

1. **Sandboxed Play Services can provide enough for RCS on some carriers** — if the carrier's RCS path doesn't require strong Play Integrity
2. **Some carriers require "privileged access"** — deeper system integration than sandboxed Play Services can provide
3. **Google made server-side changes in September 2025** that broke RCS for many GrapheneOS users
4. **Carrier Services (`com.google.android.ims`) needs background access** — GrapheneOS restricts this, causing registration failures

### GrapheneOS RCS Debugging Insights

From GrapheneOS issue tracker #6173:

```
RcsProvisioningManager: getSimIdFromSubId for subId: 1 returned no mapping.
BugleSelfIdentity: Rcs is NOT_AVAILABLE for SelfIdentity.
  [CONTEXT sub_id=1 rcs_availability="13"]
```

Error code **4006**: "Not Supported: Device does not meet security requirements" — this is the Play Integrity failure code.

The GrapheneOS team has stated: "Google has begun checking whether the device passes Play Integrity verification as part of the RCS registration process."

---

## 15. Frida Hooks for Intercepting Jibe OTT Registration

### Target: Carrier Services (`com.google.android.ims`)

```javascript
// Hook OkHttp to capture all Jibe provisioning requests
Java.perform(function() {
    var RealCall = Java.use("okhttp3.internal.connection.RealCall");
    RealCall.execute.implementation = function() {
        var request = this.request();
        var url = request.url().toString();
        
        // Filter for Jibe/Google RCS endpoints
        if (url.indexOf("rcs-acs") !== -1 || 
            url.indexOf("jibe") !== -1 || 
            url.indexOf("rcs.google") !== -1 ||
            url.indexOf("gmscore_instance_id_token") !== -1) {
            console.log("[JIBE] URL: " + url);
            console.log("[JIBE] Method: " + request.method());
            
            var headers = request.headers();
            for (var i = 0; i < headers.size(); i++) {
                console.log("[JIBE] Header: " + headers.name(i) + ": " + headers.value(i));
            }
            
            // Capture request body
            var body = request.body();
            if (body !== null) {
                var buffer = Java.use("okio.Buffer").$new();
                body.writeTo(buffer);
                console.log("[JIBE] Body: " + buffer.readUtf8());
            }
        }
        
        var response = this.execute();
        
        // Log response for Jibe endpoints
        if (url.indexOf("rcs-acs") !== -1 || url.indexOf("jibe") !== -1) {
            console.log("[JIBE] Response Code: " + response.code());
            var responseBody = response.body();
            if (responseBody !== null) {
                console.log("[JIBE] Response Body (first 1KB): " + 
                    responseBody.string().substring(0, 1024));
            }
        }
        
        return response;
    };
});
```

### Hook the CompositeToken Construction

```javascript
Java.perform(function() {
    // Search for protobuf CompositeToken building
    Java.enumerateLoadedClasses({
        onMatch: function(className) {
            if (className.indexOf("CompositeToken") !== -1 || 
                className.indexOf("AsterismConsent") !== -1 ||
                className.indexOf("InstanceToken") !== -1) {
                console.log("[TOKEN] Found class: " + className);
            }
        },
        onComplete: function() {}
    });
});
```

### Hook Play Integrity Token Generation

```javascript
Java.perform(function() {
    try {
        var IntegrityManager = Java.use("com.google.android.play.core.integrity.IntegrityManager");
        IntegrityManager.requestIntegrityToken.implementation = function(tokenRequest) {
            console.log("[PI] Play Integrity token requested");
            console.log("[PI] Nonce: " + tokenRequest.nonce());
            var result = this.requestIntegrityToken(tokenRequest);
            console.log("[PI] Token result: " + result);
            return result;
        };
    } catch(e) {
        console.log("[PI] IntegrityManager not found: " + e);
    }
});
```

### Hook Firebase IID Token

```javascript
Java.perform(function() {
    try {
        var FirebaseInstanceId = Java.use("com.google.firebase.iid.FirebaseInstanceId");
        FirebaseInstanceId.getInstance.overload().implementation = function() {
            console.log("[IID] FirebaseInstanceId.getInstance() called");
            return this.getInstance();
        };
    } catch(e) {
        console.log("[IID] FirebaseInstanceId not found: " + e);
    }
});
```

---

## 16. Complete Attack Plan for Jibe OTT Registration

### Phase 1: Verify Google Guest Still Works (1-2 days)

1. Get a certified Android device (Pixel recommended)
2. Install Google Messages + Carrier Services
3. Use a SIM from a carrier that does NOT support RCS natively
4. Verify that RCS connects via "Google Guest" (check status in Messages settings)
5. If it shows "Connected" with Google Guest — proceed
6. If it shows "Not supported by carrier" — Google Guest has been fully shut down

### Phase 2: Dynamic Analysis (3-5 days)

1. Root the device with Magisk
2. Install Play Integrity Fix + TrickyStore modules
3. Install Frida Server
4. Enable Google Messages debug menu (`*xyzzy*` in search)
5. Set up Frida hooks for:
   - OkHttp traffic (Jibe provisioning endpoints)
   - CompositeToken construction
   - Play Integrity token generation
   - Firebase IID token generation
6. Force RCS re-registration and capture the full flow
7. Use mitmproxy + Frida SSL unpinning for HTTPS decryption

### Phase 3: Protocol Documentation (2-3 days)

1. Map all Jibe OTT HTTP endpoints
2. Document request/response protobuf formats
3. Extract CompositeToken structure and lifecycle
4. Document phone number verification flow
5. Identify WebSocket message protocol (if applicable)
6. Document SIP REGISTER format and auth token format (if SIP is used)

### Phase 4: Token Generator Implementation (5-7 days)

1. Build a helper Android app that:
   - Generates Firebase IID tokens
   - Requests Play Integrity attestation
   - Assembles CompositeTokens
   - Exposes tokens via a REST API
2. Or: Use Frida on a rooted device to extract tokens on demand

### Phase 5: Python Jibe OTT Client (7-14 days)

1. Implement Jibe provisioning client (HTTPS)
2. Implement CompositeToken injection
3. Implement WebSocket/SIP message transport
4. Implement FCM push notification listener (or alternative)
5. Handle token refresh and re-registration

---

## 17. Feasibility Assessment Summary

### Jibe OTT Path Feasibility (as of May 2026)

| Factor | Status | Impact |
|--------|--------|--------|
| **Google Guest shutdown** | 🔴 Active shutdown | Cannot register new Google Guest devices |
| **Play Integrity requirement** | 🔴 Hard blocker | Cannot generate valid tokens without certified device |
| **Firebase IID requirement** | 🟡 Medium blocker | microG tokens may work but untested |
| **Protocol knowledge** | 🟡 Partially known | Some endpoints and protobuf formats documented |
| **Certificate pinning** | 🟡 Unknown | May need Frida SSL unpinning |
| **Token lifetime** | 🟡 Short-lived | Requires frequent token refresh |
| **Carrier detection** | 🔴 Server-side | Google may block based on carrier even with valid tokens |

### Overall Feasibility: **LOW and decreasing**

The Jibe OTT / Google Guest path is being systematically shut down by Google. Even with perfect protocol knowledge and valid tokens, new registrations are being blocked at the server level. The path that was the "easiest" in 2019-2024 is becoming the hardest in 2026.

### Recommended Path Forward

1. **PRIMARY: Carrier IMS via ePDG** (see carrier-ims-registration-testing.md) — this path works, is well-documented, and doesn't depend on Google Guest
2. **SECONDARY: Google Messages web interface puppeting** (mautrix/gmessages approach) — requires a phone but is known to work
3. **RESEARCH: Monitor Google Guest status** — if Google re-enables the path (unlikely), we'll be ready with protocol knowledge
4. **RESEARCH: Track microG RCS bounty** ($14,999 on issue #2994) — if microG solves the Play Integrity problem, their approach may be usable

---

## 18. Key References and Sources

### Community Research

1. **microG GmsCore Issue #2994** — $14,999 RCS bounty: https://github.com/microg/GmsCore/issues/2994
2. **microG GmsCore Issue #2063** — Original RCS on microG: https://github.com/microg/GmsCore/issues/2063
3. **microG GmsCore PR #2995** — RCS service implementation: https://github.com/microg/GmsCore/pull/2995
4. **GrapheneOS Issue #6173** — RCS provisioning fails: https://github.com/GrapheneOS/os-issue-tracker/issues/6173
5. **GrapheneOS RCS Discussion**: https://discuss.grapheneos.org/d/1353-using-rcs-with-google-messages-on-grapheneos

### Google Guest Shutdown Reports

6. **Reddit: Google Guest RCS appears to be disappearing** (Sep 2025): https://www.reddit.com/r/UniversalProfile/comments/1n6uv5b/
7. **Reddit: RCS must be provided through carrier now** (Oct 2025): https://www.reddit.com/r/GoogleMessages/comments/1oics3w/
8. **Reddit: RCS messaging is now provided by your carrier** (Aug 2025): https://www.reddit.com/r/GoogleMessages/comments/1n0m8k6/
9. **Openmind Networks: To RCS or Not to RCS - The African Dilemma** (Dec 2025): https://www.openmindnetworks.com/blog/to-rcs-or-not-to-rcs-the-african-dilemma/
10. **Sinch Community: What is Google Guest Cloud** (Feb 2025): https://community.sinch.com/t5/RCS/What-is-Google-Guest-Cloud/ta-p/16540

### Play Integrity & RCS

11. **Android Police: Google blocking RCS on rooted devices** (Mar 2024): https://www.androidpolice.com/google-blocking-rcs-google-messages-rooted-android/
12. **Android Gadget Hacks: Hidden RCS diagnostic** (Aug 2025): https://android.gadgethacks.com/news/when-your-custom-rom-breaks-rcs-the-hidden-diagnostic-coming-to-google-messages-could-finally-tell-you-why-0409265/
13. **PlayIntegrityFork module**: https://github.com/osm0sis/PlayIntegrityFork

### Technical Documentation

14. **Wikipedia: Rich Communication Services** (updated May 2026): https://en.wikipedia.org/wiki/Rich_Communication_Services
15. **Jibe Platform Documentation** (partner-only): https://docs.jibemobile.com/
16. **GSMA RCC.14** — Service Provider Device Configuration
17. **GSMA RCC.07** — RCS Advanced Communications
18. **AOSP IMS Single Registration**: https://source.android.com/docs/core/connect/ims-single-registration

### Existing Research in This Project

19. **Jibe RCS Cloud Protocol Research**: /home/ubuntu/rcs-research/jibe-rcs-cloud-protocol-research.md
20. **Google Messages Reverse Engineering**: /home/ubuntu/rcs-research/google-messages-reverse-engineering.md
21. **AOSP RCS IMS Audit**: /home/ubuntu/rcs-research/aosp-rcs-ims-audit-report.md
22. **Carrier IMS Registration Testing**: /home/ubuntu/rcs-research/carrier-ims-registration-testing.md

---

*Report generated 2026-05-16 from analysis of 4 internal research documents + 25+ targeted web searches covering Google Guest RCS architecture, Jibe OTT registration protocol, Play Integrity enforcement, CompositeToken protobuf format, Google Guest shutdown timeline, microG RCS support status, GrapheneOS RCS debugging, and Frida-based interception techniques.*
