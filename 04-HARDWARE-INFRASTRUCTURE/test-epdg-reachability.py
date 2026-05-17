#!/usr/bin/env python3
"""
Jio/Airtel/Vi ePDG Reachability Tester

Tests whether Indian carrier ePDGs respond to IKEv2 from your IP.
If all TIMEOUT → your IP is geoblocked. You need an Indian IP.

Usage:
  python3 test-epdg-reachability.py          # Test from current IP
  python3 test-epdg-reachability.py --proxy  # Show proxy options
  
Results:
  - "RESPONSE" = ePDG is reachable (your IP is not blocked)
  - "TIMEOUT"  = ePDG is not responding (geoblocked or filtered)
"""

import socket, struct, time, sys, json

# Known Indian ePDG IPs (resolved via DNS FQDNs)
EPPGS = {
    "Jio (MNC856/MCC405)": {
        "fqdn": "epdg.epc.mnc856.mcc405.pub.3gppnetwork.org",
        "ips": ["49.44.190.248", "49.44.190.243"],
    },
    "Airtel (MNC010/MCC404)": {
        "fqdn": "epdg.epc.mnc010.mcc404.pub.3gppnetwork.org",
        "ips": ["106.201.214.127", "106.201.214.99", "106.201.214.117"],
    },
    "Vi (MNC002/MCC404)": {
        "fqdn": "epdg.epc.mnc002.mcc404.pub.3gppnetwork.org",
        "ips": ["106.201.214.113"],
    },
}

PROXY_OPTIONS = [
    {"name": "IPMunk", "price": "$27/mo", "type": "Jio/Airtel 4G", "udp": True, "proto": "SOCKS5+UDP"},
    {"name": "Coronium.io", "price": "$30-50/mo", "type": "Jio/Airtel/Vi SIMs", "udp": True, "proto": "HTTP+SOCKS5"},
    {"name": "SOAX", "price": "$2/GB", "type": "Jio/Airtel/BSNL mobile", "udp": True, "proto": "HTTP+SOCKS5+UDP/QUIC"},
    {"name": "Hostinger India VPS", "price": "₹599/mo", "type": "Indian DC IP", "udp": "N/A (direct)", "proto": "Direct"},
    {"name": "AWS Mumbai", "price": "₹1,500/mo", "type": "Indian DC IP", "udp": "N/A (direct)", "proto": "Direct"},
    {"name": "DIY (friend's phone)", "price": "₹599/mo", "type": "Real Jio mobile IP", "udp": "Via WireGuard", "proto": "Socseeds/Proxidize"},
]

def make_ike_init(target_ip, target_port, timeout=5):
    """Send minimal IKE_SA_INIT and check for response."""
    # IKEv2 header: initiator cookie | responder cookie | next payload | version | exchange type | flags | message ID | length
    isakmp_hdr = struct.pack('!II', 0xDEADBEEF, 0x00000000)  # cookies
    isakmp_hdr += struct.pack('!BB', 0x00, 0x20)              # next: none, version: 2.0
    isakmp_hdr += struct.pack('!BB', 0x22, 0x08)              # IKE_SA_INIT, initiator
    isakmp_hdr += struct.pack('!II', 0x00000000, 28)          # msg ID, length
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        start = time.time()
        sock.sendto(isakmp_hdr, (target_ip, target_port))
        data, addr = sock.recvfrom(4096)
        elapsed = time.time() - start
        if len(data) >= 12:
            resp_exchange = data[10]
            resp_flags = data[11]
            is_responder = bool(resp_flags & 0x20)
            if resp_exchange == 34 and is_responder:
                return "REACHABLE", f"IKEv2 RESPONSE ({len(data)}B, {elapsed:.2f}s) - ePDG IS LIVE!"
            elif resp_exchange == 35:  # IKE_AUTH
                return "REACHABLE", f"IKE_AUTH response ({len(data)}B, {elapsed:.2f}s)"
            else:
                return "UNKNOWN", f"Response ({len(data)}B, {elapsed:.2f}s) exchange={resp_exchange}"
    except socket.timeout:
        return "BLOCKED", f"TIMEOUT ({timeout}s) - geoblocked or port filtered"
    except Exception as e:
        return "ERROR", str(e)
    finally:
        sock.close()

def get_my_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return "unknown"

def get_public_ip():
    import urllib.request
    try:
        return urllib.request.urlopen('https://ifconfig.me', timeout=5).read().decode().strip()
    except:
        try:
            return urllib.request.urlopen('https://icanhazip.com', timeout=5).read().decode().strip()
        except:
            return "unknown"

def main():
    if "--proxy" in sys.argv:
        print("\n=== Indian Proxy Options for ePDG Bypass ===\n")
        print(f"{'Provider':<25} {'Price':<12} {'IP Type':<25} {'UDP?':<15} {'Protocol'}")
        print("-" * 95)
        for p in PROXY_OPTIONS:
            print(f"{p['name']:<25} {p['price']:<12} {p['type']:<25} {str(p['udp']):<15} {p['proto']}")
        print("\nRecommended: Start with Hostinger VPS (₹599/mo). If DC IP blocked, upgrade to IPMunk mobile proxy ($27/mo).")
        return
    
    print("=" * 70)
    print("  Indian ePDG Reachability Tester")
    print("=" * 70)
    
    # Get our IP info
    pub_ip = get_public_ip()
    print(f"\n  Our IP: {pub_ip}")
    
    # Check location
    try:
        import urllib.request
        info = urllib.request.urlopen(f'https://ipinfo.io/{pub_ip}/json', timeout=5).read().decode()
        loc = json.loads(info)
        print(f"  Location: {loc.get('city', '?')}, {loc.get('country', '?')}")
        print(f"  Org: {loc.get('org', '?')}")
    except:
        print("  Location: unknown")
    
    print(f"\n  Testing IKEv2 reachability to Indian ePDGs...")
    print(f"  (If all TIMEOUT = your IP is geoblocked)\n")
    
    results = {}
    for carrier, info in EPPGS.items():
        print(f"--- {carrier} ---")
        print(f"  FQDN: {info['fqdn']}")
        carrier_reachable = False
        for ip in info['ips']:
            for port in [500, 4500]:
                status, msg = make_ike_init(ip, port)
                symbol = "✓" if status == "REACHABLE" else "✗"
                print(f"  {symbol} {ip}:{port} -> {msg}")
                if status == "REACHABLE":
                    carrier_reachable = True
        results[carrier] = carrier_reachable
        print()
    
    # Summary
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    all_blocked = all(not v for v in results.values())
    if all_blocked:
        print(f"\n  ALL CARRIERS BLOCKED from IP {pub_ip}")
        print(f"  You need an Indian IP to reach ePDG.")
        print(f"\n  Options:")
        print(f"    1. Indian VPS:    Hostinger ₹599/mo, AWS Mumbai free tier")
        print(f"    2. Mobile proxy:  IPMunk $27/mo (real Jio 4G IP)")
        print(f"    3. DIY proxy:    Friend's phone in India + Socseeds app")
        print(f"\n  Run with --proxy flag for full provider list:")
        print(f"    python3 test-epdg-reachability.py --proxy")
    else:
        reachable = [k for k, v in results.items() if v]
        print(f"\n  REACHABLE carriers: {', '.join(reachable)}")
        print(f"  You can proceed with ePDG connection from this IP!")

if __name__ == "__main__":
    main()
