# macOS

**O IT Toolkit não corre em macOS, e não é por falta de porte.**

---

## Porquê

Esta pasta existe para dar a resposta em vez de a deixar por descobrir. Os outros projectos deste repositório têm aqui um lançador; este não tem, e a razão é a própria natureza da ferramenta.

O IT Toolkit não é uma aplicação que por acaso foi escrita em Windows. É uma aplicação **sobre** o Windows. O que ela faz é:

| Módulo | O que lê | Existe em Linux? |
| :--- | :--- | :--- |
| Análise de eventos | Registos de eventos do Windows, via `wevtutil` | Não. O equivalente é o `log show` unificado da Apple, com outro modelo de dados |
| Inventário | WMI — processador, memória, placas, BIOS | Não. O equivalente é o `system_profiler` |
| Discos | SMART via WMI e `wmic` | Há o `diskutil` e o `system_profiler`, mas nada em comum com o código actual |
| Serviços | Serviços do Windows, via `sc` e PowerShell | Não. O equivalente é o `launchd` |
| Rede | `ipconfig`, `netsh` | Existem `ifconfig` e `networksetup`, com outra sintaxe |

Portar isto não seria portar: seria **escrever outra aplicação** que faz o mesmo trabalho num sistema diferente, partilhando pouco mais do que a interface gráfica e a estrutura dos relatórios.

---

## O que a alternativa seria

Se um dia fizer sentido, o caminho não é adaptar este código. É criar um projecto próprio — um *macOS Toolkit* — com a mesma ideia e a mesma estrutura de relatórios, lendo `log show`, `launchctl`, `diskutil` e `system_profiler`. A camada de apresentação e o motor de relatórios são reaproveitáveis; a recolha não é.

---

## O que **corre** em macOS, neste repositório

| Projecto | Branch |
| :--- | :--- |
| PDF Suite | [`PDF-Suite`](../../../../tree/PDF-Suite) |
| Monitor de Toners | [`Printer-Remote-Toner-Monitor`](../../../../tree/Printer-Remote-Toner-Monitor) |
| Transcritor Médico PT | [`Medical-Audio-to-Text`](../../../../tree/Medical-Audio-to-Text) |
| Network Config Builder | [`Network-Config-Builder`](../../../../tree/Network-Config-Builder) |
| Network Topology Mapper | [`Network-Topology-Mapper`](../../../../tree/Network-Topology-Mapper) |

Cada um tem uma pasta `macOS/` com um lançador que funciona.

---

<sub>Created by Redfox using Claude</sub>
