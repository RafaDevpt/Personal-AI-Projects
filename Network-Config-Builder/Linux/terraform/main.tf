# Created by Redfox using Claude
#
# PT-PT: Exemplo de como correr o Network-Config-Builder com Terraform e Docker. O Terraform
#        constrói a imagem a partir de ../Dockerfile e cria um contentor com o
#        comando, a pasta de dados e a rede definidos em variables.tf. O
#        contentor corre uma vez e pára; para voltar a correr com a mesma
#        configuração: `docker start -a network-config-builder`. Nenhum segredo vai para estes
#        ficheiros nem para o estado: passam-se em TF_VAR_ambiente ou pelo
#        terminal.
#
# EN-UK: Example of running Network-Config-Builder with Terraform and Docker. Terraform builds
#        the image from ../Dockerfile and creates a container with the
#        command, data folder and network set in variables.tf. The container
#        runs once and stops; to run it again with the same configuration:
#        `docker start -a network-config-builder`. No secret goes into these files or the
#        state file by design: pass them through TF_VAR_ambiente or the
#        terminal.

terraform {
  required_version = ">= 1.6"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {
  host = var.docker_host
}

locals {
  contexto = abspath("${path.module}/..")
  # PT-PT: a imagem só é reconstruída quando o código ou as dependências mudam.
  # EN-UK: the image is rebuilt only when the code or dependencies change.
  impressao = sha1(join("", concat(
    [for f in sort(fileset(local.contexto, "src/**")) : filesha1("${local.contexto}/${f}") if !strcontains(f, "__pycache__")],
    [filesha1("${local.contexto}/requirements.txt"), filesha1("${local.contexto}/Dockerfile")],
  )))
}

resource "docker_image" "app" {
  name = "local/network-config-builder:${substr(local.impressao, 0, 12)}"

  build {
    context = local.contexto
  }

  triggers = {
    impressao = local.impressao
  }
}

resource "docker_container" "app" {
  name         = "network-config-builder"
  image        = docker_image.app.image_id
  command      = var.comando
  network_mode = var.rede
  user         = var.utilizador
  env          = [for k, v in var.ambiente : "${k}=${v}"]

  # PT-PT: corre e sai; o Terraform não o volta a arrancar.
  # EN-UK: runs and exits; Terraform does not restart it.
  must_run = false
  restart  = "no"

  read_only     = true
  security_opts = ["no-new-privileges:true"]
  capabilities {
    drop = ["ALL"]
  }
  tmpfs = { "/tmp" = "rw,noexec,nosuid,size=64m" }

  volumes {
    host_path      = abspath(var.pasta_dados)
    container_path = "/dados"
  }
}
