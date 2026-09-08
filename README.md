<!--
  VMware Fleet Console — README
  Created by Redfox using Claude
-->

<div align="center">

# 🖥️ VMware Fleet Console

**The whole VMware estate on one terminal screen — and the maintenance that follows**

![Status](https://img.shields.io/badge/status-active-2EA043?style=for-the-badge)
![Version](https://img.shields.io/badge/version-1.0.0-1F6FEB?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/691_tests-2EA043?style=for-the-badge)

<a href="../../tree/main"><img src="https://img.shields.io/badge/←_back_to_index-30363D?style=flat-square" /></a>

</div>

---

## What it does

At eleven at night something is wrong with a virtual machine and the answer is behind a browser, a certificate warning, a login, and four clicks through a web client that was not built for someone in a hurry.

VMware Fleet Console answers it from a terminal. It connects to a **vCenter** or straight to an **ESXi host**, reads the whole inventory in one pass, and puts on one screen the question that brought you there:

> **Is everything all right? And if not — what, where, and what do I do about it?**

Then it handles what comes next: power operations, snapshots, maintenance mode. No browser, and no re-authenticating every time.

---

## The certificate, which is where vSphere tooling usually goes wrong

Nearly every ESXi and vCenter presents a self-signed certificate, because that is what ships from the factory. So nearly everybody writing vSphere automation ends up writing the line that switches verification off:

```python
context.verify_mode = ssl.CERT_NONE     # <- what this application does NOT do
```

Past that line the connection is **encrypted but not authenticated**. Anything sitting between the workstation and the server can present itself as the server and take a vSphere administrator password in clear text out of the far end of the tunnel. On a management network running through the same switches as everything else, that is not a theoretical risk.

This does what SSH does instead:

1. **Try normal validation.** With an internal CA installed on the machine, this passes and there is nothing to discuss.
2. **If it fails, do not connect.** Show the SHA-256 fingerprint and wait for somebody to compare it against what the server displays. **No credential is sent before that.**
3. **Once accepted, pin it.** Later connections compare against the pin.

And **a changed fingerprint stops the connection**, showing the old and new side by side. That happens when a certificate is regenerated — and it happens when you are not talking to the same server any more. It is a nuisance once a year, and it is the difference between noticing a certificate substitution and not noticing one.

The refuse button holds focus, so somebody hitting Enter by reflex does not accept a certificate they did not read.

---

## Shutting down is not powering off

`ShutdownGuest` asks the guest to shut itself down. `PowerOff` is the wall socket. Both options always appear together with what each one does written beside them — and when VMware Tools are not running, the clean option appears **as a refusal with the reason**, rather than silently disappearing:

```
  > Encerrar pelo sistema convidado — limpo, pede às Tools
    Desligar à força — equivale a cortar a corrente
    Reiniciar pelo sistema convidado
    Suspender — guarda a memória em disco
```

### Confirmation is typed, not clicked

Destructive operations have no Yes and No. They have a box where the **object's name** must be typed.

A dialog with a confirm button teaches people to press confirm. A box that needs `SRV-DC01` typed into it forces you to read that the machine about to be stopped is called SRV-DC01. It is the only real defence against the list having sorted differently from how you thought.

Snapshot confirmations ask for the **machine's** name, not the snapshot's — every snapshot is called "before the upgrade", and typing that separates nothing.

---

## Three guards that earn the module

**A machine whose host is unreachable takes no orders.** vCenter still lists it carrying its last known state, and sending it a `PowerOn` returns an error nobody understands. The application says up front that it does not know the machine's state.

**Maintenance mode with machines still running.** In a DRS cluster vCenter migrates them and the task finishes. Without DRS — a single host, which is most small sites — the task sits at 2% *forever*, **with no error at all**, waiting for somebody to power the machines off by hand. So they are counted first and the warning says how many and what will happen.

**A free-licensed ESXi has a read-only API.** Every write is refused however administrative the account is, and the server's own error (`RestrictedVersion`) says nothing about licences. It is detected on connect and stated in the header, once, instead of letting every button fail unexplained.

**Reverting a snapshot is treated as a deletion, because it is one** — and the warning says how many days of changes go with it, not just that changes will be lost.

---

## What it tells you that nobody configured

vCenter has alarms, and this reads them all. What it adds are the readings nobody sets up as an alarm because they have no obvious threshold.

| Rule | Threshold | Why this value |
| :--- | :--- | :--- |
| Datastore free space | **10%** critical, **20%** warning | 10% is where VMFS stops being able to grow a snapshot or a thin disk without stopping the machines |
| Snapshot age | **3 d** warning, **30 d** critical | three days is where it stops being "one before the upgrade" and becomes a forgotten file |
| Snapshot chain depth | **3 levels** | each level is one more delta file read on every disk access |
| Host uptime | **90 d** | a full patch cycle unapplied |
| Host memory | **90%** | past 95% ESXi balloons and swaps, and what you notice is slowness *inside* the machines |
| VMware Tools | stopped / absent | with none, there is no clean shutdown |

Plus the question that needs the whole estate to answer: **if the largest host falls over, does the memory in use fit in what is left?** A host in maintenance does not count as headroom — it takes no machines.

### And what it refuses to do

**A healthy estate produces an empty report**, and a test enforces it. A tool that always flags something teaches its reader to ignore it.

It does not warn about templates, or about Tools on stopped machines — a template is powered off by definition, and on a stopped machine "Tools not running" is the description of a stopped machine.

It does not treat **"no data" as healthy**. vSphere's `gray` means vCenter is receiving nothing about that object: neither well nor sick, and usually the most urgent of the three.

---

## Passwords are never written to disk

There is no field for one, no option, and no "remember me" switched off by default that somebody could switch on. A vCenter administrator password reaches every machine on the estate — domain controllers, databases, backups. Encrypting it with a key that also sits on the machine does not fix that; it postpones it.

Tests fail if anybody adds a password field to a structure that gets serialised, and verify that a password put into the file by hand is ignored and does not survive the next write.

There is no `--senha` flag either: a command-line argument is visible in `ps` to every user on the machine and written to the shell history. For automation there is `VFC_PASSWORD`.

---

## Current state

- **691 tests** across three versions (235 Windows · 225 Linux · 231 macOS), **none of which needs a vCenter**
- Health rules, operation guards and the certificate decision all take already-read models and return decisions — which is what makes them testable against an estate invented in `conftest.py`
- Textual TUI plus a headless text mode with distinct exit codes
- CI on three native runners — `windows-latest`, `ubuntu-latest`, `macos-latest`
- Bilingual source, PT-PT and EN-UK

---

## Installation

Three independent versions, one per system. Pick yours and ignore the other two.

| Folder | System | Open with |
| :--- | :--- | :--- |
| [`Windows/`](VMware-Fleet-Console/Windows/) | Windows 10 / 11 | double-click `EXECUTAR.bat` |
| [`Linux/`](VMware-Fleet-Console/Linux/) | any distribution | `./executar.sh` |
| [`macOS/`](VMware-Fleet-Console/macOS/) | Apple Silicon and Intel | double-click `executar.command` |

No elevation required — this tool reads nothing from the local machine.

```bash
cd VMware-Fleet-Console/Linux
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m vfc
```

Two dependencies: `pyvmomi` and `textual`. That is all.

---

## Usage

```bash
python -m vfc                                          # the interface
python -m vfc --diagnostico                            # what this machine is missing
./cli.sh --servidor vcenter.local --utilizador admin@vsphere.local
./cli.sh --json --seccao estado                        # for automation
```

Exit codes: **0** nothing to report · **1** warnings · **2** critical · **3** could not connect. The 3 is separate on purpose — failing to connect is not the same as everything being wrong, and it is the distinction that avoids waking somebody over a network cable.

**Text mode writes nothing to vSphere.** A destructive operation with no typed confirmation sits one `Ctrl-R` away from the next time somebody repeats it without thinking. A test fails if such an option ever appears.

Full documentation in [`VMware-Fleet-Console/README.md`](VMware-Fleet-Console/README.md).

---

## Known limits

- **Free-licensed ESXi: the API is read-only.** A VMware licence restriction, not an application one. All monitoring works; no write does.
- **Without DRS, maintenance mode migrates nothing.** The application warns with the count of running machines, but does not move or stop them for you — that is the decision of whoever is doing the work.
- **It does not create machines, migrate them, or touch networking.** This is a maintenance tool, not an administration console. Those are project operations, and they belong in the web client.
- **Snapshot size is not always reported.** vCenter is inconsistent about it across versions and datastore types. When it is missing the warning goes without it rather than inventing a number — the age, which is what decides, is always there.
- **An open session is an open session.** On a large estate the refresh interval is load on vCenter. It is configurable, and zero switches automatic refresh off.

---

## License

MIT — see [`LICENSE`](LICENSE).

<sub>Created by Redfox using Claude</sub>
