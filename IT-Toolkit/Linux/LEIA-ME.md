# Linux

**O IT Toolkit não corre em Linux, e não é por falta de porte.**

---

## Porquê

Esta pasta existe para dar a resposta em vez de a deixar por descobrir. Os outros projectos deste repositório têm aqui um lançador; este não tem, e a razão é a própria natureza da ferramenta.

O IT Toolkit não é uma aplicação que por acaso foi escrita em Windows. É uma aplicação **sobre** o Windows. O que ela faz é:

| Módulo | O que lê | Existe em Linux? |
| :--- | :--- | :--- |
| Análise de eventos | Registos de eventos do Windows, via `wevtutil` | Não. O equivalente é o `journald`, com um modelo de dados completamente diferente |
| Inventário | WMI — processador, memória, placas, BIOS | Não. WMI é uma API do Windows |
| Discos | SMART via WMI e `wmic` | Há equivalentes (`smartctl`), mas nada em comum com o código actual |
| Serviços | Serviços do Windows, via `sc` e PowerShell | Não. O equivalente é o `systemd` |
| Rede | `ipconfig`, `netsh` | Os equivalentes existem e chamam-se outra coisa |

Portar isto não seria portar: seria **escrever outra aplicação** que faz o mesmo trabalho num sistema diferente, partilhando pouco mais do que a interface gráfica e a estrutura dos relatórios.

---

## O que a alternativa seria

Se um dia fizer sentido, o caminho não é adaptar este código. É criar um projecto próprio — um *Linux Toolkit* — com a mesma ideia e a mesma estrutura de relatórios, lendo `journalctl`, `systemctl`, `lsblk`, `smartctl` e `/proc`. A camada de apresentação e o motor de relatórios são reaproveitáveis; a recolha não é.

---

## O que **corre** em Linux, neste repositório

| Projecto | Branch |
| :--- | :--- |
| PDF Suite | [`PDF-Suite`](../../../../tree/PDF-Suite) |
| Monitor de Toners | [`Printer-Remote-Toner-Monitor`](../../../../tree/Printer-Remote-Toner-Monitor) |
| Transcritor Médico PT | [`Medical-Audio-to-Text`](../../../../tree/Medical-Audio-to-Text) |
| Network Config Builder | [`Network-Config-Builder`](../../../../tree/Network-Config-Builder) |
| Network Topology Mapper | [`Network-Topology-Mapper`](../../../../tree/Network-Topology-Mapper) |

Cada um tem uma pasta `Linux/` com um lançador que funciona.

---

<sub>Created by Redfox using Claude</sub>
