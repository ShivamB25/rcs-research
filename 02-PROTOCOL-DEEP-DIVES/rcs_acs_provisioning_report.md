# RCS ACS (Auto Configuration Server) XML Provisioning — Complete Reference

## Table of Contents
1. [Complete ACS XML Parameter Reference](#1-complete-acs-xml-parameter-reference)
2. [ACS URL Construction Format](#2-acs-url-construction-format)
3. [HTTP Request Format (Client → ACS)](#3-http-request-format-client--acs)
4. [GBA Authentication Mechanism for ACS Access](#4-gba-authentication-mechanism-for-acs-access)
5. [P-CSCF Address Delivery](#5-p-cscf-address-delivery)
6. [Authentication Type Configuration](#6-authentication-type-configuration)
7. [Carrier RCS vs Google Jibe RCS Provisioning](#7-carrier-rcs-vs-google-jibe-rcs-provisioning)
8. [RCS-e vs Universal Profile Provisioning](#8-rcs-e-vs-universal-profile-provisioning)
9. [Critical Parameters for Registration Success](#9-critical-parameters-for-registration-success)
10. [Biddyweb Stack Architecture](#10-biddyweb-stack-architecture)

---

## 1. Complete ACS XML Parameter Reference

The ACS XML uses OMA CP (Open Mobile Alliance Client Provisioning) format: `<wap-provisioningdoc version="1.1">`. It contains multiple `<characteristic>` blocks. Two APPLICATION sections exist: `ap2001` (IMS Settings) and `ap2002` (RCS-e Settings).

### VERS Section
| Parameter | Meaning | Typical Value | Notes |
|-----------|---------|---------------|-------|
| `version` | Config version identifier | `"1"` or date like `"20160401"` | Used by client to detect if config has changed; if same as stored, skip re-provisioning |
| `validity` | Cache validity in seconds | `"604800"` (7 days) or `"300"` (5 min) | How long client should use this config before re-fetching |

### MSG Section
| Parameter | Meaning | Typical Value | Notes |
|-----------|---------|---------------|-------|
| `title` | Message title for UI prompt | `"generic - blackbird"` | Displayed to user if config requires acceptance |
| `message` | Message body | `"generic - blackbird"` | Descriptive text |
| `Accept_btn` | Show accept button | `"1"` | 1 = show, 0 = hide |
| `Reject_btn` | Show reject button | `"0"` | 1 = show, 0 = hide |

### APPLICATION Section 1: IMS Settings (AppID=ap2001)
| Parameter | Meaning | Typical Value | Notes |
|-----------|---------|---------------|-------|
| `AppID` | Application identifier | `"ap2001"` | **Fixed**: ap2001 = IMS Settings |
| `Name` | Application name | `"IMS Settings"` | Display name |
| `AppRef` | Cross-reference key | `"IMS-Settings"` | Referenced by ap2002's `To-AppRef` |
| `ConRef` | APN connection reference | `"your APN"` or `"0"` | APN to use for IMS signaling |
| `PDP_ContextOperPref` | PDP context preference | `"0"` | 0 = use default IMS APN |
| **Timer_T1** | SIP T1 timer (ms) | `"2000"` or `"500"` | SIP retransmission timeout; controls how fast SIP retransmits. Lower = faster on low-latency networks |
| **Timer_T2** | SIP T2 timer (ms) | `"16000"` or `"4000"` | Max retransmit interval; T2 caps the exponential backoff |
| **Timer_T4** | SIP T4 timer (ms) | `"17000"` or `"5000"` | Time network takes to clear messages; determines how long to wait for ACK |
| **Private_User_Identity** | IMPI (IMS Private Identity) | `"+msisdn@domain"` or `"IMSI@realm"` | Used in SIP REGISTER; format: `{IMPI}@{home_domain}`. Often `{IMSI}@ims.mnc{MNC}.mcc{MCC}.pub.3gppnetwork.org` |
| **Public_User_Identity** | IMPU (IMS Public Identity) | `"sip:+msisdn@number"` | SIP URI used as public address; shown in SIP From/To headers |
| `Home_network_domain_name` | Home network domain | `"domain"` or `"ims.mnc001.mcc001.pub.3gppnetwork.org"` | Used for SIP routing and realm construction |
| `NatUrlFmt` | NAT URL format | `"0"` | 0 = tel URI, 1 = sip URI for NAT traversal |
| `IntUrlFmt` | Internal URL format | `"0"` or `"1"` | 0 = tel URI, 1 = sip URI for internal addressing |
| `Q-Value` | SIP registration q-value | `"0.5"` | Priority for multiple registrations (lower = higher priority) |
| `MaxSizeImageShare` | Max image share size (bytes) | `"15360000"` or `"5242880"` | Maximum image share payload |
| `MaxTimeVideoShare` | Max video share duration (sec) | `"3600"` or `"300"` | Maximum video share session length |

#### SecondaryDevicePar (within Ext)
| Parameter | Meaning | Typical Value |
|-----------|---------|---------------|
| `VoiceCall` | Secondary device: voice call | `"0"` (disabled) |
| `Chat` | Secondary device: chat | `"0"` |
| `SendSms` | Secondary device: SMS | `"0"` |
| `SendMms` | Secondary device: MMS | `"0"` |
| `FileTransfer` | Secondary device: file transfer | `"0"` |
| `VideoShare` | Secondary device: video share | `"0"` |
| `ImageShare` | Secondary device: image share | `"0"` |
| `VideoCall` | Secondary device: video call | `"0"` |
| `GeoLocPush` | Secondary device: geo location push | `"0"` |

#### ICSI_List
| Parameter | Meaning | Typical Value |
|-----------|---------|---------------|
| `ICSI` | IMS Communication Service Identifier | `"0"` or empty |
| `ICSI_Resource_Allocation_Mode` | Resource allocation mode | `"0"` or empty |

#### **LBO_P-CSCF_Address** (CRITICAL)
| Parameter | Meaning | Typical Value | Notes |
|-----------|---------|---------------|-------|
| **`Address`** | **P-CSCF outbound proxy** | `"outbound.proxy.FQDN"` or `"ss.epdg.epc.mnc001.mcc001.pub.3gppnetwork.org"` | **The SIP proxy the client sends REGISTER to. MUST be resolvable.** |
| `AddressType` | Address type | `"FQDN"` | FQDN or IPv4 or IPv6 |

#### PhoneContext_List
| Parameter | Meaning | Typical Value |
|-----------|---------|---------------|
| `PhoneContext` | Phone context domain | `"domain"` |
| `Public_user_identity` | Tel URI for phone context | `"tel:+msisdn"` |

#### Additional IMS Parameters (from ShareTechnote live capture)
| Parameter | Meaning | Typical Value |
|-----------|---------|---------------|
| `Voice_Domain_Preference_E_UTRAN` | Voice pref on LTE | `"1"` (IMS preferred) |
| `SMS_Over_IP_Networks_Indication` | SMS over IP support | `"1"` (supported) |
| `Keep_Alive_Enabled` | SIP keep-alive | `"0"` (disabled) or `"1"` |
| `Voice_Domain_Preference_UTRAN` | Voice pref on UMTS | `"1"` |
| `Mobility_Management_IMS_Voice_Termination` | MM voice termination | `"1"` |
| **`RegRetryBaseTime`** | **Registration retry base (sec)** | `"30"` or `"300"` | Base wait time before retry after reg failure |
| **`RegRetryMaxTime`** | **Registration retry max (sec)** | `"1800"` or `"3600"` | Maximum wait time for registration retry (exponential backoff cap) |

#### **APPAUTH** (CRITICAL — Authentication)
| Parameter | Meaning | Typical Value | Notes |
|-----------|---------|---------------|-------|
| **`AuthType`** | **Authentication method** | `"Digest"` or `"AKA"` or `"GIBA"` | **Determines how SIP REGISTER is authenticated. See §6 for details.** |
| `Realm` | Authentication realm | `"domain"` | SIP authentication realm; typically home network domain |
| `UserName` | Auth username (IMPI) | `"+msisdn@domain"` | Must match Private_User_Identity for Digest; for AKA, uses ISIM credentials |
| `UserPwd` | Auth password | `"your password"` | Only used for Digest auth; not used for AKA/GIBA |

### APPLICATION Section 2: RCS-e Settings (AppID=ap2002)
| Parameter | Meaning | Typical Value | Notes |
|-----------|---------|---------------|-------|
| `AppID` | Application identifier | `"ap2002"` | **Fixed**: ap2002 = RCS-e Settings |
| `Name` | Application name | `"RCS-e Settings"` | |
| `AppRef` | Cross-reference key | `"RCSe-Settings"` | |
| `To-AppRef` | Reference to IMS settings | `"IMS-Settings"` | Links to ap2001 for IMS config |

#### SERVICES
| Parameter | Meaning | Typical Value | Notes |
|-----------|---------|---------------|-------|
| `presencePrfl` | Presence profile | `"0"` | 0 = no presence |
| `ChatAuth` | Chat authorization | `"1"` | 0=never, 1=always, 2=on request |
| `ftAuth` | File transfer auth | `"1"` | |
| `standaloneMsgAuth` | Standalone msg auth | `"0"` | |
| `geolocPullAuth` | Geolocation pull auth | `"0"` | |
| `geolocPushAuth` | Geolocation push auth | `"1"` | |
| `vsAuth` | Video share auth | `"1"` | |
| `isAuth` | Image share auth | `"1"` | |
| `rcsIPVoiceCallAuth` | IP voice call auth | `"3"` | |
| `rcsIPVideoCallAuth` | IP video call auth | `"3"` | |

#### PRESENCE
| Parameter | Meaning | Typical Value |
|-----------|---------|---------------|
| `AvailabilityAuth` | Availability authorization | `"0"` |
| `AutMa` | Auto management | `"Auto"` |
| `LabelMaxLength` | Max label length | `"0"` |
| `IconMaxSize` | Max icon size | `"0"` |
| `NoteMaxSize` | Max note size | `"0"` |
| `NonVipPollPeriodSetting` | Non-VIP poll period | `"0"` |
| `NonVipMaxPollPerPeriod` | Non-VIP max polls | `"0"` |
| `PublishTimer` | Presence publish interval | `"0"` |
| `NickNameLength` | Max nickname length | `"0"` |
| `TextMaxLength` | Location text max | `"0"` |
| `LocInfoMaxValidTime` | Location info validity | `"0"` |
| `client-obj-datalimit` | Client object data limit | `"0"` |
| `source-throttle-publish` | Publish throttle | `"0"` |
| `max-number-of-subscriptions-in-presence-list` | Max subscriptions | `"0"` |

#### XDMS (XML Document Management Server)
| Parameter | Meaning | Typical Value |
|-----------|---------|---------------|
| `RevokeTimer` | Revoke timer | `"0"` |
| `enableXDMSSubscribe` | Enable XDM subscribe | `"0"` |
| `XCAPRootURI` | XCAP root URI | `"test"` |
| `XCAPAuthenticationUserName` | XCAP auth username | `"test"` |
| `XCAPAuthenticationSecret` | XCAP auth password | `"test"` |
| `XCAPAuthenticationType` | XCAP auth type | `"Digest"` |

#### SUPL (Secure User Plane Location)
| Parameter | Meaning | Typical Value |
|-----------|---------|---------------|
| `TextMaxLength` | Text max length | `"0"` |
| `LocInfoMaxValidTime` | Location validity | `"0"` |
| `Addr` | SUPL server address | `"test"` |

#### **IM** (Instant Messaging — CRITICAL)
| Parameter | Meaning | Typical Value | Notes |
|-----------|---------|---------------|-------|
| `imMsgTech` | IM messaging tech | `"0"` | 0=MSRP, 1=CPM |
| `imCapAlwaysON` | IM capability always on | `"1"` | Publish IM capability even when not in active chat |
| `GroupChatFullStandFwd` | Group chat S&F | `"0"` | Store-and-forward for full group chat |
| `GroupChatOnlyFStandFwd` | Group chat only S&F | `"0"` | S&F only for group chat |
| `imWarnSF` | Warn on S&F delivery | `"1"` | |
| `SmsFallBackAuth` | SMS fallback auth | `"1"` | 1=allowed |
| `imCapNonRCS` | IM cap for non-RCS | `"0"` | |
| `imWarnIW` | Warn on interop | `"0"` | |
| `AutAccept` | Auto-accept 1-1 chat | `"0"` | |
| `imSessionStart` | IM session start mode | `"0"` | |
| `AutAcceptGroupChat` | Auto-accept group chat | `"1"` | |
| `firstMessageInvite` | First msg as INVITE | `"1"` | 1=use large message mode (INVITE+MSRP), 0=use SIP MESSAGE |
| `TimerIdle` | Idle session timeout (sec) | `"300"` | 5 min idle before closing MSRP session |
| `MaxConcurrentSession` | Max concurrent sessions | `"0"` | 0=unlimited |
| `multiMediaChat` | Multi-media chat | `"0"` | |
| `MaxSize1to1` | Max 1-1 message size (KB) | `"510"` | |
| `MaxSize1toM` | Max group msg size (KB) | `"2000"` | |
| `ftWarnSize` | FT warning threshold (KB) | `"10240"` | |
| **`MaxSizeFileTr`** | **Max file transfer size (KB)** | `"15360"` (15MB) | |
| `ftThumb` | FT thumbnail | `"0"` | |
| `ftStAndFwEnabled` | FT S&F enabled | `"0"` | |
| `ftCapAlwaysON` | FT capability always on | `"0"` | |
| `ftAutAccept` | FT auto accept | `"1"` | |
| **`ftHTTPCSURI`** | **FT HTTP server URI** | `"your file transfer HTTP server URI"` | **HTTP file transfer upload/download server** |
| `ftHTTPCSUser` | FT HTTP username | `"your login"` | |
| `ftHTTPCSPwd` | FT HTTP password | `"your password"` | |
| **`ftDefaultMech`** | **Default FT mechanism** | `"HTTP"` | **"HTTP" = use HTTP file transfer, "MSRP" = use in-band MSRP** |
| `pres-srv-cap` | Presence server capability | `"0"` | |
| `deferred-msg-func-uri` | Deferred msg function URI | `"sip:foo@bar"` | |
| **`max_adhoc_group_size`** | **Max ad-hoc group size** | `"20"` | Max participants in group chat |
| **`conf-fcty-uri`** | **Conference factory URI** | `"sip:Conference-Factory@domain"` | **URI for creating group chat conferences** |
| **`exploder-uri`** | **Standalone msg exploder URI** | `"sip:rcse-standfw@domain"` | **URI for store-and-forward message distribution** |
| `conv-hist-func-uri` | Conversation history URI | `"sip:foo@bar"` | |
| `delete-uri` | Delete message URI | `"sip:foo@bar"` | |

#### CPM (Converged IP Messaging)
| Parameter | Meaning | Typical Value |
|-----------|---------|---------------|
| `MaxSizeStandalone` | Max standalone msg size | `"0"` |
| `AuthProt` | Message store auth protocol | `"1"` |

#### **CAPDISCOVERY** (Capability Discovery)
| Parameter | Meaning | Typical Value | Notes |
|-----------|---------|---------------|-------|
| `pollingPeriod` | Capability poll period | `"0"` | Seconds between capability polls |
| `pollingRate` | Max polls per period | `"0"` | |
| `pollingRatePeriod` | Polling rate period | `"0"` | |
| `capInfoExpiry` | Capability cache expiry (hrs) | `"0"` | How long to cache capabilities |
| `defaultDisc` | Default discovery method | `"0"` | 0=SERVER, 1=CLIENT |
| `msgCapValidity` | Message capability validity (days) | `"5"` | (under Ext/joyn) |
| `capDiscCommonStack` | Use common stack for discovery | `"0"` | |

#### APN
| Parameter | Meaning | Typical Value | Notes |
|-----------|---------|---------------|-------|
| `rcseOnlyAPN` | RCS-e dedicated APN | `"your APN"` or `"ims"` | |
| `enableRcseSwitch` | Enable RCS-e switch | `"1"` or `"-1"` | |
| `alwaysUseIMSAPN` | Always use IMS APN | `"1"` | |

#### **OTHER / transportProto** (CRITICAL)
| Parameter | Meaning | Typical Value | Notes |
|-----------|---------|---------------|-------|
| **`psSignalling`** | **PS signalling transport** | `"SIPoUDP"` | **SIP over UDP for cellular** |
| **`psMedia`** | **PS media transport** | `"MSRP"` | **MSRP for message media over cellular** |
| **`psRTMedia`** | **PS real-time media** | `"RTP"` | **RTP for voice/video over cellular** |
| `wifiSignalling` | WiFi signalling transport | `"SIPoTCP"` or `"SIPoUDP"` | SIP transport over WiFi |
| `wifiMedia` | WiFi media transport | `"MSRP"` | |
| `wifiRTMedia` | WiFi real-time media | `"RTP"` | |
| `endUserConfReqId` | End user config request URI | `"endUserConfReq@domain"` | SIP URI for terms & conditions flow |
| `allowVSSave` | Allow video share save | `"0"` or `"1"` | |
| `beIPCallBreakOut` | IP call breakout | `"0"` | |
| `beIPCallBreakOutCS` | CS breakout from IP call | `"0"` | |
| `beIPVideoCallUpgradeFromCS` | Video upgrade from CS | `"0"` | |
| `beIPVideoCallUpgradeOnCapError` | Video upgrade on cap error | `"0"` | |
| `beIPVideoCallUpgradeAttemptEarly` | Early video upgrade attempt | `"0"` | |
| `uuid_Value` | UUID value | `"0"` | |
| `IPCallBreakOut` | IP call breakout | `"0"` | |

#### SERVICEPROVIDEREXT/joyn/UX
| Parameter | Meaning | Typical Value |
|-----------|---------|---------------|
| `e2eVoiceCapabilityHandling` | E2E voice cap handling | `"0"` |
| `messagingUX` | Messaging UX mode | `"1"` |
| `oneButtonVideoCall` | One-button video call | `"0"` |

#### SERVICEPROVIDEREXT/joyn/Messaging
| Parameter | Meaning | Typical Value |
|-----------|---------|---------------|
| `deliveryTimeout` | Delivery timeout | `"0"` |
| `ftHTTPCapAlwaysOn` | FT HTTP cap always on | `"1"` |

---

## 2. ACS URL Construction Format

### DNS Naming Convention (3gppnetwork.org)

The ACS URL is constructed using the PLMN (Public Land Mobile Network) identity derived from the SIM card:

```
config.rcs.mnc{MNC}.mcc{MCC}.pub.3gppnetwork.org
```

**Format breakdown:**
- `config.rcs` — Fixed prefix for RCS configuration service
- `mnc{MNC}` — Mobile Network Code (3 digits, zero-padded)
- `mcc{MCC}` — Mobile Country Code (3 digits)
- `pub.3gppnetwork.org` — Fixed 3GPP domain suffix

**Example (from ShareTechnote capture):**
- MCC=001, MNC=001 → `config.rcs.mnc001.mcc001.pub.3gppnetwork.org`
- MCC=234, MNC=015 → `config.rcs.mnc015.mcc234.pub.3gppnetwork.org`
- T-Mobile US: MCC=310, MNC=260 → `config.rcs.mnc260.mcc310.pub.3gppnetwork.org`

### DNS Resolution

The FQDN is resolved via standard DNS. The ACS server IP is returned via:
1. **A/AAAA record** — Direct IP resolution
2. **NAPTR/SRV records** — Service-based discovery (less common for ACS)

The DNS infrastructure for 3gppnetwork.org FQDNs typically resolves via the operator's DNS or the GRX/IPX DNS infrastructure for roaming scenarios.

### Protocol

- **Step 1**: HTTP (non-secured) GET to check server availability → `http://config.rcs.mnc{MNC}.mcc{MCC}.pub.3gppnetwork.org/`
- **Step 2**: HTTPS (secured) GET to retrieve actual config → `https://config.rcs.mnc{MNC}.mcc{MCC}.pub.3gppnetwork.org/?{query_params}`

---

## 3. HTTP Request Format (Client → ACS)

### Step 1: HTTP GET (Server Availability Check)

```
GET / HTTP/1.1
Cache-Control: max-age=0
Host: config.rcs.mnc001.mcc001.pub.3gppnetwork.org
User-Agent: 3gpp-gba
Connection: Keep-Alive
Accept-Language: en-US
```

**Key headers:**
- `User-Agent: 3gpp-gba` — Signals that the client supports GBA authentication
- `Host` — The ACS FQDN constructed from PLMN identity

### Step 2: HTTPS GET (Configuration Request)

```
GET /?IMEI=353756074161860
    &terminal_vendor=testVendor
    &rcs_version=5.1B
    &terminal_model=SM-N920T
    &client_version=RCSAndr-5.0
    &IMSI=001001123456789
    &terminal_sw_version=N920TUVS2COKC
    &client_vendor=SEC
    &vers=20160401
    &rcs_profile=joyn_blackbird HTTP/1.1
Cookie: PHPSESSID=dv+z7IckAiXiBX+aFEJh+g==
Cache-Control: max-age=0
Host: config.rcs.mnc001.mcc001.pub.3gppnetwork.org
User-Agent: IM-client/OMA1.0 testVendor/SM-N920T-OKC testVendor-RCS/5.0 3gpp-gba
Connection: Keep-Alive
Accept-Language: en-US
```

### Complete Query Parameter Reference

| Parameter | Meaning | Example | Required |
|-----------|---------|---------|----------|
| **`IMEI`** | International Mobile Equipment Identity | `353756074161860` | Yes — identifies the device |
| **`IMSI`** | International Mobile Subscriber Identity | `001001123456789` | Yes — identifies the SIM/subscriber |
| **`rcs_version`** | RCS release version | `5.1B` | Yes — tells ACS which RCS spec version the client supports |
| **`rcs_profile`** | RCS profile name | `joyn_blackbird` | Yes — determines which config template to return |
| **`client_version`** | Client software version | `RCSAndr-5.0` | Yes — used for version-specific config |
| **`client_vendor`** | Client vendor code | `SEC` (Samsung) | Yes — vendor-specific feature flags |
| **`terminal_vendor`** | Device manufacturer | `testVendor` | Yes |
| **`terminal_model`** | Device model | `SM-N920T` | Yes |
| **`terminal_sw_version`** | Device firmware version | `N920TUVS2COKC` | Yes |
| **`vers`** | Current config version on device | `20160401` | Yes — allows ACS to skip if config unchanged |

### User-Agent Format

The `User-Agent` header follows this format:
```
IM-client/OMA1.0 {vendor}/{model}-{sw_version} {vendor}-RCS/{version} 3gpp-gba
```

The `3gpp-gba` token in User-Agent indicates the client supports GBA-based authentication for the ACS session.

---

## 4. GBA Authentication Mechanism for ACS Access

### Overview

GBA (Generic Bootstrapping Architecture), defined in 3GPP TS 33.220, allows application-level authentication (like ACS access) to reuse the strong 3GPP AKA (Authentication and Key Agreement) mechanism from the cellular network. This means the ACS doesn't need a separate username/password — it trusts the network's authentication of the SIM card.

### Architecture Components

```
UE (Phone) ←→ BSF (Bootstrapping Server Function) ←→ HSS (Home Subscriber Server)
                              ↕
                         NAF (Network Application Function = ACS)
```

- **BSF** — Bootstrapping Server Function; runs AKA with UE, derives shared keys
- **NAF** — Network Application Function; the ACS server in this context
- **HSS** — Home Subscriber Server; stores subscriber credentials (Ki, etc.)
- **UE** — User Equipment; contains USIM/ISIM with shared secret Ki

### GBA Process for ACS Access

1. **UE initiates GBA bootstrapping** with BSF over HTTP (Ub interface)
2. **BSF requests Authentication Vector (AV)** from HSS: `AV = RAND || AUTN || XRES || CK || IK`
3. **BSF sends RAND + AUTN** to UE
4. **UE verifies AUTN** using ISIM/USIM, calculates RES using Ki
5. **UE sends RES** to BSF
6. **BSF verifies RES == XRES** → authentication successful
7. **Both sides derive Ks** = CK || IK (session key material)
8. **NAF-specific keys are derived**:
   - `Ks_ext_NAF = KDF(Ks, "gba-me", RAND, IMPI, NAF_Id)`
   - `Ks_int_NAF = KDF(Ks, "gba-u", RAND, IMPI, NAF_Id)`
9. **BSF provides NAF keys to ACS** over Zh interface
10. **UE uses Ks_int_NAF** as password/credential for HTTPS to ACS
11. **ACS validates** using keys received from BSF

### BSF Address Discovery

The BSF address is derived from ISIM/UICC parameters per 3GPP TS 23.003 §16.2:
```
bsf.mnc{MNC}.mcc{MCC}.pub.3gppnetwork.org
```

### GBA in ACS Context

For the ACS provisioning flow:
- The `User-Agent: 3gpp-gba` header signals GBA support
- The HTTPS connection to ACS uses GBA-derived credentials
- HTTP Digest auth over the HTTPS session uses `Ks_int_NAF` as the password
- The `btid` (bootstrapping transaction ID) from the BSF may be sent as a cookie

### GBA Variants

| Variant | Description | Use Case |
|---------|-------------|----------|
| **GBA_ME** | Keys stored in Mobile Equipment | Standard for ACS; `Ks_ext_NAF` |
| **GBA_U** | Keys stored in UICC/ISIM | Higher security; `Ks_int_NAF` |
| **GBA-TMPI** | Temporary GBA | Lightweight variant for constrained devices |

---

## 5. P-CSCF Address Delivery

The P-CSCF (Proxy-Call Session Control Function) is the SIP proxy that the RCS client must send its SIP REGISTER to. It is delivered via the ACS XML in the `LBO_P-CSCF_Address` characteristic:

```xml
<characteristic type="LBO_P-CSCF_Address">
    <parm name="Address" value="ss.epdg.epc.mnc001.mcc001.pub.3gppnetwork.org"/>
    <parm name="AddressType" value="FQDN"/>
</characteristic>
```

### Delivery Methods

| Method | Description | Priority |
|--------|-------------|----------|
| **ACS XML (LBO_P-CSCF_Address)** | Primary method via auto-configuration | 1st choice |
| **PDP Context (PCO)** | P-CSCF address in Protocol Configuration Options during PDP context activation | 2nd choice |
| **DHCP** | P-CSCF via DHCP option on IMS APN | 3rd choice |
| **DNS NAPTR/SRV** | P-CSCF discovered via DNS records | 4th choice |

### P-CSCF Address Types

| AddressType | Format | Example |
|-------------|--------|---------|
| `FQDN` | Fully Qualified Domain Name | `pcscf.operator.com` |
| `IPv4` | IPv4 address | `10.1.1.1` |
| `IPv6` | IPv6 address | `2001:db8::1` |

### How the Client Uses P-CSCF

1. Client resolves P-CSCF FQDN via DNS → gets IP address
2. Client sends SIP REGISTER to `sip:{IMPU}@{home_domain}` via P-CSCF
3. P-CSCF forwards REGISTER to S-CSCF via I-CSCF
4. S-CSCF authenticates the user (401 challenge)
5. Client responds with credentials → 200 OK → registered

---

## 6. Authentication Type Configuration

### APPAUTH Section

```xml
<characteristic type="APPAUTH">
    <parm name="AuthType" value="Digest"/>
    <parm name="Realm" value="domain"/>
    <parm name="UserName" value="+msisdn@domain"/>
    <parm name="UserPwd" value="your password"/>
</characteristic>
```

### Authentication Methods

| AuthType | Mechanism | How It Works | When Used |
|----------|-----------|--------------|-----------|
| **`Digest`** | HTTP Digest (RFC 2617) | Username/password in ACS XML; client responds to SIP 401/407 with MD5 digest response | Test/lab environments; non-SIM devices; secondary devices |
| **`AKA`** (or `AKAv1-MD5`) | IMS AKA (3GPP TS 33.203) | Uses ISIM/USIM on SIM card; client runs AKA algorithm with RAND from 401 challenge; response calculated using Ki on SIM | **Primary method for carrier IMS**; most secure; requires ISIM/USIM |
| **`GIBA`** | GBA-Improved Bootstrapping Authentication | Early IMS authentication; uses HTTP Digest with GBA-derived keys; no ISIM required | Fallback when ISIM not available; older networks |
| **`Bearer`** (RFC 8898) | Third-party token-based | Uses OAuth 2.0 Bearer token in SIP Authorization header; token obtained from auth server | **Google Jibe / Universal Profile 2.0+**; token-based auth |

### SIP REGISTER Authentication Flow (Digest)

```
1. UE → P-CSCF: REGISTER sip:domain (no credentials)
2. P-CSCF → S-CSCF: Forward REGISTER
3. S-CSCF → UE: 401 Unauthorized (WWW-Authenticate: Digest realm="domain", nonce="xxx")
4. UE: Calculate response = MD5(MD5(username:realm:password):nonce:MD5(REGISTER:URI))
5. UE → P-CSCF: REGISTER (with Authorization header)
6. S-CSCF → UE: 200 OK
```

### SIP REGISTER Authentication Flow (AKA)

```
1. UE → P-CSCF: REGISTER sip:domain (no credentials)
2. S-CSCF: Generate RAND, AUTN from HSS
3. S-CSCF → UE: 401 Unauthorized (WWW-Authenticate: Digest algorithm=AKAv1-MD5, nonce="Base64(RAND||AUTN||MAC||SQN)")
4. UE/ISIM: Verify AUTN using Ki, calculate RES and CK/IK
5. UE → P-CSCF: REGISTER (Authorization: Digest response=Base64(RES), ck=CK, ik=IK)
6. S-CSCF: Verify RES, establish IPsec SA using CK/IK
7. S-CSCF → UE: 200 OK
```

---

## 7. Carrier RCS vs Google Jibe RCS Provisioning

### Carrier-Native RCS Provisioning

| Aspect | Details |
|--------|---------|
| **ACS URL** | `config.rcs.mnc{MNC}.mcc{MCC}.pub.3gppnetwork.org` — resolves to carrier's own ACS server |
| **Authentication** | GBA (3gpp-gba) or ISIM/USIM-based AKA — relies on SIM credentials |
| **P-CSCF** | Carrier's own IMS P-CSCF — delivered in ACS XML or via PDP context |
| **IMS Core** | Carrier's own IMS infrastructure (S-CSCF, I-CSCF, HSS, TAS, etc.) |
| **Registration** | SIP REGISTER to carrier's P-CSCF → carrier's S-CSCF |
| **Feature Control** | Carrier controls all features via ACS XML parameters |
| **Interoperability** | Via carrier's IMS interconnect (GRX/IPX) |
| **Client** | OEM's RCS client or carrier-branded "joyn" app |

### Google Jibe RCS Provisioning

| Aspect | Details |
|--------|---------|
| **ACS URL** | Google-hosted ACS: `config.rcs.mnc{MNC}.mcc{MCC}.pub.3gppnetwork.org` but DNS redirects to Google's Jibe Cloud, OR directly `rcs.jibe.com`-style URL |
| **Authentication** | **Bearer token** (OAuth 2.0) — not GBA; Google Messages obtains token via Google Play Services |
| **P-CSCF** | Google/Jibe's own P-CSCF in their cloud IMS |
| **IMS Core** | Jibe Cloud (Google's hosted IMS platform) — SBC, P-CSCF, S-CSCF, application servers all hosted by Google |
| **Registration** | SIP REGISTER to Jibe's P-CSCF → Jibe S-CSCF |
| **Feature Control** | Google controls features; carrier may have some control via Jibe Hub |
| **Interoperability** | Jibe Hub provides interconnect to carrier networks via GRX/IPX |
| **Client** | Google Messages app (built-in on Android) |
| **Bypass Mechanism** | Google Messages can fall back to "Google Guest" RCS when carrier doesn't provide RCS — skips carrier ACS entirely |

### Key Differences

| Dimension | Carrier RCS | Google Jibe RCS |
|-----------|-------------|-----------------|
| **ACS Auth** | GBA/3gpp-gba (SIM-based) | Bearer token (Google account-based) |
| **SIM Dependency** | Requires carrier SIM with ISIM/USIM | Works with any SIM; uses Google Play Services |
| **IMS Infrastructure** | Carrier-owned | Google-hosted (Jibe Cloud) |
| **Config Source** | Carrier ACS (3gppnetwork.org) | Google ACS or hardcoded in Google Messages |
| **Registration** | SIP REGISTER to carrier IMS | SIP REGISTER to Jibe Cloud |
| **Feature Parity** | May lag behind (carrier-dependent) | Always latest Universal Profile features |
| **Roaming** | Requires GRX/IPX interconnect | Works anywhere with internet |
| **Provisioning Flow** | Full ACS XML (as described above) | Simplified; much of config is hardcoded in the app |

### Google Guest Program

When a carrier does not provide RCS, Google Messages falls back to the "Google Guest" program:
- Bypasses carrier ACS entirely
- Uses Google's own RCS infrastructure
- Authentication via Google account (not SIM-based)
- Feature set limited to Universal Profile baseline
- The user's phone number is verified via SMS OTP

---

## 8. RCS-e vs Universal Profile Provisioning

### RCS-e (Rich Communication Services - enhanced)

| Aspect | Details |
|--------|---------|
| **Spec** | GSMA RCC.07 (RCS-e) |
| **ACS XML** | Full wap-provisioningdoc with ap2001 + ap2002 |
| **AppIDs** | `ap2001` (IMS) + `ap2002` (RCS-e) |
| **Profiles** | `joyn_blackbird`, `joyn_albatros` |
| **IM** | MSRP-based (session-based messaging) |
| **FT** | MSRP in-band or HTTP (ftHTTP) |
| **Presence** | Full presence server (SUBSCRIBE/NOTIFY/PUBLISH) |
| **Cap Discovery** | Presence-based or OPTIONS-based |
| **Group Chat** | Conference factory via SIP INVITE |
| **Auth** | Digest, AKA, GIBA |
| **Transport** | SIPoUDP (PS), SIPoTCP (WiFi) |
| **Dual Registration** | Separate IMS registration for RCS and VoLTE |

### Universal Profile (UP)

| Aspect | Details |
|--------|---------|
| **Spec** | GSMA RCC.71 (Universal Profile 1.0/2.0/3.0) |
| **ACS XML** | Simplified; may use RCC.14 config document or carrier-config Android API |
| **AppIDs** | Still uses ap2001/ap2002 for backward compat, but many params now hardcoded |
| **Profiles** | `up_2.0`, `up_2.1`, `up_2.2`, `up_3.0` |
| **IM** | MSRP or CPIM (more commonly MSRP still) |
| **FT** | HTTP file transfer (preferred), MSRP fallback |
| **Presence** | **Deprecated** — replaced by SIP OPTIONS capability exchange |
| **Cap Discovery** | SIP OPTIONS-based (no presence server needed) |
| **Group Chat** | Chatbot-friendly; still conference factory but with modern features |
| **Auth** | Bearer token (new), AKA, Digest |
| **Transport** | SIPoTCP preferred, SIPoWS (WebSocket) in some implementations |
| **Single Registration** | Shared IMS registration for RCS and VoLTE (MMTEL) |

### Key Parameter Differences

| Parameter | RCS-e Value | Universal Profile Value | Significance |
|-----------|-------------|------------------------|--------------|
| `presencePrfl` | Active (various values) | `"0"` (disabled) | UP removed presence server dependency |
| `defaultDisc` | May be `0` (server) | `1` (client/OPTIONS) | UP uses SIP OPTIONS for discovery |
| `AuthType` | `Digest`/`AKA`/`GIBA` | `Bearer`/`AKA` | UP adds token-based auth |
| `wifiSignalling` | `SIPoTCP` | `SIPoTCP`/`SIPoWS` | UP may use WebSocket |
| `rcs_profile` | `joyn_blackbird` | `up_2.0` etc. | Profile identifier |
| Presence parameters | Populated | All `"0"` | UP doesn't use presence |
| `firstMessageInvite` | `"1"` | `"1"` | Same — large message mode |

---

## 9. Critical Parameters for Registration Success

### Absolutely Required (Registration Will Fail Without These)

| # | Parameter | Why Critical | Failure Mode |
|---|-----------|-------------|--------------|
| 1 | **LBO_P-CSCF_Address / Address** | Client must know where to send SIP REGISTER | Cannot register at all — "no SIP proxy" |
| 2 | **AuthType** | Determines authentication method | Wrong auth type → 401 loop or immediate rejection |
| 3 | **Private_User_Identity** | IMPI for SIP REGISTER Authorization header | Missing → server rejects as anonymous |
| 4 | **Public_User_Identity** | IMPU for SIP REGISTER To/From headers | Missing → malformed REGISTER |
| 5 | **Home_network_domain_name** | SIP REGISTER request-URI domain | Wrong domain → REGISTER sent to wrong network |
| 6 | **Realm** (for Digest) | Authentication realm | Wrong realm → 401 challenge mismatch |

### Highly Important (Registration May Succeed But Services Will Break)

| # | Parameter | Why Important | Failure Mode |
|---|-----------|--------------|--------------|
| 7 | **Timer_T1/T2/T4** | SIP retransmission timing | Too low on slow networks → excessive retransmits; too high → slow failover |
| 8 | **RegRetryBaseTime / RegRetryMaxTime** | Retry timing after registration failure | Too aggressive → network load; too conservative → long outage |
| 9 | **psSignalling** | Transport protocol for SIP | Wrong protocol → SIP messages dropped |
| 10 | **ftHTTPCSURI** | HTTP file transfer server | File transfer broken without it |
| 11 | **conf-fcty-uri** | Group chat conference factory | Group chat creation fails |
| 12 | **max_adhoc_group_size** | Max group participants | Group chat limited or fails if too many participants |

### Common Misconfiguration Pitfalls

1. **Wrong P-CSCF address**: FQDN doesn't resolve or points to wrong server
2. **AuthType mismatch**: Client configured for Digest but network expects AKA
3. **IMPI format**: Must match network's expected format (IMSI-based vs MSISDN-based)
4. **IMPU scheme**: Must use correct URI scheme (`sip:` vs `tel:`)
5. **Home domain mismatch**: Domain in IMPI/IMPU doesn't match network's IMS domain
6. **Missing IMS APN**: APN not configured or wrong APN used
7. **Transport mismatch**: Client tries SIPoUDP but P-CSCF only accepts SIPoTCP/TLS

---

## 10. Biddyweb Stack Architecture

### Repository Structure

```
android-rcs-ims-stack/
├── apidemo/              # API demo applications
│   ├── extension/        # Custom extensions (games, whiteboard)
│   ├── gsma/             # GSMA API demo
│   └── sip/              # SIP-level demo
├── appdemo/              # Application demo (full messaging app)
├── core/                 # ★ CORE RCS STACK ★
│   ├── template-ota_config-generic.xml  # ACS provisioning template
│   ├── src/com/orangelabs/rcs/
│   │   ├── core/ims/
│   │   │   ├── ImsModule.java              # Main IMS module (orchestrates registration)
│   │   │   ├── network/registration/
│   │   │   │   ├── RegistrationManager.java        # ★ SIP registration manager ★
│   │   │   │   ├── RegistrationProcedure.java      # Registration procedure interface
│   │   │   │   ├── GibaRegistrationProcedure.java   # GIBA auth registration
│   │   │   │   ├── HttpDigestRegistrationProcedure.java  # Digest auth registration
│   │   │   │   └── RegistrationUtils.java           # Registration helper utilities
│   │   │   ├── protocol/          # SIP protocol handling
│   │   │   └── service/          # IMS services (IM, FT, presence, rich call)
│   │   ├── provisioning/
│   │   │   ├── Parameter.java              # Provisioning parameter definitions
│   │   │   ├── ProvisioningInfo.java       # Provisioning data model
│   │   │   ├── ProvisioningParser.java     # ★ XML parser for ACS response ★
│   │   │   ├── https/
│   │   │   │   ├── HttpsProvisioningManager.java   # ★ HTTPS provisioning manager ★
│   │   │   │   ├── HttpsProvisioningConnection.java  # HTTP connection to ACS
│   │   │   │   └── HttpsProvisioningUtils.java       # URL construction, query params
│   │   │   └── local/
│   │   │       └── Provisioning.java       # Local provisioning (fallback)
│   │   └── ...
│   └── ...
├── ri/                   # Reference Implementation (UI app)
├── script/               # Build scripts
└── siplog/               # SIP log viewer
```

### Key Components

#### ImsModule.java
- **Central orchestrator** for the RCS stack
- Manages the IMS registration lifecycle
- Coordinates between registration, services, and network events
- Handles network bearer changes (3G ↔ WiFi)

#### RegistrationManager.java
- **Handles SIP REGISTER flow**:
  - Constructs SIP REGISTER request
  - Processes 401/407 challenges
  - Implements authentication (Digest or GIBA)
  - Manages registration state machine (UNREGISTERED → REGISTERING → REGISTERED)
  - Handles re-registration timers
  - Processes 200 OK response (extracts P-Associated-URI, Service-Route, etc.)
  - Implements `RegRetryBaseTime`/`RegRetryMaxTime` exponential backoff

#### RegistrationProcedure.java (Interface)
- Defines the authentication contract
- Two implementations:
  - `HttpDigestRegistrationProcedure` — MD5 Digest auth
  - `GibaRegistrationProcedure` — GBA-Improved Bootstrapping Authentication

#### ProvisioningParser.java
- **Parses the ACS XML response** into the `ProvisioningInfo` data model
- Maps XML `<parm>` elements to `Parameter` enum values
- Handles both ap2001 (IMS) and ap2002 (RCS-e) application sections

#### HttpsProvisioningManager.java
- **Manages the ACS provisioning session**
- Constructs the ACS URL from PLMN identity (MCC/MNC from SIM)
- Builds the HTTPS GET request with query parameters (IMEI, IMSI, rcs_version, etc.)
- Handles GBA authentication for the HTTPS session
- Processes the XML response via ProvisioningParser
- Implements version checking (skip if same `vers`)
- Implements validity timer (re-provision after `validity` seconds)

### IMS Server Components (Network Side)

The biddyweb stack is a **client-only** implementation. It connects to standard IMS core network components:

| Component | Function | Relevant for RCS |
|-----------|----------|------------------|
| **P-CSCF** | Proxy-CSCF; first hop for SIP | Receives SIP REGISTER from client |
| **I-CSCF** | Interrogating-CSCF | Routes REGISTER to correct S-CSCF |
| **S-CSCF** | Serving-CSCF | Authenticates user, maintains registration state |
| **HSS** | Home Subscriber Server | Stores subscriber profile, authentication vectors |
| **ACS** | Auto Configuration Server | Provides XML provisioning to client |
| **BSF** | Bootstrapping Server Function | GBA authentication for ACS access |
| **TAS** | Telephony Application Server | VoLTE/MMTEL services |
| **RCS AS** | RCS Application Server | Chat, FT, presence, capability servers |
| **XDM** | XML Document Management | Manages presence lists, policies |
| **Conference Factory** | Group chat server | Manages group chat conferences |
| **MRF** | Media Resource Function | MSRP relay, media processing |

### Open Source Libraries Used
- **NIST SIP** (javax.sip) — SIP stack implementation
- **DNS Java** — DNS resolution for P-CSCF discovery
- **Bouncy Castle** — Cryptography (for AKA/GIBA key derivation)

### Version History
- Originally developed by **Orange Labs** (France Telecom/Orange)
- Released as open source under Apache 2.0 license
- Last maintained version: **2.5.18** (RCS-e / Blackbird profile)
- The successor project is **android-rcs/rcsjta** on GitHub (GSMA API compatible, newer profiles)
- Package namespace: `com.orangelabs.rcs` (biddyweb) → `com.gsma.rcs` (rcsjta)

---

*Report generated from analysis of biddyweb/android-rcs-ims-stack, ShareTechnote IMS documentation, GSMA RCC.14/RCC.07/RCC.71 specifications, 3GPP TS 33.220 (GBA), and network capture data.*
