# Carrier IMS Infrastructure Mapping — P-CSCF, ACS & ePDG Discovery

## Table of Contents
1. [3GPP DNS Naming Convention](#1-3gpp-dns-naming-convention)
2. [P-CSCF Discovery Methods](#2-p-cscf-discovery-methods)
3. [DNS Query Results](#3-dns-query-results)
4. [ACS Server URLs by Carrier](#4-acs-server-urls-by-carrier)
5. [Known P-CSCF Addresses from Public Sources](#5-known-p-cscf-addresses-from-public-sources)
6. [Carrier IMS Registration from Non-Carrier IPs](#6-carrier-ims-registration-from-non-carrier-ips)
7. [ePDG and WiFi Calling IMS Access](#7-epdg-and-wifi-calling-ims-access)
8. [Carrier Infrastructure Table](#8-carrier-infrastructure-table)
9. [Practical Conclusion](#9-practical-conclusion)
10. [References](#references)

---

## 1. 3GPP DNS Naming Convention

### The 3gppnetwork.org Domain Hierarchy

The 3GPP has defined a standardized DNS naming convention for mobile network infrastructure, specified in **3GPP TS 23.003** (Numbering, Addressing and Identification) and elaborated in **GSMA IR.67** (DNS Guidelines for Service Providers and GRX and IPX Providers). The domain `3gppnetwork.org` is owned and operated by 3GPP and serves as the root for all PLMN-specific DNS names.

### PLMN Identity FQDN Format

Every carrier (PLMN — Public Land Mobile Network) has a unique DNS subdomain based on its MCC (Mobile Country Code) and MNC (Mobile Network Code):

```
mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org
```

**Rules:**
- MNC is always zero-padded to **3 digits** (e.g., MNC 7 → `mnc007`, MNC 10 → `mnc010`)
- MCC is always 3 digits
- The `pub` subdomain indicates the "public" 3GPP network domain
- This FQDN is resolvable on the public Internet DNS AND on the GRX/IPX DNS infrastructure

### Service-Specific Subdomains

Under the PLMN domain, various services have standardized subdomain prefixes:

| Service | FQDN Pattern | Example |
|---------|---------------|---------|
| **IMS Core** | `ims.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org` | `ims.mnc260.mcc310.pub.3gppnetwork.org` |
| **RCS ACS** | `config.rcs.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org` | `config.rcs.mnc260.mcc310.pub.3gppnetwork.org` |
| **ePDG** | `epdg.epc.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org` | `epdg.epc.mnc260.mcc310.pub.3gppnetwork.org` |
| **BSF (GBA)** | `bsf.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org` | `bsf.mnc260.mcc310.pub.3gppnetwork.org` |
| **ECS (Entitlement)** | `ecs.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org` | `ecs.mnc260.mcc310.pub.3gppnetwork.org` |

### IMS Node FQDNs within the IMS Domain

Per GSMA IR.67, individual IMS nodes under the IMS subdomain follow this convention:

```
<node>.ims.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org
```

| Node | FQDN Pattern |
|------|-------------|
| P-CSCF | `pcscf.ims.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org` |
| I-CSCF | `icscf.ims.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org` |
| S-CSCF | `scscf.ims.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org` |
| HSS | `hss.ims.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org` |

### ePDG FQDN Variants

Per 3GPP TS 23.003 §17, the ePDG FQDN has several possible formats:

1. **Standard**: `epdg.epc.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org`
2. **With Geographic prefix**: `epdg.epc.geo.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org` (T-Mobile US uses this)
3. **With "ss" prefix**: `ss.epdg.epc.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org` (Seen in T-Mobile US)
4. **With "ss" + geo**: `ss.epdg.epc.geo.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org`
5. **Carrier-custom FQDN**: Some carriers use their own domain instead (e.g., `epdg.epc.att.net`, `epdg.vodafone.co.uk`)

The `geo` prefix enables geographically-distributed ePDG selection — the DNS returns different IP addresses based on the resolver's location, directing the UE to the nearest ePDG. The `ss` prefix appears to be a T-Mobile-specific variant (possibly "secure signaling").

### DNS Record Types for IMS Discovery

Per **3GPP TS 29.303** (DNS Procedures for IMS) and **RFC 3263** (SIP: Locating SIP Servers):

| Record Type | Purpose | Example |
|-------------|---------|---------|
| **NAPTR** | Service discovery — maps domain to SRV records | `ims.mnc260.mcc310.pub.3gppnetwork.org → NAPTR → _sip._udp.ims...` |
| **SRV** | Service + port + hostname | `_sip._udp.ims... → SRV 0 0 5060 pcscf.ims...` |
| **A/AAAA** | IP address resolution | `pcscf.ims... → A 10.1.1.1` |

The theoretical DNS-based discovery chain:
```
1. NAPTR lookup on ims.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org
   → Returns replacement: _sip._udp.ims.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org
2. SRV lookup on _sip._udp.ims.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org
   → Returns: 0 0 5060 pcscf.ims.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org
3. A lookup on pcscf.ims.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org
   → Returns: 10.1.1.1
```

**IMPORTANT**: In practice, **most carriers do NOT publish NAPTR/SRV records on the public DNS** for their IMS infrastructure. These records are typically only resolvable on the carrier's internal DNS or the GRX/IPX DNS. Our live DNS queries confirmed this (see §3 below).

---

## 2. P-CSCF Discovery Methods

Per **3GPP TS 24.229** (SIP Call Control) and **3GPP TS 24.228**, the UE can discover the P-CSCF address through five methods, in order of priority:

### Method 1: ISIM EF_PCSCF (Highest Priority)

If the SIM card has an ISIM application, the P-CSCF address may be stored in the **EF_PCSCF** (Elementary File — P-CSCF Address) file on the ISIM, specified in **3GPP TS 31.103** §4.2.8.

- EF_PCSCF can contain one or more P-CSCF addresses (FQDN or IPv4/IPv6)
- The ISIM also stores the **Home Network Domain Name** (EF_HDOMAIN) — e.g., `ims.mnc001.mcc001.pub.3gppnetwork.org`
- pySim can read EF_PCSCF: `pySim-read.py` supports reading this file
- pySim can also **write** EF_PCSCF when programming sysmoISIM-SJA5 cards: `--pcscf pcscf.ims.mnc001.mcc001.3gppnetwork.org`

**Limitation**: Most commercial ISIM cards do NOT have EF_PCSCF populated — it's typically empty, and the P-CSCF is discovered via other methods.

### Method 2: PDP Context PCO (Primary Method for Cellular)

When the UE establishes a dedicated EPS bearer for the IMS APN (QCI=5), it requests the P-CSCF address in the **Protocol Configuration Options (PCO)** Information Element. The network responds with the P-CSCF IPv4 and/or IPv6 address(es).

This is the **most commonly used method** on commercial networks, as confirmed by Nick vs Networking's analysis:
- UE sends PDN Connectivity Request with IMS APN
- UE includes "P-CSCF IPv4 Address Request" in PCO
- Network responds with P-CSCF IP in PCO answer
- Multiple P-CSCF addresses can be provided for redundancy

**Limitation**: Only available during cellular attach — not accessible from a headless server without a cellular modem.

### Method 3: ACS XML (LBO_P-CSCF_Address)

The RCS Auto Configuration Server delivers the P-CSCF address in the ACS XML provisioning document, in the `LBO_P-CSCF_Address` characteristic:

```xml
<characteristic type="LBO_P-CSCF_Address">
    <parm name="Address" value="ss.epdg.epc.mnc001.mcc001.pub.3gppnetwork.org"/>
    <parm name="AddressType" value="FQDN"/>
</characteristic>
```

This is the **primary method for RCS-specific P-CSCF discovery** and is particularly relevant for headless clients that can fetch ACS XML over HTTP/HTTPS. See `rcs_acs_provisioning_report.md` §5 for full details.

**Note**: The `LBO` prefix stands for "Local Break-Out" — meaning the P-CSCF is in the visited network. For home-routed IMS, the P-CSCF may differ.

### Method 4: DHCP

If P-CSCF is not obtained via PCO or ISIM, the UE can use DHCP on the IMS APN interface:

- **DHCP Option 120** (SIP Servers DHCP Option, RFC 3361): Carries the P-CSCF FQDN or IP
- **DHCPv6 Option 21** (SIP Servers): Same for IPv6

This method is rarely used on commercial networks (most use PCO), but is defined in the standard as a fallback.

### Method 5: DNS NAPTR/SRV (Lowest Priority)

The UE can use DNS to discover the P-CSCF by querying NAPTR and SRV records for the IMS domain, as described in §1 above.

**Critical limitation**: DNS-based IMS discovery on the **public Internet** typically fails because:
1. Most carriers do NOT publish NAPTR/SRV records on public DNS
2. These records are only available on the carrier's internal DNS or GRX/IPX DNS
3. The carrier's DNS zone is authoritative (SOA record exists) but NAPTR/SRV records are empty

### Method 6: ePDG/IKEv2 (WiFi Calling Path)

When connected via WiFi (untrusted non-3GPP access), the UE discovers the P-CSCF through the ePDG:

1. UE resolves ePDG FQDN via DNS → gets ePDG IP
2. UE establishes IKEv2 tunnel to ePDG (EAP-AKA authentication using SIM)
3. ePDG provides P-CSCF address via **IKEv2 configuration payload** (RFC 7651) or **PCO via DHCP inside the tunnel**
4. UE sends SIP REGISTER to the P-CSCF through the IPsec tunnel

This is the path that enables IMS access from **any IP address** (including data centers), as the ePDG accepts IKEv2 connections from any source IP after EAP-AKA authentication.

---

## 3. DNS Query Results

All DNS queries were executed on 2026-05-16 from a public Internet server.

### 3.1 SIP SRV Records for IMS Domains

| Query | Result | SOA |
|-------|--------|-----|
| `_sip._udp.ims.mnc260.mcc310.pub.3gppnetwork.org` (T-Mobile US) | **NXDOMAIN** (no SRV record) | `anppol31.gsm1900.org` (T-Mobile DNS) |
| `_sip._udp.ims.mnc410.mcc310.pub.3gppnetwork.org` (AT&T) | **NXDOMAIN** (no SRV record) | `alpinetdns.mycingular.net` (AT&T DNS) |
| `_sip._udp.ims.mnc012.mcc311.pub.3gppnetwork.org` (Verizon) | **NOERROR, 0 answers** | `dns51.cloudns.net` (generic) |
| `_sip._udp.ims.mnc874.mcc405.pub.3gppnetwork.org` (Jio India) | **NXDOMAIN** | — |
| `_sip._udp.ims.mnc010.mcc404.pub.3gppnetwork.org` (Airtel India) | **NXDOMAIN** | `dns51.cloudns.net` (generic) |

**Conclusion**: No carrier publishes SIP SRV records on public DNS for their IMS domains. T-Mobile and AT&T have authoritative DNS zones (their SOA records are returned), but no IMS SRV records are published.

### 3.2 NAPTR Records for IMS Domains

| Query | Result |
|-------|--------|
| `ims.mnc260.mcc310.pub.3gppnetwork.org` (T-Mobile) | **NOERROR, 0 answers** — NAPTR exists in zone but no records returned |
| `ims.mnc410.mcc310.pub.3gppnetwork.org` (AT&T) | **NOERROR, 0 answers** |
| `ims.mnc874.mcc405.pub.3gppnetwork.org` (Jio) | **NOERROR, 0 answers** |
| `ims.mnc010.mcc404.pub.3gppnetwork.org` (Airtel) | **NOERROR, 0 answers** |

### 3.3 NAPTR Records for ePDG Domains

| Query | Result |
|-------|--------|
| `epdg.epc.mnc260.mcc310.pub.3gppnetwork.org` (T-Mobile) | NAPTR → `epdg.epc.geo.mnc260.mcc310.pub.3gppnetwork.org` (redirects to geo-aware FQDN) |
| `epdg.epc.geo.mnc260.mcc310.pub.3gppnetwork.org` (T-Mobile geo) | **NOERROR, 0 NAPTR answers** (uses A record directly) |

### 3.4 ePDG A Record Lookups

| Carrier | FQDN | Resolves? | IP Address(es) |
|---------|------|-----------|-----------------|
| **T-Mobile US** | `epdg.epc.geo.mnc260.mcc310.pub.3gppnetwork.org` | ✅ | `208.54.34.3` (~26 IPs per Netify) |
| **T-Mobile US (ss)** | `ss.epdg.epc.geo.mnc260.mcc310.pub.3gppnetwork.org` | ✅ | `208.54.5.195` |
| **AT&T** | `epdg.epc.mnc410.mcc310.pub.3gppnetwork.org` | ✅ (CNAME) | → `epdg.epc.att.net` → `epdg.epc.att-idns.net` → `107.122.31.31` |
| **Verizon** | `epdg.epc.mnc012.mcc311.pub.3gppnetwork.org` | ✅ | `127.0.0.1` (broken/misconfigured) |
| **Verizon (480)** | `epdg.epc.mnc480.mcc311.pub.3gppnetwork.org` | ❌ | NXDOMAIN (confirmed by Cloudflare community) |
| **Jio India** | `epdg.epc.mnc874.mcc405.pub.3gppnetwork.org` | ✅ | `49.44.190.248` |
| **Jio India (854)** | `epdg.epc.mnc854.mcc405.pub.3gppnetwork.org` | ✅ | `49.44.190.243`, `49.44.190.248` |
| **Airtel India** | `epdg.epc.mnc010.mcc404.pub.3gppnetwork.org` | ✅ | `106.201.214.127` |
| **Vodafone UK** | `epdg.epc.mnc015.mcc234.pub.3gppnetwork.org` | ✅ (CNAME) | → `epdg.vodafone.co.uk` → `88.82.11.208`, `88.82.11.221`, `148.252.188.96` |
| **EE UK** | `epdg.epc.mnc030.mcc234.pub.3gppnetwork.org` | ✅ | `31.94.76.1`, `31.94.76.2`, `31.94.76.5`, `31.94.76.6`, `31.94.76.10` |
| **Three UK** | `epdg.epc.mnc020.mcc234.pub.3gppnetwork.org` | ✅ | `185.153.237.96` |
| **Orange France** | `epdg.epc.mnc001.mcc208.pub.3gppnetwork.org` | ✅ | `80.12.36.221`, `80.12.25.138` |
| **Deutsche Telekom DE** | `epdg.epc.mnc001.mcc262.pub.3gppnetwork.org` | ✅ | `109.237.187.141`–`109.237.187.159` (12 IPs) |
| **Movistar ES** | `epdg.epc.mnc007.mcc214.pub.3gppnetwork.org` | ✅ | `213.4.100.129`, `213.4.100.137`, `213.4.100.145`, `213.4.100.153` |
| **NTT Docomo JP** | `epdg.epc.mnc010.mcc440.pub.3gppnetwork.org` | ❌ | `127.0.0.1` (broken) |
| **Telstra AU** | `epdg.epc.mnc001.mcc505.pub.3gppnetwork.org` | ✅ | `149.135.224.26`, `149.135.226.11`, `149.135.232.3`, `149.135.233.3` |
| **Singtel SG** | `epdg.epc.mnc001.mcc525.pub.3gppnetwork.org` | ✅ | `111.65.100.1`, `111.65.100.17` |
| **Rogers CA** | `epdg.epc.mnc720.mcc302.pub.3gppnetwork.org` | ✅ | `209.148.157.48` |
| **Bell CA** | `epdg.epc.mnc640.mcc302.pub.3gppnetwork.org` | ✅ | `69.158.207.146` |
| **US Cellular** | `epdg.epc.mnc028.mcc311.pub.3gppnetwork.org` | ❌ | `127.0.0.1` (broken) |
| **Sprint/T-Mobile** | `epdg.epc.mnc120.mcc310.pub.3gppnetwork.org` | ❌ | NXDOMAIN |
| **Globe PH** | `epdg.epc.mnc002.mcc515.pub.3gppnetwork.org` | ❌ | NXDOMAIN |

### 3.5 IMS Domain A Records

| FQDN | Resolves? |
|------|-----------|
| `ims.mnc260.mcc310.pub.3gppnetwork.org` (T-Mobile) | ❌ No A record |
| `ims.mnc410.mcc310.pub.3gppnetwork.org` (AT&T) | ❌ No A record |

### 3.6 BSF (GBA Bootstrapping Server) A Records

| FQDN | Resolves? | IP |
|------|-----------|-----|
| `bsf.mnc260.mcc310.pub.3gppnetwork.org` (T-Mobile) | ✅ (CNAME) | → `bsf.sipgeo.t-mobile.com` → `208.54.150.87` |
| `bsf.mnc410.mcc310.pub.3gppnetwork.org` (AT&T) | ❌ | — |

### Key Findings from DNS Queries

1. **ePDG FQDNs are publicly resolvable** for most carriers — this is by design, as UEs need to discover ePDGs from any network
2. **IMS domain NAPTR/SRV records are NOT publicly resolvable** — carriers keep IMS infrastructure private
3. **RCS ACS config domains ARE publicly resolvable** — they serve HTTP/HTTPS to any client
4. **BSF domains may or may not be resolvable** — T-Mobile's BSF resolves, AT&T's doesn't
5. Some carriers use **CNAME chains** to their own domains (AT&T → `att.net`, Vodafone → `vodafone.co.uk`)
6. A few carriers return `127.0.0.1` for ePDG (Verizon, Docomo, US Cellular) — this appears to be a DNS misconfiguration or intentional blocking of the 3gppnetwork.org ePDG FQDN, as these carriers may use custom ePDG addresses instead
7. **T-Mobile uses a NAPTR redirect** from `epdg.epc.mnc260` to `epdg.epc.geo.mnc260` for geographic load balancing

---

## 4. ACS Server URLs by Carrier

### DNS Resolution Results for config.rcs Domains

| Carrier | FQDN | Resolves? | IP / CNAME |
|---------|------|-----------|------------|
| **T-Mobile US** | `config.rcs.mnc260.mcc310.pub.3gppnetwork.org` | ✅ | → `config.rcs.mnc260.mcc310.pub.3gppnetwork.org.edgekey.net` → `e225072.dsca.akamaiedge.net` → `96.17.180.42`, `96.17.180.44` |
| **AT&T** | `config.rcs.mnc410.mcc310.pub.3gppnetwork.org` | ✅ | → `config.rcs.gslb.mnc410.mcc310.pub.3gppnetwork.org` → `166.216.153.141` |
| **Jio India** | `config.rcs.mnc874.mcc405.pub.3gppnetwork.org` | ✅ | `103.63.128.132` |
| **Verizon (480)** | `config.rcs.mnc480.mcc311.pub.3gppnetwork.org` | ✅ (CNAME) | → `config.rcs.gtm.mnc480.mcc311.pub.3gppnetwork.org` → `127.0.0.1` |
| **Vodafone UK** | `config.rcs.mnc015.mcc234.pub.3gppnetwork.org` | ✅ | `85.205.100.141` |
| **EE UK** | `config.rcs.mnc030.mcc234.pub.3gppnetwork.org` | ✅ | `192.196.181.12`, `192.196.181.13`, `192.196.181.14` |
| **Globe PH** | `config.rcs.mnc002.mcc515.pub.3gppnetwork.org` | ✅ | `72.14.246.6` |
| **Telstra AU** | `config.rcs.mnc001.mcc505.pub.3gppnetwork.org` | ✅ | `144.135.120.170`, `144.135.121.170` |
| **Airtel India** | `config.rcs.mnc010.mcc404.pub.3gppnetwork.org` | ❌ | NXDOMAIN |
| **Orange France** | `config.rcs.mnc001.mcc208.pub.3gppnetwork.org` | ❌ | NXDOMAIN |
| **Three UK** | `config.rcs.mnc020.mcc234.pub.3gppnetwork.org` | ❌ | NXDOMAIN |
| **Verizon (012)** | `config.rcs.mnc012.mcc311.pub.3gppnetwork.org` | ❌ | NXDOMAIN |
| **NTT Docomo JP** | `config.rcs.mnc010.mcc440.pub.3gppnetwork.org` | ❌ | NXDOMAIN |

### ACS Hosting Patterns

| Pattern | Carriers | Notes |
|---------|----------|-------|
| **Akamai CDN** (edgekey.net → akamaiedge.net) | T-Mobile US | Large-scale CDN delivery; likely Google Jibe ACS behind it |
| **Carrier own IP** | AT&T (166.216.153.x), Jio (103.63.128.x) | Self-hosted ACS |
| **GSLB** (Global Server Load Balancing) | AT&T, Verizon | `config.rcs.gslb` or `config.rcs.gtm` subdomain |
| **Google Jibe Cloud** | T-Mobile, Vodafone UK, EE UK, Globe PH, Telstra AU | IP ranges consistent with Google Cloud hosting |
| **No ACS** | Airtel, Orange, Three UK, Docomo | Either uses non-standard ACS URL or Google Jibe bypasses carrier ACS |

---

## 5. Known P-CSCF Addresses from Public Sources

### From ACS XML Captures (ShareTechnote)

The ACS XML parameter `LBO_P-CSCF_Address` typically contains one of these patterns:

| Pattern | Example | Interpretation |
|---------|---------|---------------|
| `ss.epdg.epc.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org` | `ss.epdg.epc.mnc001.mcc001.pub.3gppnetwork.org` | ePDG FQDN — P-CSCF is co-located with or behind the ePDG |
| `pcscf.ims.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org` | Generic | Direct P-CSCF FQDN |
| `outbound.proxy.FQDN` | Carrier-specific | Carrier's own P-CSCF FQDN |

### From Wireshark Captures / PCO Analysis

Based on public captures and Nick vs Networking's analysis:

| Carrier | P-CSCF Discovery Method | P-CSCF Address Source |
|---------|------------------------|----------------------|
| **T-Mobile US** | PCO during EPS bearer + ACS XML | P-CSCF delivered via PCO (IP address) and ACS (FQDN) |
| **AT&T** | PCO during EPS bearer + ACS XML | P-CSCF delivered via PCO |
| **Verizon** | PCO during EPS bearer | P-CSCF via PCO |
| **Jio** | PCO during EPS bearer | P-CSCF via PCO; IMS domain resolves internally |
| **Airtel** | PCO during EPS bearer | P-CSCF via PCO |

### From VoWiFi/ePDG Path (WiFi Calling)

When connecting via ePDG, the P-CSCF address is provided through:
1. **IKEv2 Configuration Payload** (RFC 7651) — `CONFIGURATION_PAYLOAD` with P-CSCF IPv4/IPv6 attributes
2. **DHCP inside the IPSec tunnel** — P-CSCF via DHCP Option 120 after tunnel is established
3. **EAP-AKA authentication** — The IKEv2 SA is established using EAP-AKA (SIM credentials)

### Security Research: ePDG Accessibility

According to the research paper "VoWiFi Security: An Exploration of Non-3GPP Untrusted Access via Public ePDG URLs" (CEUR Workshop, 2024) and "Why E.T. Can't Phone Home" (MobiSys 2024):

- **ePDGs are publicly accessible** from any IP address on the Internet
- The ePDG accepts IKEv2 connection attempts from any source IP
- Authentication is performed via EAP-AKA (using the SIM card's credentials)
- Some carriers implement **IP-based geoblocking** at the ePDG — rejecting IKEv2 connections from IPs outside their home country or outside expected ranges
- The **epdg_discoverer** tool (https://github.com/Spinlogic/epdg_discoverer) successfully resolves ePDG IPs for most global carriers and tests IKEv2 connectivity
- A companion tool **epdg_n3iwf_discoverer** (https://github.com/francozamp2/epdg_n3iwf_discoverer) extends this to 5G N3IWF

---

## 6. Carrier IMS Registration from Non-Carrier IPs

### Can a Headless Server Register on Carrier IMS from a Data Center IP?

The answer is **YES, but with significant caveats** depending on the access path.

### Path 1: Direct SIP to P-CSCF (Cellular Path)

| Factor | Assessment |
|--------|------------|
| P-CSCF reachable from data center? | **Usually NO** — P-CSCF addresses are typically private (10.x.x.x, 192.168.x.x) or only accessible via the carrier's own network |
| P-CSCF accepts SIP from non-carrier IPs? | **Usually NO** — P-CSCF checks source IP against registered UE IP ranges |
| IPSec required? | Yes — SIP signaling over cellular uses IPSec SAs established during AKA registration |
| Conclusion | **Not feasible** without being on the carrier's network |

### Path 2: ePDG / WiFi Calling Path (Most Promising)

| Factor | Assessment |
|--------|------------|
| ePDG reachable from data center? | **Usually YES** — ePDGs have public IP addresses resolvable via public DNS |
| ePDG accepts IKEv2 from any IP? | **YES** — ePDG accepts IKEv2 connections from any source IP |
| EAP-AKA authentication | **Required** — must have physical SIM card in a reader |
| Geoblocking? | **Some carriers block** connections from non-domestic IPs (see below) |
| P-CSCF delivery | **Inside the IKEv2 tunnel** — ePDG provides P-CSCF address via configuration payload |
| IPSec tunnel | **Automatically established** — IKEv2 tunnel carries SIP signaling to P-CSCF |
| Conclusion | **Feasible** for most carriers, with SIM card access |

### Geoblocking by Carriers

The "Why E.T. Can't Phone Home" research paper (arxiv:2403.11759) measured geoblocking at ePDGs worldwide:

| Behavior | Carriers | Notes |
|----------|----------|-------|
| **No geoblocking** | Many carriers globally | ePDG accepts IKEv2 from any country |
| **IP-based geoblocking** | Some carriers | ePDG rejects IKEv2 from IPs outside home country |
| **DNS-based geoblocking** | Some carriers | ePDG FQDN resolves differently (or not at all) based on resolver location |

The paper found that **geoblocking is not universal** — many carriers allow VoWiFi from any location (which is the whole point of WiFi calling while roaming).

### Path 3: ACS-Discovered P-CSCF + Direct SIP

Even if the ACS XML provides a P-CSCF FQDN, directly sending SIP REGISTER to that P-CSCF from a data center IP typically fails because:

1. **IPSec is mandatory** — 3GPP TS 33.203 requires IPSec SAs between UE and P-CSCF
2. **Source IP validation** — P-CSCF validates that SIP comes from an IP assigned to a registered UE
3. **No tunnel** — Without the ePDG tunnel, there's no IPSec SA, and no UE-assigned IP

---

## 7. ePDG and WiFi Calling IMS Access

### How ePDG Enables IMS Over WiFi

The **evolved Packet Data Gateway (ePDG)** is the key enabler for IMS access from non-cellular networks. It provides:

1. **Secure tunnel** — IKEv2/IPSec tunnel between UE and ePDG, authenticated via EAP-AKA (SIM)
2. **Network access** — After authentication, the UE gets an internal IP address via the PGW, just as if it were on the cellular network
3. **P-CSCF delivery** — The ePDG provides P-CSCF address to the UE (via IKEv2 config payload)
4. **SIP routing** — All SIP signaling goes through the IPSec tunnel to the P-CSCF, then through the normal IMS core
5. **Media path** — RTP/MSRP media also flows through the tunnel (or via optimized path)

### VoWiFi Call Flow

```
┌─────────┐     ┌──────┐     ┌─────────┐     ┌──────┐     ┌───────┐     ┌──────┐
│ Headless │     │ WiFi │     │  ePDG   │     │ PGW  │     │P-CSCF│     │S-CSCF│
│  Client  │     │(any) │     │(public) │     │      │     │      │     │      │
└────┬─────┘     └──────┘     └────┬────┘     └──┬───┘     └──┬───┘     └──┬───┘
     │                             │              │            │            │
(1)  │── DNS: epdg.epc.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org ──→│
     │                             │              │            │            │
(2)  │──── IKEv2 SA_INIT ─────────→│              │            │            │
     │←─── IKEv2 SA_INIT resp ─────│              │            │            │
     │                             │              │            │            │
(3)  │──── IKEv2 AUTH (EAP-AKA) ──→│── EAP-AKA ──→3GPP AAA ──→HSS         │
     │     (identity: IMSI@nai)    │              │            │            │
     │←─── EAP-Request/AKA ───────│←── RAND,AUTN ──────────── │            │
     │                             │              │            │            │
(4)  │── SIM computes RES ────────│              │            │            │
     │──── EAP-Response/AKA ────→│── verify RES →│            │            │
     │                             │              │            │            │
(5)  │←─── IKEv2 AUTH success ────│              │            │            │
     │←─── Config Payload:        │              │            │            │
     │     - P-CSCF IPv4/IPv6     │              │            │            │
     │     - Internal IP address  │              │            │            │
     │                             │              │            │            │
(6)  │──── SIP REGISTER ──────────│──────────────→│───────────→│── Cx ────→│
     │     (via IPSec tunnel)     │              │            │            │
     │←─── 401 Unauthorized ──────│←─────────────│←───────────│←─ RAND ──│
     │                             │              │            │            │
(7)  │── SIM computes AKA RES ───│──────────────→│───────────→│── verify ─│
     │←─── 200 OK ───────────────│←─────────────│←───────────│←──────────│
     │     (IMS REGISTERED)       │              │            │            │
```

### ePDG Discovery by the UE

Per 3GPP TS 24.302, the UE discovers the ePDG through:

1. **ISIM EF_EPDGID** — ePDG FQDN or IP stored on the ISIM (if present)
2. **DNS query** — Standard 3gppnetwork.org FQDN resolution (primary method)
3. **Pre-configured FQDN** — Hard-coded in device/carrier configuration
4. **Visited network ePDG** — When roaming, the UE may use the visited network's ePDG

### ePDG Security Architecture

The ePDG implements:
- **IKEv2 with EAP-AKA** — Mutual authentication using SIM credentials
- **IPSec ESP tunnel** — All user traffic (SIP, RTP, data) encrypted
- **NAT traversal** — IKEv2 NAT-T (UDP encapsulation of ESP)
- **MOBIKE** (RFC 4555) — Mobility and multihoming support for IKEv2 (allows UE to change IP without re-establishing tunnel)
- **Multiple IKEv2 transforms** — Supported algorithms vary by carrier; see the USENIX Security 2024 paper on VoWiFi key exchange analysis

---

## 8. Carrier Infrastructure Table

### Major Carrier IMS Infrastructure Mapping

| Carrier | Country | MCC | MNC | IMS Domain | ACS URL | P-CSCF Source | ePDG FQDN | ePDG IP(s) | Notes |
|--------|---------|-----|-----|------------|---------|---------------|-----------|-------------|-------|
| **T-Mobile US** | USA | 310 | 260 | `ims.mnc260.mcc310.pub.3gppnetwork.org` | `config.rcs.mnc260.mcc310.pub.3gppnetwork.org` (Akamai → `96.17.180.42/44`) | PCO + ACS (via ePDG) | `epdg.epc.geo.mnc260.mcc310.pub.3gppnetwork.org` | `208.54.34.3` (+25 more) | Uses `geo` prefix for geographic load balancing; `ss.epdg` variant exists; RCS via Google Jibe |
| **AT&T** | USA | 310 | 410 | `ims.mnc410.mcc310.pub.3gppnetwork.org` | `config.rcs.mnc410.mcc310.pub.3gppnetwork.org` (`166.216.153.141`) | PCO + ACS | `epdg.epc.mnc410.mcc310.pub.3gppnetwork.org` → `epdg.epc.att.net` | `107.122.31.31` | Self-hosted ACS; custom ePDG domain; RCS via Google Jibe |
| **Verizon** | USA | 311 | 480 | `ims.mnc480.mcc311.pub.3gppnetwork.org` | `config.rcs.mnc480.mcc311.pub.3gppnetwork.org` (broken → `127.0.0.1`) | PCO | `epdg.epc.mnc480.mcc311.pub.3gppnetwork.org` | NXDOMAIN | ePDG not resolvable via 3gppnetwork.org; likely uses custom FQDN; RCS via Google Jibe |
| **Jio** | India | 405 | 874/854/855/etc | `ims.mnc874.mcc405.pub.3gppnetwork.org` | `config.rcs.mnc874.mcc405.pub.3gppnetwork.org` (`103.63.128.132`) | PCO | `epdg.epc.mnc874.mcc405.pub.3gppnetwork.org` | `49.44.190.248` | Self-hosted RCS infrastructure; multiple MNCs per circle; VoWiFi supported |
| **Airtel** | India | 404 | 010 | `ims.mnc010.mcc404.pub.3gppnetwork.org` | Not resolvable (NXDOMAIN) | PCO | `epdg.epc.mnc010.mcc404.pub.3gppnetwork.org` | `106.201.214.127` | No 3gppnetwork.org ACS; RCS via Google Jibe; ePDG resolves |
| **Vodafone UK** | UK | 234 | 015 | `ims.mnc015.mcc234.pub.3gppnetwork.org` | `config.rcs.mnc015.mcc234.pub.3gppnetwork.org` (`85.205.100.141`) | PCO + ACS | `epdg.epc.mnc015.mcc234.pub.3gppnetwork.org` → `epdg.vodafone.co.uk` | `88.82.11.208`, `88.82.11.221`, `148.252.188.96` | Custom ePDG domain; ACS resolvable |
| **EE UK** | UK | 234 | 030 | `ims.mnc030.mcc234.pub.3gppnetwork.org` | `config.rcs.mnc030.mcc234.pub.3gppnetwork.org` (`192.196.181.12-14`) | PCO + ACS | `epdg.epc.mnc030.mcc234.pub.3gppnetwork.org` | `31.94.76.1-10` (5 IPs) | Google-hosted ACS; multiple ePDG IPs |
| **Three UK** | UK | 234 | 020 | `ims.mnc020.mcc234.pub.3gppnetwork.org` | Not resolvable (NXDOMAIN) | PCO | `epdg.epc.mnc020.mcc234.pub.3gppnetwork.org` | `185.153.237.96` | No 3gppnetwork.org ACS |
| **Orange France** | France | 208 | 001 | `ims.mnc001.mcc208.pub.3gppnetwork.org` | Not resolvable (NXDOMAIN) | PCO | `epdg.epc.mnc001.mcc208.pub.3gppnetwork.org` | `80.12.36.221`, `80.12.25.138` | TS.43 reference carrier; no 3gppnetwork.org ACS |
| **Deutsche Telekom** | Germany | 262 | 001 | `ims.mnc001.mcc262.pub.3gppnetwork.org` | Not tested | PCO | `epdg.epc.mnc001.mcc262.pub.3gppnetwork.org` | `109.237.187.141-159` (12 IPs) | Large ePDG farm; T-Mobile parent |
| **Movistar/Telefónica** | Spain | 214 | 007 | `ims.mnc007.mcc214.pub.3gppnetwork.org` | Not tested | PCO | `epdg.epc.mnc007.mcc214.pub.3gppnetwork.org` | `213.4.100.129-153` (4 IPs) | Standard 3gppnetwork.org ePDG |
| **Telstra** | Australia | 505 | 001 | `ims.mnc001.mcc505.pub.3gppnetwork.org` | `config.rcs.mnc001.mcc505.pub.3gppnetwork.org` (`144.135.120/121.170`) | PCO + ACS | `epdg.epc.mnc001.mcc505.pub.3gppnetwork.org` | `149.135.224-233.x` (4 IPs) | ACS and ePDG both resolvable |
| **Singtel** | Singapore | 525 | 001 | `ims.mnc001.mcc525.pub.3gppnetwork.org` | Not tested | PCO | `epdg.epc.mnc001.mcc525.pub.3gppnetwork.org` | `111.65.100.1`, `111.65.100.17` | ePDG resolvable |
| **Rogers** | Canada | 302 | 720 | `ims.mnc720.mcc302.pub.3gppnetwork.org` | Not tested | PCO | `epdg.epc.mnc720.mcc302.pub.3gppnetwork.org` | `209.148.157.48` | ePDG resolvable |
| **Bell** | Canada | 302 | 640 | `ims.mnc640.mcc302.pub.3gppnetwork.org` | Not tested | PCO | `epdg.epc.mnc640.mcc302.pub.3gppnetwork.org` | `69.158.207.146` | ePDG resolvable |
| **Globe Telecom** | Philippines | 515 | 002 | `ims.mnc002.mcc515.pub.3gppnetwork.org` | `config.rcs.mnc002.mcc515.pub.3gppnetwork.org` (`72.14.246.6`) | PCO + ACS | `epdg.epc.mnc002.mcc515.pub.3gppnetwork.org` | NXDOMAIN | ACS resolvable but ePDG not via 3gppnetwork.org |

---

## 9. Practical Conclusion

### Can a Headless Server Register on Carrier IMS from a Data Center IP?

**YES — via the ePDG/VoWiFi path, with the following requirements:**

### Requirements

| Requirement | Details | Feasibility |
|-------------|---------|-------------|
| **Physical SIM card** | Must have a real carrier SIM with ISIM/USIM application | ✅ Standard commercial SIMs work |
| **SIM card reader** | PC/SC reader (sysmoOCTSIM, etc.) connected to the server | ✅ Readily available hardware |
| **EAP-AKA implementation** | Must implement EAP-AKA over IKEv2 to authenticate with ePDG | ⚠️ Requires development; strongSwan has partial support |
| **ePDG FQDN/IP** | Resolved via DNS or extracted from SIM | ✅ Most carriers' ePDGs resolve on public DNS |
| **IPSec tunnel** | Must establish IKEv2/IPSec tunnel to ePDG | ✅ Standard VPN technology |
| **SIP stack** | Must send SIP REGISTER through the IPSec tunnel to P-CSCF | ⚠️ Must support IMS AKA authentication |
| **IMS AKA on SIM** | Must compute AKA RES for SIP 401 challenge using SIM | ✅ Via sim-rest-server or direct APDU |
| **Geoblocking** | Some carriers may reject IKEv2 from data center IPs | ⚠️ Not universal; varies by carrier |

### Recommended Architecture for Headless RCS Client

```
┌─────────────────────────────────────────────────────────────────┐
│                     Data Center Server                          │
│                                                                 │
│  ┌────────────┐   ┌──────────────┐   ┌──────────────────────┐  │
│  │ SIM Reader  │   │ IKEv2/EAP-AKA│   │  SIP/RCS Stack      │  │
│  │ (PC/SC)    │←─→│ (strongSwan  │←─→│  (Kamailio/custom)   │  │
│  │ + SIM card │   │  + SIM auth) │   │  + AKA auth          │  │
│  └────────────┘   └──────┬───────┘   └──────────┬───────────┘  │
│                          │                      │               │
│                   IKEv2/IPSec tunnel     SIP REGISTER          │
│                          │              (inside tunnel)        │
└──────────────────────────┼──────────────┼──────────────────────┘
                           │              │
                    ┌──────┴──────┐   ┌────┴─────┐
                    │   ePDG     │   │  P-CSCF  │
                    │ (public)  │──→│ (inside  │──→ IMS Core
                    │            │   │ carrier  │
                    └────────────┘   │ network) │
                                    └──────────┘
```

### Step-by-Step for Headless IMS Registration

1. **Read SIM card** — Extract IMSI, MCC, MNC from SIM via PC/SC reader
2. **Resolve ePDG** — DNS query `epdg.epc.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org`
3. **Establish IKEv2 tunnel** — EAP-AKA authentication using SIM card
4. **Receive P-CSCF address** — From IKEv2 configuration payload
5. **Fetch ACS XML** (optional) — GET `https://config.rcs.mnc<MNC>.mcc<MCC>.pub.3gppnetwork.org/` for RCS parameters
6. **SIP REGISTER** — Send through IPSec tunnel to P-CSCF with IMS AKA auth (using SIM)
7. **RCS session** — Once registered, send SIP MESSAGE, INVITE, etc.

### Carrier-Specific Feasibility Assessment

| Carrier | ePDG Accessible? | ACS Resolvable? | Geoblocking? | Overall Feasibility |
|---------|-----------------|-----------------|-------------|-------------------|
| **T-Mobile US** | ✅ Yes (geo load-balanced) | ✅ Yes (Akamai CDN) | ⚠️ Possible | **High** — well-documented infrastructure |
| **AT&T** | ✅ Yes (custom domain) | ✅ Yes (self-hosted) | ⚠️ Possible | **High** |
| **Verizon** | ❌ ePDG broken on 3gppnetwork.org | ⚠️ Broken (127.0.0.1) | Unknown | **Low** — may need custom ePDG discovery |
| **Jio India** | ✅ Yes | ✅ Yes (self-hosted) | ⚠️ Possible | **High** |
| **Airtel India** | ✅ Yes | ❌ No 3gppnetwork.org ACS | ⚠️ Possible | **Medium** — ePDG works, but ACS needs alternate discovery |
| **Vodafone UK** | ✅ Yes (custom domain) | ✅ Yes | ⚠️ Possible | **High** |
| **EE UK** | ✅ Yes | ✅ Yes (Google-hosted) | ⚠️ Possible | **High** |
| **Telstra AU** | ✅ Yes | ✅ Yes | ⚠️ Possible | **High** |

### Key Risks and Limitations

1. **Geoblocking** — Some carriers may reject IKEv2 connections from non-domestic data center IPs. Test with the specific carrier's ePDG before committing.
2. **SIM card requirement** — The SIM card must remain physically present in the reader; this is not a software-only solution.
3. **ISIM vs USIM** — ISIM application is preferred for IMS AKA; USIM can work but may require different authentication paths.
4. **Carrier detection** — Anomalous IMS registration patterns (e.g., single SIM registering from a data center IP 24/7) could trigger carrier fraud detection.
5. **SIP timer tuning** — IMS SIP timers (T1, T2, T4) and re-registration intervals must be configured correctly per carrier.
6. **RCS feature negotiation** — Contact header feature tags (+g.3gpp.icsi-ref, +g.3gpp.iari-ref) must be correct for the carrier's RCS AS to accept registration.
7. **No cellular fallback** — A headless server can't fall back to the cellular path if the ePDG path fails.

---

## References

1. **3GPP TS 23.003** — Numbering, Addressing and Identification (ePDG FQDN format in §17)
2. **3GPP TS 24.229** — SIP Call Control (P-CSCF discovery procedures)
3. **3GPP TS 24.302** — Access to the 3GPP EPC via non-3GPP access networks (ePDG selection)
4. **3GPP TS 29.303** — DNS Procedures for IMS
5. **3GPP TS 31.103** — Characteristics of the ISIM application (EF_PCSCF, EF_HDOMAIN)
6. **GSMA IR.67** — DNS Guidelines for Service Providers and GRX and IPX Providers (v21.0)
7. **GSMA RCC.14** — Service Provider Device Configuration (ACS XML format)
8. **RFC 3263** — SIP: Locating SIP Servers
9. **RFC 7651** — 3GPP IMS Option for IKEv2 (P-CSCF address in Configuration Payload)
10. **RFC 4187** — EAP-AKA
11. **Nick vs Networking** — "VoLTE / IMS – P-CSCF Assignment": https://nickvsnetworking.com/volte-ims-p-cscf-assignment/
12. **Nick vs Networking** — "Improving WiFi Calling quality for WiFi Operators": https://nickvsnetworking.com/improving-wifi-calling-quality-for-wifi-operators/
13. **Spinlogic/epdg_discoverer** — https://github.com/Spinlogic/epdg_discoverer
14. **"Why E.T. Can't Phone Home"** — IP-based geoblocking at ePDG servers: https://arxiv.org/abs/2403.11759
15. **"VoWiFi Security: An Exploration of Non-3GPP Untrusted Access"** — CEUR Workshop Vol-3731, 2024
16. **"Key Exchange Stories from Commercial VoWiFi Deployments"** — USENIX Security 2024
17. **ShareTechnote** — IMS P-CSCF Discovery: https://www.sharetechnote.com/html/IMS_SIP_CSCF_Discovery.html
18. **ShareTechnote** — ePDG Discovery: https://www.sharetechnote.com/html/Handbook_LTE_WiFi_Offload_ePDG_Discovery.html
19. **Dr Moazzam Tiwana** — "P-CSCF Discovery": https://drmoazzam.com/4-ims-procedure-p-cscf-discovery
20. **SystemTek** — "What is 3gppnetwork.org": https://www.systemtek.co.uk/2024/11/what-is-3gppnetwork-org-resolved/
21. **Netify.ai** — Hostname information for 3gppnetwork.org subdomains

---

*Report generated 2026-05-16 from live DNS queries, web research, and analysis of existing research documents (rcs_acs_provisioning_report.md, ts43-entitlement-eapaka.md, open5gs-ims-rcs-analysis-report.md).*
