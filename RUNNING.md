# Rodando o Service Monitoring Host

Guia completo para executar e gerenciar o Service Monitoring Host.

---

## 1. Pre-requisitos

### 1.1 Python 3.12+

```bash
python3 --version
# Expects: Python 3.12.x ou superior
```

Se nao estiver instalado:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

### 1.2 Docker + Docker Compose

```bash
docker --version
# Expects: Docker version 24.x ou superior

docker compose version
# Expects: Docker Compose version v2.x.x
```

Se nao estiver instalado:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
# Fazer logout/login apos o usermod para usar docker sem sudo
```

### 1.3 Verificacao rapida

```bash
# Todos esses comandos devem retornar versao, sem erro
python3 --version
docker --version
docker compose version
```

---

## 2. Instalacao Automatica

O script `install.sh` faz tudo: instala dependencias, cria venv, deploy dos containers, instala systemd service.

```bash
git clone <repo-url>
cd service-monitoring

chmod +x scripts/install.sh
./scripts/install.sh
```

O que o install.sh faz:

1. Instala Python3, Docker, docker-compose, rsync
2. Prepara e inicia o Docker via systemd
3. Copia o projeto para `/opt/service-monitoring`
4. Cria virtualenv e instala PyYAML
5. Deploy dos containers via `ports_check.py` (com resolucao de portas)
6. Instala e inicia o systemd service `service-monitoring.service`

---

## 3. Execucao Manual (Desenvolvimento)

### 3.1 Preparar ambiente

```bash
# Entrar no diretorio do projeto
cd service-monitoring

# Criar virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.2 Levantar containers alvo

Os containers sao os servicos que o Host vai monitorar. Precisam estar rodando antes de iniciar o monitoramento.

```bash
# Deploy com resolucao automatica de conflitos de porta
python scripts/ports_check.py -f docker-compose.yaml -v
```

O `ports_check.py` faz tres coisas:

1. Detecta portas ocupadas e reatribui automaticamente
2. Atualiza o `docker-compose.yaml` com as novas portas
3. **Sincroniza o `app/config/services.json`** com as portas reais

Isso e essencial — sem sincronizacao, o monitoramento tenta checar portas erradas e todos os health checks falham.

> **Sem conflito de portas?** Se todas as portas originais estiverem livres, o script mantem as portas padrao e nao altera nada.

### 3.3 Verificar containers

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Saida esperada (portas podem variar se houve reatribuicao):

```
NAMES               STATUS          PORTS
monitor-redis       Up X minutes    0.0.0.0:6379->6379/tcp
monitor-postgres    Up X minutes    0.0.0.0:5432->5432/tcp
monitor-nginx       Up X minutes    0.0.0.0:8080->80/tcp
monitor-whoami      Up X minutes    0.0.0.0:8081->80/tcp
monitor-mock-api    Up X minutes    0.0.0.0:3000->3000/tcp
monitor-idle-worker Up X minutes
```

Se as portas foram reatribuidas, verifique o `services.json` para confirmar a sincronizacao:

```bash
grep -E '"port"|"url"' app/config/services.json
```

### 3.4 Iniciar o Host

```bash
# Com a virtualenv ativa
python -m app.main
```

### 3.5 O que observar nos logs

A saida segue o formato:

```
2026-07-20 10:00:00 | INFO     | Initializing Host...
2026-07-20 10:00:00 | INFO     | Creating service type: docker
2026-07-20 10:00:00 | INFO     | Instance name: redis
2026-07-20 10:00:00 | INFO     | Creating service type: docker
2026-07-20 10:00:00 | INFO     | Instance name: postgres
...
2026-07-20 10:00:00 | INFO     | 6 services registered.
2026-07-20 10:00:00 | INFO     | Starting services...
2026-07-20 10:00:01 | INFO     | All services started.
2026-07-20 10:00:01 | INFO     | HealthMonitor started.
2026-07-20 10:00:01 | INFO     | Linux Service Host is running.

2026-07-20 10:00:06 | INFO     | [HEALTH] redis -> HEALTHY
2026-07-20 10:00:06 | INFO     | [HEALTH] postgres -> HEALTHY
2026-07-20 10:00:06 | INFO     | [HEALTH] nginx -> HEALTHY
2026-07-20 10:00:06 | INFO     | [HEALTH] whoami -> HEALTHY
2026-07-20 10:00:06 | INFO     | [HEALTH] mock-api -> HEALTHY
2026-07-20 10:00:06 | INFO     | [HEALTH] idle-worker -> HEALTHY
```

### 3.6 Observar o ciclo de recuperacao

Para testar a recuperacao, pare um container manualmente em outro terminal:

```bash
# Em outro terminal
docker stop monitor-redis
```

Nos logs do Host, observe o ciclo:

```
2026-07-20 10:05:10 | WARNING  | [HEALTH] redis -> FAILED
2026-07-20 10:05:10 | WARNING  | [redis] Recovery attempt 1/3
2026-07-20 10:05:12 | INFO     | [redis] Container restarted successfully.
2026-07-20 10:05:12 | INFO     | [redis] Recovered successfully.
```

Se o container nao voltar apos 3 tentativas, o circuit breaker abre:

```
2026-07-20 10:05:30 | CRITICAL | [redis] Circuit breaker OPEN — 3 consecutive failures. Manual intervention required.
```

### 3.7 Parar a aplicacao

Pressione `Ctrl+C` no terminal onde o Host esta rodando:

```
2026-07-20 10:10:00 | INFO     | KeyboardInterrupt received.
2026-07-20 10:10:00 | INFO     | Stopping Host...
2026-07-20 10:10:00 | INFO     | HealthMonitor stopped.
2026-07-20 10:10:00 | INFO     | Host stopped.
```

---

## 4. Execucao via Systemd (Producao)

### 4.1 Servicos do systemd

Apos rodar o `install.sh`, o servico esta disponivel:

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

# Ultimas 50 linhas
sudo journalctl -u service-monitoring -n 50 --no-pager

# Logs desde o ultimo boot
sudo journalctl -u service-monitoring -b --no-pager
```

---

## 5. Comandos Uteis

### Gerenciamento de containers

```bash
# Listar containers do projeto
docker ps --filter "name=monitor-"

# Parar todos os containers do projeto
docker stop $(docker ps --filter "name=monitor-" -q)

# Remover todos os containers do projeto
docker compose down

# Verificar logs de um container
docker logs monitor-redis
docker logs monitor-nginx --tail 20
```

### Debug

```bash
# Verificar se as portas estao ocupadas
python scripts/ports_check.py -f docker-compose.yaml -v

# Sincronizar services.json manualmente
python scripts/ports_check.py -f docker-compose.yaml -s app/config/services.json -v

# Testar se o mock-api responde
curl http://127.0.0.1:3000/health
# Expects: {"status":"ok"}

# Testar se o nginx responde
curl http://127.0.0.1:8080/
# Expects: HTML do nginx
```

### Reinstalacao completa

```bash
# Parar e limpar tudo
sudo systemctl stop service-monitoring || true
sudo systemctl disable service-monitoring || true
docker compose down
sudo rm -rf /opt/service-monitoring

# Reinstalar
./scripts/install.sh
```

---

## 6. Troubleshooting

| Problema | Solucao |
|---|---|
| `ModuleNotFoundError: No module named 'yaml'` | `pip install PyYAML` na virtualenv ativa |
| `docker: permission denied` | `sudo usermod -aG docker $USER` + logout/login |
| Containers nao sobem (porta em uso) | `python scripts/ports_check.py -f docker-compose.yaml -v` |
| `python -m app.main` nao encontra `services.json` | Verificar que esta no diretorio raiz do projeto |
| Service systemd falha ao iniciar | `sudo journalctl -u service-monitoring -n 50` |
| Health check retorna FAILED para todos | Verificar se containers estao rodando: `docker ps` |
| Circuit breaker abre e nao recupera | `docker start <container-name>` manualmente |
