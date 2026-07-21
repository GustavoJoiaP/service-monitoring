# Configuration Guide

Guia de configuração do Service Monitoring Host para monitorar seus próprios containers.

## Visão Geral

O monitor precisa de dois arquivos:

1. **Compose file** (`docker-compose.yaml` ou `podman-compose.yaml`): define os containers que serão executados.
2. **`services.json`**: diz ao monitor quais containers existem e como verificar se estão saudáveis.

> O `container_name` no compose DEVE ser igual ao `container_name` no `services.json`. É assim que o monitor encontra o container no runtime.

---

## 1. Estrutura do services.json

```json
{
    "compose": {
        "file": "podman-compose.yaml"
    },
    "services": [
        {
            "name": "meu-servico",
            "type": "docker",
            "enabled": true,
            "runtime": "podman",
            "container_name": "meu-container",
            "check": "tcp",
            "host": "127.0.0.1",
            "port": 6379,
            "timeout": 5
        }
    ]
}
```

### Campos

| Campo | Obrigatório | Tipo | Default | Descrição |
|---|---|---|---|---|
| `name` | sim | string | — | Nome lógico exibido nos logs |
| `type` | sim | string | — | Sempre `"docker"` para containers |
| `enabled` | não | bool | `true` | Se `false`, o serviço é ignorado na inicialização |
| `runtime` | não | string | `"docker"` | Binário do container: `"podman"` ou `"docker"` |
| `container_name` | sim | string | — | Deve ser **exatamente** o nome do container no runtime |
| `check` | não | string | `"container_state"` | Tipo de health check (ver seção 2) |
| `host` | depende | string | `"127.0.0.1"` | Obrigatório para check `tcp` |
| `port` | depende | int | — | Obrigatório para check `tcp` |
| `url` | depende | string | — | Obrigatório para check `http` |
| `expected_status` | não | int | `200` | Status HTTP esperado (check `http`) |
| `timeout` | não | int | `5` | Timeout em segundos para conexões |

### Chave `compose` (opcional)

Usada apenas para **recuperação em nível de compose** (último estágio do circuit breaker).

```json
{
    "compose": {
        "file": "podman-compose.yaml"
    }
}
```

O caminho do arquivo é resolvido relativamente à raiz do projeto. Se omitido, o circuit breaker não tentará compose-level recovery (apenas restart individual).

---

## 2. Tipos de Check

### `container_state`

Verifica se o container está no estado `running` usando `{runtime} inspect`.

**Quando usar:** Serviços que não expõem porta (workers, agents, serviços internos, filas).

```json
{
    "name": "meu-worker",
    "type": "docker",
    "runtime": "podman",
    "container_name": "worker",
    "check": "container_state"
}
```

**Exemplo real:** `livekit-agents`, `rag_worker`, `front` (quando não expõe porta externa).

### `tcp`

Tenta abrir conexão TCP no `host:port`. Timeout padrão: 5s.

**Quando usar:** Bancos de dados, Redis, Qdrant, qualquer serviço que escute em porta TCP mas não tenha HTTP.

```json
{
    "name": "meu-redis",
    "type": "docker",
    "runtime": "podman",
    "container_name": "redis",
    "check": "tcp",
    "host": "127.0.0.1",
    "port": 6379
}
```

**Exemplos reais:**
- Redis → porta `6379`
- PostgreSQL → porta `5432`
- Qdrant → porta `6333`

### `http`

Faz requisição HTTP GET na `url` e valida o `expected_status`.

**Quando usar:** APIs REST, frontends, serviços com health endpoint.

```json
{
    "name": "minha-api",
    "type": "docker",
    "runtime": "podman",
    "container_name": "api",
    "check": "http",
    "url": "http://127.0.0.1:8080/health",
    "expected_status": 200,
    "timeout": 5
}
```

**Exemplos reais:**
- Whisper → `http://127.0.0.1:10023/v1/models`
- Kokoro TTS → `http://127.0.0.1:8300/health`
- Apache → `http://127.0.0.1:80/`

---

## 3. Runtime: Podman vs Docker

O campo `runtime` controla qual binário é usado para os comandos de container:

| Runtime | `container_state` / restart | Exemplo de uso |
|---|---|---|
| `"podman"` | `podman ps`, `podman inspect`, `podman restart` | Produção com Podman |
| `"docker"` | `docker ps`, `docker inspect`, `docker restart` | Desenvolvimento local |

**Importante:** O runtime é **por serviço**. Você pode ter serviços com `"runtime": "podman"` e `"runtime": "docker"" no mesmo arquivo, desde que ambos os runtimes estejam instalados.

### Resolução do Compose

O `compose_utils.py` detecta automaticamente o binário de compose disponível, nesta ordem:

1. `podman compose` (plugin nativo do Podman)
2. `docker compose` (plugin nativo do Docker)
3. `docker-compose` (standalone)
4. `podman-compose` (standalone)

Isso é independente do `runtime` configurado no serviço.

---

## 4. Estratégia de Recuperação

O `RecoveryManager` segue este fluxo para cada serviço com falha:

```
Falha detectada no health check
    ↓
Cooldown de 30s desde a última tentativa?
    ├── Sim → ignora (evita flood de restart)
    └── Não → prossegue
    ↓
Já tentou 3 vezes?
    ├── Não → executa {runtime} restart <container>
    │         ├── Se saudável após restart → OK
    │         └── Se não → +1 tentativa, aguarda backoff exponencial
    └── Sim → CIRCUIT BREAKER ABRE
              → compose down (derruba todos os containers)
              → compose up -d (sobe tudo novamente)
              → Aguarda 10s e revalida
```

**Parâmetros configuráveis** (diretamente no código, em `RecoveryManager.__init__`):

| Parâmetro | Default | Descrição |
|---|---|---|
| `max_retries` | 3 | Número de restart attempts antes do circuit breaker |
| `cooldown` | 30s | Tempo mínimo entre tentativas para o mesmo serviço |

---

## 5. Exemplo Mínimo Funcional

### Compose file (`docker-compose.yaml`)

```yaml
services:
  meu-redis:
    image: redis:7-alpine
    container_name: meu-redis
    ports:
      - "6379:6379"

  minha-api:
    image: my-api:latest
    container_name: minha-api
    ports:
      - "3000:3000"
```

### services.json

```json
{
    "services": [
        {
            "name": "redis",
            "type": "docker",
            "runtime": "docker",
            "container_name": "meu-redis",
            "check": "tcp",
            "host": "127.0.0.1",
            "port": 6379
        },
        {
            "name": "api",
            "type": "docker",
            "runtime": "docker",
            "container_name": "minha-api",
            "check": "http",
            "url": "http://127.0.0.1:3000/health",
            "expected_status": 200,
            "timeout": 5
        }
    ]
}
```

### Para rodar

```bash
docker compose up -d
python -m app.main
```

Saída esperada:

```
2026-07-21 10:00:00 | INFO     | Initializing Host...
2026-07-21 10:00:00 | INFO     | 2 services registered.
2026-07-21 10:00:00 | INFO     | Starting services...
2026-07-21 10:00:01 | INFO     | All services started.
2026-07-21 10:00:01 | INFO     | HealthMonitor started.
2026-07-21 10:00:06 | INFO     | [HEALTH] redis -> HEALTHY
2026-07-21 10:00:06 | INFO     | [HEALTH] api -> HEALTHY
```

---

## 6. Mapeamento Completo: Compose → services.json

Para cada serviço no seu compose, o `container_name` deve ser referenciado no `services.json`:

| Compose | services.json |
|---|---|
| `container_name: redis` | `"container_name": "redis"` |
| Porta mapeada: `6379:6379` | `"check": "tcp", "port": 6379` |
| Porta mapeada: `8080:80` | `"check": "http", "url": "http://127.0.0.1:8080/"` |

Se usar `ports_check.py` com `-f compose.yaml`, ele reatribui portas conflito automaticamente e sincroniza o `services.json`.
