# Rodando o Service Monitoring Host

Guia completo para executar e gerenciar o Service Monitoring Host.

---

## 1. Pré-requisitos

### 1.1 Python 3.12+

```bash
python3 --version
# Esperado: Python 3.12.x ou superior
```

Se não estiver instalado:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

### 1.2 Container Runtime

O monitor funciona com Podman **ou** Docker.

**Podman (recomendado para produção):**

```bash
sudo apt install podman podman-compose
podman --version
podman-compose --version
```

**Docker (alternativa):**

```bash
sudo apt install docker.io docker-compose-v2
sudo usermod -aG docker $USER
# Faça logout/login após o usermod
```

### 1.3 Verificação rápida

```bash
python3 --version
podman --version   # ou docker --version
podman-compose --version   # ou docker compose version
```

---

## 2. Instalação Automática

O script `install.sh` detecta automaticamente se Podman ou Docker está instalado, instala dependências, cria venv, faz deploy dos containers e instala o systemd service.

```bash
git clone <repo-url>
cd service-monitoring

chmod +x scripts/install.sh
./scripts/install.sh
```

O que o `install.sh` faz:

1. Detecta Podman ou Docker (prioriza Podman se ambos estiverem presentes)
2. Instala Python3, rsync e o runtime escolhido (se necessário)
3. Prepara e inicia o runtime via systemd
4. Copia o projeto para `/opt/service-monitoring`
5. Cria virtualenv e instala PyYAML
6. Deploy dos containers via `ports_check.py` (com resolução automática de portas)
7. Instala e inicia o systemd service `service-monitoring.service`

---

## 3. Execução Manual (Desenvolvimento)

### 3.1 Preparar ambiente

```bash
cd service-monitoring

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### 3.2 Usando com seus próprios serviços

O repositório já vem com um `services.json` configurado para os serviços de produção. Para testar com seus próprios serviços:

```bash
# Crie seu compose file (ex: docker-compose.yaml)
# Crie seu services.json a partir do template
cp app/config/services.example.json app/config/services.json
# Edite services.json com seus serviços
```

Veja [CONFIGURATION.md](CONFIGURATION.md) para referência completa do schema.

### 3.3 Levantar containers alvo

Os containers precisam estar rodando antes de iniciar o monitoramento.

```bash
# Deploy com resolução automática de conflitos de porta
python scripts/ports_check.py -f podman-compose.yaml -v
```

O `ports_check.py` faz três coisas:

1. Detecta portas ocupadas e reatribui automaticamente
2. Atualiza o compose file com as novas portas
3. **Sincroniza o `app/config/services.json`** com as portas reais

Se preferir usar docker-compose diretamente:

```bash
# Com Docker
docker compose -f docker-compose.yaml up -d

# Com Podman
podman-compose -f podman-compose.yaml up -d
```

### 3.4 Verificar containers

```bash
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Saída esperada para os serviços de produção (exemplo):

```
NAMES               STATUS          PORTS
redis               Up X minutes    0.0.0.0:6379->6379/tcp
whisper             Up X minutes    0.0.0.0:10023->8000/tcp
kokoro-tts          Up X minutes    0.0.0.0:8300->8300/tcp
livekit-agents      Up X minutes
front               Up X minutes
apache              Up X minutes    0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
local-api           Up X minutes    0.0.0.0:55185->3000/tcp
rag_api             Up X minutes    0.0.0.0:8023->8023/tcp
rag_worker          Up X minutes
rag_qdrant          Up X minutes    0.0.0.0:6333->6333/tcp, 0.0.0.0:6334->6334/tcp
rag_phoenix         Up X minutes    0.0.0.0:6006->6006/tcp
rag_postgres        Up X minutes    0.0.0.0:5432->5432/tcp
```

> Se as portas foram reatribuídas pelo `ports_check.py`, verifique o `services.json` para confirmar a sincronização:
> ```bash
> grep -E '"port"|"url"' app/config/services.json
> ```

### 3.5 Iniciar o Host

```bash
python -m app.main
```

### 3.6 O que observar nos logs

```
2026-07-21 10:00:00 | INFO     | Initializing Host...
2026-07-21 10:00:00 | INFO     | Creating service type: docker
2026-07-21 10:00:00 | INFO     | Instance name: redis
...
2026-07-21 10:00:00 | INFO     | 12 services registered.
2026-07-21 10:00:00 | INFO     | Starting services...
2026-07-21 10:00:01 | INFO     | All services started.
2026-07-21 10:00:01 | INFO     | HealthMonitor started.
2026-07-21 10:00:01 | INFO     | Linux Service Host is running.

2026-07-21 10:00:06 | INFO     | [HEALTH] redis -> HEALTHY
2026-07-21 10:00:06 | INFO     | [HEALTH] whisper -> HEALTHY
2026-07-21 10:00:06 | INFO     | [HEALTH] rag_api -> HEALTHY
```

### 3.7 Ciclo de recuperação

Para testar, pare um container manualmente em outro terminal:

```bash
podman stop redis
```

Nos logs do monitor:

```
2026-07-21 10:05:10 | WARNING  | [HEALTH] redis -> FAILED
2026-07-21 10:05:10 | WARNING  | [redis] Recovery attempt 1/3
2026-07-21 10:05:12 | INFO     | [redis] Container restarted and healthy.
2026-07-21 10:05:12 | INFO     | [redis] Recovered successfully.
```

Se o container não voltar após 3 tentativas, o circuit breaker abre:

```
2026-07-21 10:05:30 | CRITICAL | [redis] Circuit breaker OPEN — 3 consecutive failures. Escalating to compose-level recovery.
```

### 3.8 Parar a aplicação

Pressione `Ctrl+C` no terminal onde o Host está rodando:

```
2026-07-21 10:10:00 | INFO     | KeyboardInterrupt received.
2026-07-21 10:10:00 | INFO     | Stopping Host...
2026-07-21 10:10:00 | INFO     | HealthMonitor stopped.
2026-07-21 10:10:00 | INFO     | Host stopped.
```

---

## 4. Execução via Systemd (Produção)

### 4.1 Serviço systemd

Após rodar o `install.sh`, o serviço está disponível:

```bash
# Status
sudo systemctl status service-monitoring

# Iniciar
sudo systemctl start service-monitoring

# Parar
sudo systemctl stop service-monitoring

# Reiniciar
sudo systemctl restart service-monitoring

# Habilitar no boot
sudo systemctl enable service-monitoring
```

### 4.2 Visualizar logs em tempo real

```bash
# Logs em tempo real (follow)
sudo journalctl -u service-monitoring -f

# Últimas 50 linhas
sudo journalctl -u service-monitoring -n 50 --no-pager

# Logs desde o último boot
sudo journalctl -u service-monitoring -b --no-pager
```

---

## 5. Comandos Úteis

### Gerenciamento de containers (substitua `podman` por `docker` se necessário)

```bash
# Listar containers do projeto
podman ps --filter "name=rag_"

# Parar todos os containers
podman stop $(podman ps -q)

# Ver logs de um container
podman logs redis
podman logs rag_api --tail 20
```

### Debug

```bash
# Verificar se as portas estão ocupadas
python scripts/ports_check.py -f podman-compose.yaml -v

# Sincronizar services.json manualmente
python scripts/ports_check.py -f podman-compose.yaml -s app/config/services.json -v

# Testar health endpoints manualmente
curl http://127.0.0.1:8023/health
curl http://127.0.0.1:6006/
```

### Reinstalação completa

```bash
sudo systemctl stop service-monitoring || true
sudo systemctl disable service-monitoring || true
podman-compose down
sudo rm -rf /opt/service-monitoring

./scripts/install.sh
```

---

## 6. Troubleshooting

| Problema | Solução |
|---|---|
| `ModuleNotFoundError: No module named 'yaml'` | `pip install PyYAML` na virtualenv ativa |
| `podman info` ou `docker info` falha | `sudo systemctl start podman.socket` (ou `docker`) |
| Podman rootless não encontra containers | Verificar se systemd service roda como root (`User=root` no service) |
| Containers não sobem (porta em uso) | `python scripts/ports_check.py -f podman-compose.yaml -v` |
| `python -m app.main` não encontra `services.json` | Verificar que está no diretório raiz do projeto |
| Service systemd falha ao iniciar | `sudo journalctl -u service-monitoring -n 50` |
| Health check retorna FAILED para todos | Verificar se containers estão rodando: `podman ps` |
| Circuit breaker abre e não recupera | `podman start <container-name>` manualmente e investigue a causa |
| Erro "No docker-compose or podman-compose found" | Instalar `podman-compose` ou `docker compose plugin` |
