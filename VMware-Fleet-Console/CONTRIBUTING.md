# Contribuir · Contributing

<sub>Created by Redfox using Claude</sub>

---

## As três versões

Este projecto tem **três aplicações independentes**, uma por sistema. Não são um
programa com ramificações: são três programas que fazem o mesmo trabalho, cada um
com o seu `src/`, os seus `tests/`, o seu `requirements.txt` e o seu lançador.

**O custo, dito à cabeça: uma correcção ao código partilhado tem de ser aplicada
três vezes.**

É uma escolha deliberada. Cada versão lê-se mais simplesmente, não carrega código
que não lhe diz respeito, e o utilizador leva para a máquina dele só o que
precisa. O preço é este, e o comando abaixo é o que impede que ele se torne
silencioso.

### Confirmar que as três não divergiram

```bash
cd VMware-Fleet-Console

# PT: Só três ficheiros podem diferir entre versões.
# EN: Only three files may differ between versions.
diff -rq --exclude='__pycache__' --exclude='.venv' \
     --exclude='.pytest_cache' --exclude='.ruff_cache' \
     Linux/src Windows/src
diff -rq --exclude='__pycache__' --exclude='.venv' \
     --exclude='.pytest_cache' --exclude='.ruff_cache' \
     Linux/src macOS/src
```

A saída **só** pode conter:

| Ficheiro | Porque difere |
| :--- | :--- |
| `src/vfc/platform_support.py` | é o módulo específico do sistema |
| `src/vfc/__init__.py` | uma linha da docstring diz qual é a versão |

Qualquer outra linha na saída é uma divergência a corrigir. E o mesmo para os
testes, onde só `tests/test_platform_support.py` pode diferir:

```bash
diff -rq --exclude='__pycache__' --exclude='.pytest_cache' \
     Linux/tests Windows/tests
diff -rq --exclude='__pycache__' --exclude='.pytest_cache' \
     Linux/tests macOS/tests
```

### E dentro de cada versão, nenhuma ramificação

Cada versão tem um teste — `TestSemRamificacaoPorSistema` — que percorre o
`src/vfc/` inteiro e falha se encontrar um `sys.platform`, um
`platform.system()` ou um `os.name ==`.

Uma versão que ramifica por sistema operativo é o princípio de voltar a ter um
programa só com ramificações, que é exactamente o que as três pastas existem para
evitar.

---

## Correr os testes

Em cada versão, a partir da pasta dela:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

python -m pytest                 # 235 / 225 / 231, conforme a versão
python -m ruff check .
python -m mypy src               # opcional
```

**Nenhum teste precisa de um vCenter.** O parque de testes é inventado no
`tests/conftest.py`, com um exemplar de cada coisa que costuma correr mal num
sítio real: um anfitrião sem resposta, um datastore quase cheio, uma máquina com
um snapshot esquecido há oito meses, uma máquina sem Tools, um template, e uma
máquina cujo anfitrião caiu.

Um teste que dependesse de um servidor VMware ligado seria um teste que ninguém
correria — e a suite existe precisamente para se poder mexer nas guardas sem
medo.

---

## Onde pôr o quê

O ficheiro decide o que pode fazer:

| Módulo | Pode tocar na rede? | O que lá vive |
| :--- | :---: | :--- |
| `models.py` | **não** | os objectos, e a formatação de grandezas |
| `health.py` | **não** | as regras — recebem modelos, devolvem achados |
| `actions.py` (`guard_*`) | **não** | as decisões sobre operações |
| `actions.py` (`Operations`) | sim | a execução, que verifica a guarda outra vez |
| `collect.py` (`map_*`) | **não** | a tradução do vSphere para os modelos |
| `collect.py` (`collect_fleet`) | sim | a recolha |
| `connection.py` | sim | a ligação e o certificado |
| `cli.py` | **não** | a formatação em texto e JSON |
| `tui/` | — | **o único sítio que importa Textual** |

Esta separação não é arrumação: é o que torna quase tudo testável. Uma regra nova
que precise de fazer uma chamada ao vCenter está na camada errada — o que ela
precisa deve ser lido em `collect.py` e guardado num modelo.

---

## Regras que não se negoceiam

**1. Nenhuma senha vai para disco.** Não há campo, não há opção, não há
"lembrar-me". Há testes que falham se alguém acrescentar um campo de senha às
estruturas que são serializadas.

**2. Nenhuma operação destrutiva passa sem confirmação escrita.** O teste
`test_todas_as_destrutivas_exigem_confirmacao` percorre o enum `Action` e falha
se alguém acrescentar uma operação destrutiva sem guarda. Acrescentar a operação
sem a guarda parte a suite — de propósito.

**3. A verificação do certificado não se desliga.** Não há flag `--inseguro`. Se
o certificado não valida, mostra-se a impressão digital e espera-se por uma
decisão. Ver `connection.py`.

**4. O modo de texto não escreve no vSphere.** Há um teste que falha se aparecer
uma opção de operação na linha de comandos.

---

## Estilo

- **Bilingue.** Cada módulo, classe e função pública documentados em PT-PT e
  EN-UK. Os comentários explicam **porquê**, não o quê — o código já diz o quê.
- **Português nos identificadores internos**, inglês nas APIs públicas dos
  modelos (é o que os torna legíveis a quem vem do vSphere).
- `ruff` com `line-length = 100`. O `E501` está desligado porque os comentários
  bilingues são naturalmente longos e cortar frases a meio torná-los-ia
  ilegíveis.
- Um valor por omissão **nunca** substitui "não sei" por zero. Um datastore sem
  números não está vazio; uma máquina desligada não tem zero segundos de uptime.

---

## Antes de abrir um pull request

```bash
# PT: nas três versões
# EN: in all three versions
for v in Windows Linux macOS; do
  (cd "$v" && python -m ruff check . && python -m pytest -q) || echo "FALHOU: $v"
done
```

E o `diff` das três, lá em cima.
