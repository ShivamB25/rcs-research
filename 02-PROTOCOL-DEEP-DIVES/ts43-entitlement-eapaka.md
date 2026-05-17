# TS.43 Service Entitlement & EAP-AKA Authentication — Deep Research

## Table of Contents
1. [What TS.43 Entitlement Checks Are](#1-what-ts43-entitlement-checks-are)
2. [The Full EAP-AKA Authentication Flow](#2-the-full-eap-aka-authentication-flow)
3. [How Android's ImsServiceEntitlement App Works](#3-how-androids-imsserviceentitlement-app-works)
4. [What the Entitlement Server Returns](#4-what-the-entitlement-server-returns)
5. [Entitlement Server URL Format and Discovery](#5-entitlement-server-url-format-and-discovery)
6. [Satisfying Entitlement from a Headless Client](#6-satisfying-entitlement-from-a-headless-client)
7. [Performing EAP-AKA via sim-rest-server](#7-performing-eap-aka-via-sim-rest-server)
8. [What Happens If Entitlement Check Is Bypassed](#8-what-happens-if-entitlement-check-is-bypassed)
9. [Carrier-Specific Entitlement Requirements](#9-carrier-specific-entitlement-requirements)
10. [Whether Google Jibe Bypasses Carrier Entitlement](#10-whether-google-jibe-bypasses-carrier-entitlement)

---

## 1. What TS.43 Entitlement Checks Are

### Definition

**TS.43 Service Entitlement Configuration** is a GSMA specification (currently at v13.0 as of 2026) that defines the **entitlement verification step** for the activation and ongoing verification of IMS-based services on mobile devices. It is the gate that determines whether a device/subscriber is authorized to use:

- **VoLTE** (Voice over LTE) — per IR.92
- **VoWiFi** (Voice over Wi-Fi) — per IR.51
- **SMSoIP** (SMS over IP) — per IR.51
- **RCS** (Rich Communication Services) — per RCC.14/RCC.07
- **On-Device Service Activation (ODSA)** — eSIM companion device provisioning
- **Data plan information** — subscription status queries

### Why It Matters for RCS

RCS registration on a carrier network is **conditional on passing the entitlement check**. The device must prove to the carrier's entitlement server that:

1. The subscriber's account is provisioned for RCS
2. The SIM card is authentic (via EAP-AKA)
3. The device is authorized for the requested service

If entitlement fails, the device will **not** proceed to IMS SIP REGISTER for RCS, and the RCS client will show as "unsupported" or "not provisioned." This is the **single most important gate** before RCS registration — the ACS provisioning (see `rcs_acs_provisioning_report.md`) provides configuration parameters, but entitlement determines whether those parameters are even usable.

### Relationship to Other Specifications

| Spec | Role | Relationship to TS.43 |
|------|------|----------------------|
| **TS.32** | Technical Adaptation of Device (TAD) | TS.43 implements the TAD procedure defined in TS.32 |
| **IR.92** | IMS VoLTE profile | TS.43 verifies VoLTE entitlement per IR.92 |
| **IR.51** | IMS VoWiFi/SMSoIP profile | TS.43 verifies VoWiFi/SMSoIP entitlement per IR.51 |
| **RCC.07** | RCS Universal Profile | TS.43 verifies RCS entitlement per RCC.07 |
| **RCC.14** | RCS Client Configuration | ACS provides config; TS.43 provides permission to use it |
| **RFC 4187** | EAP-AKA | The authentication mechanism TS.43 uses |
| **RFC 5448/9048** | EAP-AKA' (improved) | Updated version with stronger key separation |

---

## 2. The Full EAP-AKA Authentication Flow

### Overview

EAP-AKA (Extensible Authentication Protocol — Authentication and Key Agreement) is defined in **RFC 4187** and provides mutual authentication between the device (supplicant) and the carrier network (authentication server) using cryptographic material stored on the SIM/USIM/ISIM card. It requires no user input — the SIM card itself provides the credentials.

### Protocol Flow for TS.43 Entitlement

```
┌─────────────┐       ┌──────────────────┐       ┌──────────────┐       ┌──────────┐
│  ImsService │       │  service_         │       │  Entitlement │       │  HSS/    │
│  Entitlement│       │  entitlement      │       │  Server (ECS)│       │  AAA/AuC │
│  App        │       │  Library          │       │              │       │          │
└──────┬──────┘       └────────┬──────────┘       └──────┬───────┘       └────┬─────┘
       │                       │                          │                   │
  (1)  │─ invoke TS.43 API ──→│                          │                   │
       │                       │                          │                   │
  (2)  │                       │── HTTP GET/POST ───────→│                   │
       │                       │   (EAP-Identity)       │                   │
       │                       │                          │── EAP-AKA Init ─→│
       │                       │                          │   (IMSI/ID)      │
       │                       │                          │                  │
       │                       │                          │←─ RAND, AUTN ───│
       │                       │                          │   (Auth Vector)  │
       │                       │                          │                   │
  (3)  │                       │←── EAP-Request/AKA ────│                   │
       │                       │    (RAND, AUTN, MAC)     │                   │
       │                       │                          │                   │
       │  ┌────────────────────┼─────────────────────┐    │                   │
       │  │ getIccAuthentication() on SIM/ISIM       │    │                   │
       │  │ → USIM/ISIM computes RES, CK, IK         │    │                   │
       │  │ → Returns RES to library                 │    │                   │
       │  └────────────────────┼─────────────────────┘    │                   │
       │                       │                          │                   │
  (4)  │                       │── EAP-Response/AKA ────→│                   │
       │                       │   (RES, MAC)            │── RES verification→│
       │                       │                          │                   │
       │                       │                          │←── Result ────────│
       │                       │                          │                   │
  (5)  │                       │←── EAP-Success ─────────│                   │
       │                       │    + Access Token        │                   │
       │                       │    + Entitlement Data    │                   │
       │                       │                          │                   │
  (6)  │←─ entitlement result ─│                          │                   │
       │   (VoLTE=enabled,     │                          │                   │
       │    VoWiFi=enabled,    │                          │                   │
       │    RCS=enabled, etc.) │                          │                   │
```

### Step-by-Step Detail

#### Step 1: Client App Initiates Request
The `ImsServiceEntitlement` app calls the `service_entitlement` library API (e.g., `ServiceEntitlement.checkVoLteEntitlement()` or `ServiceEntitlement.checkRcsEntitlement()`).

#### Step 2: HTTP Request to Entitlement Server
The library sends an HTTP request to the carrier's entitlement server URL. This initiates the EAP-AKA exchange. The initial request typically includes:
- **IMSI** (or a pseudonym/temporary identity for privacy)
- **Service type** being queried (VoLTE, VoWiFi, RCS, SMSoIP)
- The request goes over the **default data network** (cellular or Wi-Fi)

#### Step 3: EAP-AKA Challenge from Server
The entitlement server (acting as EAP authenticator) responds with an `EAP-Request/AKA-Challenge` containing:
- **RAND** — 16-byte random number (challenge)
- **AUTN** — 16-byte authentication token (includes SQN sequence number and MAC)
- **MAC** — Message authentication code over the EAP message

The RAND and AUTN are derived from an authentication vector generated by the carrier's HSS/AuC.

#### Step 4: SIM Card Computes Response
This is the critical step that makes headless authentication possible. The library calls `TelephonyManager.getIccAuthentication()` which routes the RAND+AUTN to the SIM card:

- The **USIM** application (on the SIM) processes RAND using the shared secret key `K` stored on the SIM
- Computes **RES** (Expected Response) — the challenge response
- Computes **CK** (Cipher Key) and **IK** (Integrity Key) — session keys
- Verifies **AUTN** to authenticate the network (mutual authentication)
- If AUTN verification fails (MAC mismatch), the SIM returns an authentication error
- If SQN is out of sync, the SIM returns **AUTS** (synchronisation failure) for re-sync

The key insight: **the secret key K never leaves the SIM card**. The computation happens entirely on the SIM's secure element.

#### Step 5: EAP-Response Sent to Server
The library sends the `EAP-Response/AKA-Challenge` containing:
- **RES** — the computed response
- **MAC** — computed over the response using IK

The entitlement server (or its backend HSS/AuC) verifies RES matches the expected XRES. If it matches, the device is authenticated.

#### Step 6: Entitlement Data Returned
Upon successful EAP-AKA authentication, the entitlement server returns:
- **EAP-Success** confirmation
- **Access Token** (OAuth 2.0 Bearer token) for subsequent API calls
- **Entitlement status** for each service (enabled/disabled/incompatible)
- Optionally, **service configuration data** (e.g., P-CSCF addresses, feature flags)

### EAP-AKA' (EAP-AKA Prime)

RFC 5448 (updated by RFC 9048) defines **EAP-AKA'**, which improves upon EAP-AKA by:
- Deriving keys with a different pseudo-random function (PRF') that includes the network name
- Providing stronger key separation between access networks
- Being required for non-3GPP access (e.g., Wi-Fi calling VoWiFi)
- Using `CK' || IK'` derived from `CK || IK` and the access network identity

TS.43 entitlement servers may support EAP-AKA' for VoWiFi entitlement queries, though basic EAP-AKA is used for VoLTE/RCS queries.

### Fast Re-authentication

EAP-AKA supports **fast re-authentication** that reuses keys from a previous full authentication without involving the HSS again. This is identified by a different EAP method type and uses a re-authentication identity instead of the permanent IMSI-based identity. For entitlement checks, this means subsequent checks (e.g., periodic re-verification) are much faster.

---

## 3. How Android's ImsServiceEntitlement App Works

### Architecture (Android 12+)

From the AOSP documentation, the IMS service entitlement feature consists of two components:

#### 3.1 `service_entitlement` Static Library

**Source**: `frameworks/libs/service_entitlement/`

This library implements the TS.43 specification and provides:
- **TS.43 HTTP protocol** implementation (EAP-AKA exchange over HTTP)
- **EAP-AKA helper** for non-TS.43 use cases
- **App-facing APIs** for each TS.43 use case

Key classes:
- `ServiceEntitlement` — Main API for TS.43 entitlement queries
- `EapAkaHelper` — Lower-level EAP-AKA API for custom use cases
- `EapAkaResponse` — Encapsulates RAND+AUTN challenge and RES+CK+IK response

The library uses `TelephonyManager.getIccAuthentication(int appType, int authType, String challengeData)` to send APDU commands to the SIM. The `appType` parameter selects between:
- `UICC_APP_TYPE_USIM` (0x02) — for USIM authentication
- `UICC_APP_TYPE_ISIM` (0x03) — for ISIM authentication (preferred for IMS)

#### 3.2 `ImsServiceEntitlement` Client App

**Source**: `packages/apps/ImsServiceEntitlement/`

This is a privileged system app installed in the product partition. It:
- Uses the `service_entitlement` library to perform entitlement queries
- Renders carrier web portal UIs (for VoWiFi emergency address signup, terms and conditions)
- Interacts with `ProvisioningManager` to set provisioning states
- Handles FCM (Firebase Cloud Messaging) push notifications for entitlement state changes
- Implements periodic entitlement re-verification

### CarrierConfig Keys

| Key | Purpose |
|-----|---------|
| `KEY_ENTITLEMENT_SERVER_URL_STRING` | Carrier's entitlement server URL (must include `https://` prefix) |
| `KEY_FCM_SENDER_ID_STRING` | Carrier's FCM sender ID for push notifications (optional) |
| `KEY_SHOW_VOWIFI_WEBVIEW_BOOL` | Whether to show carrier web portal for VoWiFi signup (typically NA carriers) |
| `KEY_WFC_EMERGENCY_ADDRESS_CARRIER_APP_STRING` | Set to `com.android.imsserviceentitlement/.WfcActivationActivity` if web portal needed |
| `KEY_IMS_PROVISIONING_BOOL` | Whether carrier requires background IMS provisioning (typically EU carriers) |
| `KEY_CARRIER_VOLTE_PROVISIONING_REQUIRED_BOOL` | Set to `true` if `KEY_IMS_PROVISIONING_BOOL` is true |

### Provisioning State Flow

After a successful entitlement check, the app updates platform provisioning states via `ProvisioningManager`:

```java
// VoWiFi
ProvisioningManager.setProvisioningIntValue(
    KEY_VOICE_OVER_WIFI_ENABLED_OVERRIDE, value);

// VoLTE
ProvisioningManager.setProvisioningIntValue(
    KEY_VOLTE_PROVISIONING_STATUS, value);

// SMSoIP
ProvisioningManager.setProvisioningIntValue(
    KEY_SMS_OVER_IP_ENABLED, value);
```

System UI components (settings, status bar) read these values via `getProvisioningIntValue()` or register callbacks via `registerProvisioningChangedCallback()`.

### Testing Overrides (Root Required)

From Android 11+, carrier config overrides are available with root:

```bash
# Skip VoWiFi signup
adb root
adb shell cmd phone cc set-value -p carrier_wfc_emergency_address_carrier_app_string ""

# Skip IMS provisioning entirely
adb shell cmd phone cc set-value -p carrier_volte_provisioning_required_bool false

# Change entitlement server URL
adb shell cmd phone cc set-value -p entitlement_server_url_string "https://custom-entitlement.example.com"

# Clear all overrides
adb shell cmd phone cc clear-values
```

### GMS Partner Carriers (Android 12, TS.43 v5.0)

The initial TS.43 v5.0 support in AOSP covered:
- **US**: CSpire, US Cellular, Cellcom
- **France**: Orange

---

## 4. What the Entitlement Server Returns

### Response Structure

After successful EAP-AKA authentication, the entitlement server returns service entitlement data. Based on the TS.43 specification, the response includes status for each service:

#### VoLTE Entitlement Response
```
imsVoLTE: <enabled | disabled | incompatible>
```
- **enabled** — Subscriber is provisioned for VoLTE; device should proceed with IMS registration
- **disabled** — Subscriber account does not have VoLTE; device should not attempt VoLTE
- **incompatible** — Device/network does not support VoLTE

#### VoWiFi Entitlement Response
```
imsVoWiFi: <enabled | disabled | incompatible>
```
- Same tri-state as VoLTE
- If enabled, may also include:
  - **Emergency address URL** — for North American carriers requiring 911 address registration
  - **Web portal URL** — for terms & conditions acceptance

#### SMSoIP Entitlement Response
```
imsSMSoIP: <enabled | disabled | incompatible>
```

#### RCS Entitlement Response
```
rcs: <enabled | disabled | incompatible>
```
- **enabled** — RCS should be activated; device proceeds with RCS client configuration and IMS registration
- **disabled** — Subscriber is not RCS-provisioned
- **incompatible** — Device or network doesn't support RCS

### Access Token

The server also returns an **OAuth 2.0 Bearer access token** that:
- Is used for subsequent authenticated API calls to the entitlement server
- Has a limited lifetime (typically hours to days)
- Can be refreshed using a refresh token or via re-authentication
- Is specific to the authenticated subscriber

### Additional Configuration Data

The entitlement server may also return:
- **P-CSCF address** — for IMS registration (alternative/override to ACS-provided P-CSCF)
- **Feature capabilities** — which RCS features are enabled (chat, ft, geolocation, etc.)
- **TTL (Time To Live)** — how long the entitlement result should be cached before re-checking
- **Service portal URLs** — for user-facing service management

### Example Entitlement Response (Conceptual)

```json
{
  "imsVoLTE": "enabled",
  "imsVoWiFi": "enabled",
  "imsSMSoIP": "enabled",
  "rcs": "enabled",
  "token": {
    "access_token": "abcdef123456...",
    "token_type": "Bearer",
    "expires_in": 86400
  },
  "ttl": 604800,
  "vowifi_emergency_address_url": "https://carrier.example.com/e911",
  "service_portal_url": "https://carrier.example.com/portal"
}
```

The exact format depends on the TS.43 version and carrier implementation. Earlier versions (v5.0-v8.0) used simpler HTTP response codes and headers; later versions (v11.0+) use JSON-based responses with more granular status fields.

---

## 5. Entitlement Server URL Format and Discovery

### URL Configuration

The entitlement server URL is configured via `CarrierConfigManager.ImsServiceEntitlement.KEY_ENTITLEMENT_SERVER_URL_STRING` and is **carrier-specific**. There is no single universal entitlement server.

### URL Format Patterns

Based on carrier deployments and AOSP source, entitlement server URLs typically follow these patterns:

```
https://entitlement.carrier.com/api/v1/entitlement
https://sgws.carrier.com/ecs/entitlement
https://ecs.mnc{MNC}.mcc{MCC}.pub.3gppnetwork.org/entitlement
https://entitlement-server.carrier.net/ts43/v1
```

The `https://` prefix is mandatory (enforced by AOSP).

### Discovery Mechanisms

1. **CarrierConfig (Primary)** — The entitlement server URL is hardcoded in the carrier's CarrierConfig APK, which is loaded based on the SIM's MCC/MNC. This is the standard Android mechanism.

2. **Default URL in AOSP** — Android does NOT include a default entitlement server URL. It must be explicitly configured per carrier.

3. **SIM-based Discovery** — Some carriers store the entitlement server URL in SIM file systems (e.g., EF_EST (Entitlement Server URL), EF_EHPLMN, or proprietary files). The AOSP `service_entitlement` library reads from CarrierConfig, not directly from SIM files.

4. **DNS-based** — In theory, the 3GPP domain naming convention (`ecs.mnc{MNC}.mcc{MCC}.pub.3gppnetwork.org`) could be used, but this is not universally deployed.

### Known Carrier Entitlement Server URLs

Specific entitlement server URLs are **not publicly documented** by carriers (they are proprietary). However, from reverse-engineering and community research:

| Carrier | Known/Estimated Pattern | Notes |
|---------|------------------------|-------|
| T-Mobile US | `https://sgws.t-mobile.com/...` | Uses TS.43 for VoWiFi; RCS via Jibe |
| AT&T | `https://entitlement.att.com/...` or `https://acr.att.com/...` | TS.43 for VoLTE/VoWiFi provisioning |
| Verizon | `https://devices.vzw.com/...` or similar | Moved to Jibe for RCS |
| Orange FR | `https://acs.orange.fr/...` | One of the first TS.43 v5.0 deployments |
| CSpire US | Carrier-specific | TS.43 v5.0 reference carrier |
| US Cellular | Carrier-specific | TS.43 v5.0 reference carrier |
| Jio (India) | Not publicly known | Jio uses its own RCS infrastructure |
| Airtel (India) | Not publicly known | Airtel partners with Google Jibe for RCS |

**Important**: The actual URLs can be extracted from CarrierConfig APKs on real devices by decompiling the carrier configuration overlays. The `ImsServiceEntitlement` app reads these at runtime.

---

## 6. Satisfying Entitlement from a Headless Client

### The Core Challenge

A headless client (no Android framework, no CarrierConfig, no `TelephonyManager.getIccAuthentication()`) faces three fundamental gaps:

1. **No entitlement server URL** — Without CarrierConfig, the client doesn't know which server to contact
2. **No EAP-AKA computation on SIM** — Without Android's telephony framework, the client can't route RAND+AUTN to the SIM card
3. **No platform integration** — No `ProvisioningManager` to set entitlement state, triggering the IMS stack

### Solutions

#### Gap 1: Entitlement Server URL
- **Extract from CarrierConfig APK** — Decompile the carrier's config overlay APK from a real device to find `KEY_ENTITLEMENT_SERVER_URL_STRING`
- **Network capture** — Use a proxy (e.g., mitmproxy) on a real Android device during entitlement check to capture the URL
- **DNS enumeration** — Try `ecs.mnc{MNC}.mcc{MCC}.pub.3gppnetwork.org` patterns
- **Hardcode known URLs** — From the table above

#### Gap 2: EAP-AKA Computation (The SIM Problem)
This is the most critical and solvable gap. There are two approaches:

**Approach A: Use sim-rest-server (Recommended)**
- Connect the physical SIM card to a PC/SC reader (e.g., sysmoOCTSIM, 8-card reader)
- Run `sim-rest-server.py` from Osmocom pySim
- Implement the EAP-AKA client logic that:
  1. Sends HTTP request to entitlement server
  2. Receives RAND+AUTN challenge
  3. Forwards to `sim-rest-server` for ISIM authentication
  4. Receives RES+CK+IK back
  5. Sends EAP-Response to entitlement server

**Approach B: Direct APDU communication**
- Use `pysim-shell` or raw PC/SC to send AUTHENTICATE APDUs directly to the ISIM
- Requires implementing the full EAP-AKA state machine in the headless client

**Approach C: Known keys (DEV/TESTING ONLY)**
- If you have a test SIM with known K/OPc, you can compute RES+CK+IK locally without needing a physical SIM reader
- This only works with test SIMs, not commercial SIMs

#### Gap 3: Platform Integration
- The headless client doesn't need `ProvisioningManager` — it just needs to know the entitlement result
- If entitlement returns "enabled", the client proceeds to SIP REGISTER and RCS registration
- The entitlement check is a **prerequisite**, not something that triggers automatic platform behavior

### Feasibility Assessment

| Component | Headless Feasibility | Notes |
|-----------|---------------------|-------|
| Entitlement server URL | ✅ Solvable | Extract from CarrierConfig or capture |
| EAP-AKA authentication | ✅ Solvable | sim-rest-server + ISIM |
| HTTP/TLS to entitlement server | ✅ Trivial | Standard HTTP client |
| EAP-AKA state machine | ✅ Solvable | Implement from RFC 4187 + TS.43 spec |
| Provisioning state propagation | ❌ Not needed | Headless client doesn't need Android framework |
| FCM push for entitlement changes | ⚠️ Partial | Could implement FCM client, or use polling |
| Web portal (VoWiFi signup) | ⚠️ Complex | Some carriers require emergency address; may need web scraping |

**Conclusion**: Entitlement can be satisfied from a headless client, provided you have:
1. Physical access to the SIM card (in a reader)
2. The entitlement server URL
3. An EAP-AKA implementation

---

## 7. Performing EAP-AKA Against the Entitlement Server Using sim-rest-server

### Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌───────────────┐     ┌──────────┐
│  Headless    │     │  sim-rest-server │     │  PC/SC Reader │     │  ISIM     │
│  RCS Client  │     │  (pySim)         │     │  (sysmoOCTSIM)│     │  Card     │
└──────┬───────┘     └────────┬─────────┘     └───────┬───────┘     └────┬─────┘
       │                      │                         │                  │
  (1)  │── HTTP GET ─────────────────────────────────→ Entitlement Server
       │                      │                         │                  │
  (2)  │←── EAP-AKA Challenge (RAND, AUTN) ──────────── Entitlement Server
       │                      │                         │                  │
  (3)  │── POST /sim-auth-api/v1/slot/0 ──→│            │                  │
       │   {"rand": "...", "autn": "..."}   │            │                  │
       │                      │── SELECT ADF.ISIM ───→│── AUTHENTICATE ──→│
       │                      │←── RES, CK, IK ──────│←── RES, CK, IK ───│
       │                      │                         │                  │
  (4)  │←── {"successful_3g_authentication": │         │                  │
       │       {"res":"...", "ck":"...", "ik":"..."}}  │                  │
       │                      │                         │                  │
  (5)  │── EAP-Response/AKA (RES, MAC) ──────────────────────────────→ Entitlement Server
       │                      │                         │                  │
  (6)  │←── EAP-Success + Entitlement Data ─────────── Entitlement Server
```

### Implementation Steps

#### Step 1: Set Up sim-rest-server

```bash
# Install pySim
git clone https://github.com/osmocom/pysim.git
cd pysim
pip install -r requirements.txt

# Start the REST server with ISIM support
# NOTE: Default sim-rest-server uses USIM; for ISIM, modify code to select ADF.ISIM
python contrib/sim-rest-server.py -H 0.0.0.0 -p 8000
```

**CRITICAL**: The default `sim-rest-server.py` hardcodes `card.select_adf_by_aid(adf='usim')`. For IMS entitlement, you must authenticate against **ISIM** (ADF.ISIM, AID=`A0000000871004`). This requires modifying the server code:

```python
# Change from:
card.select_adf_by_aid(adf='usim')
# To:
card.select_adf_by_aid(adf='isim')
```

See `pysim-sim-auth-rest-audit-report.md` for the complete API specification and ISIM authentication details.

#### Step 2: Implement EAP-AKA Client

The EAP-AKA client needs to:

1. **Initiate HTTP request** to the entitlement server with service type and identity
2. **Parse EAP-Request/AKA-Challenge** from the server response (extract RAND, AUTN)
3. **Forward to sim-rest-server**:
   ```bash
   curl -X POST http://localhost:8000/sim-auth-api/v1/slot/0 \
     -H "Content-Type: application/json" \
     -d '{"rand": "bb685a4b2fc4d697b9d6a129dd09a091", "autn": "eea7906f8210000004faf4a7df279b56"}'
   ```
4. **Receive response**:
   ```json
   {
     "successful_3g_authentication": {
       "res": "b15379540ec93985",
       "ck": "713fde72c28cbd282a4cd4565f3d6381",
       "ik": "2e641727c95781f1020d319a0594f31a",
       "kc": "771a2c995172ac42"
     }
   }
   ```
5. **Construct EAP-Response** with RES and compute MAC using IK
6. **Send to entitlement server** and receive success/failure + entitlement data

#### Step 3: Handle EAP-AKA Edge Cases

- **Synchronisation failure** (AUTS): If the SIM's SQN is out of sync with the HSS, the SIM returns AUTS. The client must forward this to the server for re-synchronisation, then retry.
  ```json
  {
    "synchronisation_failure": {
      "auts": "dc2a591fe072c92d7c46ecfe97e5"
    }
  }
  ```

- **Identity privacy**: Some servers may request a pseudonym identity. The client should handle EAP-Request/AKA-Identity and respond appropriately.

- **Re-authentication**: If the server supports fast re-authentication, the client can use the cached keys for subsequent entitlement checks without full EAP-AKA.

#### Step 4: Use Access Token for Service Queries

After successful authentication, use the Bearer token for service-specific queries:

```bash
curl -H "Authorization: Bearer <token>" \
  https://entitlement.carrier.com/api/v1/service/volte
```

### Hardware Requirements

| Component | Options | Notes |
|-----------|---------|-------|
| SIM card reader | sysmoOCTSIM (8 slots), SCC (single), generic PC/SC USB | Must support APDU-level access |
| SIM card | Any commercial USIM with ISIM application | ISIM is required for IMS AKA |
| Server | Any Linux box with PC/SC support | sim-rest-server runs on Python |

---

## 8. What Happens If Entitlement Check Is Bypassed

### Theoretical Bypass Methods

1. **Skip entitlement check entirely** — Hardcode VoLTE/VoWiFi/RCS as "enabled" and proceed directly to SIP REGISTER
2. **Override CarrierConfig** — Set `carrier_volte_provisioning_required_bool` to `false` (requires root)
3. **Fake entitlement response** — Return a synthetic "enabled" response to the ImsServiceEntitlement app

### What Actually Happens

#### At the Device Level
- If the Android `ImsServiceEntitlement` app is bypassed, it won't set `ProvisioningManager` provisioning states
- The ImsService may refuse to register for services that aren't provisioned
- However, if you're implementing a **custom headless client**, you control the registration logic — there's no platform gate

#### At the Network Level (The Real Gate)
- **SIP REGISTER will still be sent** regardless of entitlement check result
- The **IMS core (P-CSCF/S-CSCF)** will authenticate the SIP registration using IMS AKA (separate from entitlement EAP-AKA)
- If the subscriber is **actually provisioned** in the HSS for IMS services, the SIP registration will succeed regardless of the entitlement check result
- If the subscriber is **NOT provisioned** in the HSS, the SIP registration will fail with 403 Forbidden or 401 Unauthorized

**Key insight**: The entitlement check is a **device-side gate**, not a network-side gate. The carrier's HSS is the ultimate authority on whether a subscriber can register for IMS services. The entitlement check prevents the device from *attempting* registration for unsubscribed services, reducing load on the network and improving user experience (no "registration failed" errors shown to users).

#### Practical Implications for Headless Clients

For a headless RCS client:
- **If the SIM is legitimately provisioned** for RCS (the subscriber pays for/has RCS), bypassing the entitlement check is safe — the SIP REGISTER will succeed anyway
- **If the SIM is NOT provisioned** for RCS, bypassing the entitlement check will just result in a failed SIP REGISTER — the network will reject it
- **Some carriers** may use the entitlement server to dynamically enable/disable services in the HSS. In this case, passing the entitlement check may trigger the carrier to provision the service in the HSS before the SIP REGISTER can succeed

### Risks of Bypassing

1. **No dynamic service updates** — Without FCM push notifications, the client won't know if the carrier disables a service
2. **VoWiFi emergency address** — Bypassing means the carrier won't have the user's emergency address on file (legal/regulatory issue in NA)
3. **Carrier detection** — The carrier may notice devices that never hit the entitlement server but register for IMS services; could flag as anomalous
4. **Service portal bypass** — Some carriers require portal interaction for VoWiFi activation; bypassing this may result in VoWiFi being technically registered but non-functional

---

## 9. Carrier-Specific Entitlement Requirements

### T-Mobile US

- **Entitlement Server**: Uses TS.43 for VoWiFi; RCS is handled via Google Jibe
- **VoWiFi**: Requires 911 emergency address registration via web portal (TS.43 with `KEY_SHOW_VOWIFI_WEBVIEW_BOOL=true`)
- **RCS**: Provided through Google Jibe Cloud — T-Mobile was one of the first US carriers to switch to Jibe (2023)
- **VoLTE**: Generally auto-provisioned; entitlement check verifies account status
- **MCC/MNC**: 310/260

### AT&T

- **Entitlement Server**: TS.43-based for VoLTE and VoWiFi
- **NumberSync (ODSA)**: AT&T uses TS.43's ODSA use case for companion device provisioning (smartwatches)
- **RCS**: Moved to Google Jibe for Android RCS
- **VoWiFi**: Requires emergency address; uses carrier web portal
- **MCC/MNC**: 310/410

### Verizon

- **RCS**: Switched to Google Jibe in 2024
- **VoLTE/VoWiFi**: Uses proprietary entitlement mechanisms (not fully TS.43 in earlier deployments)
- **Advanced Calling**: Verizon's brand for VoLTE/VoWiFi; entitlement check via Verizon's own servers
- **MCC/MNC**: 311/480, 311/481, etc.

### Jio (India)

- **Infrastructure**: Jio operates its own RCS infrastructure (not Google Jibe)
- **Entitlement**: Likely uses TS.43 or custom entitlement for VoLTE/VoWiFi; RCS may be auto-provisioned for all Jio subscribers
- **SIM**: Jio SIMs are 4G/5G only with VoLTE mandatory — all SIMs should have ISIM
- **MCC/MNC**: 405/854, 405/855, 405/856 (varies by circle)

### Airtel (India)

- **RCS**: Airtel partnered with Google Jibe (announced late 2025) for RCS rollout
- **Entitlement**: Custom; Airtel's RCS support has been limited but expanding
- **VoLTE/VoWiFi**: Airtel uses VoLTE widely; VoWiFi is limited
- **MCC/MNC**: 404/10, 404/45, etc. (varies by circle)

### Common Patterns Across Carriers

| Feature | Most Carriers | NA Carriers | EU Carriers | Indian Carriers |
|---------|--------------|-------------|-------------|-----------------|
| TS.43 Version | v5.0-v8.0 | v5.0+ (v11.0+) | v8.0+ | Varies |
| VoWiFi Web Portal | Optional | Required (911) | Optional | Not typical |
| IMS Provisioning | On-demand | Background | Background | Auto |
| RCS via Jibe | Common | Universal | Common | Growing |
| EAP-AKA for auth | Standard | Standard | Standard | Standard |

---

## 10. Whether Google Jibe Bypasses Carrier Entitlement Checks

### How Google Jibe Works

Google's Jibe platform provides RCS service in three deployment models:

1. **Jibe Cloud (Google-hosted)** — Google operates the RCS infrastructure; carrier just points devices to Jibe
2. **Jibe Hub (Carrier-hosted)** — Carrier deploys Jibe software in their own network
3. **Jibe Turbo** — Optimized RCS platform for carriers

### The Key Question: Does Jibe Skip Carrier Entitlement?

**Short answer**: Google Jibe **does not bypass** carrier entitlement for carriers that require it. It works **in cooperation with** carrier entitlement.

**Detailed answer**:

#### When Jibe Provides RCS Directly (Google Messages App)

- Google Messages on Android can connect directly to **Jibe Cloud** (`rcs.google.com`) for RCS
- This was the original "bypass" approach: Google Messages would register with Jibe Cloud regardless of carrier entitlement status
- This worked because Google Messages acted as a **cloud RCS client** — it didn't need carrier IMS infrastructure
- However, this "bypass" was controversial: carriers couldn't control RCS provisioning on their network

#### Current State (2024-2026)

- **US carriers** (T-Mobile, AT&T, Verizon) have all **switched to Jibe as their RCS provider**
- This means RCS registration now goes **through the carrier's Jibe instance**, not Google's generic cloud
- When the carrier uses Jibe Hub/Cloud as their RCS infrastructure, the **carrier controls entitlement** for Jibe RCS
- Google Messages respects the carrier's entitlement configuration — if the CarrierConfig says to check TS.43 entitlement, it does so

#### The "Jibe Sandbox" (Historical)

Before universal carrier adoption, Google operated a "Jibe sandbox" that allowed RCS on any carrier without entitlement checks. This was deprecated as carriers adopted Jibe. The old XDA tricks to force-enable Jibe RCS by modifying `rcs.google.com` endpoints no longer work on most carriers.

#### iOS RCS (Apple)

- Apple's RCS implementation in iOS 18+ follows carrier entitlement strictly
- If the carrier doesn't signal RCS support (via CarrierBundle/entitlement), iOS won't show RCS
- This is why RCS on iOS has been slow in some markets — carriers must explicitly enable it

### Entitlement Flow with Jibe RCS

```
┌────────────────┐    ┌──────────────────┐    ┌──────────────┐    ┌──────────────┐
│ Google Messages │    │ Carrier           │    │ Jibe RCS     │    │ Carrier      │
│ (RCS Client)   │    │ Entitlement Server│    │ Platform     │    │ IMS Core     │
└───────┬────────┘    └────────┬──────────┘    └──────┬───────┘    └──────┬───────┘
        │                      │                       │                   │
   (1)  │── Check entitlement →│                       │                   │
        │                      │                       │                   │
   (2)  │←── RCS=enabled ─────│                       │                   │
        │                      │                       │                   │
   (3)  │──────────────────────────────────────────→│                   │
        │   SIP REGISTER to Jibe RCS platform       │                   │
        │                      │                       │                   │
   (4)  │                      │                       │── IMS AKA auth ──→│
        │                      │                       │                   │
   (5)  │←── 200 OK ─────────────────────────────────│                   │
```

**Note**: Steps (3)-(5) use IMS AKA for SIP authentication, which is a **separate** EAP-AKA exchange from the entitlement check. The SIP REGISTER goes to the Jibe RCS platform, which proxies to the carrier's IMS core.

### Summary

| Scenario | Entitlement Check | RCS Works? |
|----------|-------------------|------------|
| Carrier uses Jibe + TS.43 | TS.43 entitlement → Jibe RCS | Yes, if entitlement passes |
| Carrier uses Jibe, no TS.43 | Carrier-specific or none | Yes, if carrier provisions |
| Google Messages, carrier blocks RCS | Google tries Jibe Cloud direct | Varies — may work on some carriers |
| Headless client, no entitlement check | Skipped entirely | SIP REGISTER may succeed if HSS provisions IMS |
| iOS, carrier supports RCS | Apple checks carrier bundle | Yes, if carrier enables |

---

## Appendix A: EAP-AKA Protocol Details (RFC 4187)

### Message Types

| Message | Direction | Contents |
|---------|-----------|----------|
| EAP-Request/Identity | Server → Client | Request for subscriber identity |
| EAP-Response/Identity | Client → Server | IMSI or pseudonym identity |
| EAP-Request/AKA-Challenge | Server → Client | RAND, AUTN, MAC |
| EAP-Response/AKA-Challenge | Client → Server | RES, MAC, (selected identity) |
| EAP-Request/AKA-Authentication-Reject | Server → Client | Authentication failed |
| EAP-Response/AKA-Authentication-Reject | Client → Server | Client rejects server auth |
| EAP-Request/AKA-Synchronization-Failure | Client → Server | AUTS (re-sync data) |
| EAP-Success | Server → Client | Authentication succeeded + key material |
| EAP-Failure | Server → Client | Authentication failed |

### Key Derivation

```
MK  = PRF'(IK || CK, "EAP-AKA'" | Identity)
K_encr = MK[0:127]    (encryption key)
K_aut  = MK[128:383]   (authentication key)
MSK    = MK[0:1279]    (Master Session Key)
EMSK   = MK[1280:2559] (Extended MSK)
```

### SIM APDU for Authentication

```
-- SELECT ADF.ISIM
00 A4 04 00 07 A0 00 00 00 87 10 04 00

-- AUTHENTICATE (3G AKA)
00 88 00 81 <Lc> <RAND_16bytes> <AUTN_16bytes> 00 Le

-- Response (success):
RES (variable, typically 8 bytes) || CK (16 bytes) || IK (16 bytes) || SW 9000

-- Response (sync failure):
AUTS (14 bytes) || SW 6986
```

---

## Appendix B: Key AOSP Source Files

| File | Path | Purpose |
|------|------|---------|
| ServiceEntitlement.java | `frameworks/libs/service_entitlement/src/...` | Main TS.43 API |
| EapAkaHelper.java | `frameworks/libs/service_entitlement/src/...` | EAP-AKA helper |
| EapAkaResponse.java | `frameworks/libs/service_entitlement/src/...` | EAP-AKA response encapsulation |
| ImsServiceEntitlement app | `packages/apps/ImsServiceEntitlement/` | System entitlement app |
| CarrierConfigManager.ImsServiceEntitlement | `frameworks/base/.../telephony/` | CarrierConfig keys |
| ProvisioningManager | `frameworks/base/.../telephony/ims/` | IMS provisioning state |
| TelephonyManager.getIccAuthentication() | `frameworks/base/.../telephony/` | SIM auth API |

---

## Appendix C: References

1. **GSMA TS.43 v13.0** — Service Entitlement Configuration (latest as of 2026): https://www.gsma.com/get-involved/working-groups/gsma_resources/ts-43-service-entitlement-configuration
2. **AOSP IMS Service Entitlement**: https://source.android.com/docs/core/connect/ims-service-entitlement
3. **RFC 4187** — EAP-AKA: https://datatracker.ietf.org/doc/html/rfc4187
4. **RFC 5448/9048** — EAP-AKA' (improved): https://datatracker.ietf.org/doc/html/rfc9048
5. **Osmocom pySim sim-rest-server**: https://downloads.osmocom.org/docs/pysim/master/html/sim-rest.html
6. **GSMA IR.92** — IMS VoLTE profile
7. **GSMA IR.51** — IMS VoWiFi/SMSoIP profile
8. **GSMA RCC.07** — RCS Universal Profile
9. **U2opia TS.43 Deployment Guide**: https://www.u2opia.com/blog/ts43-entitlement-server-deployment-checklist
10. **Global Telco Consult TS.43 Overview**: https://globaltelcoconsult.com/ts-43-gsma-standard-for-service-entitlement
