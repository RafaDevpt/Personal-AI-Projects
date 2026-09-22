#!/usr/bin/env python3
"""
PT-PT: Corre um modelo novo contra a MESMA prova que o 3b, o 7b e o 8b fizeram,
       e poe o resultado ao lado dos deles.

       A razao de existir: a pergunta "vale a pena um modelo maior?" nao se
       responde com uma impressao depois de trocar duas mensagens com ele. Os
       150 candidatos, os 6 achados verificados a mao e o marcador ja existem --
       o que faltava era poder apontar isto a outra maquina.

       O que se mede, por ordem de importancia:

       1. **Excesso de reclamacao.** Quantas vezes chama REAL a coisas que
          objectivamente nao sao exploraveis. O 3b esteve nos 100%, o 7b nos
          66%. E este numero que decide se o funil serve para alguma coisa.
       2. **Recall no que foi verificado a mao.** Apanha o painel de
          administracao sem autenticacao? O 7b foi o unico que apanhou.
       3. **Sobrevivencia ao formato.** Quantas respostas nao se conseguem ler.
          Mede a configuracao tanto como o modelo -- ver o caso do qwen3:8b.

EN-UK: Runs a new model against the SAME test the 3b, 7b and 8b took, and puts
       the result beside theirs. The question "is a bigger model worth it?" is
       not answered by an impression after two messages with it. The 150
       candidates, 6 hand-verified findings and the scorer already exist; what
       was missing was being able to point this at another machine.

Uso / Usage:
    python3 provar_modelo.py qwen3:30b-a3b --host http://100.110.43.103:11434
    python3 provar_modelo.py qwen3:30b-a3b --host ... --num-predict 2000
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def modelos_em(host: str, timeout: float = 8.0) -> list[str] | None:
    """PT-PT: O que esta instalado naquele Ollama. / EN-UK: What that Ollama has."""
    try:
        with urllib.request.urlopen(f"{host.rstrip('/')}/api/tags", timeout=timeout) as r:
            return sorted(m["name"] for m in json.load(r).get("models", []))
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None


def e_moe(host: str, modelo: str) -> tuple[bool, str]:
    """
    PT-PT: O modelo e Mixture-of-Experts?

           Interessa porque e a condicao de entrada do FreeToken: so acelera
           MoE, e so quando o modelo nao cabe na VRAM. Se o modelo for denso,
           nao ha nada a ganhar em experimenta-lo.
    EN-UK: Is the model Mixture-of-Experts? It matters because that is
           FreeToken's entry condition: it only speeds up MoE, and only when the
           model does not fit in VRAM. For a dense model there is nothing to gain.
    """
    try:
        pedido = urllib.request.Request(
            f"{host.rstrip('/')}/api/show",
            data=json.dumps({"model": modelo}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(pedido, timeout=20) as r:
            d = json.load(r)
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
        return False, f"não foi possível consultar: {exc}"

    info = d.get("model_info", {})
    chaves = {k: v for k, v in info.items() if "expert" in k.lower()}
    detalhes = d.get("details", {})
    descricao = (f"{detalhes.get('family','?')} · {detalhes.get('parameter_size','?')} · "
                 f"{detalhes.get('quantization_level','?')}")
    if chaves:
        activos = next((v for k, v in chaves.items() if "used" in k.lower()), "?")
        total = next((v for k, v in chaves.items() if "count" in k.lower()), "?")
        return True, f"{descricao} · MoE, {activos} de {total} experts por token"
    return False, f"{descricao} · denso"


def principal() -> int:
    p = argparse.ArgumentParser(description="Prova um modelo contra o banco de ensaio.")
    p.add_argument("modelo")
    p.add_argument("--host", default="http://127.0.0.1:11434")
    p.add_argument("--num-predict", type=int, default=80,
                   help="Fichas por candidato. Suba para 2000+ se o modelo raciocinar.")
    p.add_argument("--sem-raciocinio", action="store_true")
    p.add_argument("--lote", type=int, default=6)
    p.add_argument("--so-verificar", action="store_true",
                   help="Confirma que dá para correr e sai, sem gastar tempo de máquina.")
    args = p.parse_args()

    print(f"\n  Ollama: {args.host}")
    disponiveis = modelos_em(args.host)
    if disponiveis is None:
        print(f"\n  Não foi possível falar com {args.host}.")
        print("  Verifique:")
        print("    - a máquina está ligada e na tailnet   (tailscale status)")
        print("    - o Ollama está a escutar para fora    (OLLAMA_HOST=0.0.0.0:11434)")
        return 2

    print(f"  modelos lá: {', '.join(disponiveis) or '(nenhum)'}")
    if args.modelo not in disponiveis:
        print(f"\n  {args.modelo!r} não está instalado nessa máquina.")
        print(f"  Lá:  ollama pull {args.modelo}")
        return 2

    moe, descricao = e_moe(args.host, args.modelo)
    print(f"  {args.modelo}: {descricao}")
    if moe:
        print("  → É MoE: o FreeToken pode fazer diferença, se não couber na VRAM.")
    else:
        print("  → É denso: o FreeToken não se aplica a este modelo.")

    if args.so_verificar:
        print("\n  Dá para correr. Repita sem --so-verificar.\n")
        return 0

    saida = AQUI / f"triage_v3_{args.modelo.replace(':', '_').replace('.', '_')}.json"
    comando = [sys.executable, str(AQUI / "llm_triage_v3.py"), args.modelo, str(saida),
               "prefilter_v2.json", "--host", args.host,
               "--num-predict", str(args.num_predict), "--lote", str(args.lote)]
    if args.sem_raciocinio:
        comando.append("--sem-raciocinio")

    print(f"\n  A correr 150 candidatos. Com um modelo grande isto leva um bom bocado.\n")
    inicio = time.monotonic()
    r = subprocess.run(comando, cwd=str(AQUI), check=False)
    if r.returncode != 0:
        print(f"\n  A triagem falhou (código {r.returncode}).")
        return 1
    print(f"\n  Terminado em {(time.monotonic() - inicio) / 60:.1f} min.")

    # PT-PT: Pontua este a par dos anteriores, para a comparacao ser directa.
    # EN-UK: Scores this alongside the earlier ones, so the comparison is direct.
    anteriores = ["triage_v2_qwen2_5-coder_3b.json",
                  "triage_v2_qwen2_5-coder_7b.json",
                  "triage_v2_qwen3_8b.json"]
    existentes = [f for f in anteriores if (AQUI / f).exists()]
    print("\n" + "═" * 64)
    subprocess.run([sys.executable, str(AQUI / "score_triage.py"), *existentes, saida.name],
                   cwd=str(AQUI), check=False)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
