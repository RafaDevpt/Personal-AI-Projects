<!--
  HP Toner Monitor — README
  Created by Redfox using Claude
-->

<div align="center">

# 🖨️ HP Toner Monitor

**Automated supply monitoring for HP printer fleets**

![Status](https://img.shields.io/badge/status-active-2EA043?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Protocols](https://img.shields.io/badge/LEDM_·_SNMP_·_HTTP-6E5494?style=for-the-badge)
![HP](https://img.shields.io/badge/HP_LaserJet-0096D6?style=for-the-badge&logo=hp&logoColor=white)

<a href="../../tree/main"><img src="https://img.shields.io/badge/←_back_to_index-30363D?style=flat-square" /></a>

</div>

---

## What it does

Checking toner levels across a printer fleet means opening the web interface of every device, one at a time, and writing down what you find. On a fleet of twenty-plus printers that is a recurring half-hour that produces nothing but a shopping list.

This tool does the round automatically:

- Queries every printer in the inventory
- **Flags any cartridge below 15%**
- Identifies the **colour and cartridge reference** so the reorder is unambiguous
- Saves each device's usage page as a **PDF named after the printer**
- Drafts the **reorder request as a local `.eml`** ready to review and send

---

## The collection chain

Corporate networks fight back. Proxies intercept, certificates are self-signed, SNMP is disabled on some models and not others. So collection falls through a chain rather than relying on one method:

```
  ┌────────┐    ┌────────┐    ┌──────────────┐    ┌─────────────────┐
  │  LEDM  │───►│  SNMP  │───►│  HTML scrape │───►│ Browser fallback│
  └────────┘    └────────┘    └──────────────┘    └─────────────────┘
    native        standard        parse EWS         Selenium + Edge
```

Each method is tried in turn; the first that answers wins. The browser fallback exists specifically for devices whose embedded web server serves HTTPS with a self-signed certificate — it handles the **"Your connection isn't private"** interstitial automatically so a certificate warning never stalls the run.

---

## Configuration

The inventory lives in a configuration file, one entry per device:

```json
{
  "printers": [
    {
      "name": "Reception-01",
      "ip": "192.0.2.10",
      "model": "HP LaserJet Pro M404dn",
      "location": "Front Office"
    }
  ],
  "threshold": 15,
  "output_dir": "./reports",
  "email": {
    "to": "supplies@example.com",
    "subject": "Toner reorder request"
  }
}
```

> Keep your real inventory out of version control. Ship an `config.example.json` and add `config.json` to `.gitignore` — IP addresses and internal hostnames do not belong in a public repository.

---

## Requirements

| | |
| :--- | :--- |
| **OS** | Windows 10 / 11 |
| **Python** | 3.11 or newer |
| **Browser** | Microsoft Edge (for the fallback method) |
| **Network** | Direct access to the printers — see troubleshooting below |

---

## Installation

```bash
git clone --branch toner-monitor --single-branch https://github.com/RafaDevpt/Personal-AI-Projects.git
cd Personal-AI-Projects
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy `config.example.json` to `config.json` and fill in your fleet.

---

## Usage

```
run.bat
```

Or:

```bash
python main.py
```

Output lands in the configured directory: one PDF per printer, plus a single `.eml` draft listing everything below threshold.

---

## Troubleshooting

<details>
<summary><b>Every printer times out</b></summary>

<br />

Almost always a proxy. A domain-joined machine routes HTTP through the corporate proxy, which has no idea what to do with an internal printer address.

Add the printer subnet to the proxy bypass list, or set `NO_PROXY` for the run:

```bash
set NO_PROXY=192.0.2.0/24
python main.py
```

</details>

<details>
<summary><b>Certificate warning blocks the browser fallback</b></summary>

<br />

Expected — printer embedded web servers use self-signed certificates. The fallback is built to click through the interstitial automatically. If it stalls, confirm the Edge WebDriver version matches your installed Edge.

</details>

<details>
<summary><b>A specific model returns nothing</b></summary>

<br />

Older LaserJets expose a different EWS layout and may not support LEDM at all. Confirm SNMP is enabled on the device, then check whether the HTML scrape needs a model-specific selector.

</details>

---

## Roadmap

- [ ] Scheduled unattended runs
- [ ] Historical consumption tracking per device
- [ ] Direct SMTP send instead of `.eml` draft
- [ ] Page count and duty cycle reporting
- [ ] Support for non-HP devices via pure SNMP

---

## License

GPL-3.0 — see [`LICENSE`](LICENSE) in the repository root.

<div align="center">
<sub>Created by Redfox using Claude</sub>
</div>
