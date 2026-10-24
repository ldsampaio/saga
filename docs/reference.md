Fechado, gateway então. Sua razão é boa: com um ponto único de acesso, regras e migrações ficam num só lugar e os sistemas novos nascem mais simples. O risco do ponto único de falha dá para reduzir bastante com réplicas, cache e backups, e isso está tratado no documento. Abaixo está o pacote completo em um único arquivo, que você pode dividir em vários se preferir, já com todos os ajustes que combinamos (Python/FastAPI, PostgreSQL único, RabbitMQ, Keycloak, k3s, Terraform).

# Plataforma de Sistemas Acadêmicos: Arquitetura de Referência

Versão: 1.0 (rascunho para validação)
Escopo: SAGA

## 1. Objetivos e princípios

1. Cada sistema é independente: repositório, pipeline, deploy e ciclo de manutenção próprios.
2. Todos compartilham uma base de dados comum, acessada exclusivamente por um Database Gateway.
3. Uma única linguagem de backend (Python) e um único framework de frontend, para reduzir custo de manutenção.
4. Toda infraestrutura é declarada como código (Terraform + Helm) e roda em servidor auto-hospedado da faculdade.
5. Comunicação entre sistemas é feita por API (síncrona, via gateway) ou por eventos (assíncrona, via RabbitMQ). Nenhum sistema acessa o banco diretamente.
6. Simplicidade antes de sofisticação: só adicionar uma peça nova quando houver necessidade concreta.

## 2. Stack padrão

| Camada | Tecnologia |
|---|---|
| Linguagem backend | Python 3.12 |
| Framework de API | FastAPI |
| ORM e migrações | SQLAlchemy 2.x + Alembic (migrações somente no gateway) |
| Banco de dados | PostgreSQL (schemas separados, JSONB para dados flexíveis) |
| Pool de conexões | PgBouncer |
| Mensageria | RabbitMQ |
| Cache | Redis (opcional, introduzir só se necessário) |
| Autenticação | Keycloak (OIDC, JWT) |
| Frontend | React + TypeScript (ou Jinja2 + HTMX para interfaces simples) |
| Contêineres | Docker |
| Orquestração | k3s (Kubernetes leve) |
| IaC | Terraform |
| Deploy de aplicações | Helm |
| Virtualização do servidor | Proxmox VE (se for o hipervisor da faculdade) |
| Observabilidade | Prometheus, Grafana, Loki |
| CI/CD | GitLab CI ou GitHub Actions (conforme o que a faculdade usar) |

## 3. Visão geral



Exportar

HTTP + JWT

HTTP + JWT

HTTP + JWT

outbox publisher

valida tokens

login

login

login

Usuários

Frontend SGOA

Frontend SGRF

Frontend SGE

SGOA API

SGRF API

SGE API

Database Gateway

PgBouncer

PostgreSQL

RabbitMQ

Keycloak





## 4. Componentes

### 4.1 Database Gateway

Serviço FastAPI que é o único com credenciais do PostgreSQL. Responsabilidades:

- Expor a API de dados versionada (`/v1/...`) para todos os sistemas.
- Aplicar autorização por escopo (cada sistema só escreve no seu domínio).
- Validar regras de integridade e de negócio que sejam comuns.
- Registrar auditoria de toda escrita.
- Publicar eventos de domínio no RabbitMQ usando o padrão outbox (seção 7).
- Ser o dono de todas as migrações Alembic.

Organização interna: monólito modular, um módulo por domínio, para evitar que o gateway vire um gargalo de desenvolvimento.

```
gateway/
  app/
    main.py
    core/            # config, segurança, db, auditoria, outbox
    modules/
      common/        # users, roles, permissions, units (cursos, departamentos)
        router.py
        service.py
        models.py
        schemas.py
      sgoa/
      sgrf/
      sge/
  migrations/        # Alembic (um branch por schema)
  tests/
  openapi/           # contrato exportado (openapi.json) versionado no Git
  Dockerfile
```

Regras de design da API do gateway:

- A API é orientada a domínio, não a tabelas. Exemplo: `POST /v1/sgoa/orientations/{id}/approve` em vez de PATCH genérico em campos soltos.
- Contrato primeiro: o `openapi.json` é versionado e revisado em pull request. Mudanças incompatíveis exigem nova versão (`/v2`).
- Versões antigas permanecem ativas por um período de depreciação documentado (padrão: 6 meses).
- Paginação, filtros e ordenação seguem um padrão único em todos os módulos.
- Idempotência: operações de criação aceitam o header `Idempotency-Key`.

### 4.2 Biblioteca cliente (SDK interno)

Pacote Python `platform-client`, gerado a partir do OpenAPI do gateway e versionado (semver). Cada sistema o instala e o usa no lugar de chamadas HTTP manuais. Contém:

- Cliente tipado para os endpoints do gateway.
- Obtenção e renovação automática de token (client credentials do Keycloak).
- Timeouts, retentativas com backoff e circuit breaker.
- Validação de JWT de usuários final para as APIs dos sistemas.
- Utilitários de logging estruturado e publicação/consumo de eventos.

### 4.3 Sistemas (SGOA, SGRF, SGE e futuros)

Cada sistema é composto por uma API FastAPI e um frontend. Regras:

- Não possuem credenciais do PostgreSQL.
- Mantêm estado próprio apenas se for efêmero (cache, filas locais).
- Falam com o gateway via `platform-client` e com outros sistemas via eventos.
- São stateless: qualquer instância atende qualquer requisição, permitindo escala horizontal.
- Cada um tem seu repositório, imagem Docker, Helm chart e pipeline.

### 4.4 RabbitMQ

- Exchange do tipo `topic` chamada `platform.events`.
- Cada sistema declara suas próprias filas (`sgoa.q.<evento>`) e dead-letter queues.
- Mensagens persistentes e confirmações de publicação (publisher confirms) ativadas.

### 4.5 Keycloak

- Um realm (`faculdade`) com usuários e papéis da instituição (idealmente federado ao diretório da faculdade, LDAP/AD ou SSO institucional, se existir).
- Um client por frontend (fluxo Authorization Code + PKCE).
- Um client por sistema backend (fluxo client credentials) para chamadas ao gateway.

## 5. Banco de dados

### 5.1 Schemas

| Schema | Dono lógico | Conteúdo |
|---|---|---|
| `common` | Plataforma | usuários, papéis, permissões, unidades institucionais |
| `sgoa` | SGOA | orientações, orientadores, orientandos, encontros, documentos |
| `sgrf` | SGRF | orçamentos, contas, lançamentos, prestações de contas |
| `sge` | SGE | modelos, mensagens, logs de envio (payloads em JSONB) |
| `audit` | Gateway | trilha de auditoria de escritas |
| `platform` | Gateway | tabela `outbox`, controle de idempotência |

### 5.2 Papéis do banco

- `gateway_app`: único papel de aplicação, com permissão nos schemas acima.
- `backup_ro`: leitura, usado para backup.
- `admin_dba`: uso humano excepcional, com auditoria.
- Nenhum outro papel de aplicação deve existir. Credenciais ficam em segredos do Kubernetes, nunca no repositório.

### 5.3 Convenções de modelagem

- Chaves primárias UUID (v7 quando possível).
- Colunas `created_at`, `updated_at`, `created_by`, `updated_by` em todas as tabelas.
- Exclusão lógica (`deleted_at`) para entidades de negócio.
- Referências entre schemas de sistemas diferentes são proibidas. Referências para `common` são permitidas (por exemplo, `user_id`).
- Dados semiestruturados usam JSONB com índice GIN apenas quando houver consulta que o justifique.

### 5.4 Migrações (Alembic)

- Somente o gateway executa migrações, como um Job do Helm antes do deploy.
- Padrão expand/contract para mudanças que quebram compatibilidade: (1) adicionar o novo, (2) migrar dados e clientes, (3) remover o antigo em release posterior.
- Toda migração tem `upgrade` e `downgrade` e é testada em banco de teste com cópia anonimizada dos dados.

## 6. Autenticação e autorização

- Usuários finais autenticam no Keycloak e recebem JWT; cada API de sistema valida o token.
- Chamadas sistema para gateway usam o token do client do sistema.
- Escopos no formato `<dominio>:<acao>`, por exemplo `common:read`, `sgoa:read`, `sgoa:write`, `sgrf:write`.
- Matriz padrão de escopos por client:

| Client | Escopos concedidos |
|---|---|
| sgoa-backend | `common:read`, `sgoa:read`, `sgoa:write` |
| sgrf-backend | `common:read`, `sgrf:read`, `sgrf:write` |
| sge-backend | `common:read`, `sge:read`, `sge:write` |

- Leitura de dados de outro domínio só ocorre por endpoint explicitamente exposto no gateway para esse fim, ou por evento. O gateway recusa o resto.
- Permissões finas por usuário (por exemplo, "orientador só vê suas orientações") são aplicadas no gateway com base nas claims do token do usuário, repassadas pelo sistema chamador.
- Dados pessoais seguem a LGPD: minimização, finalidade registrada, retenção definida por domínio, acesso auditado.
- Tráfego externo sempre em HTTPS (certificados via cert-manager; Let's Encrypt se o domínio for público, ou CA interna da faculdade).

## 7. Eventos

### 7.1 Padrão outbox

Para não perder nem duplicar eventos, o gateway grava o evento na tabela `platform.outbox` na mesma transação da alteração de dados. Um publicador (processo separado dentro do gateway) lê a outbox e publica no RabbitMQ, marcando como enviado. Consumidores devem ser idempotentes (entrega "pelo menos uma vez").

### 7.2 Envelope padrão



Json
Copiar
{
  "id": "0192f0c2-7c1a-7b3e-9d5e-1a2b3c4d5e6f",
  "type": "sgoa.orientation.created",
  "version": 1,
  "occurred_at": "2026-10-23T18:00:00Z",
  "actor": { "user_id": "uuid", "system": "sgoa" },
  "data": { "orientation_id": "uuid" }
}




### 7.3 Convenções

- Nome do evento: `<dominio>.<entidade>.<acao_no_passado>`.
- Eventos contêm identificadores e o mínimo de dados; o consumidor busca detalhes via API se precisar.
- Mudança incompatível no payload incrementa `version`, e as duas versões são publicadas durante a transição.

### 7.4 Exemplos de fluxos

- `sgoa.orientation.created` → SGE envia e-mail ao orientando e ao orientador.
- `sgrf.budget.updated` → SGOA atualiza indicadores de projetos vinculados.
- `common.user.deactivated` → todos os sistemas encerram sessões e tarefas do usuário.

## 8. Infraestrutura

### 8.1 Topologia

- Um servidor da faculdade com Proxmox VE (ou outro hipervisor) hospedando VMs.
- Fase 1: uma VM com k3s (single node) rodando toda a plataforma.
- Fase 2 (recomendada quando houver hardware): três VMs k3s (alta disponibilidade do control plane) e PostgreSQL em VM dedicada com réplica.
- Namespaces Kubernetes: `platform` (gateway, PgBouncer, RabbitMQ, Keycloak), `sgoa`, `sgrf`, `sge`, `observability`, `ingress`.

### 8.2 Terraform

Estrutura do repositório `platform-infra`:

```
platform-infra/
  terraform/
    modules/
      proxmox-vm/
      k3s-bootstrap/
      platform-core/     # namespaces, ingress, cert-manager, RabbitMQ, Keycloak
      app-release/       # módulo genérico para instalar um sistema via Helm
    envs/
      dev/
      prod/
  helm/
    gateway/
    sgoa/
    sgrf/
    sge/
  docs/
```

Exemplo-base (esqueleto a ser validado no ambiente real). Segredos sempre por variáveis sensíveis ou cofre, nunca em texto puro no código:



Hcl
Copiar
terraform {
  required_providers {
    proxmox = {
      source = "bpg/proxmox"
    }
    helm = {
      source = "hashicorp/helm"
    }
    kubernetes = {
      source = "hashicorp/kubernetes"
    }
  }
}

variable "proxmox_endpoint" {
  type = string
}

variable "proxmox_api_token" {
  type      = string
  sensitive = true
}

variable "proxmox_node" {
  type = string
}

variable "cloud_image_file_id" {
  type        = string
  description = "ID da imagem cloud-init (ex.: Ubuntu 24.04) já presente no storage do Proxmox"
}

variable "ssh_public_key" {
  type = string
}

provider "proxmox" {
  endpoint  = var.proxmox_endpoint
  api_token = var.proxmox_api_token
}

resource "proxmox_virtual_environment_vm" "k3s_node" {
  name      = "k3s-01"
  node_name = var.proxmox_node

  cpu {
    cores = 4
  }

  memory {
    dedicated = 16384
  }

  disk {
    datastore_id = "local-lvm"
    file_id      = var.cloud_image_file_id
    interface    = "scsi0"
    size         = 100
  }

  network_device {
    bridge = "vmbr0"
  }

  initialization {
    ip_config {
      ipv4 {
        address = "192.168.1.100/24"
        gateway = "192.168.1.1"
      }
    }
    user_account {
      username = "ubuntu"
      keys     = [var.ssh_public_key]
    }
  }
}




Observações:

- O estado do Terraform (`terraform.tfstate`) contém dados sensíveis e deve ficar em backend remoto protegido (por exemplo, MinIO/S3 interno ou GitLab) com bloqueio de estado.
- Segredos de aplicação: usar Kubernetes Secrets criptografados (SOPS + age) ou HashiCorp Vault/OpenBao se a equipe tiver capacidade de operá-lo.
- A instalação do k3s pode ser feita via cloud-init ou pelo módulo `k3s-bootstrap`; o provider Helm/Kubernetes é configurado a partir do kubeconfig gerado.

### 8.3 Helm

Cada sistema possui um chart com: Deployment (mínimo 2 réplicas para o gateway), Service, Ingress, HPA opcional, ConfigMap, referência a Secret, liveness e readiness probes e PodDisruptionBudget.

Valores mínimos do gateway:



Yaml
Copiar
replicaCount: 2
image:
  repository: registry.faculdade.edu.br/platform/gateway
  tag: "1.0.0"
resources:
  requests: { cpu: 250m, memory: 256Mi }
  limits:   { cpu: "1",  memory: 512Mi }
probes:
  liveness:  /health/live
  readiness: /health/ready
podDisruptionBudget:
  minAvailable: 1
env:
  DB_HOST: pgbouncer.platform.svc
  RABBITMQ_URL_SECRET: gateway-rabbitmq
  OIDC_ISSUER: https://auth.faculdade.edu.br/realms/faculdade




## 9. Mitigação do ponto único de falha (gateway)

Como a decisão aceita conscientemente o gateway como ponto crítico, estas medidas são obrigatórias:

1. Mínimo de 2 réplicas, em nós diferentes quando houver mais de um nó, com PodDisruptionBudget.
2. Gateway stateless, com health checks, e rollout gradual (rolling update) com rollback automático.
3. Resiliência no cliente: timeouts curtos, retentativas com backoff e circuit breaker no `platform-client`.
4. Cache local com TTL curto (1 a 5 minutos) de dados raramente alterados (usuários, permissões, unidades) nos sistemas, para tolerar quedas breves.
5. Operações de escrita não críticas podem ser enfileiradas localmente e reenviadas (com `Idempotency-Key`).
6. PgBouncer entre o gateway e o PostgreSQL para controlar conexões.
7. Alertas no Prometheus para latência, taxa de erro 5xx, saturação de conexões e atraso da outbox.
8. Testes de carga periódicos antes de mudanças grandes e testes de falha (matar um pod e verificar o comportamento).
9. Rever esta decisão se o tráfego crescer muito: o gateway pode ser dividido por domínio mantendo o mesmo contrato de API, pois os schemas já são separados.

Limitação conhecida: enquanto houver um único servidor físico ou um único nó k3s, uma falha de hardware derruba tudo. Replicas de pods não resolvem isso; apenas a Fase 2 da seção 8.1 e os backups da seção 10 mitigam.

## 10. Backup e recuperação

- PostgreSQL: backup completo diário e arquivamento contínuo de WAL (pgBackRest ou WAL-G) para permitir recuperação a um ponto no tempo.
- Cópia dos backups para armazenamento fora do servidor principal (outro servidor, NAS ou storage institucional).
- Backup do estado do Terraform, do Keycloak (export do realm) e dos manifests/valores Helm (já no Git).
- Meta inicial: RPO de até 15 minutos e RTO de até 4 horas (ajustar conforme a criticidade definida pela faculdade).
- Teste de restauração documentado e executado ao menos uma vez por semestre.

## 11. Observabilidade

- Logs estruturados em JSON com `trace_id` propagado entre sistemas e gateway (Loki).
- Métricas padrão por serviço: requisições, latência, erros, filas RabbitMQ (Prometheus + Grafana).
- Tracing distribuído com OpenTelemetry (opcional na Fase 1).
- Dashboards mínimos: saúde do gateway, filas e dead-letters, uso do banco, jobs de migração.

## 12. CI/CD e repositórios

Repositórios independentes:

- `platform-infra`: Terraform, Helm charts compartilhados, documentação operacional.
- `platform-gateway`: código do gateway, migrações e `openapi.json`.
- `platform-client`: SDK Python (gerado do OpenAPI e publicado em registry interno de pacotes).
- `sgoa`, `sgrf`, `sge`: um repositório por sistema.

Pipeline padrão de cada sistema: lint e type check (ruff, mypy), testes unitários, testes de contrato contra o OpenAPI do gateway, build da imagem, varredura de vulnerabilidades (Trivy), publicação da imagem, deploy automático em `dev` e deploy manual aprovado em `prod`.

Pipeline do gateway: igual ao anterior, mais teste de migrações (upgrade/downgrade em banco efêmero), verificação de quebra de contrato (diff do OpenAPI) e geração/publicação de nova versão do `platform-client`.

## 13. Regras para agentes de IA e desenvolvedores

1. Nunca conectar um sistema diretamente ao PostgreSQL; toda leitura e escrita passa pelo gateway.
2. Nunca criar migrações fora do repositório do gateway.
3. Nunca consultar tabelas de outro domínio; usar endpoint exposto ou evento.
4. Mudanças na API do gateway começam pelo contrato OpenAPI e exigem revisão humana.
5. Mudanças incompatíveis exigem nova versão da API e plano de depreciação.
6. Nunca colocar segredos, senhas ou tokens no código, em logs ou em arquivos versionados.
7. Todo novo endpoint ou evento deve ter testes e documentação atualizada neste repositório.
8. Todo evento consumido deve ser tratado de forma idempotente.
9. Seguir a stack da seção 2; qualquer tecnologia nova exige registro de decisão (ADR).
10. Em caso de dúvida sobre regra de negócio, consultar o responsável do sistema em vez de assumir.

## 14. Plano de implementação

Fase 0, fundações
- Definir domínio e nomes finais, escopos e matriz de permissões.
- Levantar o modelo de dados atual de SGOA, SGRF e SGE (já implementados) e mapear para os schemas.
- Registrar a decisão do gateway como ADR-001.

Fase 1, infraestrutura
- Provisionar VM e k3s com Terraform.
- Instalar ingress, cert-manager, PostgreSQL, PgBouncer, RabbitMQ, Keycloak e observabilidade.
- Configurar backup e testar restauração.

Fase 2, gateway e SDK
- Implementar o módulo `common` (usuários, papéis, permissões) e a integração com Keycloak.
- Implementar auditoria, outbox e publicador.
- Gerar o `platform-client` e publicar no registry interno.

Fase 3, migração dos sistemas existentes (um por vez)
- Criar o módulo do sistema no gateway e o schema correspondente.
- Migrar os dados do banco atual para o schema novo, com validação e período de execução em paralelo.
- Trocar o acesso a dados do sistema para o `platform-client`.
- Ordem sugerida: o sistema com menos dependências primeiro (provavelmente SGE), depois SGOA, depois SGRF.

Fase 4, integração por eventos
- Implementar os fluxos da seção 7.4.
- Configurar dead-letter queues e alertas.

Fase 5, endurecimento
- Testes de carga e de falha, revisão de segurança e LGPD, documentação operacional e treinamento da equipe.

## 15. Decisões registradas

| ID | Decisão | Motivo | Consequência aceita |
|---|---|---|---|
| ADR-001 | Acesso ao banco exclusivamente via Database Gateway | Manutenção mais simples ao longo do tempo, regras centralizadas | Ponto crítico de falha, mitigado conforme seção 9 |
| ADR-002 | Python/FastAPI como único backend | Uma linguagem reduz custo de manutenção | Sistemas em outra linguagem exigem justificativa |
| ADR-003 | PostgreSQL único com schemas e JSONB (sem MongoDB) | Menos componentes para operar | Dados flexíveis ficam em JSONB |
| ADR-004 | RabbitMQ no lugar de Kafka | Volume modesto, operação mais simples | Reavaliar se o volume crescer muito |
| ADR-005 | k3s + Terraform + Helm | Leve para um servidor único, tudo versionado | Alta disponibilidade só na Fase 2 de infraestrutura |

## 16. Pendências a definir

- Hipervisor real do servidor da faculdade (Proxmox ou outro) e especificações de hardware.
- Existência de SSO ou diretório institucional para federar no Keycloak.
- Modelo de dados atual de SGOA, SGRF e SGE e volume aproximado de dados.
- Plataforma de Git e CI usada pela faculdade.
- Requisitos formais de retenção, auditoria e LGPD definidos pela instituição.
- Escolha do frontend: React + TypeScript ou Jinja2 + HTMX.
- Nomes e escopo dos futuros sistemas.
