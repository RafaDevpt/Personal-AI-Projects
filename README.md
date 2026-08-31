<!--
  Network Topology Mapper — README
  Created by Redfox using Claude
-->

<div align="center">

# 🗺️ Network Topology Mapper

**Walks the network from the controller to the socket, and tells you what is on the other end**

![Status](https://img.shields.io/badge/status-active-2EA043?style=for-the-badge)
![Version](https://img.shields.io/badge/version-1.0.0-1F6FEB?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Read only](https://img.shields.io/badge/read--only-6E5494?style=for-the-badge)

<a href="../../tree/main"><img src="https://img.shields.io/badge/←_back_to_index-30363D?style=flat-square" /></a>

</div>

---

## What it does

Nobody knows what is plugged into port 27 of the second-floor switch. The label says "office" and was written in 2019. Finding out means walking to the comms room, following a cable, and hoping the patch panel matches the drawing.

Network Topology Mapper answers it from a desk. Give it one core switch — or a UniFi controller — and it walks the network on its own, neighbour to neighbour, down to the last access switch. On each one it reads the MAC address table, the ARP table, the port state and the PoE draw. Then it crosses all of it and produces the thing nobody has: **a list of every device, which switch and port it is on, and what it appears to be**.

Excel to work with, PDF with the topology drawn.

---

## How it finds things

### The walk

LLDP and CDP, breadth-first from the seeds. Every neighbour announcing itself as a switch joins the queue.

Two things deliberately do not: **access points**, which have no MAC table to give, and **IP phones**, which announce themselves as bridges because they genuinely contain a two-port switch. Without that second exception, mapping a hotel would try to authenticate against every room phone in the building.

### The correlation

A MAC address appears in the table of *every* switch between it and the rest of the network — on the uplink port each time, except on one, where it appears on the port it is actually plugged into. Finding that one is finding the device. LLDP is what tells an uplink from a socket.

Three cases get explicit handling rather than a guess: a MAC on **two sockets at once** (bonded NIC, or a loop) is flagged ambiguous with both locations; a MAC appearing **only on uplinks** is reported as sitting beyond a switch that could not be reached; and an **access point's port** is where the AP lives, not where its wireless clients live.

---

## What it will and will not claim

Every classification carries a **confidence level and the list of signals behind it**.

| Signal | Worth | Example |
| :--- | :--- | :--- |
| LLDP / CDP | High — the device speaks for itself | Announces itself as a WLAN AP → it **is** an AP |
| Factory hostname | High | `NPI1A2B3C` is an HP JetDirect |
| Virtualisation OUI | High | A VMware MAC **is** a virtual machine |
| PoE draw | Medium | 14 W is an AP; 5 W is a phone; 0 W is neither |
| Vendor OUI | Low to medium | An Intel NIC lives in a PC, a server or a high-end printer |
| Nothing | None | It says so |

**When signals disagree, confidence drops and the conflict is recorded.** HP is the case that forced the rule: it makes workstations and printers under the same OUI, and answering "workstation" would be right half the time and misleading the other half.

### The finding that earns its keep

A port with six MAC addresses and no LLDP neighbour has an **unmanaged switch** on the far side — the desk switch somebody plugged in. It explains the loops, the traffic where it should not be, and the socket that "sometimes drops". The conclusion is attached to the *port*, not to any of the six devices, because none of them is the switch.

---

## Read-only, by construction

Every command is checked against a list of allowed verbs before it is sent — `show`, `display`, and the `telnet localhost` needed to reach a UniFi's CLI. Chained commands are refused. A test walks every reader's command set and fails if any of them stops being a read.

A mapping tool enters an entire property's infrastructure, often with administrative credentials, out of hours, with nobody watching. That guarantee cannot depend on someone remembering.

Credentials are never written to disk — not the switches', not the controller's.

---

## Current state

- **155 tests**, none of which opens a network connection
- Three platform readers — Aruba AOS-CX, Cisco IOS/IOS-XE, Ubiquiti EdgeSwitch/UniFi — tested against saved output of the documented formats
- UniFi controller support for seeding and for exact wired-client locations
- GUI and headless CLI with distinct exit codes
- Bilingual source, PT-PT and EN-UK

---

## Installation

Double-click **`Windows\EXECUTAR.bat`**. No elevation required — this tool reads nothing from the local machine.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m netmap
```

---

## Usage

```bash
python -m netmap                                             # GUI
python -m netmap mapear --semente 10.0.10.1                  # map from a core switch
python -m netmap mapear --unifi https://10.0.10.5:8443       # seed from the controller
python -m netmap oui --importar oui.csv                      # load the full IEEE vendor list
```

Full documentation — including how to prepare the network so the map comes out complete — in [`Network-Topology-Mapper/README.md`](Network-Topology-Mapper/README.md).

---

## Known limits

- **Three platforms.** A Juniper or a MikroTik appears on the map as a neighbour but is not visited.
- **CLI readers follow documented formats.** A firmware that lays its tables out differently is read partially — and the tool **counts the lines it did not understand** and says so, rather than presenting a map with a silent hole.
- **No LLDP, no topology.** Tables can still be read per switch, but nothing links them.
- **A device that has not spoken recently is not in the MAC table.** A printer switched off for three days is not there.
- **The UniFi controller only knows the UniFi world.** On a mixed network it is a head start, not a source of truth.

---

## License

MIT — see [`LICENSE`](LICENSE).

<sub>Created by Redfox using Claude</sub>
