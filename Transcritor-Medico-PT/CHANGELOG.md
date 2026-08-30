# Changelog

**PT** · Todas as alterações relevantes deste projeto.
**EN** · All notable changes to this project.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento segundo [SemVer](https://semver.org/lang/pt-BR/).

---

## [4.0.1] — 2026-08-30

**PT** · Correcções, saneamento e integração contínua.
**EN** · Fixes, sanitisation and continuous integration.

### Infra-estrutura · Infrastructure

- `.gitignore` — o repositório não tinha nenhum. Impede que `config.json`,
  relatórios gerados, `.venv/` e `__pycache__/` cheguem a ser versionados
- Integração contínua em GitHub Actions: `ruff` e `pytest` em `windows-latest`
  a cada `push` e cada `pull request` sobre este branch
- Árvore limpa de avisos do `ruff` sob a configuração que o projecto já
  declarava em `pyproject.toml`, que até aqui não passava

### Corrigido · Fixed

- `medical_terms.py` — a validação da ordem das expressões de pontuação passa a
  usar `itertools.pairwise`, que diz o que faz, em vez de `zip(l, l[1:])`
- `corrections.py` — o `zip()` sobre os blocos alinhados declara `strict=True`.
  A guarda acima já garante comprimentos iguais; agora essa garantia está
  escrita no código
- `gui/dialogs.py` — a reposição do cursor após substituição passa a
  `contextlib.suppress`, com a razão documentada: perder a posição do cursor é
  aceitável, rebentar com a caixa de texto não é

### Adicionado · Added

- `CLI.bat` — lançador de linha de comandos, para transcrever lotes de
  gravações sem abrir a interface gráfica

---

## [4.0.0] — 2026-08-27

**PT** · Reescrita completa. Versão anterior (3.0 Premium) descontinuada.
**EN** · Complete rewrite. The previous version (3.0 Premium) is discontinued.

### Adicionado · Added

- Interface CustomTkinter com tema claro/escuro e paleta de baixa saturação
- Localizar e substituir no editor (`Ctrl+F`), com substituição em bloco
  anulável num só `Ctrl+Z`
- Janela de gestão das correções aprendidas, com remoção individual de regras
- Modo lote via `--batch`, para transcrever pastas sem interface
- Escrita incremental: o texto aparece no editor à medida que é transcrito
- Cabeçalho de proveniência nos `.txt` (modelo, duração, idioma, data)
- Exportação para Markdown com metadados YAML
- Registo rotativo em ficheiro, com garantia de não conter texto clínico
- Deteção automática de GPU CUDA com recuo silencioso para CPU
- Cancelamento de transcrição em curso
- Aviso ao fechar ou mudar de ficheiro com texto por exportar
- 30 testes automatizados

### Alterado · Changed

- **Motor**: `openai-whisper` → `faster-whisper`. Cerca de 4× mais rápido em
  CPU, aproximadamente metade da memória, e dispensa o PyTorch (menos ~2,5 GB
  de instalação)
- **Vocabulário clínico**: agora entregue ao modelo como contexto inicial,
  corrigindo à cabeça em vez de remendar com regex depois
- **Dicionário**: uma única expressão regular compilada substitui uma passagem
  por termo; ordenação por comprimento para os termos compostos ganharem
- **Aprendizagem**: `difflib` substitui a comparação posicional, funcionando
  quando o utilizador acrescenta ou remove palavras
- **Capitalização**: normalização por frase, com lista de abreviaturas, em vez
  de acrescentar um ponto no fim do texto
- **Caminhos**: configuráveis e persistidos, em vez do `A:\` fixo no código
- **Codificação**: `.txt` gravado em UTF-8 com BOM e quebras de linha Windows,
  para o Bloco de Notas mostrar os acentos corretamente

### Corrigido · Fixed

- Erros ortográficos no próprio dicionário: `ultrasssom` → `ultrassom`,
  `biópia` → `biópsia`
- Substituições destruíam a maiúscula inicial da frase
- `except:` nu no carregamento de configuração engolia `KeyboardInterrupt`
- Cerca de 150 entradas do tipo `"paciente" → "paciente"`, sem efeito, que
  custavam uma passagem de regex cada
- Transcrição bloqueava a interface por não correr em fio separado
- Ficheiro de saída existente era sobreposto em silêncio
- Botões de formatação do editor sem efeito no ficheiro exportado (removidos)

### Removido · Removed

- `openai-whisper` e a dependência de PyTorch
- Formatação a negrito/itálico no editor (não sobrevive ao `.txt`)
- Caminho fixo para a unidade `A:`
- Ficheiros `.bat` de diagnóstico dispersos, substituídos por `--verbose`

### Segurança · Security

- `.gitignore` bloqueia áudios, transcrições, correções aprendidas e registos
- Registo nunca escreve texto transcrito, apenas contagens
- Configuração gravada em `%APPDATA%`, fora da árvore do repositório

---

## [3.0.0] — 2025-12-06

**PT** · Versão anterior, baseada em `openai-whisper`. Não mantida.
**EN** · Previous version, based on `openai-whisper`. Not maintained.

---

*Created by Redfox using Claude*
