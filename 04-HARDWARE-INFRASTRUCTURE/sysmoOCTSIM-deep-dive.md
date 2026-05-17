# sysmoOCTSIM Deep Dive Report

**Purpose**: Research for 100-SIM RCS Messaging Farm infrastructure decision  
**Date**: 2026-05-16  
**Sources**: sysmocom.de product pages, sysmoOCTSIM User Manual (v2, March 2025), Ludovic Rousseau blog, pySim documentation, strongSwan issue tracker, PCSC-lite GitHub issues, sysmoSIMBANK product page

---

## 1. Hardware Deep Dive

### 1.1 Exact Specifications

| Parameter | Value |
|---|---|
| **Product** | sysmoOCTSIM — 8-slot smart card reader PCBA |
| **Manufacturer** | sysmocom-systems for mobile communications GmbH (Germany) |
| **USB Version** | USB 2.0 (Mini-B connector or 2.54mm pin header, factory option) |
| **USB Speed** | Full-Speed (12 Mbps) — confirmed from sysmoSIMBANK lsusb output showing `12M` |
| **CCID Compliance** | Yes — USB-CCID v1.1 class device (Vendor ID: 0x1d50, Product ID: 0x6141) |
| **USB Device Class** | Chip/SmartCard (CCID), plus CDC-ACM, Application Specific, DFU interfaces |
| **Power Draw** | 5V DC, typical 120mA (board only), max 670mA (8 × Class-A SIMs @ 70mA each) |
| **External Power** | **Required** — 5V DC barrel jack (5.5mm/2.5mm, center positive) |
| **Form Factor** | 160 × 120 mm four-layer PCBA, two-sided component placement |
| **Stacking Height** | Minimum 13.5 mm between stacked boards |
| **Weight** | ~1 kg (EVK with enclosure) |
| **Mounting** | 5 × M3 mounting holes for spacers/stands |
| **Microcontroller** | Atmel SAM D54/E54 (SAME54N19A: 512KB Flash, 192KB RAM) |
| **SIM Card Front-End** | 8 independent front-end ICs with dedicated UARTs and LDOs |
| **SIM Slots** | 8 × ETSI/3GPP 2FF (Mini-SIM), edge-launch drawer-style |
| **Smart Card Voltage** | 1.8V, 3V, 5V (auto-selected or user-forced) |
| **Smart Card Clock** | 2.5, 5, 10, 20 MHz |
| **Smart Card Baud Rate** | Up to 300 kBps tested, higher speeds possible |
| **Protocol** | ISO 7816-3 T=0 (T=1 available on customer request) |
| **LEDs** | 8 × yellow (per-slot SIM activity) + 1 × green (unit power) + 1 × green (3.3V diagnostic) |
| **Debug Ports** | SWD/JTAG (TagConnect TC2050), 3.3V UART (shared with SIM7), CAN (RFU), Ethernet (RFU) |
| **Firmware Upgrade** | USB DFU (in-field reprogrammable) |
| **Firmware License** | GPLv2+ (FOSS) — osmo-ccid-firmware + osmo-asf4-dfu bootloader |
| **Environmental** | -40°C to +85°C (industrial temp range components) |

### 1.2 USB Controller & CCID Details

- **USB Controller Chip**: Atmel SAME54 — ARM Cortex-M4F based microcontroller
- **CCID Descriptor**:
  - `bMaxSlotIndex = 0x07` (8 slots, indexed 0-7)
  - `bMaxCCIDBusySlots = 8` (all 8 slots can be busy simultaneously)
  - The hardware supports simultaneous/concurrent transactions on all 8 slots
  - **CRITICAL BUG**: The Linux libccid driver does NOT support simultaneous multi-slot access (see §2.2)

### 1.3 Slot Enumeration

Each sysmoOCTSIM appears as **one USB device with one CCID interface exposing 8 slots**. In pcsc_scan, each slot appears as a separate reader context:

```
0: sysmocom sysmoOCTSIM [CCID] (serial_number) 00 00   ← Slot 0
1: sysmocom sysmoOCTSIM [CCID] (serial_number) 00 01   ← Slot 1
2: sysmocom sysmoOCTSIM [CCID] (serial_number) 00 02   ← Slot 2
...
7: sysmocom sysmoOCTSIM [CCID] (serial_number) 00 07   ← Slot 7
```

The two-digit numbers after the serial are: **first digit = device index, second digit = slot index**.

With multiple boards, device index increments:
```
 0-7:   Board 0, slots 0-7  (device index 00, slots 00-07)
 8-15:  Board 1, slots 0-7  (device index 01, slots 00-07)
16-23:  Board 2, slots 0-7  (device index 02, slots 00-07)
...
```

### 1.4 Maximum Boards per USB Bus/Controller

- **USB 2.0 bandwidth**: Each sysmoOCTSIM operates at Full-Speed (12 Mbps). SIM card APDU transactions are very small (typically 200-500 bytes), so bandwidth is NOT a bottleneck even with 13 boards.
- **sysmoSIMBANK proof**: The sysmoSIMBANK-96 houses 12 sysmoOCTSIM boards connected through 3 USB hubs (4 boards each) to a single EHCI (USB 2.0) host controller. This is a proven configuration running 96 SIMs on one USB bus.
- **USB device limit**: Linux xhci_hcd supports up to 256 devices per bus (USB 3.0) or 128 per bus (EHCI). 13 boards + hubs are well within limits.
- **Recommended**: Use 2-3 USB hubs, each connecting 4-5 boards to a single USB 2.0/3.0 host controller. No need for separate USB controllers for 13 boards.

### 1.5 Daisy-Chaining

- sysmoOCTSIM does NOT daisy-chain. Each board connects to a USB hub or host.
- The sysmoSIMBANK uses a 3-tier USB hub topology: Host → Hub → Hub → 4× sysmoOCTSIM
- For 13 boards, use a similar topology: Host → Powered USB Hub (7-port) → 4-Port Hub → boards

### 1.6 Power Requirements

| Configuration | Power Needed |
|---|---|
| Board only (no SIMs) | ~80-120 mA @ 5V |
| Board + 8 typical SIMs | ~400-500 mA @ 5V |
| Board + 8 worst-case Class-A SIMs | ~670 mA @ 5V (EXCEEDS USB spec) |
| 13 boards + 100 SIMs (estimated) | ~8.7A @ 5V total |

**⚠️ CRITICAL**: You CANNOT power sysmoOCTSIM from USB bus power alone. The barrel jack 5V power supply is **mandatory**. Each board needs its own 5V/1A+ supply, or a centralized 5V/10A+ supply for 13 boards.

The sysmoSIMBANK uses custom USB hubs with **per-port power switching**, allowing each set of 8 slots to be power-cycled independently.

### 1.7 SIM Form Factors

- **Native**: 2FF (Mini-SIM, 25×15mm) only
- **EVK includes**: 2FF-to-3FF/4FF adapters (8×) + ejector pins
- **For 3FF/4FF SIMs**: You need adapter trays or adapters. The Molex 91236-0001 card holder accepts 2FF cards.
- **Recommendation**: For 100-SIM farm, source 2FF SIMs directly, or use adapter trays for 3FF/4FF cards.

### 1.8 Heat Dissipation

- The board uses industrial temp range components (-40°C to 85°C)
- Manual warns: "Care must be taken to ensure sufficient heat dissipation"
- Board self-power is low (~0.6W), but 8 SIM front-end ICs + SIMs add heat
- For 13 boards stacked in enclosure: **active ventilation recommended** (40mm fans)
- The sysmoSIMBANK-96 uses a 2U rack enclosure with ventilation for 12 boards

### 1.9 Reliability

- No known systematic hardware failures reported
- SIM card fault detection is built into the front-end ICs
- Temperature monitoring is integrated into the MCU
- Per-port power switching (in sysmoSIMBANK) allows recovery from hung SIMs
- The FOSS firmware is actively maintained and field-upgradeable via USB DFU
- **Caveat**: Console port is shared with SIM7 — cannot use both simultaneously

---

## 2. Software Compatibility

### 2.1 PCSC-lite / libccid Support

**Status**: ✅ Fully supported, with caveats

- sysmoOCTSIM uses standard USB-CCID protocol → works with pcsc-lite + libccid
- **USB VID/PID**: 0x1D50:0x6141 — must be added to `/etc/libccid_Info.plist` if not already present in your distro's libccid version
- sysmocom provides a `check_libccid_config.py` script in osmo-ccid-firmware repo
- **Reader name in pcsc_scan**: `sysmocom sysmoOCTSIM [CCID] (serial_number) XX YY`

### 2.2 ⚠️ CRITICAL: Simultaneous Multi-Slot Access Bug

**The libccid driver does NOT support simultaneous access to multiple slots of the same CCID device by default.**

This was documented by Ludovic Rousseau (pcsc-lite/libccid maintainer) in October 2020:

> "My CCID driver does support multi-slots readers since version 0.9.2 released in 2004. But the driver is limited because it does not support using the slots at the same time, even if the reader declares it supports it. pcsc-lite has support for simultaneous multi-slot. But the driver tells pcsc-lite that simultaneous multi-slot is not supported."

> "Of course I tried to modify the code of the CCID driver to tell pcsc-lite that simultaneous multi-slot can be used. But then the driver is confused by mixed USB frames. I then remembered why this support was disabled."

**Impact**: When accessing 8 slots on one board, pcsc-lite serializes the APDU transactions. Only one slot is active at a time per board. This adds latency but does NOT prevent functionality.

**Workaround options**:
1. **sim-rest-server (pySim)**: Each slot gets its own REST endpoint — requests are queued per slot but the REST server handles them sequentially per board. For EAP-AKA at typical rates (1 auth every few seconds per SIM), this is likely fine.
2. **Patch libccid**: Contact Ludovic Rousseau to collaborate on enabling simultaneous multi-slot. He explicitly invites this: "If you want or plan to use such a reader with pcsc-lite on GNU/Linux or another Unix system then contact me so we can discuss what you can do."
3. **Use osmo-remsim**: The osmo-remsim bankd has its own CCID driver implementation that supports concurrent slot access.
4. **Serial access is probably fine for RCS**: EAP-AKA authentication is not continuous — each SIM does a challenge-response every few minutes during IMS re-registration. Sequential slot access per board (8 slots × ~10ms APDU = ~80ms per round) is unlikely to be a bottleneck.

### 2.3 sim-rest-server (pySim) Compatibility

**Status**: ✅ Explicitly designed for sysmoOCTSIM

- Part of the pySim project (Osmocom)
- `sim-rest-server.py` speaks to a local USIM via PC/SC API
- Provides REST API: `POST /sim-auth-api/v1/slot/SLOT_NR`
- **SLOT_NR** corresponds to the PC/SC reader number (0-7 for a single board)
- Returns RES, CK, IK (for successful 3G AKA) or AUTS (for sync failure)
- **This is the recommended approach for RCS IMS authentication**
- Example:
  ```
  POST /sim-auth-api/v1/slot/0
  {"rand": "bb685a4b2fc4d697b9d6a129dd09a091", "autn": "eea7906f8210000004faf4a7df279b56"}
  ```
  Response:
  ```json
  {"successful_3g_authentication": {"res": "b15379540ec93985", "ck": "713fde72c28cbd282a4cd4565f3d6381", "ik": "2e641727c95781f1020d319a0594f31a", "kc": "771a2c995172ac42"}}
  ```

**For 100 SIMs with 13 boards**: You'd run one sim-rest-server instance, and address slots by their global PC/SC reader index (0-103). The server handles the PC/SC API internally.

### 2.4 strongSwan EAP-AKA Compatibility

**Status**: ⚠️ eap-sim-pcsc does NOT support EAP-AKA

- **eap-sim-pcsc plugin**: Only implements `get_triplet()` for EAP-SIM. Does NOT implement `get_quintuplet()` which is required for EAP-AKA.
- This was confirmed by strongSwan developer Tobias Brunner (Issue #2316):
  > "The eap-sim-pcsc plugin currently does not implement get_quintuplet of simaka_card_t, which is required for EAP-AKA (it only implements get_triplet for EAP-SIM)."

**Alternative approaches for EAP-AKA with sysmoOCTSIM**:
1. **sim-rest-server + custom EAP-AKA handler**: Use pySim's sim-rest-server as the SIM authentication backend, then feed the AKA results into your IMS client stack. This is the most practical approach.
2. **eap-aka-3gpp plugin**: Uses software MILENAGE (Ki + OP/OPc stored in config files). Does NOT use a PCSC reader at all — the SIM crypto is done in software. If you have the Ki/OPc keys, this eliminates the need for physical SIMs entirely.
3. **eap-simaka-sql plugin**: Reads triplets/quintuplets from a SQL database. You could pre-populate the database using sysmoOCTSIM + sim-rest-server, then disconnect the readers.
4. **Extend eap-sim-pcsc**: Implement `get_quintuplet()` in the eap-sim-pcsc plugin. This would require C development in strongSwan's plugin framework.

**For RCS farm recommendation**: Use sim-rest-server as the primary auth backend. It's purpose-built for this use case by the same team (sysmocom/Osmocom).

### 2.5 pySim Compatibility

**Status**: ✅ Full support

- pySim (the Osmocom SIM programming tool) uses PC/SC API and works with any CCID reader
- Can access specific slots by reader name/number
- pySim-shell allows interactive access to individual SIMs
- sim-rest-server is part of the pySim ecosystem
- **Note**: pySim operates one SIM at a time — for bulk operations, you'd script it

### 2.6 osmo-remsim Compatibility

**Status**: ✅ Explicitly supported — sysmoOCTSIM is a primary target

- osmo-remsim is sysmocom's open-source remote SIM software
- **Components**:
  - `osmo-remsim-bankd`: Manages SIM bank (physical SIM slots), communicates with SIM cards via CCID
  - `osmo-remsim-server`: REST API for mapping SIM slots to client/modem connections
  - `osmo-remsim-client`: Runs on the modem side, presents remote SIM as virtual smart card
  - `ifd_handler`: Enables PC/SC access to remote card slots
- **sysmoOCTSIM is listed as a supported bank device** in osmo-remsim documentation
- The bankd has its own CCID driver implementation (not using libccid), which may support concurrent slot access
- Provides a full remote-SIM architecture where SIMs can be anywhere on the network

**For RCS farm**: osmo-remsim adds unnecessary complexity if SIM readers and IMS clients are on the same server. Use sim-rest-server instead. osmo-remsim is valuable if SIMs need to be geographically separated from modems/clients.

### 2.7 Linux Driver / Udev Issues

- **libccid_Info.plist**: Must add VID/PID 0x1D50:0x6141 if not present
- **udev rules**: pcscd uses udev for hotplug detection. No special udev rules needed beyond standard CCID handling
- **pcscd auto-start**: Ensure pcscd service is running (`systemctl enable pcscd`)
- **Permissions**: Users need to be in the appropriate group or use sudo for initial setup

---

## 3. Scaling to 100 SIMs (13 Boards)

### 3.1 USB Topology

For 13 boards, based on the proven sysmoSIMBANK-96 design:

```
Server USB 3.0 Controller (xHCI)
  └── Powered USB 3.0 Hub (7-port)
        ├── USB 2.0 Hub #1 (4-port)
        │     ├── Board 0 (slots 0-7)
        │     ├── Board 1 (slots 8-15)
        │     ├── Board 2 (slots 16-23)
        │     └── Board 3 (slots 24-31)
        ├── USB 2.0 Hub #2 (4-port)
        │     ├── Board 4 (slots 32-39)
        │     ├── Board 5 (slots 40-47)
        │     ├── Board 6 (slots 48-55)
        │     └── Board 7 (slots 56-63)
        ├── USB 2.0 Hub #3 (4-port)
        │     ├── Board 8 (slots 64-71)
        │     ├── Board 9 (slots 72-79)
        │     ├── Board 10 (slots 80-87)
        │     └── Board 11 (slots 88-95)
        └── Board 12 (slots 96-103) [direct connection]
```

**USB controllers needed**: 1 (one xHCI controller can handle this easily)

### 3.2 USB Bandwidth

- Each sysmoOCTSIM uses Full-Speed USB (12 Mbps)
- A single EAP-AKA APDU exchange is ~200-500 bytes
- At 13 boards doing simultaneous auth, worst case: ~6.5KB per round
- USB 2.0 (480 Mbps Hi-Speed) has orders of magnitude more bandwidth than needed
- **USB 2.0 is MORE than sufficient** for 13 boards doing EAP-AKA

### 3.3 Server Hardware Recommendations

| Component | Recommendation |
|---|---|
| **CPU** | 4+ cores (e.g., Intel Xeon E-series or AMD EPYC) — minimal CPU needed |
| **RAM** | 8-16 GB (pcscd + sim-rest-server are lightweight) |
| **USB** | 1× PCIe USB 3.0 card (4+ ports) OR motherboard USB 3.0 |
| **Storage** | 256GB SSD (OS + logs) |
| **Network** | 1 Gbps (for IMS/SIP traffic to RCS clients) |
| **Power** | 5V / 10A+ supply for 13 boards (see §1.6) |
| **Cooling** | Active ventilation if boards are in enclosed space |
| **Form Factor** | 2U-4U rack mount server or tower |

**PCIe USB Cards**: Any xHCI-compliant PCIe USB 3.0 card works. Recommended:
- Startech PEXUSB3S44V (4 external ports, Renesas controller)
- ORICO PU3-4P (4-port USB 3.0 PCIe)

### 3.4 pcscd Configuration for 100+ Readers

**⚠️ MUST recompile pcsc-lite and libccid**:

Default `PCSCLITE_MAX_READERS_CONTEXTS = 16` limits you to 16 reader contexts (slots). For 104 slots (13 boards × 8), you need:

1. **Recompile pcsc-lite**:
   ```c
   // In src/PCSC/pcsclite.h.in
   #define PCSCLITE_MAX_READERS_CONTEXTS 128  // was 16
   ```

2. **Recompile libccid**:
   ```c
   // In src/ccid_ifdhandler.h
   #define CCID_DRIVER_MAX_READERS 128  // was 16
   ```

3. **Build and install**:
   ```bash
   # pcsc-lite
   git clone https://github.com/LudovicRousseau/PCSC.git
   cd PCSC/pcsc-lite
   # Edit pcsclite.h.in
   ./configure && make && sudo make install
   
   # libccid
   git clone https://salsa.debian.org/rousseau/CCID.git
   cd CCID
   # Edit ccid_ifdhandler.h
   ./configure && make && sudo make install
   ```

4. **Restart pcscd**: `sudo systemctl restart pcscd`

**Alternative**: Some users report using 36+ readers by simply recompiling. The sysmoSIMBANK-96 with its 96 slots proves this works at scale.

### 3.5 Programmatically Addressing Specific SIM Slots

Each slot gets a unique global reader index in pcscd. The naming convention is:

```
"sysmocom sysmoOCTSIM [CCID] (SERIAL) DD SS"
```

Where:
- `SERIAL` = board serial number (unique per board)
- `DD` = device index (hex, increments per board: 00, 01, 02, ...)
- `SS` = slot index (hex, 00-07 per board)

**In sim-rest-server**: `POST /sim-auth-api/v1/slot/N` where N is the global reader index (0-103).

**In Python (pyscard)**:
```python
from smartcard.System import readers
readers_list = readers()
# readers_list[0] = first slot of first board
# readers_list[7] = last slot of first board
# readers_list[8] = first slot of second board
# etc.
```

**In C (PC/SC API)**:
```c
LONG rv;
SCARDCONTEXT hContext;
SCARD_READERSTATE rgReaderStates[104];
// Set rgReaderStates[i].szReader = reader name
rv = SCardEstablishContext(SCARD_SCOPE_SYSTEM, NULL, NULL, &hContext);
rv = SCardConnect(hContext, readerName, SCARD_SHARE_SHARED, SCARD_PROTOCOL_T0, &hCard, &dwActiveProtocol);
```

---

## 4. Operational Concerns

### 4.1 Hot-Swapping

**Status**: ✅ Supported

From the product page: "All cards can be individually accessed and replaced without taking other cards offline."

The drawer-style SIM slots (Molex 91228-3001) allow insertion/removal while the board is powered. pcscd will detect the card removal/insertion event and update the reader state.

**⚠️ Important note from manual**: "Don't insert empty SIM card drawers — either always supply a SIM card with them or leave any empty drawer removed." Empty drawers cause the firmware to probe and time out, adding delays.

### 4.2 SIM Detection Time

- pcscd uses udev hotplug mechanism
- Card insertion/removal triggers a reader state change event
- Typical detection time: **1-3 seconds** after physical insertion
- Cold-start detection of 96 cards in sysmoSIMBANK: a few seconds for all

### 4.3 Concurrent AKA on All 8 Slots

- **Hardware**: Supports it — `bMaxCCIDBusySlots = 8`
- **Software (libccid)**: ⚠️ NOT supported — slots are serialized per board
- **Software (osmo-remsim bankd)**: Likely supports concurrent access (uses own CCID driver)
- **Practical impact for RCS**: Minimal. EAP-AKA is not a continuous high-frequency operation. Each IMS re-registration happens every ~30-60 minutes. Even serialized, 8 slots × 10ms = 80ms per board per auth round is negligible.

### 4.4 SIM Failure Handling

- SIM card fault detection is built into each front-end IC
- If a SIM goes bad, pcscd reports the slot as "Card removed" or returns error on APDU
- The other 7 slots on the same board are unaffected (fully independent UARTs)
- sysmoSIMBANK's per-port power switching can power-cycle individual sets of 8 slots
- For bare boards: power-cycle the board, or replace the bad SIM
- **sim-rest-server returns HTTP 410 (Gone)** if no SIM is in the slot

### 4.5 LED Indicators

| LED | Color | Default Function |
|---|---|---|
| LED101-LED402 (8 total) | Yellow | Per-slot SIM activity (blink on APDU) |
| LED501 | Green | Unit powered on / bootloader mode |
| LED701 | Green | 3.3V DC voltage present (diagnostic) |

- All LEDs are MCU-controlled and can be programmed with custom blink patterns
- Light guide mounts are available for front-panel integration (e.g., Mentor brand)
- LED colors can be customized per production batch (MOQ applies)

### 4.6 Monitoring

- **pcsc_scan**: Lists all readers and their state (card inserted/removed)
- **sim-rest-server health**: HTTP status codes (200 OK, 404 slot not found, 410 no SIM)
- **pcscd monitoring**: `systemctl status pcscd`, `journalctl -u pcscd`
- **Custom monitoring**: Write a script that periodically queries each slot via sim-rest-server and alerts on failures
- **LED monitoring**: Per-slot activity LEDs give visual indication

---

## 5. Pricing & Availability

### 5.1 Current Pricing

| Product | Price (incl. VAT) | Notes |
|---|---|---|
| **sysmoOCTSIM Evaluation Kit** (sysmoOCTSIM-EVK) | **€595.00** | Board + enclosure + power supply + USB cable + 8× SIM adapters + 10× sysmoISIM-SJA5 cards (no ADM keys) |
| **sysmoOCTSIM Board Only** | **Not listed in webshop** | Contact sysmocom for quantity pricing. The EVK is for evaluation; volume orders are priced separately. |

**Estimated board-only pricing**: Based on the EVK including enclosure, power supply, SIM cards, etc., the bare board is likely €300-400. For 13+ boards, expect significant volume discount. **Must contact sysmocom directly for quote.**

### 5.2 Shipping to India

- **Shipping method**: UPS only (as of July 2022, Deutsche Post/DHL no longer viable)
- **Shipping frequency**: Once per week, typically Tuesdays
- **UPS services**: UPS Standard, UPS Expedited, UPS Express Saver (availability depends on destination)
- **Shipping cost**: Real-time calculation via UPS API based on weight and destination — shown at checkout
- **Estimated shipping cost to India**: For 13+ boards (~5-6 kg), expect €150-300 via UPS Express (rough estimate)
- **Customs**: India imposes import duty on electronics (typically 18-28% depending on classification). GST (18%) applies. Shipments may attract customs scrutiny.
- **Transit time**: UPS Express to India: 3-5 business days. UPS Expedited: 5-7 business days.
- **Payment**: PayPal or Stripe (credit card) accepted

### 5.3 Bulk Discount

- sysmocom explicitly states: "The Evaluation Kit is intended for you to evaluate the product for your project, before placing any quantity orders at related project quantity pricing at sysmocom."
- **Volume pricing is available** — must contact sales@sysmocom.de
- For 13 boards, expect a meaningful discount from the per-unit EVK price
- sysmocom also sells the sysmoSIMBANK-96 (pre-built 96-slot solution) which may be more cost-effective than 13 individual boards

### 5.4 Alternative: sysmoSIMBANK-96

If you need 96-100 SIMs, consider the sysmoSIMBANK-96:
- 96 slots in 2U rack mount = 12 × sysmoOCTSIM boards + embedded x86_64 Linux system
- Custom USB hubs with per-port power switching
- Built-in AMD GX-412TC processor, 4GB RAM, 16GB mSATA SSD
- 3× Gigabit Ethernet
- Runs osmo-remsim + pcsc-lite natively
- **Pricing**: Not listed in webshop — contact sysmocom for quote
- **Advantage**: Turnkey solution, no need to build your own USB topology, power distribution, or enclosure

### 5.5 Lead Time

- EVK: "Available, lead time 1-2 weeks" (as of May 2026)
- Volume orders: Likely 4-8 weeks depending on quantity and component availability
- Contact: info@sysmocom.de or sales@sysmocom.de

### 5.6 Warranty

- sysmocom is a German company subject to EU consumer/commercial warranty law
- Products come with a Declaration of Conformity (CE marked)
- Specific warranty terms for volume/custom orders are negotiated

### 5.7 Alternative Sources/Resellers

- **sysmocom is the sole manufacturer** — no known resellers
- The sysmoOCTSIM is a niche product with no direct competitors in the 8-slot CCID reader space
- Alternative single-slot readers (Gemalto, SCM, OmniKey) exist but don't scale to 100 SIMs efficiently

---

## 6. What We CANNOT Do with sysmoOCTSIM

### 6.1 No Radio / No GSM Network Access

- sysmoOCTSIM is a **smart card reader only** — it has no radio, no baseband, no antenna
- It cannot register on a GSM/UMTS/LTE/5G network by itself
- It can only perform the **SIM card side** of authentication (compute SRES/RES, CK, IK from RAND/AUTN)
- To actually use a SIM on a network, you need a modem (e.g., sysmoQMOD, or USB modem)

### 6.2 No Direct SMS/Voice Without ePDG+SIP

- SIM cards in sysmoOCTSIM cannot send/receive SMS or make calls on their own
- For RCS messaging, you need:
  1. **IMS core** (e.g., Kamailio + RTPEngine, or Open IMS Core)
  2. **ePDG** (e.g., strongSwan with EAP-AKA) for IPSec tunnel to IMS
  3. **SIP/RCS client stack** that authenticates via EAP-AKA using the SIM
  4. sysmoOCTSIM provides the AKA crypto (via sim-rest-server) but not the network transport

### 6.3 Cannot Share One SIM Across Multiple IMS Registrations

- A SIM card can only be in one "active" session at a time
- You cannot use one SIM for two simultaneous IMS registrations
- You need **one SIM per concurrent IMS session** (hence 100 SIMs for the farm)

### 6.4 Other Limitations

- **2FF only**: No native 3FF/4FF support (needs adapters)
- **Console port shares SIM7**: Cannot use debug UART and SIM7 simultaneously
- **CAN/Ethernet ports**: Reserved for future use, currently non-functional
- **T=1 protocol**: Not supported by default (T=0 only), but can be added on request
- **USB bus power insufficient**: Must use external power supply
- **libccid serialization**: Slots accessed sequentially per board (not truly concurrent)
- **Firmware probing on empty drawers**: Causes timeouts — always keep SIMs inserted or remove drawers
- **No SIM multiplexing**: Each SIM is a physical card — cannot virtually slice a SIM

---

## 7. Architecture Recommendation for 100-SIM RCS Farm

### Recommended Stack

```
┌─────────────────────────────────────────────────┐
│              IMS / RCS Application              │
│         (Kamailio + SIP/RCS clients)            │
├─────────────────────────────────────────────────┤
│            EAP-AKA Authentication               │
│     (Custom handler calling sim-rest-server)    │
├─────────────────────────────────────────────────┤
│            sim-rest-server (pySim)              │
│    POST /sim-auth-api/v1/slot/{0..103}         │
├─────────────────────────────────────────────────┤
│              PC/SC (pcsc-lite + libccid)         │
│     (recompiled: MAX_READERS_CONTEXTS=128)     │
├─────────────────────────────────────────────────┤
│     13× sysmoOCTSIM (USB 2.0 CCID)             │
│     Board 0: slots 0-7   Board 7: slots 56-63  │
│     Board 1: slots 8-15  ...                    │
│     Board 6: slots 48-55 Board 12: slots 96-103│
└─────────────────────────────────────────────────┘
```

### Key Implementation Steps

1. **Order 13× sysmoOCTSIM boards** (contact sysmocom for volume pricing)
2. **Build server**: x86_64 Linux (Debian recommended), 8GB+ RAM, USB 3.0 PCIe card
3. **Recompile pcsc-lite** with `PCSCLITE_MAX_READERS_CONTEXTS=128`
4. **Recompile libccid** with `CCID_DRIVER_MAX_READERS=128`
5. **Add VID/PID** 0x1D50:0x6141 to `/etc/libccid_Info.plist`
6. **Connect boards**: Use powered USB hubs (see §3.1 topology)
7. **Power each board**: 5V/1A+ per board via barrel jack
8. **Install sim-rest-server** from pySim: `pip install pysim`
9. **Run sim-rest-server**: One instance handles all 104 slots
10. **Configure IMS stack**: Point EAP-AKA handler at sim-rest-server REST API
11. **Monitor**: Script that polls each slot via REST API and alerts on failures

### Estimated Budget

| Item | Qty | Unit Price | Total |
|---|---|---|---|
| sysmoOCTSIM boards | 13 | ~€350-400 (est. volume) | ~€4,550-5,200 |
| 5V power supplies | 13 | ~€10 | ~€130 |
| Powered USB hubs | 3 | ~€50 | ~€150 |
| USB cables | 13 | ~€5 | ~€65 |
| Server hardware | 1 | ~€1,500 | ~€1,500 |
| Shipping (UPS to India) | 1 | ~€200 | ~€200 |
| **Subtotal (hardware)** | | | **~€6,595-7,245** |
| India import duty (est. 20%) | | | ~€1,319-1,449 |
| India GST (18%) | | | ~€1,427-1,565 |
| **Grand Total (estimated)** | | | **~€9,341-10,259** |

*Note: Prices are estimates. Contact sysmocom for actual quotes.*

---

## 8. References

- [sysmoOCTSIM Product Page](https://sysmocom.de/products/sim/sysmooctsim/index.html)
- [sysmoOCTSIM Data Sheet (PDF)](https://sysmocom.de/downloads/sysmoOCTSIM_data_sheet.pdf)
- [sysmoOCTSIM User Manual (PDF)](https://sysmocom.de/manuals/sysmoOCTSIM-manual.pdf)
- [sysmocom Webshop - EVK](https://shop.sysmocom.de/sysmoOCTSIM-evaluation-kit/sysmoOCTSIM-EVK)
- [osmo-ccid-firmware (FOSS)](https://gitea.osmocom.org/sim-card/osmo-ccid-firmware)
- [osmo-asf4-dfu bootloader (FOSS)](https://gitea.osmocom.org/electronics/osmo-asf4-dfu)
- [Ludovic Rousseau: sysmoOCTSIM 8-slots reader](https://blog.apdu.fr/posts/2020/10/sysmooctsim-8-slots-reader/)
- [Ludovic Rousseau: A reader for 96 smart cards](https://blog.apdu.fr/posts/2021/06/a-reader-for-96-smart-cards-sysmosimbank/)
- [PCSC GitHub - Max readers limit Issue #8](https://github.com/LudovicRousseau/PCSC/issues/8)
- [sim-rest-server documentation (pySim)](https://downloads.osmocom.org/docs/pysim/master/html/sim-rest.html)
- [osmo-remsim Wiki](https://osmocom.org/projects/osmo-remsim/wiki)
- [osmo-remsim User Manual (PDF)](https://ftp.osmocom.org/docs/osmo-remsim/0.2.2/osmo-remsim-usermanual.pdf)
- [sysmoSIMBANK Product Page](https://sysmocom.de/products/sim/sysmosimbank/index.html)
- [strongSwan Issue #2316: EAP-AKA with PCSC](https://wiki.strongswan.org/issues/2316)
- [strongSwan Issue #2326: eap-aka-3gpp plugin](https://wiki.strongswan.org/issues/2326)
- [StackOverflow: Limit of 16 cardreaders in PCSC](https://stackoverflow.com/questions/73224320/limit-of-16-cardreaders-in-pcsc-on-ubuntu-server)
- [sysmocom Payment/Shipping Info](https://shop.sysmocom.de/Information/Payment-Shipping/)
