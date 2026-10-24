# Changelog

<!-- Created by Redfox using Claude -->

## [0.2.0] — 2026-10-24

Bastidores, vários edifícios e o editor de plantas.

### Acrescentado
- **Ecrã de arranque** com um cartão por edifício (miniatura da planta, pisos, salas, bastidores, equipamentos, erros). Um clique abre logo o edifício completo; menus de edifício e piso na barra de topo.
- **Vários edifícios** por projeto (`edificios: [...]`), com cabos entre edifícios a sair pela fachada mais próxima e etiqueta clicável.
- **Bastidores** posicionados por edifício/piso/sala, à escala real (largura, profundidade, altura em U), com **vista de bastidor** em 3D: numeração de U, coluna de etiquetas, intervalos livres, vizinhos da mesma sala.
- **Máquinas no bastidor** (switch, router, firewall, servidor, storage, UPS, patch panel, organizador, PDU, KVM, prateleira, outro), cada uma com modelo 3D próprio; adicionar, editar, retirar e mover bastidores na própria interface. Uma máquina ligada a um equipamento de rede assume a sua posição e cor.
- Verificações **B03–B08**: máquinas sobrepostas, fora do bastidor, ligadas a equipamento desconhecido, o mesmo equipamento montado duas vezes, bastidor fora da sala, conflitos de posição. Agora 30 verificações.
- **Editor de edifícios** com importação de plantas de **imagem, PDF e DXF**: calibração de escala, origem comum, deteção automática de todas as salas e do contorno (texto e arcos de porta ignorados), varinha mágica, retângulo/polígono, edição de vértices com encaixe, modo ortogonal, duplicar piso, pré-visualização 3D em direto.
- Contorno de edifício a partir do **OpenStreetMap** (com número de pisos quando o OSM o sabe).
- Gráficos mais detalhados: iluminação de estúdio, sombras, *bloom* nos LEDs, planta original como textura do piso, paredes de vidro, calhas de teto e prumadas.
- Exemplo com dois edifícios, sala de servidores e cinco bastidores.

### Alterado
- O campo `edificio` (um só ficheiro) continua a ler-se e passa a `edificios` ao gravar.
- Os testes de JavaScript correm com `node --test "tests/js/*.test.mjs"`.

## [0.1.0] — 2026-10-24

Primeira versão.

### Acrescentado
- Gémeo digital que cruza o mapa do **Network Topology Mapper** (exportação JSON, formato 1) com os perfis do **Network Config Builder** e com um edifício em `edificio.json`.
- Motor de validação com 24 verificações em 8 famílias (ligações, VLANs, portas, PoE, redundância, equipamentos, edifício, importadas do mapper), cada uma com correcção sugerida.
- Vista **lógica** (camadas borda → core → distribuição → acesso → APs) e vista **edifício** (pisos empilhados, salas, isolamento de piso, afastamento de pisos).
- Cabos coloridos pela pior constatação; tracejado para cabos desenhados e não encontrados; animação de tráfego.
- Posicionamento de equipamentos por piso/sala na própria interface, gravado no projeto.
- Exportações CSV (constatações e lista de cabos) prontas para Excel.
- Modo sem janela: `--validar`, `--cena`, `--csv-constatacoes`, `--csv-cabos`.
- Hotel de exemplo com dados sintéticos e erros plantados.
