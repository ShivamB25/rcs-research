# RCSJTA Audit & IMS AKA Glue Code

## Table of Contents
1. [RCSJTA Deep Audit](#part-1-rcsjta-deep-audit)
   - [Repository Overview](#11-repository-overview)
   - [SIP Registration Flow](#12-sip-registration-flow-registrationmanager)
   - [Auth Procedures: GIBA vs Digest MD5](#13-auth-procedures-giba-vs-digest-md5)
   - [Token/Session Storage in RcsSettings](#14-tokensession-storage-in-rcssettings)
   - [ACS Provisioning Trigger and XML Parsing](#15-acs-provisioning-trigger-and-xml-parsing)
   - [Key Classes and File Paths](#16-key-classes-and-file-paths)
   - [Messaging Flow (INVITE+MSRP for Chat)](#17-messaging-flow-invitemsrp-for-chat)
2. [IMS AKA Glue Code](#part-2-ims-aka-glue-code)
   - [Architecture](#21-architecture)
   - [parse_401_challenge()](#22-parse_401_challenge)
   - [decode_aka_nonce()](#23-decode_aka_nonce)
   - [call_sim_rest_server()](#24-call_sim_rest_server)
   - [compute_aka_digest_response()](#25-compute_aka_digest_response)
   - [build_sip_register()](#26-build_sip_register)
   - [Full Orchestration](#27-full-orchestration)
   - [AKAv2-MD5 Support](#28-akav2-md5-support)

---

# PART 1: RCSJTA Deep Audit

## 1.1 Repository Overview

**Repository**: `https://github.com/android-rcs/rcsjta`
**License**: Apache 2.0
**Origin**: Originally developed by Orange Labs (France Telecom/Orange); later maintained by Sony Mobile
**Namespace**: `com.gsma.rcs` (successor to `com.orangelabs.rcs` in the older biddyweb stack)
**Compliance**: GSMA RCS-e Blackbird (joyn) profile; TAPI 1.5 / 1.6
**SIP Stack**: NIST-SIP (javax2.sip)
**DNS Stack**: DNSJava
**Crypto**: Bouncy Castle

### Directory Structure (Key Paths)

```
rcsjta/
├── core/                          ★ CORE RCS STACK ★
│   └── src/com/gsma/rcs/
│       ├── core/ims/
│       │   ├── ImsModule.java                           # Central IMS orchestrator
│       │   ├── network/
│       │   │   ├── ImsNetworkInterface.java              # Network interface abstraction
│       │   │   ├── ImsConnectionManager.java             # Connection state management
│       │   │   ├── registration/
│       │   │   │   ├── RegistrationManager.java          ★ SIP registration state machine
│       │   │   │   ├── RegistrationProcedure.java        ★ Abstract auth procedure interface
│       │   │   │   ├── GibaRegistrationProcedure.java    ★ GIBA (early-IMS) auth
│       │   │   │   ├── HttpDigestRegistrationProcedure.java ★ HTTP Digest MD5 auth
│       │   │   │   └── RegistrationUtils.java            # Feature tags, utilities
│       │   │   ├── sip/
│       │   │   │   ├── SipManager.java                  # SIP stack manager
│       │   │   │   ├── SipMessageFactory.java           # SIP message construction
│       │   │   │   └── SipUtils.java                    # SIP header utilities
│       │   │   └── gsm/CallManager.java                  # CS call management
│       │   ├── protocol/
│       │   │   ├── sip/                                  # SIP protocol layer
│       │   │   │   ├── SipRequest.java
│       │   │   │   ├── SipResponse.java
│       │   │   │   ├── SipDialogPath.java
│       │   │   │   └── SipTransactionContext.java
│       │   │   └── msrp/                                # MSRP protocol layer
│       │   ├── security/
│       │   │   └── HttpDigestMd5Authentication.java     ★ MD5 digest computation
│       │   ├── service/
│       │   │   ├── im/                                   # Instant Messaging service
│       │   │   ├── capability/                           # Capability discovery
│       │   │   ├── presence/                              # Presence service
│       │   │   ├── richcall/                              # Rich call (video share, etc.)
│       │   │   ├── sip/                                   # SIP service
│       │   │   └── terms/                                # Terms & conditions
│       │   └── userprofile/UserProfile.java              # IMS user profile (IMPI, IMPU, password)
│       ├── provisioning/
│       │   ├── ProvisioningInfo.java                     # Provisioning data model
│       │   ├── ProvisioningParser.java                   ★ ACS XML parser
│       │   └── https/
│       │       ├── HttpsProvisioningManager.java         ★ HTTPS provisioning manager
│       │       ├── HttpsProvisioningConnection.java       # Network connectivity for provisioning
│       │       ├── HttpsProvisioningUtils.java           # URL construction, query params
│       │       ├── HttpsProvisioningService.java         # Android service wrapper
│       │       ├── HttpsProvisioningSMS.java             # SMS OTP handling
│       │       └── HttpsProvisioningResult.java          # Result data class
│       ├── provider/settings/
│       │   ├── RcsSettings.java                          ★ Persistent settings accessor
│       │   └── RcsSettingsData.java                      # Settings keys & defaults
│       └── service/
│           └── RcsServiceControlReceiver.java            ★ Boot/activation receiver
├── RI/                            # Reference Implementation (UI app)
├── libs/api/                      # TAPI public API (com.gsma.services.rcs)
└── tools/settings/                # Settings management app
```

---

## 1.2 SIP Registration Flow (RegistrationManager)

The `RegistrationManager` class is the central SIP registration state machine. It extends `PeriodicRefresher` which handles the re-registration timer.

### Step-by-Step Registration Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        REGISTRATION FLOW                            │
│                                                                     │
│  1. register() called                                               │
│     ├─ If mDialogPath == null:                                      │
│     │   ├─ mRegistrationProcedure.init()  ← Reset auth procedure   │
│     │   ├─ Generate new Call-ID                                      │
│     │   ├─ Build target: "sip:" + getHomeDomain()                    │
│     │   ├─ Get public URI from procedure.getPublicUri()             │
│     │   └─ Create SipDialogPath(cseq=1)                             │
│     └─ Else: incrementCseq()                                        │
│                                                                     │
│  2. Create REGISTER request                                         │
│     ├─ SipMessageFactory.createRegister(dialogPath, featureTags,     │
│     │     expirePeriod, instanceId, keepAliveEnabled)               │
│     └─ mRegistrationProcedure.writeSecurityHeader(register)         │
│         ├─ GIBA: no header written                                  │
│         └─ Digest: Authorization header with realm/nonce/response   │
│                                                                     │
│  3. sendRegister(register)                                          │
│     ├─ Send via SIP stack, wait for response                        │
│     └─ Switch on status code:                                       │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ 200 OK:                                                        │ │
│  │   ├─ Extract P-Associated-URI → set associated URIs            │ │
│  │   ├─ Extract Contact +sip.instance → set GRUU                  │ │
│  │   ├─ Extract Service-Route → set service route path            │ │
│  │   ├─ Detect NAT (Via header IP vs local IP)                    │ │
│  │   ├─ mRegistrationProcedure.readSecurityHeader(resp)           │ │
│  │   │   └─ Digest: read Authentication-Info nextnonce           │ │
│  │   ├─ Retrieve expire period from Contact/Expires               │ │
│  │   ├─ Set mRegistered = true                                    │ │
│  │   ├─ Start periodic re-registration timer                       │ │
│  │   └─ Notify listener: onRegistrationSuccessful()              │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ 401 Unauthorized:                                              │ │
│  │   ├─ Increment mNb401Failures                                 │ │
│  │   ├─ If >= MAX_REGISTRATION_FAILURES (3): fail                  │ │
│  │   ├─ mRegistrationProcedure.readSecurityHeader(resp)           │ │
│  │   │   ├─ GIBA: read P-Associated-URI → set username/domain     │ │
│  │   │   └─ Digest: read WWW-Authenticate → realm/nonce/opaque/qop│ │
│  │   ├─ Increment CSeq                                            │ │
│  │   ├─ Create new REGISTER with writeSecurityHeader()            │ │
│  │   │   └─ Digest: compute response = MD5(user:realm:pwd, etc.)  │ │
│  │   └─ sendRegister(register)  ← re-send with credentials        │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ 403 Forbidden:                                                 │ │
│  │   ├─ If count < MAX_403_REGISTRATION_FAILURES (5):            │ │
│  │   │   ├─ Increment counter                                     │ │
│  │   │   ├─ Stop RCS core service                                  │ │
│  │   │   └─ Trigger HttpsProvisioningService (re-provision)        │ │
│  │   └─ Else: stop RCS, reset config, mark config invalid         │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ 423 Interval Too Brief:                                        │ │
│  │   ├─ Extract Min-Expires from response                         │ │
│  │   ├─ Update mExpirePeriod                                      │ │
│  │   └─ Re-send REGISTER with corrected expire                    │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ 302 Moved Temporarily:                                         │ │
│  │   ├─ Extract new target from Contact header                    │ │
│  │   ├─ Update dialogPath target                                  │ │
│  │   └─ Re-send REGISTER to new address                           │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Registration Details

| Parameter | Value | Notes |
|-----------|-------|-------|
| MAX_REGISTRATION_FAILURES | 3 | Max 401 failures before giving up |
| MAX_403_REGISTRATION_FAILURES | 5 | Max 403 failures before resetting config |
| DEFAULT_EXPIRE_PERIOD | 1,200,000 ms (1200s) | Default registration lifetime |
| Re-registration timing | At 50% of expire period | Starts timer at half the expiry |
| Feature tags | From RegistrationUtils | Includes +g.3gpp.icsi-ref, +sip.instance |

### De-registration Flow

```
deRegister():
  1. stopTimer() — stop periodic re-registration
  2. incrementCseq()
  3. SipMessageFactory.createRegister(expire=0) — REGISTER with Expires:0
  4. sendRegister(register)
  5. Set mRegistered = false
  6. resetDialogPath()
  7. Notify: onRegistrationTerminated(BATTERY_LOW or CONNECTION_LOST)
```

---

## 1.3 Auth Procedures: GIBA vs Digest MD5

**CRITICAL FINDING: rcsjta does NOT implement IMS AKA (AKAv1-MD5) authentication.** It only supports two auth procedures:

### RegistrationProcedure (Abstract Interface)

```java
public abstract class RegistrationProcedure {
    public abstract void init();
    public abstract String getHomeDomain();
    public abstract String getPublicUri();
    public abstract void writeSecurityHeader(SipRequest request) throws PayloadException;
    public abstract void readSecurityHeader(SipResponse response) throws PayloadException;
}
```

### GIBA (GibaRegistrationProcedure)

**What it is**: GBA-Improved Bootstrapping Authentication, also known as "early IMS" or "IMS before ISIM". Used when the device has no ISIM or doesn't support AKA.

**How it works**:
1. `init()`: Reads IMSI, MCC, MNC from `TelephonyManager`
2. `getHomeDomain()`: Constructs `ims.mnc<MNC>.mcc<MCC>.3gppnetwork.org`
3. `getPublicUri()`: Derives IMPU as `sip:<IMSI>@ims.mnc<MNC>.mcc<MCC>.3gppnetwork.org`
4. `writeSecurityHeader()`: **Does nothing** — no Authorization header is added to REGISTER
5. `readSecurityHeader()`: Reads `P-Associated-URI` from the 200 OK response to extract the real MSISDN-based SIP URI, then updates `UserProfile` with the real username and home domain

**Security**: GIBA relies on the cellular bearer being already authenticated — the network trusts that the SIP signaling comes from the same device that established the PDP context. No cryptographic challenge-response.

**When used**: When `AuthType` in ACS XML is `"GIBA"`, or when no ISIM is available. Common in early RCS-e deployments.

### HTTP Digest MD5 (HttpDigestRegistrationProcedure)

**What it is**: Standard RFC 2617 HTTP Digest authentication using MD5. The client has a pre-shared username and password (provisioned via ACS XML).

**How it works**:
1. `init()`: Creates `HttpDigestMd5Authentication` instance
2. `getHomeDomain()`: Returns `ImsModule.getImsUserProfile().getHomeDomain()` (from ACS or settings)
3. `getPublicUri()`: Returns `sip:<username>@<homeDomain>` (from UserProfile)
4. `writeSecurityHeader()`:
   - If nonce is empty (first REGISTER): writes empty Authorization header
   - If nonce is present (after 401): computes `response = MD5(MD5(user:realm:password):nonce:MD5(REGISTER:uri))` and writes full Authorization header with `algorithm=MD5`
   - Supports qop="auth" with nc and cnonce
   - Supports opaque parameter
   - Supports nextnonce from Authentication-Info header in 200 OK
5. `readSecurityHeader()`:
   - From 401: reads `WWW-Authenticate` header → realm, nonce, opaque, qop
   - From 200 OK: reads `Authentication-Info` header → nextnonce for future use

**Authorization header format** (from source code):
```
Digest username="<privateID>",uri="<requestURI>",algorithm=MD5,
  realm="<realm>",nonce="<nonce>",response="<response>",
  opaque="<opaque>",nc=<nc>,qop=<qop>,cnonce="<cnonce>"
```

**Security**: Standard MD5 digest auth. Password is obtained from ACS XML (`UserPwd` parameter in `APPAUTH` section) or stored in `RcsSettings`.

### Auth Type Selection

The auth type is determined by `RcsSettingsData.AuthenticationProcedure` which is set during ACS provisioning parsing (`ProvisioningParser.parseAppAuthent()`):

| ACS AuthType | rcsjta AuthProcedure | Notes |
|-------------|---------------------|-------|
| `"GIBA"` | `GibaRegistrationProcedure` | Early IMS, no challenge |
| `"Digest"` | `HttpDigestRegistrationProcedure` | MD5 digest with password |
| `"AKA"` | **NOT IMPLEMENTED** | Would need ISIM AKA — rcsjta has no AKA class |

### The AKA Gap

**rcsjta has NO implementation of AKAv1-MD5 or AKAv2-MD5**. There is:
- No `AkaRegistrationProcedure` class
- No code to extract RAND/AUTN from the SIP 401 nonce
- No code to communicate with the ISIM/SIM for AUTHENTICATE APDU
- No code to compute the AKA-Digest response using RES/CK/IK
- No `Security-Client`/`Security-Server` header handling for IPSec

This is the single largest gap for carrier IMS deployment. Most production carriers require AKAv1-MD5, not Digest MD5 and certainly not GIBA.

---

## 1.4 Token/Session Storage in RcsSettings

`RcsSettings` is the persistent settings accessor backed by a content provider (`RcsSettingsProvider`). All configuration from ACS provisioning and runtime state is stored here.

### Key Settings Related to Registration

| Setting Key | Description | Source |
|------------|-------------|--------|
| `UserProfileImsPrivateId` | IMPI (e.g., `user@domain`) | ACS `Private_User_Identity` |
| `UserProfileImsDomain` | Home domain | ACS `Home_network_domain_name` |
| `UserProfileImsUserName` | MSISDN/username | ACS `Public_User_Identity` or GIBA P-Associated-URI |
| `UserProfileImsPassword` | SIP auth password | ACS `UserPwd` in APPAUTH |
| `Realm` | Authentication realm | ACS APPAUTH `Realm` |
| `AuthenticationProcedure` | GIBA or Digest | ACS APPAUTH `AuthType` |
| `RegisterExpirePeriod` | Registration expiry (ms) | ACS or default 1,200,000 |
| `SipTimerT1/T2/T4` | SIP retransmit timers | ACS `Timer_T1/T2/T4` |
| `RegisterRetryBaseTime` | Reg retry base (ms) | ACS `RegRetryBaseTime` |
| `RegisterRetryMaxTime` | Reg retry max (ms) | ACS `RegRetryMaxTime` |
| `ProvisioningToken` | Provisioning token | ACS token param |
| `ProvisioningVersion` | Config version | ACS `vers` param |
| `ConfigurationValid` | Whether config is valid | Set after successful parse |
| `PcscfAddress` | P-CSCF FQDN | ACS `LBO_P-CSCF_Address` |
| `SecondaryProvisioningAddress` | Backup ACS URL | From settings |

### Session State (in RegistrationManager, not persisted)

| Field | Type | Description |
|-------|------|-------------|
| `mRegistered` | boolean | Whether currently registered |
| `mDialogPath` | SipDialogPath | Current SIP dialog (Call-ID, CSeq, tags) |
| `mExpirePeriod` | long | Current registration expiry |
| `mNb401Failures` | int | Count of 401 failures for current attempt |
| `mNb4xx5xx6xxFailures` | int | Count of other failures |
| `mReasonCode` | ReasonCode | Reason for de-registration |
| `mPendingUnRegister` | boolean | De-register pending after current reg |

### HttpDigestMd5Authentication (Runtime State)

| Field | Description |
|-------|-------------|
| `realm` | Current auth realm |
| `nonce` | Server nonce from 401 |
| `nextnonce` | Next nonce from 200 OK Authentication-Info |
| `opaque` | Server opaque value |
| `qop` | Quality of protection |
| `cnonce` | Client nonce (generated) |
| `nc` | Nonce counter |

---

## 1.5 ACS Provisioning Trigger and XML Parsing

### Trigger Mechanism

1. **Boot time**: `RcsServiceControlReceiver` receives `BOOT_COMPLETED` → starts `HttpsProvisioningService`
2. **Network connectivity**: `HttpsProvisioningConnection` detects network changes → triggers `updateConfig()`
3. **403 Forbidden**: `RegistrationManager.handle403Forbidden()` → stops core service → starts `HttpsProvisioningService` with `enforce=true`
4. **Version check**: If ACS returns a version ≤ stored version, config is unchanged; if greater, re-parse
5. **511 Network Auth Required**: ACS returns HTTP 511 → triggers SMS OTP flow for WiFi provisioning

### HttpsProvisioningManager Flow

```
1. buildProvisioningAddress()
   → "config.rcs.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org"

2. On mobile network:
   a. HTTP GET to primary URI (unsecured)
   b. If 200 OK → HTTPS GET with query params (secured)
   c. If 511 → switch to OTP flow

3. On WiFi:
   a. HTTPS GET with OTP (SMS-based one-time password)
   b. Requires MSISDN input from user
   c. Wait for SMS OTP → resend HTTPS with OTP

4. Query parameters (built by getHttpsRequestArguments()):
   - vers=<provisioning_version>
   - rcs_version=<version_string>
   - rcs_profile=<profile_name>
   - client_vendor=<vendor>
   - client_version=<version>
   - terminal_vendor=<device_vendor>
   - terminal_model=<device_model>
   - terminal_sw_version=<firmware>
   - IMSI=<imsi>
   - IMEI=<imei>
   - SMS_port=<port> (for OTP)
   - msisdn=<phone_number> (for WiFi)
   - token=<provisioning_token> (WiFi only)

5. Process result:
   ├─ 200 OK + valid XML → parse → apply settings → launch RCS core
   ├─ 200 OK + empty/OTP → wait for SMS OTP
   ├─ 403 Forbidden → reset config, stop service
   ├─ 511 → retry with OTP
   └─ 503 Unavailable → retry after Retry-After timer
```

### ProvisioningParser XML Parsing

The parser handles OMA CP `<wap-provisioningdoc>` XML with `<characteristic>` sections:

| Section | Parser Method | Key Parameters |
|---------|--------------|----------------|
| VERS | `parseVersion()` | `version`, `validity` |
| TOKEN | `parseToken()` | `token`, `validity` |
| MSG | `parseTermsMessage()` | `title`, `message`, `Accept_btn`, `Reject_btn` |
| APPLICATION | `parseApplication()` | `AppID`, `Name`, `AppRef` → dispatches to `parseIMS()` or `parseRCSe()` |
| IMS | `parseIMS()` | `Timer_T1/T2/T4`, `Private_User_Identity`, `Home_network_domain_name`, `Keep_Alive_Enabled`, `RegRetryBaseTime`, `RegRetryMaxTime` |
| APPAUTH | `parseAppAuthent()` | `AuthType` (GIBA/Digest), `Realm`, `UserName`, `UserPwd` |
| LBO_P-CSCF_Address | `parsePcscfAddress()` | `Address`, `AddressType` |
| SERVICES | `parseServices()` | `ChatAuth`, `ftAuth`, `vsAuth`, `isAuth`, `geolocPushAuth`, `rcsIPVoiceCallAuth`, etc. |
| PRESENCE | `parsePresence()` | `usePresence`, `presencePrfl`, `IconMaxSize`, `PublishTimer` |
| IM | `parseIM()` | `imMsgTech`, `firstMessageInvite`, `TimerIdle`, `MaxSize1to1`, `ftHTTPCSURI`, `ftDefaultMech`, `conf-fcty-uri`, `max_adhoc_group_size` |
| CAPDISCOVERY | `parseCapabilityDiscovery()` | `defaultDisc`, `pollingPeriod`, `capInfoExpiry` |
| APN | `parseAPN()` | `rcseOnlyAPN`, `enableRcseSwitch`, `alwaysUseIMSAPN` |
| OTHER | `parseOther()` | `psSignalling`, `psMedia`, `psRTMedia` |
| XDMS | `parseXDMS()` | `RevokeTimer`, `XCAPRootURI`, `XCAPAuthenticationUserName`, `XCAPAuthenticationSecret` |

### Auth Type Parsing (Critical Section)

From `ProvisioningParser.parseAppAuthent()`:
```java
// AuthType parameter → maps to RcsSettingsData.AuthenticationProcedure enum
// "GIBA"   → AuthenticationProcedure.GIBA   → GibaRegistrationProcedure
// "Digest" → AuthenticationProcedure.DIGEST  → HttpDigestRegistrationProcedure
// "AKA"    → NOT MAPPED (would need new enum + AkaRegistrationProcedure)
```

The `RcsSettingsData.AuthenticationProcedure` enum only has `GIBA` and `DIGEST` values.

---

## 1.6 Key Classes and File Paths

| Class | Path | Role |
|-------|------|------|
| `RegistrationManager` | `core/src/com/gsma/rcs/core/ims/network/registration/RegistrationManager.java` | SIP REGISTER state machine; handles 200/401/403/423/302 |
| `RegistrationProcedure` | `core/src/com/gsma/rcs/core/ims/network/registration/RegistrationProcedure.java` | Abstract auth procedure interface |
| `GibaRegistrationProcedure` | `core/src/com/gsma/rcs/core/ims/network/registration/GibaRegistrationProcedure.java` | GIBA auth: IMSI-derived IMPU, no challenge |
| `HttpDigestRegistrationProcedure` | `core/src/com/gsma/rcs/core/ims/network/registration/HttpDigestRegistrationProcedure.java` | MD5 Digest auth: username/password from ACS |
| `HttpDigestMd5Authentication` | `core/src/com/gsma/rcs/core/ims/security/HttpDigestMd5Authentication.java` | MD5 digest computation engine |
| `ImsModule` | `core/src/com/gsma/rcs/core/ims/ImsModule.java` | Central IMS orchestrator; manages services and connection |
| `UserProfile` | `core/src/com/gsma/rcs/core/ims/userprofile/UserProfile.java` | IMS identity: IMPI, IMPU, realm, password |
| `SipMessageFactory` | `core/src/com/gsma/rcs/core/ims/network/sip/SipMessageFactory.java` | Constructs SIP REGISTER, MESSAGE, INVITE |
| `ProvisioningParser` | `core/src/com/gsma/rcs/provisioning/ProvisioningParser.java` | OMA CP XML parser for ACS response |
| `HttpsProvisioningManager` | `core/src/com/gsma/rcs/provisioning/https/HttpsProvisioningManager.java` | HTTPS provisioning: URL construction, HTTP requests, OTP |
| `HttpsProvisioningUtils` | `core/src/com/gsma/rcs/provisioning/https/HttpsProvisioningUtils.java` | URL helpers, rcs_version, rcs_profile strings |
| `RcsSettings` | `core/src/com/gsma/rcs/provider/settings/RcsSettings.java` | Persistent settings accessor |
| `RcsSettingsData` | `core/src/com/gsma/rcs/provider/settings/RcsSettingsData.java` | Settings key constants and defaults |
| `RcsServiceControlReceiver` | `core/src/com/gsma/rcs/service/RcsServiceControlReceiver.java` | Boot receiver; starts provisioning on device boot |
| `ImsConnectionManager` | `core/src/com/gsma/rcs/core/ims/network/ImsConnectionManager.java` | Manages mobile/WiFi network interfaces |
| `InstantMessagingService` | `core/src/com/gsma/rcs/core/ims/service/im/InstantMessagingService.java` | IM service: chat sessions, MSRP, file transfer |
| `CapabilityService` | `core/src/com/gsma/rcs/core/ims/service/capability/CapabilityService.java` | Capability discovery (presence or SIP OPTIONS) |
| `PresenceService` | `core/src/com/gsma/rcs/core/ims/service/presence/PresenceService.java` | SIP presence (SUBSCRIBE/NOTIFY/PUBLISH) |

---

## 1.7 Messaging Flow (INVITE+MSRP for Chat)

### Session-Mode Chat (Large Messages / Group Chat)

```
1. Sender → P-CSCF: SIP INVITE with SDP offering MSRP session
   - SDP: m=message <port> TCP/MSRP *
   - SDP: a=path:msrp://<local_ip>:<port>/<session_id>;tcp
   - SDP: a=accept-types:message/cpim application/im-iscomposing+xml
   - SDP: a=accept-wrapped-types:text/plain message/imdn+xml
   - SIP: P-Preferred-Service: urn:urn-7:3gpp-service.ims.icsi.oma.cpm.session
   - SIP: Contribution-ID, Conversation-ID

2. Receiver → P-CSCF: 200 OK with SDP answer (MSRP path)
   - SDP: a=path:msrp://<remote_ip>:<port>/<session_id>;tcp

3. Sender: ACK

4. Sender → Receiver: TCP/MSRP SEND
   - MSRP:<session_id> SEND
   - To-Path: msrp://<remote_ip>:<port>/<session_id>;tcp
   - From-Path: msrp://<local_ip>:<port>/<session_id>;tcp
   - Content-Type: message/cpim
   - CPIM body with text/plain payload

5. Receiver → Sender: MSRP 200 OK

6. Session kept alive per TimerIdle (default 300s)
   - Further messages sent on same MSRP session

7. Close: SIP BYE
```

### Pager-Mode Chat (Standalone SIP MESSAGE)

For short messages, rcsjta can use SIP MESSAGE (pager mode) instead of INVITE+MSRP, controlled by the `firstMessageInvite` ACS parameter:
- `firstMessageInvite=1`: Use INVITE+MSRP (session mode, default for Blackbird)
- `firstMessageInvite=0`: Use SIP MESSAGE (pager mode)

### Feature Tags in REGISTER

The `RegistrationUtils.getSupportedFeatureTags()` method builds the feature tag list that the client includes in REGISTER to indicate supported services:

```
+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.msg"
+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.session"
+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.filetransfer"
+g.3gpp.iari-ref="urn%3Aurn-7%3A3gpp-application.ims.iari.rcs.filedl"
+g.3gpp.iari-ref="urn%3Aurn-7%3A3gpp-application.ims.iari.rcs.geolocpush"
+g.3gpp.iari-ref="urn%3Aurn-7%3A3gpp-application.ims.iari.rcs.ipcall"
+sip.instance="<urn:gsma:imei:...>"
```

---

# PART 2: IMS AKA Glue Code

## 2.1 Architecture

This Python module bridges `sim-rest-server` (pySim) to a SIP stack for IMS AKA registration. It fills the gap that rcsjta has — no AKA auth implementation — by providing standalone functions that:

1. Parse the SIP 401 challenge to extract RAND/AUTN from the nonce
2. Call `sim-rest-server` to perform ISIM AKA authentication on a physical SIM card
3. Compute the AKAv1-MD5 digest response per RFC 3310 / RFC 2617
4. Build the authenticated SIP REGISTER packet
5. Orchestrate the full registration flow

```
┌─────────────────┐     ┌──────────────────────┐     ┌──────────────────┐     ┌─────────┐
│  SIP Stack       │────→│  parse_401_challenge  │────→│  decode_aka_nonce│────→│ RAND    │
│  (raw socket     │     │  (extract algorithm,  │     │  (Base64 decode, │     │ AUTN    │
│   or pjsip)      │     │   nonce, realm, qop)  │     │   split at byte  │     │         │
│                  │     └──────────────────────┘     │   boundaries)     │     └────┬────┘
│                  │                                   └──────────────────┘          │
│                  │                                                                 │
│                  │     ┌──────────────────────┐     ┌──────────────────┐          │
│                  │←────│  build_sip_register    │←────│  compute_aka_    │←─────────┤
│                  │     │  (construct SIP       │     │  digest_response │          │
│                  │     │   REGISTER packet)    │     │  (RFC 3310 MD5   │     ┌────┴────┐
│                  │     └──────────────────────┘     │   chain with     │     │ RES     │
│                  │                                   │   RES, CK, IK)   │     │ CK, IK  │
│                  │                                   └──────────────────┘     └────┬────┘
│                  │                                                                 │
│                  │                                   ┌──────────────────┐          │
│                  │                                   │ call_sim_rest_    │←─────────┘
│                  │                                   │ server            │
│                  │                                   │ (HTTP POST with   │
│                  │                                   │  RAND, AUTN →     │
│                  │                                   │  RES, CK, IK)     │
│                  │                                   └──────────────────┘
└─────────────────┘
```

## 2.2 parse_401_challenge()

```python
"""
parse_401_challenge: Extract authentication parameters from a SIP 401 Unauthorized response.

Per RFC 3261 / RFC 2617, the 401 response contains a WWW-Authenticate header
with Digest parameters including algorithm, nonce, realm, qop, and opaque.

For IMS AKA, algorithm will be "AKAv1-MD5" or "AKAv2-MD5", and the nonce
contains Base64(RAND || AUTN || server_specific_data) per RFC 3310 Section 3.2.
"""

import re
from typing import Dict, Optional


def parse_401_challenge(sip_response: str) -> Dict[str, str]:
    """
    Parse a SIP 401 Unauthorized response to extract WWW-Authenticate header parameters.

    Args:
        sip_response: The raw SIP 401 response text (including status line and all headers).

    Returns:
        Dictionary with keys: algorithm, nonce, realm, qop, opaque, stale, nc, cnonce_domain
        All values are strings; missing parameters are empty strings.

    Raises:
        ValueError: If the response is not a 401 or lacks WWW-Authenticate header.
    """
    # Verify this is a 401 response
    status_line = sip_response.split("\r\n")[0] if "\r\n" in sip_response else sip_response.split("\n")[0]
    if "401" not in status_line:
        raise ValueError(f"Not a 401 response: {status_line}")

    # Find the WWW-Authenticate header (case-insensitive, may span multiple lines)
    # SIP headers can be folded: continuation lines start with space/tab
    www_auth_match = re.search(
        r"WWW-Authenticate\s*:\s*(.*?)(?=\r\n\S|\n\S|\r\n\r\n|\n\n|$)",
        sip_response,
        re.IGNORECASE | re.DOTALL,
    )
    if not www_auth_match:
        raise ValueError("No WWW-Authenticate header found in 401 response")

    # Unfold header continuation lines
    auth_text = www_auth_match.group(1)
    auth_text = re.sub(r"\r\n[ \t]+", " ", auth_text)
    auth_text = re.sub(r"\n[ \t]+", " ", auth_text)

    # Remove "Digest" prefix if present
    auth_text = re.sub(r"^\s*Digest\s+", "", auth_text, flags=re.IGNORECASE)

    # Parse key=value pairs from the Digest challenge
    # Handles both quoted and unquoted values, and supports:
    #   algorithm=AKAv1-MD5        (unquoted)
    #   nonce="base64string=="     (quoted)
    #   qop="auth"                 (quoted)
    params: Dict[str, str] = {
        "algorithm": "",
        "nonce": "",
        "realm": "",
        "qop": "",
        "opaque": "",
        "stale": "",
    }

    # Regex for Digest auth parameters: key=quoted or key=unquoted-token
    # Match quoted: key="value"  (value may contain escaped quotes, but typically doesn't)
    # Match unquoted: key=value  (value is a token without spaces/commas)
    for match in re.finditer(
        r'(\w+)\s*=\s*(?:"([^"]*?)"|([^\s,]+))', auth_text
    ):
        key = match.group(1).lower()
        value = match.group(2) if match.group(2) is not None else match.group(3)
        if key in params:
            params[key] = value
        # Also store unknown keys as-is
        params.setdefault(key, value)

    # Validate required fields
    if not params["nonce"]:
        raise ValueError("WWW-Authenticate header missing 'nonce' parameter")
    if not params["realm"]:
        raise ValueError("WWW-Authenticate header missing 'realm' parameter")
    if not params["algorithm"]:
        # Default to AKAv1-MD5 for IMS, but warn
        params["algorithm"] = "AKAv1-MD5"

    return params
```

## 2.3 decode_aka_nonce()

```python
"""
decode_aka_nonce: Decode the Base64-encoded AKA nonce per RFC 3310 Section 3.2.

RFC 3310 Section 3.2 defines the nonce format for AKA digest authentication:
  nonce = Base64(RAND || AUTN || <server specific data>)

Where:
  - RAND: 16 bytes (random challenge from HSS/AuC)
  - AUTN: 16 bytes (authentication token, includes SQN||AMF||MAC)
  - Server specific data: variable length (opaque to client)

The nonce may also include additional fields per some implementations:
  - Some carriers include a MAC over the nonce for integrity
  - Some include SQN or AMF separately

The client MUST extract exactly the first 32 bytes (16 RAND + 16 AUTN)
and pass them to the SIM card for ISIM AKA authentication.
"""

import base64
from typing import Dict, Optional


def decode_aka_nonce(base64_nonce: str) -> Dict[str, bytes]:
    """
    Decode the Base64-encoded AKA nonce to extract RAND, AUTN, and any server data.

    Per RFC 3310 Section 3.2:
        nonce = Base64(RAND || AUTN || server_specific_data)

    Args:
        base64_nonce: The Base64-encoded nonce string from the WWW-Authenticate header.
                      May contain '=' padding. Some implementations omit padding.

    Returns:
        Dictionary with keys:
            'rand':  16 bytes - the random challenge (RAND)
            'autn':  16 bytes - the authentication token (AUTN)
            'server_data': remaining bytes - server-specific data (if any)
            'rand_hex': hex string of RAND
            'autn_hex': hex string of AUTN

    Raises:
        ValueError: If the nonce cannot be decoded or is too short.
    """
    if not base64_nonce:
        raise ValueError("Empty nonce string")

    # Fix Base64 padding if needed
    # Some carriers send nonce without proper '=' padding
    padding_needed = len(base64_nonce) % 4
    if padding_needed:
        base64_nonce += "=" * (4 - padding_needed)

    try:
        nonce_bytes = base64.b64decode(base64_nonce)
    except Exception as e:
        raise ValueError(f"Failed to Base64-decode nonce: {e}")

    if len(nonce_bytes) < 32:
        raise ValueError(
            f"Nonce too short: {len(nonce_bytes)} bytes, need at least 32 "
            f"(16 RAND + 16 AUTN). Decoded hex: {nonce_bytes.hex()}"
        )

    rand = nonce_bytes[0:16]
    autn = nonce_bytes[16:32]
    server_data = nonce_bytes[32:]  # May be empty

    # AUTN structure per TS 33.102 Section 6.3.3:
    # AUTN = SQN ⊕ AK || AMF || MAC
    # Where:
    #   SQN ⊕ AK: 6 bytes (sequence number XOR anonymity key)
    #   AMF:      2 bytes (authentication management field)
    #   MAC:     8 bytes (message authentication code)
    # We don't split these here — the SIM card handles MAC verification internally.

    return {
        "rand": rand,
        "autn": autn,
        "server_data": server_data,
        "rand_hex": rand.hex(),
        "autn_hex": autn.hex(),
    }
```

## 2.4 call_sim_rest_server()

```python
"""
call_sim_rest_server: Send RAND+AUTN to pySim's sim-rest-server for ISIM AKA authentication.

The sim-rest-server exposes a REST API at:
  POST /sim-auth-api/v1/slot/<SLOT_NR>
  Body: {"rand": "<hex>", "autn": "<hex>"}
  Response (success): {"successful_3g_authentication": {"res": "<hex>", "ck": "<hex>", "ik": "<hex>", "kc": "<hex>"}}
  Response (sync failure): {"synchronisation_failure": {"auts": "<hex>"}}

IMPORTANT: The default sim-rest-server hardcodes ADF.USIM selection.
For IMS AKA, you MUST patch it to select ADF.ISIM (AID=A0000000871004).
See pysim-sim-auth-rest-audit-report.md Section 6.3 for the patch.
"""

import requests
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SimAuthError(Exception):
    """Base exception for SIM authentication errors."""
    pass


class SimSyncFailure(SimAuthError):
    """SQN synchronisation failure — the SIM returned AUTS instead of RES."""

    def __init__(self, auts_hex: str):
        self.auts_hex = auts_hex
        super().__init__(
            f"SIM SQN synchronisation failure. AUTS={auts_hex}. "
            f"The client must re-REGISTER with AUTS to trigger HSS re-sync."
        )


class SimAuthRejected(SimAuthError):
    """SIM rejected authentication (e.g., MAC mismatch, PIN not verified)."""
    pass


def call_sim_rest_server(
    rand_hex: str,
    autn_hex: str,
    slot: int = 0,
    base_url: str = "http://localhost:8000",
    timeout: float = 10.0,
    app: str = "isim",
) -> Dict[str, str]:
    """
    Perform ISIM AKA authentication via pySim's sim-rest-server.

    Sends RAND and AUTN to the REST API, which forwards them to the physical
    SIM card's ISIM application. The SIM computes RES, CK, IK using its
    secret key K and the MILENAGE algorithm.

    Args:
        rand_hex: Hex string of the RAND (32 hex chars = 16 bytes).
        autn_hex: Hex string of the AUTN (32 hex chars = 16 bytes).
        slot: PC/SC reader slot number (0-based). Default 0.
        base_url: Base URL of the sim-rest-server. Default http://localhost:8000.
        timeout: HTTP request timeout in seconds. Default 10.
        app: SIM application to select: 'isim' (recommended) or 'usim'.
             NOTE: 'isim' requires a patched sim-rest-server. See docs.

    Returns:
        Dictionary with keys:
            'res_hex': Hex string of RES (response)
            'ck_hex':  Hex string of CK  (cipher key, 16 bytes)
            'ik_hex':  Hex string of IK  (integrity key, 16 bytes)
            'kc_hex':  Hex string of Kc  (GSM cipher key, 8 bytes, may be absent for ISIM)

    Raises:
        SimSyncFailure: If the SIM returns AUTS (SQN out of sync with HSS).
        SimAuthRejected: If the SIM rejects the authentication (MAC error, PIN not verified).
        SimAuthError: For other authentication failures.
        requests.RequestException: For HTTP/connection errors.
        ValueError: If the REST API returns an unexpected response format.
    """
    # Validate input lengths
    if len(rand_hex) != 32:
        raise ValueError(f"RAND must be 16 bytes (32 hex chars), got {len(rand_hex)}")
    if len(autn_hex) != 32:
        raise ValueError(f"AUTN must be 16 bytes (32 hex chars), got {len(autn_hex)}")

    url = f"{base_url}/sim-auth-api/v1/slot/{slot}"

    payload = {
        "rand": rand_hex.lower(),
        "autn": autn_hex.lower(),
    }

    # Note: the 'app' parameter requires a patched sim-rest-server
    # that supports application selection. The stock server hardcodes
    # ADF.USIM. If using a stock server with an ISIM, it will still
    # work IF the card's default ADF is ISIM, but this is unlikely.
    if app == "isim":
        payload["app"] = "isim"

    logger.info(f"POST {url} with RAND={rand_hex}, AUTN={autn_hex}, app={app}")

    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except requests.ConnectionError as e:
        raise SimAuthError(
            f"Cannot connect to sim-rest-server at {base_url}. "
            f"Is it running? Error: {e}"
        )
    except requests.Timeout:
        raise SimAuthError(
            f"sim-rest-server request timed out after {timeout}s. "
            f"The SIM card may be slow or the reader disconnected."
        )

    if resp.status_code == 404:
        raise SimAuthError(f"SIM slot {slot} not found on sim-rest-server.")
    if resp.status_code == 410:
        raise SimAuthError(f"No SIM card inserted in slot {slot}.")
    if resp.status_code != 200:
        raise SimAuthError(
            f"sim-rest-server returned HTTP {resp.status_code}: {resp.text}"
        )

    result = resp.json()

    # Check for synchronisation failure (AUTS)
    if "synchronisation_failure" in result:
        auts = result["synchronisation_failure"]["auts"]
        logger.warning(f"SIM synchronisation failure: AUTS={auts}")
        raise SimSyncFailure(auts)

    # Check for successful authentication
    if "successful_3g_authentication" in result:
        auth = result["successful_3g_authentication"]
        logger.info(
            f"ISIM AKA auth success: RES={auth.get('res', 'N/A')[:8]}..., "
            f"CK={auth.get('ck', 'N/A')[:8]}..., IK={auth.get('ik', 'N/A')[:8]}..."
        )
        return {
            "res_hex": auth["res"],
            "ck_hex": auth["ck"],
            "ik_hex": auth["ik"],
            "kc_hex": auth.get("kc", ""),  # Kc may be absent for ISIM
        }

    # Unknown response format
    raise SimAuthError(f"Unexpected sim-rest-server response: {result}")
```

## 2.5 compute_aka_digest_response()

```python
"""
compute_aka_digest_response: Compute the AKAv1-MD5 digest response per RFC 3310 / RFC 2617.

RFC 3310 defines how AKA is integrated with HTTP Digest authentication for SIP.
The key difference from regular Digest is that the "password" is replaced by
the AKA RES (response) value.

AKAv1-MD5 Computation (RFC 3310 Section 3.3 + RFC 2617):

  H(A1) = MD5( username ":" realm ":" RES_hex_string )
  H(A2) = MD5( Method ":" digest_uri )

  Without qop:
    response = MD5( H(A1) ":" nonce ":" H(A2) )

  With qop="auth":
    response = MD5( H(A1) ":" nonce ":" nc ":" cnonce ":" qop ":" H(A2) )

CRITICAL NOTES:
  1. RES is used as its HEX STRING representation (ASCII) in H(A1), NOT raw binary.
     This is per 3GPP TS 33.203 and confirmed by practical testing.
  2. The nonce in the response calculation is the ORIGINAL Base64 nonce string
     from the server — do NOT decode it or strip '=' padding.
  3. Username is the IMPI (IMS Private Identity, NAI format).
  4. digest_uri is typically "sip:<home_domain>".
"""

import hashlib
import os
from typing import Tuple, Optional


def compute_aka_digest_response(
    impi: str,
    realm: str,
    res_hex: str,
    digest_uri: str,
    nonce_b64: str,
    algorithm: str = "AKAv1-MD5",
    qop: Optional[str] = None,
    nc: str = "00000001",
    cnonce: Optional[str] = None,
    ck_hex: Optional[str] = None,
    ik_hex: Optional[str] = None,
) -> Tuple[str, str, str]:
    """
    Compute the SIP Digest AKA response per RFC 3310 / RFC 2617.

    Args:
        impi: IMS Private User Identity (NAI format, e.g. "user@ims.mnc001.mcc001.3gppnetwork.org").
        realm: Authentication realm from the 401 challenge.
        res_hex: Hex string of RES from SIM authentication (used as "password").
        digest_uri: The SIP URI for the Authorization header (e.g. "sip:ims.mnc001.mcc001.3gppnetwork.org").
        nonce_b64: The Base64-encoded nonce string from the 401 challenge (preserved exactly as-is).
        algorithm: "AKAv1-MD5" (default) or "AKAv2-MD5".
        qop: Quality of protection from the 401 challenge ("auth" or None).
        nc: Nonce count (8 hex digits). Default "00000001".
        cnonce: Client nonce (hex string). Generated randomly if not provided.
        ck_hex: Cipher Key hex (16 bytes). Required for AKAv2-MD5.
        ik_hex: Integrity Key hex (16 bytes). Required for AKAv2-MD5.

    Returns:
        Tuple of (response, cnonce, nc):
            response: 32-char lowercase hex MD5 digest (the Authorization "response" value)
            cnonce:   The client nonce used (for inclusion in Authorization header)
            nc:       The nonce count used

    Raises:
        ValueError: If required parameters are missing for the algorithm variant.
    """
    if cnonce is None:
        cnonce = os.urandom(8).hex()  # 16 hex chars

    # ── Stage 1: Compute H(A1) ──
    # For AKAv1-MD5 (RFC 3310):
    #   H(A1) = MD5( username ":" realm ":" RES_hex_string )
    #
    # RES is treated as the "password" — its hex ASCII string representation
    # is used, NOT the raw binary bytes. This is a common source of bugs.
    #
    # For AKAv2-MD5 (RFC 4169):
    #   H(A1_base) = MD5( username ":" realm ":" RES_hex_string )
    #   H(A1) = MD5( H(A1_base) ":" CK_hex ":" IK_hex )

    if algorithm.upper() in ("AKAV1-MD5", "AKAV1-MD5-SESS"):
        # AKAv1-MD5: RES hex string is the "password"
        a1_input = f"{impi}:{realm}:{res_hex}"
        ha1 = hashlib.md5(a1_input.encode("ascii")).hexdigest()

    elif algorithm.upper() in ("AKAV2-MD5", "AKAV2-MD5-SESS"):
        # AKAv2-MD5: H(A1) = MD5( MD5(user:realm:RES) ":" CK ":" IK )
        if not ck_hex or not ik_hex:
            raise ValueError("AKAv2-MD5 requires CK and IK parameters")

        a1_base = hashlib.md5(f"{impi}:{realm}:{res_hex}".encode("ascii")).hexdigest()
        a1_input = f"{a1_base}:{ck_hex}:{ik_hex}"
        ha1 = hashlib.md5(a1_input.encode("ascii")).hexdigest()

    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}. Use AKAv1-MD5 or AKAv2-MD5.")

    # ── Stage 2: Compute H(A2) ──
    # H(A2) = MD5( "REGISTER" ":" digest_uri )
    # For SIP REGISTER, the method is always "REGISTER"
    a2_input = f"REGISTER:{digest_uri}"
    ha2 = hashlib.md5(a2_input.encode("ascii")).hexdigest()

    # ── Stage 3: Compute final response ──
    if qop and qop.lower().startswith("auth"):
        # With qop="auth" (or "auth-int"):
        # response = MD5( H(A1) ":" nonce ":" nc ":" cnonce ":" qop ":" H(A2) )
        response_input = f"{ha1}:{nonce_b64}:{nc}:{cnonce}:{qop}:{ha2}"
    else:
        # Without qop (legacy / simplified):
        # response = MD5( H(A1) ":" nonce ":" H(A2) )
        response_input = f"{ha1}:{nonce_b64}:{ha2}"

    response = hashlib.md5(response_input.encode("ascii")).hexdigest()

    return response, cnonce, nc
```

## 2.6 build_sip_register()

```python
"""
build_sip_register: Construct a SIP REGISTER packet with AKA-Digest Authorization header.

This builds a complete SIP REGISTER message suitable for sending via UDP socket
to a P-CSCF. It includes the Authorization header with the computed AKA-Digest
response, all required SIP headers, and IMS-specific feature tags.
"""

import os
import time
from typing import Optional


def build_sip_register(
    impi: str,
    impu: str,
    pcscf_domain: str,
    realm: str,
    nonce_b64: str,
    response: str,
    cseq: int = 2,
    algorithm: str = "AKAv1-MD5",
    qop: Optional[str] = None,
    nc: str = "00000001",
    cnonce: Optional[str] = None,
    opaque: Optional[str] = None,
    local_ip: str = "192.168.1.100",
    local_port: int = 5060,
    branch: Optional[str] = None,
    call_id: Optional[str] = None,
    tag: Optional[str] = None,
    expires: int = 600000,
    instance_id: Optional[str] = None,
    feature_tags: Optional[list] = None,
    security_client: bool = True,
    digest_uri: Optional[str] = None,
) -> str:
    """
    Construct a SIP REGISTER packet with AKA-Digest Authorization header.

    Args:
        impi: IMS Private User Identity (NAI, e.g. "user@domain").
        impu: IMS Public User Identity (SIP URI, e.g. "sip:user@domain").
        pcscf_domain: Home network domain (used in Request-URI and Via).
        realm: Authentication realm from 401 challenge.
        nonce_b64: Base64-encoded nonce from 401 challenge.
        response: Computed AKA-Digest response (32-char hex).
        cseq: CSeq number. Use 1 for initial, 2+ after 401 challenge. Default 2.
        algorithm: Algorithm from 401 challenge. Default "AKAv1-MD5".
        qop: Quality of protection ("auth" or None).
        nc: Nonce count (8 hex digits). Default "00000001".
        cnonce: Client nonce (hex string). Generated if not provided.
        opaque: Opaque value from 401 challenge (echoed back).
        local_ip: Local IP address for Via/Contact. Default "192.168.1.100".
        local_port: Local SIP port. Default 5060.
        branch: Via branch parameter. Generated if not provided.
        call_id: Call-ID header value. Generated if not provided.
        tag: From tag. Generated if not provided.
        expires: Registration expiry in seconds. Default 600000.
        instance_id: +sip.instance GRUU identifier.
        feature_tags: List of feature tag strings for Contact header.
        security_client: Whether to include Security-Client header. Default True.
        digest_uri: The URI for Authorization header. Defaults to "sip:<pcscf_domain>".

    Returns:
        Complete SIP REGISTER message as a string, ready to send via UDP socket.
    """
    if branch is None:
        branch = f"z9hG4bK{os.urandom(6).hex()}"
    if call_id is None:
        call_id = f"{os.urandom(4).hex()}@{local_ip}"
    if tag is None:
        tag = f"{int(time.time())}"
    if cnonce is None:
        cnonce = os.urandom(8).hex()
    if digest_uri is None:
        digest_uri = f"sip:{pcscf_domain}"

    # Extract the user part from IMPI (before @)
    impi_user = impi.split("@")[0] if "@" in impi else impi

    # ── Build Authorization header ──
    auth_parts = [
        f'Digest username="{impi}"',
        f'realm="{realm}"',
        f'nonce="{nonce_b64}"',
        f'uri="{digest_uri}"',
        f'response="{response}"',
        f"algorithm={algorithm}",  # algorithm is NOT quoted per RFC 2617
    ]
    if opaque:
        auth_parts.append(f'opaque="{opaque}"')
    if qop and qop.lower().startswith("auth"):
        auth_parts.append(f"qop={qop}")
        auth_parts.append(f"nc={nc}")
        auth_parts.append(f'cnonce="{cnonce}"')

    auth_header = ", ".join(auth_parts)

    # ── Build Contact header with feature tags ──
    contact_params = []
    if instance_id:
        contact_params.append(f'+sip.instance="<{instance_id}>"')

    # Default IMS feature tags for RCS
    if feature_tags is None:
        feature_tags = [
            '+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.msg"',
            '+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.session"',
        ]
    contact_params.extend(feature_tags)

    contact_suffix = ";".join(contact_params)
    contact = f"<sip:{impi_user}@{local_ip}:{local_port}>;{contact_suffix}"

    # ── Build Security-Client header (IPSec negotiation) ──
    security_header = ""
    if security_client:
        # Per TS 33.203, the UE proposes security algorithms
        # alg=hmac-md5-96; ealg=aes-cbc; prot=esp; mod=trans
        # SPI-C and SPI-S are random values chosen by the client
        spi_c = os.urandom(4).hex()  # 4-byte SPI for client-to-server
        # Note: port-c and port-s are the protected port pairs
        # The P-CSCF will use the Security-Server header to confirm
        security_header = (
            f"Security-Client: alg=hmac-md5-96; ealg=aes-cbc; "
            f"prot=esp; mod=trans; spi-c={int(spi_c, 16)}; "
            f"port-c={local_port + 1}\r\n"
            f"Require: sec-agree\r\n"
            f"Proxy-Require: sec-agree\r\n"
        )

    # ── Assemble the full SIP REGISTER ──
    register_msg = (
        f"REGISTER sip:{pcscf_domain} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch={branch}\r\n"
        f"Max-Forwards: 70\r\n"
        f"From: <{impu}>;tag={tag}\r\n"
        f"To: <{impu}>\r\n"
        f"Call-ID: {call_id}\r\n"
        f"CSeq: {cseq} REGISTER\r\n"
        f"Contact: {contact}\r\n"
        f"Expires: {expires}\r\n"
        f"Authorization: {auth_header}\r\n"
        f"{security_header}"
        f"Content-Length: 0\r\n"
        f"\r\n"
    )

    return register_msg
```

## 2.7 Full Orchestration

```python
"""
ims_aka_register: Full orchestration function that chains everything together.

This function performs the complete IMS AKA SIP registration flow:
  1. Send initial SIP REGISTER (no auth) → get 401 Unauthorized
  2. Parse the 401 challenge → extract algorithm, nonce, realm
  3. Decode the AKA nonce → extract RAND and AUTN
  4. Call sim-rest-server with RAND/AUTN → get RES, CK, IK
  5. Compute the AKA-Digest response → get the MD5 digest
  6. Build and send authenticated SIP REGISTER → get 200 OK
"""

import socket
import re
import logging
from typing import Dict, Optional, Tuple

# Import the individual functions from this module
# (In practice, these would be in the same file or imported)

logger = logging.getLogger(__name__)


def send_sip_udp(
    message: str,
    dest_ip: str,
    dest_port: int,
    local_ip: str = "0.0.0.0",
    local_port: int = 5060,
    timeout: float = 5.0,
) -> str:
    """
    Send a SIP message via UDP and return the response.

    Args:
        message: The SIP message to send.
        dest_ip: Destination IP address (P-CSCF).
        dest_port: Destination port (usually 5060).
        local_ip: Local IP to bind. Default "0.0.0.0".
        local_port: Local port to bind. Default 5060.
        timeout: Socket receive timeout in seconds. Default 5.

    Returns:
        The raw SIP response text.

    Raises:
        socket.timeout: If no response within timeout.
        ConnectionRefusedError: If the destination is unreachable.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((local_ip, local_port))
        sock.settimeout(timeout)
        sock.sendto(message.encode("utf-8"), (dest_ip, dest_port))
        data, addr = sock.recvfrom(65535)
        return data.decode("utf-8", errors="replace")
    finally:
        sock.close()


def parse_200_ok(response: str) -> Dict:
    """Extract key headers from a SIP 200 OK response."""
    result = {"registered": "200 OK" in response}

    # P-Associated-URI
    associated = re.findall(r"P-Associated-URI\s*:\s*<([^>]+)>", response, re.IGNORECASE)
    result["associated_uris"] = associated

    # Service-Route
    routes = re.findall(r"Service-Route\s*:\s*<([^>]+)>", response, re.IGNORECASE)
    result["service_routes"] = routes

    # Expires
    expire_match = re.search(r"expires\s*=\s*(\d+)", response, re.IGNORECASE)
    if expire_match:
        result["expires"] = int(expire_match.group(1))

    # Security-Server (for IPSec SA setup)
    sec_match = re.search(
        r"Security-Server\s*:\s*(.*?)(?:\r\n|\n)", response, re.IGNORECASE
    )
    if sec_match:
        result["security_server"] = sec_match.group(1).strip()

    return result


def build_initial_register(
    impi: str,
    impu: str,
    pcscf_domain: str,
    realm: str,
    local_ip: str = "192.168.1.100",
    local_port: int = 5060,
    instance_id: Optional[str] = None,
    expires: int = 600000,
) -> Tuple[str, str, str, str]:
    """
    Build the initial SIP REGISTER with empty Authorization header.

    Returns:
        Tuple of (register_message, branch, call_id, tag)
    """
    import os
    import time

    branch = f"z9hG4bK{os.urandom(6).hex()}"
    call_id = f"{os.urandom(4).hex()}@{local_ip}"
    tag = f"{int(time.time())}"

    impi_user = impi.split("@")[0] if "@" in impi else impi

    # Feature tags for Contact header
    contact_params = [f'+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.msg"',
                      f'+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.oma.cpm.session"']
    if instance_id:
        contact_params.append(f'+sip.instance="<{instance_id}>"')

    register_msg = (
        f"REGISTER sip:{pcscf_domain} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch={branch}\r\n"
        f"Max-Forwards: 70\r\n"
        f"From: <{impu}>;tag={tag}\r\n"
        f"To: <{impu}>\r\n"
        f"Call-ID: {call_id}\r\n"
        f"CSeq: 1 REGISTER\r\n"
        f"Contact: <sip:{impi_user}@{local_ip}:{local_port}>;{';'.join(contact_params)}\r\n"
        f"Expires: {expires}\r\n"
        f"Authorization: Digest username=\"{impi}\", realm=\"{realm}\", "
        f"nonce=\"\", uri=\"sip:{pcscf_domain}\", response=\"\"\r\n"
        f"Content-Length: 0\r\n"
        f"\r\n"
    )

    return register_msg, branch, call_id, tag


def ims_aka_register(
    impi: str,
    impu: str,
    pcscf_addr: str,
    pcscf_port: int = 5060,
    pcscf_domain: Optional[str] = None,
    sim_rest_url: str = "http://localhost:8000",
    sim_slot: int = 0,
    local_ip: str = "192.168.1.100",
    local_port: int = 5060,
    instance_id: Optional[str] = None,
    expires: int = 600000,
    max_401_retries: int = 3,
    udp_timeout: float = 5.0,
) -> Dict:
    """
    Full IMS AKA SIP registration orchestration.

    This function performs the complete 2-step IMS registration:
      Step 1: Send initial REGISTER → receive 401 with AKA challenge
      Step 2: Process challenge via SIM → send authenticated REGISTER → receive 200 OK

    Args:
        impi: IMS Private User Identity (NAI format).
        impu: IMS Public User Identity (SIP URI).
        pcscf_addr: P-CSCF IP address or FQDN.
        pcscf_port: P-CSCF port. Default 5060.
        pcscf_domain: Home network domain for Request-URI. Defaults to IMPI domain.
        sim_rest_url: Base URL of sim-rest-server. Default http://localhost:8000.
        sim_slot: SIM card slot number. Default 0.
        local_ip: Local IP for SIP signaling. Default 192.168.1.100.
        local_port: Local SIP port. Default 5060.
        instance_id: GRUU instance ID (IMEI-based URN).
        expires: Registration expiry in seconds. Default 600000.
        max_401_retries: Max 401 retry attempts. Default 3.
        udp_timeout: SIP UDP timeout in seconds. Default 5.0.

    Returns:
        Dictionary with registration result including:
            'registered': bool
            'associated_uris': list of URIs from 200 OK
            'service_routes': list of Service-Route paths
            'expires': registration expiry in seconds

    Raises:
        SimSyncFailure: If SIM returns AUTS (SQN sync failure).
        SimAuthError: If SIM authentication fails.
        ValueError: If the 401 challenge is malformed.
        RuntimeError: If registration fails after max retries.
    """
    if pcscf_domain is None:
        pcscf_domain = impi.split("@")[1] if "@" in impi else pcscf_addr

    # ── Step 1: Send initial REGISTER ──
    logger.info(f"Step 1: Sending initial REGISTER to {pcscf_addr}:{pcscf_port}")

    register_msg, branch, call_id, tag = build_initial_register(
        impi=impi,
        impu=impu,
        pcscf_domain=pcscf_domain,
        realm=pcscf_domain,  # Use domain as initial realm
        local_ip=local_ip,
        local_port=local_port,
        instance_id=instance_id,
        expires=expires,
    )

    response = send_sip_udp(
        register_msg, pcscf_addr, pcscf_port, local_ip, local_port, udp_timeout
    )

    # Check for 401 Unauthorized
    if "401" not in response and "407" not in response:
        status_line = response.split("\r\n")[0]
        if "200" in status_line:
            logger.warning("Received 200 OK without 401 challenge — already registered?")
            return parse_200_ok(response)
        raise RuntimeError(
            f"Expected 401 Unauthorized, got: {status_line}"
        )

    logger.info("Step 1 complete: Received 401 Unauthorized with AKA challenge")

    # ── Step 2: Parse the 401 challenge ──
    logger.info("Step 2: Parsing 401 challenge")
    challenge = parse_401_challenge(response)
    algorithm = challenge["algorithm"]
    nonce_b64 = challenge["nonce"]
    realm = challenge["realm"]
    qop = challenge.get("qop")
    opaque = challenge.get("opaque", "")

    logger.info(f"  Algorithm: {algorithm}")
    logger.info(f"  Realm: {realm}")
    logger.info(f"  Nonce (b64): {nonce_b64[:40]}...")

    # ── Step 3: Decode the AKA nonce ──
    logger.info("Step 3: Decoding AKA nonce → RAND + AUTN")
    aka_nonce = decode_aka_nonce(nonce_b64)
    rand_hex = aka_nonce["rand_hex"]
    autn_hex = aka_nonce["autn_hex"]

    logger.info(f"  RAND: {rand_hex}")
    logger.info(f"  AUTN: {autn_hex}")

    # ── Step 4: Call sim-rest-server for ISIM AKA auth ──
    logger.info(f"Step 4: Calling sim-rest-server (slot={sim_slot})")
    sim_result = call_sim_rest_server(
        rand_hex=rand_hex,
        autn_hex=autn_hex,
        slot=sim_slot,
        base_url=sim_rest_url,
    )
    res_hex = sim_result["res_hex"]
    ck_hex = sim_result["ck_hex"]
    ik_hex = sim_result["ik_hex"]

    logger.info(f"  RES: {res_hex}")
    logger.info(f"  CK:  {ck_hex}")
    logger.info(f"  IK:  {ik_hex}")

    # ── Step 5: Compute AKA-Digest response ──
    logger.info("Step 5: Computing AKA-Digest response")
    digest_uri = f"sip:{pcscf_domain}"

    response_digest, cnonce, nc = compute_aka_digest_response(
        impi=impi,
        realm=realm,
        res_hex=res_hex,
        digest_uri=digest_uri,
        nonce_b64=nonce_b64,
        algorithm=algorithm,
        qop=qop,
        ck_hex=ck_hex if "AKAv2" in algorithm.upper() else None,
        ik_hex=ik_hex if "AKAv2" in algorithm.upper() else None,
    )

    logger.info(f"  Digest response: {response_digest}")

    # ── Step 6: Build and send authenticated REGISTER ──
    logger.info("Step 6: Sending authenticated REGISTER")

    auth_register = build_sip_register(
        impi=impi,
        impu=impu,
        pcscf_domain=pcscf_domain,
        realm=realm,
        nonce_b64=nonce_b64,
        response=response_digest,
        cseq=2,  # CSeq incremented after 401
        algorithm=algorithm,
        qop=qop,
        nc=nc,
        cnonce=cnonce,
        opaque=opaque if opaque else None,
        local_ip=local_ip,
        local_port=local_port,
        call_id=call_id,
        tag=tag,
        expires=expires,
        instance_id=instance_id,
        digest_uri=digest_uri,
    )

    # Use a different local port for the second REGISTER (some P-CSCFs require this)
    response = send_sip_udp(
        auth_register, pcscf_addr, pcscf_port, local_ip, local_port + 1, udp_timeout
    )

    # ── Step 7: Process the response ──
    if "200 OK" in response:
        logger.info("Step 7: IMS Registration successful! ✅")
        result = parse_200_ok(response)
        result["ck_hex"] = ck_hex  # Save for IPSec SA setup
        result["ik_hex"] = ik_hex
        return result
    elif "401" in response:
        logger.error("Step 7: Received another 401 — AKA-Digest computation may be wrong ❌")
        # Could retry with new challenge
        raise RuntimeError(
            "Received 401 after authenticated REGISTER. "
            "Possible causes: wrong RES encoding in H(A1), wrong algorithm, "
            "realm mismatch, or nonce expired."
        )
    elif "403" in response:
        logger.error("Step 7: 403 Forbidden — not authorized for IMS ❌")
        raise RuntimeError("403 Forbidden: subscriber not authorized for IMS services")
    else:
        status_line = response.split("\r\n")[0]
        logger.error(f"Step 7: Unexpected response: {status_line} ❌")
        raise RuntimeError(f"Registration failed: {status_line}")


# ═══════════════════════════════════════════════════════════════════
# SQN Synchronisation Failure Handler
# ═══════════════════════════════════════════════════════════════════

def build_auts_register(
    impi: str,
    impu: str,
    pcscf_domain: str,
    realm: str,
    nonce_b64: str,
    auts_hex: str,
    opaque: Optional[str] = None,
    local_ip: str = "192.168.1.100",
    local_port: int = 5060,
    call_id: Optional[str] = None,
    tag: Optional[str] = None,
    cseq: int = 2,
    algorithm: str = "AKAv1-MD5",
) -> str:
    """
    Build a SIP REGISTER with AUTS parameter for SQN re-synchronisation.

    When the SIM returns AUTS (synchronisation failure), the client must
    send a REGISTER with the AUTS value instead of a response. The S-CSCF
    forwards AUTS to the HSS, which re-synchronizes its SQN counter and
    generates a fresh RAND/AUTN pair. The client then receives a new 401
    with the fresh challenge and retries the full AKA flow.

    Args:
        impi: IMS Private User Identity.
        impu: IMS Public User Identity.
        pcscf_domain: Home network domain.
        realm: Authentication realm.
        nonce_b64: The nonce from the original 401 challenge.
        auts_hex: AUTS hex string from SIM (14 bytes = 28 hex chars).
        opaque: Opaque value from the 401 challenge.
        local_ip: Local IP address.
        local_port: Local SIP port.
        call_id: Call-ID from the original registration attempt.
        tag: From tag from the original registration attempt.
        cseq: CSeq number.
        algorithm: Algorithm from the original 401 challenge.

    Returns:
        SIP REGISTER message with AUTS parameter.
    """
    import os

    branch = f"z9hG4bK-auts-{os.urandom(4).hex()}"
    impi_user = impi.split("@")[0] if "@" in impi else impi

    # Build Authorization header with AUTS instead of response
    auth_parts = [
        f'Digest username="{impi}"',
        f'realm="{realm}"',
        f'nonce="{nonce_b64}"',
        f'uri="sip:{pcscf_domain}"',
        f'auts="{auts_hex}"',
        f"algorithm={algorithm}",
    ]
    if opaque:
        auth_parts.append(f'opaque="{opaque}"')

    auth_header = ", ".join(auth_parts)

    register_msg = (
        f"REGISTER sip:{pcscf_domain} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch={branch}\r\n"
        f"Max-Forwards: 70\r\n"
        f"From: <{impu}>;tag={tag}\r\n"
        f"To: <{impu}>\r\n"
        f"Call-ID: {call_id}\r\n"
        f"CSeq: {cseq} REGISTER\r\n"
        f"Contact: <sip:{impi_user}@{local_ip}:{local_port}>\r\n"
        f"Authorization: {auth_header}\r\n"
        f"Content-Length: 0\r\n"
        f"\r\n"
    )

    return register_msg
```

## 2.8 AKAv2-MD5 Support

The `compute_aka_digest_response()` function already supports AKAv2-MD5 (RFC 4169) when the `algorithm` parameter is set to `"AKAv2-MD5"` and `ck_hex`/`ik_hex` are provided. The difference from AKAv1-MD5:

```
AKAv1-MD5 (RFC 3310):
  H(A1) = MD5( username ":" realm ":" RES_hex )

AKAv2-MD5 (RFC 4169):
  H(A1_base) = MD5( username ":" realm ":" RES_hex )
  H(A1) = MD5( H(A1_base) ":" CK_hex ":" IK_hex )
```

AKAv2 is used in some 5G IMS deployments and provides stronger key separation by incorporating CK and IK into the digest computation.

---

# Appendix A: Complete Python Module File

To use all the functions above as a single importable module, combine them into `ims_aka_glue.py`:

```python
#!/usr/bin/env python3
"""
ims_aka_glue.py — IMS AKA Glue Code: Bridge sim-rest-server → SIP REGISTER

This module provides the complete pipeline for IMS AKA (AKAv1-MD5 / AKAv2-MD5)
SIP registration using a physical SIM card via pySim's sim-rest-server.

Dependencies:
  - requests (pip install requests)
  - Standard library: hashlib, base64, socket, re, os, time, logging

Usage:
  from ims_aka_glue import ims_aka_register

  result = ims_aka_register(
      impi="001010123456789@ims.mnc001.mcc001.3gppnetwork.org",
      impu="sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org",
      pcscf_addr="10.1.1.1",
      pcscf_domain="ims.mnc001.mcc001.3gppnetwork.org",
      sim_rest_url="http://localhost:8000",
  )

References:
  - RFC 3310: AKA for HTTP Digest Authentication
  - RFC 4169: AKAv2-MD5 for HTTP Digest Authentication
  - RFC 2617: HTTP Authentication: Basic and Digest
  - 3GPP TS 33.203: IMS Security
  - 3GPP TS 31.103: ISIM Characteristics
  - pySim sim-rest-server: https://downloads.osmocom.org/docs/pysim/master/html/sim-rest.html
"""

# All functions from sections 2.2–2.7 are combined here.
# See the individual sections above for the complete implementation.
# The module exports:
#   - parse_401_challenge(sip_response) → dict
#   - decode_aka_nonce(base64_nonce) → dict
#   - call_sim_rest_server(rand_hex, autn_hex, ...) → dict
#   - compute_aka_digest_response(impi, realm, res_hex, ...) → (response, cnonce, nc)
#   - build_sip_register(impi, impu, pcscf_domain, ...) → str
#   - ims_aka_register(impi, impu, pcscf_addr, ...) → dict  [full orchestration]
#   - build_auts_register(impi, impu, ...) → str  [SQN re-sync]
#   - SimAuthError, SimSyncFailure  [custom exceptions]
```

---

# Appendix B: RCSJTA → AKA Integration Path

To add AKA support to rcsjta, the following changes would be needed:

### 1. New Class: `AkaRegistrationProcedure.java`

```java
// Path: core/src/com/gsma/rcs/core/ims/network/registration/AkaRegistrationProcedure.java
// Extends RegistrationProcedure
//
// init():         No-op (ISIM credentials are on the SIM)
// getHomeDomain(): From ISIM EF.DOMAIN or IMPI domain
// getPublicUri():  From ISIM EF.IMPU
// writeSecurityHeader():
//   - First REGISTER: empty Authorization header (like Digest)
//   - After 401: decode nonce → extract RAND/AUTN → send to ISIM via
//     TelephonyManager.getIccAuthentication() → compute AKA-Digest response
//     → write full Authorization header with algorithm=AKAv1-MD5
// readSecurityHeader():
//   - From 401: read WWW-Authenticate → extract nonce, realm, algorithm, qop, opaque
//   - From 200 OK: read Authentication-Info → nextnonce
```

### 2. Android ISIM Access via TelephonyManager

```java
// Android 5+ API for ISIM AKA:
TelephonyManager tm = TelephonyManager.getDefault();
// appType = UICC_APP_TYPE_ISIM (3)
// authType = AUTHTYPE_EAP_SIM (1) or AUTHTYPE_EAP_AKA (2)
String base64Challenge = Base64.encodeToString(concat(rand, autn), Base64.NO_WRAP);
String base64Result = tm.getIccAuthentication(
    TelephonyManager.UICC_APP_TYPE_ISIM,
    TelephonyManager.AUTHTYPE_EAP_AKA,
    base64Challenge
);
// Parse base64Result → RES + CK + IK
```

### 3. Settings Changes

```java
// Add to RcsSettingsData.AuthenticationProcedure enum:
//   AKA  (new value for AuthType="AKA" from ACS XML)

// Add to ProvisioningParser.parseAppAuthent():
//   case "AKA":
//   case "AKAv1-MD5":
//     mRcsSettings.setAuthenticationProcedure(AuthenticationProcedure.AKA);
//     break;
```

### 4. Security-Client/Server for IPSec

After successful AKA registration, CK and IK are used to establish IPSec Security Associations between the UE and P-CSCF. This requires:
- `Security-Client` header in REGISTER (proposing algorithms and SPI values)
- `Security-Server` header in 200 OK (confirming algorithms and SPI values)
- Linux `ip xfrm` commands or `strongSwan` to establish the actual IPSec tunnel

---

# Appendix C: Common AKA-Digest Pitfalls

| Pitfall | Wrong Approach | Correct Approach |
|---------|---------------|-----------------|
| RES in H(A1) | Using raw binary RES bytes | Using hex ASCII string of RES |
| Username | Using IMPU (sip:user@domain) | Using IMPI (user@domain, NAI without sip: prefix) |
| Nonce encoding | Decoding Base64 nonce, stripping padding | Preserving the Base64 nonce string exactly as received |
| Algorithm string | Writing `algorithm="AKAv1-MD5"` (quoted) | Writing `algorithm=AKAv1-MD5` (unquoted per RFC 2617) |
| Digest URI | Using the P-CSCF address | Using `sip:<home_domain>` (from Request-URI) |
| qop absent | Including nc/cnonce when no qop | Omitting nc/cnonce if qop is not present |
| Realm mismatch | Using a different realm in H(A1) vs 401 | Must match the realm from the 401 challenge exactly |
| AKAv2 keys | Using raw CK/IK bytes | Using hex string of CK/IK concatenated with colon separator |
| CSeq after 401 | Reusing CSeq=1 | Incrementing to CSeq=2 after the 401 challenge |
| Call-ID after 401 | Generating new Call-ID | Reusing the same Call-ID from the initial REGISTER |
