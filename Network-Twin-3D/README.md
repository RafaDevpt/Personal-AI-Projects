<!--
  Network Twin 3D — README
  Created by Redfox using Claude
-->

<div align="center">

# 🧊 Network Twin 3D

**The network as it is, against the network as it was designed — in 3D, inside and outside the buildings, down to the rack unit, with every cable checked at both ends**

![Status](https://img.shields.io/badge/status-alpha-DFA83F?style=for-the-badge)
[![CI](https://img.shields.io/github/actions/workflow/status/RafaDevpt/Personal-AI-Projects/network-twin-3d.yml?branch=network-twin-3d&style=for-the-badge&label=CI)](https://github.com/RafaDevpt/Personal-AI-Projects/actions/workflows/network-twin-3d.yml)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Three.js](https://img.shields.io/badge/Three.js-r186-000000?style=for-the-badge&logo=three.js&logoColor=white)
![Offline](https://img.shields.io/badge/offline-6E5494?style=for-the-badge)

<a href="https://github.com/RafaDevpt/Personal-AI-Projects"><img src="https://img.shields.io/badge/←_back_to_index-30363D?style=flat-square" /></a>

</div>

---

![Start screen](docs/img/inicio.png)

## What it does

A pretty network diagram proves nothing. What matters is whether each cable, with the configuration it has **at both ends**, actually carries what it should — and where, physically, that cable and those switches are.

Two sibling tools already exist. [Network Topology Mapper](https://github.com/RafaDevpt/network-topology-mapper) walks the network and records **what exists**. [Network Config Builder](https://github.com/RafaDevpt/network-config-builder) holds **what should exist**. Nobody was comparing them, and nobody could see them in the building.

Network Twin 3D does both:

- **Validates** — 30 checks over every cable, port, rack and placement: native VLAN mismatches, VLANs that die on a trunk, trunk on one side and access on the other, designed uplinks that are not there, single points of failure, PoE over budget, machines overlapping in a rack… Every finding comes with the fix.
- **Places** — every switch, AP and rack in its building, floor and room; the original floor plan as the floor texture; racks at real scale with the machines mounted unit by unit.
- **Imports** — floor plans from an image, PDF or **DXF (AutoCAD)**, with automatic room and outline detection, or a building outline from **OpenStreetMap**.
- **Dresses the outside** — façade **photos or elevation drawings** perspective-corrected onto the walls, real roofs, the **surroundings** from OpenStreetMap, your own orthophoto on the ground, and the **sun** at any date and time.

## Start: pick a building

Opening a project shows one card per building — plan thumbnail, floors, rooms, racks, devices, and the errors inside it. **Click a building and the whole building opens.** The top menus switch building and floor at any time.

![Second building](docs/img/pavilhao.png)

## Building view

![Building view](docs/img/edificio.png)

Floors stacked and pulled apart, the original plan on each floor, walls derived from the room polygons, racks with their machines, cables up risers and along ceiling trays. A cable to **another building** leaves through the nearest façade with a clickable `↗` label. Pick a single floor for full-height walls and room names; click a room and the camera flies in.

![Server room](docs/img/sala-servidores.png)

## Rack view

![Rack view](docs/img/bastidor.png)

The rack up close, door off: U numbering, a label column with leader lines, **free ranges marked**, neighbours in the same room alongside. Mount, edit or remove machines — switch, router, firewall, server, storage, UPS, patch panel, PDU, KVM, shelf — each with its own 3D model. A machine linked to a network device takes that device's position and colour, and its cables leave through the rack top. The app **refuses** overlapping machines, machines beyond the rack height, and a device mounted twice.

## Logical view and findings

![Network view](docs/img/rede.png)

The network by layers — edge, core, distribution, access, APs — independent of the building. **Click a finding** and everything else dims while the camera goes to the problem (switching building or opening the rack if needed).

![Finding focus](docs/img/constatacao.png)

## Exterior view

![Exterior view](docs/img/exterior.png)

All buildings where they stand, each placed by its geographic origin. Each is made of **volumes** (outline × height) with a **roof** — flat with parapet, mono-pitch, gable or hip — and each wall carries its **photo or elevation**, perspective-corrected. Walls with no photo get windows drawn per floor, at each floor's real height; at night they light up. Around them, the **surroundings** from OpenStreetMap: neighbours with height, roads by width, green, water, trees.

| Control | What it does |
| :--- | :--- |
| **Day / Hour** | The sun for the site's latitude and longitude, with shadows — which façade gets the afternoon sun |
| **X-ray** | Walls go transparent: floors, rooms, **racks** and devices inside, coloured by verdict and clickable. The basement shows through the ground |
| **Map · Neighbours · Trees · Orthophoto** | Surroundings layers |

![X-ray](docs/img/raio-x.png)

### From photos to façades

![Corner tool](docs/img/cantos.png)

Pick a volume edge in the editor's **Exterior** tab, load a photo (or an elevation, image or PDF) and drag the **four corners** of the façade — with a 4× loupe, perspective guides and a live preview. A homography straightens the photo onto the wall at its real proportions. The original is kept, so the corners can be re-fitted later. Trees and cars in front stay in the texture, as they would.

**What it is not:** photogrammetry. Rebuilding geometry from photos needs dozens to hundreds of overlapping shots and returns a messy mesh; with a handful of phone photos it does not work, local or cloud. The *shape* comes from the plans, the drawn volumes and OpenStreetMap; the photos are the *skin*. This is the method of Google's old Building Maker, and it gives a clean, recognisable model.

**Why not Google Maps:** its terms forbid storing its data or using it outside its API — exactly what a local app needs to do. OpenStreetMap is open (ODbL) and only asks for attribution, which the app shows. Surroundings are downloaded **once** into `envolvente.json` and work **offline** from then on.

![Editor — Exterior](docs/img/editor-exterior.png)

Volumes come from the floors above ground, from drawing on the ground-floor plan, or from OpenStreetMap `building:part`s with their heights and roof shapes. Pitched roofs sit on the volume's minimum rectangle; a volume that is not close to rectangular keeps a flat roof and says why — split it into rectangular volumes, which is how roofs are built anyway.

An **orthophoto** of your own (council, drone survey) goes on the ground, aligned by **two point pairs**, by the corner coordinates of a north-up image, or by hand.

## Building editor

![Building editor](docs/img/editor.png)

The importer that turns plans into the 3D building:

| Source | How |
| :--- | :--- |
| **Image / PDF** | Calibrate the scale (two clicks on a known dimension), set a common origin, then **detect all rooms** or use the **magic wand** room by room, and **detect the outline**. Text and door arcs on the plan are recognised as *not walls* by their shape, so they do not split rooms. |
| **DXF** | Pick the layers that are rooms; closed polylines become rooms with real measurements, and the texts inside them name them. Units from `$INSUNITS` (or chosen). |
| **OpenStreetMap** | Building outlines around a coordinate — and, when OSM knows the number of levels, the floors too. |
| **By hand** | Rectangle and polygon tools on a metre grid, vertex editing, snapping to neighbouring rooms so they share walls, right-angle mode. |

Duplicate a floor for repeated hotel floors. A live 3D preview grows as you draw. Saving validates exactly like reading — the editor never writes a file that will not open.

## Private by construction

- Everything is local: Three.js is vendored, nothing is fetched from the Internet. The OpenStreetMap lookups (outline, building parts, surroundings) are the only network calls, made only when you press the button, and stored afterwards.
- Real projects never belong in a public repository — they combine topology, addresses, floor plans, façade photos and the location of every rack. `.gitignore` blocks them; the bundled example is **entirely synthetic**: plans, façade "photos", elevation, surroundings and orthophoto are all invented.

## Download

Ready-to-run executables — **no Python needed** — on the [releases page](https://github.com/RafaDevpt/Personal-AI-Projects/releases) (`network-twin-3d-v…`):

| System | File | Open |
| :--- | :--- | :--- |
| Windows 10/11 (x64) | `NetworkTwin3D-…-windows-x64.zip` | `NetworkTwin3D.exe` (unsigned: SmartScreen → *More info → Run anyway*) |
| macOS (Apple Silicon) | `NetworkTwin3D-…-macos-arm64.zip` | `NetworkTwin3D.app` (unsigned: right-click → *Open* the first time) |
| Linux (x64, glibc 2.35+) | `NetworkTwin3D-…-linux-x64.tar.gz` | `NetworkTwin3D/NetworkTwin3D` (Qt WebEngine bundled) |

Each one is built on its own system's runner and smoke-tested on the bundled example before the release is published. To build yourself: `pip install -r requirements-compilar.txt && python empacotar/compilar.py`.

## Installation & usage (from source)

```
cd Network-Twin-3D
EXECUTAR.bat                                   # Windows — opens the window
./executar.sh                                  # Linux / macOS
EXECUTAR.bat --validar projeto.json            # headless: exit 0 clean, 1 errors, 2 unreadable
NetworkTwin3D --validar --exemplo               # the compiled app, on its bundled example
```

DXF and PDF import need two optional libraries: `pip install -r requirements-importacao.txt` (images work without them).

Then **Open the example hotel**. Everything else — data sources, project and building formats, every check, the editor workflow — is in [LEIA-ME](LEIA-ME.md) (Portuguese).

## Requirements on the other tools

Needs the **JSON export** of Network Topology Mapper (format 1), which records which side announced each cable — without it, a cable seen from one side only is indistinguishable from a healthy one.

## Tests

```
pip install -r requirements-dev.txt && python -m pytest      # engine, loaders, racks, exterior, bridge, importers
node --test "tests/js/*.test.mjs"                             # room detection; homography, rectification, roofs, sun
```

## Known limits

- The mapper reads each port's access VLAN, not trunk allowed lists: trunk checks compare **design against design** on both ends of a real cable.
- Room detection does not read text (no OCR): rooms are named in the list, or by the DXF.
- Photos give the exterior its **skin**, not its shape: no photogrammetry, so balconies and reliefs stay flat in the texture.
- Pitched roofs only on near-rectangular volumes; complex roofs are built from several volumes.
- Flat terrain: a hillside hotel stands on level ground (use a volume's base height for the higher blocks).
- The sun uses this computer's clock time zone, not the site's.
- One codebase for Windows, Linux and macOS rather than the three folders of the sibling projects: the window is HTML through pywebview, so the three copies would be identical.

## License

MIT — see the repository [LICENSE](../LICENSE). Three.js is MIT, © three.js authors (`src/nettwin/web/vendor/three/LICENSE`). OpenStreetMap data © OpenStreetMap contributors (ODbL).

---

<div align="center"><sub>Created by Redfox using Claude</sub></div>
