# osmo-remsim: Remote SIM Card Architecture for Multi-SIM RCS

**Source**: Firecrawl searches, 2026-05-16

---

## 1. What is osmo-remsim?

osmo-remsim is Osmocom's open-source **Remote SIM software suite** that decouples physical SIM cards from the devices (phones/modems) that use them.

- **GitHub**: https://github.com/osmocom/osmo-remsim
- **Wiki**: https://osmocom.org/projects/osmo-remsim/wiki
- **Manual**: https://ftp.osmocom.org/docs/osmo-remsim/0.2.2/osmo-remsim-usermanual.pdf

### Key Capability
> "Using osmo-remsim, you can operate an entire fleet of modems/phones, as well as banks of SIM cards and dynamically establish or remove the connections between modems/phones and cards."

---

## 2. Architecture

### 2.1 Components
| Component | Function |
|-----------|----------|
| **osmo-remsim-server** | Central coordinator, manages SIM-to-modem mappings |
| **osmo-remsim-bankd** | SIM Bank Daemon - manages one bank of SIM card readers |
| **osmo-remsim-client** | Runs on modem/phone side, connects to server to get SIM access |
| **osmo-remsim-client-shell** | Interactive client for manual SIM APDU exchange |

### 2.2 Hardware
- **sysmoQMOD**: Osmocom's modem board with remote SIM support
- **SIMtrace2**: Can act as SIM card emulator (client side)
- **ngff-cardem**: M.2 modem carrier board with SIM tracing/switching/remote forwarding
- **sysmoOCTSIM**: 8-slot SIM card reader (bank side)

### 2.3 Flow
```
[Phone/Modem] ←→ [SIMtrace2/ngff-cardem] ←→ [osmo-remsim-client]
                                                    ↓ (TCP/IP)
                                            [osmo-remsim-server]
                                                    ↓
                                        [osmo-remsim-bankd] ←→ [sysmoOCTSIM + 8 SIMs]
```

---

## 3. Can osmo-remsim Share One SIM Across Multiple IMS Registrations?

### 3.1 The Short Answer: **NO, not simultaneously**

osmo-remsim maps SIM cards to modems in a **1:1 relationship** at any given time. The mapping is dynamic (you can change it), but:
- One SIM → One modem at a time
- You CANNOT have the same SIM authenticated on two IMS networks simultaneously
- IMS AKA challenge-response is stateful (SQN sequence numbers must be sequential)

### 3.2 Time-Division Multiplexing (Theoretical)
You COULD theoretically:
1. Connect SIM-A to Modem-1 for 5 minutes
2. Disconnect, reconnect SIM-A to Modem-2 for 5 minutes
3. Each modem does its own IMS registration

**BUT**: IMS registrations expire. SIP re-REGISTER is needed every ~600,000 seconds (7 days). EAP-AKA re-auth is needed every 24h. You'd need each "session" to complete registration AND messaging before switching.

### 3.3 Practical Implication for RCS Farm
- **osmo-remsim does NOT reduce the number of SIMs you need**
- You still need 1 SIM per concurrent IMS registration
- The benefit is: SIMs can be in a centralized bank, modems can be distributed
- This is useful for **geographic distribution** (modems in different cities), not **SIM reduction**

---

## 4. How osmo-remsim COULD Help Your RCS Farm

### 4.1 Remote SIM Management
- Keep all 100 SIMs in a secure, climate-controlled bank room
- Modems/SIM-emulators can be anywhere with internet
- Dynamic reallocation: if one modem's IMS registration fails, swap SIMs without physical access

### 4.2 Centralized Key Management
- All SIMs in one physical location (the bank)
- Easier to manage re-auth cycles (EAP-AKA every 24h)
- Single point of monitoring and alerting

### 4.3 Integration with strongSwan-ePDG
- The osmo-remsim-bankd exposes APDU access to SIMs over TCP/IP
- strongSwan's PCSC plugin could potentially be modified to use osmo-remsim instead of local PCSC
- **This is NOT currently implemented** - would require custom development

### 4.4 Hardware Costs
| Item | Cost | Notes |
|------|------|-------|
| sysmoOCTSIM (8 slots) | ~€299 (~₹27,000) | Per 8 SIMs |
| SIMtrace2 | ~€199 (~₹18,000) | Per modem (client side) |
| osmo-remsim-server | Free (software) | Runs on any Linux |
| 100 SIMs = 13× sysmoOCTSIM | ~₹3,51,000 | SIM bank hardware |

---

## 5. Alternative: Building a 128/256 SIM Bank with Consumer Tech

From https://medium.com/@sertys/building-a-128-256-sim-card-bank-with-consumer-tech-on-the-cheap-884ea1b3874c

- Use consumer USB CCID smart card readers in bulk
- A single USB host can handle 128+ readers with proper USB topology
- Linux PCSC-lite handles multiple readers natively
- **Much cheaper than sysmoOCTSIM for large scale**

### Estimated Cost for 100-SIM Bank
| Item | Unit Cost | Qty | Total |
|------|-----------|-----|-------|
| USB CCID smart card reader | ₹500 | 100 | ₹50,000 |
| Powered USB hubs (7-port) | ₹1,500 | 15 | ₹22,500 |
| Server with enough USB ports | ₹30,000 | 1 | ₹30,000 |
| **Total** | | | **₹1,02,500** |

vs sysmoOCTSIM approach (13 units × ₹27,000 = ₹3,51,000)

**Consumer approach is 3.4x cheaper for 100 SIMs.**

---

## 6. Verdict: osmo-remsim for RCS Farm

| Factor | Assessment |
|--------|-----------|
| Reduces SIM count needed? | **NO** - still 1 SIM per registration |
| Enables remote SIM management? | **YES** - centralized SIM bank |
| Reduces physical access needs? | **YES** - no swapping SIMs physically |
| Works with strongSwan out of box? | **NO** - needs custom integration |
| Cost effective at 100 SIM scale? | **MAYBE** - consumer readers cheaper |
| Worth the complexity? | **MARGINAL** - only if you need geographic distribution |

### Recommendation
For a single-datacenter RCS farm, skip osmo-remsim. Use:
- **sysmoOCTSIM** (13 units) for 100 SIMs if budget allows
- **Consumer CCID readers** on USB hubs if budget-constrained
- Direct PCSC access from strongSwan/sim-rest-server

osmo-remsim only makes sense if you need modems in multiple cities connecting back to a central SIM bank.
