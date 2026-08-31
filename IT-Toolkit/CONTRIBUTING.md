# Contribuir · Contributing

**PT** · Obrigado pelo interesse. Este documento descreve como propor
alterações.
**EN** · Thank you for your interest. This document describes how to propose
changes.

---

## Só há uma versão, e a razão está nas pastas vazias

A aplicação vive em `Windows/`. As pastas `Linux/` e `macOS/` existem e não têm
código: levam a explicação de porque é que esta ferramenta não corre lá.

Não é falta de porte. Ela lê registos de eventos por `wevtutil`, inventário por
WMI, serviços por `sc` e PowerShell, e SMART por `wmic`. Portar isto não seria
portar — seria escrever outra aplicação que faz o mesmo trabalho noutro sistema,
partilhando pouco mais do que a interface e a estrutura dos relatórios.

Se um dia fizer sentido, o caminho é um projecto próprio, e não uma quarta
ramificação dentro deste.

---

## Antes de tudo · Before anything else

> **PT** · **Nunca** inclua relatórios gerados, nomes de máquina, endereços IP
> reais, números de série, nomes de utilizador ou capturas de ecrã com o
> ambiente visível num commit, issue ou pull request. Um relatório desta
> ferramenta é um retrato completo de uma máquina interna. Ao reportar um
> problema, substitua os endereços por `10.0.0.x`, os nomes de máquina por
> `PC-EXEMPLO` e apague as mensagens de erro que contenham caminhos de rede.
>
> **EN** · **Never** include generated reports, machine names, real IP
> addresses, serial numbers, user names or screenshots showing the environment
> in a commit, issue or pull request. A report from this tool is a complete
> portrait of an internal machine.

---

## Ambiente · Environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

```bash
pytest                            # testes
pytest --cov=ittoolkit            # com cobertura
ruff check src/ tests/            # análise estática
```

**PT** · Os testes correm em qualquer sistema operativo, de propósito.

---

## Testes · Tests

**PT** · Duas regras inegociáveis.

**Nenhum teste toca no Windows.** As respostas do PowerShell são fixtures —
dicionários com a forma que o `ConvertTo-Json` produz. Se precisar de uma
resposta nova, acrescente a fixture; não vá buscá-la a uma máquina real durante
a execução dos testes. É por isso que o módulo `events` está partido em duas
metades: `ler_log` toca no Windows, `analisar` só vê dicionários.

**O `customtkinter` não é instalado na integração contínua.** A lógica de
recolha e de relatórios tem de continuar a funcionar sem interface gráfica — é
disso que o modo `--cli` depende. Se um módulo fora de `gui/` passar a importar
`customtkinter`, a CI parte, e é para isso que lá está.

---

## Estilo de código · Code style

- **Comentários e docstrings em PT-PT e EN-UK**, nesta ordem. É a convenção do
  projeto e aplica-se a todo o código novo.
- Comentar o **porquê**, não o **quê**. `# converte para inteiro` não acrescenta
  nada; `# o Id vem como string em algumas versões do PowerShell` sim.
- Type hints em todas as funções públicas.
- `pathlib.Path` em vez de `os.path`.
- Exceções específicas. Nunca `except:` nu.
- `logging`, nunca `print()` — excepto na saída do modo `--cli`.
- Linhas até 100 caracteres.

---

## Acrescentar uma regra à base · Adding a knowledge-base rule

**PT** · O ficheiro `src/ittoolkit/knowledge.py` contém apenas dados. Uma regra
nova é uma entrada na lista `REGRAS`:

```python
Regra(
    event_id=1234,
    providers=("nome-do-provider",),      # obrigatório, em minúsculas
    titulo="Frase curta que descreve o evento",
    causa="Porque é que isto acontece, em linguagem de operador.",
    solucao="O que verificar, por ordem de probabilidade.",
    gravidade=Gravidade.ALTA,
    ruido=False,                          # True para ruído conhecido do Windows
)
```

Regras da casa:

| Regra | Porquê |
|---|---|
| O `providers` nunca fica vazio | Um Event ID sozinho não identifica nada. |
| A `solucao` diz o que **verificar**, não o que fazer | A decisão é sempre do operador; esta ferramenta não repara nada sozinha. |
| Ordene as causas por probabilidade | Quem lê o relatório às três da manhã segue a primeira linha. |
| `ruido=True` para o que o Windows produz sem haver problema | Sem isso, o relatório perde credibilidade e o operador aprende a ignorá-lo. |
| `CRITICA` só para perda de dados, avaria de hardware ou compromisso de segurança | Se tudo for crítico, nada é. |

**PT** · Há um teste que percorre a base inteira à procura de entradas sem
causa, sem solução, sem provider ou com pares duplicados. Corra o `pytest`
antes de submeter.

---

## Acrescentar uma verificação · Adding a check

**PT** · Uma verificação nova devolve `Achado`, não texto. Assim entra no
relatório, na contagem por gravidade e nos códigos de saída do `--cli` sem ter
de mexer em mais nada:

```python
Achado(
    modulo="Discos",
    titulo="Frase curta",
    detalhe="Os números concretos.",
    gravidade=Gravidade.ALTA,
    solucao="O que verificar.",
)
```

**PT** · Se a verificação depender de Windows, trate a ausência dele
devolvendo lista vazia — não levante excepção. O `_recolher` apanha excepções
para que um módulo partido não derrube os outros, mas contar com isso é
desleixo.

---

## Pull requests

1. Ramo a partir de `main`: `git checkout -b feat/descricao-curta`
2. Testes a passar e um teste novo por cada correcção de bug
3. Commits no formato [Conventional Commits](https://www.conventionalcommits.org/):
   `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
4. Actualize o `CHANGELOG.md` na secção *Unreleased*
5. Descreva **o problema** que resolve, não apenas o que alterou

---

## Reportar problemas · Reporting issues

Inclua: versão do Windows, versão do Python, se correu com ou sem elevação, o
que esperava, o que aconteceu, e as linhas relevantes do registo (`--verbose`)
**depois de substituir nomes de máquina e endereços reais**.

---

*Created by Redfox using Claude*
