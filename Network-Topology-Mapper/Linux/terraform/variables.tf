# Created by Redfox using Claude

variable "docker_host" {
  description = "Endereço do Docker / Docker endpoint"
  type        = string
  default     = "unix:///var/run/docker.sock"
}

variable "pasta_dados" {
  description = "Pasta do anfitrião montada em /dados (entradas, saídas, configuração) / Host folder mounted at /dados (inputs, outputs, configuration)"
  type        = string
  default     = "./dados"
}

variable "comando" {
  description = "Argumentos passados à aplicação / Arguments passed to the application"
  type        = list(string)
  default     = ["--diagnostico"]
}

variable "utilizador" {
  description = "uid:gid com que corre, para poder escrever na pasta de dados; usar $(id -u):$(id -g) / uid:gid to run as, so it can write to the data folder; use $(id -u):$(id -g)"
  type        = string
  default     = null
}

variable "rede" {
  description = "Rede do contentor: bridge, host ou none / Container network: bridge, host or none"
  type        = string
  default     = "host"
}

variable "ambiente" {
  description = "Variáveis de ambiente, por exemplo segredos; passar com TF_VAR_ambiente / Environment variables, e.g. secrets; pass with TF_VAR_ambiente"
  type        = map(string)
  default     = {}
  sensitive   = true
}
