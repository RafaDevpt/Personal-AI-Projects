# Contribuir · Contributing

**PT** · Obrigado pelo interesse. Este documento descreve como propor
alterações.
**EN** · Thank you for your interest.

---

## Antes de tudo · Before anything else

> **PT** · **Nunca** inclua documentos reais, propostas de fornecedores,
> formulários preenchidos, preços, nomes de empresas, contactos ou capturas de
> ecrã com conteúdo verdadeiro num commit, issue ou pull request.
>
> Uma proposta comercial é um documento de negociação. Um formulário preenchido
> tem dados pessoais. Ao reportar um problema, use os ficheiros do
> `tools/gerar_exemplos.py` — foram feitos precisamente para isso — ou construa
> um caso mínimo com valores inventados.
>
> **EN** · **Never** include real documents, vendor quotes, completed forms,
> prices, company names, contacts or screenshots with real content. Use the
> files from `tools/gerar_exemplos.py` instead — they exist for this.

---

## Ambiente · Environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

python tools/gerar_exemplos.py exemplos
```

```bash
pytest                            # testes
pytest --cov=pdfsuite             # com cobertura
ruff check src/ tests/ tools/     # análise estática
```

---

## Testes · Tests

**PT** · Duas regras inegociáveis.

**Nenhum teste usa documentos reais.** Os PDF de teste são construídos com o
`reportlab` dentro do próprio teste, num `tmp_path`. Um ficheiro de exemplo no
repositório seria um ficheiro binário que ninguém revê e que mais cedo ou mais
tarde alguém substituiria por um documento verdadeiro «só para testar».

**O `customtkinter` não é instalado na integração contínua.** A leitura, a
detecção, a escrita do AcroForm, a pontuação e os relatórios têm de continuar a
funcionar sem interface gráfica — é disso que a linha de comandos depende. Se
um módulo fora de `gui/` passar a importar `customtkinter`, a CI parte, e é para
isso que lá está.

**PT** · Há ainda um job de CI que gera os exemplos e corre o fluxo completo.
Existe porque um AcroForm mal formado não levanta excepção nenhuma ao ser
escrito — só não funciona quando alguém o abre, que já é tarde.

---

## Estilo de código · Code style

- **Comentários e docstrings em PT-PT e EN-UK**, nesta ordem.
- Comentar o **porquê**, não o **quê**. `# converte para float` não acrescenta
  nada; `# 1.234 é ambíguo entre PT e EN e nada no número os distingue` sim.
- Type hints em todas as funções públicas.
- `pathlib.Path` em vez de `os.path`.
- Exceções específicas. Nunca `except:` nu.
- `logging`, nunca `print()` — excepto na saída da linha de comandos.
- Linhas até 100 caracteres.

---

## As coordenadas · Coordinates

**PT** · Vale a pena ler isto antes de mexer em `detect.py`, `forms.py` ou
`gui/editor.py`.

São três convenções em jogo:

| Onde | Origem | Cresce |
|---|---|---|
| pdfplumber | canto superior esquerdo | para baixo |
| PDF e AcroForm | canto inferior esquerdo | para cima |
| Tela do editor | canto superior esquerdo | para baixo |

**PT** · A conversão acontece em exactamente três sítios: no detector, quando
lê do pdfplumber; e em `_para_tela` e `_para_pdf`, no editor. Em mais lado
nenhum. Misturar as convenções é o erro clássico deste tipo de ferramenta e
produz campos correctos na horizontal e invertidos na vertical — o que é
suficientemente estranho para levar horas a diagnosticar.

---

## Acrescentar um padrão de extracção · Adding an extraction pattern

**PT** · Um fornecedor escreve as condições de uma maneira que a aplicação não
apanha. Em `analyse.py`:

1. Acrescente o marcador à lista da função respectiva
2. Escreva um teste em `tests/test_analyse_scoring.py` com um texto mínimo
3. Confirme que os testes existentes continuam a passar

**PT** · Regras da casa para esta zona do código:

| Regra | Porquê |
|---|---|
| Guarde sempre o contexto no `Valor` | Sem a frase original, quem duvidar do número tem de abrir o PDF e procurar à mão — que é o trabalho que a ferramenta devia poupar |
| Um valor não encontrado é `None`, nunca zero | «Não diz» e «zero» são informações diferentes, e confundi-las inverte comparações |
| Confiança baixa quando o formato é ambíguo | É o que a interface usa para pedir confirmação |
| Converta para a unidade comum na extracção | «3 anos» tem de sair em meses, senão perde para «24 meses» |

---

## Acrescentar um critério à comparação · Adding a criterion

1. Acrescente um `Criterio` a `CRITERIOS_OMISSAO` em `scoring.py`
2. Acrescente o ramo correspondente em `valor_do_criterio`
3. Acrescente a extracção em `analyse.py` e o campo em `Proposta`
4. O relatório HTML e o Excel apanham-no sozinhos — as colunas são geradas a
   partir da lista de critérios

**PT** · O `maior_melhor` é o único sítio onde se diz se mais é melhor. Errá-lo
inverte silenciosamente aquele critério inteiro, e um teste com dois valores
diferentes apanha isso de imediato.

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

Inclua: sistema operativo, versão do Python, o que esperava, o que aconteceu, e
as linhas relevantes do registo (`--verbose`).

Se for um problema de extracção, **descreva o formato da linha, não o
conteúdo**: «o total estava numa linha a dizer `Valor global da adjudicação` e
o valor vinha na linha seguinte» é útil e não revela nada. Colar a proposta
não é nem uma coisa nem outra.

---

*Created by Redfox using Claude*
