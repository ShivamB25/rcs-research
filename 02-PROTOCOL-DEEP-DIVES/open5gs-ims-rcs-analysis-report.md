# Open5GS + Kamailio IMS + RCS Feasibility Analysis Report

## 1. Full Architecture of docker_open5gs + Kamailio IMS Stack

### 1.1 Core Network (EPC/5GC) - Open5GS
The docker_open5gs project provides a complete containerized 4G+5G core:

**4G EPC Components:**
| Component | Function | Docker Service |
|-----------|----------|----------------|
| MME | Mobility Management Entity | `mme` |
| SGW-C | Serving Gateway Control | `sgwc` |
| SGW-U | Serving Gateway User Plane | `sgwu` |
| PGW-C | PDN Gateway Control | `pgwc` |
| PGW-U | PDN Gateway User Plane | `pgwu` |
| HSS | Home Subscriber Server | `hss` (Open5GS built-in) |
| PCRF | Policy and Charging Rules | `pcrf` |

**5GC Components (SA mode):**
| Component | Function | Docker Service |
|-----------|----------|----------------|
| AMF | Access and Mobility Management | `amf` |
| SMF | Session Management | `smf` |
| UPF | User Plane Function | `upf` |
| AUSF | Authentication Server | `ausf` |
| UDM | Unified Data Management | `udm` |
| UDR | Unified Data Repository | `udr` |
| BSF | Binding Support Function | `bsf` |
| NRF | Network Repository Function | `nrf` |
| NSSF | Network Slice Selection | `nssf` |
| SCP | Service Communication Proxy | `scp` |

### 1.2 IMS Core - Kamailio
The IMS core is built on Kamailio SIP server (custom fork by herlesupreeth, branch 5.3) with dedicated IMS modules:

| Component | Port | Database | Key Modules |
|-----------|------|----------|-------------|
| **P-CSCF** | 5060/5061 (SIP), 3868 (Diameter) | `pcscf` (MySQL) | `ims_auth`, `ims_registrar_pcscf`, `ims_usrloc_pcscf`, `ims_dialog`, `ims_qos`, `ims_ipsec_pcscf`, `ims_charging` |
| **I-CSCF** | 4060/4061 (SIP), 3868 (Diameter) | `icscf` (MySQL) | `ims_icscf`, `cdp`, `cdp_avp`, `ims_diameter_server` |
| **S-CSCF** | 6060/6061 (SIP), 3868 (Diameter) | `scscf` (MySQL) | `ims_registrar_scscf`, `ims_usrloc_scscf`, `ims_auth`, `ims_isc`, `ims_charging`, `ims_ocs`, `ims_dialog` |

**IMS Databases (MySQL):**
- `pcscf`: active_watchers, dialog_in/out, location, presentity, pua, xcap
- `scscf`: active_watchers, contact, impu, impu_contact, impu_subscriber, subscriber, ro_session, presentity, pua, xcap
- `icscf`: nds_trusted_domains, s_cscf, s_cscf_capabilities

### 1.3 Supporting IMS Components
| Component | Function |
|-----------|----------|
| **FHoSS** (OpenIMSCore) | IMS HSS with web console (port 8080) - stores IMPI/IMPU/IMSU, handles Diameter Cx interface |
| **PyHSS** | Alternative lightweight IMS HSS (used in some docker configs) |
| **rtpengine** | Media relay for RTP traffic |
| **DNS (bind9)** | Resolves IMS domain names (pcscf.ims.mnc001.mcc001.3gppnetwork.org, etc.) |
| **osmohlr** | For SMS over SGs |

### 1.4 RAN
| Component | Function |
|-----------|----------|
| **srsRAN_4G** | eNodeB (software-defined, with USRP B210 or similar SDR) |
| **UERANSIM** | 5G gNB + UE simulator |

### 1.5 Network Topology
```
UE <--(Uu)--> eNB/gNB <--(S1AP/NGAP)--> MME/AMF
                                          |
                                    SGW-C/SMF <--(PFCP)--> SGW-U/UPF
                                          |                    |
                                    PGW-C/SMF               Internet
                                          |                    
                                    PGW-U/UPF                
                                          |                    
                               UE IMS APN (QCI=5)            
                                          |                    
                                    P-CSCF:5060               
                                          |                    
                                    I-CSCF:4060 <--(Cx/Diameter)--> HSS
                                          |                    
                                    S-CSCF:6060               
                                          |                    
                                    Application Servers (VoLTE AS, etc.)
```

**DNS Zone Example:**
```
ims.mnc001.mcc001.3gppnetwork.org:
  pcscf    IN A    <HOST_IP>
  _sip._udp.pcscf  SRV 0 0 5060 pcscf
  icscf    IN A    <HOST_IP>
  _sip._udp         SRV 0 0 4060 icscf
  scscf    IN A    <HOST_IP>
  _sip._udp.scscf  SRV 0 0 6060 scscf
  hss      IN A    <HOST_IP>
```

**APN Configuration:**
- `internet`: QCI=9, ARP=8 (default data bearer)
- `ims`: QCI=5, ARP=1 (IMS signaling) + QCI=1, ARP=2 (voice) + QCI=2, ARP=4 (video)

---

## 2. Components Needed for RCS Beyond VoLTE

The current docker_open5gs stack provides **VoLTE only** (SIP registration + voice/video calls via INVITE). RCS requires significantly more:

### 2.1 Required Additional IMS Components

| Component | Purpose | Standards | Status in Stack |
|-----------|---------|-----------|-----------------|
| **RCS Application Server (RCS AS)** | Core RCS logic: 1-1 chat, group chat, file transfer, read receipts, typing indicators | GSMA RCC.07, TS 24.227 | **MISSING** |
| **Presence Server** | Capability discovery, availability status | RFC 3856, RFC 3903 | **PARTIAL** - Kamailio has presence modules loaded but not configured for RCS |
| **XDM Server (XML Document Management)** | Shared XDMS for presence rules, group lists, resource lists | OMA XDMS TS | **MISSING** |
| **Chat Server / Conferencing AS** | Group chat (MSRP-based or SIP MESSAGE-based) | RFC 4975 (MSRP), GSMA RCC.07 | **MISSING** |
| **File Transfer Server** | HTTP/MSRP file transfer, store & forward | GSMA RCC.07 | **MISSING** |
| **STUN/TURN Server** | NAT traversal for MSRP/media | RFC 5389 | **MISSING** |

### 2.2 SIP Protocol Extensions for RCS

RCS introduces specific SIP header parameters that must be handled:

**Contact header feature tags (REGISTER):**
```
+sip.instance="<urn:gsma:imei:XXXXXXX-XXXXXX-X>"
+g.oma.sip-im
+g.3gpp.iari-ref="urn:urn-7:3gpp-application.ims.iari.rcse.im,urn:urn-7:3gpp-application.ims.iari.rcse.ft,..."
+g.3gpp.icsi-ref="urn:urn-7:3gpp-service.ims.icsi.gsma.rcs.extension"
```

**Accept-Contact header (SUBSCRIBE, OPTIONS):**
```
+g.oma.sip-im;+g.3gpp.icsi-ref="urn:urn-7:3gpp-service.ims.icsi.gsma.ipcall"
+g.3gpp.iari-ref="urn:urn-7:3gpp-application.ims.iari.rcse.im,..."
```

**Key IARI (IMS Application Reference Identifier) values:**
| IARI | RCS Feature |
|------|-------------|
| `urn:urn-7:3gpp-application.ims.iari.rcse.im` | Standalone messaging |
| `urn:urn-7:3gpp-application.ims.iari.rcse.ft` | File transfer |
| `urn:urn-7:3gpp-application.ims.iari.rcs.fthttp` | File transfer over HTTP |
| `urn:urn-7:3gpp-application.ims.iari.rcs.ftthumb` | File transfer thumbnails |
| `urn:urn-7:3gpp-application.ims.iari.rcs.ext.streaming` | Video sharing / streaming |
| `urn:urn-7:3gpp-application.ims.iari.rcs.ext.messaging` | Extended messaging |
| `urn:urn-7:3gpp-application.ims.iari.rcs.geopush` | Geolocation push |

**Key ICSI (IMS Communication Service Identifier) values:**
| ICSI | Service |
|------|---------|
| `urn:urn-7:3gpp-service.ims.icsi.gsma.rcs.extension` | RCS extension services |
| `urn:urn-7:3gpp-service.ims.icsi.gsma.ipcall` | IP voice call |
| `urn:urn-7:3gpp-service.ims.icsi.gsma.ipvideo` | IP video call |

### 2.3 Presence Infrastructure

The Kamailio IMS modules list already includes:
- `presence`, `presence_conference`, `presence_dialoginfo`, `presence_mwi`, `presence_profile`, `presence_reginfo`, `presence_xml`
- `pua`, `pua_bla`, `pua_dialoginfo`, `pua_reginfo`, `pua_rpc`, `pua_usrloc`, `pua_xmpp`
- `rls` (Resource List Server) - **NOT included** in current modules.lst
- `xcap_client`, `xcap_server` - present but not configured for RCS XDMS

These are loaded but only configured for VoLTE dialog-info. RCS needs:
1. **Presence publication** from RCS AS when user's capabilities change
2. **Presence subscription** from UE to watch other users' capabilities
3. **RLS (Resource List Server)** for batch presence queries (contact list)
4. **XCAP manipulation** for presence rules and resource lists

---

## 3. RCS Registration Status on docker_open5gs

### 3.1 GitHub Issues Search
**Search query:** `RCS` on `herlesupreeth/docker_open5gs` issues

**Result: ZERO matching issues.** The GitHub issues search returned "No results" — no one has reported attempting or achieving RCS on the docker_open5gs stack.

### 3.2 Related Community Findings
- The `android-rcs/rcsjta` project (RCS-e stack for Android) has an issue #264 asking about IMS servers for RCS client testing — no Open5GS solutions were cited
- Reddit r/UniversalProfile threads confirm no open-source RCS server stack exists
- The `jega-ms/RCS-Server` repo on GitHub is described as "RCS Server Using Kamailio" but appears to be a minimal/experimental implementation

### 3.3 What IS Working
- VoLTE SIP registration ✅
- Voice/video calls (INVITE/200 OK) ✅
- IPSec support on P-CSCF ✅
- IMS charging (Ro interface) ✅
- SMS over SGs ✅
- SMS over IMS **partially** (issue #68 documents problems)

### 3.4 What is NOT Working for RCS
- No RCS AS deployed or configured ❌
- No MSRP relay for chat ❌
- No presence/capability exchange for RCS ❌
- No XDM server ❌
- S-CSCF third-party registration to RCS AS not configured ❌
- Feature tag handling (IARI/ICSI) not implemented in S-CSCF routing ❌

---

## 4. Kamailio IMS Config for S-CSCF with RCS Feature Tags

### 4.1 Current S-CSCF Configuration
The S-CSCF in docker_open5gs (from `Kamailio_IMS_Config` repo, branch 5.3) handles:
- SIP REGISTER processing with IMS-AKA authentication
- Third-party registration to Application Servers via `ims_isc` module
- Diameter Cx interface to HSS for user profile retrieval
- Initial Filter Criteria (iFC) evaluation for routing to AS

### 4.2 What Needs to Change for RCS

The S-CSCF must be configured to:

1. **Parse RCS feature tags from REGISTER Contact header:**
```kamailio
# Extract ICSI from Contact
$var(icsi) = $hdr(Contact);
# Parse +g.3gpp.icsi-ref and +g.3gpp.iari-ref parameters
```

2. **Route to RCS AS based on ICSI/IARI:**
The S-CSCF uses Initial Filter Criteria (iFC) from HSS to decide when to route to an AS. For RCS, you need iFC rules like:
```
If REGISTER contains +g.3gpp.icsi-ref containing "gsma.rcs"
  → Third-party REGISTER to sip:rcs-as.ims.mnc001.mcc001.3gppnetwork.org
If INVITE/MESSAGE with ICSI "urn:urn-7:3gpp-service.ims.icsi.gsma.rcs.extension"
  → Route to RCS AS
```

3. **HSS iFC configuration for RCS AS:**
In FHoSS, add an Application Server entry:
```
AS Name: RCS-AS
SIP Server URI: sip:rcs-as.ims.mnc001.mcc001.3gppnetwork.org
Default Handling: SESSION_CONTINUED
iFC: Trigger on REGISTER + INVITE + MESSAGE + SUBSCRIBE with RCS ICSI/IARI
```

4. **Third-party registration handling in S-CSCF config (`kamailio_scscf.cfg`):**
```kamailio
# In the REGISTER handling block, after successful auth:
# The ims_isc module handles third-party registration
# based on iFC from HSS - just needs AS provisioned in HSS
```

The key insight is that **the S-CSCF doesn't need major code changes** — it already supports iFC-based routing and third-party registration. The missing piece is provisioning the RCS AS in HSS and implementing the RCS AS itself.

---

## 5. OpenSIPS RCS Capability Management Tutorial Summary

Source: https://www.opensips.org/Documentation/Tutorials-RCS-Managing-Capabilities (by Liviu Chircu)

### 5.1 Core Concept
RCS capabilities are expressed as SIP Contact header parameters and Accept-Contact header parameters (per RFC 3841). Each RCS feature maps to a specific feature tag.

### 5.2 Iterating Capabilities
```opensips
$var(caps) = $(hdr(Contact){nameaddr.params});
$var(i) = 0;
while ($(var(caps){s.select,$var(i),;}) != NULL) {
    $var(cap) = $(var(caps){param.name,$var(i)});
    $var(val) = $(var(caps){param.valueat,$var(i)});
    
    # Special handling for +g.3gpp.iari-ref which contains sub-list
    if ($var(cap) == "+g.3gpp.iari-ref") {
        $var(j) = 0;
        while ($(var(val){s.select,$var(j),,}) != NULL) {
            $var(subcap) = $(var(val){s.select,$var(j),,}{s.unescape.param});
            xlog("  iari-ref: $var(subcap)\n");
            $var(j) += 1;
        }
    }
    $var(i) += 1;
}
```

### 5.3 Modifying Capabilities (Removing/Adding)
To remove a capability (e.g., File Transfer) and add another (e.g., Geolocation Push):
1. Iterate through all capabilities
2. Filter out unwanted ones (regex match on IARI)
3. Build new capability string
4. `remove_hf("Accept-Contact")` then `append_hf("Accept-Contact: $var(new_caps)\r\n")`

### 5.4 Key Takeaway
This approach works in both OpenSIPS and Kamailio (similar scripting syntax). A Kamailio-based P-CSCF or S-CSCF can use similar transformations to inspect, filter, or modify RCS capability tags during registration or call setup. The `{s.unescape.param}` transformation is critical for decoding hex-encoded URIs in IARI/ICSI values.

---

## 6. Programming sysmoISIM-SJA5 Cards with IMS Credentials

### 6.1 Card Specifications
The **sysmoISIM-SJA5** is a 3GPP Release 17 compliant programmable SIM/USIM/ISIM card:
- Supports 2G (SIM), 3G/4G (USIM), and IMS/VoLTE (ISIM) applications
- Also supports HPSIM (5G)
- Available in 2FF/3FF/4FF form factors
- Ships with ADM keys for programming
- Can use shared or separate K/OP keys across SIM, USIM, ISIM applications

### 6.2 Programming Tools
Two tools are commonly used:

**Option A: `pySim-shell` (Recommended, modern)**
- From Osmocom's `pysim` repository: https://github.com/osmocom/pysim
- Interactive shell for advanced card programming
- Supports ISIM application programming

**Option B: `pySim-prog.py` (Legacy, simpler)**
- One-shot programming with command-line flags

### 6.3 Programming Procedure with pySim-prog.py

```bash
./pySim-prog.py -p 0 \
  -n "LibreCellular" \         # Network display name
  -c 44 \                       # Country code (issuer)
  -x 001 \                      # MCC
  -y 01 \                       # MNC
  -s <ICCID> \                  # Card serial (from sysmocom)
  -a <ADM1> \                   # Admin key (from sysmocom)
  -i <IMSI> \                   # e.g., 001010123456789
  --msisdn <MSISDN> \           # Phone number
  -k <Ki> \                     # 32-digit hex key (or auto-generated)
  -o <OPc> \                    # 32-digit hex OPc (or auto-generated)
  --epdgid epdg.epc.mnc001.mcc001.pub.3gppnetwork.org \
  --pcscf pcscf.ims.mnc001.mcc001.3gppnetwork.org \
  --ims-hdomain ims.mnc001.mcc001.3gppnetwork.org \
  --impi <IMSI>@ims.mnc001.mcc001.3gppnetwork.org \
  --impu sip:<IMSI>@ims.mnc001.mcc001.3gppnetwork.org
```

### 6.4 IMS-Specific Parameters

| Parameter | ISIM Field | Example Value |
|-----------|------------|---------------|
| `--impi` | IMPI (IMS Private Identity) | `001010123456789@ims.mnc001.mcc001.3gppnetwork.org` |
| `--impu` | IMPU (IMS Public Identity) | `sip:001010123456789@ims.mnc001.mcc001.3gppnetwork.org` |
| `--pcscf` | P-CSCF address | `pcscf.ims.mnc001.mcc001.3gppnetwork.org` |
| `--ims-hdomain` | Home Network Domain | `ims.mnc001.mcc001.3gppnetwork.org` |
| `--epdgid` | ePDG FQDN (for VoWiFi) | `epdg.epc.mnc001.mcc001.pub.3gppnetwork.org` |

### 6.5 Security Parameters
| Parameter | Description | Where Used |
|-----------|-------------|------------|
| **K** | 128-bit subscriber key | Shared secret between ISIM and HSS |
| **OP/OPc** | Operator Variant key | Derived in HSS; OPc is on card |
| **SQN** | Sequence number | Must be synchronized (or disable SQN check) |
| **AMF** | Authentication Management Field | Typically `8000` for test networks |
| **ADM1** | Admin key for card programming | Supplied by sysmocom with each card |

**Important:** Disable SQN check on Sysmocom cards using `sysmo-usim-tool` to avoid synchronization issues during testing:
```bash
sysmo-isim-tool.sja5.py --disable-sqn-check
```

### 6.6 HSS Provisioning (FHoSS Web Console)
After programming the SIM card, you must also provision in FHoSS:
1. Create IMSU with name = IMSI
2. Create IMPI: `<IMSI>@ims.mnc001.mcc001.3gppnetwork.org` with K, OP, AMF, SQN matching card
3. Create IMPUs:
   - `sip:<IMSI>@ims.mnc001.mcc001.3gppnetwork.org` (IMS-derived)
   - `tel:<MSISDN>` (E.164 tel URI)
   - `sip:<MSISDN>@ims.mnc001.mcc001.3gppnetwork.org`
4. Add IMPUs to implicit registration set

---

## 7. What's Missing to Make RCS Work on a Self-Hosted Stack

### 7.1 Critical Missing Components (Must-Have)

1. **RCS Application Server** — This is the most critical missing piece. It must:
   - Handle SIP MESSAGE for standalone messaging (1-1 chat)
   - Handle SIP INVITE with MSRP for session-based messaging
   - Implement file transfer (HTTP-based per RCS Universal Profile, or MSRP-based)
   - Generate presence PUBLISH for capability changes
   - Handle group chat (SIP conferencing + MSRP)
   - Process third-party REGISTER from S-CSCF
   - Return SIP 200 OK to MESSAGE with delivery receipts

2. **Presence/RLS Configuration** — While Kamailio has presence modules, they need:
   - Configuration for RCS presence namespace
   - RLS (Resource List Server) for buddy list presence
   - PIDF (Presence Information Data Format) documents with RCS-specific extensions

3. **iFC Rules in HSS** — Initial Filter Criteria must be configured to:
   - Trigger third-party REGISTER to RCS AS on user registration
   - Route SIP MESSAGE to RCS AS
   - Route SIP INVITE with RCS ICSI to RCS AS
   - Route SIP SUBSCRIBE for presence to presence server

### 7.2 Important Missing Components (Should-Have)

4. **MSRP Relay** — For session-based messaging (chat sessions), an MSRP relay is needed:
   - Can use Kamailio's `msrp` module or a standalone MSRP relay
   - Required for MSRP SEND within INVITE/SDP session

5. **HTTP File Transfer Server** — RCS Universal Profile uses HTTP for file transfer:
   - Need a web server that accepts file uploads and generates download URLs
   - The RCS AS sends the URL in the SIP MESSAGE body

6. **STUN/TURN Server** — For NAT traversal in MSRP/media sessions

### 7.3 Configuration Changes Needed

7. **S-CSCF iFC configuration** — Provision RCS AS in HSS with appropriate triggers
8. **P-CSCF capability handling** — Parse and forward RCS feature tags properly
9. **DNS entries** — Add `rcs-as.ims.mnc001.mcc001.3gppnetwork.org` to DNS zone
10. **IMS APN** — Already configured (QCI=5), but may need additional QoS for MSRP

---

## 8. IMS Auth Proxy ("Man-in-the-Middle") Feasibility

### 8.1 Concept
Instead of running a full IMS core, could the stack act as a proxy that:
1. Intercepts IMS REGISTER from UE
2. Forwards authentication to the real carrier's IMS core
3. Uses the carrier's IMS for authentication but self-hosts RCS services

### 8.2 Analysis

**This is NOT feasible for the following reasons:**

1. **AKA Authentication is bound to carrier HSS** — The ISIM on the card contains K/OP that matches the carrier's HSS. Your self-hosted HSS cannot generate valid authentication vectors without the same K/OP values. Getting a carrier's K/OP is practically impossible.

2. **No shared keys** — Carriers do not expose subscriber K values. The SIM card's ISIM K is provisioned by the carrier and only shared with their HSS.

3. **IPSec tunnel requirement** — P-CSCF establishes IPSec SAs with the UE during registration. This requires the P-CSCF to act as the security gateway, which means it must complete the AKA challenge-response cycle.

4. **Diameter routing** — The carrier's HSS won't accept Diameter Cx requests from an unknown S-CSCF/I-CSCF.

**Partial workaround (theoretical):**
- If you have a SIM card with known K/OP (like sysmoISIM-SJA5 for test networks), you can run your own HSS with matching credentials
- But this means you're running your own IMS core, not proxying to a carrier
- Real carrier SIM cards have K/OP values that are only known to the carrier

### 8.3 Alternative: SIM Card Clone Approach (ILLEGAL in most jurisdictions)
- Cloning a carrier SIM card's K/OP values is technically possible with some cards
- This would allow your self-hosted HSS to authenticate the same IMSI
- **This is illegal** in virtually all countries and violates carrier terms of service
- Modern SIM cards (like SJA5) have hardware protections against key extraction

### 8.4 Feasible Alternative: Self-Hosted Test Network
The only viable approach is:
1. Use **programmable SIM cards** (sysmoISIM-SJA5) with your own K/OP values
2. Run your own **complete IMS core** (as docker_open5gs provides)
3. Add **RCS AS** to this self-hosted stack
4. UEs connect to your test eNB (srsRAN) using your programmed SIMs

**Limitation:** This only works for devices on your private RAN — not for devices on commercial carrier networks.

---

## 9. Estimated Effort to Add RCS AS Support

### 9.1 Approach A: Build RCS AS from Scratch

| Task | Effort | Notes |
|------|--------|-------|
| RCS AS core (SIP MESSAGE handling, third-party REGISTER) | 3-4 months | Must handle MSRP sessions, MESSAGE routing, delivery receipts |
| Chat functionality (1-1 + group) | 2-3 months | MSRP relay + conferencing AS |
| File transfer (HTTP-based per UP) | 1-2 months | Need upload/download server + URL generation |
| Presence integration | 1-2 months | PUBLISH/SUBSCRIBE/NOTIFY with Kamailio presence |
| HSS iFC provisioning | 1-2 weeks | Configure in FHoSS or PyHSS |
| Kamailio config changes | 2-4 weeks | S-CSCF routing, P-CSCF capability handling |
| MSRP relay setup | 1-2 weeks | Kamailio msrp module or standalone |
| XDM server | 1-2 months | OMA XDMS for presence rules |
| **Total** | **8-14 months** | For 1-2 experienced developers |

### 9.2 Approach B: Integrate with Existing Open-Source Projects

| Task | Effort | Notes |
|------|--------|-------|
| Evaluate `jega-ms/RCS-Server` | 1-2 weeks | Appears experimental, may need significant work |
| Adapt OpenSIPS RCS capability handling | 2-4 weeks | Port OpenSIPS scripting patterns to Kamailio |
| Build minimal RCS AS (MESSAGE only) | 1-2 months | Focus on 1-1 messaging first |
| Add presence | 1-2 months | Configure Kamailio presence modules |
| Add file transfer | 1-2 months | HTTP upload server |
| **Total (minimal RCS)** | **4-8 months** | Messaging + presence only |

### 9.3 Approach C: Use Android RCS Client Stack

The `android-rcs/rcsjta` project provides an RCS-e client stack for Android with GSMA APIs. However:
- This is a **client-side** implementation, not a server
- It expects to connect to an IMS core with RCS AS already present
- Does not help with the server-side gap

### 9.4 Minimal Viable RCS (Fastest Path)

To get basic RCS working (1-1 messaging only):

1. **Deploy a simple SIP MESSAGE handler as RCS AS** (2-4 weeks)
   - Accept third-party REGISTER from S-CSCF
   - Route SIP MESSAGE between registered users
   - Send delivery receipts (200 OK with body)
   
2. **Configure HSS iFC for RCS AS** (1 week)
   - Add AS entry pointing to RCS AS
   - Create iFC for MESSAGE and REGISTER triggers

3. **Enable Kamailio presence modules** (1-2 weeks)
   - Already loaded, just need routing config
   - Support SUBSCRIBE/NOTIFY for capability discovery

4. **Configure P-CSCF for RCS feature tags** (1 week)
   - Parse +g.3gpp.icsi-ref and +g.3gpp.iari-ref
   - Route based on RCS ICSI

**Estimated minimum: 4-8 weeks** for basic 1-1 RCS messaging with presence.

---

## 10. Summary and Recommendations

### Key Findings

1. **docker_open5gs provides a solid VoLTE foundation** — Kamailio IMS with P/I/S-CSCF, FHoSS, charging, and IPSec are all working. This is the best starting point for any IMS project.

2. **RCS has NEVER been achieved on this stack** — Zero GitHub issues, zero community reports of RCS on docker_open5gs.

3. **The main blocker is the RCS Application Server** — There is no mature open-source RCS AS available. This must be built or adapted.

4. **Kamailio IMS modules are sufficient for SIP signaling** — The presence, pua, xcap, and ISC modules provide the plumbing. Configuration, not code, is needed.

5. **The S-CSCF's iFC mechanism is the integration point** — No major S-CSCF code changes are needed; just provision the RCS AS in HSS.

6. **IMS auth proxy is NOT feasible** — Carrier SIM cards have secrets locked to carrier HSS. Self-hosted approach requires programmable SIM cards.

7. **sysmoISIM-SJA5 + pySim** provides a clean path for ISIM programming with all IMS parameters.

### Recommended Path Forward

1. **Start with docker_open5gs VoLTE stack** as the foundation
2. **Build a minimal RCS AS** that handles:
   - Third-party REGISTER (subscribe to user registrations)
   - SIP MESSAGE routing (1-1 chat)
   - Basic presence PUBLISH
3. **Configure HSS iFC** to route MESSAGE and REGISTER to RCS AS
4. **Enable Kamailio presence** for capability discovery
5. **Iteratively add** group chat, file transfer, and advanced features

### Risk Factors

- **UE compatibility**: Android RCS clients (Google Messages) may not work with non-carrier IMS — they may hard-code carrier-specific behavior
- **Carrier Privileges**: Android devices require Carrier Privileges to enable VoLTE/IMS on test MCC/MNC (001/01). Use `CoIMS` tool to force-enable.
- **IPv6**: The stack does not support IPv6; some RCS clients may require it
- **MSRP complexity**: Session-based messaging via MSRP adds significant protocol complexity
- **No certification**: Self-hosted RCS will not pass GSMA RCS certification

---

## References

- docker_open5gs: https://github.com/herlesupreeth/docker_open5gs
- Kamailio IMS Config: https://github.com/herlesupreeth/Kamailio_IMS_Config
- Open5GS VoLTE Tutorial: https://open5gs.org/open5gs/docs/tutorial/03-VoLTE-dockerized/
- Open5GS VoLTE Setup: https://open5gs.org/open5gs/docs/tutorial/02-VoLTE-setup/
- APNIC Blog - Deploying Open Source IMS: https://blog.apnic.net/2025/04/03/deploying-open-source-ims-and-mobile-core-networks-with-open5gs/
- OpenSIPS RCS Tutorial: https://www.opensips.org/Documentation/Tutorials-RCS-Managing-Capabilities
- pySim: https://github.com/osmocom/pysim
- sysmoISIM-SJA5 Manual: https://sysmocom.de/manuals/sysmoisim-sja5-manual.pdf
- LibreCellular SIM Programming: https://librecellular.org/user/sim
- CoIMS Wiki (VoLTE override): https://github.com/herlesupreeth/CoIMS_Wiki
- sysmo-usim-tool: https://github.com/sysmocom/sysmo-usim-tool
- RCS-Server (experimental): https://github.com/jega-ms/RCS-Server
- android-rcs/rcsjta: https://github.com/android-rcs/rcsjta
