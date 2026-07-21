# Service Monitoring Host

Framework em Python para monitoramento de health-check de containers (Docker/Podman) com recuperação automática (circuit breaker) e deploy via systemd.

> **Aviso:** Os arquivos `services.json` e `podman-compose.yaml` neste repositório são exemplos reais de produção. Para monitorar seus próprios serviços, veja o guia de configuração em [CONFIGURATION.md](CONFIGURATION.md).

## Funcionalidades

- Monitoramento de containers via 3 tipos de check: `container_state`, `tcp`, `http`
- Runtime configurável por serviço: Podman **ou** Docker
- Recuperação automática com circuit breaker (N tentativas individuais → compose-level recovery)
- Cooldown entre tentativas para evitar flood de restart
- Serviço systemd para produção (auto-restart em falhas)
- Suporte a workers de processo Linux
- Serviços internos para teste: Heartbeat, Counter, FaultyService

## Quick Start

```bash
# 1. Clone
git clone <repo> && cd service-monitoring

# 2. Crie seu arquivo de serviços (copia do template)
cp app/config/services.example.json app/config/services.json

# 3. Crie um docker-compose.yaml ou podman-compose.yaml com os containers a monitorar
#    (veja CONFIGURATION.md para exemplos)

# 4. Instale dependências
pip install -r requirements.txt

# 5. Rode o monitor
python -m app.main
```

## Pré-requisitos

- Python 3.12+
- Podman **ou** Docker (com suporte a compose)

Instalação rápida no Ubuntu:

```bash
# Podman (recomendado para produção)
sudo apt install podman podman-compose

# Docker (alternativa)
sudo apt install docker.io docker-compose-v2
```

## Documentação

| Documento | Público | Conteúdo |
|---|---|---|
| [CONFIGURATION.md](CONFIGURATION.md) | Desenvolvedores | Schema do `services.json`, tipos de check, runtime, exemplos |
| [RUNNING.md](RUNNING.md) | Operadores | Instalação, systemd, logs, troubleshooting |
| [Linux_Service_Host_Architecture.md](Linux_Service_Host_Architecture.md) | Contribuidores | Arquitetura interna, componentes, fluxos |

## Licença

MIT
