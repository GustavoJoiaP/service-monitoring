# Service Monitoring Host

POC de um Linux Service Host desenvolvido em Python.

## Funcionalidades

- Registro dinâmico de serviços
- Monitoramento de saúde
- Reinício automático
- Monitoramento de processos Linux
- Execução de Workers externos
- Arquitetura baseada em Host

## Requisitos

- Python 3.12+
- Podman
- Podman Compose

## Instalação

```bash
git clone <repo>

cd service-monitoring

chmod +x scripts/install.sh

./scripts/install.sh
```

## Executar manualmente

```bash
source .venv/bin/activate

python -m app.main
```