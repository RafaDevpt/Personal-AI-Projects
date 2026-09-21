# Revisão de segurança — 2026-09-21/22

**PT-PT:** Revisão dos nove projectos, com correcções aplicadas. Cada achado foi
confirmado a ler o código; nenhuma correcção foi feita a partir do que um modelo
disse, conforme combinado.

**EN-UK:** Review of all nine projects, with fixes applied. Every finding was
confirmed by reading the code; no fix was driven by a model's verdict, as agreed.

---

## Como rever / How to review

Uma branch por projecto, todas já enviadas. Nenhum PR aberto.

| Projecto | Branch | Repo |
|---|---|---|
| Projecto-de-escola | `security-fixes` | `Projecto-de-escola` |
| VMware-Fleet-Console | `security-fixes/VMware-Fleet-Console` | `Personal-AI-Projects` |
| Printer-Remote-Toner-Monitor | `security-fixes/Printer-Remote-Toner-Monitor` | `Personal-AI-Projects` |
| Network-Config-Builder | `security-fixes/Network-Config-Builder` | `Personal-AI-Projects` |
| Network-Topology-Mapper | `security-fixes/Network-Topology-Mapper` | `Personal-AI-Projects` |
| Medical-Audio-to-Text | `security-fixes/Medical-Audio-to-Text` | `Personal-AI-Projects` |
| Virtual-Lab-Builder | `security-fixes/Virtual-Lab-Builder` | `Personal-AI-Projects` |

---

## O mais grave / The most serious

### 1. Execução remota de código — `Projecto-de-escola`

Os dois tratadores de envio de imagem aceitavam qualquer ficheiro:

- o tipo era lido de `$_FILES[...]['type']`, que vem do cabeçalho enviado pelo
  cliente e é trivial de forjar;
- o nome do ficheiro era usado tal e qual, sem validação de extensão;
- `$pasta_imagens` nunca foi definida, pelo que o destino saía no directório do
  site.

Enviar `evil.php` com `Content-Type: image/jpeg` escrevia PHP dentro do site,
bastando depois pedi-lo pelo browser. **Sem autenticação nenhuma** — nem sequer
havia verificação de sessão nessas páginas.

Agora o tipo é decidido pelo conteúdo com `getimagesize()` e o nome no disco é
gerado localmente: nada do que o cliente escreve chega ao sistema de ficheiros.

### 2. Autenticação decorativa — `Projecto-de-escola`

`processa_login.php`, que é o destino do formulário de `index.php`, **nunca
iniciava sessão**. Em caso de sucesso fazia apenas `header()` para
`menu_admin.php`. Como `menu_admin.php` era HTML puro sem qualquer verificação,
o painel de administração estava acessível a quem escrevesse o URL.

Havia ainda contorno por injecção de SQL no mesmo ficheiro, e qualquer conta
autenticada era encaminhada para o painel de administração independentemente do
nível — um utilizador registado pelo formulário público recebia o menu de admin.

### 3. TOCTOU no certificado — `VMware-Fleet-Console`

A impressão digital era comparada em `evaluate_trust()`, que abre uma ligação
para ir buscar o certificado. Depois `connect()` abria **outra** ligação, e era
nessa que a senha seguia — com `CERT_NONE`. Entre uma e outra não se verificava
nada.

O módulo inteiro existe para fechar essa janela, e o docstring afirmava que a
identidade "já tinha sido estabelecida" — tinha, noutra ligação.

Agora o certificado aceite é entregue ao OpenSSL como única âncora de confiança,
com `CERT_REQUIRED`, pelo que a verificação acontece **durante** o aperto de mão.

**Verificado** com dois certificados auto-assinados e um servidor TLS local, a
simular a troca exacta:

| | resultado |
|---|---|
| comportamento antigo (`CERT_NONE`) | aperto de mão **aceite** contra o certificado do atacante |
| comportamento novo | aperto de mão **recusado** |
| contra o servidor legítimo | continua a ligar, sem regressão |

### 4. Palavra-passe da impressora em claro — `Printer-Remote-Toner-Monitor`

O gestor de credenciais prende-se ao *opener*, não a um esquema, e o recurso
entre protocolos era incondicional. Quando o `https` falhava, a tentativa
seguinte saía em **`http`** com o mesmo `HTTPBasicAuthHandler` atrás — e o Basic
responde ao desafio 401 com utilizador e palavra-passe em base64, que não é
cifra nenhuma.

Bastava a impressora recusar o `https` naquele instante.

### 5. Filtro de segredos com fuga — `Network-Config-Builder` e `Network-Topology-Mapper`

O módulo diz que o filtro de segredos "é a parte que não pode ser esquecida".
Estava, em **metade** dos casos reais:

| linha | antes | |
|---|---|---|
| `enable secret 5 $1$mERr$Xk3lQ...` | `enable secret *** $1$mERr$Xk3lQ...` | resumo vai para o registo |
| `username admin password 7 0822455D...` | `password *** 0822455D...` | tipo 7 é **reversível** |
| `password: hunter2` | `password: hunter2` | separador não apanhado |
| `password=hunter2` | `password=hunter2` | idem |

O padrão apanhava o algarismo do tipo de cifra e substituía-o, deixando o
segredo escrito. Os testes existentes só cobriam a forma simples — é por isso
que sobreviveu. Acrescentados oito casos de regressão.

O mesmo defeito existia nos dois projectos. No Topology-Mapper conta ainda mais,
porque lida com comunidades SNMP e com a palavra-passe do UniFi.

### 6. Dados de saúde legíveis por outras contas — `Medical-Audio-to-Text`

O programa faz bem a parte difícil: a transcrição é local e **confirmou-se que
não há saída para rede nenhuma**. O que faltava era o passo pequeno — os
ficheiros eram criados com a máscara por omissão, tipicamente `0644`.

Abrange a transcrição, a gravação áudio da consulta, e o dicionário de
correcções, que acumula nomes vindos das consultas. Tudo isso é dado de saúde.

Agora `0600` nos ficheiros e `0700` nas pastas criadas. **Verificado**: exportar
para uma árvore nova não deixa nenhum caminho legível por grupo ou outros.

---

## Resto das correcções / Remaining fixes

- **Injecção de SQL** em `registar_utilizador.php` (registo **público**),
  `processar_registo.php`, `adicionar_categoria.php`, `artigos_categoria.php`,
  `comprar.php`, `atualizar_compra.php`.
- **Credenciais de root em código** em `ver_utilizador.php`
  (`mysql_connect('localhost','root','')`), num ficheiro que listava todos os
  clientes sem autenticação.
- **Verificação que nunca testou nada**: `estado_encomenda.php` lia
  `$_SESSION['nivel_utilizador'==2]`, que indexa o *resultado* da comparação.
- **Verificação comentada** em `historico_encomendas.php`.
- **BOM UTF-8** removido dos ficheiros alterados: era emitido antes de qualquer
  `header()`, o que impedia os redireccionamentos de funcionar.
- **`--location-trusted`** retirado do `Virtual-Lab-Builder`. Não era explorável
  hoje (`--max-redirs 0` na mesma linha), mas contrariava o desenho do módulo.

---

## Revisto sem achados / Reviewed, nothing found

- **IT-Tool-Kit** — `subprocess` sempre com lista de argumentos, nunca
  `shell=True`; relatórios HTML com 38 usos de `escape()` e as únicas
  interpolações não escapadas são inteiros.
- **PDF-Suite** — sem análise de XML (logo sem XXE); nomes de saída construídos
  com `Path.stem`, que corta directórios; relatórios devidamente escapados.
- **VMware-Fleet-Console**, fora do TOCTOU — senhas nunca gravadas, ignoradas se
  alguém as puser no ficheiro de configuração, `getpass` no modo texto, e o
  filtro de registo deste projecto já cobria os separadores `=` e `:` que
  faltavam nos projectos de rede.

Nem tudo tinha defeitos. Vários destes módulos estão acima da média do que se vê
em produção — o `seguranca.sh` do Virtual-Lab-Builder, com lista de domínios
revalidada a cada salto e soma de verificação obrigatória, é o exemplo claro.

---

## Fica por decidir / Left for you to decide

1. **Palavras-passe em texto simples** na base de dados do `Projecto-de-escola`
   (`clientes.palavra_passe`, `utilizadores.palavra_passe`). Corrigir obriga a
   migrar os registos existentes com `password_hash()`/`password_verify()`, o
   que não se faz só no código.
2. **`mysql_*` continua morto no PHP 7+.** Conforme combinado, não houve
   migração para mysqli/PDO. Como essa extensão não tem consultas preparadas, a
   mitigação aplicada foi `mysql_real_escape_string()` — está assinalado em cada
   commit.
3. **`CERT_NONE` com credenciais no Printer-Remote-Toner-Monitor.** Tirou-se o
   pior caso (a descida para `http`), mas a ligação `https` continua a aceitar
   qualquer certificado. Fixar a impressão digital de cada impressora na
   primeira leitura é o passo seguinte, e é decisão de quem gere o parque.
4. **Sem PHP nem pytest no contentor**, e sem `sudo` para os instalar. As
   alterações PHP foram verificadas por leitura, não por execução. Os testes
   Python de asserção simples foram corridos directamente (28 passaram,
   incluindo os 8 novos), mas não é uma corrida completa de pytest.

---

## O que os modelos locais fizeram / What the local models did

Esta era a pergunta de fundo da corrida. A resposta é clara e não é boa.

### `qwen2.5-coder:3b`, corrida v2 (150 candidatos)

| medida | valor |
|---|---|
| veredictos REAL | 124 de 150 (82,7%) |
| candidatos objectivamente não exploráveis chamados REAL | **80 de 80 — 100%** |
| não interpretados | 0 (eram 13 na v1) |
| veredictos previsíveis **só a partir do nome da regra** | **96%** |

A última linha é a que interessa. Cinco das seis regras têm veredicto unânime:
todos os 69 `php-mysql-ext` → REAL, todos os 15 `ssl-unverified` → REAL, todos os
18 `hardcoded-secret` → FALSE_POSITIVE. O modelo não está a ler o código — está a
devolver a descrição da regra. Como filtro sobre o prefiltro de expressões
regulares que o alimenta, acrescenta cerca de 4%.

### E errou o achado mais grave que lhe foi mostrado

A v2 do prefiltro passou a apanhar o `menu_admin.php` — o painel de administração
sem `session_start()` nem verificação, que era o achado GT-1. Foi entregue ao
modelo com a regra escrita à frente. Veredicto:

> `FALSE_POSITIVE` — *"No session_start() or authorisation check is needed for a
> simple menu."*

A página tem "Menu de administrador" escrito na primeira linha. Na v1 este achado
nem sequer chegava ao modelo; na v2 chegou, e foi descartado.

### Resumo honesto

O modelo diz REAL a 100% das coisas inofensivas e FALSE_POSITIVE ao único
contorno de autenticação genuíno que viu. O sinal está praticamente invertido.
Isto confirma, com números, a regra que já seguíamos: **estes modelos sinalizam,
não decidem** — e nesta configuração nem a sinalizar acrescentam muito.

O canal `EXTRA` novo funciona mecanicamente (sete achados voluntários), mas o
conteúdo é fraco: três notas quase iguais sobre credenciais de teste, e um erro
de sintaxe inventado em `historico_encomendas.php`.

As corridas do `7b` e do `8b` continuam. Os números acima são do `3b`; os
ficheiros `triage_v2_*.json` e `scores.json` ficam com o resto.

### Notas sobre o próprio banco de ensaio

- A v1 tinha um defeito que só se viu por acaso: com 13 candidatos num prompt, o
  `3b` entrava em ciclo de repetição e devolvia 13 linhas iguais, sem veredicto
  nenhum. Corrigido com lotes de 6 — a v2 teve 0 não interpretados.
- A v1 não guardava a resposta em bruto, pelo que diagnosticar obrigava a repetir
  a corrida. A v2 guarda `triage_<modelo>_raw.jsonl`.
- Um prefiltro de linhas **não consegue** encontrar um defeito que é uma
  *ausência*. O `menu_admin.php` não tinha texto nenhum para casar. Daí as regras
  de ficheiro inteiro na v2.

---

*Created by Redfox using Claude*
