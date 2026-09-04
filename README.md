<!--
  Laboratório Virtual — README
  Created by Redfox using Claude
-->

<div align="center">

# 🧪 Laboratório Virtual

**Builds virtual machines without the two things that go wrong: an image that is not what it claims, and a specification that leaves the host unusable**

![Status](https://img.shields.io/badge/status-active-2EA043?style=for-the-badge)
![Version](https://img.shields.io/badge/version-1.3.1-1F6FEB?style=for-the-badge)
![PowerShell](https://img.shields.io/badge/PowerShell-5.1-5391FE?style=for-the-badge&logo=powershell&logoColor=white)
![bash](https://img.shields.io/badge/bash-3.2+-4EAA25?style=for-the-badge&logo=gnubash&logoColor=white)
![Tests](https://img.shields.io/badge/345_tests-2EA043?style=for-the-badge)

<a href="../../tree/main"><img src="https://img.shields.io/badge/←_back_to_index-30363D?style=flat-square" /></a>

</div>

---

## What it does

Creating a virtual machine is not hard. The two hard things are around it: making sure the image really is what it says it is, and picking a specification that does not leave the host unusable. This program concentrates on those two; for the rest it calls the hypervisor and gets out of the way.

Pick a system, answer three questions, and it fetches the image from the project's **own** servers with the whole verification chain along the way, works out the specification from what the host actually has, and builds the machine.

Three independent programs — `Windows/`, `Linux/`, `macOS/` — each with its own code, its own tests and its own launcher.

---

## The order of the checks matters more than the checks

Four layers, applied in an order that is itself the security property.

| Layer | What it proves |
| :--- | :--- |
| Domain allowlist, re-checked **on every redirect** | The file came from the project, not from somewhere a redirect pointed at |
| HTTPS, no exceptions | Nothing downgraded the connection along the way |
| GPG signature of the checksum manifest | The manifest is the project's, not an attacker's |
| SHA-256, mandatory, no off switch | The file matches the manifest |

Redirects are followed **by hand**, with `--max-redirs 0` and `-MaximumRedirection 0`, because the normal behaviour of `curl -L` and `Invoke-WebRequest` voids the allowlist entirely: a server could redirect anywhere and the program would download from there unchecked.

**And the signature is verified before the filename is read out of the manifest.** The other way round, a tampered manifest could point at anything — and the final checksum would happily confirm that anything matched the value the attacker put there.

**The filename is never invented.** It comes out of the signed manifest, because a name pinned in a catalogue goes stale on the first point release — and a wrong name is indistinguishable from an attack.

**A pinned fingerprint is a condition, not a warning.** A valid signature from the wrong key is exactly what an attacker with a tampered catalogue would produce.

### The program never claims more than it did

Layers that did not run appear in the report as `[--]` rather than being left off:

```
    [ok]  Domain on the trusted list
    [ok]  HTTPS on every hop
    [--]  GPG signature of the manifest
    [ok]  SHA-256 of the file
```

Saying "verified" when only a same-channel checksum was compared is a misleading truth, and this program is built on not telling it.

---

## It recognises the hypervisor you already paid for

Before proposing to install anything, it looks at what is already there — and it knows how to drive each one.

| | Recognises | Can build machines in it |
| :--- | :--- | :--- |
| **Windows** | Hyper-V · VirtualBox · **VMware Workstation** and Player | yes |
| **Linux** | KVM/libvirt · VirtualBox · **VMware Workstation** | yes |
| **macOS** | QEMU · VirtualBox · **Parallels Desktop** · **VMware Fusion** · UTM | yes, except UTM |

Somebody with a company-paid VMware, machines already inside it, does not need a second hypervisor — and should not have one. The two fight over the processor's virtualisation extensions and both end up slow.

**Offering "would you like to use the one you have?" and then not knowing how to use it would be a pretend question.** So the work was not detection: it was learning to drive each of them. And they are driven in ways that share nothing — Parallels has `prlctl`, a real command-line tool; VMware has no equivalent, only a text file, the `.vmx`, that describes the whole machine and is written by hand. There is no abstraction to share between the two, and inventing one would make both worse.

---

## When there is none, it installs one

Automatically. No wizard to click through — choosing "install VirtualBox" from a menu that says so is the answer, and asking again adds no decision.

The progress appears in the terminal: elapsed time and megabytes written, which is true, rather than a bar filling itself and pretending to know how much is left. **And the exit code is not trusted** — at the end it goes looking for `VBoxManage` where it should be, because an installer returning zero having installed nothing is a thing that happens.

**Each system gets its strongest available proof, and none of the three could copy another:**

- **Windows** — Oracle's `SHA256SUMS` is **not** GPG-signed, so the checksum only proves the file arrived intact. What proves origin is the **Authenticode signature**, verified against Windows' certificate chain — which did not come from Oracle
- **macOS** — Apple's **notarisation** of the `.dmg` and the **Developer ID** on the `.pkg` inside it
- **Linux** — no binary is downloaded at all. Oracle's **key is pinned by fingerprint** before it enters the system, and from then on the package manager verifies every package, forever

In all three it is the same idea: the layer that counts is the one that does **not** depend on the server that supplied the file. And in all three it is a condition, not a warning — what fails is deleted.

---

## Three questions, then nothing

1. **Which hypervisor** — the ones already here, plus the option to install another
2. **Where to keep the image** — asked when the image is chosen, not at the end. An image runs to three or five gigabytes, and saying this after downloading it would be saying it late
3. **The specification and the name, on one screen** — with the reasoning underneath

```
    Name            ubuntu-24-04
    Processor       4 core(s)            of 6 physical
    Memory          8 GB                 of 15.7 GB
    Disk            40 GB dynamic        321 GB free
    Network         NAT                  reaches the Internet, unreachable from outside

    1. Create with this specification
    2. Change something
    0. Cancel
```

**After that screen there are no more questions.** It downloads, verifies, creates.

The specification is worked out from the host, and the program explains the arithmetic instead of just giving numbers: never more virtual cores than physical, never more memory than the guest recommends, a reserve for the host capped at half the total, and a dynamic disk shrunk if the promise does not fit.

---

## Bring your own image

For a Proxmox, a TrueNAS, an appliance, or the ISO your company hands you. `.iso`, `.img`, `.raw`, `.qcow2`, `.vdi`, `.vmdk`, `.vhd`, `.vhdx`, `.ova`, `.ovf`.

**No guarantees are invented here.** The report shows four layers unapplied and, at best, the checksum.

What it can still do is say **where the file came from**, and each system knows something different: the Mark of the Web on Windows (which often carries the download URL), Gatekeeper's quarantine and `kMDItemWhereFroms` on macOS, `user.xdg.origin.url` on Linux. On all three, no mark means the system does not know — **not** that the file is safe.

And it knows that **an ISO is the installer while a disk image is the machine**: creating an empty disk beside a `.qcow2` and booting from a CD that is not there gives exactly the *no bootable device* nobody can explain.

---

## What each version knows that the others do not

- **Windows** — that WMI reports the processor extensions as disabled on a machine where Hyper-V is on, because Windows is itself a guest by then. And that WSL 2, Docker Desktop and Memory Integrity all switch the hypervisor on without saying so, which makes VirtualBox slow for no visible reason
- **Linux** — that `nproc` counts threads and not cores, and that joining the `kvm` and `libvirt` groups has no effect on the session already open
- **macOS** — that the system bash is 3.2 and has no `mapfile`, that there is no `sha256sum`, and that on Apple Silicon an x86_64 image does not run slowly: it runs emulated, ten to twenty times slower

---

## What this program refuses to do

- **Download Windows or macOS around the vendor's form.** Microsoft requires one; Apple only distributes on a Mac. It opens the official page and verifies the file afterwards
- **Virtualise macOS off Apple hardware.** Not a technical limit — the licence. And third-party macOS images are not legitimate, even when they work
- **Install Homebrew.** It is installed by piping a script from the Internet straight into an interpreter, which is the pattern this program exists to avoid. There is a test that fails if that ever appears here
- **Offer VirtualBox on an Apple Silicon Mac.** Oracle now publishes an ARM build, but on an ARM host only ARM guests get hardware acceleration — and VirtualBox is almost always wanted for an x86 guest
- **Manage machines after they are created.** It is not an administration panel. It creates, and gets out of the way

---

## Current state

- **345 tests** — 113 Windows · 116 Linux · 116 macOS. None opens a network connection, creates a virtual machine or installs anything
- **Seventeen images** in the catalogue: eleven Linux distributions including ARM64, two Microsoft evaluations, the macOS installer and two Android entries
- Continuous integration on **three native runners** — a Linux version tested on a Windows runner proves nothing about what it does on Linux, and the macOS version, written for bash 3.2, is only confirmed as such on a Mac
- Bilingual source throughout, PT-PT and EN-UK

---

## Installation

Pick your system's folder. Each is a complete program.

| Folder | How to open | Hypervisors |
| :--- | :--- | :--- |
| **`Windows/`** | Double-click `EXECUTAR.bat` | Hyper-V · VirtualBox · VMware |
| **`Linux/`** | `./executar.sh` | KVM/libvirt · VirtualBox · VMware |
| **`macOS/`** | Double-click `executar.command` | QEMU · VirtualBox · Parallels · Fusion |

Nothing needs to be installed beforehand: without a hypervisor the program still runs, shows everything, and offers to install one. Without `gpg` it runs and verifies the checksum — and says it did not verify the signature.

---

## Usage

```bash
EXECUTAR.bat -Diagnostico              # what this machine has, and what is missing
./executar.sh --verificar-catalogo     # validate the catalogue and show the fingerprints
./executar.sh --verificar-ficheiro caminho.iso --soma <SHA-256>
```

Full documentation in [`Laboratorio-Virtual/README.md`](Laboratorio-Virtual/README.md), and one per version: [Windows](Laboratorio-Virtual/Windows/LEIA-ME.md) · [Linux](Laboratorio-Virtual/Linux/LEIA-ME.md) · [macOS](Laboratorio-Virtual/macOS/LEIA-ME.md).

---

## Known limits

- **Creation in VMware and Parallels has not been exercised against the real products.** The `.vmx` is verified field by field and the `prlctl` calls follow the documentation, but neither the author's machine nor the CI runners have a licence for either. The first machine you build in one of them is the first real test
- **Windows and macOS images are not downloaded automatically**, and that is deliberate — see above
- **The catalogue ages.** Six of the seventeen images carry a pinned GPG fingerprint; the rest rely on the checksum and the official server's HTTPS certificate, because their projects publish nothing stronger
- **It does not convert images.** When a format does not suit the hypervisor it gives the `qemu-img` command and stops there. Converting three gigabytes is an operation whoever orders it should know they are ordering
- **The UTM machine on macOS is pointed at, not built.** Assembling a `.utm` bundle from a script gives, easily, a machine that opens and does not boot

---

## License

MIT — see [`LICENSE`](LICENSE).

<sub>Created by Redfox using Claude</sub>
