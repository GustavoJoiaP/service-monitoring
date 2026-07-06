# Linux Service Host (LSH)

## Artefato de Arquitetura -- Ciclo de Vida

### Objetivo

Documentar o fluxo de execução do Linux Service Host antes da
implementação.

## Componentes

-   **Host**: Orquestra a plataforma.
-   **Configuration**: Carrega configurações.
-   **Registry**: Registra e mantém os serviços.
-   **IService**: Contrato comum dos serviços.
-   **Health Monitor**: Avalia saúde dos serviços.
-   **Recovery Manager**: Executa recuperação.

## Diagrama de Sequência

``` text
main.py
    |
    v
+---------+
|  Host   |
+---------+
    |
    |--> Configuration.load()
    |<-- Configuração carregada
    |
    |--> Registry.register(HeartbeatService)
    |--> Registry.register(CounterService)
    |
    |--> Registry.start_all()
    |        |
    |        +--> Heartbeat.start()
    |        +--> Counter.start()
    |
    +----------------------------------------------+
    |           LOOP PRINCIPAL (Daemon)            |
    |                                              |
    |--> HealthMonitor.check_all()                 |
    |        |                                     |
    |        +--> Heartbeat.health()               |
    |        +--> Counter.health()                 |
    |                                              |
    |   Algum serviço falhou?                      |
    |            |                                 |
    |         Não|-------------> Sleep(intervalo)  |
    |            |                                 |
    |           Sim                                |
    |            |                                 |
    |            v                                 |
    |--> RecoveryManager.recover(service)          |
    |        |                                     |
    |        +--> stop()                           |
    |        +--> start()                          |
    |        +--> validar health()                 |
    |                                              |
    +-----------------------> volta ao LOOP -------+
```

## Responsabilidades

### Host

-   Inicializar a plataforma.
-   Carregar configuração.
-   Registrar serviços.
-   Iniciar serviços.
-   Executar o loop principal.

### Registry

-   Registrar serviços.
-   Localizar serviços.
-   Iniciar/parar todos.
-   Expor coleção de serviços.

### IService

Contrato mínimo: - start() - stop() - restart() - health()

### Health Monitor

-   Executar verificações periódicas.
-   Produzir relatório de saúde.
-   Nunca reiniciar serviços.

### Recovery Manager

-   Receber serviços com falha.
-   Aplicar estratégia de recuperação.
-   Validar retorno à operação.

## Fluxo de Estados

``` text
REGISTERED
      |
      v
STARTING
      |
      v
RUNNING
      |
      +------> HEALTHY
      |
      +------> FAILED
                   |
                   v
              RECOVERING
                   |
           +-------+------+
           |              |
           v              v
       RUNNING        STOPPED
```

## Roadmap

1.  Fundação ✔
2.  Contratos ✔
3.  Registry + Serviços
4.  Health Monitor
5.  Recovery Manager
6.  Integração Systemd
7.  Integração Podman
8.  Observabilidade
