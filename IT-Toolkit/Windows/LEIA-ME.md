# Windows

**IT Toolkit — arranque em Windows**

Esta pasta é uma versão completa e independente. Não partilha código com as pastas `Linux/` e `macOS/`: lê os event logs por `wevtutil`, o inventário por WMI, os serviços pelo PowerShell e o SMART pelo `Get-PhysicalDisk`. As outras duas fazem o mesmo trabalho com as ferramentas dos sistemas delas.

---

## Como abrir

Duplo clique em **`EXECUTAR.bat`**. Na primeira execução pede elevação, cria o ambiente e instala as dependências.

A elevação é pedida porque sem ela o registo de Segurança fica ilegível, o SMART não devolve nada e os serviços não arrancam. A aplicação abre na mesma sem ela e diz o que não vai conseguir fazer.

---

## Pré-requisitos

| O quê | Como |
| :--- | :--- |
| **Windows** | 10 ou 11 |
| **Python 3.10+** | [python.org/downloads](https://www.python.org/downloads/) — marque **Add Python to PATH** |

Só duas dependências de Python, de propósito: tudo o resto assenta na biblioteca padrão e nas ferramentas que já vêm no Windows, porque esta ferramenta corre em máquinas de domínio onde instalar pacotes é lento ou está bloqueado por política.

---

## Sem interface gráfica

```
VERIFICAR.bat
```

Escreve o relatório HTML e sai com um código conforme o que encontrou:

| Código | Significado |
| :--- | :--- |
| `0` | Limpo |
| `1` | Problemas não críticos |
| `2` | Problemas críticos |
| `4` | Não conseguiu gravar o relatório |

Para agendar: Agendador de Tarefas → Criar Tarefa → **Executar com privilégios mais elevados** → Acção «Iniciar um programa» → este ficheiro.

---

## Onde ficam as coisas

Configuração e registo em `%APPDATA%\ITToolkit`. Relatórios na pasta configurada, dentro dos Documentos. Nada é escrito dentro da pasta do programa — os relatórios contêm dados da máquina e não devem acabar num repositório.

---

<sub>Created by Redfox using Claude</sub>
