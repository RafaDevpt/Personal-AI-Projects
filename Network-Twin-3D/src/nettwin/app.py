#!/usr/bin/env python3
"""
PT-PT: Janela de ambiente de trabalho (pywebview).

       A interface é HTML + Three.js servido localmente — nada vem da
       Internet, porque esta ferramenta vai correr em redes de hotel onde a
       saída pode estar fechada, e porque os dados (topologia, IPs, MACs) não
       devem sair do PC.

       A classe `Api` é o que o JavaScript chama (`window.pywebview.api.*`).
       Cada método devolve `{"ok": True, ...}` ou `{"ok": False, "erro": "..."}`
       — nunca deixa uma excepção atravessar a ponte, porque do lado do
       JavaScript ela chegava como um erro genérico sem a mensagem.

EN-UK: Desktop window (pywebview).

       The interface is HTML + Three.js served locally — nothing comes from the
       Internet, because this tool will run on hotel networks where egress may
       be closed, and because the data (topology, IPs, MACs) must not leave the
       PC.

       `Api` is what the JavaScript calls (`window.pywebview.api.*`). Every
       method returns `{"ok": True, ...}` or `{"ok": False, "erro": "..."}` —
       no exception ever crosses the bridge, since on the JavaScript side it
       would arrive as a generic error without its message.

Created by Redfox using Claude
"""

from __future__ import annotations

import base64
import copy
import json
import logging
import re
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import engine, exports, importers, loaders
from .models import RACK_MACHINE_KINDS
from .scene import build_scene, plan_data_url

log = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent / "web"
EXAMPLE_PROJECT = Path(__file__).resolve().parents[2] / "exemplo" / "projeto.json"


class Api:
    """
    PT-PT: A ponte entre a interface e o Python.
    EN-UK: The bridge between the interface and Python.
    """

    def __init__(self) -> None:
        self.window: Any = None
        self.project: dict[str, Any] | None = None
        self.project_path: Path | None = None
        self.dirty = False
        self._twin: Any = None
        self._result: Any = None
        self.initial_project: Path | None = None

    def arranque(self) -> dict[str, Any]:
        """
        PT-PT: Chamado pela página quando fica pronta: abre o projeto dado na
               linha de comandos, se houver.
        EN-UK: Called by the page once ready: opens the command-line project,
               if any.
        """
        if self.initial_project is None:
            return {"ok": False, "vazio": True}
        return self._open_path(self.initial_project)

    # -----------------------------------------------------------------------
    # PT-PT: Abrir. / EN-UK: Open.
    # -----------------------------------------------------------------------

    def abrir_projeto(self) -> dict[str, Any]:
        """PT-PT: Pede um projeto.json e abre-o. / EN-UK: Asks for a projeto.json and opens it."""
        caminhos = self._dialog_open("Projeto do Network Twin 3D (*.json)", multiple=False)
        if not caminhos:
            return {"ok": False, "cancelado": True}
        return self._open_path(Path(caminhos[0]))

    def abrir_exemplo(self) -> dict[str, Any]:
        """PT-PT: Abre o hotel de exemplo. / EN-UK: Opens the example hotel."""
        if not EXAMPLE_PROJECT.exists():
            return {"ok": False, "erro": f"Exemplo não encontrado em {EXAMPLE_PROJECT}."}
        return self._open_path(EXAMPLE_PROJECT)

    def novo_projeto(self) -> dict[str, Any]:
        """
        PT-PT: Monta um projeto a partir de ficheiros soltos: mapa (opcional),
               perfis (opcional, vários) e edifício (opcional). Pelo menos o
               mapa ou um perfil.
        EN-UK: Builds a project from loose files: map, profiles and building,
               all optional, but at least the map or one profile.
        """
        mapa = self._dialog_open("Mapa do Network Topology Mapper (*.json)", multiple=False)
        perfis = self._dialog_open("Perfis do Network Config Builder (*.json)", multiple=True)
        if not mapa and not perfis:
            return {"ok": False, "erro": "É preciso pelo menos o mapa ou um perfil."}
        edificio = self._dialog_open("Edifício (*.json) — opcional", multiple=False)
        projeto = {
            "nome": "Novo projeto",
            "mapa": mapa[0] if mapa else "",
            "perfis": list(perfis or []),
            "edificio": edificio[0] if edificio else "",
            "cablagem": [],
            "equipamentos": {},
            "posicoes": {},
        }
        return self._load(projeto, path=None, dirty=True)

    def recarregar(self) -> dict[str, Any]:
        """
        PT-PT: Volta a ler tudo do disco — depois de um novo mapeamento ou de
               mexer num perfil no Config Builder.
        EN-UK: Re-reads everything from disk — after a new mapping run or a
               profile change in Config Builder.
        """
        if self.project is None:
            return {"ok": False, "erro": "Não há projeto aberto."}
        return self._load(self.project, self.project_path, self.dirty)

    # -----------------------------------------------------------------------
    # PT-PT: Editar e guardar. / EN-UK: Edit and save.
    # -----------------------------------------------------------------------

    def posicionar(self, device_id: str, building: str, floor: str, room: str) -> dict[str, Any]:
        """
        PT-PT: Põe um equipamento num edifício/piso/sala (ou tira-o, com piso
               vazio). As coordenadas exactas saem — a interface volta a
               distribuí-lo.
        EN-UK: Puts a device in a building/floor/room (or removes it, with an
               empty floor). Exact coordinates are dropped.
        """

        def alterar(projeto: dict[str, Any]) -> None:
            posicoes = projeto.setdefault("posicoes", {})
            if floor:
                posicoes[device_id] = {"edificio": building, "piso": floor, "sala": room}
            else:
                posicoes.pop(device_id, None)

        return self._mutate(alterar)

    # -----------------------------------------------------------------------
    # PT-PT: Bastidores. / EN-UK: Racks.
    # -----------------------------------------------------------------------

    def criar_bastidor(self, dados: dict[str, Any]) -> dict[str, Any]:
        """
        PT-PT: Cria um bastidor numa sala. `dados`: nome, edificio, piso, sala,
               altura_u (omissão 42), e opcionalmente x, y.
        EN-UK: Creates a rack in a room.
        """

        def alterar(projeto: dict[str, Any]) -> None:
            nome = str(dados.get("nome") or "").strip()
            if not nome:
                raise ValueError("O bastidor precisa de um nome.")
            if not dados.get("piso"):
                raise ValueError("Escolha o piso do bastidor.")
            bastidores = projeto.setdefault("bastidores", [])
            novo = {
                "id": _unique_id(nome, {b["id"] for b in bastidores}),
                "nome": nome,
                "edificio": str(dados.get("edificio") or ""),
                "piso": str(dados["piso"]),
                "sala": str(dados.get("sala") or ""),
                "altura_u": _int_in(dados.get("altura_u", 42), 1, 60, "Altura do bastidor (U)"),
                "equipamentos": [],
            }
            for chave in ("x", "y"):
                if dados.get(chave) not in (None, ""):
                    novo[chave] = round(float(dados[chave]), 3)
            bastidores.append(novo)

        return self._mutate(alterar)

    def editar_bastidor(self, rack_id: str, dados: dict[str, Any]) -> dict[str, Any]:
        """
        PT-PT: Altera nome, altura, rotação e medidas. Recusa encolher um
               bastidor abaixo da máquina mais alta — perdia-se a máquina.
        EN-UK: Changes name, height, rotation and size. Refuses to shrink a
               rack below its highest machine.
        """

        def alterar(projeto: dict[str, Any]) -> None:
            bastidor = _find_rack(projeto, rack_id)
            if "nome" in dados:
                nome = str(dados["nome"]).strip()
                if not nome:
                    raise ValueError("O nome não pode ficar vazio.")
                bastidor["nome"] = nome
            if "altura_u" in dados:
                altura = _int_in(dados["altura_u"], 1, 60, "Altura do bastidor (U)")
                topo = max((_top(m) for m in bastidor.get("equipamentos", [])), default=0)
                if altura < topo:
                    raise ValueError(f"Há máquinas até à U{topo}: o bastidor não pode ter só {altura} U.")
                bastidor["altura_u"] = altura
            if "rotacao_graus" in dados:
                bastidor["rotacao_graus"] = float(dados["rotacao_graus"]) % 360
            for chave, minimo, maximo in (("largura_mm", 400, 1200), ("profundidade_mm", 300, 1400)):
                if chave in dados:
                    bastidor[chave] = _int_in(dados[chave], minimo, maximo, chave)

        return self._mutate(alterar)

    def mover_bastidor(
        self, rack_id: str, building: str, floor: str, room: str, x: float | None, y: float | None
    ) -> dict[str, Any]:
        """
        PT-PT: Muda o bastidor de sítio. Sem `x`/`y`, fica alinhado na sala.
        EN-UK: Moves the rack. Without `x`/`y`, it lines up in the room.
        """

        def alterar(projeto: dict[str, Any]) -> None:
            if not floor:
                raise ValueError("Escolha o piso.")
            bastidor = _find_rack(projeto, rack_id)
            bastidor.update({"edificio": building, "piso": floor, "sala": room})
            for chave, valor in (("x", x), ("y", y)):
                if valor is None or valor == "":
                    bastidor.pop(chave, None)
                else:
                    bastidor[chave] = round(float(valor), 3)

        return self._mutate(alterar)

    def remover_bastidor(self, rack_id: str) -> dict[str, Any]:
        """
        PT-PT: Apaga o bastidor do projeto (só do projeto — os ficheiros do
               mapa e dos perfis não são tocados). Os equipamentos de rede que
               lá estavam ficam sem posição.
        EN-UK: Deletes the rack from the project only. Its network devices are
               left unplaced.
        """

        def alterar(projeto: dict[str, Any]) -> None:
            _find_rack(projeto, rack_id)
            projeto["bastidores"] = [b for b in projeto["bastidores"] if b["id"] != rack_id]

        return self._mutate(alterar)

    def adicionar_maquina(self, rack_id: str, dados: dict[str, Any]) -> dict[str, Any]:
        """
        PT-PT: Monta uma máquina no bastidor. Recusa Us ocupadas ou fora do
               bastidor, com a mensagem a dizer qual é o conflito.
        EN-UK: Mounts a machine in the rack. Refuses occupied or out-of-range
               Us, naming the conflict.
        """

        def alterar(projeto: dict[str, Any]) -> None:
            bastidor = _find_rack(projeto, rack_id)
            maquina = _machine_from(dados, {"id": uuid.uuid4().hex[:10]})
            _check_fit(projeto, bastidor, maquina)
            bastidor.setdefault("equipamentos", []).append(maquina)

        return self._mutate(alterar)

    def editar_maquina(self, rack_id: str, machine_id: str, dados: dict[str, Any]) -> dict[str, Any]:
        """PT-PT: Altera uma máquina (incluindo mudar de U). / EN-UK: Edits a machine."""

        def alterar(projeto: dict[str, Any]) -> None:
            bastidor = _find_rack(projeto, rack_id)
            lista = bastidor.get("equipamentos", [])
            indice = _machine_index(bastidor, machine_id)
            maquina = _machine_from({**lista[indice], **dados}, {"id": lista[indice].get("id") or machine_id})
            _check_fit(projeto, bastidor, maquina, ignore=indice)
            lista[indice] = maquina

        return self._mutate(alterar)

    def remover_maquina(self, rack_id: str, machine_id: str) -> dict[str, Any]:
        """PT-PT: Tira uma máquina do bastidor. / EN-UK: Removes a machine from the rack."""

        def alterar(projeto: dict[str, Any]) -> None:
            bastidor = _find_rack(projeto, rack_id)
            del bastidor["equipamentos"][_machine_index(bastidor, machine_id)]

        return self._mutate(alterar)

    # -----------------------------------------------------------------------
    # PT-PT: Edifícios e editor. / EN-UK: Buildings and editor.
    # -----------------------------------------------------------------------

    def planta(self, building_id: str, floor_id: str) -> dict[str, Any]:
        """
        PT-PT: A imagem da planta de um piso, como data URL, para a textura do
               chão. Pedida uma vez por piso e guardada pela interface.
        EN-UK: A floor's plan image as a data URL, for the floor texture.
        """
        edificio = self._twin.building(building_id) if self._twin else None
        piso = edificio.floor(floor_id) if edificio else None
        if piso is None or piso.plan is None:
            return {"ok": False, "erro": "Este piso não tem planta em imagem."}
        caminho = Path(piso.plan.image)
        if not caminho.exists():
            return {"ok": False, "erro": f"A imagem da planta não está no disco: {caminho}"}
        try:
            return {"ok": True, "url": plan_data_url(caminho)}
        except (OSError, ValueError) as exc:
            return {"ok": False, "erro": str(exc)}

    def editar_edificio(self, building_id: str) -> dict[str, Any]:
        """
        PT-PT: O ficheiro de um edifício do projeto, tal como está, mais as
               plantas em data URL, para abrir no editor.
        EN-UK: A project building's file as is, plus plans as data URLs, to
               open in the editor.
        """
        edificio = self._twin.building(building_id) if self._twin else None
        if edificio is None or not edificio.path:
            return {"ok": False, "erro": f"Edifício {building_id!r} não encontrado no projeto."}
        try:
            dados = loaders._read_json(Path(edificio.path), "Edifício")
        except loaders.LoadError as exc:
            return {"ok": False, "erro": str(exc)}
        imagens = {}
        for piso in edificio.floors:
            if piso.plan and Path(piso.plan.image).exists():
                imagens[piso.id] = plan_data_url(Path(piso.plan.image))
        dados.setdefault("id", edificio.id)
        return {"ok": True, "edificio": dados, "imagens": imagens, "caminho": edificio.path}

    def guardar_edificio(
        self, dados: dict[str, Any], imagens: dict[str, str], path: str = ""
    ) -> dict[str, Any]:
        """
        PT-PT: Grava o edifício vindo do editor e junta-o ao projeto aberto.

               `imagens` é {id do piso: data URL} só para as plantas novas ou
               mudadas; as outras ficam como estão. As imagens vão para uma
               pasta `plantas/` ao lado do ficheiro, e o JSON guarda o caminho
               relativo — a pasta pode mudar de PC.

               Antes de gravar, o edifício passa pela mesma validação que a
               leitura: o editor nunca escreve um ficheiro que depois não abre.

        EN-UK: Saves the building from the editor and adds it to the open
               project. Images go to a `plantas/` folder next to the file, with
               relative paths. The building is validated exactly as on reading:
               the editor never writes a file that will not open.
        """
        try:
            bid = str(dados.get("id") or "").strip()
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", bid or "-?-"):
                raise ValueError("O id do edifício só pode ter letras, números, '-', '_' e '.'.")
            if path:
                destino = Path(path)
            else:
                pasta = self.project_path.parent if self.project_path else None
                escolhido = self._dialog_save(f"edificio-{bid}.json", directory=pasta)
                if not escolhido:
                    return {"ok": False, "cancelado": True}
                destino = Path(escolhido)
            pasta_plantas = destino.parent / "plantas"
            dados = copy.deepcopy(dados)
            dados["formato"], dados["tipo"] = loaders.SUPPORTED_VERSION, loaders.BUILDING_TYPE
            for piso in dados.get("pisos") or []:
                url = (imagens or {}).get(piso.get("id"))
                if url:
                    ficheiro = _write_data_url(url, pasta_plantas / f"{bid}-{piso['id']}")
                    piso.setdefault("planta", {})["imagem"] = ficheiro.relative_to(destino.parent).as_posix()
            loaders.building_from_dict(dados, destino.name, base_dir=destino.parent)
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(json.dumps(dados, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except (ValueError, OSError) as exc:
            return {"ok": False, "erro": str(exc)}

        if self.project is None:
            return {"ok": True, "caminho": str(destino), "cena": None}

        def juntar(projeto: dict[str, Any]) -> None:
            lista = projeto.setdefault("edificios", [])
            if str(destino.resolve()) not in {str(Path(e).resolve()) for e in lista}:
                lista.append(str(destino.resolve()))

        resposta = self._mutate(juntar)
        resposta["caminho"] = str(destino)
        return resposta

    def retirar_edificio(self, building_id: str) -> dict[str, Any]:
        """
        PT-PT: Tira o edifício do projeto (o ficheiro fica no disco).
        EN-UK: Removes the building from the project (the file stays on disk).
        """
        edificio = self._twin.building(building_id) if self._twin else None
        if edificio is None:
            return {"ok": False, "erro": f"Edifício {building_id!r} não encontrado."}

        def alterar(projeto: dict[str, Any]) -> None:
            alvo = str(Path(edificio.path).resolve())
            projeto["edificios"] = [e for e in projeto.get("edificios", []) if str(Path(e).resolve()) != alvo]

        return self._mutate(alterar)

    def importar_planta(self) -> dict[str, Any]:
        """
        PT-PT: Escolher uma planta: imagem (devolvida como data URL), PDF
               (página 1 desenhada; diz quantas páginas tem) ou DXF (devolve
               camadas e polígonos já em metros).
        EN-UK: Pick a plan: image (data URL), PDF (page 1 rendered; reports the
               page count) or DXF (layers and polygons already in metres).
        """
        caminhos = self._dialog_open(
            "Plantas (*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.pdf;*.dxf)", multiple=False
        )
        if not caminhos:
            return {"ok": False, "cancelado": True}
        caminho = Path(caminhos[0])
        sufixo = caminho.suffix.lower()
        try:
            if sufixo == ".dxf":
                return {"ok": True, "tipo": "dxf", "caminho": str(caminho), "nome": caminho.name,
                        **self._dxf(caminho, None)}
            if sufixo == ".pdf":
                paginas = importers.pdf_page_count(caminho)
                png = importers.render_pdf_page(caminho, 0)
                return {"ok": True, "tipo": "imagem", "nome": caminho.name, "caminho": str(caminho),
                        "paginas": paginas, "url": "data:image/png;base64," + base64.b64encode(png).decode()}
            return {"ok": True, "tipo": "imagem", "nome": caminho.name, "url": plan_data_url(caminho)}
        except importers.PlanImportError as exc:
            return {"ok": False, "erro": str(exc), "caminho": str(caminho)}
        except (OSError, ValueError) as exc:
            return {"ok": False, "erro": f"Não foi possível abrir {caminho.name}: {exc}"}

    def pagina_pdf(self, path: str, page: int) -> dict[str, Any]:
        """PT-PT: Outra página de um PDF já escolhido. / EN-UK: Another page of a chosen PDF."""
        try:
            png = importers.render_pdf_page(Path(path), int(page))
        except (importers.PlanImportError, OSError, ValueError) as exc:
            return {"ok": False, "erro": str(exc)}
        return {"ok": True, "url": "data:image/png;base64," + base64.b64encode(png).decode()}

    def ler_dxf(self, path: str, metres_per_unit: float | None) -> dict[str, Any]:
        """
        PT-PT: Relê um DXF com a escala escolhida (para DXF sem unidades).
        EN-UK: Re-reads a DXF with a chosen scale (for unitless DXFs).
        """
        try:
            return {"ok": True, "tipo": "dxf", "caminho": path, "nome": Path(path).name,
                    **self._dxf(Path(path), metres_per_unit)}
        except importers.PlanImportError as exc:
            return {"ok": False, "erro": str(exc)}

    def contorno_osm(self, lat: float, lon: float) -> dict[str, Any]:
        """
        PT-PT: Contornos de edifícios do OpenStreetMap à volta de lat/lon.
        EN-UK: OpenStreetMap building outlines around lat/lon.
        """
        try:
            return {"ok": True, "contornos": importers.osm_footprints(float(lat), float(lon))}
        except (importers.PlanImportError, ValueError) as exc:
            return {"ok": False, "erro": str(exc)}

    def _dxf(self, path: Path, metres_per_unit: float | None) -> dict[str, Any]:
        return importers.read_dxf(path, metres_per_unit).to_dict()

    def guardar(self) -> dict[str, Any]:
        """PT-PT: Grava o projeto (pede onde, se for novo). / EN-UK: Saves (asks where if new)."""
        if self.project is None:
            return {"ok": False, "erro": "Não há projeto aberto."}
        destino = self.project_path
        if destino is None:
            escolhido = self._dialog_save("projeto.json")
            if not escolhido:
                return {"ok": False, "cancelado": True}
            destino = Path(escolhido)
        try:
            loaders.save_project_file(self.project, destino)
        except OSError as exc:
            return {"ok": False, "erro": f"Não foi possível gravar {destino}: {exc}"}
        self.project_path = destino
        self.dirty = False
        return {"ok": True, "caminho": str(destino)}

    def exportar(self, kind: str) -> dict[str, Any]:
        """
        PT-PT: `constatacoes` ou `cabos`, em CSV.
        EN-UK: `constatacoes` (findings) or `cabos` (cables), as CSV.
        """
        if self._twin is None:
            return {"ok": False, "erro": "Não há projeto aberto."}
        nome = {"constatacoes": "constatacoes.csv", "cabos": "lista-de-cabos.csv"}.get(kind)
        if nome is None:
            return {"ok": False, "erro": f"Exportação desconhecida: {kind}"}
        escolhido = self._dialog_save(nome)
        if not escolhido:
            return {"ok": False, "cancelado": True}
        try:
            if kind == "constatacoes":
                caminho = exports.write_findings_csv(self._result, Path(escolhido))
            else:
                caminho = exports.write_cable_list_csv(self._twin, self._result, Path(escolhido))
        except OSError as exc:
            return {"ok": False, "erro": f"Não foi possível gravar: {exc}"}
        return {"ok": True, "caminho": str(caminho)}

    # -----------------------------------------------------------------------
    # PT-PT: Interno. / EN-UK: Internal.
    # -----------------------------------------------------------------------

    def _mutate(self, change: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        """
        PT-PT: Aplica uma alteração a uma cópia do projeto e recarrega. Se a
               alteração for recusada (ValueError) ou o resultado não abrir, o
               projeto em memória fica exactamente como estava.
        EN-UK: Applies a change to a copy of the project and reloads. If the
               change is refused or the result does not load, the in-memory
               project stays exactly as it was.
        """
        if self.project is None:
            return {"ok": False, "erro": "Não há projeto aberto."}
        projeto = copy.deepcopy(self.project)
        try:
            change(projeto)
        except (ValueError, KeyError, TypeError) as exc:
            return {"ok": False, "erro": str(exc).strip("'\"")}
        return self._load(projeto, self.project_path, dirty=True)

    def _open_path(self, path: Path) -> dict[str, Any]:
        try:
            projeto = loaders.load_project_file(path)
        except loaders.LoadError as exc:
            return {"ok": False, "erro": str(exc)}
        return self._load(projeto, path, dirty=False)

    def _load(self, project: dict[str, Any], path: Path | None, dirty: bool) -> dict[str, Any]:
        try:
            gemeo = loaders.build_twin(project)
        except loaders.LoadError as exc:
            return {"ok": False, "erro": str(exc)}
        except Exception as exc:  # noqa: BLE001 — nada pode atravessar a ponte / nothing crosses the bridge
            log.exception("Falha inesperada a montar o gémeo")
            return {"ok": False, "erro": f"Erro inesperado: {exc}"}
        resultado = engine.validate(gemeo)
        self.project, self.project_path, self.dirty = project, path, dirty
        self._twin, self._result = gemeo, resultado
        return {
            "ok": True,
            "cena": build_scene(gemeo, resultado),
            "caminho": str(path) if path else "",
            "por_gravar": dirty,
        }

    def _dialog_open(self, label: str, multiple: bool) -> list[str]:
        import webview

        tipo = webview.FileDialog.OPEN if hasattr(webview, "FileDialog") else webview.OPEN_DIALOG
        escolha = self.window.create_file_dialog(
            tipo, allow_multiple=multiple, file_types=(label, "Todos os ficheiros (*.*)")
        )
        return list(escolha or [])

    def _dialog_save(self, filename: str, directory: Path | None = None) -> str:
        import webview

        tipo = webview.FileDialog.SAVE if hasattr(webview, "FileDialog") else webview.SAVE_DIALOG
        escolha = self.window.create_file_dialog(
            tipo, directory=str(directory or ""), save_filename=filename
        )
        if not escolha:
            return ""
        return escolha if isinstance(escolha, str) else escolha[0]


def run(project: Path | None = None, debug: bool = False) -> int:
    """
    PT-PT: Abre a janela. Devolve o código de saída.
    EN-UK: Opens the window. Returns the exit code.
    """
    try:
        import webview
    except ImportError:
        print(
            "[ERRO] O pywebview não está instalado. Instale com: pip install pywebview\n"
            "       (ou use o EXECUTAR.bat, que trata disso).",
        )
        return 2

    api = Api()
    janela = webview.create_window(
        "Network Twin 3D",
        url=str(WEB_DIR / "index.html"),
        js_api=api,
        width=1440,
        height=900,
        min_size=(1000, 640),
        background_color="#111316",
    )
    api.window = janela
    api.initial_project = project

    # PT-PT: Servidor HTTP interno explícito: módulos ES (Three.js) não
    #        carregam a partir de file://, o motor do browser bloqueia-os.
    # EN-UK: Explicit built-in HTTP server: ES modules (Three.js) do not load
    #        from file://, the browser engine blocks them.
    webview.start(debug=debug, http_server=True)
    return 0


# ---------------------------------------------------------------------------
# PT-PT: Auxiliares das edições. / EN-UK: Edit helpers.
# ---------------------------------------------------------------------------


def _unique_id(name: str, taken: set[str]) -> str:
    """
    PT-PT: Id legível a partir do nome ("Bastidor P1" → "bastidor-p1"), com
           sufixo se já existir.
    EN-UK: Readable id from the name, suffixed if taken.
    """
    base = re.sub(r"[^a-z0-9]+", "-", _strip_accents(name.lower())).strip("-") or "bastidor"
    candidato, n = base, 2
    while candidato in taken:
        candidato, n = f"{base}-{n}", n + 1
    return candidato


def _strip_accents(text: str) -> str:
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def _int_in(value: Any, low: int, high: int, label: str) -> int:
    try:
        numero = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label}: tem de ser um número inteiro.") from None
    if not low <= numero <= high:
        raise ValueError(f"{label}: tem de estar entre {low} e {high}.")
    return numero


def _find_rack(project: dict[str, Any], rack_id: str) -> dict[str, Any]:
    for bastidor in project.get("bastidores") or []:
        if bastidor.get("id") == rack_id:
            return bastidor
    raise ValueError(f"Bastidor {rack_id!r} não encontrado.")


def _machine_index(rack: dict[str, Any], machine_id: str) -> int:
    """
    PT-PT: Posição da máquina na lista. Máquinas escritas à mão sem id têm o
           id "<bastidor>#<n>" que o leitor lhes deu.
    EN-UK: The machine's index. Hand-written machines without an id carry the
           "<rack>#<n>" id the loader gave them.
    """
    for i, m in enumerate(rack.get("equipamentos") or []):
        if (m.get("id") or f"{rack['id']}#{i + 1}") == machine_id:
            return i
    raise ValueError(f"Máquina {machine_id!r} não encontrada no bastidor {rack.get('nome', rack['id'])}.")


def _top(machine: dict[str, Any]) -> int:
    return int(machine.get("u") or 1) + int(machine.get("altura_u") or 1) - 1


def _machine_from(data: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """PT-PT: Valida e normaliza uma máquina vinda da interface. / EN-UK: Validates a machine."""
    nome = str(data.get("nome") or "").strip()
    if not nome:
        raise ValueError("A máquina precisa de um nome.")
    tipo = str(data.get("tipo") or "outro")
    if tipo not in RACK_MACHINE_KINDS:
        raise ValueError(f"Tipo de máquina desconhecido: {tipo}.")
    maquina = {
        "id": str(data.get("id") or defaults["id"]),
        "nome": nome,
        "tipo": tipo,
        "u": _int_in(data.get("u"), 1, 60, "U"),
        "altura_u": _int_in(data.get("altura_u", 1), 1, 20, "Altura (U)"),
    }
    for origem, destino in (("equipamento_rede", "equipamento_rede"), ("modelo", "modelo"),
                            ("serie", "serie"), ("nota", "nota")):
        valor = str(data.get(origem) or "").strip()
        if valor:
            maquina[destino] = valor
    return maquina


def _check_fit(
    project: dict[str, Any], rack: dict[str, Any], machine: dict[str, Any], ignore: int | None = None
) -> None:
    """
    PT-PT: A máquina cabe? Dentro do bastidor, sem sobrepor outra, e o mesmo
           equipamento de rede não pode estar montado em dois sítios.
    EN-UK: Does the machine fit? Inside the rack, overlapping nothing, and the
           same network device cannot be mounted twice.
    """
    altura = int(rack.get("altura_u") or 42)
    if _top(machine) > altura:
        raise ValueError(
            f"{machine['nome']} ocuparia U{machine['u']}–U{_top(machine)}, mas o bastidor só tem {altura} U."
        )
    for i, outra in enumerate(rack.get("equipamentos") or []):
        if i == ignore:
            continue
        if machine["u"] <= _top(outra) and int(outra.get("u") or 1) <= _top(machine):
            raise ValueError(
                f"U{machine['u']}–U{_top(machine)} já está ocupada por {outra.get('nome')} "
                f"(U{outra.get('u')}–U{_top(outra)})."
            )
    rede = machine.get("equipamento_rede")
    if rede:
        for bastidor in project.get("bastidores") or []:
            for i, outra in enumerate(bastidor.get("equipamentos") or []):
                if bastidor is rack and i == ignore:
                    continue
                if outra.get("equipamento_rede") == rede:
                    raise ValueError(f"{rede} já está montado em {bastidor.get('nome')} U{outra.get('u')}.")


def _write_data_url(url: str, stem: Path) -> Path:
    """
    PT-PT: Grava um data URL de imagem com a extensão certa. Só aceita PNG,
           JPEG e WebP — o que vem do editor — e no máximo 40 MB.
    EN-UK: Writes an image data URL with the right extension. PNG, JPEG and
           WebP only, 40 MB max.
    """
    correspondencia = re.match(r"^data:(image/(png|jpeg|webp));base64,(.+)$", url, re.DOTALL)
    if not correspondencia:
        raise ValueError("A planta não é uma imagem PNG, JPEG ou WebP válida.")
    dados = base64.b64decode(correspondencia.group(3), validate=False)
    if len(dados) > 40 * 1024 * 1024:
        raise ValueError("A planta tem mais de 40 MB; reduza a resolução antes de importar.")
    extensao = {"png": ".png", "jpeg": ".jpg", "webp": ".webp"}[correspondencia.group(2)]
    destino = stem.with_suffix(extensao)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(dados)
    return destino
