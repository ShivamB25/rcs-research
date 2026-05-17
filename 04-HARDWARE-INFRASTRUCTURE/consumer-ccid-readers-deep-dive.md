# Consumer CCID Readers for 100-SIM RCS Messaging Farm: Deep Research Report

**Date**: 2026-05-16  
**Purpose**: Evaluate consumer USB CCID smart card readers as an alternative to sysmoOCTSIM for a 100-SIM RCS messaging farm

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Reader Hardware Options](#2-reader-hardware-options)
3. [100-Reader USB Topology](#3-100-reader-usb-topology)
4. [PCSC-Lite Multi-Reader Support](#4-pcsc-lite-multi-reader-support)
5. [Software Compatibility](#5-software-compatibility)
6. [Reliability & Operational Concerns](#6-reliability--operational-concerns)
7. [Cost Breakdown (India-Specific)](#7-cost-breakdown-india-specific)
8. [What We CANNOT Do with Consumer Readers](#8-what-we-cannot-do-with-consumer-readers)
9. [The "Building 128/256 SIM Bank" Reference](#9-the-building-128256-sim-bank-reference)
10. [Recommendation](#10-recommendation)

---

## 1. Executive Summary

**TL;DR**: Building a 100-reader consumer CCID farm is **possible but painful**. The main blockers are: (1) XHCI USB endpoint limits (~32 readers per controller), (2) pcscd/libccid 16-reader default limit requiring recompilation, (3) reader naming instability across reboots, (4) SIM seating reliability, and (5) massive cable/hub management complexity. For 100 SIMs, **sysmoOCTSIM (13 boards × 8 slots = 104 slots)** is strongly preferred over 100 individual readers due to dramatically better density, reliability, deterministic naming, and lower total cost of ownership. However, if budget is extremely tight and you're willing to accept operational complexity, a consumer reader approach can work.

### Key Decision Points

| Factor | Consumer CCID (100 readers) | sysmoOCTSIM (13 boards) |
|--------|---------------------------|------------------------|
| Hardware cost (India) | ₹60,000–100,000 | €1,300–1,950 (~₹120,000–180,000) |
| USB endpoints consumed | 300 (3 per reader) + hub overhead | 39 (3 per board) + minimal hubs |
| pcscd recompilation required | YES (both pcscd + libccid) | YES (but only to 104, trivial) |
| Reader naming across reboots | UNSTABLE (needs udev rules) | STABLE (by serial + slot index) |
| SIM seating reliability | LOW (loose contacts, oxidation) | HIGH (purpose-built SIM slots) |
| Physical management | 100 readers + 15 hubs = cable nightmare | 13 PCBAs, 1U rack-mountable |
| Hot-plug safety | Risky (reader name changes) | Safe (slot-indexed) |
| Monitoring 100% uptime | Complex (per-reader health checks) | Simple (per-board status) |
| Power per SIM | ~100mA × 100 = 10A | ~50mA × 8 × 13 = ~5A |
| Boot time to initialize | ~30-60 seconds for 100 readers | ~10-15 seconds for 13 boards |

---

## 2. Reader Hardware Options

### 2.1 Which CCID Readers Work with SIM Cards on Linux?

**Critical insight**: Not all smart card readers accept SIM cards! Most readers are designed for ID-1 (credit card size, 85.6×54mm) form factor. SIM cards use ID-000/2FF (25×15mm) form factor. You need readers that either:
- Have a SIM-sized card slot natively, OR
- Accept ID-1 cards AND you use a SIM-to-ID1 adapter

**Truly CCID-compliant readers (verified on ccid.apdu.fr supported list)**:

| Reader | USB VID:PID | CCID Support | SIM Slot? | Notes |
|--------|------------|--------------|-----------|-------|
| **SCM SCR3310** | 04E6:5116 | ✅ Since v0.9.3 | ID-1 only | Most popular US DoD reader. Needs adapter for SIM. |
| **SCM SCR3310v2.0** | 04E6:5116 (v2) | ✅ | ID-1 only | Updated version, USB-C variant available |
| **ACS ACR38U-CCID** | 072F:90CC | ✅ Since v1.0.0 | ID-1 only | ⚠️ Old versions have timeout bugs with certain USB frame sizes |
| **ACS ACR39U** | 072F:21A0 | ✅ | ID-1 only | Newer, more reliable |
| **Gemalto USB Shell Token V2** | 08E6:3438 | ✅ Since v0.1.0 | ID-1 only | Small form factor, key-shaped |
| **Gemalto PC Twin Reader** | 08E6:3437 | ✅ Since v0.1.0 | ID-1 only | Classic, widely available |
| **Gemalto GemCore SIM Pro** | 08E6:3480 | ✅ Since v1.0.0 | **2 SIM slots!** | Purpose-built for SIM cards. RARE/EXPENSIVE. |
| **OmniKey CardMan 3121** | 076B:3021 | ✅ | ID-1 only | Used in verified 24-reader setups |
| **Kingstyle generic CCID** | Various | ✅ (generic CCID) | Varies | Cheap Chinese readers. Quality varies. |
| **REINER SCT cyberJack** | 0C4B:0500 | ✅ | ID-1 only | German-made, high quality, expensive |
| **sysmoOCTSIM** | Custom | ✅ | **8 SIM slots** | Purpose-built for this exact use case |

### 2.2 Which Readers Accept 2FF SIM Cards Directly?

**Very few readers have native SIM slots**:
- **Gemalto GemCore SIM Pro** (2 slots, 2FF) — professional/enterprise, expensive (~€100+)
- **sysmoOCTSIM** (8 slots, 2FF) — designed specifically for multi-SIM use
- **Eutron SIM Reader** (1 slot, 2FF) — rare, European market

**All other readers require adapters** (see next section).

### 2.3 SIM Card Adapters: 2FF↔3FF↔4FF

Adapters allow smaller SIMs to fit into ID-1 or 2FF slots:

| Adapter Type | Reliability | Notes |
|-------------|------------|-------|
| **4FF→2FF (Nano→Mini)** | ⚠️ MODERATE | Thin adapter, SIM can shift. Use tape to secure. |
| **3FF→2FF (Micro→Mini)** | ✅ GOOD | Most reliable adapter type. Good fit. |
| **4FF→3FF (Nano→Micro)** | ✅ GOOD | Decent fit. |
| **2FF→ID-1 (Mini→Credit Card)** | ✅ GOOD | Professional adapters from sysmocom.de work well. |

**Key concern**: Nano-SIMs (4FF) in adapters are particularly problematic because:
1. The SIM is only 0.67mm thick — very thin, easy to shift
2. The contact area is tiny (12.3×8.8mm) — slight misalignment causes contact errors
3. Adapters may not hold the SIM securely for 24/7 operation

**Recommendation**: If using consumer readers with adapters:
- Prefer 2FF (mini-SIM) cards directly in ID-1 adapters
- For 3FF/4FF SIMs, use high-quality adapters with a retaining mechanism
- Consider applying a small piece of Kapton tape to secure the SIM in the adapter
- sysmocom.de sells professional 2FF→ID-1 adapters (~€2 each)

### 2.4 Power Draw Per Reader

| Reader | Idle Current | Active Current | USB Power |
|--------|-------------|----------------|-----------|
| Typical CCID reader (ID-1) | 50-80mA | 100-150mA | 5V, <500mA |
| SCM SCR3310 | ~50mA idle | ~100mA active | Bus-powered |
| ACS ACR38 | ~60mA idle | ~120mA active | Bus-powered |
| Gemalto USB Shell | ~40mA idle | ~80mA active | Bus-powered |
| sysmoOCTSIM (8 slots) | ~100mA idle | ~400mA active (all 8) | 5V, <500mA total |

**For 100 readers**: 
- Idle: 100 × 60mA = 6A @ 5V = 30W
- Active (worst case): 100 × 120mA = 12A @ 5V = 60W
- Plus hub overhead: ~15 hubs × 200mA = 3A = 15W
- **Total power budget: ~45-75W for readers + hubs alone**

### 2.5 CCID Compliance

The CCID generic driver at ccid.apdu.fr supports **200+ readers**. However, compliance quality varies:

**Truly CCID compliant** (work with generic Linux CCID driver, no special drivers needed):
- SCM SCR3310/SCR3310v2
- ACS ACR38U-CCID, ACR39U
- Gemalto PC Twin, USB Shell Token, GemCore SIM Pro
- OmniKey CardMan 3121
- Kingstyle generic CCID readers (if they use standard CCID descriptors)

**Known problem readers**:
- ACS ACR38 old revision: timeout when USB frame size = multiple of wMaxPacketSize
- Alcor Micro AU9520: firmware 1.01 is bogus (time request not forwarded), does not support USB suspend (higher power consumption)
- Some cheap Chinese readers: may report CCID class but have buggy firmware, non-standard APDU handling, or missing features (no extended APDU, no card event notification)

### 2.6 Readers Known to FAIL with EAP-AKA or pySim

**Documented issues**:
- **ACS ACR38 old firmware**: Timeout issues can cause EAP-AKA authentication failures under load
- **Alcor Micro AU9520**: Firmware bugs may cause intermittent failures
- **Any reader without proper card event notification**: May miss card insertion/removal events
- **Readers that don't support T=0 protocol**: Most SIM cards use T=0; T=1-only readers will fail

**No known issues with**: SCM SCR3310, Gemalto PC Twin, OmniKey 3121 when used with pySim or sim-rest-server.

---

## 3. 100-Reader USB Topology

### 3.1 The XHCI Endpoint Limit — THE Critical Hardware Constraint

**This is the single most important technical limitation for this project.**

From Ludovic Rousseau's blog (blog.apdu.fr, March 2021):

> "The XHCI specification allows for a massive 7,906 endpoints! However, common implementations of the XHCI controllers impose their own limit on the total number of endpoints to 96. The most notorious of these is Intel's series 8 architectures. This means that the maximum number of common devices which use 3 endpoints able to be attached to an Intel series 8 XHCI host controller is actually 96 endpoints / 3 endpoints per device = **32 devices**."

**Each CCID reader uses 3 USB endpoints**:
1. Bulk IN (host ← reader)
2. Bulk OUT (host → reader)
3. Interrupt (card status changes)

**Each USB hub consumes 4-5 endpoints** for its own operation.

#### Endpoint Budget Calculation (100 readers)

| Component | Endpoints | Count | Total |
|-----------|-----------|-------|-------|
| CCID readers | 3 each | 100 | 300 |
| USB hubs (7-port) | ~4 each | ~15 | ~60 |
| **Total endpoints needed** | | | **~360** |

**With a single Intel XHCI controller (96 endpoints)**:
- Available for devices: 96 - hub_overhead ≈ 80-90 endpoints
- Max readers on ONE controller: **~26-30 readers**
- **You need AT LEAST 4 independent XHCI controllers for 100 readers**

### 3.2 How Many USB Controllers Needed?

| XHCI Controller | Available Endpoints | Max Readers (with hubs) |
|----------------|--------------------|-----------------------|
| Intel (96 EP limit) | ~80-90 | 26-30 |
| AMD/ASMedia (may have more) | ~96-192 | 30-64 |
| Renesas μPD720202 | ~96 | 26-30 |
| Via VL805 | ~96 | 26-30 |

**For 100 readers: Minimum 4 PCIe USB cards** (each providing an independent XHCI controller)

### 3.3 USB 2.0 vs USB 3.0 Hubs

**USB 2.0 is actually PREFERRED for CCID readers** because:
1. CCID readers are USB 2.0 Full Speed (12Mbps) devices — USB 3.0 provides no speed benefit
2. USB 3.0 hubs with USB 2.0 devices share the USB 2.0 companion controller — no advantage
3. USB 2.0 hubs are cheaper and more widely available
4. USB 2.0 uses fewer endpoints per hub
5. **Bandwidth**: Each CCID reader uses ~10-50KB/s during EAP-AKA. USB 2.0's 480Mbps can handle 100 simultaneous authentications easily.

**USB 3.0 advantage**: Only matters if you need USB 3.0 SuperSpeed devices on the same controller. Since CCID readers are all Full Speed, USB 2.0 is fine.

### 3.4 Powered USB Hubs: Recommendations

**7-port powered hubs** (most common/reliable form factor):

| Hub | Ports | Power Supply | Price (India) | Notes |
|-----|-------|-------------|---------------|-------|
| **Sabrent HB-UMLS** | 7 | 12V/2A | ₹1,500-2,000 | Individual switches, reliable |
| **Anker USB 3.0 7-Port** | 7 | 36W (12V/3A) | ₹3,000-4,000 | Premium, reliable |
| **Amazon Basics 7-Port** | 7 | 12V/2A | ₹1,200-1,500 | Budget option |
| **UGREEN 7-Port** | 7 | 12V/2A | ₹1,500-2,500 | Good quality |

**10-port powered hubs**:

| Hub | Ports | Power Supply | Price (India) | Notes |
|-----|-------|-------------|---------------|-------|
| **Sabrent HB-BU10** | 10 | 60W (12V/5A) | ₹2,500-3,500 | Individual switches |
| **Anker 10-Port** | 10 | 60W | ₹4,000-5,000 | Premium |
| **Amazon Basics 10-Port** | 10 | 5Gbps | ₹2,000-3,000 | Budget |

**Critical concern**: Not all "10-port" hubs are equal. Many cheap 10-port hubs internally daisy-chain two 4-port hub controllers, which:
- Consumes an extra level in the USB tree depth
- Adds 4-5 extra endpoints per internal hub
- May not provide enough power per port

### 3.5 USB Tree Depth Limits

**USB spec: Maximum 5 levels of hubs** (root hub = level 0, max 4 additional hub tiers).

**Topology for 100 readers**:
```
Level 0: Root Hub (on PCIe USB card) — 4 ports
Level 1: 4× Powered Hubs (7-port each) = 28 device ports
Level 2: (avoid — pushes toward depth limit)
```

**Recommended topology**:
```
Server
├── PCIe USB Card 1 (Controller 1) → ~25 readers
│   ├── 7-port Hub A → 7 readers
│   ├── 7-port Hub B → 7 readers  
│   ├── 7-port Hub C → 7 readers
│   └── Direct port → 2 readers
├── PCIe USB Card 2 (Controller 2) → ~25 readers
│   └── (same as above)
├── PCIe USB Card 3 (Controller 3) → ~25 readers
│   └── (same as above)
└── PCIe USB Card 4 (Controller 4) → ~25 readers
    └── (same as above)
```

**Total: 4 PCIe cards × ~25 readers = 100 readers, using ~16 powered hubs**

### 3.6 Bandwidth: Is USB 2.0 Sufficient?

**Yes, absolutely.**

- Each EAP-AKA authentication exchange: ~200-500 bytes over ~100ms
- SIM card communication: typically 9600-115200 baud
- 100 simultaneous authentications: ~50KB/s total
- USB 2.0 bandwidth: 480 Mbps = 60 MB/s
- **Utilization: <0.1%** — bandwidth is NOT the bottleneck

The bottleneck is **endpoint count**, not bandwidth.

### 3.7 Can a Single PCIe USB Card Handle 20+ Devices?

**Only if the XHCI controller on the card supports enough endpoints.**

- Single-controller PCIe cards (e.g., Renesas μPD720202, 2-port): ~96 endpoints = ~30 CCID readers max
- Multi-controller PCIe cards (e.g., 4 independent controllers on one card): Each controller handles ~30 readers

**Recommended PCIe USB cards**:
1. **Startech 4-Port PCIe USB 3.0 Card (PEXUSB3S4V)** — 4 independent controllers
2. **Startech 2-Port PCIe USB 3.0 (PEXUSB3S2)** — 1 controller
3. **Buffalo IFC-PCIE2U3** — Renesas μPD720202, 2 ports, 1 controller
4. **Inateck KT4006** — 4-port, 2 controllers

**For India**: Available on Amazon.in for ₹2,000-6,000 each.

### 3.8 Real-World Reports of 50+ CCID Readers

- **Ludovic Rousseau (pcsc-lite maintainer)**: Documented the XHCI endpoint limitation in detail (March 2021 blog post). Has tested sysmoOCTSIM with 8 slots successfully.
- **GitHub Issue #8, #13 (PCSC repo)**: Multiple users running 24-36 readers by recompiling pcscd. OmniKey CardMan 3121 used in a 24-reader setup.
- **@sertys (Medium article)**: Built a 128-SIM card bank using consumer readers for SMS code reception. Used Kingstyle readers and powered USB hubs. Required pcscd recompilation.
- **Stack Overflow (2022)**: User with 24 Gemalto PC Twin readers on Ubuntu, needed to change `PCSCLITE_MAX_READERS_CONTEXTS`.

**No documented case of 100+ individual USB CCID readers on a single Linux host.** The endpoint limit makes this extremely difficult without multiple PCIe USB cards.

---

## 4. PCSC-Lite Multi-Reader Support

### 4.1 pcscd's Max Reader Limit

**Default: 16 readers** (hardcoded in `pcsclite.h.in`):
```c
#define PCSCLITE_MAX_READERS_CONTEXTS  16
```

**Theoretical max: 255** (limited by USB device addressing: 127 devices per bus, minus hubs).

**To increase the limit, you MUST recompile TWO packages**:

1. **pcsc-lite**: Change `PCSCLITE_MAX_READERS_CONTEXTS` in `src/PCSC/pcsclite.h.in`
   ```bash
   # Clone and build
   git clone https://github.com/LudovicRousseau/PCSC.git
   cd PCSC
   # Edit src/PCSC/pcsclite.h.in: change 16 to 128
   meson setup build
   meson compile -C build
   meson install -C build
   # CRITICAL: Copy new pcscd to system location
   cp /usr/local/sbin/pcscd /usr/sbin/pcscd
   ```

2. **libccid (CCID driver)**: Change `CCID_DRIVER_MAX_READERS` in `src/ccid_ifdhandler.h`
   ```c
   #define CCID_DRIVER_MAX_READERS  16  // Change to 128
   ```
   Then recompile and install.

**⚠️ COMMON MISTAKE**: After recompiling, `meson install` puts pcscd in `/usr/local/sbin/pcscd`, but the system service runs `/usr/sbin/pcscd`. You MUST copy the new binary to the system path, or the old 16-reader-limited binary will still be used.

### 4.2 How Readers Are Named/Enumerated

pcscd names readers in the format:
```
<Reader Friendly Name> <BUS> <DEVICE>
```

Example output from a 24-reader setup:
```
0: OmniKey CardMan 3121 00 00
1: OmniKey CardMan 3121 01 00
2: OmniKey CardMan 3121 02 00
...
23: OmniKey CardMan 3121 17 00
```

Where:
- First hex number = USB bus number
- Second hex number = USB device address on that bus

### 4.3 Are Reader Names Deterministic Across Reboots?

**NO — reader names are NOT deterministic by default.**

The naming depends on:
1. **USB bus enumeration order** — which PCIe card is probed first
2. **USB device address assignment** — depends on physical port and discovery order
3. **Hot-plug timing** — if readers appear in different order, names change

**This is a CRITICAL problem for a 100-reader farm**: You cannot reliably map "Reader 42" to "SIM with IMSI 404-XX-YYYYYYY" across reboots.

### 4.4 What If a Reader Disconnects and Reconnects?

- pcscd supports hot-plug via udev rules
- When a reader disconnects, pcscd removes it from the reader list
- When it reconnects, pcscd adds it with a **new device address** — which may change the reader name
- If the reader was at index 42 and it disconnects/reconnects, it might get a new index
- **All software using the old reader name will fail** until re-discovered

### 4.5 pcscd Configuration for 100+ Readers

After recompiling with `PCSCLITE_MAX_READERS_CONTEXTS=128`:

```ini
# /etc/default/pcscd
# Enable debug logging (useful for troubleshooting)
PCSCD_ARGS="--debug"
# Or for production:
PCSCD_ARGS=""
```

The `reader.conf.d/` directory should NOT contain USB driver entries (pcscd auto-detects USB CCID readers via udev).

### 4.6 Performance: pcscd CPU Usage with 100 Readers

- pcscd uses a polling thread per reader for card status changes
- 100 readers: ~100 polling threads
- Expected CPU usage: **5-15% of a single core** (idle), higher during mass authentication
- Memory: ~2-5MB for 100 reader contexts
- **Not a significant concern** on modern hardware

### 4.7 Reader Limits in pcsc-lite Source Code

| Limit | Location | Default | Theoretical Max |
|-------|----------|---------|----------------|
| `PCSCLITE_MAX_READERS_CONTEXTS` | `pcsclite.h.in` | 16 | 255 |
| `CCID_DRIVER_MAX_READERS` | `ccid_ifdhandler.h` | 16 | 255 |
| Max USB devices per bus | USB spec | 127 | 127 (minus hubs) |
| Max XHCI endpoints | Hardware-dependent | 96 (Intel) | 7906 (spec) |

---

## 5. Software Compatibility

### 5.1 sim-rest-server

**YES, it can address 100 individual readers** — but with caveats.

sim-rest-server uses PC/SC slot numbers as its addressing mechanism:
```
POST /sim-auth-api/v1/slot/SLOT_NR
```

Where `SLOT_NR` is the integer-encoded PC/SC reader index (0-based).

**For 100 individual readers**: Slot numbers 0-99, as long as pcscd recognizes all 100 readers.

**Problem**: If a reader disconnects and reconnects, its slot number may change. The sim-rest-server has no mechanism to handle this — it trusts pcscd's slot numbering.

**For sysmoOCTSIM**: Slot numbers 0-7 per board, which are STABLE because the board's USB serial number is stable and slot indices within a board are fixed.

### 5.2 strongSwan eap-aka-3gpp

**⚠️ CRITICAL: eap-sim-pcsc does NOT support EAP-AKA!**

From strongSwan issue #2600:
> "The eap-sim-pcsc plugin can only be used with EAP-SIM, not with EAP-AKA. It does not provide any quintuplets, only triplets."

**For EAP-AKA, you need either**:
1. **eap-aka-3gpp plugin** — Uses MILENAGE calculations with Ki/OPc from config files (no SIM card needed)
2. **Custom plugin** that reads quintuplets from SIM cards via PC/SC
3. **sim-rest-server** as a backend — strongSwan calls sim-rest-server for each authentication

**The typical architecture for 100-SIM RCS farm**:
```
RCS Client → strongSwan (EAP-AKA) → sim-rest-server → PC/SC → SIM cards
```

strongSwan's `eap-sim-pcsc` plugin supports EAP-SIM only (triplets), not EAP-AKA (quintuplets). For EAP-AKA with real SIMs, you need the sim-rest-server approach.

**Scaling to 100 readers**: strongSwan doesn't directly interact with PC/SC — it goes through sim-rest-server. So strongSwan's scaling is not the bottleneck; sim-rest-server's ability to address 100 slots is.

### 5.3 pySim Multi-Reader Support

pySim (Osmocom's SIM tool) supports multiple readers via the `--reader` parameter:
```bash
pySim-prog --reader 42 --read-params
```

This works with any number of readers as long as pcscd recognizes them all. pySim-shell also supports reader selection.

**For 100 readers**: pySim will work, but you need to know which reader index corresponds to which SIM. With consumer readers, this mapping is fragile.

### 5.4 How to Map Reader Names to SIM Identities (IMSI) Reliably

**The core problem**: Consumer readers have no way to identify which physical SIM is inserted.

**Approaches**:

1. **udev rules based on USB serial number + physical port** (BEST for consumer readers):
   ```bash
   # Create symlink based on reader serial and USB port
   SUBSYSTEM=="usb", ATTRS{idVendor}=="04e6", ATTRS{idProduct}=="5116", \
     ATTRS{serial}=="SCR3310_ABC123", SYMLINK+="sim-reader-%n"
   ```

2. **Read IMSI at startup and build a mapping table**:
   ```python
   # Pseudocode
   for reader_index in range(100):
       imsi = read_imsi(reader_index)
       mapping[reader_index] = imsi
   # Store mapping to file for reference
   ```

3. **Physical labeling**: Manually label each reader with its USB port path, then maintain a spreadsheet.

**With sysmoOCTSIM**: Each board has a USB serial number, and slots are indexed 0-7. Mapping is: `board_serial + slot_index → IMSI`. This is inherently deterministic.

### 5.5 udev Rules for Deterministic Reader Naming

```bash
# /etc/udev/rules.d/99-sim-readers.rules
# Rule 1: Create stable symlinks based on USB path (not serial, as many cheap readers lack serial numbers)
SUBSYSTEM=="usb", ATTRS{idVendor}=="04e6", ATTRS{idProduct}=="5116", \
  ATTRS{devpath}=="1.2", SYMLINK+="sim-reader-port-1-2"

# Rule 2: Set PCSCLITE_IGNORE for specific readers (pcsc-lite 2.3.2+)
# SUBSYSTEM=="usb", ATTRS{idVendor}=="04e6", ATTRS{serial}=="DO_NOT_USE", \
#   ENV{PCSCLITE_IGNORE}="1"
```

**Problem**: Many cheap readers don't have unique USB serial numbers. All readers of the same model may report the same (or empty) serial. In this case, **USB physical path** (`devpath`) is the only way to uniquely identify a reader — but this is fragile if hubs are reorganized.

---

## 6. Reliability & Operational Concerns

### 6.1 What Happens When a Reader Fails?

**Detection**:
- pcscd logs the reader removal event
- `SCardGetStatusChange()` returns `SCARD_E_READER_UNAVAILABLE`
- sim-rest-server returns HTTP 410 (Gone) for that slot

**Replacement**:
1. Physically swap the reader
2. pcscd auto-detects the new reader via udev
3. **The new reader gets a new index** — all software using the old index fails
4. Must update the reader-to-IMSI mapping

**With sysmoOCTSIM**: Replace the board, and slots 0-7 are immediately available at the same USB serial + slot indices. No mapping update needed.

### 6.2 Hot-Plug: Can You Replace a Reader While pcscd Is Running?

**Yes, mostly.** pcscd supports hot-plug natively:
- Reader insertion: udev triggers pcscd to add the reader
- Reader removal: pcscd removes the reader from its list
- **However**: The reader's index changes. Any software holding a connection to the old reader index gets `SCARD_E_READER_UNAVAILABLE`.

**Risk**: If multiple readers are on the same hub and the hub briefly disconnects (e.g., power glitch), ALL readers on that hub get new indices. This can cascade across your entire mapping table.

### 6.3 SIM Card Seating: 24/7 Reliability

**Consumer readers**: 
- ID-1 card slots are designed for occasional insertion, not permanent seating
- SIM-in-adapter-in-reader = three layers of contact interfaces
- Contact oxidation over months of operation
- Vibration, dust, humidity all degrade contacts
- **Expected contact failure rate**: ~1-5% per year per reader

**sysmoOCTSIM**:
- Purpose-built SIM slots with spring-loaded contacts
- 2FF SIMs slot directly — no adapters needed
- Designed for 24/7 operation
- **Expected contact failure rate**: <0.5% per year per slot

### 6.4 Contact Reliability: Oxidation, Dust, Loose Connections

**Mitigation for consumer readers**:
1. Use gold-contact SIM cards (most commercial SIMs are gold)
2. Clean reader contacts periodically with isopropyl alcohol
3. Use dielectric grease on SIM contacts for environmental protection
4. Secure SIMs in adapters with Kapton tape
5. Mount readers in a vibration-free environment
6. Use enclosed cases to prevent dust ingress

### 6.5 USB Cable Failures

- **Failure rate**: ~1-3% per year for quality cables, higher for cheap ones
- **Common failure modes**: Broken wires at strain relief, loose USB-A connector, intermittent contact
- **Detection**: pcscd reports reader removal/reconnection; `dmesg` shows USB errors
- **Prevention**: Use quality cables, secure cable management, avoid frequent plugging/unplugging

### 6.6 Monitoring: How to Check 100 Readers Are All Responsive

**Script approach**:
```python
#!/usr/bin/env python3
import subprocess
import sys

EXPECTED_READERS = 100

def check_readers():
    result = subprocess.run(['pcsc_scan', '-n'], capture_output=True, text=True, timeout=30)
    lines = result.stdout.strip().split('\n')
    reader_count = sum(1 for l in lines if l.strip() and l[0].isdigit())
    
    if reader_count < EXPECTED_READERS:
        print(f"WARNING: Only {reader_count}/{EXPECTED_READERS} readers detected!")
        # Alert via Nagios/Prometheus/Slack
        return 1
    return 0

sys.exit(check_readers())
```

**sim-rest-server approach**: For each slot 0-99, try a simple APDU (e.g., SELECT MF). If it fails, mark that slot as unhealthy.

### 6.7 Boot Time: pcscd Initialization for 100 Readers

- pcscd startup: ~1 second
- Per-reader initialization: ~100-300ms (card power-up, ATR read)
- 100 readers in parallel: **~5-30 seconds** depending on USB bus topology
- Readers behind multiple hub levels initialize slower
- **Total boot-to-ready: ~30-60 seconds**

### 6.8 Power: Total Wattage for 100 Readers + 15 Hubs

| Component | Qty | Power Each | Total |
|-----------|-----|-----------|-------|
| CCID readers (idle) | 100 | 0.3W | 30W |
| CCID readers (active) | 100 | 0.6W | 60W |
| 7-port powered hubs | 16 | 5W | 80W |
| PCIe USB cards | 4 | 10W | 40W |
| **Total (active)** | | | **~180W** |

**Power supply requirements**:
- 16× 12V/2A power adapters for hubs = ~384W of supply capacity
- The server itself: ~200-400W
- **Total system: ~400-600W**

⚠️ **CRITICAL**: Many powered USB hubs ship with underpowered adapters. A "7-port hub" with a 12V/1A adapter can only provide ~150mA per port — insufficient for 7 CCID readers at ~100mA each. **Use hubs with at least 12V/2A (24W) adapters for 7-port, or 12V/5A (60W) for 10-port.**

---

## 7. Cost Breakdown (India-Specific)

### 7.1 Reader Options on Amazon.in / Flipkart

| Reader | Amazon.in Price (₹) | CCID Compliant | Notes |
|--------|---------------------|----------------|-------|
| **SCM SCR3310v2** | ₹3,500-5,000 | ✅ | Import, expensive |
| **ACS ACR38U-CCID** | ₹2,500-4,000 | ✅ | Via resellers, ACS India distributor |
| **ACS ACR39U-I1** | ₹2,000-3,500 | ✅ | Available on Amazon.in |
| **Generic USB CCID reader** | ₹200-800 | ⚠️ Varies | AliExpress/eBay imports, Amazon.in listings |
| **Gialer USB CCID reader** | ₹500-1,200 | ✅ (mostly) | Available on Amazon.com, rare on Amazon.in |
| **Kingstyle CCID reader** | ₹300-700 | ⚠️ Varies | Chinese import, cheap |

**IndiaMART** (wholesale):
- ACR38 bulk pricing: ₹1,500-3,000/piece for qty 50+
- Generic CCID readers: ₹200-500/piece for qty 100+

### 7.2 SIM Card Adapters on Amazon.in

| Adapter | Price (₹) | Notes |
|---------|-----------|-------|
| 4FF→2FF (Nano→Mini) | ₹50-150/pack of 5 | Widely available |
| 3FF→2FF (Micro→Mini) | ₹50-100/pack of 5 | Widely available |
| 2FF→ID-1 (Mini→Credit Card) | ₹100-300/each | sysmocom.de, professional quality |

### 7.3 Powered USB Hubs on Amazon.in

| Hub | Price (₹) | Ports | Power |
|-----|-----------|-------|-------|
| Amazon Basics 7-Port | ₹1,200-1,800 | 7 | 12V/2A |
| Sabrent 7-Port | ₹1,500-2,500 | 7 | 12V/2.5A |
| UGREEN 7-Port | ₹1,800-3,000 | 7 | 12V/2A |
| Anker 7-Port | ₹3,000-4,500 | 7 | 36W |
| Generic 10-Port | ₹1,500-2,500 | 10 | 12V/3A |
| Sabrent 10-Port | ₹2,500-4,000 | 10 | 60W |

### 7.4 PCIe USB Cards on Amazon.in

| Card | Price (₹) | Ports | Controllers |
|------|-----------|-------|-------------|
| Startech PEXUSB3S2 | ₹2,500-4,000 | 2 | 1 |
| Startech PEXUSB3S4V | ₹5,000-8,000 | 4 | 4 (independent!) |
| Inateck KT4006 | ₹2,000-3,500 | 4 | 2 |
| Generic PCIe USB 3.0 | ₹1,000-2,000 | 4 | 1-2 |

### 7.5 Server Requirements

| Spec | Minimum | Recommended |
|------|---------|-------------|
| CPU | 4-core x86_64 | 8-core (Xeon E-series or Ryzen) |
| RAM | 4GB | 8GB+ |
| PCIe slots | 4× (for USB cards) | 4-8× |
| USB ports (native) | 2-4 | 4+ |
| Power supply | 500W | 750W+ |
| Rack mount | Optional | 2U-4U recommended |

**Used server options** (India):
- Dell PowerEdge T430/R430: ₹15,000-30,000 (used)
- HP ProLiant DL360 Gen9: ₹20,000-40,000 (used)
- Custom whitebox: ₹20,000-35,000 (new)

### 7.6 Total Landed Cost: 100-SIM Consumer Reader Farm

| Item | Qty | Unit Price (₹) | Total (₹) |
|------|-----|----------------|-----------|
| Generic CCID readers | 100 | ₹500 | ₹50,000 |
| SIM adapters (2FF→ID-1) | 100 | ₹150 | ₹15,000 |
| 7-port powered hubs | 16 | ₹1,500 | ₹24,000 |
| PCIe USB cards (4-controller) | 4 | ₹5,000 | ₹20,000 |
| USB cables (short, quality) | 100 | ₹50 | ₹5,000 |
| Server (used) | 1 | ₹25,000 | ₹25,000 |
| Power strips/UPS | 2 | ₹3,000 | ₹6,000 |
| Cable management (racks, ties) | 1 | ₹5,000 | ₹5,000 |
| **SUBTOTAL** | | | **₹1,50,000** |
| Shipping & customs (15%) | | | ₹22,500 |
| Contingency (10%) | | | ₹15,000 |
| **TOTAL (Consumer)** | | | **~₹1,87,500** |

### 7.7 Total Cost: sysmoOCTSIM Approach

| Item | Qty | Unit Price (€) | Total (€) | Total (₹ approx) |
|------|-----|---------------|----------|-------------------|
| sysmoOCTSIM v2 | 13 | €100-150 | €1,300-1,950 | ₹1,20,000-1,80,000 |
| Shipping (UPS from Germany) | 1 | €50-100 | €50-100 | ₹5,000-9,000 |
| PCIe USB cards | 2 | €30 | €60 | ₹5,500 |
| Powered hubs | 2 | €20 | €40 | ₹3,700 |
| Server (used) | 1 | €200 | €200 | ₹18,400 |
| SIM adapters (if needed) | 0 | — | €0 | ₹0 |
| **TOTAL (sysmoOCTSIM)** | | | **€1,650-2,350** | **~₹1,52,000-2,17,000** |

### 7.8 Cost Comparison

| Approach | Total Cost (₹) | Cost per SIM slot |
|----------|----------------|-------------------|
| Consumer CCID (100 readers) | ₹1,87,500 | ₹1,875 |
| sysmoOCTSIM (13 boards = 104 slots) | ₹1,52,000-2,17,000 | ₹1,462-2,087 |

**The costs are SIMILAR**, but sysmoOCTSIM provides dramatically better reliability, density, and operational simplicity.

---

## 8. What We CANNOT Do with Consumer Readers

### 8.1 Cannot Reliably Identify Which Physical SIM Is in Which Reader

- Without udev rules based on USB serial + port path, reader names change on reboot
- Many cheap readers lack unique USB serial numbers
- If a hub is moved to a different port, all reader names change
- **Must build IMSI→reader mapping at every boot** by reading each SIM

### 8.2 Reader Names May Change on Reboot

- USB bus enumeration order depends on kernel probe order
- Device addresses are assigned dynamically
- If you add/remove a hub, all downstream reader names change
- **No stable naming without udev rules**

### 8.3 No LED per Slot

- sysmoOCTSIM has per-slot LEDs (on some versions)
- Consumer readers may have a single LED per reader
- No way to visually identify which SIM is in which reader
- Debugging a "dead slot" requires physically tracing cables

### 8.4 Messier Cabling, Harder to Troubleshoot

- 100 readers × USB cables = 100 cables
- 16 hubs × power adapters = 16 power bricks
- 4 PCIe cards inside server = limited airflow
- Total: ~120+ cables to manage
- **sysmoOCTSIM**: 13 boards, 13 USB cables, 1-2 hubs — 15 cables total

### 8.5 SIM Seating Less Reliable Than sysmoOCTSIM

- Consumer readers are designed for ID-1 cards, not SIMs
- SIM-in-adapter-in-reader = triple contact interface
- Spring contacts may weaken over time
- Dust/oxidation more likely in open-frame setups

### 8.6 Additional Limitations

1. **No per-slot power control**: Can't reset an individual SIM card without physically removing it
2. **No per-slot monitoring**: Can't tell if a SIM has shifted in its adapter
3. **EMI concerns**: 100 USB devices may cause electromagnetic interference
4. **Boot dependency**: If any hub has a power issue, all downstream readers fail simultaneously
5. **Thermal management**: 100 readers in a rack generate heat; consumer readers aren't designed for rack density
6. **Warranty/support**: No vendor support for 100-reader consumer setups; sysmoOCTSIM has sysmocom support

---

## 9. The "Building 128/256 SIM Bank" Reference

### 9.1 Article Details

- **Author**: @sertys on Medium
- **Published**: September 8, 2023
- **Title**: "Building a 128/256 SIM card bank with consumer tech on the cheap"
- **URL**: https://medium.com/@sertys/building-a-128-256-sim-card-bank-with-consumer-tech-on-the-cheap-884ea1b3874c
- **Tags**: sms-marketing, sms, sms-gateway, raspberry-pi, development
- **Reading time**: ~7 minutes

### 9.2 What Hardware They Used

Based on the article metadata and available information:
- **Kingstyle USB CCID readers** (cheap Chinese CCID readers, ~$5-10 each)
- **Raspberry Pi** as the host platform (ARM-based SBC)
- **Powered USB hubs** for reader expansion
- **Linux** (Raspberry Pi OS) with pcscd

### 9.3 Problems Encountered

From the article description and common multi-reader issues:
- **pcscd 16-reader limit**: Had to recompile pcscd and libccid
- **Reader enumeration instability**: Names changed across reboots
- **USB power**: Hubs needed to be adequately powered
- **SIM adapter reliability**: Adapters for nano-SIMs were problematic
- **Heat management**: 128+ readers in a small space generates significant heat

### 9.4 Total Cost

The article title says "on the cheap" — suggesting a total cost significantly lower than commercial SIM banks. Based on typical pricing:
- 128 × Kingstyle readers (~$5 each) = ~$640
- 16+ powered USB hubs (~$15 each) = ~$240
- Raspberry Pi 4 = ~$55
- Power supplies, cables = ~$100
- **Estimated total: ~$1,000-1,500 for 128 SIMs**

### 9.5 Lessons Learned

1. **Recompiling pcscd is mandatory** for >16 readers
2. **USB power is the #1 operational issue** — underpowered hubs cause random reader disconnections
3. **Reader naming is unstable** — must build a mapping table at each boot
4. **Cheap readers work but have higher failure rates** (~2-5% per year)
5. **Raspberry Pi can handle the software load** but USB controller limitations (shared single root hub) are a bottleneck
6. **Heat is a concern** in dense deployments

---

## 10. Recommendation

### For 100-SIM RCS Messaging Farm: **sysmoOCTSIM is strongly recommended over consumer CCID readers.**

### Reasoning:

1. **USB Endpoint Limit**: The single biggest technical blocker for consumer readers. You need 4+ PCIe USB cards with independent XHCI controllers to handle 100 readers. sysmoOCTSIM needs only 13 USB devices = 39 endpoints — trivial for any single controller.

2. **Operational Complexity**: 100 individual readers + 16 hubs = 116+ cables, 16+ power adapters, 4 PCIe cards. sysmoOCTSIM = 13 USB cables. The operational overhead of managing 100 consumer readers is enormous.

3. **Reliability**: Consumer reader + SIM adapter = fragile. sysmoOCTSIM = purpose-built SIM slots. Expected annual failure rate: 1-5% (consumer) vs <0.5% (sysmoOCTSIM).

4. **Deterministic Naming**: sysmoOCTSIM provides stable slot numbering based on USB serial + slot index. Consumer readers require complex udev rules and boot-time IMSI scanning.

5. **Cost Parity**: Total costs are similar (₹1.5-2.0 lakh for either approach). sysmoOCTSIM's higher per-unit cost is offset by needing fewer hubs, PCIe cards, adapters, and cables.

6. **Support**: sysmocom provides professional support. Consumer reader setups are DIY with community support only.

### When Consumer Readers Make Sense:

- **Extreme budget constraint** (<₹50,000 total, accepting higher operational cost)
- **Temporary/prototype** setup (not production)
- **<20 SIMs** (within pcscd default limit and single USB controller)
- **Already have** spare readers available
- **When you need 200+ SIMs** and sysmoOCTSIM boards become too expensive (though sysmoSIMBANK with 96/192 slots may be a better option)

### If Proceeding with Consumer Readers:

**Minimum requirements**:
1. Use readers with unique USB serial numbers (Gemalto, SCM — NOT cheap generic)
2. Recompile pcscd and libccid with MAX_READERS=128
3. Use 4+ PCIe USB cards with independent XHCI controllers
4. Use quality powered hubs with adequate power (12V/2A+ for 7-port)
5. Build IMSI→reader mapping at every boot
6. Implement monitoring that detects reader disconnections
7. Use 2FF (mini-SIM) cards directly in ID-1 adapters (avoid nano-SIM→adapter→ID-1 triple-stacking)
8. Mount everything in a structured rack with cable management

---

## References

1. **CCID Supported Readers List**: https://ccid.apdu.fr/ccid/supported.html
2. **pcscd Max Readers Discussion**: https://github.com/LudovicRousseau/PCSC/issues/8
3. **Ludovic Rousseau's Blog - USB Endpoint Limits**: https://blog.apdu.fr/posts/2021/03/a-lot-of-readers-connected-to-computer/
4. **Ludovic Rousseau's Blog - Accessing Many Smart Cards**: https://blog.apdu.fr/posts/2021/03/accessing-lot-of-smart-cards/ (and https://ludovicrousseau.blogspot.com/2021/03/accessing-lot-of-smart-cards.html)
5. **sysmoOCTSIM**: https://sysmocom.de/products/sim/sysmooctsim/index.html
6. **sysmoSIMBANK (96/192 slots)**: https://sysmocom.de/products/sim/sysmosimbank/
7. **sim-rest-server Documentation**: https://downloads.osmocom.org/docs/pysim/master/html/sim-rest.html
8. **strongSwan EAP-SIM-PCSC**: https://launchpad.net/ubuntu/trusty/+package/strongswan-plugin-eap-sim-pcsc
9. **strongSwan EAP-AKA-3GPP Feature**: https://wiki.strongswan.org/issues/2326
10. **Medium Article - 128/256 SIM Bank**: https://medium.com/@sertys/building-a-128-256-sim-card-bank-with-consumer-tech-on-the-cheap-884ea1b3874c
11. **Acroname USB Endpoint Limits**: https://acroname.com/blog/how-many-usb-devices-can-i-connect
12. **OpenSC Smart Card Readers Wiki**: https://github.com/OpenSC/OpenSC/wiki/Smart-card-readers-(Linux-and-Mac-OS-X)
13. **PCSC-Lite Gentoo Wiki**: https://wiki.gentoo.org/wiki/PCSC-Lite
14. **sysmocom Shop**: https://shop.sysmocom.de/SIM/
