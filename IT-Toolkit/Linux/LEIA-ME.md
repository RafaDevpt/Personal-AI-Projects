# Linux

**IT Toolkit — arranque em Linux**

Esta pasta é uma versão completa e independente. Não partilha código com as pastas `Windows/` e `macOS/`: lê o diário do systemd em vez do registo de eventos, fala com o `systemctl` em vez do gestor de serviços, e lê o `/sys/class/dmi/id` em vez do WMI.

---

## Como abrir

```bash
./executar.sh
```

Na primeira execução cria o ambiente e instala as dependências. Nas seguintes arranca directamente.

Se o ficheiro não estiver executável — acontece quando o repositório foi copiado por uma máquina Windows:

```bash
chmod +x executar.sh cli.sh
```

**Não corra a interface gráfica com `sudo`.** O Tk fica com o ambiente do root e os relatórios passam a pertencer ao root, o que impede o utilizador normal de os abrir. Para o diagnóstico completo, use `sudo ./cli.sh --cli`.

---

## Pré-requisitos

| O quê | Como |
| :--- | :--- |
| **Python 3.10+** | Vem em todas as distribuições suportadas |
| **Tkinter** | `python3-tk` (Debian/Ubuntu) · `python3-tkinter` (Fedora) · `tk` (Arch) |

Só duas dependências de Python, de propósito: tudo o resto assenta na biblioteca padrão e nas ferramentas que a distribuição já traz, porque esta ferramenta corre em máquinas geridas onde instalar pacotes é lento ou está bloqueado por política.

### O que é opcional, e o que se perde sem ele

O diagnóstico corre sem nada disto instalado. O que ele **não** faz é fingir que verificou o que não conseguiu ver — cada secção que fica vazia diz porquê e qual é o comando que resolve.

| Ferramenta | O que destranca | Sem ela |
| :--- | :--- | :--- |
| `smartmontools` | Estado de saúde dos discos | Não há aviso de disco a falhar |
| `dmidecode` | Modelo, número de série, BIOS | Inventário de hardware incompleto |
| `iproute2` | Endereços, rotas e DNS | Separador Rede vazio |
| `traceroute` | Rota até um destino | Usa o `tracepath` do `iputils` |

```bash
./executar.sh --diagnostico
```

Diz o que está instalado, o que falta e o comando de instalação **da sua distribuição**.

---

## As duas permissões, que não são a mesma coisa

Esta é a diferença que mais confunde num diagnóstico de Linux, e a razão de a barra lateral mostrar as duas:

- **root** — sem ele não há estado SMART nem número de série. O `smartctl` não consegue sequer abrir o dispositivo.
- **grupo `systemd-journal`** — sem ele o `journalctl` corre, devolve zero e mostra apenas as mensagens do próprio utilizador. Não há erro nenhum, e é por isso que é perigoso: um diagnóstico distraído conclui «sem erros no sistema» a partir de um diário que nunca viu.

```bash
sudo usermod -aG systemd-journal $USER     # e voltar a iniciar sessão
```

---

## Sem interface gráfica

```bash
sudo ./cli.sh --cli
```

Escreve o relatório HTML e sai com um código conforme o que encontrou:

| Código | Significado |
| :--- | :--- |
| `0` | Limpo |
| `1` | Problemas não críticos |
| `2` | Problemas críticos |
| `3` | Falta a interface gráfica |
| `4` | Não conseguiu gravar o relatório |
| `130` | Interrompido |

Outras opções úteis:

```bash
./cli.sh --cli --horas 168          # a última semana
./cli.sh --cli --este-arranque      # só desde o último boot
./cli.sh --cli --com-utilizador     # inclui o diário da sessão gráfica
./cli.sh --cli --sem-eventos        # salta o diário; mais rápido
```

Para agendar com um temporizador do systemd, em `/etc/systemd/system/ittoolkit.service`:

```ini
[Service]
Type=oneshot
ExecStart=/caminho/para/Linux/cli.sh --cli
```

E o temporizador correspondente em `ittoolkit.timer`. Um `cron` diário também serve — a ferramenta não depende de nenhum dos dois.

---

## Onde ficam as coisas

Configuração e registo em `$XDG_CONFIG_HOME/ITToolkit`, ou `~/.config/ITToolkit` quando a variável não está definida. Relatórios na pasta configurada, dentro dos Documentos.

Nada é escrito dentro da pasta do programa — os relatórios contêm o inventário e o endereçamento da máquina e não devem acabar num repositório.

---

<sub>Created by Redfox using Claude</sub>
