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

### 6. Chave de anfitrião SSH não verificada — `Network-Config-Builder` e `Network-Topology-Mapper`

> ⚠️ **Esta é a única correcção da noite que muda o comportamento.** Ver a
> secção *Fica por decidir* antes de usar.

O `ConnectHandler` era chamado sem `ssh_strict` nem `system_host_keys`. A
omissão do Netmiko é `ssh_strict=False`, e nessa altura o paramiko fica com a
`AutoAddPolicy`: **qualquer** chave de anfitrião é aceite sem perguntar.

Logo a seguir seguem o utilizador, a palavra-passe **e o enable secret**. Quem
estivesse no meio da rede de gestão recebia as credenciais do equipamento
inteiras — a mesma classe de problema do TOCTOU do vSphere, com o agravante de
levar o enable.

Confirmado no código do netmiko 4.3.0, não de memória:

```python
# base_connection.py
ssh_strict: bool = False,        # ":param ssh_strict: ... (default: False, which
                                 #  means unknown SSH host keys will be accepted)"
if not ssh_strict:
    self.key_policy = paramiko.AutoAddPolicy()
```

Repare-se em como isto escapou ao prefiltro: existia uma regra à procura de
`AutoAddPolicy` no código, e não encontrou nada — porque a palavra não está lá
escrita. É uma omissão de biblioteca, e **uma expressão regular não vê
omissões**. É o mesmo ponto cego que deixava passar o `menu_admin.php`.

Passa a usar-se `RejectPolicy` com o `~/.ssh/known_hosts`, como o `ssh` da linha
de comandos, com uma definição nova `verificar_chave_ssh` (por omissão `True`).

### 7. Dados de saúde legíveis por outras contas — `Medical-Audio-to-Text`

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

### ⚠️ Primeiro, a única alteração que muda o comportamento

`Network-Config-Builder` e `Network-Topology-Mapper` passam a **recusar**
equipamentos cuja chave de anfitrião não esteja no `~/.ssh/known_hosts`. Antes
ligavam a tudo.

Se na segunda-feira nenhum switch responder, é isto — e resolve-se com uma linha
por equipamento, depois de confirmar a chave:

```bash
ssh-keyscan -H 10.0.0.1 >> ~/.ssh/known_hosts
```

A mensagem de erro já diz isto, não fica só aqui. Para voltar ao comportamento
antigo, `verificar_chave_ssh: false` no ficheiro de definições.

Escolhi falhar fechado em vez de aberto, porque o que seguia na ligação era o
enable secret. Se preferir o contrário até ter o `known_hosts` povoado, é mudar
uma linha — mas é decisão sua, e é por isso que está no topo desta secção.

Verificado que um ficheiro de definições escrito antes desta alteração carrega
na mesma e fica com `True`, em vez de herdar o comportamento antigo por omissão.

### Depois, o que não foi tocado

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

Esta era a pergunta de fundo da corrida. As três passagens terminaram.

| modelo | tempo | REAL | FALSE_POSITIVE | não interpretado | excesso¹ | apanhou o GT-1? |
|---|---:|---:|---:|---:|---:|---|
| `qwen2.5-coder:3b` | 15 min | 124 | 26 | 0% | **100%** | não — disse FALSE_POSITIVE |
| `qwen2.5-coder:7b` | 34 min | 122 | 28 | 0% | **66%** | **sim** |
| `qwen3:8b` | 118 min | 48 | 23 | **53%** | 76%² | não — não respondeu |

¹ Percentagem de candidatos **objectivamente não exploráveis** (API `mysql_*`
morta, casamentos dentro de comentários) a que o modelo chamou REAL, contada
apenas sobre os que chegou a julgar.

² Ver a ressalva sobre o `qwen3:8b` mais abaixo — este número não mede o modelo.

### O 7b é o único que serve para alguma coisa

Foi o único que, perante o `menu_admin.php` — o painel de administração sem
`session_start()` nem verificação — respondeu REAL. E tem quase metade do
excesso do 3b. Se este funil for para continuar, é o 7b, e não o 3b, que deve
estar na etapa 2.

### O 3b não está a ler o código

**96% dos veredictos do 3b são previsíveis só a partir do nome da regra.** Cinco
das seis regras vieram unânimes: todos os 69 `php-mysql-ext` → REAL, todos os 15
`ssl-unverified` → REAL, todos os 18 `hardcoded-secret` → FALSE_POSITIVE. Está a
devolver a descrição da regra, não a julgar o código. Como filtro sobre o
prefiltro que o alimenta, acrescenta cerca de 4%.

E o achado mais grave que lhe foi mostrado, com a regra escrita à frente:

> `FALSE_POSITIVE` — *"No session_start() or authorisation check is needed for a
> simple menu."*

A página tem "Menu de administrador" na primeira linha.

### Ressalva: o número do `qwen3:8b` é culpa do banco de ensaio, não do modelo

O `qwen3` é um modelo de raciocínio. O orçamento de tokens que eu lhe dei
(`num_predict = 80 × candidatos + 120`) chega para um modelo que responde
directamente e **não chega** para um que pensa primeiro:

- 70 das 99 chamadas terminaram com `done_reason=length` — ficaram sem
  orçamento a meio;
- 64 devolveram resposta **vazia**: gastaram tudo no raciocínio e nunca chegaram
  ao veredicto;
- as 29 que terminaram em `stop` responderam bem, e no formato certo.

Portanto os 53% de não interpretado medem a minha configuração, não a
capacidade do modelo. **Não o classifique como o pior dos três com base nesta
tabela.** Uma medição justa precisa de repetir a passagem com o orçamento muito
maior, ou com o raciocínio desligado — são cerca de duas horas de máquina, e não
cabiam antes das 07:30.

### Resumo honesto

A regra que já seguíamos fica confirmada com números: **estes modelos sinalizam,
não decidem.** O 3b, nesta configuração, nem a sinalizar acrescenta. O 7b é
utilizável como primeira peneira desde que alguém leia o que ele marca — que foi
exactamente o que se fez esta noite: **nenhuma das correcções deste relatório
saiu do veredicto de um modelo.** Todas saíram de ler o código.

O canal `EXTRA` funciona mecanicamente (7 achados no 3b, 4 no 8b), mas o
conteúdo é fraco: notas repetidas sobre credenciais de teste e um erro de
sintaxe inventado em `historico_encomendas.php`.

### Notas sobre o próprio banco de ensaio

- A v1 tinha um defeito que só se viu por acaso: com 13 candidatos num prompt, o
  `3b` entrava em ciclo de repetição e devolvia 13 linhas iguais, sem veredicto
  nenhum. Corrigido com lotes de 6 — a v2 teve 0 não interpretados no 3b e no 7b.
- A v1 não guardava a resposta em bruto, pelo que diagnosticar obrigava a repetir
  a corrida. A v2 guarda `triage_<modelo>_raw.jsonl` — e foi só por causa disso
  que o problema do `qwen3` se percebeu em minutos em vez de ficar por explicar.
- Um prefiltro de linhas **não consegue** encontrar um defeito que é uma
  *ausência*. Isso apanhou-nos duas vezes: o `menu_admin.php`, que não tinha
  texto para casar, e o `ssh_strict` do Netmiko, onde a regra procurava
  `AutoAddPolicy` e a palavra não está escrita em lado nenhum — é uma omissão.
- O próprio `score_triage.py` tinha um erro que dava jeito não ter: calculava o
  excesso sobre **todos** os candidatos não exploráveis, incluindo os que o
  modelo nunca respondeu. Com isso o `qwen3:8b` aparecia com 40% e parecia o
  mais prudente dos três, quando apenas não tinha respondido. Corrigido para
  contar só sobre os julgados, o que o põe em 76%.

---

*Created by Redfox using Claude*
