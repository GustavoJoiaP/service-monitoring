# Linux Service Host (LSH) — Arquitetura

## Objetivo

Documentar a arquitetura, componentes e fluxo de execução do Service Monitoring Host.

O LSH é um framework em Python para monitorar a saúde de containers (Docker/Podman), com recuperação automática em caso de falha e deploy via systemd para produção.

---

## Componentes

| Componente | Responsabilidade |
|---|---|
| **Host** | Orquestra a plataforma: carrega configuração, registra serviços, inicia o loop principal |
| **Configuration** | Lê e valida o `services.json` |
| **ServiceFactory** | Cria a implementação correta com base no `type` do serviço |
| **Registry** | Mantém o catálogo de serviços registrados |
| **ServiceManager** | Inicia/para/reinicia serviços individualmente ou em massa |
| **IService** | Contrato (interface) que todo serviço deve implementar |
| **ContainerService** | Monitora um container via Podman ou Docker |
| **WorkerProcessService** | Gerencia um processo Linux externo |
| **HeartbeatService** | Serviço interno de heartbeat (para testes) |
| **CounterService** | Serviço interno de contagem (para testes) |
| **FaultyService** | Serviço que simula falhas (para testes de recuperação) |
| **HealthMonitor** | Loop periódico que verifica a saúde de todos os serviços |
| **RecoveryManager** | Executa a estratégia de recuperação (circuit breaker) |

---

## Diagrama de Sequência

```text
main.py
    |
    v
+------+
| Host |
+------+
    |
    |--> Configuration("services.json")
    |<-- Lista de serviços carregada
    |
    |--> ServiceFactory.create(service)  (para cada serviço)
    |<-- ContainerService | WorkerProcessService | etc.
    |
    |--> Registry.register(instância)
    |
    |--> ServiceManager.start_all()
    |        |
    |        +--> ContainerService.start()
    |        |       └── {runtime} ps -a --format {{.Names}}
    |        |           ├── encontrou → RUNNING
    |        |           └── não encontrou → FAILED
    |        |
    |        +--> HeartbeatService.start()
    |        +--> WorkerProcessService.start()
    |
    +----------------------------------------------+
    |           LOOP PRINCIPAL (Daemon)            |
    |                                              |
    |--> HealthMonitor.check_all()  [a cada 5s]    |
    |        |                                     |
    |        +--> ContainerService.is_alive()      |
    |        |       ├── container_state           |
    |        |       │   └── {runtime} inspect     |
    |        |       ├── tcp                       |
    |        |       │   └── asyncio.open_connection|
    |        |       └── http                      |
    |        |           └── urllib.request (GET)  |
    |        |                                     |
    |        +--> WorkerProcessService.is_alive()  |
    |        |       └── os.kill(pid, 0)           |
    |        |                                     |
    |   Algum serviço falhou?                      |
    |        |                                     |
    |     Não |------> Sleep(5s)                   |
    |        |                                     |
    |       Sim                                    |
    |        |                                     |
    |        v                                     |
    |--> RecoveryManager.recover(service)          |
    |        |                                     |
    |        +--> restart() x3 (com cooldown)      |
    |        |       └── {runtime} restart         |
    |        |                                     |
    |        +--> Se esgotou: compose down/up      |
    |              (derruba e sobe tudo)            |
    |                                              |
    +-----------------------> volta ao LOOP -------+
```

---

## Fluxo de Estados

```text
REGISTERED
    |
    v
STARTING
    |
    v
RUNNING ──────> HEALTHY (is_alive retorna true)
    |
    └──────> FAILED (is_alive retorna false)
                 |
                 v
            RECOVERING
                 |
         +-------+------+
         |              |
         v              v
     RUNNING        STOPPED
```

---

## Principais Decisões Técnicas

### Runtime configurável

O `ContainerService` aceita um campo `runtime` no config (`"podman"` ou `"docker"`).
Todos os comandos de container (`ps`, `inspect`, `restart`) usam o runtime configurado,
permitindo que o mesmo monitor opere com Podman em produção e Docker em desenvolvimento.

### Recuperação em dois níveis

1. **Nível individual:** `{runtime} restart <container>` com backoff exponencial (2^tentativa segundos)
2. **Nível compose:** `compose down && compose up -d` quando o restart individual esgota as tentativas

O segundo nível é opcional — depende da chave `compose` no `services.json`.

### Health checks assíncronos

- **container_state:** chamada ao runtime via `asyncio.create_subprocess_exec`
- **tcp:** `asyncio.open_connection` com timeout
- **http:** `urllib.request` rodado em `run_in_executor` (não bloqueia o event loop)

### Circuit breaker

Cada serviço tem um contador de falhas. Após `max_retries` (3) falhas consecutivas,
o circuit breaker abre e escala para compose-level recovery. Um cooldown de 30s
entre tentativas evita flood de restart em cenários de falha intermitente.

---

## Roadmap

- [x] Fundação (Host, Configuration, Registry)
- [x] Contratos (IService, ServiceStatus)
- [x] Registry + Serviços (ContainerService, WorkerProcessService)
- [x] Health Monitor (loop periódico de verificação)
- [x] Recovery Manager (circuit breaker, compose recovery)
- [x] Integração Systemd (service production-ready)
- [x] Integração Podman (runtime configurável)
- [ ] Observabilidade (métricas, alertas, dashboard)
