# Google Jibe RCS Cloud Protocol - Deep Research Report

## Executive Summary

Google Jibe RCS is **not** just a hosted IMS core — it is a proprietary, Google-controlled RCS backend that **bypasses carrier IMS infrastructure entirely** for most Android users. While Jibe implements the GSMA RCS Universal Profile standards for messaging (SIP/MSRP), the **registration and provisioning layer is proprietary** and undocumented. A non-Android client **cannot** currently register with Jibe's "Google Guest" (non-carrier) RCS service, as it requires Google Play Services integration (Firebase tokens, Play Integrity attestation). However, if a carrier hosts RCS via Jibe Cloud (SaaS), any spec-compliant RCS client (including Apple's iOS) can connect using standard GSMA provisioning flows.

---

## 1. How Google Jibe RCS Registration Works (Step by Step)

There are **two distinct registration paths**, depending on whether the user's carrier supports RCS natively or not:

### Path A: Carrier-Supported RCS (via Jibe Cloud SaaS)
When a carrier uses Jibe Cloud (e.g., T-Mobile, AT&T, Verizon, Vodafone, Deutsche Telekom):
1. **Device queries carrier config**: Android's telephony stack checks the carrier's IMS configuration (typically via MCC/MNC lookup in carrier config files or the ACS — Auto Configuration Server).
2. **ACS provisioning**: The device contacts the carrier's ACS endpoint to retrieve RCS configuration (SIP domain, IM server address, capabilities). This follows **GSMA RCC.14** specification.
3. **SIP REGISTER**: The RCS client sends a standard SIP REGISTER to the carrier's IMS core (hosted by Jibe Cloud on behalf of the carrier).
4. **Authentication**: SIP digest auth or **AKA (Authentication and Key Agreement)** using the SIM's ISIM/USIM credentials. On modern carriers, **EAP-AKA** is used per RCC.14 section 2.13.
5. **Session established**: After successful registration, the client can send/receive RCS messages using SIP/MSRP.

This path is spec-compliant and is what Apple's iOS RCS implementation also uses.

### Path B: "Google Guest" / Non-Carrier RCS (Proprietary)
When a carrier does **not** support RCS, Google Messages still enables RCS by directly connecting to Google's Jibe backend:
1. **Google Messages detects no carrier RCS support**: The app checks (via Carrier Services / GMS) whether the carrier has RCS infrastructure.
2. **Fallback to Jibe direct**: Google Messages connects directly to Google's Jibe servers over the data channel (internet), bypassing carrier IMS entirely.
3. **Phone number verification**: The phone number is verified via **SMS-based OTP** (a silent SMS is sent to the device). Google Messages uses GMS `Constellation` (Phone device verification) service for this, which internally follows **RCC.14 section C.3 & D** — essentially an EAP-AKA-like flow or SMS verification.
4. **Play Integrity / Device Attestation**: Google Messages requires the device to pass **Google Play Integrity** checks (formerly SafetyNet/Device Integrity). The app sends a `gmscore_instance_id_token` header containing a composite token (Firebase Instance ID + Play Integrity attestation token) via the `com.google.android.gms.asterism.IAsterismApiService.getAsterismConsent` API. Samsung Messages also uses this same mechanism.
5. **Firebase Cloud Messaging (FCM) registration**: The device registers with FCM for push notifications (new message delivery). This requires a valid Firebase token.
6. **SIP REGISTER to Jibe**: Once phone number is verified and device attested, the client sends a SIP REGISTER to Jibe's SIP server.
7. **Bearer token auth**: The SIP REGISTER uses an **opaque auth token** (derived from the device attestation / phone verification process) in the SIP `Authorization` header, not standard SIP digest or IMS AKA.

**Key insight**: The "Google Guest" path is the proprietary one — it's what enables RCS for users whose carriers don't support it, and it's the one that **cannot be replicated without Google Play Services**.

---

## 2. Does Jibe Use Standard SIP REGISTER or Proprietary Protocol?

**Both**, depending on the path:

- **Carrier path**: Standard SIP REGISTER per GSMA RCS Universal Profile (RCC.07). Uses SIP over TCP/TLS to the carrier's IMS core (Jibe-hosted). Authentication is via **IMS AKA** (using SIM credentials) or SIP digest auth. This is fully spec-compliant.

- **Google Guest path**: The SIP REGISTER itself may follow the standard format, but the **authentication mechanism is proprietary**. The `Authorization` header contains an opaque token derived from Google's proprietary phone verification and Play Integrity attestation flow. This is **not** standard IMS AKA or SIP digest. Additionally, the SIP domain used is Google's own (not a carrier IMS domain).

From the microG GmsCore issue #2994, a contributor (unpluggederan) confirmed:
> "Google's Jibe platform bypasses the carrier's IMS infrastructure entirely, however it may need to use IMS during provisioning (for example to check if the carrier has an RCS server)."

---

## 3. What Authentication Method Does Jibe Use?

### For Carrier-Jibe RCS:
- **IMS AKA (EAP-AKA)**: Uses the SIM card's ISIM application to authenticate. The device sends an AKA challenge/response through the SIP REGISTER flow.
- Per **RCC.14 section 2.13**, phone number validation uses **EAP-AKA** which returns a temporary JWT token uploaded via `as_temp_token`.
- Per **RCC.14 section 2.12**, a **client certificate** (`client_certificate_upload`) is used to generate the `opaque` parameter in SIP auth.
- Per **RCC.14 section 2.11**, **client authenticity verification** (Play Integrity on Android, App Attest on iOS) is done via `client_authenticity_support` and `client_authenticity_result_1` fields.

### For Google Guest (non-carrier) RCS:
- **SMS-based phone number verification**: Google sends a silent SMS to verify the phone number.
- **Play Integrity attestation**: Device must pass Google's Play Integrity check (device integrity verdict). The attestation token is included in the `gmscore_instance_id_token` header as a protobuf-encoded `CompositeToken` containing both Firebase IID token and Play Integrity attestation token.
- **Proprietary opaque token**: The SIP auth uses an opaque bearer token (not standard IMS AKA). This token is obtained through Google's proprietary verification flow, which involves GMS services (specifically the `Constellation` API for phone number verification and `IAsterismApiService` for attestation consent).
- **Not RFC 8898**: While the concept of OAuth Bearer tokens for SIP auth exists (RFC 8898 / RFC 8765), Jibe's Google Guest flow uses its own proprietary token mechanism, not a standard OAuth flow.

---

## 4. Can a Non-Android Client Register with Jibe?

**For Carrier-Jibe RCS: YES** — If the carrier uses Jibe Cloud and the client implements GSMA RCC.07/RCC.14 correctly (including IMS AKA auth, client certificate upload, and client authenticity verification), any device can register. **Apple's iOS** does exactly this for carriers that support RCS.

**For Google Guest (non-carrier) RCS: NO** — Google has explicitly stated they do not wish to open this proprietary backend to third-party apps. From the Google Issue Tracker (issue #408010447):
> Google does not wish to open access to their proprietary Jibe backend for third-party apps.

The Google Guest path requires:
- Google Play Services (for Firebase token, Play Integrity, Constellation API)
- Android device attestation
- Specific GMS service interfaces (`IAsterismApiService`, `IRcsService`, etc.)

A non-Android client cannot satisfy these requirements.

---

## 5. Jibe Provisioning Server URL/Endpoint

Based on the research:

### Carrier ACS (Auto Configuration Server) endpoints:
- **Varies by carrier**: Each carrier's ACS has its own URL. Historically, users manually set ACS URLs like `https://rcs-acs-prod-us.google.com/` or carrier-specific ones.
- **T-Mobile example**: `eas3.msg.t-mobile.com` (used by Apple iOS) vs `ts43.eas3.msg.t-mobile.com` (used by Google Messages / TS.43 flow)
- The ACS URL is typically discovered via the carrier's configuration (Android carrier config, or TS.43 service entitlement).

### Jibe SIP server:
- **Not publicly documented**. The Jibe SIP domain/address is returned by the ACS during provisioning.
- From the old ACS hack era, users discovered various Jibe SIP endpoints, but these are not standardized or publicly available.

### Jibe Hub:
- Jibe Hub provides interconnection between RCS-enabled carriers. It uses the **GSMA PathFinder API** to discover which RCS server handles a given phone number. The Jibe Hub architecture is documented at `docs.jibemobile.com` (requires partner login).

### Google RCS Business Messaging API:
- `rcsbusinessmessaging.googleapis.com` — This is the **business messaging** API, NOT the consumer RCS registration endpoint. It's for enterprises to send RCS messages to users.

---

## 6. How Google Messages Obtains the Jibe Connection Config

Google Messages obtains RCS configuration through multiple possible mechanisms:

1. **Carrier Config (primary for carrier-supported RCS)**: Android's `CarrierConfigManager` provides IMS/RCS parameters including the ACS URL, SIP domain, and IM server address. This is populated from carrier config XML files on the device or via TS.43 service entitlement queries.

2. **Google Carrier Services app (`com.google.android.ims`)**: This app acts as an intermediary between Google Messages and the carrier's RCS infrastructure. It handles:
   - RCS provisioning configuration retrieval
   - SIP registration management
   - IMS service integration
   - Carrier entitlement checks

3. **Google Play Services (GMS) fallback**: When no carrier RCS is detected, GMS provides the configuration to connect directly to Jibe's servers. This includes:
   - Firebase token for push notifications
   - Play Integrity token for device attestation
   - Constellation service for phone number verification

4. **AOSP Service Entitlement library**: Android includes a `service_entitlement` library (`frameworks/libs/service_entitlement/`) that implements the TS.43 flow for retrieving RCS configuration from carrier ACS servers.

---

## 7. Can Jibe Registration Be Replicated from a Server with a Real SIM?

**Theoretically possible for Carrier-Jibe RCS, but extremely difficult for Google Guest:**

### Carrier-Jibe RCS (possible with a SIM):
- If you have a real SIM with ISIM/USIM credentials (K, OPc, etc.), you could theoretically:
  1. Query the carrier's ACS to get RCS configuration
  2. Perform EAP-AKA authentication using the SIM's credentials
  3. Send a SIP REGISTER with proper auth
  4. Exchange messages via SIP/MSRP
- **Challenges**: 
  - You'd need the SIM's secret key (K) to compute AKA responses, which is normally only accessible to the SIM's cryptographic processor.
  - The client authenticity verification (Play Integrity / App Attest) would be hard to bypass from a server.
  - EAP-AKA requires a real SIM's cryptographic capabilities (or extracted keys).

### Google Guest RCS (effectively impossible from a server):
- Requires Google Play Services (Firebase, Play Integrity, Constellation)
- Requires Android device attestation
- Requires a running Android device to generate the composite token
- Google has actively fought against non-Android clients (as seen in the Beeper Mini / iMessage-style battles)

**Workaround path**: The microG community has been attempting to reverse-engineer the GMS interfaces needed for RCS registration. A $14,999 bounty exists for making RCS work with microG (issue #2994). The current approach is implementing the `IRcsService` AIDL interface that Google Messages expects, but the actual Jibe protocol communication still needs to be reverse-engineered.

---

## 8. What Data Is Sent During Jibe Registration

### During ACS provisioning (RCC.14):
- **Phone number** (MSISDN)
- **Device identifier** (IMEI or device-specific ID)
- **Client version** (RCS client version string)
- **Client vendor** (e.g., "google", "apple", "samsung")
- **Device capabilities** (supported RCS features)
- **Client certificate** (X.509, for SIP auth opaque token generation)
- **Client authenticity proof** (Play Integrity token on Android, App Attest on iOS)
- **EAP-AKA response** (if using SIM-based auth)
- **Temporary token** (JWT from EAP-AKA, uploaded as `as_temp_token`)
- **Vendor-embedded data** (proprietary fields from Google/Apple/Samsung)

### During SIP REGISTER:
- **SIP URI** (sip:user@domain)
- **Authorization header** with auth mechanism-specific credentials (AKA response, digest, or opaque token)
- **Contact header** (device's IP/port for incoming messages)
- **Expires** (registration timeout)
- **Via/Route headers** (network path)

### Google Messages specifically sends:
- `gmscore_instance_id_token` header containing a protobuf `CompositeToken` with:
  - `iid_token`: Firebase Instance ID token
  - `pia_token`: Play Integrity attestation token
- This is sent during the ACS provisioning request

---

## 9. How Often Do Jibe Tokens/Sessions Expire

Based on the research:

- **SIP Registration**: Standard SIP registration uses an `Expires` header, typically **3600 seconds (1 hour)** per GSMA RCS specs. The client must re-register before expiry.
- **FCM/Firebase token**: Firebase Instance ID tokens can be refreshed by the FCM SDK. They don't have a fixed expiry but can be invalidated by server-side rotation or app updates.
- **Play Integrity token**: Short-lived (typically **minutes to hours**). A fresh attestation must be obtained for each registration attempt.
- **EAP-AKA temporary token (JWT)**: Per RCC.14, the `as_temp_token` JWT has an expiry — typically short-lived (not documented publicly, but likely **minutes to hours**).
- **RCS session**: Persistent while the app is active and SIP registration is maintained. If registration lapses, the client must re-provision and re-register.
- **Phone number verification**: Verified once, but Google may re-verify periodically (especially after app updates, SIM changes, or device changes).

From the microG GmsCore issue, users reported that:
- RCS registration can break after app updates
- Google may "shadow ban" numbers if verification is attempted too many times
- Transferring a working RCS registration between devices (via backup/restore) can temporarily preserve the registration, but it eventually breaks

---

## 10. Is Jibe Just a Hosted IMS Core or Something Completely Different?

**Jibe is both — it's a hosted IMS core AND something additional:**

### Jibe Cloud = Hosted IMS Core (for carriers):
- Jibe Cloud is essentially a **GSMA-compliant IMS core hosted by Google** that carriers can rent as SaaS.
- It implements standard RCS Universal Profile specs (RCC.07, RCC.14).
- It supports standard SIP REGISTER, SIP MESSAGE, MSRP for file transfer, and Presence/Capability exchange.
- When a carrier switches to Jibe Cloud (like T-Mobile, AT&T, Verizon did), their RCS infrastructure is simply Google-hosted but follows GSMA standards.
- Any spec-compliant RCS client (including iOS) can connect to carrier-Jibe RCS.

### Jibe's "Google Guest" = Proprietary Extension:
- Beyond hosting carrier IMS, Google added a **proprietary over-the-top (OTT) RCS service** called "Google Guest" (launched 2019).
- This allows Google Messages users on **non-RCS-supporting carriers** to still use RCS by connecting directly to Jibe servers over the internet.
- This bypasses carrier IMS entirely.
- The authentication and provisioning for this OTT service is **proprietary and closed**.
- Google explicitly stated they will **not** open this to third-party clients.

### Jibe Hub = Interconnection:
- Jibe Hub connects different RCS networks (carrier-to-carrier) for message routing.
- Uses GSMA PathFinder API for number-to-server discovery.
- However, hubbing between Jibe and non-Jibe carriers has largely died off (the CCMI in North America was killed).

**Summary**: Jibe is a standard IMS core when used by carriers, but the "Google Guest" OTT service that enables RCS for non-carrier users is proprietary and represents Google's effective monopolization of RCS.

---

## 11. Known Reverse Engineering of the Jibe Protocol

### Active reverse engineering efforts:

1. **microG GmsCore** (GitHub: microg/GmsCore):
   - **Issue #2063**: Initial discovery that RCS works outside FCM but requires GMS for registration. Found that backing up a Google Messages installation with active RCS and restoring on a microG device temporarily preserves RCS.
   - **Issue #2994**: Active $14,999 bounty for implementing RCS support in microG. Key findings:
     - Play Integrity attestation is required (via `IAsterismApiService`)
     - Firebase Instance ID token is needed
     - Carrier Services (`com.google.android.ims`) plays a key role
     - The `gmscore_instance_id_token` header contains a protobuf `CompositeToken` with both IID and Play Integrity tokens
     - Samsung Messages also uses Play Integrity (same mechanism)

2. **RCSJTA** (GitHub: android-rcs/rcsjta):
   - An RCS-e stack for Android implementing GSMA APIs. Older project, primarily for RCS-e (pre-Universal Profile).

3. **RustyRcs** (GitHub: Hirohumi/RustyRcs):
   - An open-source RCS implementation in Rust. Not connected to any server, but demonstrates the protocol stack.

4. **phhusson's Python script**:
   - A Python script that can retrieve SIP configuration, tokens, and a full RCS config file from carrier ACS servers. Demonstrated working with carrier-Jibe RCS.

5. **benwaffle's analysis** (in microG #2994):
   - Identified the `gmscore_instance_id_token` header structure (protobuf `CompositeToken` with `iid_token` and `pia_token` fields).
   - Found that Samsung's RCS implementation also uses Play Integrity.
   - Noted Samsung's IMS and Messages apps have many unstripped symbols, making them better targets for reverse engineering than Google Messages.

6. **iOS RCS capture analysis** (in microG #2994):
   - Detailed analysis of iOS's RCS registration flow showing it follows RCC.14 spec:
     - `client_certificate_upload: applecertificate` (section 2.12)
     - `client_authenticity_support: apple-appattest` (section 2.11)
     - EAP-AKA validation with `as_temp_token` (section 2.13)
     - Apple uses `eas3.msg.t-mobile.com` vs Google's `ts43.eas3.msg.t-mobile.com`
     - The JWT tokens from both paths have different structures

7. **GrapheneOS community**:
   - Users have reported success enabling RCS on GrapheneOS (sandboxed Play Services) with specific permission changes, but the exact mechanism is not fully documented.

8. **Old ACS URL hack** (2019-2020):
   - Before Google's official RCS rollout, users manually changed the ACS URL in Google Messages' activity flags to point to Jibe servers, enabling RCS on any carrier. This was patched by Google.

---

## Key Conclusions

1. **Jibe uses standard SIP REGISTER for messaging** but the **provisioning and authentication for Google Guest RCS is proprietary**.
2. **Authentication is a mix**: IMS AKA/EAP-AKA for carrier RCS, proprietary tokens (Play Integrity + Firebase IID) for Google Guest RCS.
3. **Non-Android clients cannot register with Google Guest RCS** — Google has explicitly refused to open this.
4. **Carrier-Jibe RCS IS accessible** to spec-compliant clients (Apple does this), but requires carrier cooperation and proper IMS AKA auth.
5. **The Jibe provisioning server URL varies by carrier** and is discovered through Android's carrier config system or TS.43 entitlement.
6. **Google Messages obtains Jibe config through GMS (Play Services)** — this is the critical dependency that microG is trying to replicate.
7. **Server-side replication with a real SIM is theoretically possible** for carrier-Jibe RCS but extremely difficult due to AKA needing SIM crypto + client attestation requirements.
8. **Registration sends**: phone number, device ID, client version, client certificate, Play Integrity token, EAP-AKA response, and vendor-specific data.
9. **Sessions expire** typically every 1 hour (SIP registration), with short-lived attestation tokens (minutes to hours).
10. **Jibe is both** a hosted IMS core (for carriers) and a proprietary OTT service (Google Guest). The OTT service is what's closed.
11. **Active reverse engineering** is ongoing via microG ($14,999 bounty), with key protocol details extracted from Samsung Messages symbols and iOS packet captures.

---

## Sources

- GitHub microG/GmsCore #2063: https://github.com/microg/GmsCore/issues/2063
- GitHub microG/GmsCore #2994: https://github.com/microg/GmsCore/issues/2994
- GSMA RCC.14 v10.0 (Service Provider Device Configuration): https://www.gsma.com/solutions-and-impact/technologies/networks/gsma_resource
- GSMA RCC.07 (RCS Advanced Communications): https://www.gsma.com/solutions-and-impact/technologies/networks/gsma_resource
- Jibe Platform docs: https://docs.jibemobile.com/ (requires partner login)
- Jibe Platform: https://jibe.google.com/
- Wikipedia RCS: https://en.wikipedia.org/wiki/Rich_Communication_Services
- Android IMS Single Registration: https://source.android.com/docs/core/connect/ims-single-registration
- AOSP Service Entitlement: https://cs.android.com/android/platform/superproject/+/android-latest-release:frameworks/libs/service_entitlement/
- Jibe Hub White Paper: Referenced in microG #2994
- Openmind Networks analysis: https://www.openmindnetworks.com/blog/google-rcs-messaging-explained/
