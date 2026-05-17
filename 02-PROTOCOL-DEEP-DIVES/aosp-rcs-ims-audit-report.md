# AOSP IMS/RCS Implementation Audit Report

## 1. ImsService API Surface for RCS

### Core Architecture
The ImsService API is an **Android System API** (not public SDK), defined in `android.telephony.ims.ImsService`. It is implemented as a bound Android Service that the telephony framework discovers and binds to via the intent filter `android.telephony.ims.ImsService`.

**Key Classes:**

| Class | Type | Purpose |
|---|---|---|
| `ImsService` | System API | Base service class; framework binds to it |
| `RcsFeature` | System API | RCS feature implementation within ImsService |
| `MmTelFeature` | System API | MMTEL (VoLTE/VoWiFi/emergency calling) feature |
| `ImsRcsManager` | **Public SDK** (API 30+) | App-facing manager for RCS operations |
| `SipDelegateManager` | System API | Manages SIP delegate creation for single registration |
| `RcsUceAdapter` | Public SDK | User Capability Exchange (UCE) operations |
| `ProvisioningManager` | Public SDK | Get/set IMS provisioning status |
| `ImsManager` | Public SDK | Entry point to get ImsRcsManager, ImsMmTelManager |

### ImsService Registration with Framework
The ImsService registers via AndroidManifest.xml:
```xml
<service android:name="com.egcorp.ims.EgImsService"
         android:permission="android.permission.BIND_IMS_SERVICE">
    <intent-filter>
        <action android:name="android.telephony.ims.ImsService" />
    </intent-filter>
</service>
```

Two types of ImsService binding:
1. **Carrier "override" ImsService** — Preloaded on device, configured via CarrierConfig keys `KEY_MMTEL_IMS_SERVICE_OVERRIDE_PKG` and `KEY_RCS_IMS_SERVICE_OVERRIDE_PKG`
2. **Device "default" ImsService** — The default ImsService loaded via `config_ims_package` resource overlay; used when no carrier-specific ImsService is available

**Critical:** Android does **not** support third-party downloadable ImsService apps. ImsService implementations must be preloaded as system apps or privileged apps.

### Feature Discovery Flow
1. Framework binds to ImsService
2. Calls `ImsService.querySupportedImsFeatures()` to discover capabilities
3. Calls `ImsService.createMmTelFeature()` and/or `ImsService.createRcsFeature()` for each supported feature
4. ImsService can signal feature changes via `ImsService.onUpdateSupportedImsFeatures()`

### RcsFeature Capabilities
The RcsFeature supports capability exchange in two modes:
- **CAPABILITY_TYPE_OPTIONS_UCE** — SIP OPTIONS-based capability discovery
- **CAPABILITY_TYPE_PRESENCE_UCE** — Presence server-based capability discovery

---

## 2. ImsRcsManager Public API (Android 11+, API 30+)

Created via `ImsManager.getImsRcsManager(int subscriptionId)`.

| Method | Permission | Description |
|---|---|---|
| `registerImsRegistrationCallback(Executor, RegistrationCallback)` | READ_PRECISE_PHONE_STATE or carrier privs | Listen for IMS registration state changes |
| `unregisterImsRegistrationCallback(RegistrationCallback)` | Same | Remove registration callback |
| `getRegistrationState(Executor, Consumer<Integer>)` | READ_PRECISE_PHONE_STATE or carrier privs | Query current registration state (NOT_REGISTERED, REGISTERING, REGISTERED) |
| `getRegistrationTransportType(Executor, Consumer<Integer>)` | READ_PRECISE_PHONE_STATE or carrier privs | Get transport type (WWAN, WLAN, INVALID) |
| `registerImsStateCallback(Executor, ImsStateCallback)` | READ_PRECISE_PHONE_STATE or READ_PRIVILEGED_PHONE_STATE or ACCESS_RCS_USER_CAPABILITY_EXCHANGE | Monitor ImsService availability |
| `unregisterImsStateCallback(ImsStateCallback)` | None | Remove state callback |
| `getUceAdapter()` | None | Get RcsUceAdapter for UCE operations |
| `addOnAvailabilityChangedListener(Executor, OnAvailabilityChangedListener)` | System API, READ_PRIVILEGED_PHONE_STATE | Listen for RCS capability availability changes |
| `isCapable(int, int)` | System API, READ_PRIVILEGED_PHONE_STATE | Check if RCS capability is currently capable |
| `isAvailable(int, int)` | System API, READ_PRIVILEGED_PHONE_STATE | Check if RCS capability is currently available (registered + service up) |

**What a third-party app can do with ImsRcsManager:**
- ✅ Register for IMS registration state callbacks (with READ_PRECISE_PHONE_STATE)
- ✅ Query registration state and transport type
- ✅ Get UceAdapter for capability exchange queries
- ✅ Monitor ImsService availability
- ❌ **Cannot** directly trigger SIP REGISTER
- ❌ **Cannot** create SipDelegates (requires PERMISSION_IMS_SINGLE_REGISTRATION — System API)
- ❌ **Cannot** modify provisioning state (requires carrier privileges)
- ❌ **Cannot** implement a custom ImsService (requires system app preloading)

---

## 3. How Google Messages Hooks into ImsService for RCS Registration

Google Messages (`com.google.android.apps.messaging`) hooks into the IMS/RCS stack through multiple paths:

### Path 1: Carrier Services (Primary, Default)
- Google Messages delegates to **Carrier Services** (`com.google.android.ims`) when available
- Carrier Services acts as the ImsService implementation, providing RcsFeature
- Messages connects to the ImsService via the framework binder interfaces
- Carrier Services handles SIP REGISTER, provisioning, and capability exchange

### Path 2: Built-in RCS Fallback
- When Carrier Services is unavailable, Google Messages uses its own internal RCS implementation
- This is a Google Jibe-based RCS client that handles registration directly
- The `BugleRcsEngine` component in Messages handles the RCS engine lifecycle
- Logs show `RcsEngineImpl[DUAL_REG]` indicating dual registration mode support

### Path 3: SipDelegate (Single Registration)
- On Android 12+ with single registration support, Messages can request a SipDelegate via SipDelegateManager
- This allows Messages to forward SIP traffic through the device's shared IMS registration
- Requires `PERMISSION_IMS_SINGLE_REGISTRATION` (granted to default SMS app)

### Provisioning Flow within Messages
1. `RcsProvisioningManager` attempts to get SIM ID mapping and phone number
2. Checks provisioning status via `ProvisioningManager`
3. If no configuration found, triggers ACS provisioning
4. On entitlement servers (TS.43), performs EAP-AKA authentication
5. Receives configuration XML from carrier/ACS server
6. Applies configuration to the ImsService

---

## 4. The Role of Carrier Services (com.google.android.ims)

### Identity
- **Package:** `com.google.android.ims`
- **Play Store listing:** "Carrier Services provides services to support RCS (Rich Communication Services) messaging in Google's Messages app"
- **Installed as:** System app on stock Android devices (preloaded by OEMs/carriers)

### What It Actually Does
Carrier Services IS Google's proprietary ImsService implementation. Based on the package name (`.ims`) and its behavior:

1. **Implements the full ImsService API** — Registers with the `android.telephony.ims.ImsService` intent, providing both MmTelFeature and RcsFeature
2. **Handles SIP registration** — Performs SIP REGISTER to the carrier's IMS network for both MMTEL and RCS
3. **RCS provisioning** — Fetches RCS provisioning configuration from carrier ACS servers
4. **Capability exchange** — Implements UCE (SIP OPTIONS and/or Presence) for contact capability discovery
5. **SIP transport** — Provides the SIP message transport layer for RCS SIP traffic
6. **Diagnostic data collection** — Collects diagnostic and crash data (per Play Store description)

### Is It a Full ImsService?
**Yes.** Carrier Services implements the complete ImsService interface including:
- MmTelFeature (VoLTE, VoWiFi, emergency calling)
- RcsFeature (RCS registration, provisioning, UCE)
- SipDelegate support (for single registration mode on Android 12+)

### Why It Can't Work on GrapheneOS as a User App
- ImsService implementations must be **system apps** with `BIND_IMS_SERVICE` permission
- Carrier Services requires `READ_PRIVILEGED_PHONE_STATE` and carrier privileges
- It needs to be the **bound ImsService** in the framework, which requires proper intent filter registration
- It depends on GMS/Play Services callbacks for provisioning handshakes
- Without system-level installation, it cannot bind as the device's ImsService

---

## 5. Why RCS Fails Without Play Services (GrapheneOS Analysis)

Based on GrapheneOS issue tracker #6173 and related discussion:

### Root Causes of Failure

**A. Permission Denials:**
```
SecurityException: getPhoneNumberFromFirstAvailableSource: Neither user 10189 nor current process
has android.permission.READ_PHONE_NUMBERS or android.permission.READ_PRIVILEGED_PHONE_STATE
or carrier privileges.
```
- Google Messages and Carrier Services cannot obtain the phone number needed for RCS provisioning
- GrapheneOS's sandboxed Play Services cannot grant `READ_PRIVILEGED_PHONE_STATE`
- Manual AppOps permission grants don't fully resolve this (framework still rejects)

**B. GMS Callback Failures:**
- RCS provisioning is dependent on callbacks from Google Play Services
- `GmsCompat/Hooks` spoofs some permission checks but the underlying binder call fails
- `com.google.android.gms.unstable` process is involved in the callback chain
- When the callback fails, provisioning stalls at "Verifying..." or "Setting up..."

**C. SIM Identity Mapping Failures:**
```
RcsProvisioningManager: getSimIdFromSubId for subId: 1 returned no mapping.
BugleSelfIdentity: Rcs is NOT_AVAILABLE for SelfIdentity. [CONTEXT sub_id=1 rcs_availability="13"]
```
- The provisioning manager cannot map subscription IDs to SIM identifiers
- This prevents establishment of RCS provisioning identities

**D. Carrier-Specific Problems (T-Mobile/AT&T):**
- T-Mobile and AT&T require "privileged access" — a more problematic approach
- These carriers use a different IMS registration model that requires system-level carrier privileges
- GrapheneOS explicitly cannot grant these privileged permissions
- Error code 4006: "Not Supported: Device does not meet security requirements" (attestation failure)

**E. Server-Side Changes (September 2025):**
- Google made service-side changes that broke Google Messages for most GrapheneOS users
- Older versions of Messages also stopped working (not just a client-side issue)
- The Jibe provisioning handshake now requires Carrier Services background activity
- GrapheneOS blocks Carrier Services from constant background calling home

### Current GrapheneOS Status
- GrapheneOS has **working RCS support at the OS level** 
- Google Messages integration is being developed
- Works on many carriers (Verizon-based, most international carriers)
- Fails on T-Mobile and AT&T due to privileged access requirements
- RCS works intermittently — may connect then disconnect after periodic IMS audits

---

## 6. The SIP Registration Flow in the Single Registration Model

### Architecture (Android 12+)
In single registration mode, the device's ImsService handles a single SIP REGISTER that covers both MMTEL and RCS services. RCS applications use SipDelegate to send/receive SIP messages through this shared registration.

### Flow:

```
1. ImsService performs SIP REGISTER to carrier's IMS core
   ├── Includes MMTEL feature tags (VoLTE, VoWiFi)
   └── Includes RCS feature tags (chat, ft, geolocation, etc.)

2. Framework binds to ImsService and creates features
   ├── ImsService.createMmTelFeature() → MmTelFeature
   └── ImsService.createRcsFeature() → RcsFeature

3. RCS application (e.g., Google Messages) requests SipDelegate
   ├── SipDelegateManager.createSipDelegate(DelegateRequest, ...)
   ├── ImsService creates SipDelegate with filtering criteria
   └── SipDelegateConnection provided to app for SIP message I/O

4. RCS application sends SIP traffic via SipDelegate
   ├── Outbound: App → SipDelegate → ImsService → IMS network
   └── Inbound: IMS network → ImsService → SipDelegate → App

5. SIP methods restricted via SipDelegate:
   ├── CANNOT send: REGISTER, PUBLISH, OPTIONS (handled by ImsService)
   └── CAN send: MESSAGE, SUBSCRIBE, NOTIFY, custom methods
```

### Key Constraint
The SipDelegate cannot send SIP REGISTER, PUBLISH, or OPTIONS requests — those are managed exclusively by the ImsService. This ensures the single registration model where the ImsService owns the SIP dialog with the IMS core.

### Feature Tags
The DelegateRequest specifies which SIP feature tags the application needs (e.g., `+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.mmtel"` for MMTEL, RCS-specific tags for chat, file transfer, etc.). The ImsService routes incoming SIP messages to the correct SipDelegate based on matching feature tags.

---

## 7. How Provisioning XML Is Fetched and Applied

### AutoConfiguration Server (ACS) Flow

```
1. Device detects SIM insertion / carrier change
2. Carrier entitlement app triggers TS.43 entitlement check
3. service_entitlement library performs:
   ├── HTTP request to carrier entitlement server URL
   ├── EAP-AKA authentication (using SIM credentials)
   └── Receives service entitlement + configuration data

4. If RCS is entitled:
   ├── Carrier app calls ProvisioningManager.setRcsProvisioningStatus()
   └── If ACS used: carrier app calls ProvisioningManager with config XML

5. ACS provisioning:
   ├── Device sends HTTP/HTTPS request to ACS URL
   ├── ACS returns XML configuration document
   ├── XML contains: RCS server addresses, SIP configuration, capability exchange settings
   └── Applied via ProvisioningManager API

6. ImsService receives provisioning update:
   ├── RcsFeature.onRcsAutoConfigurationReceived() called with XML
   └── ImsService configures SIP stack per received XML
```

### TS.43 Service Entitlement (AOSP Implementation)
- **Library:** `frameworks/libs/service_entitlement/` — static library for TS.43 API
- **App:** `ImsServiceEntitlement` — AOSP reference implementation
- **Flow:** HTTP request → EAP-AKA auth → entitlement server → configuration data
- **Config values:** Entitlement server URL from CarrierConfig (`KEY_ENTITLEMENT_SERVER_URL`)

### ProvisioningManager API
- `setRcsProvisioningStatus(int status)` — Set RCS provisioning enabled/disabled
- `getRcsProvisioningStatus()` — Query current status
- `setRcsConfiguration(byte[] config)` — Pass configuration XML to ImsService
- The ImsService receives the configuration via `RcsFeature.onRcsAutoConfigurationReceived(byte[] xml, boolean isCompress)`

---

## 8. SIP Stack Implementation

### SipDelegateManager (System API, Android 12+)
- **File:** `frameworks/base/telephony/java/android/telephony/ims/SipDelegateManager.java`
- Requires `FEATURE_TELEPHONY_IMS_SINGLE_REGISTRATION` feature flag
- Methods:
  - `isSupported()` — Check if carrier/device supports single registration
  - `createSipDelegate(DelegateRequest, Executor, DelegateConnectionStateCallback, DelegateConnectionMessageCallback)` — Request SipDelegate creation
  - `destroySipDelegate(SipDelegateConnection, int reason)` — Tear down delegate
  - `triggerFullNetworkRegistration(SipDelegateConnection, int sipCode, String sipReason)` — Force re-registration after network error
  - `registerSipDialogStateCallback(Executor, SipDialogStateCallback)` — Monitor SIP dialog state
  - `unregisterSipDialogStateCallback(SipDialogStateCallback)` — Remove callback

### SipDelegate (ImsService side)
- Created by the ImsService implementation when framework requests it
- Handles SIP message routing between the IMS network and the RCS application
- Manages feature tag filtering — routes messages to correct delegate based on tags
- Reports state changes: DELEGATE_STATE_READY, feature tag availability changes

### DelegateConnection (App side)
- Provided to the RCS application when SipDelegate is created
- Allows sending/receiving SIP messages
- Message failure reasons: DELEGATE_DEAD, NOT_REGISTERED, INVALID_START_LINE, STALE_IMS_CONFIGURATION, etc.

### DedicatedSipTransportService
- This is part of the vendor/OEM ImsService implementation (not in AOSP framework)
- Implements the actual SIP transport layer (TCP/UDP, TLS)
- Handles SIP REGISTER, keeps registration alive, manages SIP dialogs
- Specific implementation varies by SoC vendor (Qualcomm, Samsung, MediaTek, etc.)

---

## 9. TestRcsApp

### Location
- AOSP path: `testapps/TestRcsApp`
- Built as debug package: `PRODUCT_PACKAGES_DEBUG += TestRcsApp` (in device/google/gs201/device.mk and similar)
- Not included in production builds

### Purpose
- Tests the RCS APIs exposed by the framework
- Tests single registration flow including SipDelegate creation
- Validates ImsService binding and RcsFeature creation
- Used during carrier certification for IMS single registration test cases

---

## 10. Can a Custom ImsService Handle RCS Registration Independently?

### Theoretically: YES
The AOSP ImsService API is designed to be implementable by OEMs/carriers. A custom ImsService could:
- Implement RcsFeature with SIP REGISTER handling
- Support ACS provisioning
- Implement UCE (SIP OPTIONS / Presence) for capability exchange
- Provide SipDelegate for single registration mode

### Practically: VERY DIFFICULT
1. **System App Requirement:** ImsService must be a system app with `BIND_IMS_SERVICE` permission — cannot be a third-party Play Store app
2. **Carrier Configuration:** The carrier must configure the ImsService package name via CarrierConfig, which requires carrier cooperation or device OEM support
3. **SIP Stack Complexity:** Implementing a full SIP stack with IMS AKA authentication, SIP REGISTER keepalive, SIP dialog management, and carrier-specific quirks is extremely complex
4. **Provisioning:** Must support carrier-specific provisioning (ACS XML, TS.43 entitlement, or proprietary mechanisms)
5. **Carrier Certification:** Must pass carrier certification test suites
6. **No Public ImsService API:** The ImsService class is a System API, not available to third-party developers via the public SDK

### What IS Possible
- **OEM/SoC vendor** can implement a custom ImsService (as Samsung, Qualcomm do)
- **Custom ROM** like GrapheneOS could implement its own ImsService for RCS
- **AOSP reference implementation** exists but is minimal/test-only

### What is NOT Possible for a Third-Party App
- Cannot implement ImsService (needs system app + BIND_IMS_SERVICE)
- Cannot create SipDelegates (needs PERMISSION_IMS_SINGLE_REGISTRATION)
- Cannot modify provisioning state (needs carrier privileges)
- Cannot bypass the framework's ImsService binding mechanism
- Cannot directly send SIP REGISTER (handled by ImsService exclusively)

---

## Summary Table

| Capability | ImsService (System) | ImsRcsManager (Public) | Third-Party App |
|---|---|---|---|
| SIP REGISTER | ✅ Handles | ❌ Read-only state | ❌ Cannot |
| RCS Provisioning | ✅ Receives & applies | ❌ Read-only status | ❌ Cannot |
| UCE/Capability Exchange | ✅ Implements | ✅ Query via UceAdapter | ✅ With permission |
| SipDelegate Creation | ✅ Creates delegates | ❌ Not exposed | ❌ Cannot |
| Send SIP Messages | ✅ Via SipDelegate | ❌ Not exposed | ✅ Via SipDelegate* |
| Monitor Registration | ✅ Full control | ✅ Callbacks | ✅ With permission |
| Modify Provisioning | ✅ Full control | ❌ Read-only | ❌ Cannot |
| Feature Tag Filtering | ✅ Manages | ❌ Not exposed | ❌ Cannot |

*Only if the app is the default SMS app and has PERMISSION_IMS_SINGLE_REGISTRATION

---

## Key Source References

- AOSP ImsService: `frameworks/base/telephony/java/android/telephony/ims/ImsService.java`
- AOSP ImsRcsManager: `frameworks/base/telephony/java/android/telephony/ims/ImsRcsManager.java`
- AOSP SipDelegateManager: `frameworks/base/telephony/java/android/telephony/ims/SipDelegateManager.java`
- AOSP ProvisioningManager: `frameworks/base/telephony/java/android/telephony/ims/ProvisioningManager.java`
- AOSP RcsFeature: `frameworks/base/telephony/java/android/telephony/ims/feature/RcsFeature.java`
- AOSP Service Entitlement Library: `frameworks/libs/service_entitlement/`
- AOSP ImsServiceEntitlement App: `packages/apps/ImsServiceEntitlement/`
- AOSP TestRcsApp: `testapps/TestRcsApp`
- IMS Single Registration PDF: `source.android.com/static/docs/core/connect/ims_single_registration_v1_1_1.pdf`
- GrapheneOS Issue: `github.com/GrapheneOS/os-issue-tracker/issues/6173`
- Carrier Services: `play.google.com/store/apps/details?id=com.google.android.ims`
