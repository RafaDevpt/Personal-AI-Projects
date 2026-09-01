# Contribuir · Contributing

**PT** · Obrigado pelo interesse. Este documento descreve como propor alterações.
**EN** · Thank you for your interest. This document describes how to propose changes.

---

## A regra que define este projecto

**Há três versões independentes — `Windows/`, `Linux/` e `macOS/` — e cada uma é
um programa completo.**

Aqui a separação vai mais longe do que nos projectos irmãos deste repositório,
porque nem sequer partilham a linguagem: a de Windows é PowerShell, as outras
duas são `bash`. O que partilham é a estrutura, os nomes dos módulos, o
comportamento e — este sim, palavra a palavra — o catálogo.

### O que é partilhado e o que não é

| Ficheiro | Igual nas três? |
| :--- | :--- |
| `src/catalogo.json` | **Sim, byte a byte.** É o único ficheiro que tem de coincidir |
| `seguranca`, `catalogo`, `hardware`, `hipervisor` | **Não.** São o sistema operativo |
| `recomendacao` | Não, mas **tem de dar os mesmos números** — ver abaixo |
| Testes | **Não.** Cada um testa o seu sistema |
| `LEIA-ME.md` e lançadores | **Não.** São instruções de sistemas diferentes |

```bash
diff Windows/src/catalogo.json Linux/src/catalogo.json
diff Windows/src/catalogo.json macOS/src/catalogo.json
```

Se algum destes devolver alguma coisa, as versões divergiram no único ficheiro
que não pode divergir. Uma imagem que exista numa versão e não noutra é uma
armadilha para quem mudar de máquina.

### A recomendação tem de dar os mesmos números

O cálculo está escrito três vezes — em PowerShell com GB decimais, e em `bash`
com MB inteiros, porque a shell não tem vírgula flutuante. **As duas formas têm
de chegar ao mesmo sítio.** Um Ubuntu Desktop num anfitrião de 16 GB com 8
núcleos dá 2 núcleos virtuais e 8 GB nas três versões, e há um teste em cada uma
que o fixa.

Se mudar a regra numa, mude nas três e actualize os três testes. Um utilizador
que crie a mesma máquina em dois sistemas e receba conselhos diferentes deixa de
confiar em qualquer um deles.

---

## Antes de tudo · Before anything else

> **PT** · **Nunca** acrescente ao catálogo um endereço que não tenha confirmado
> na página oficial do projecto, nessa altura, com o seu próprio navegador. Este
> ficheiro decide de onde é que o programa descarrega imagens de sistema
> operativo, e uma entrada errada é a diferença entre um laboratório e uma
> máquina comprometida.
>
> **Nunca** copie uma impressão digital GPG de um artigo, de um fórum ou de uma
> resposta de um modelo de linguagem — incluindo esta. Vá à página do projecto.
>
> **EN** · **Never** add an address to the catalogue you have not confirmed on
> the project's official page, at that moment, in your own browser. This file
> decides where the program downloads operating system images from.
>
> **Never** copy a GPG fingerprint from an article, a forum or a language
> model's answer — this one included. Go to the project's page.

---

## Ambiente · Environment

Não há nada a instalar para desenvolver. É essa a intenção.

```bash
# Linux e macOS
bash tests/executar-testes.sh
bash -n src/laboratorio-virtual.sh src/lib/*.sh    # sintaxe
shellcheck src/laboratorio-virtual.sh src/lib/*.sh # se o tiver
```

```powershell
# Windows
.\tests\Executar-Testes.ps1
```

O arranque de testes é próprio e tem quarenta linhas. Não usa Pester nem
`bats` — não por serem maus, mas porque um projecto que se descreve como «uma
pasta e um lançador» não pode começar por pedir que se instale um arranque de
testes.

---

## Duas regras que não se negoceiam

### 1. Nenhum teste toca na rede

A suite tem de correr numa máquina sem Internet, num runner de integração
contínua, e em menos de um segundo. Tudo o que descarrega está atrás de uma
fronteira que os testes não atravessam; o que se testa é o que **decide** — se
um domínio passa, se um manifesto é lido como deve, se a soma confere.

Um teste que precisasse de descarregar três gigabytes não corria na integração
contínua e, por isso, não corria nunca.

### 2. Nenhuma camada de verificação tem interruptor

Não há `--sem-verificar`, não há `--forcar`, não há `-k` no `curl`. Se aparecer
um pedido para acrescentar um, a resposta é não, e a razão é esta: uma opção que
desliga a verificação existe para ser usada no dia em que a verificação falha —
que é exactamente o dia em que ela está a fazer o seu trabalho.

O que **há** é o programa dizer sempre que camadas correram. Uma camada que não
correu aparece na lista com `[--]`, e não é omitida.

---

## Acrescentar uma imagem ao catálogo

Uma entrada nova é um objecto em `src/catalogo.json`, e tem de ser copiada para
as três versões.

```json
{
  "id": "exemplo-1.0",
  "nome": "Exemplo 1.0",
  "familia": "linux",
  "arquitectura": "x86_64",
  "tipo": "iso",
  "pagina_oficial": "https://exemplo.org/download",
  "directorio": "https://cdimage.exemplo.org/1.0/",
  "manifesto": "SHA256SUMS",
  "assinatura": "SHA256SUMS.gpg",
  "chave_gpg": "0000000000000000000000000000000000000000",
  "chave_url": "https://exemplo.org/chave.asc",
  "padrao_ficheiro": "exemplo-[0-9.]+-amd64\\.iso$",
  "minimo":      { "cpu": 1, "ram_gb": 2, "disco_gb": 10 },
  "recomendado": { "cpu": 2, "ram_gb": 4, "disco_gb": 20 },
  "notas_pt": "Uma frase que ajude a escolher entre esta e as outras."
}
```

Regras da casa:

| Regra | Porquê |
|---|---|
| O `directorio` e a `chave_url` têm de estar em `dominios_confiaveis` | É a lista curta, a de onde se descarrega. A validação recusa o catálogo se não estiverem |
| A `pagina_oficial` vai na lista das páginas | Só é mostrada e aberta no navegador. Misturá-la com a outra triplicava a lista de descarregamento |
| Nunca fixe um nome de ficheiro | O nome sai do manifesto. Um nome fixado fica desactualizado à primeira versão menor |
| O `padrao_ficheiro` tem de apanhar **um** ficheiro | Se apanhar dois, o programa fica com o primeiro, e o primeiro pode não ser o que quer |
| `chave_gpg` só com uma impressão digital que **confirmou** | Ver a caixa no topo. Uma impressão errada faz o programa recusar uma imagem legítima; uma impressão de uma chave errada é pior |
| Sem manifesto, use `"tipo": "guiado"` | Este programa não descarrega o que não consegue verificar. A validação impede-o |

E corra os testes: há um em cada versão que percorre o catálogo à procura de
entradas sem manifesto, com domínios fora da lista, em HTTP, ou com uma
impressão digital que não é uma impressão digital.

---

## Acrescentar um hipervisor

1. Uma função `estado_<nome>` que diga se está utilizável, e **porque não**, se
   não estiver. Devolver só «não» obriga o utilizador a adivinhar
2. Uma função `criar_maquina_<nome>` que recuse criar por cima de uma máquina
   existente. Este programa não substitui nada
3. Rede em NAT por omissão. Uma máquina de laboratório com um serviço mal
   configurado não deve estar exposta à rede da empresa
4. A máquina não arranca sozinha com o anfitrião
5. Um teste para a tradução do identificador do catálogo para o vocabulário do
   hipervisor — é onde se erra, e o erro dá uma máquina que arranca com metade
   das definições erradas

---

## Estilo · Style

- **Comentários e docstrings em PT-PT e EN-UK**, nesta ordem
- Comentar o **porquê**, não o **quê**. `# converte para inteiro` não acrescenta
  nada; `# o nproc conta fios e não núcleos` sim
- **PowerShell**: `Set-StrictMode -Version Latest`, verbos aprovados,
  ficheiros em **UTF-8 com BOM** — sem o BOM, o Windows PowerShell 5.1 lê o
  ficheiro como ANSI e os acentos partem a sintaxe
- **bash**: `set -euo pipefail` nos executáveis, aspas em todas as expansões,
  nunca `eval` sobre entrada de fora
- **macOS**: escrito para o **bash 3.2**. Sem `mapfile`, sem arrays
  associativos, sem `${var^^}`, sem `sha256sum`
- Linhas até 100 caracteres

---

## O que não vai ser aceite

- **Uma opção que desligue a verificação.** Ver acima
- **Um endereço `http://`** em qualquer lado do catálogo
- **Um nome de ficheiro fixado** em vez de vindo do manifesto
- **Seguir redireccionamentos sem os verificar.** O `-L` do `curl` e o
  comportamento normal do `Invoke-WebRequest` anulam a lista de domínios por
  completo, e é por isso que os saltos são seguidos à mão
- **Descarregar uma imagem de Windows ou macOS contornando o formulário do
  fabricante.** É o que separa esta ferramenta das que não se devem usar
- **Uma imagem de macOS de um sítio que não seja a Apple**, com qualquer
  justificação

---

<sub>Created by Redfox using Claude</sub>
