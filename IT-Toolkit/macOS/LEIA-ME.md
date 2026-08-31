# macOS

**IT Toolkit — arranque em macOS**

Esta pasta é uma versão completa e independente. Não partilha código com as pastas `Windows/` e `Linux/`: lê o diário unificado em vez do registo de eventos, fala com o `launchd` em vez do gestor de serviços, e usa o `diskutil` e o `system_profiler` em vez do WMI.

---

## Como abrir

Duplo clique em **`executar.command`**. Na primeira execução cria o ambiente e instala as dependências.

Se o Finder recusar abrir — acontece quando o repositório foi copiado por uma máquina Windows, que não preserva a permissão de execução:

```bash
chmod +x executar.command cli.sh
```

Na primeira vez, o Gatekeeper pode avisar que o ficheiro foi descarregado da Internet. Botão direito › Abrir autoriza-o de uma vez por todas.

**Não corra a interface gráfica com `sudo`.** Os relatórios ficariam com o dono trocado e o utilizador normal deixaria de conseguir abrir os seus próprios ficheiros. Para o diagnóstico completo, use `sudo ./cli.sh --cli`.

---

## As duas permissões, e porque é que o sudo não chega

Esta é a diferença que mais confunde num diagnóstico de macOS, e a razão de a barra lateral mostrar as duas:

- **root** — sem ele, o `launchctl list` mostra apenas os serviços deste utilizador, e os daemons do sistema ficam por ler.
- **Acesso Total ao Disco** — é uma autorização do TCC, o subsistema de privacidade, e **o `sudo` não a dá**. Sem ela, os relatórios de paragem do sistema — os kernel panics incluídos — e parte do diário ficam invisíveis. E o sistema não devolve erro nenhum ao escondê-los: o comando corre, devolve zero, e mostra menos. É a pior forma de falhar que existe, porque parece sucesso.

A autorização pertence à **aplicação que corre o processo**, não ao Python. Um diagnóstico lançado do Terminal precisa que o Terminal a tenha:

> Definições do Sistema › Privacidade e Segurança › Acesso Total ao Disco › **+** › Terminal

Se agendar isto com um agente do `launchd`, o agente é um processo próprio e tem de ser autorizado separadamente. Se o relatório agendado sair sempre mais limpo do que o que corre à mão, é isto.

---

## Pré-requisitos

| O quê | Como |
| :--- | :--- |
| **macOS** | 11 (Big Sur) ou superior |
| **Python 3.10+** | `brew install python` — ou as Command Line Tools |
| **Tkinter** | `brew install python-tk` |

O Python que vem com o macOS (`/usr/bin/python3`) funciona, mas traz um Tk antigo que desenha janelas desfocadas em ecrãs Retina, e a Apple já anunciou que o vai retirar. O lançador avisa quando é esse que está a ser usado.

Só duas dependências de Python, de propósito: o `log`, o `diskutil`, o `launchctl`, o `system_profiler`, o `scutil` e o `tmutil` fazem parte do macOS e não se instalam.

### Opcional

```bash
brew install smartmontools
```

Dá os atributos SMART detalhados. O estado básico do disco vem do `diskutil` e não precisa dele.

```bash
./executar.command --diagnostico
```

Diz o que está instalado, que permissões existem, e o que falta.

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
./cli.sh --cli --horas 168        # a última semana
./cli.sh --cli --sem-eventos      # salta o diário; é o que mais tempo poupa
./cli.sh --cli --sem-paragens     # não lê os relatórios de paragem
```

**Sobre o tempo:** o `log show` de um Mac com histórico demora dezenas de segundos a minutos, porque o diário unificado regista tudo o que qualquer processo diz. Não é a ferramenta que está bloqueada. O `--sem-eventos` corta essa parte e deixa o resto — discos, rede, serviços e inventário — a responder em segundos.

Para agendar, um agente em `~/Library/LaunchAgents/com.redfox.ittoolkit.plist` com `ProgramArguments` a apontar para o `cli.sh --cli` e um `StartCalendarInterval`. Não esquecer a autorização de Acesso Total ao Disco para o agente.

---

## Onde ficam as coisas

Configuração e registo em `~/Library/Application Support/ITToolkit`, que é a convenção do macOS. Relatórios na pasta configurada, dentro dos Documentos.

Nada é escrito dentro da pasta do programa — os relatórios contêm o número de série da máquina e o seu endereçamento, e não devem acabar num repositório.

---

<sub>Created by Redfox using Claude</sub>
