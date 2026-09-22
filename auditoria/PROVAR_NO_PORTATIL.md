# Provar um modelo no portátil

Como medir se um modelo maior vale a pena, em vez de decidir por impressão.

A prova é a mesma que o `qwen2.5-coder:3b`, o `7b` e o `qwen3:8b` já fizeram:
150 candidatos reais dos teus repositórios, 6 achados verificados à mão, e um
marcador que conta excesso de reclamação e recall. Assim o número novo fica
lado a lado com os antigos.

## No portátil, uma vez

**1. Ollama a escutar na tailnet — e só nela.**

```bash
mkdir -p ~/.config/systemd/user/ollama.service.d
cat > ~/.config/systemd/user/ollama.service.d/tailnet.conf <<'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF
systemctl --user daemon-reload && systemctl --user restart ollama
```

> `0.0.0.0` aqui faz o Ollama atender em todas as interfaces, **incluindo a do
> Wi-Fi da rua**. O Ollama não tem autenticação nenhuma: quem lhe chegar usa os
> teus modelos e lê o que lhe mandares. Se o portátil sair de casa, ou usa a
> firewall para deixar passar só a `tailscale0`, ou desliga isto quando acabar.
>
> No Windows é uma variável de ambiente do sistema com o mesmo nome.

**2. O modelo.** O candidato óbvio é o MoE do Qwen3 — 30 B de parâmetros, só
~3 B activos por token:

```bash
ollama pull qwen3:30b-a3b
```

Em Q4 são cerca de 18 GB. **Não cabe nos 6 GB da 4050**, cabe nos 32 GB de RAM —
que é exactamente a situação em que o FreeToken diz ganhar ao Ollama.

**3. O endereço na tailnet:**

```bash
tailscale ip -4
```

## No servidor

```bash
cd /data/llm-audit

# confirma que dá, sem gastar tempo de máquina
python3 provar_modelo.py qwen3:30b-a3b --host http://<ip-do-portatil>:11434 --so-verificar

# a prova a sério
python3 provar_modelo.py qwen3:30b-a3b --host http://<ip-do-portatil>:11434
```

Diz logo se o modelo é MoE ou denso, e no fim pontua-o ao lado dos outros três.

### Se o modelo raciocinar antes de responder

O `qwen3:8b` gastou o orçamento inteiro a pensar e devolveu resposta **vazia**
em 64 de 99 chamadas. Os 53% de «não interpretado» dele medem a minha
configuração, não o modelo. Para um modelo destes:

```bash
python3 provar_modelo.py <modelo> --host ... --num-predict 2000
# ou
python3 provar_modelo.py <modelo> --host ... --sem-raciocinio
```

## O que olhar no resultado

| medida | o que quer dizer | referência |
|---|---|---|
| **excesso de reclamação** | REAL em coisas que objectivamente não são exploráveis | 3b: 100% · 7b: 66% · 8b: 76% |
| **recall** | apanhou o painel de administração sem autenticação? | só o 7b apanhou |
| **não interpretado** | respostas ilegíveis — mede a configuração tanto como o modelo | 3b e 7b: 0% · 8b: 53% |
| **tempo** | 150 candidatos | 3b: 15 min · 7b: 34 min · 8b: 118 min |

**O número que decide é o excesso.** Um modelo que chame REAL a tudo não serve
de filtro, por muito bem que escreva. Se o MoE descer dos 66% do 7b **e**
apanhar o contorno de autenticação, vale a pena. Se ficar igual e levar três
vezes mais tempo, não vale — e aí a resposta ao FreeToken é que não há nada
para acelerar que valha a pena.

## Depois, e só depois, o FreeToken

Primeiro saber se o modelo presta; só então tratar de o acelerar.

E com cepticismo quanto aos números do vídeo: foram medidos numa RTX 5090, com
32 GB de VRAM e cerca de 1800 GB/s de largura de banda. A 4050 do portátil tem
6 GB e à volta de 190 GB/s — **cerca de nove vezes menos** — e a DDR4 anda pelos
50 GB/s. Um mecanismo descrito como «adaptativo à largura de banda» é
precisamente aquilo cujos ganhos não se transferem entre esses dois extremos.

A comparação honesta é correr a mesma prova duas vezes, uma com Ollama e outra
com FreeToken, no **teu** hardware.
