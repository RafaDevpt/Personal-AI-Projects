#!/usr/bin/env python3
"""
PT-PT: A janela principal.

       Cinco separadores, pela ordem em que o trabalho acontece: constrói-se a
       configuração, arruma-se as portas, escolhe-se o equipamento, compara-se
       com o que lá está e só depois se envia. Quem chegar ao quinto separador
       já passou pelos quatro anteriores, e é isso que se pretende — a ordem do
       ecrã é a ordem segura.

       Tudo o que fala com a rede corre noutra linha de execução. Um switch que
       demora 30 segundos a responder não pode deixar a janela pendurada: com a
       interface congelada, a reacção natural é fechar a aplicação a meio de um
       envio, que é exactamente o que não pode acontecer.

EN-UK: The main window.

       Five tabs, in the order the work happens: build the configuration, sort
       out the ports, pick the device, compare against what is there and only
       then push. Anyone reaching the fifth tab has been through the previous
       four, and that is the intent — the screen's order is the safe order.

       Everything that talks to the network runs on another thread. A switch
       taking 30 seconds to answer must not leave the window hanging: with a
       frozen interface the natural reaction is to close the application
       mid-push, which is exactly what must not happen.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog
from typing import Any

import customtkinter as ctk

from .. import __app_name__, __version__, diffing, inventory, presets, specfile
from ..config import Settings, save_settings
from ..models import (
    Credentials,
    Device,
    DeviceSpec,
    Interface,
    Management,
    Platform,
    PortMode,
    Security,
    Services,
    Severity,
    Vlan,
)
from ..transport import SwitchSession, TransportError, netmiko_available, reachable
from ..validation import has_errors, validate
from ..vendors import get_generator
from . import theme
from .dialogs import ConfirmPushDialog, CredentialsDialog, PortDialog, VlanDialog
from .widgets import (
    Card,
    ChoiceField,
    Field,
    MonoView,
    SwitchField,
    danger_button,
    primary_button,
    quiet_button,
)

logger = logging.getLogger(__name__)

_PLATFORM_BY_LABEL = {p.label: p for p in Platform}
_PRESET_BY_LABEL = {p.label: p.key for p in presets.PRESETS}


class App(ctk.CTk):
    """
    PT-PT: A aplicação. Guarda a configuração em edição, o inventário e as
           credenciais da sessão, e é quem coordena os separadores.
    EN-UK: The application. It holds the configuration being edited, the
           inventory and the session credentials, and coordinates the tabs.
    """

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings
        self.spec: DeviceSpec = DeviceSpec(platform=settings.platform)
        self.devices: list[Device] = []
        self.credentials: Credentials | None = None
        self.generated: str = ""
        self.current_running: str = ""

        ctk.set_appearance_mode(settings.tema)
        ctk.set_default_color_theme("blue")

        self.title(f"{__app_name__} {__version__}")
        self.minsize(theme.WINDOW_MIN_WIDTH, theme.WINDOW_MIN_HEIGHT)
        self.geometry(f"{theme.WINDOW_MIN_WIDTH}x{theme.WINDOW_MIN_HEIGHT}")
        self.configure(fg_color=theme.SURFACE)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_tabs()
        self._build_status_bar()

        self._apply_defaults()
        self._load_inventory_quietly()

    # -----------------------------------------------------------------------
    # PT-PT: Estrutura da janela.
    # EN-UK: Window structure.
    # -----------------------------------------------------------------------

    def _build_header(self) -> None:
        cabecalho = ctk.CTkFrame(self, fg_color=theme.SIDEBAR, corner_radius=0, height=64)
        cabecalho.grid(row=0, column=0, sticky="ew")
        cabecalho.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            cabecalho,
            text=__app_name__,
            font=ctk.CTkFont(size=theme.SIZE_TITLE, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=theme.PAD_L, pady=theme.PAD_M)

        ctk.CTkLabel(
            cabecalho,
            text="Aruba AOS-CX · Cisco IOS · Ubiquiti",
            font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED,
        ).grid(row=0, column=1, sticky="w", padx=theme.PAD_S)

    def _build_tabs(self) -> None:
        self.tabs = ctk.CTkTabview(
            self,
            fg_color=theme.SURFACE,
            segmented_button_selected_color=theme.ACCENT,
            segmented_button_selected_hover_color=theme.ACCENT_HOVER,
            text_color=theme.TEXT_PRIMARY,
        )
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=theme.PAD_M, pady=theme.PAD_S)

        for nome in ["Construtor", "Portas", "Equipamentos", "Comparar e enviar", "Definições"]:
            self.tabs.add(nome)
            self.tabs.tab(nome).grid_columnconfigure(0, weight=1)
            self.tabs.tab(nome).grid_rowconfigure(0, weight=1)

        self._build_builder_tab(self.tabs.tab("Construtor"))
        self._build_ports_tab(self.tabs.tab("Portas"))
        self._build_devices_tab(self.tabs.tab("Equipamentos"))
        self._build_push_tab(self.tabs.tab("Comparar e enviar"))
        self._build_settings_tab(self.tabs.tab("Definições"))

    def _build_status_bar(self) -> None:
        barra = ctk.CTkFrame(self, fg_color=theme.SIDEBAR, corner_radius=0, height=30)
        barra.grid(row=2, column=0, sticky="ew")
        barra.grid_columnconfigure(0, weight=1)

        self._status = ctk.CTkLabel(
            barra,
            text="Pronto.",
            font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED,
            anchor="w",
        )
        self._status.grid(row=0, column=0, sticky="w", padx=theme.PAD_M, pady=theme.PAD_XS)

    def status(self, message: str, tone: str = "info") -> None:
        """
        PT-PT: Escreve na barra de estado.

        EN-UK: Writes to the status bar.

        :param message:
            PT-PT: O que mostrar. / EN-UK: What to show.
        :param tone:
            PT-PT: "info", "ok", "aviso" ou "erro".
            EN-UK: "info", "ok", "aviso" or "erro".
        """
        cores = {
            "info": theme.TEXT_MUTED,
            "ok": theme.OK,
            "aviso": theme.WARNING,
            "erro": theme.DANGER,
        }
        self._status.configure(text=message, text_color=cores.get(tone, theme.TEXT_MUTED))

    # -----------------------------------------------------------------------
    # PT-PT: Separador do construtor.
    # EN-UK: Builder tab.
    # -----------------------------------------------------------------------

    def _build_builder_tab(self, parent: Any) -> None:
        parent.grid_columnconfigure(0, weight=3)
        parent.grid_columnconfigure(1, weight=4)

        formulario = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        formulario.grid(row=0, column=0, sticky="nsew", padx=(0, theme.PAD_S))
        formulario.grid_columnconfigure(0, weight=1)

        # --- Plataforma e modelo ---
        cartao = Card(
            formulario,
            "Plataforma e modelo",
            "A plataforma decide a sintaxe. O modelo preenche a forma; os valores são sempre seus.",
        )
        cartao.grid(row=0, column=0, sticky="ew", pady=(0, theme.PAD_S))
        self.f_platform = ChoiceField(
            cartao,
            "Plataforma",
            [p.label for p in Platform],
            value=self.settings.platform.label,
            command=self._on_platform_changed,
        )
        self.f_preset = ChoiceField(cartao, "Modelo de partida", [p.label for p in presets.PRESETS])
        quiet_button(cartao.body, "Aplicar modelo", self._apply_preset, width=150).grid(
            row=cartao.next_row(), column=1, sticky="w", pady=theme.PAD_XS
        )

        # --- Identidade ---
        cartao = Card(formulario, "Identidade e gestão")
        cartao.grid(row=1, column=0, sticky="ew", pady=theme.PAD_S)
        self.f_hostname = Field(cartao, "Nome do equipamento", placeholder="SW-PISO1-01")
        self.f_mgmt_vlan = Field(cartao, "VLAN de gestão", value="1", placeholder="10")
        self.f_mgmt_ip = Field(cartao, "Endereço de gestão", placeholder="10.0.10.2/24")
        self.f_gateway = Field(cartao, "Gateway", placeholder="10.0.10.1")
        self.f_domain = Field(cartao, "Domínio", placeholder="hotel.local")
        self.f_dns = Field(cartao, "Servidores DNS", placeholder="10.0.10.5, 10.0.10.6")

        # --- VLANs ---
        cartao = Card(formulario, "VLANs")
        cartao.grid(row=2, column=0, sticky="ew", pady=theme.PAD_S)
        self._vlan_list = ctk.CTkFrame(cartao.body, fg_color="transparent")
        self._vlan_list.grid(row=cartao.next_row(), column=0, columnspan=2, sticky="ew")
        self._vlan_list.grid_columnconfigure(0, weight=1)
        botoes = ctk.CTkFrame(cartao.body, fg_color="transparent")
        botoes.grid(row=cartao.next_row(), column=0, columnspan=2, sticky="w", pady=(theme.PAD_S, 0))
        quiet_button(botoes, "+ VLAN", self._add_vlan, width=110).pack(side="left", padx=(0, theme.PAD_XS))

        # --- Serviços ---
        cartao = Card(formulario, "Serviços")
        cartao.grid(row=3, column=0, sticky="ew", pady=theme.PAD_S)
        self.f_ntp = Field(cartao, "Servidores NTP", placeholder="10.0.10.5")
        self.f_syslog = Field(cartao, "Servidores syslog", placeholder="10.0.10.6")
        self.f_timezone = Field(cartao, "Fuso horário", value="WET")
        self.f_snmp = Field(cartao, "Comunidade SNMP", placeholder="não usar public")
        self.f_snmp_local = Field(cartao, "Localização SNMP", placeholder="Piso 1 - Bastidor A")
        self.f_snmp_contact = Field(cartao, "Contacto SNMP", placeholder="ti@exemplo.pt")

        # --- Segurança ---
        cartao = Card(
            formulario,
            "Segurança",
            "A palavra-passe não é pedida aqui: o ficheiro sai com um marcador para substituir à mão.",
        )
        cartao.grid(row=4, column=0, sticky="ew", pady=theme.PAD_S)
        self.f_admin = Field(cartao, "Utilizador administrativo", value="admin")
        self.f_banner = Field(cartao, "Aviso de entrada", placeholder="Acesso restrito")
        self.f_telnet = SwitchField(cartao, "Desligar telnet", True)
        self.f_http = SwitchField(cartao, "Desligar servidor Web", True)
        self.f_rstp = SwitchField(cartao, "Spanning-tree rápido (RSTP / RPVST)", True)

        # --- Notas ---
        cartao = Card(formulario, "Notas", "Vão para o cabeçalho do ficheiro gerado.")
        cartao.grid(row=5, column=0, sticky="ew", pady=(theme.PAD_S, theme.PAD_M))
        self.f_notes = Field(cartao, "Nota", placeholder="Intervenção 2026-09-01, ticket 4821", width=320)

        # --- Pré-visualização ---
        direita = ctk.CTkFrame(parent, fg_color="transparent")
        direita.grid(row=0, column=1, sticky="nsew")
        direita.grid_columnconfigure(0, weight=1)
        direita.grid_rowconfigure(1, weight=3)
        direita.grid_rowconfigure(3, weight=1)

        acoes = ctk.CTkFrame(direita, fg_color="transparent")
        acoes.grid(row=0, column=0, sticky="ew", pady=(0, theme.PAD_S))
        primary_button(acoes, "Gerar", self._generate, width=110).pack(side="left", padx=(0, theme.PAD_XS))
        quiet_button(acoes, "Guardar .cfg", self._save_config, width=120).pack(side="left", padx=theme.PAD_XS)
        quiet_button(acoes, "Guardar perfil", self._save_profile, width=130).pack(side="left", padx=theme.PAD_XS)
        quiet_button(acoes, "Abrir perfil", self._open_profile, width=120).pack(side="left", padx=theme.PAD_XS)

        self._preview = MonoView(direita)
        self._preview.grid(row=1, column=0, sticky="nsew")

        ctk.CTkLabel(
            direita,
            text="Validação",
            font=ctk.CTkFont(size=theme.SIZE_HEADING, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", pady=(theme.PAD_M, theme.PAD_XS))

        self._issues = MonoView(direita, height=140)
        self._issues.grid(row=3, column=0, sticky="nsew")

        self._refresh_vlans()

    def _on_platform_changed(self, _label: str) -> None:
        self.spec.platform = _PLATFORM_BY_LABEL[self.f_platform.get()]
        self.status(f"Plataforma: {self.spec.platform.label}")

    def _apply_preset(self) -> None:
        plataforma = _PLATFORM_BY_LABEL[self.f_platform.get()]
        chave = _PRESET_BY_LABEL[self.f_preset.get()]
        self.spec = presets.get(chave, plataforma)
        self._spec_to_form()
        self.status(f"Modelo aplicado: {self.f_preset.get()}", "ok")

    def _refresh_vlans(self) -> None:
        """PT-PT: Redesenha a lista de VLANs. / EN-UK: Redraws the VLAN list."""
        for filho in self._vlan_list.winfo_children():
            filho.destroy()

        if not self.spec.vlans:
            ctk.CTkLabel(
                self._vlan_list,
                text="Sem VLANs. Um switch sem VLANs declaradas fica todo na VLAN 1.",
                font=ctk.CTkFont(size=theme.SIZE_SMALL),
                text_color=theme.TEXT_MUTED,
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", pady=theme.PAD_XS)
            return

        for linha, vlan in enumerate(sorted(self.spec.vlans, key=lambda v: v.vid)):
            fila = ctk.CTkFrame(self._vlan_list, fg_color=theme.SURFACE, corner_radius=theme.RADIUS)
            fila.grid(row=linha, column=0, sticky="ew", pady=2)
            fila.grid_columnconfigure(1, weight=1)

            etiqueta = f"{vlan.vid}  ·  {vlan.safe_name}"
            if vlan.ip_cidr:
                etiqueta += f"  ·  {vlan.ip_cidr}"
            ctk.CTkLabel(
                fila, text=etiqueta, anchor="w", text_color=theme.TEXT_PRIMARY,
                font=ctk.CTkFont(size=theme.SIZE_SMALL),
            ).grid(row=0, column=1, sticky="ew", padx=theme.PAD_S, pady=theme.PAD_XS)

            quiet_button(fila, "Editar", lambda v=vlan: self._edit_vlan(v), width=70, height=26).grid(
                row=0, column=2, padx=2, pady=2
            )
            quiet_button(fila, "Remover", lambda v=vlan: self._remove_vlan(v), width=80, height=26).grid(
                row=0, column=3, padx=(2, theme.PAD_XS), pady=2
            )

    def _add_vlan(self) -> None:
        nova = VlanDialog(self).show()
        if nova is None:
            return
        self.spec.vlans = [v for v in self.spec.vlans if v.vid != nova.vid] + [nova]
        self._refresh_vlans()

    def _edit_vlan(self, vlan: Vlan) -> None:
        alterada = VlanDialog(self, vlan).show()
        if alterada is None:
            return
        self.spec.vlans = [v for v in self.spec.vlans if v.vid not in {vlan.vid, alterada.vid}]
        self.spec.vlans.append(alterada)
        self._refresh_vlans()

    def _remove_vlan(self, vlan: Vlan) -> None:
        self.spec.vlans = [v for v in self.spec.vlans if v.vid != vlan.vid]
        self._refresh_vlans()

    # -----------------------------------------------------------------------
    # PT-PT: Separador das portas.
    # EN-UK: Ports tab.
    # -----------------------------------------------------------------------

    def _build_ports_tab(self, parent: Any) -> None:
        parent.grid_rowconfigure(1, weight=1)

        acoes = ctk.CTkFrame(parent, fg_color="transparent")
        acoes.grid(row=0, column=0, sticky="ew", pady=(0, theme.PAD_S))
        primary_button(acoes, "+ Porta", self._add_port, width=110).pack(side="left", padx=(0, theme.PAD_XS))
        ctk.CTkLabel(
            acoes,
            text="Uma linha pode ser uma porta ou um intervalo — 1/1/1-1/1/24 configura 24 de uma vez.",
            font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED,
        ).pack(side="left", padx=theme.PAD_M)

        self._port_list = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self._port_list.grid(row=1, column=0, sticky="nsew")
        self._port_list.grid_columnconfigure(0, weight=1)
        self._refresh_ports()

    def _refresh_ports(self) -> None:
        """PT-PT: Redesenha a lista de portas. / EN-UK: Redraws the port list."""
        for filho in self._port_list.winfo_children():
            filho.destroy()

        if not self.spec.interfaces:
            ctk.CTkLabel(
                self._port_list,
                text="Sem portas configuradas. Aplique um modelo no construtor ou acrescente uma.",
                text_color=theme.TEXT_MUTED,
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", pady=theme.PAD_M)
            return

        for linha, interface in enumerate(self.spec.interfaces):
            fila = ctk.CTkFrame(self._port_list, fg_color=theme.SURFACE_RAISED, corner_radius=theme.RADIUS)
            fila.grid(row=linha, column=0, sticky="ew", pady=3)
            fila.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                fila,
                text=interface.name,
                width=160,
                anchor="w",
                text_color=theme.TEXT_PRIMARY,
                font=ctk.CTkFont(
                    family=theme.resolve_font(theme.FONT_MONO, theme.FONT_MONO_FALLBACKS),
                    size=theme.SIZE_SMALL,
                ),
            ).grid(row=0, column=0, sticky="w", padx=theme.PAD_S, pady=theme.PAD_S)

            ctk.CTkLabel(
                fila,
                text=_port_summary(interface),
                anchor="w",
                text_color=theme.TEXT_MUTED,
                font=ctk.CTkFont(size=theme.SIZE_SMALL),
            ).grid(row=0, column=1, sticky="ew", padx=theme.PAD_S)

            quiet_button(fila, "Editar", lambda i=interface: self._edit_port(i), width=70, height=28).grid(
                row=0, column=2, padx=2
            )
            quiet_button(fila, "Duplicar", lambda i=interface: self._duplicate_port(i), width=80, height=28).grid(
                row=0, column=3, padx=2
            )
            quiet_button(fila, "Remover", lambda i=interface: self._remove_port(i), width=80, height=28).grid(
                row=0, column=4, padx=(2, theme.PAD_S)
            )

    def _port_hint(self) -> str:
        exemplos = {
            Platform.ARUBA_CX: "No AOS-CX: 1/1/1 ou 1/1/1-1/1/24",
            Platform.CISCO_IOS: "No IOS: GigabitEthernet1/0/1 ou GigabitEthernet1/0/1-24",
            Platform.UBIQUITI_EDGESWITCH: "No EdgeSwitch: 0/1 ou 0/1-0/24",
            Platform.UBIQUITI_UNIFI: "No UniFi: 0/1 ou 0/1-0/24",
        }
        return exemplos[_PLATFORM_BY_LABEL[self.f_platform.get()]]

    def _add_port(self) -> None:
        nova = PortDialog(self, hint=self._port_hint()).show()
        if nova is None:
            return
        self.spec.interfaces.append(nova)
        self._refresh_ports()

    def _edit_port(self, interface: Interface) -> None:
        alterada = PortDialog(self, interface, hint=self._port_hint()).show()
        if alterada is None:
            return
        indice = self.spec.interfaces.index(interface)
        self.spec.interfaces[indice] = alterada
        self._refresh_ports()

    def _duplicate_port(self, interface: Interface) -> None:
        copia = Interface(
            name=interface.name,
            description=interface.description,
            mode=interface.mode,
            access_vlan=interface.access_vlan,
            native_vlan=interface.native_vlan,
            tagged_vlans=list(interface.tagged_vlans),
            voice_vlan=interface.voice_vlan,
            poe=interface.poe,
            enabled=interface.enabled,
            edge_port=interface.edge_port,
        )
        nova = PortDialog(self, copia, hint=self._port_hint()).show()
        if nova is None:
            return
        self.spec.interfaces.append(nova)
        self._refresh_ports()

    def _remove_port(self, interface: Interface) -> None:
        self.spec.interfaces.remove(interface)
        self._refresh_ports()

    # -----------------------------------------------------------------------
    # PT-PT: Separador dos equipamentos.
    # EN-UK: Devices tab.
    # -----------------------------------------------------------------------

    def _build_devices_tab(self, parent: Any) -> None:
        parent.grid_rowconfigure(1, weight=1)

        acoes = ctk.CTkFrame(parent, fg_color="transparent")
        acoes.grid(row=0, column=0, sticky="ew", pady=(0, theme.PAD_S))
        quiet_button(acoes, "Importar lista", self._import_inventory, width=130).pack(side="left", padx=(0, theme.PAD_XS))
        quiet_button(acoes, "Exportar Excel", self._export_inventory, width=130).pack(side="left", padx=theme.PAD_XS)
        quiet_button(acoes, "Testar ligação", self._test_all, width=130).pack(side="left", padx=theme.PAD_XS)
        quiet_button(acoes, "Backup de todos", self._backup_all, width=140).pack(side="left", padx=theme.PAD_XS)

        self._device_list = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self._device_list.grid(row=1, column=0, sticky="nsew")
        self._device_list.grid_columnconfigure(0, weight=1)

    def _refresh_devices(self) -> None:
        """PT-PT: Redesenha a lista de equipamentos. / EN-UK: Redraws the device list."""
        for filho in self._device_list.winfo_children():
            filho.destroy()

        if not self.devices:
            ctk.CTkLabel(
                self._device_list,
                text=(
                    "Inventário vazio. Importe a lista que já tem em Excel, ou crie um modelo com:\n"
                    "python -m netconfig inventario --criar-modelo inventario.xlsx"
                ),
                text_color=theme.TEXT_MUTED,
                anchor="w",
                justify="left",
            ).grid(row=0, column=0, sticky="ew", pady=theme.PAD_M)
            return

        self._device_status: dict[str, ctk.CTkLabel] = {}
        for linha, device in enumerate(self.devices):
            fila = ctk.CTkFrame(self._device_list, fg_color=theme.SURFACE_RAISED, corner_radius=theme.RADIUS)
            fila.grid(row=linha, column=0, sticky="ew", pady=3)
            fila.grid_columnconfigure(2, weight=1)

            ctk.CTkLabel(
                fila, text=device.name, width=170, anchor="w", text_color=theme.TEXT_PRIMARY
            ).grid(row=0, column=0, sticky="w", padx=theme.PAD_S, pady=theme.PAD_S)
            ctk.CTkLabel(
                fila, text=device.host, width=130, anchor="w", text_color=theme.TEXT_MUTED,
                font=ctk.CTkFont(
                    family=theme.resolve_font(theme.FONT_MONO, theme.FONT_MONO_FALLBACKS),
                    size=theme.SIZE_SMALL,
                ),
            ).grid(row=0, column=1, sticky="w")
            ctk.CTkLabel(
                fila,
                text=f"{device.platform.label}  ·  {device.site or 'sem local'}",
                anchor="w",
                text_color=theme.TEXT_MUTED,
                font=ctk.CTkFont(size=theme.SIZE_SMALL),
            ).grid(row=0, column=2, sticky="ew", padx=theme.PAD_S)

            estado = ctk.CTkLabel(fila, text="—", width=90, text_color=theme.TEXT_MUTED)
            estado.grid(row=0, column=3, padx=theme.PAD_S)
            self._device_status[device.name] = estado

    def _load_inventory_quietly(self) -> None:
        try:
            self.devices = inventory.load(self.settings.inventory_file)
        except (inventory.InventoryError, OSError) as exc:
            logger.warning("Inventário não lido: %s", exc)
            self.devices = []
        self._refresh_devices()
        self._refresh_device_choices()

    def _import_inventory(self) -> None:
        caminho = filedialog.askopenfilename(
            title="Importar inventário",
            filetypes=[("Listas", "*.xlsx *.xlsm *.csv *.json"), ("Todos", "*.*")],
        )
        if not caminho:
            return
        try:
            self.devices = inventory.load(Path(caminho))
            inventory.save_json(self.devices, self.settings.inventory_file)
        except (inventory.InventoryError, OSError) as exc:
            self.status(str(exc), "erro")
            return
        self._refresh_devices()
        self._refresh_device_choices()
        self.status(f"{len(self.devices)} equipamentos importados.", "ok")

    def _export_inventory(self) -> None:
        caminho = filedialog.asksaveasfilename(
            title="Exportar inventário", defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if not caminho:
            return
        try:
            destino = inventory.save_xlsx(self.devices, Path(caminho))
        except (inventory.InventoryError, OSError) as exc:
            self.status(str(exc), "erro")
            return
        self.status(f"Inventário escrito em {destino}", "ok")

    def _test_all(self) -> None:
        if not self.devices:
            self.status("Inventário vazio.", "aviso")
            return

        self.status("A testar ligação...")

        def trabalho() -> list[tuple[str, bool]]:
            return [(d.name, reachable(d.host, d.port)) for d in self.devices]

        def concluido(resultados: list[tuple[str, bool]]) -> None:
            for nome, ok in resultados:
                etiqueta = self._device_status.get(nome)
                if etiqueta is not None:
                    etiqueta.configure(
                        text="responde" if ok else "sem resposta",
                        text_color=theme.OK if ok else theme.OFFLINE,
                    )
            alcancaveis = sum(1 for _, ok in resultados if ok)
            self.status(f"{alcancaveis} de {len(resultados)} respondem em SSH.", "ok")

        self._run_async(trabalho, concluido)

    def _backup_all(self) -> None:
        if not self._require_netmiko() or not self.devices:
            return
        credenciais = self._require_credentials()
        if credenciais is None:
            return

        self.status("A guardar configurações...")
        pasta = self.settings.backup_path

        def trabalho() -> list[str]:
            resultados: list[str] = []
            for device in self.devices:
                try:
                    with SwitchSession(device, credenciais, self.settings.ssh_timeout) as sessao:
                        caminho = sessao.backup(pasta)
                    resultados.append(f"{device.name}: {caminho.name}")
                except TransportError as exc:
                    resultados.append(f"{device.name}: FALHOU — {exc}")
            return resultados

        def concluido(resultados: list[str]) -> None:
            falhas = sum(1 for linha in resultados if "FALHOU" in linha)
            tom = "aviso" if falhas else "ok"
            self.status(f"Backups terminados. {falhas} falharam. Pasta: {pasta}", tom)

        self._run_async(trabalho, concluido)

    # -----------------------------------------------------------------------
    # PT-PT: Separador de comparar e enviar.
    # EN-UK: Compare and push tab.
    # -----------------------------------------------------------------------

    def _build_push_tab(self, parent: Any) -> None:
        parent.grid_rowconfigure(2, weight=1)

        topo = ctk.CTkFrame(parent, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", pady=(0, theme.PAD_S))

        ctk.CTkLabel(topo, text="Equipamento", text_color=theme.TEXT_PRIMARY).pack(side="left", padx=(0, theme.PAD_S))
        self._device_choice = ctk.StringVar(value="")
        self._device_menu = ctk.CTkOptionMenu(
            topo,
            variable=self._device_choice,
            values=["(inventário vazio)"],
            width=260,
            fg_color=theme.SURFACE,
            button_color=theme.ACCENT,
            button_hover_color=theme.ACCENT_HOVER,
            text_color=theme.TEXT_PRIMARY,
        )
        self._device_menu.pack(side="left", padx=(0, theme.PAD_M))

        quiet_button(topo, "Ler do equipamento", self._read_running, width=170).pack(side="left", padx=theme.PAD_XS)
        quiet_button(topo, "Comparar", self._compare, width=110).pack(side="left", padx=theme.PAD_XS)
        quiet_button(topo, "Simular envio", self._simulate_push, width=130).pack(side="left", padx=theme.PAD_XS)
        danger_button(topo, "Enviar", self._push, width=110).pack(side="left", padx=theme.PAD_XS)

        ctk.CTkLabel(
            parent,
            text=(
                "A ordem é sempre a mesma: ler, comparar, simular, enviar. "
                "O envio guarda a configuração actual antes de escrever."
            ),
            font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(0, theme.PAD_S))

        self._push_view = MonoView(parent)
        self._push_view.grid(row=2, column=0, sticky="nsew")

    def _refresh_device_choices(self) -> None:
        nomes = [d.name for d in self.devices] or ["(inventário vazio)"]
        self._device_menu.configure(values=nomes)
        if self._device_choice.get() not in nomes:
            self._device_choice.set(nomes[0])

    def _selected_device(self) -> Device | None:
        nome = self._device_choice.get()
        for device in self.devices:
            if device.name == nome:
                return device
        self.status("Escolha um equipamento do inventário.", "aviso")
        return None

    def _read_running(self) -> None:
        device = self._selected_device()
        if device is None or not self._require_netmiko():
            return
        credenciais = self._require_credentials()
        if credenciais is None:
            return

        self.status(f"A ler {device.name}...")
        timeout = self.settings.ssh_timeout

        def trabalho() -> str:
            with SwitchSession(device, credenciais, timeout) as sessao:
                return sessao.read_running_config()

        def concluido(texto: str) -> None:
            self.current_running = texto
            self._push_view.set_text(texto)
            self.status(f"{device.name}: {len(texto.splitlines())} linhas lidas.", "ok")

        self._run_async(trabalho, concluido)

    def _compare(self) -> None:
        if not self.current_running:
            self.status("Leia primeiro a configuração do equipamento.", "aviso")
            return
        if not self._generate():
            return

        diferenca = diffing.unified(self.current_running, self.generated)
        resumo = diffing.summarise(self.current_running, self.generated)
        self._push_view.set_text(diferenca or "Sem diferenças entre o equipamento e a configuração gerada.")
        self.status(str(resumo), "aviso" if resumo.changed else "ok")

    def _simulate_push(self) -> None:
        self._do_push(dry_run=True)

    def _push(self) -> None:
        self._do_push(dry_run=False)

    def _do_push(self, dry_run: bool) -> None:
        device = self._selected_device()
        if device is None or not self._require_netmiko():
            return
        if not self._generate():
            return

        credenciais = self._require_credentials()
        if credenciais is None:
            return

        texto = self.generated
        pasta = self.settings.backup_path
        timeout = self.settings.ssh_timeout

        if not dry_run:
            from ..transport import commands_for_push

            aviso = "A configuração actual é guardada antes de escrever."
            if not device.platform.writable:
                aviso = (
                    "Este equipamento é gerido por controlador UniFi: o que for escrito "
                    "desaparece no provisionamento seguinte."
                )
            confirmado = ConfirmPushDialog(
                self, device.name, len(commands_for_push(texto)), aviso
            ).show()
            if not confirmado:
                self.status("Envio cancelado.", "info")
                return

        self.status(f"{'A simular' if dry_run else 'A enviar'} em {device.name}...")

        def trabalho() -> Any:
            with SwitchSession(device, credenciais, timeout) as sessao:
                return sessao.push(texto, pasta, dry_run=dry_run)

        def concluido(resultado: Any) -> None:
            cabecalho = [
                f"Equipamento: {resultado.device}",
                f"Backup: {resultado.backup_path}",
                f"Comandos: {len(resultado.commands)}",
                "",
            ]
            self._push_view.set_text("\n".join(cabecalho) + resultado.output)
            if resultado.dry_run:
                self.status("Simulação concluída. Nada foi escrito.", "ok")
            else:
                self.status(
                    f"Enviado para {resultado.device}."
                    + (" Gravado para arranque." if resultado.saved else ""),
                    "ok",
                )

        self._run_async(trabalho, concluido)

    # -----------------------------------------------------------------------
    # PT-PT: Separador das definições.
    # EN-UK: Settings tab.
    # -----------------------------------------------------------------------

    def _build_settings_tab(self, parent: Any) -> None:
        quadro = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        quadro.grid(row=0, column=0, sticky="nsew")
        quadro.grid_columnconfigure(0, weight=1)

        cartao = Card(quadro, "Pastas", "Nada é escrito dentro da pasta do programa.")
        cartao.grid(row=0, column=0, sticky="ew", pady=(0, theme.PAD_S))
        self.s_output = Field(cartao, "Configurações", self.settings.output_dir, width=420)
        self.s_backup = Field(cartao, "Backups", self.settings.backup_dir, width=420)
        self.s_inventory = Field(cartao, "Inventário", self.settings.inventory_path, width=420)

        cartao = Card(quadro, "Valores iniciais do formulário")
        cartao.grid(row=1, column=0, sticky="ew", pady=theme.PAD_S)
        self.s_platform = ChoiceField(
            cartao, "Plataforma", [p.label for p in Platform], value=self.settings.platform.label
        )
        self.s_domain = Field(cartao, "Domínio", self.settings.default_domain)
        self.s_ntp = Field(cartao, "NTP", ", ".join(self.settings.default_ntp))
        self.s_syslog = Field(cartao, "Syslog", ", ".join(self.settings.default_syslog))
        self.s_timezone = Field(cartao, "Fuso horário", self.settings.default_timezone)

        cartao = Card(quadro, "Rede e aparência")
        cartao.grid(row=2, column=0, sticky="ew", pady=theme.PAD_S)
        self.s_timeout = Field(cartao, "Tempo limite SSH (s)", str(self.settings.ssh_timeout))
        self.s_theme = ChoiceField(cartao, "Tema", ["system", "light", "dark"], value=self.settings.tema)

        primary_button(quadro, "Guardar definições", self._save_settings, width=180).grid(
            row=3, column=0, sticky="w", pady=theme.PAD_M
        )

    def _save_settings(self) -> None:
        self.settings.output_dir = self.s_output.get()
        self.settings.backup_dir = self.s_backup.get()
        self.settings.inventory_path = self.s_inventory.get()
        self.settings.default_platform = _PLATFORM_BY_LABEL[self.s_platform.get()].value
        self.settings.default_domain = self.s_domain.get()
        self.settings.default_ntp = _split(self.s_ntp.get())
        self.settings.default_syslog = _split(self.s_syslog.get())
        self.settings.default_timezone = self.s_timezone.get() or "WET"
        self.settings.tema = self.s_theme.get()

        timeout = self.s_timeout.get()
        self.settings.ssh_timeout = int(timeout) if timeout.isdigit() else 30

        caminho = save_settings(self.settings)
        ctk.set_appearance_mode(self.settings.tema)
        self.status(f"Definições gravadas em {caminho}", "ok")

    # -----------------------------------------------------------------------
    # PT-PT: Formulário ↔ configuração.
    # EN-UK: Form ↔ configuration.
    # -----------------------------------------------------------------------

    def _apply_defaults(self) -> None:
        """PT-PT: Põe no formulário os valores iniciais das definições."""
        self.f_domain.set(self.settings.default_domain)
        self.f_ntp.set(", ".join(self.settings.default_ntp))
        self.f_syslog.set(", ".join(self.settings.default_syslog))
        self.f_timezone.set(self.settings.default_timezone)

    def _form_to_spec(self) -> DeviceSpec:
        """
        PT-PT: Lê o formulário para uma configuração.
        EN-UK: Reads the form into a configuration.
        """
        vlan_gestao = self.f_mgmt_vlan.get()
        self.spec.platform = _PLATFORM_BY_LABEL[self.f_platform.get()]
        self.spec.management = Management(
            hostname=self.f_hostname.get(),
            mgmt_vlan=int(vlan_gestao) if vlan_gestao.isdigit() else 1,
            mgmt_ip_cidr=self.f_mgmt_ip.get(),
            gateway=self.f_gateway.get(),
            domain=self.f_domain.get(),
            dns_servers=_split(self.f_dns.get()),
        )
        self.spec.services = Services(
            ntp_servers=_split(self.f_ntp.get()),
            syslog_servers=_split(self.f_syslog.get()),
            timezone=self.f_timezone.get() or "WET",
            snmp_community=self.f_snmp.get(),
            snmp_location=self.f_snmp_local.get(),
            snmp_contact=self.f_snmp_contact.get(),
        )
        self.spec.security = Security(
            admin_user=self.f_admin.get() or "admin",
            banner=self.f_banner.get(),
            disable_telnet=self.f_telnet.get(),
            disable_http=self.f_http.get(),
            rapid_stp=self.f_rstp.get(),
        )
        self.spec.notes = self.f_notes.get()
        return self.spec

    def _spec_to_form(self) -> None:
        """
        PT-PT: Escreve a configuração no formulário.
        EN-UK: Writes the configuration into the form.
        """
        mgmt = self.spec.management
        self.f_platform.set(self.spec.platform.label)
        self.f_hostname.set(mgmt.hostname)
        self.f_mgmt_vlan.set(str(mgmt.mgmt_vlan))
        self.f_mgmt_ip.set(mgmt.mgmt_ip_cidr)
        self.f_gateway.set(mgmt.gateway)
        self.f_domain.set(mgmt.domain)
        self.f_dns.set(", ".join(mgmt.dns_servers))

        services = self.spec.services
        self.f_ntp.set(", ".join(services.ntp_servers))
        self.f_syslog.set(", ".join(services.syslog_servers))
        self.f_timezone.set(services.timezone)
        self.f_snmp.set(services.snmp_community)
        self.f_snmp_local.set(services.snmp_location)
        self.f_snmp_contact.set(services.snmp_contact)

        security = self.spec.security
        self.f_admin.set(security.admin_user)
        self.f_banner.set(security.banner)
        self.f_telnet.set(security.disable_telnet)
        self.f_http.set(security.disable_http)
        self.f_rstp.set(security.rapid_stp)

        self.f_notes.set(self.spec.notes)
        self._refresh_vlans()
        self._refresh_ports()

    def _generate(self) -> bool:
        """
        PT-PT: Valida e gera. Devolve False se houver erros — nesse caso a
               pré-visualização fica com o que estava e a lista mostra porquê.
        EN-UK: Validates and generates. Returns False when there are errors — in
               which case the preview keeps what it had and the list says why.
        """
        spec = self._form_to_spec()
        problemas = validate(spec)

        if problemas:
            self._issues.set_text("\n".join(str(p) for p in problemas))
        else:
            self._issues.set_text("Sem problemas.")

        if has_errors(problemas):
            erros = sum(1 for p in problemas if p.severity is Severity.ERROR)
            self.status(f"{_plural(erros, 'erro', 'erros')} por corrigir antes de gerar.", "erro")
            return False

        self.generated = get_generator(spec.platform).generate(spec, problemas)
        self._preview.set_text(self.generated)
        avisos = len(problemas)
        self.status(
            "Configuração gerada."
            + (f" {_plural(avisos, 'aviso', 'avisos')}." if avisos else ""),
            "aviso" if avisos else "ok",
        )
        return True

    def _save_config(self) -> None:
        if not self._generate():
            return
        nome = self.spec.management.hostname or "configuracao"
        caminho = filedialog.asksaveasfilename(
            title="Guardar configuração",
            initialdir=str(self.settings.output_path),
            initialfile=f"{nome}-{self.spec.platform.value}.cfg",
            defaultextension=".cfg",
            filetypes=[("Configuração", "*.cfg *.txt"), ("Todos", "*.*")],
        )
        if not caminho:
            return
        destino = Path(caminho)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(self.generated, encoding="utf-8")
        self.status(f"Configuração escrita em {destino}", "ok")

    def _save_profile(self) -> None:
        spec = self._form_to_spec()
        caminho = filedialog.asksaveasfilename(
            title="Guardar perfil",
            initialdir=str(self.settings.output_path),
            initialfile=f"{spec.management.hostname or 'perfil'}.json",
            defaultextension=".json",
            filetypes=[("Perfil", "*.json")],
        )
        if not caminho:
            return
        destino = specfile.save(spec, Path(caminho))
        self.status(f"Perfil gravado em {destino}", "ok")

    def _open_profile(self) -> None:
        caminho = filedialog.askopenfilename(
            title="Abrir perfil", filetypes=[("Perfil", "*.json"), ("Todos", "*.*")]
        )
        if not caminho:
            return
        try:
            self.spec = specfile.load(Path(caminho))
        except specfile.SpecFileError as exc:
            self.status(str(exc), "erro")
            return
        self._spec_to_form()
        self.status(f"Perfil aberto: {Path(caminho).name}", "ok")

    # -----------------------------------------------------------------------
    # PT-PT: Utilitários.
    # EN-UK: Utilities.
    # -----------------------------------------------------------------------

    def _require_netmiko(self) -> bool:
        if netmiko_available():
            return True
        self.status(
            "O netmiko não está instalado; a leitura e o envio ficam indisponíveis. "
            "Instale com: pip install netmiko",
            "erro",
        )
        return False

    def _require_credentials(self) -> Credentials | None:
        if self.credentials is not None:
            return self.credentials
        self.credentials = CredentialsDialog(self).show()
        if self.credentials is None:
            self.status("Sem credenciais não é possível falar com o equipamento.", "aviso")
        return self.credentials

    def _run_async(self, work: Callable[[], Any], on_done: Callable[[Any], None]) -> None:
        """
        PT-PT: Corre `work` noutra linha de execução e entrega o resultado a
               `on_done` já na linha da interface.

               O Tk não é seguro fora da sua própria linha de execução: tocar
               num widget a partir da thread de trabalho produz falhas
               esporádicas e impossíveis de reproduzir. Daí o `after(0, ...)`.

        EN-UK: Runs `work` on another thread and hands the result to `on_done`
               back on the interface thread.

               Tk is not safe outside its own thread: touching a widget from the
               worker thread produces sporadic, unreproducible failures. Hence
               the `after(0, ...)`.

        :param work:
            PT-PT: O que fazer em segundo plano. / EN-UK: What to do in the background.
        :param on_done:
            PT-PT: O que fazer com o resultado. / EN-UK: What to do with the result.
        """

        def envolver() -> None:
            # PT-PT: A mensagem é lida já, e não dentro do lambda. O Python
            #        apaga o nome da excepção no fim do `except`, e o lambda só
            #        corre depois — lá dentro, `exc` já não existiria.
            # EN-UK: The message is read now, not inside the lambda. Python
            #        deletes the exception name at the end of the `except`, and
            #        the lambda only runs later — by then `exc` would be gone.
            try:
                resultado = work()
            except TransportError as exc:
                mensagem = str(exc)
                self.after(0, lambda: self.status(mensagem, "erro"))
                return
            except Exception as exc:  # noqa: BLE001 - PT-PT: a thread não deve morrer em silêncio
                logger.exception("Falha em segundo plano")
                mensagem = f"Falhou: {exc}"
                self.after(0, lambda: self.status(mensagem, "erro"))
                return
            self.after(0, lambda: on_done(resultado))

        threading.Thread(target=envolver, daemon=True).start()


def _port_summary(interface: Interface) -> str:
    """PT-PT: Resumo de uma porta para a lista. / EN-UK: One-line port summary for the list."""
    if interface.mode is PortMode.DISABLED:
        return "desactivada"

    partes = [interface.mode.label]
    if interface.mode is PortMode.ACCESS:
        partes.append(f"VLAN {interface.access_vlan}")
        if interface.voice_vlan is not None:
            partes.append(f"voz {interface.voice_vlan}")
    else:
        if interface.native_vlan is not None:
            partes.append(f"nativa {interface.native_vlan}")
        if interface.tagged_vlans:
            partes.append("marcadas " + ",".join(str(v) for v in interface.tagged_vlans))

    partes.append("PoE" if interface.poe else "sem PoE")
    if not interface.enabled:
        partes.append("em baixo")
    if interface.description:
        partes.append(f"— {interface.description}")
    return "  ·  ".join(partes)


def _plural(count: int, singular: str, plural: str) -> str:
    """
    PT-PT: "1 aviso" e não "1 avisos". Uma barra de estado que erra a
           concordância dá a impressão de que ninguém olhou para ela.
    EN-UK: "1 aviso" rather than "1 avisos". A status bar that gets agreement
           wrong gives the impression nobody looked at it.
    """
    return f"{count} {singular if count == 1 else plural}"


def _split(text: str) -> list[str]:
    """PT-PT: Separa uma lista escrita com vírgulas. / EN-UK: Splits a comma-written list."""
    return [part.strip() for part in text.replace(";", ",").split(",") if part.strip()]


def run(settings: Settings) -> None:
    """
    PT-PT: Abre a janela e entrega o controlo ao Tk.

    EN-UK: Opens the window and hands control to Tk.

    :param settings:
        PT-PT: Definições em vigor. / EN-UK: The settings in force.
    """
    app = App(settings)
    app.mainloop()
