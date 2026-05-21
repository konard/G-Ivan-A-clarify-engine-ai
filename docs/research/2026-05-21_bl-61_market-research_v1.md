# Research: Market Comparison for Microservices Architecture Components (BL-61)

## Метаданные
- **Дата:** 2026-05-21
- **Версия:** v1
- **Тип документа:** `research`
- **Статус:** Draft -> готов к ревью PO / Tech Lead / Infra
- **Автор:** konard (AI issue solver, по [issue #216](https://github.com/G-Ivan-A/clarify-engine-ai/issues/216))
- **Спринт:** Sprint 6 - Architecture Foundation
- **PR:** [`#217`](https://github.com/G-Ivan-A/clarify-engine-ai/pull/217)
- **Depends on:** BL-60 (Next-Gen Architecture Research), BL-58 (Retrieval Research), BL-59 (Requirement Parsing Research)
- **Целевая аудитория:** Product Owner, Tech Lead, Infra Lead, ML-инженер, BA Lead
- **Связанные документы:**
  - [`docs/research/2026-05-20_bl-60_next-gen-architecture_v1.md`](2026-05-20_bl-60_next-gen-architecture_v1.md)
  - [`docs/CONCEPT.md`](../CONCEPT.md)
  - [`docs/ADR/001-rag-architecture.md`](../ADR/001-rag-architecture.md)
  - [`docs/ADR/005-audit-trail.md`](../ADR/005-audit-trail.md)
  - [`docs/research/2026-05-21_bl-57_retrieval-architecture_v1.md`](2026-05-21_bl-57_retrieval-architecture_v1.md)
  - [`docs/research/2026-05-20_bl-59_requirement-parsing_v1.md`](2026-05-20_bl-59_requirement-parsing_v1.md)

> **Scope note.** Это исследование, не реализация. Документ не меняет `src/`, `configs/`, `prompts/` и не фиксирует необратимый vendor lock-in. Цель BL-61 - дать PO / Tech Lead / Infra Lead карту рынка и миграционные варианты для 13 компонентов архитектуры BL-60.

---

## 1. Executive Summary

BL-60 предложил целевую микросервисную архитектуру, но намеренно зафиксировал несколько конкретных технологий как рабочие кандидаты: Elasticsearch для production search, NATS / RabbitMQ для очередей, Ollama / vLLM для local serving, PostgreSQL для audit. Issue #216 уточняет риск: у заказчика может не быть доступа к Elasticsearch, GPU, облаку, нужным серверам или согласованным SaaS-провайдерам. Поэтому BL-61 сравнивает не один стек, а рынок альтернатив по каждому компоненту.

Основной вывод: архитектуру нужно проектировать через **заменяемые контракты**, а не через конкретные продукты. Для Sprint 6 стоит выбрать продукты, которые имеют self-hosted путь, умеренную эксплуатационную сложность и понятную миграцию:

| Компонент | Budget option | Optimal option для pilot / early production | Enterprise option |
|-----------|---------------|---------------------------------------------|-------------------|
| Vector DB / Search | pgvector или ChromaDB | Qdrant или OpenSearch | Elasticsearch / Vespa / managed vector SaaS |
| Message bus | RabbitMQ или Redis Streams | NATS JetStream | Kafka / Pulsar / managed cloud bus |
| LLM orchestration | LiteLLM + Instructor + prompt files | LlamaIndex или Haystack + LangGraph для flows | LangSmith / Portkey / Braintrust governance |
| Document parsing | PyMuPDF + pdfplumber + python-docx/openpyxl | Docling + Unstructured | Azure Document Intelligence / Textract / Document AI |
| Embeddings | BAAI/bge-m3 self-hosted | bge-m3 + multilingual-e5 / Jina fallback | OpenAI / Cohere / Voyage / RU provider API |
| Local LLM serving | Ollama или llama.cpp | vLLM или TGI | TensorRT-LLM / KServe / BentoML |
| Reranker | FlashRank / MiniLM | bge-reranker-base/large | Cohere / Jina / Voyage / ColBERT |
| Observability | Prometheus + Grafana + Loki | OpenTelemetry + Grafana stack + Sentry | Datadog / New Relic / Dynatrace / Honeycomb |
| Audit DB | PostgreSQL append-only | ClickHouse + PostgreSQL metadata | ClickHouse Cloud / BigQuery / Snowflake |
| Object storage | local FS / MinIO single node | MinIO HA / Yandex / Selectel | S3 / Azure Blob / GCS / Ceph |
| Cache | in-process + Redis OSS | Redis / Dragonfly / KeyDB | Redis Cloud / Hazelcast / Aerospike |
| API gateway | FastAPI + NGINX | Kong / APISIX / Envoy | Kong Enterprise / Tyk / AWS API Gateway / Cloudflare |
| PII masking | custom regex + tests | Microsoft Presidio + RU recognizers | Google DLP / Azure / AWS / Nightfall / Immuta |

**Recommended default architecture for Sprint 6 PoC:**

1. Keep the current monolith contracts, but introduce provider interfaces: `SearchBackend`, `MessageBus`, `EmbeddingProvider`, `ObjectStore`, `AuditStore`.
2. Start with self-hosted, RU-resident defaults: Qdrant or OpenSearch, NATS JetStream, Docling/Unstructured, bge-m3, Ollama/vLLM, PostgreSQL + ClickHouse, MinIO, Redis, FastAPI + NGINX, Presidio.
3. Keep managed/SaaS alternatives only behind compliance flags and budget approvals: OpenAI/Cohere/Voyage, Pinecone, cloud object storage, Datadog/New Relic, Google/AWS/Azure DLP.
4. Treat Elasticsearch as a strong enterprise candidate, not an assumption. If corporate ES is available and licensed, it is still a good production choice because it covers BM25, dense vectors, filtering, security, backups, and ops maturity in one platform.

---

## 2. Методология и ограничения

### 2.1. Источники и дата проверки

Прайсы и capability-описания проверены по публичным официальным страницам и документации на дату **2026-05-21**. В конце документа есть Source Register с URL. Для продуктов с quote-only моделью указано `Quote`, потому что публичного стабильного self-serve прайса нет или цена зависит от региона, volume commit, support tier и private networking.

### 2.2. Нормализация стоимости

В таблицах используются четыре вида стоимости:

| Маркер | Что означает |
|--------|--------------|
| `$0 license` | Open-source / self-hosted без лицензии, но есть infra + ops cost. |
| `Infra estimate` | Оценка месячного TCO для типового pilot: 4-16 vCPU, 16-64 GB RAM, 100-500 GB SSD, без 24/7 DevOps. Это не vendor price. |
| `Usage-based` | Официальный SaaS/managed прайс по операциям, токенам, GB-month, request units, compute units. |
| `Quote` | Публичная цена не раскрыта, нужен sales quote. |

Все суммы в USD без НДС, egress, marketplace markup, enterprise support и скидок commit, если не указано иначе. Для RU-провайдеров и локальных DC цена зависит от договора, поэтому дана применимость, а не точный ruble-rate.

### 2.3. Типовой workload для сравнения

Чтобы сравнение не было абстрактным, принят pilot-profile:

| Параметр | Значение |
|----------|----------|
| Corpus | 10k-200k chunks, 768-1024 dim embeddings, 20-200 GB raw docs |
| Search traffic | 1-10 RPS interactive, batch indexing nightly |
| LLM traffic | 100-2,000 RAG calls/day, PII-sensitive share 30-60% |
| Availability | Pilot 99.0-99.5%, production target 99.9% |
| Compliance | RU-residency preferred, external SaaS only after approval |
| Team | 1-2 backend engineers, part-time DevOps, no dedicated SRE initially |

---

## 3. Cross-Component Decision Rules

| Rule | Decision impact |
|------|-----------------|
| **Prefer self-hosted for PII path.** | Search, embeddings, LLM serving, PII masking and audit should have a local option. |
| **Separate API contracts from products.** | Product choice must be swappable without changing `Pipeline`, UI, or export contracts. |
| **Use managed only for clear TCO win.** | SaaS is justified for bursty workloads, missing infra skills, or strong support needs. |
| **Avoid AGPL surprise.** | AGPL components are acceptable only if legal confirms distribution/SaaS obligations. |
| **Keep ChromaDB and in-memory fallbacks.** | They remain useful for tests and offline demos, even if not production-grade. |
| **Price by steady-state and migration.** | Cheapest pilot tool can become expensive if migration requires re-embedding or reindexing. |

---

## 4. Component 1 - Vector Database / Search Engine

**Responsibility:** embeddings storage, lexical search, hybrid search, metadata filtering, incremental updates, production retrieval.

| № | Решение | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Metadata filtering / Hybrid / Updates / Scale / Support |
|---:|---------|------------|-------|--------------|-----------|---------|--------------|----------|------------------|----------------------------------------------------------|
| 1 | Elasticsearch 8.x | BM25, dense vectors, hybrid RRF, filters, security | Elastic License / SSPL options, tuning complexity, JVM ops | Mature enterprise search, rich query DSL, snapshots, RBAC | Self-managed `$0 basic` + infra; Elastic Cloud usage/resource pricing | Pilot 4-8 vCPU, 16-32 GB RAM, SSD; production 3+ nodes | M/H, needs ES skills | Elastic License v2 / SSPL / AGPL options by distribution/version | Yes self-host; managed cloud may violate residency | Strong filters, strong hybrid, bulk updates, high scale, enterprise support |
| 2 | OpenSearch 2.x/3.x | ES-like search + kNN + BM25 | Fork compatibility gaps, plugin/version drift | Apache 2.0, AWS-managed path, familiar Lucene model | `$0 license`; AWS examples: c6g.large.search `$0.113/h`, semantic OCU `$0.24/h` | 3 nodes recommended for HA, 8-64 GB RAM/node | M/H | Apache 2.0 | Yes self-host; AWS region residency depends on approval | Strong filters, strong hybrid with custom query, bulk updates, high support |
| 3 | Qdrant 1.x | Vector DB with payload filters and hybrid sparse+dense | BM25 less native than Lucene, separate lexical stack may be needed | Simple ops, Rust performance, good payload filtering, cloud/free tier | OSS `$0`; Qdrant Cloud free 0.5 vCPU/1 GB/4 GB, paid usage-based | Pilot 2-4 vCPU, 8-16 GB RAM; HA 3 nodes | S/M | Apache 2.0 | Yes self-host/hybrid cloud | Strong filters, good hybrid, upsert, medium-high scale, active community |
| 4 | Weaviate | Vector DB, hybrid search, modules | Higher memory footprint, GraphQL/schema learning | Built-in hybrid, multi-tenancy, modules | OSS `$0`; Weaviate Cloud serverless/enterprise usage or quote | 4-8 vCPU, 16-32 GB RAM pilot | M | BSD-3-Clause core | Yes self-host; WCD depends region | Good filters, native hybrid, batch updates, high support |
| 5 | Milvus | High-scale vector DB | Operationally heavy (etcd, object store, query/data nodes) | Very high scale, GPU/index options, Zilliz Cloud | OSS `$0`; Zilliz Cloud usage/quote | Pilot complex; production 3+ services, object store | H | Apache 2.0 | Yes self-host | Good filters, hybrid improving, batch updates, very high scale |
| 6 | pgvector | Vectors inside PostgreSQL | Recall/latency limits at high cardinality, DB bloat | Reuses Postgres, transactional metadata, simplest governance | `$0 license`; Postgres infra already likely needed | 4-16 vCPU, 16-64 GB RAM, SSD | S/M | PostgreSQL License | Yes self-host | Excellent relational filters, BM25 requires extension/sidecar, easy updates, medium scale |
| 7 | ChromaDB | Local/dev vector store | Not ideal for HA, limited enterprise governance | Simple tests/offline, current ecosystem familiarity | `$0 license`; infra only | 2-4 vCPU, 8-16 GB RAM for small pilot | XS/S | Apache 2.0 | Yes local | Basic filters, hybrid mostly app-side, simple updates, low-medium scale |
| 8 | Pinecone | Managed vector DB and inference | SaaS/data residency, usage surprises, vendor lock-in | Low ops, serverless, read/write/storage unit model, DRN | Free/start credits; paid plan has `$50` monthly minimum, WU examples `$4-$6.75/M` by tier/region | No local infra | S | Commercial SaaS | No self-host; residency by cloud region only | Good metadata, sparse+dense/full-text options, managed scale/support |
| 9 | Vespa | Search + vector + ranking platform | Steep learning curve, ops complexity | Powerful ranking, hybrid, large-scale serving | OSS `$0`; Vespa Cloud usage/quote | 3+ nodes recommended, 16-64 GB RAM/node | H | Apache 2.0 | Yes self-host | Strong filters/hybrid/ranking, streaming updates, very high scale |
| 10 | LanceDB | Embedded/table vector storage | Young ecosystem for HA/ops, search feature depth | Cheap local/lakehouse path, Arrow/Lance format | OSS `$0`; LanceDB Cloud usage/quote | 2-8 vCPU, object store optional | S/M | Apache 2.0 | Yes self-host | Basic-good filters, hybrid available, easy batch, medium scale |
| 11 | Redis Stack Vector | Cache + vector similarity | RAM cost, persistence/search limits vs search engines | Low latency, reuses Redis, good for cache/RAG hotset | Redis OSS/RSAL mix; Redis Cloud usage | RAM-heavy: dataset must fit memory | S/M | Redis source licenses vary; modules not pure OSS in all editions | Yes self-host if license approved | Good filters, hybrid limited, fast updates, medium scale |
| 12 | MongoDB Atlas Vector Search | Document DB + vector search | SaaS lock-in, self-host vector search limitations | If MongoDB already exists, simple metadata model | Atlas cluster usage-based | Managed infra | S/M | Commercial / SSPL server | Atlas region residency only | Good document filters, vector + text search, managed scale |
| 13 | Azure AI Search | Managed hybrid search and vector | Azure lock-in, data residency approval, cost | Mature managed search, semantic ranking, RBAC | Usage by SKU/replicas/partitions | Managed infra | S/M | Commercial SaaS | Region-dependent, not local | Strong filters/hybrid, managed updates, enterprise support |
| 14 | DataStax Astra DB | Cassandra + vector | SaaS lock-in, less lexical search depth | Serverless vector on Cassandra, scalable writes | Serverless usage/quote | Managed infra | S/M | Commercial SaaS / Apache Cassandra core | Region-dependent | Good metadata, vector search, high write scale |

**Recommendations**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
|------|---------|---------------------|-----------------|
| Budget | pgvector or ChromaDB | `$1k-6k` infra + part-time ops | MVP/offline pilot, <50k chunks, minimum new infra |
| Optimal | Qdrant or OpenSearch | `$4k-20k` infra/managed + ops | Production pilot where ES access is uncertain |
| Enterprise | Elasticsearch or Vespa | `$20k-100k+` infra/license/support | Corporate search platform, high query volume, strict security/backup needs |

**Migration paths**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| ChromaDB -> Qdrant/OpenSearch/ES | Export chunks + metadata, reuse embeddings if dim/model unchanged, bulk upsert | Low with dual-write | Medium |
| pgvector -> ES/OpenSearch | Dump rows, map metadata fields, bulk index, preserve `chunk_id` | Low | Medium |
| Qdrant -> ES/OpenSearch | Export collection payload/vector, add lexical analyzer, re-run quality eval | Low-medium | Medium |
| ES/OpenSearch -> Qdrant | Export `_source`, keep embeddings, move BM25 to sidecar or sparse vectors | Medium | Medium-high |

---

## 5. Component 2 - Message Bus / Event Streaming

**Responsibility:** asynchronous service communication, ingestion jobs, backpressure, retries, delivery guarantees.

| № | Решение | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Latency / Throughput / Persistence / Delivery / DLQ / Routing / Cluster |
|---:|---------|------------|-------|--------------|-----------|---------|--------------|----------|------------------|------------------------------------------------------------------------|
| 1 | NATS JetStream | Lightweight messaging + persistent streams | Smaller enterprise bench than Kafka, stream retention tuning | Very low latency, simple ops, request/reply, KV/object store | OSS `$0`; Synadia Cloud quote/usage | 2-4 vCPU/node, 4-16 GB RAM, 3 nodes HA | S/M | Apache 2.0 | Yes self-host | p95 low ms, high throughput, file persistence, at-least-once, DLQ by consumer, subjects |
| 2 | RabbitMQ | AMQP queues, routing, worker jobs | Throughput lower than Kafka, quorum queue tuning | Mature, simple DLQ/routing, great for task queues | OSS `$0`; CloudAMQP free/paid tiers | 2-8 vCPU, 4-32 GB RAM, 3 nodes HA | S/M | MPL 2.0 | Yes self-host | Low ms, medium throughput, durable queues, at-least-once, DLQ native, exchanges |
| 3 | Apache Kafka | Durable event streaming | High ops complexity, partition/rebalance pain | Standard for high throughput streams, replay, ecosystem | OSS `$0`; Confluent Cloud eCKU/CKU/storage/network | 3+ brokers, 16-64 GB RAM/node, SSD | H | Apache 2.0 | Yes self-host | Low-medium latency, very high throughput, log persistence, at-least/exactly-once producer semantics |
| 4 | Apache Pulsar | Multi-tenant streaming + queueing | More components (BookKeeper/ZK/metadata), smaller talent pool | Tiered storage, geo-replication, queue/stream unification | OSS `$0`; StreamNative quote | Brokers + BookKeeper, 3+ nodes | H | Apache 2.0 | Yes self-host | Low latency, high throughput, durable ledger, strong multi-tenancy |
| 5 | Redis Streams | Lightweight persistent streams | Memory pressure, limited replay governance | Simple if Redis exists, consumer groups | OSS/Redis licensing varies; infra only | RAM-heavy, 1-3 nodes | S | BSD/RSAL variants by package | Yes self-host if license approved | Low latency, medium throughput, in-memory + AOF/RDB, at-least-once |
| 6 | Amazon SQS/SNS | Managed queues/topics | External cloud, no local residency, limited ordering unless FIFO | No ops, mature DLQ, cheap per request | SQS: 1M requests/month free, Standard `$0.40/M`, FIFO `$0.50/M`; SNS publish `$0.50/M` | Managed | XS/S | Commercial SaaS | Region-dependent, not local | Medium latency, high scale, durable, at-least-once, DLQ native |
| 7 | Google Pub/Sub | Managed pub/sub streaming | External cloud, egress, ordering constraints | Global managed scale, push/pull, BigQuery integration | First 10 GiB/month basic delivery free; then `$40/TiB`; import topics `$80/TiB`; storage `$0.27/GiB-month` | Managed | XS/S | Commercial SaaS | Region-dependent | Medium latency, very high scale, durable, at-least-once/exactly-once options |
| 8 | Azure Service Bus | Enterprise managed queues/topics | Azure lock-in, throughput by tier | Sessions, DLQ, topics, enterprise support | Basic/Standard/Premium; Standard includes first 13M ops/month; Premium bills Messaging Units/hour; geo-replication `$0.09-$0.23/GB` | Managed | XS/S | Commercial SaaS | Region-dependent | Medium latency, high reliability, DLQ native, filters/topics |
| 9 | ZeroMQ | Embedded messaging library | No broker persistence, app owns reliability | Very fast, minimal dependency, good for internal IPC | `$0 license` | App-local | M | MPL 2.0 | Yes | Very low latency, no built-in persistence/DLQ |
| 10 | NSQ | Simple distributed queue | Smaller ecosystem, fewer enterprise features | Easy ops, decentralized topology | `$0 license` | 2-4 vCPU nodes | S/M | MIT | Yes | Low latency, medium throughput, at-least-once, simple routing |
| 11 | ActiveMQ Artemis | JMS/AMQP/MQTT/STOMP broker | Java ops, less cloud-native mindshare | Protocol rich, mature enterprise messaging | `$0 license` | 2-8 vCPU, 8-32 GB RAM | M | Apache 2.0 | Yes | Low-medium latency, durable, DLQ, JMS semantics |
| 12 | Solace PubSub+ | Enterprise event broker | Commercial quote, lock-in | Strong enterprise routing, appliances, support | Quote / free developer tier | Managed/appliance/self-managed | M/H | Commercial | Possible self-host/private cloud | Low latency, high throughput, strong routing/governance |

**Recommendations**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
|------|---------|---------------------|-----------------|
| Budget | RabbitMQ or Redis Streams | `$1k-8k` | Worker queues, small pilot, known AMQP patterns |
| Optimal | NATS JetStream | `$2k-15k` | Microservices split with simple ops and low latency |
| Enterprise | Kafka or Pulsar | `$25k-150k+` | Event sourcing, high-volume replay, enterprise data streaming |

**Migration paths**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| RabbitMQ -> NATS | Introduce bus abstraction, dual-publish ingestion events, drain queues | Low | Medium |
| NATS -> Kafka | Map subjects to topics, define partitions/keys, run dual-write, replay from object/audit store | Medium | Medium-high |
| Redis Streams -> RabbitMQ/NATS | Consumer group offset export is custom; replay from durable source preferred | Medium | Medium |
| Cloud bus -> self-host | Wrap SDK calls behind interface, replay dead-letter/archive events | Medium | Medium |

---

## 6. Component 3 - LLM Orchestration Framework

**Responsibility:** prompt management, provider routing, chains/graphs, RAG workflow, caching, fallback, observability hooks.

| № | Решение | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | RAG / Agents / Providers / Prompt versioning / Cache / Observability / Maturity |
|---:|---------|------------|-------|--------------|-----------|---------|--------------|----------|------------------|--------------------------------------------------------------------------------|
| 1 | LangChain | Chains, tools, integrations | Abstraction churn, dependency weight | Huge ecosystem, many provider integrations | OSS `$0`; LangSmith paid for tracing/evals | App-level | M | MIT | Yes for OSS | Strong RAG, agents, many providers, LangSmith for versioning/observability |
| 2 | LlamaIndex | RAG data framework | Can duplicate existing retriever abstractions | Strong indexing/query abstractions, doc loaders | OSS `$0`; LlamaCloud/LlamaParse paid | App-level | M | MIT | Yes for OSS | Excellent RAG, agents improving, many providers, good evals |
| 3 | Haystack | Production RAG pipelines | Smaller ecosystem than LangChain | Clean pipeline components, search integration | OSS `$0`; deepset Cloud quote | App-level | M | Apache 2.0 | Yes OSS | Strong RAG, provider integrations, production-friendly |
| 4 | Semantic Kernel | Planner/orchestration SDK | Microsoft ecosystem bias | Good enterprise patterns, C#/Python/Java | OSS `$0`; Azure services billed separately | App-level | M | MIT | Yes OSS | Good orchestration, agents, Azure integrations |
| 5 | LangGraph | Stateful agent/workflow graphs | Adds complexity if simple chain enough | Deterministic graph execution, durable workflows | OSS `$0`; LangSmith optional | App-level | M/H | MIT | Yes OSS | Strong agents/workflows, checkpointing, observability via LangSmith |
| 6 | DSPy | Prompt/program optimization | Requires dataset/eval discipline | Declarative optimization, useful for prompt tuning | OSS `$0` | App-level, eval infra | M/H | MIT | Yes OSS | Good for optimization, not primary RAG runtime |
| 7 | Guidance | Structured generation control | Smaller ecosystem, less production governance | Fine-grained constrained decoding | OSS `$0` | App-level | M | MIT | Yes OSS | Useful for schema/structured output |
| 8 | Instructor | Typed structured outputs | Narrow scope, provider compatibility varies | Simple Pydantic extraction, low dependency | OSS `$0` | App-level | S | MIT | Yes OSS | Great structured output, not full orchestration |
| 9 | LiteLLM | Provider gateway, fallback, budgets | Another service in path, config governance | OpenAI-compatible proxy, routing, budget caps | OSS `$0`; LiteLLM Cloud paid/quote | 1-2 vCPU proxy + DB optional | S/M | MIT for OSS | Yes self-host | Strong provider abstraction/cache/logging |
| 10 | Portkey | AI gateway, routing, observability | SaaS/commercial lock-in if cloud | Guardrails, cache, retries, analytics | OSS gateway + paid cloud/enterprise | Proxy service | S/M | Mixed OSS/commercial | Self-host options need review | Strong gateway features |
| 11 | Helicone | LLM observability/gateway | SaaS residency unless self-host | Simple logs, cache, cost analytics | OSS/self-host; cloud plans | Proxy + ClickHouse/Postgres | S/M | Apache 2.0 / commercial | Yes self-host | Strong observability, not workflow engine |
| 12 | Braintrust | Evals, prompt management, observability | SaaS data/compliance, price quote at scale | Strong evaluation workflow | Free/paid tiers, enterprise quote | SaaS/self-host options vary | M | Commercial | Depends on deployment | Strong eval/prompt governance |

**Recommendations**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
|------|---------|---------------------|-----------------|
| Budget | LiteLLM + Instructor + existing prompt files | `$0-5k` | Need provider fallback and typed outputs without new workflow engine |
| Optimal | LlamaIndex or Haystack + LiteLLM | `$5k-25k` | Production RAG pipelines with clear components |
| Enterprise | LangGraph + LangSmith/Portkey/Braintrust | `$25k-100k+` | Complex multi-step workflows, eval governance, human-in-loop |

**Migration paths**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| Current hand-written pipeline -> LiteLLM | Keep `LLMClient` API, route provider calls through proxy | Low | Low |
| LiteLLM -> LangChain/LlamaIndex/Haystack | Wrap existing retriever/generator as components | Low-medium | Medium |
| LangChain -> LangGraph | Convert linear chain to graph nodes gradually | Low | Medium |
| SaaS observability -> self-host | Export logs/evals, standardize `run_id` and OpenTelemetry spans | Medium | Medium |

---

## 7. Component 4 - Document Parsing / Ingestion

**Responsibility:** extract text, layout, tables and references from DOCX/XLSX/PDF/PPTX while preserving locators.

| № | Решение | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Formats / Layout / Tables / OCR / Speed / GPU / Multilingual |
|---:|---------|------------|-------|--------------|-----------|---------|--------------|----------|------------------|---------------------------------------------------------------|
| 1 | Unstructured.io | Multi-format partitioning | Some features/API commercial, parser variability | Broad formats, chunking strategies | OSS `$0`; hosted API/platform paid/quote | CPU, optional OCR deps | M | Apache 2.0 core | Yes OSS self-host | DOCX/XLSX/PDF/PPTX, good layout, OCR optional |
| 2 | Docling (IBM) | PDF/DOCX structure extraction | Young but active, model downloads | Strong layout/table pipeline, local-first | `$0 license` | CPU works; GPU helps OCR/layout models | M | MIT | Yes | PDF/DOCX/HTML/images, good layout/tables/OCR |
| 3 | Marker | PDF to Markdown/JSON | GPU recommended for speed/quality, PDF-focused | High-quality PDF markdown extraction | OSS `$0` | GPU preferred, CPU slower | M | GPL/other components need review | Yes if license accepted | PDF/images, good layout/OCR |
| 4 | MinerU | Document parsing/OCR | Heavier ML stack, ops complexity | Strong academic/enterprise doc parsing | OSS `$0` | GPU preferred | M/H | AGPL/Apache mix depending package, review required | Yes if license accepted | PDF/images, OCR/layout strong |
| 5 | olmOCR | OCR for documents | OCR-only layer, model/runtime cost | Local OCR for scanned PDFs | OSS `$0` | GPU recommended | M | Apache 2.0 | Yes | OCR strong, combine with parser |
| 6 | PyMuPDF | PDF text/images/layout primitives | Manual structure logic needed | Fast, reliable, simple | OSS/commercial dual; AGPL/commercial review | CPU | S | AGPL/commercial | Yes if license accepted | PDF only, layout primitives, no OCR |
| 7 | pdfplumber | PDF text/tables | Slower, PDF quirks | Good table/debug extraction | `$0 license` | CPU | S | MIT | Yes | PDF tables/layout, no OCR |
| 8 | Camelot | PDF table extraction | Works best on text PDFs, Java/Ghostscript deps | Focused table extraction | `$0 license` | CPU | S/M | MIT | Yes | PDF tables strong for lattice/stream |
| 9 | Tabula-py | PDF table extraction | Java dependency, scanned PDFs need OCR | Mature simple table extraction | `$0 license` | CPU + Java | S/M | MIT | Yes | PDF tables |
| 10 | LlamaParse | Managed parsing API | SaaS, data residency, usage cost | Fast high-quality parsing, integrates LlamaIndex | Paid credits/subscription | Managed | XS/S | Commercial SaaS | No local by default | Broad formats, strong layout, OCR managed |
| 11 | Azure Document Intelligence | OCR/forms/layout/tables | Azure lock-in, residency approval | Mature enterprise OCR/layout | Free 500 pages/month; Read `$1.50/1k pages`, Layout/Prebuilt `$10/1k`, custom extraction `$30/1k` | Managed | S/M | Commercial SaaS | Region-dependent | Broad docs, strong OCR/tables |
| 12 | Google Document AI | OCR/processors/extractors | GCP lock-in, custom processor cost | Strong managed extraction, human review options | OCR `$1.50/1k pages`, Layout `$10/1k`, Form Parser/Custom Extractor `$30/1k` | Managed | S/M | Commercial SaaS | Region-dependent | Broad docs, strong OCR/layout |
| 13 | Amazon Textract | OCR/forms/tables/queries | AWS lock-in, per-page cost | Mature OCR, forms/tables, async jobs | Detect text starts around `$1.50/1k pages`; tables/forms/queries higher by feature and region | Managed | S/M | Commercial SaaS | Region-dependent | PDF/images, strong OCR/tables |
| 14 | python-docx + openpyxl | DOCX/XLSX custom parser | Limited PDFs/OCR, custom layout logic | Already fits current code, deterministic | `$0 license` | CPU | S | MIT | Yes | DOCX/XLSX good enough, no OCR |

**Recommendations**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
|------|---------|---------------------|-----------------|
| Budget | python-docx/openpyxl + PyMuPDF/pdfplumber | `$0-5k` | Text DOCX/XLSX/PDF, deterministic locators, no scanned-heavy docs |
| Optimal | Docling + Unstructured + custom locator layer | `$5k-20k` | Mixed PDF/DOCX with layout/table preservation and local residency |
| Enterprise | Azure DI / Textract / Document AI / LlamaParse | `$20k-100k+` usage | High OCR quality, scanned docs, managed SLA and review workflows |

**Migration paths**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| Current parsers -> Docling/Unstructured | Keep `load_requirements_by_extension`, enrich locator fields additively | Low | Medium |
| Local parsers -> managed OCR | Route only scanned/failed docs to SaaS, store raw + extracted JSON | Low | Medium |
| Managed OCR -> local | Preserve canonical `DocumentBlock` JSON, re-run extraction asynchronously | Medium | Medium |
| One parser -> ensemble | Add confidence and provenance per block, keep best block by type | Low | Medium |

---

## 8. Component 5 - Embedding Models

**Responsibility:** convert chunks and queries into vectors for semantic and hybrid retrieval.

| № | Решение | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Dim / RU+EN / Max length / Speed / Size / Benchmark / API cost |
|---:|---------|------------|-------|--------------|-----------|---------|--------------|----------|------------------|----------------------------------------------------------------|
| 1 | BAAI/bge-m3 | Multilingual dense+sparse embeddings | Local model ops, CPU latency | Strong multilingual/RU, current candidate, long context | `$0 license`; infra only | CPU usable, GPU faster; ~2 GB model class | S/M | MIT | Yes local | 1024 dim, RU/EN strong, 8192 tokens |
| 2 | all-MiniLM-L6-v2 | Cheap small embeddings | English-biased, lower RU/domain quality | Very fast CPU baseline | `$0 license` | CPU, small memory | XS/S | Apache 2.0 | Yes | 384 dim, short max length, fast |
| 3 | OpenAI text-embedding-3-large | High-quality API embeddings | External SaaS, data residency, token cost | Strong multilingual, dimensions shortening | `$0.13 / 1M tokens`, batch `$0.065` | Managed | S | Commercial API | No local; region/data policy approval needed | 3072 dim default, strong RU/EN |
| 4 | OpenAI text-embedding-3-small | Cheap API embeddings | Same SaaS risks | Very low price, good baseline | `$0.02 / 1M tokens`, batch `$0.01` | Managed | S | Commercial API | No local | 1536 dim default |
| 5 | Cohere embed-multilingual-v3/v4 | Multilingual enterprise embeddings | SaaS/commercial, pricing/version changes | Strong multilingual, enterprise support | Public pricing page; commonly per-token usage, verify quote | Managed | S | Commercial API | No local unless private deployment agreed | RU/EN strong, API |
| 6 | Voyage AI voyage-3 | Retrieval-optimized API embeddings | SaaS, smaller enterprise footprint | Strong retrieval benchmarks, rerank pairing | Public usage pricing, verify current model rate | Managed | S | Commercial API | No local | Dim/model-dependent |
| 7 | Nomic embed-text | Open/local embeddings | Quality varies by language/domain | Open weights, local/private | `$0 license` for open model; Nomic API paid | CPU/GPU local | S/M | Apache 2.0 for model variants | Yes local | Good EN, RU must benchmark |
| 8 | jina-embeddings-v3/v4/v5 | Multilingual long-context embeddings | API/local version selection, license review | Strong multilingual, long context, API or local | Open weights/API paid tiers | CPU/GPU local or managed | M | CC BY-NC / Apache/commercial varies by model, review required | Local possible if license accepted | RU/EN strong, long context |
| 9 | e5-mistral-7b-instruct | High-quality instruct embeddings | Large/slow, GPU-heavy | Strong benchmark quality | `$0 license` | GPU recommended, 7B class | M/H | MIT/Apache model-card review | Yes local | 4096 dim class, high quality |
| 10 | intfloat/multilingual-e5-large | Multilingual retrieval embeddings | Older vs bge-m3, local ops | Strong multilingual baseline | `$0 license` | CPU/GPU, ~1 GB class | S/M | MIT | Yes local | 1024 dim, RU/EN strong |
| 11 | GigaChat embeddings | RU provider embeddings | Provider access/pricing, external API | RU ecosystem, local compliance may be easier than US SaaS | Provider tariff/quote | Managed | S | Commercial API | RU provider, contract-dependent | RU strong, API |
| 12 | YandexGPT embeddings | RU provider embeddings | Provider lock-in, tariff changes | RU cloud ecosystem, possible data residency | Provider tariff/quote | Managed | S | Commercial API | RU cloud/contract-dependent | RU strong, API |

**Recommendations**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
|------|---------|---------------------|-----------------|
| Budget | bge-m3 local | `$1k-8k` infra | Default RU-resident retrieval with good quality |
| Optimal | bge-m3 + multilingual-e5/Jina benchmark fallback | `$5k-20k` | Need quality A/B without external data transfer |
| Enterprise | OpenAI/Cohere/Voyage/RU provider API with local fallback | `$10k-100k+` usage | Strong quality, managed throughput, approved external processing |

**Migration paths**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| Any embedding model -> another | Re-embed corpus into parallel index, run retrieval eval, switch alias | Low with dual index | Medium |
| Local -> API | Add batch embedding worker, redact PII before calls, cache by text hash | Low | Medium-high compliance |
| API -> local | Keep original text/chunk IDs, re-embed asynchronously, compare recall/MRR | Low-medium | Medium |
| 768 dim -> 1024/3072 dim | Requires new vector index/schema; cannot mix dims in same field | Medium | Medium |

---

## 9. Component 6 - Local LLM Serving

**Responsibility:** serve local models for PII-sensitive generation, routing/classification, fallback, batch jobs.

| № | Решение | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Quant / Throughput / TTFT / GPU / CPU / Multi-GPU / Batching / API / Formats |
|---:|---------|------------|-------|--------------|-----------|---------|--------------|----------|------------------|--------------------------------------------------------------------------------|
| 1 | Ollama | Simple local model serving | Lower throughput, limited production controls | Fast install, GGUF, local dev | `$0 license` | CPU or GPU, 8-24 GB VRAM for 7B-13B | XS/S | MIT | Yes local | Good quant, CPU/GPU, OpenAI-compatible partial |
| 2 | vLLM | High-throughput inference | GPU-first, ops tuning | PagedAttention, continuous batching, OpenAI API | `$0 license` | NVIDIA GPU, 16-80 GB VRAM | M | Apache 2.0 | Yes local | Excellent throughput/batching, multi-GPU |
| 3 | TGI | HF production serving | GPU ops, model compatibility | Mature server, streaming, quantization | `$0 license` | GPU recommended | M | Apache 2.0 | Yes local | Good throughput, safetensors |
| 4 | llama.cpp | CPU/GPU GGUF inference | Lower throughput for high concurrency | Very portable, quantization, edge/offline | `$0 license` | CPU viable, Metal/CUDA/Vulkan | S/M | MIT | Yes local | Excellent quant, CPU-only strong, GGUF |
| 5 | TensorRT-LLM | NVIDIA optimized inference | NVIDIA lock-in, complex build | Best latency/throughput on NVIDIA | `$0 license` | NVIDIA GPU, high VRAM | H | Apache 2.0 | Yes local | Excellent throughput, multi-GPU |
| 6 | DeepSpeed-MII/Inference | Distributed inference | Complex, less simple than vLLM | Large model distributed serving | `$0 license` | Multi-GPU | H | MIT | Yes local | Multi-GPU strong |
| 7 | HF Transformers native | Baseline model execution | Not optimized serving by default | Maximum compatibility, easy experiments | `$0 license` | CPU/GPU | S/M | Apache 2.0 | Yes local | Good for experiments, not high QPS |
| 8 | CTranslate2 | Efficient CPU/GPU inference | Model conversion required, less LLM-chat ecosystem | Fast CPU/GPU, quantized | `$0 license` | CPU/GPU | M | MIT | Yes local | Strong CPU, model format conversion |
| 9 | MLX | Apple Silicon local inference | Mac-only, not server standard | Great developer laptops/M-series | `$0 license` | Apple Silicon unified memory | S | MIT | Local only | Metal, local dev |
| 10 | Exo | Decentralized local inference | Young, production maturity risk | Multi-device local experiments | OSS `$0` | Multiple local devices | M/H | Apache/MIT review | Yes local | Experimental distributed serving |
| 11 | Replicate self-host / Cog | Model packaging/deploy | SaaS path external, self-host ops | Reproducible model containers | OSS tools + cloud paid | Docker/GPU | M | Apache 2.0 tools / commercial cloud | Self-host possible | Good packaging |
| 12 | BentoML | Model service packaging | Need infra decisions, not LLM-specific enough alone | API packaging, deployment, scaling | OSS `$0`; BentoCloud paid | CPU/GPU | M | Apache 2.0 | Yes self-host | Good service framework |

**Recommendations**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
|------|---------|---------------------|-----------------|
| Budget | Ollama / llama.cpp | `$1k-8k` | Single-node pilot, easy install, offline demos |
| Optimal | vLLM or TGI | `$10k-60k` GPU infra | Production pilot with concurrency and OpenAI-compatible API |
| Enterprise | TensorRT-LLM + KServe/BentoML | `$60k-300k+` | Dedicated GPU platform, strict latency/SLA |

**Migration paths**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| Ollama -> vLLM | Keep OpenAI-compatible client, change base URL/model names, validate prompts | Low | Medium |
| vLLM -> TGI | Abstract streaming/chat payload differences | Low-medium | Medium |
| Local -> managed API | Route through LiteLLM, retain local fallback for PII | Low | Compliance high |
| Single GPU -> multi-GPU | Benchmark tensor/pipeline parallelism, pin model versions | Medium | High |

---

## 10. Component 7 - Cross-Encoder Reranker

**Responsibility:** rerank top-K retrieval candidates to improve precision and grounding.

| № | Решение | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Accuracy / Latency / Size / GPU vs CPU / API cost / Languages / Integration |
|---:|---------|------------|-------|--------------|-----------|---------|--------------|----------|------------------|----------------------------------------------------------------------------|
| 1 | BAAI/bge-reranker-large | Local high-quality rerank | CPU latency, GPU needed for p95 | Strong multilingual, popular | `$0 license` | GPU recommended; CPU slower | S/M | MIT | Yes local | High accuracy, medium-high latency |
| 2 | BAAI/bge-reranker-base | Local balanced rerank | Lower quality than large | Better latency/cost | `$0 license` | CPU/GPU | S | MIT | Yes local | Good accuracy, medium latency |
| 3 | Cohere Rerank API | Managed reranking | SaaS/residency, usage cost | Strong multilingual, simple API | Public pricing/check current rate; OpenRouter lists rerank-v3.5 per search | Managed | S | Commercial API | No local | High accuracy, low integration cost |
| 4 | Jina Reranker | API/local reranker | License/model/version review | Multilingual, listwise models | API paid; local model possible | Managed or GPU local | M | Mixed model licenses | Local possible | High multilingual quality |
| 5 | Voyage AI rerank | Managed reranking | SaaS/residency | Strong retrieval stack | Usage pricing, verify current | Managed | S | Commercial API | No local | High accuracy, simple API |
| 6 | cross-encoder/ms-marco-MiniLM-L-6-v2 | Small local reranker | English-biased, RU lower | Very fast CPU baseline | `$0 license` | CPU | XS/S | Apache 2.0 | Yes local | Medium accuracy, low latency |
| 7 | cross-encoder/ms-marco-TinyBERT-L-2-v2 | Tiny local reranker | Lower quality | Very low latency | `$0 license` | CPU | XS/S | Apache 2.0 | Yes local | Low-medium accuracy |
| 8 | NV-RerankQA | NVIDIA reranker | Hardware/vendor dependence | Optimized enterprise AI stack | API/NVIDIA platform quote | GPU/API | M | Commercial/model license | Local possible with NVIDIA stack | High performance, enterprise support |
| 9 | RankGPT | LLM-based reranking | Expensive/slow, hallucination risk | Strong reasoning over candidates | Depends on LLM tokens | LLM API/local | M | Method, not product | Local if local LLM | High accuracy, high latency |
| 10 | ColBERT v2 | Late-interaction retrieval/rerank | Index/storage complexity | Strong precision with token-level matching | `$0 license`; infra | GPU for indexing, larger index | H | MIT | Yes local | High quality, higher storage |
| 11 | FlashRank | Lightweight reranking library | Model choices limited | Simple CPU rerank for app | `$0 license` | CPU | XS/S | Apache 2.0 | Yes local | Good budget quality |
| 12 | Pinecone hosted rerank | Managed rerank inside vector platform | Vendor lock-in/SaaS | Integrated with Pinecone retrieval | Included quotas + usage | Managed | S | Commercial SaaS | Region-dependent | Simple if already Pinecone |

**Recommendations**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
|------|---------|---------------------|-----------------|
| Budget | FlashRank or MiniLM | `$0-3k` | CPU-only pilot, precision boost without GPU |
| Optimal | bge-reranker-base/large | `$5k-30k` | Local RU-resident rerank for top-20/top-50 |
| Enterprise | Cohere/Jina/Voyage or ColBERT | `$15k-100k+` | Highest precision with approved SaaS or dedicated infra |

**Migration paths**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| No reranker -> local reranker | Add optional rerank stage after top-K retrieval, feature flag | Low | Low |
| Local -> API | Route only de-identified snippets, cache scores by query/chunk hash | Low | Compliance medium-high |
| Cross-encoder -> ColBERT | Requires new indexing pipeline and storage, A/B side-by-side | Medium-high | High |
| API -> local | Keep scoring contract `{chunk_id, score}`, replace provider | Low | Medium |

---

## 11. Component 8 - Observability Stack

**Responsibility:** logs, metrics, traces, alerting, dashboards, incident/debug workflow.

| № | Решение | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Signals / Storage / Query / Alerting / Dashboards / Self-host / Cost / Community |
|---:|---------|------------|-------|--------------|-----------|---------|--------------|----------|------------------|--------------------------------------------------------------------------------|
| 1 | Prometheus + Grafana + Loki + Jaeger | OSS metrics/logs/traces | Multi-tool ops, retention tuning | Standard stack, self-hosted, broad community | `$0 license`; infra only | 2-8 vCPU, 8-32 GB RAM + storage | M | Apache 2.0 / AGPL for Grafana | Yes | All signals with components, PromQL/LogQL |
| 2 | ELK Stack | Logs/search/dashboards | Elastic license, resource-heavy | Strong logs/search, mature | Self-managed basic + infra; Elastic Cloud usage | JVM/storage heavy | M/H | Elastic License/SSPL/AGPL options | Yes self-host | Logs strong, metrics/traces via integrations |
| 3 | OpenTelemetry + Tempo + Grafana | Standard traces/metrics/logs pipeline | Requires instrumentation discipline | Vendor-neutral, future-proof | `$0 license`; infra | Collector + backend storage | M | Apache 2.0 / AGPL | Yes | All signals via OTel, good traces |
| 4 | Datadog | Full SaaS observability | Cost growth, SaaS residency | Fast setup, great UX, broad integrations | Per host/container/log/APM usage | Managed agents | S | Commercial SaaS | Region/contract-dependent | All signals, strong alerting |
| 5 | New Relic | SaaS observability | Ingest/user pricing, SaaS | Unified data platform, good APM | Usage/user based, free tier | Managed agents | S | Commercial SaaS | Region/contract-dependent | All signals |
| 6 | Dynatrace | Enterprise observability | Expensive/quote, lock-in | Strong AIOps, enterprise support | DPS/quote | Managed/agents | M | Commercial SaaS/self-host options | Contract-dependent | All signals, strong automation |
| 7 | Honeycomb | Event/tracing observability | SaaS, less log-storage focus | Excellent high-cardinality traces | Events/usage plans | Managed | S/M | Commercial SaaS | Region-dependent | Traces/events strong |
| 8 | SigNoz | OSS observability on ClickHouse | ClickHouse ops, younger than Grafana | Single OSS observability platform | OSS `$0`; cloud paid | ClickHouse + services | M | MIT/Apache mix | Yes self-host | Logs/metrics/traces |
| 9 | Grafana Cloud | Managed Grafana stack | SaaS residency/cost | Familiar Grafana without ops | Free/usage tiers | Managed agents | S | Commercial SaaS | Region-dependent | Metrics/logs/traces/profiles |
| 10 | ClickHouse + Grafana | Custom logs/metrics analytics | Build/maintain own schemas | Very cost-effective high-volume logs | OSS `$0`; ClickHouse Cloud credits/usage | CPU/storage for ClickHouse | M/H | Apache 2.0 | Yes self-host | Logs/events analytics strong |
| 11 | VictoriaMetrics | Metrics TSDB | Logs/traces need other tools | Simple, efficient Prometheus-compatible metrics | OSS `$0`; enterprise/cloud paid | Low-medium | S/M | Apache 2.0 / enterprise | Yes | Metrics strong |
| 12 | Sentry | Error tracking/performance | Not full infra observability | Best app exception workflow | Free/paid per event/user | Managed or self-host | S | Business Source License / commercial | Self-host possible | Errors/performance, not logs TSDB |

**Recommendations**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
|------|---------|---------------------|-----------------|
| Budget | Prometheus + Grafana + Loki | `$2k-12k` | Self-host pilot with basic dashboards |
| Optimal | OpenTelemetry + Grafana/Tempo/Loki + Sentry | `$5k-30k` | Microservices with portable traces and useful app errors |
| Enterprise | Datadog/New Relic/Dynatrace/Honeycomb | `$30k-200k+` | 24/7 operations, enterprise alerting, low ops burden |

**Migration paths**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| Logs only -> OTel | Add trace IDs and OpenTelemetry SDK/exporter | Low | Medium |
| Grafana OSS -> Grafana Cloud | Point remote_write/log export to cloud, keep dashboards as code | Low | Low-medium |
| SaaS -> self-host | Export dashboards/alerts where possible, keep OTel as neutral pipeline | Medium | Medium |
| ELK -> Loki/ClickHouse | Re-emit logs through collector, preserve `run_id`/`trace_id` fields | Medium | Medium |

---

## 12. Component 9 - Audit Database

**Responsibility:** immutable audit events: who called what, when, model/provider, prompt/version, retrieval evidence, PII mask hash.

| № | Решение | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Write / Query / Compression / Retention / WORM / SQL / Scale / Cost / Compliance |
|---:|---------|------------|-------|--------------|-----------|---------|--------------|----------|------------------|--------------------------------------------------------------------------------|
| 1 | PostgreSQL | Transactional audit + metadata | Large log analytics can bloat, retention tuning | Already familiar, ACID, simple WORM via roles/triggers | `$0 license`; managed/self-host cost | 2-8 vCPU, 8-32 GB RAM | S/M | PostgreSQL | Yes | Medium write, strong SQL, WORM by design |
| 2 | ClickHouse | Append-only analytics/logs | Needs schema discipline, less OLTP | Very fast analytics, compression, cheap storage | OSS `$0`; Cloud $300 credits/usage | 4-16 vCPU, SSD/object storage | M | Apache 2.0 | Yes | High write, fast analytics, TTL |
| 3 | TimescaleDB | Time-series on Postgres | License/compression features review | Hypertables, retention, SQL | OSS/community + cloud paid | Postgres-like | M | Timescale license / Apache components | Yes self-host | Medium-high write, SQL |
| 4 | InfluxDB | Time-series metrics/events | Less natural relational audit joins | Fast time-series ingestion, retention | Cloud usage examples: data in `$0.0025/MB`, query `$0.012/100`, storage `$0.002/GB-hour`, out `$0.09/GB`; OSS options | 2-8 vCPU | M | MIT/Commercial depending version | Yes self-host | High write, retention |
| 5 | Elasticsearch | Audit log search | Cost/resource heavy, license | Powerful text search and Kibana | Self-managed/cloud pricing | JVM/storage | M/H | Elastic licenses | Yes self-host | High write, search strong |
| 6 | MongoDB | Document audit events | Analytics less efficient than columnar | Flexible schema, easy JSON events | Community `$0`; Atlas paid | 2-8 vCPU | S/M | SSPL/community/commercial | Yes self-host if license approved | Medium write, flexible |
| 7 | Apache Doris | OLAP analytics | Less common locally, ops | MPP SQL analytics | OSS `$0`; cloud paid | Cluster, 3+ nodes | H | Apache 2.0 | Yes | High write/query |
| 8 | DuckDB | Embedded analytics | Not concurrent production DB | Cheap local reports over parquet | `$0 license` | Local CPU | XS/S | MIT | Yes | Small-scale analytics |
| 9 | Amazon Athena | Serverless SQL over S3 | AWS lock-in, data lake governance | No servers, cheap occasional queries | Per TB scanned | Managed + S3 | S | Commercial SaaS | Region-dependent | Good analytics, no OLTP |
| 10 | Google BigQuery | Serverless data warehouse | GCP lock-in, cost if bad queries | Mature analytics, IAM, scale | On-demand `$6.25/TiB` scanned after free tier; storage extra | Managed | S/M | Commercial SaaS | Region-dependent | Very high scale |
| 11 | Snowflake | Data warehouse | Quote/credit complexity, SaaS | Enterprise governance, sharing | Credit/storage usage, quote | Managed | M | Commercial SaaS | Region-dependent | High scale/compliance |
| 12 | Azure Synapse | Azure analytics | Azure lock-in, complexity | Enterprise data platform | DWU/serverless usage | Managed | M/H | Commercial SaaS | Region-dependent | High scale |

**Recommendations**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
|------|---------|---------------------|-----------------|
| Budget | PostgreSQL append-only | `$1k-8k` | Pilot audit, simple SQL reports, minimal infra |
| Optimal | PostgreSQL metadata + ClickHouse events | `$5k-25k` | High event volume with fast analytics and local residency |
| Enterprise | ClickHouse Cloud/BigQuery/Snowflake | `$30k-200k+` | Large analytics, BI, compliance reporting, managed SLA |

**Migration paths**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| PostgreSQL -> ClickHouse | CDC or batch copy audit rows, keep Postgres as source of truth first | Low | Medium |
| ClickHouse -> BigQuery/Snowflake | Export parquet to object storage, load partitions by date | Low-medium | Medium |
| Elasticsearch logs -> ClickHouse | Reindex `_source` to columnar schema, preserve IDs | Medium | Medium |
| Any -> WORM archive | Periodic parquet/JSONL signed export to object storage with retention lock | Low | Low |

---

## 13. Component 10 - Object Storage

**Responsibility:** raw uploaded files, parser artifacts, extracted JSON, reports, snapshots, audit archives.

| № | Решение | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | S3 API / Cost / Transfer / Durability / Versioning / Lifecycle / Encryption / Managed |
|---:|---------|------------|-------|--------------|-----------|---------|--------------|----------|------------------|------------------------------------------------------------------------------------|
| 1 | MinIO | Self-hosted S3-compatible storage | Ops/backups/erasure coding, AGPL/commercial implications | Local S3 API, simple, high performance | OSS/commercial; infra only | 4+ disks for HA, 4-16 vCPU | M | AGPL v3 / commercial | Yes | Strong S3, versioning/lifecycle/encryption |
| 2 | Amazon S3 | Managed object storage | External cloud, egress, residency | Mature, durable, lifecycle, object lock | Standard storage example around `$0.023/GB-month` in us-east-1 + requests/egress | Managed | XS/S | Commercial SaaS | Region-dependent | Strongest managed S3 |
| 3 | Yandex Object Storage | RU cloud S3-compatible | Provider lock-in, tariff changes | RU residency path, S3 API | RUB tariff by storage/requests/traffic | Managed | S | Commercial SaaS | Yes RU cloud | S3-compatible, lifecycle/encryption |
| 4 | Selectel Cloud Storage | RU provider object storage | Contract/tariff dependency | RU residency, S3 API | Provider tariff | Managed | S | Commercial SaaS | Yes RU | S3-compatible |
| 5 | Ceph | Self-hosted distributed storage | High ops complexity | Enterprise self-host, S3/RBD/CephFS | `$0 license`; hardware/ops | 3+ storage nodes, disks/network | H | LGPL/GPL mix | Yes | S3 via RGW, high durability if operated well |
| 6 | Azure Blob Storage | Managed object/blob storage | Azure lock-in, region approval | Tiers, lifecycle, immutability | Hot/cool/archive GB-month + operations/egress | Managed | S | Commercial SaaS | Region-dependent | Strong lifecycle/encryption |
| 7 | Google Cloud Storage | Managed object storage | GCP lock-in, egress | Tiers, IAM, lifecycle | Standard regional examples around `$0.020-0.026/GB-month` by region | Managed | S | Commercial SaaS | Region-dependent | Strong lifecycle/encryption |
| 8 | OpenStack Swift | Self-hosted object storage | Ops complexity, smaller modern ecosystem | Open-source object storage for private cloud | `$0 license`; infra | 3+ nodes | H | Apache 2.0 | Yes | S3-compatible via gateways, native Swift |
| 9 | SeaweedFS | Simple distributed file/object store | Smaller enterprise support | Lightweight, S3 API, fast | `$0 license` | 3+ nodes for HA | M | Apache 2.0 | Yes | S3-compatible, simple ops |
| 10 | GarageFS | Lightweight geo-distributed object store | Younger ecosystem | Simple self-hosted S3-compatible storage | `$0 license` | Small nodes possible | M | AGPL v3 | Yes | S3-compatible, versioning limited |
| 11 | Local filesystem | Single-node files | No HA, backup risk, path coupling | Cheapest and simplest for offline pilot | Existing disk | Single server | XS | N/A | Yes | No S3 unless wrapped |
| 12 | NFS/SMB share | Shared filesystem | Locking/perf/HA issues | Reuses enterprise NAS | Existing NAS/license | NAS/server | S/M | N/A | Yes if on-prem | No object semantics |

**Recommendations**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
|------|---------|---------------------|-----------------|
| Budget | Local FS or MinIO single node | `$0-5k` | Offline demo/pilot, manual backups acceptable |
| Optimal | MinIO HA or RU S3-compatible provider | `$5k-30k` | Production pilot with RU residency and object API |
| Enterprise | S3/Azure/GCS/Ceph | `$20k-150k+` | High durability, lifecycle, object lock, enterprise backup |

**Migration paths**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| Local FS -> S3/MinIO | Introduce object store interface, upload files by content hash, keep path alias | Low | Low-medium |
| MinIO -> S3/Yandex/Selectel | `mc mirror`/S3 sync, preserve bucket/key layout | Low | Low |
| Cloud S3 -> self-host | S3 batch export/sync, verify object hashes and metadata | Medium | Medium |
| NFS -> object storage | Convert path references to object keys, update report links | Medium | Medium |

---

## 14. Component 11 - Cache Layer

**Responsibility:** LLM response cache, retrieval result cache, sessions, rate limits, locks, ephemeral state.

| № | Решение | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Throughput / p99 / Persistence / Eviction / Cluster / Memory / PubSub / Redis API |
|---:|---------|------------|-------|--------------|-----------|---------|--------------|----------|------------------|----------------------------------------------------------------------------|
| 1 | Redis | General cache, sessions, queues | License changes, memory cost | Standard ecosystem, TTL, pub/sub, streams | Source available/OSS variants; Redis Cloud paid | RAM sized to hotset | S/M | BSD for older, RSAL/SSPL for newer Redis Ltd; Valkey Apache 2.0 alternative | Yes if self-host/license approved | Very high throughput, low p99 |
| 2 | Memcached | Simple cache | No persistence/structures | Extremely simple, fast | `$0 license` | RAM | XS/S | BSD | Yes | High throughput, no persistence |
| 3 | Dragonfly | Redis-compatible high-performance cache | Younger than Redis | Efficient multi-threaded, Redis API | OSS `$0`; cloud paid/quote | RAM, fewer nodes | S/M | BSL/Apache terms by version, review | Yes self-host if license ok | Very high throughput |
| 4 | KeyDB | Redis fork | Ecosystem uncertainty | Multi-threaded Redis-compatible | `$0 license` | RAM | S/M | BSD | Yes | High throughput |
| 5 | Redis Cluster | Sharded Redis | Cluster ops, client behavior | Scale hotset, HA | infra/license | Multiple RAM nodes | M | Redis licensing as above | Yes | High throughput/HA |
| 6 | Hazelcast | Distributed in-memory data grid | Java/cluster ops, overkill for simple cache | Enterprise clustering, compute near data | OSS + enterprise quote | RAM cluster | M/H | Apache 2.0 core / commercial | Yes | High throughput, rich cluster |
| 7 | Apache Ignite | In-memory compute/data grid | Complexity, heavier ops | SQL, compute grid, persistence | `$0 license` | RAM/SSD cluster | H | Apache 2.0 | Yes | High throughput, complex |
| 8 | Aerospike | Low-latency KV | Commercial for enterprise features | Very high scale, SSD/RAM hybrid | Community/enterprise quote | RAM+SSD nodes | H | AGPL/commercial | Yes if license accepted | Very high throughput |
| 9 | etcd | Coordination KV | Not for high-volume cache | Strong consistency, locks/config | `$0 license` | 3 small nodes | M | Apache 2.0 | Yes | Low throughput cache, strong consistency |
| 10 | Consul KV | Service discovery/config KV | Not hot cache | Service discovery + KV | OSS/enterprise | 3 nodes | M | BUSL/commercial changes, review | Yes if license approved | Moderate KV |
| 11 | In-memory local cache | Per-process LRU/TTL | No sharing, cold restarts | Zero infra, fastest | `$0` | App memory | XS | N/A | Yes | Very low latency, no persistence |
| 12 | CDN cache (Cloudflare) | Edge HTTP cache | External, not private LLM cache | Great static/API edge cache | Free/paid tiers | Managed | S | Commercial SaaS | Region-dependent | HTTP cache/rate limits |

**Recommendations**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
|------|---------|---------------------|-----------------|
| Budget | local cache + Memcached/Valkey | `$0-3k` | Single-node pilot, low operational overhead |
| Optimal | Redis/Valkey or Dragonfly | `$3k-20k` | Shared sessions, LLM cache, rate limits |
| Enterprise | Redis Cluster/Cloud, Hazelcast, Aerospike | `$20k-120k+` | HA, multi-tenant cache, very high throughput |

**Migration paths**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| Local cache -> Redis/Valkey | Add cache interface and TTL policy, accept cold start | None | Low |
| Redis -> Dragonfly/KeyDB/Valkey | Verify command compatibility, run shadow traffic | Low | Low-medium |
| Redis single -> cluster | Add key hash tags and cluster-aware client | Medium | Medium |
| Cache provider switch | Cache is disposable; preserve only session/auth if used | Low | Low |

---

## 15. Component 12 - API Gateway

**Responsibility:** ingress, routing, auth, rate limiting, request transforms, OpenAPI, WebSocket/gRPC edge.

| № | Решение | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | RPS / Auth / Rate limit / Transform / Circuit breaker / Discovery / WS / gRPC / OpenAPI |
|---:|---------|------------|-------|--------------|-----------|---------|--------------|----------|------------------|-------------------------------------------------------------------------------------|
| 1 | FastAPI | App API + lightweight gateway | Not full gateway alone | Already Python, OpenAPI built-in, fast | `$0 license` | App server | S | MIT | Yes | Good RPS, JWT/OAuth libs, OpenAPI |
| 2 | NGINX + Lua | Reverse proxy/gateway | Lua/plugin maintenance | Mature, fast, simple edge | OSS `$0`; NGINX Plus paid | 1-2 vCPU | S/M | BSD-like / commercial Plus | Yes | High RPS, rate limit, TLS |
| 3 | Kong Gateway | API gateway/plugins | DB/plugin ops, enterprise features paid | Mature plugins, auth/rate limit, hybrid mode | OSS + Enterprise quote/cloud | 2-4 vCPU + DB | M | Apache 2.0 core / commercial | Yes self-host | Strong gateway features |
| 4 | Traefik | Cloud-native ingress | Less enterprise API governance than Kong | Simple Docker/K8s routing, auto TLS | OSS + Enterprise | 1-2 vCPU | S | MIT | Yes | Good routing, middleware |
| 5 | Envoy Proxy | L7 proxy/service mesh building block | Config complexity | High performance, gRPC, xDS | `$0 license` | 1-4 vCPU | M/H | Apache 2.0 | Yes | Strong gRPC/circuit breaker |
| 6 | Apache APISIX | API gateway on NGINX/OpenResty | Plugin/control-plane ops | High performance, dynamic config | `$0 license`; enterprise/cloud paid | 2-4 vCPU + etcd | M | Apache 2.0 | Yes | Strong auth/rate/plugins |
| 7 | Tyk | API management | Commercial features, ops | Strong API management and portal | OSS gateway + paid dashboard/cloud | 2-4 vCPU + DB | M | MPL/commercial | Yes self-host | Strong management |
| 8 | AWS API Gateway | Managed API gateway | AWS lock-in, latency/cost | No ops, auth/throttling, Lambda integration | HTTP API example `$1.00/M requests`; REST API example `$3.50/M` first tier, plus data/cache/private link | Managed | XS/S | Commercial SaaS | Region-dependent | Strong managed features |
| 9 | Cloudflare Workers | Edge gateway/functions | External edge/data path | Global edge, WAF, rate limits | Free 100k requests/day; Standard includes 10M/month, then `$0.30/M` requests and `$0.02/M` CPU-ms | Managed | S | Commercial SaaS | Global, not local | Edge scale |
| 10 | Express.js | Node API gateway | Another stack, less type safety | Simple JS ecosystem | `$0 license` | App server | S | MIT | Yes | Good for JS teams |
| 11 | Go Fiber/Gin | High-performance API | Go stack required | Very high RPS, low memory | `$0 license` | App server | M | MIT | Yes | High RPS |
| 12 | Spring Cloud Gateway | JVM enterprise gateway | JVM ops/heavy for Python project | Strong enterprise Java ecosystem | `$0 license` | JVM server | M/H | Apache 2.0 | Yes | Good enterprise integration |

**Recommendations**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
|------|---------|---------------------|-----------------|
| Budget | FastAPI + NGINX | `$0-5k` | Current Python stack, simple auth/routing |
| Optimal | Kong/APISIX or Envoy | `$5k-30k` | Multiple services, rate limits, auth, route governance |
| Enterprise | Kong Enterprise/Tyk/AWS API Gateway/Cloudflare | `$30k-150k+` | Developer portal, WAF, global edge, enterprise support |

**Migration paths**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| FastAPI only -> NGINX/Kong | Put gateway in front, keep app routes unchanged | Low | Low |
| NGINX -> Kong/APISIX | Translate routes/rate limits, migrate auth plugins | Low-medium | Medium |
| Self-host gateway -> cloud gateway | Preserve OpenAPI, DNS cutover, staged traffic | Low | Medium compliance |
| REST -> gRPC/internal | Keep REST external, introduce internal gRPC gradually | Medium | Medium |

---

## 16. Component 13 - PII Masking / Data Anonymization

**Responsibility:** detect/mask PII before external calls/logging, support RU-specific identifiers, reversible or irreversible tokenization where needed.

| № | Решение | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | RU PII / Accuracy / Latency / Custom patterns / Self-host / Cost / Reversible / Compliance |
|---:|---------|------------|-------|--------------|-----------|---------|--------------|----------|------------------|-----------------------------------------------------------------------------------------|
| 1 | Custom regex-based | Known patterns: email, phone, IP, INN/SNILS/passport | False positives/negatives, maintenance | Deterministic, auditable, current BL-23 style | `$0` | CPU | S | Project code | Yes | Strong for exact RU patterns, weak semantic |
| 2 | Microsoft Presidio | PII detection/anonymization framework | RU recognizers must be custom | Self-host, extensible recognizers, anonymizers | `$0 license` | CPU, optional NLP models | M | MIT | Yes | Good custom patterns, reversible tokenization possible |
| 3 | Amazon Comprehend PII | Managed PII detection | External cloud, RU support limitations | No ops, mature API | Per unit/character/request pricing | Managed | S | Commercial SaaS | Region-dependent | Good EN, RU must verify |
| 4 | Google Cloud Sensitive Data Protection (DLP) | DLP inspection/de-identification | External cloud, cost, data transfer | Broad detectors, de-identification, templates | Usage-based by bytes/requests | Managed | S/M | Commercial SaaS | Region-dependent | Strong generic DLP, custom infoTypes |
| 5 | Azure AI Language PII / Purview | PII detection/governance | Azure lock-in, language support must be tested | Enterprise compliance stack | Usage-based/quote | Managed | S/M | Commercial SaaS | Region-dependent | Good enterprise governance |
| 6 | Nightfall AI | SaaS DLP/PII | Quote/SaaS, data residency | Strong DLP workflows, SaaS integrations | Quote | Managed | S/M | Commercial SaaS | Contract-dependent | Broad DLP, custom detectors |
| 7 | Privacera | Data governance/access control | Heavy enterprise platform | Policy governance across data estate | Quote | Managed/self-host options | H | Commercial | Contract-dependent | Compliance/governance strong |
| 8 | Immuta | Data access governance | Overkill for simple masking | Dynamic data policies, governance | Quote | Managed/self-host options | H | Commercial | Contract-dependent | Governance strong |
| 9 | TokenEx | Tokenization | Commercial dependency, integration | PCI/tokenization expertise | Quote | Managed | M | Commercial SaaS | Contract-dependent | Reversible tokenization strong |
| 10 | Delphix | Data masking for databases | Heavy enterprise suite | Non-prod data masking, enterprise workflows | Quote | Managed/self-host | H | Commercial | Contract-dependent | Batch masking strong |
| 11 | IRI FieldShield | Data masking/anonymization | Commercial tooling | Broad masking formats, on-prem | Quote | Self-host | M/H | Commercial | Yes if deployed on-prem | Strong batch masking |
| 12 | Syntho | Synthetic data | Not request-time masking | Synthetic datasets for test/dev | Quote | SaaS/self-host options | M/H | Commercial | Contract-dependent | Synthetic data, privacy testing |

**Recommendations**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
|------|---------|---------------------|-----------------|
| Budget | Custom regex + tests | `$0-5k` | Known deterministic patterns, MVP logs and RAG context |
| Optimal | Presidio + custom RU recognizers + token vault | `$5k-25k` | Local PII Gateway before every external LLM/API call |
| Enterprise | Google/Azure/AWS DLP or Nightfall/Immuta/Privacera | `$30k-250k+` | Enterprise compliance, broad data estate, audit workflows |

**Migration paths**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| Regex -> Presidio | Convert regexes to recognizers, preserve mask token format | Low | Low-medium |
| Presidio -> cloud DLP | Add provider adapter, route only approved data classes | Low | Compliance high |
| Irreversible mask -> tokenization | Introduce token vault and key management; old masks cannot be reversed | Medium | High |
| SaaS DLP -> local | Export detector config where possible, recreate custom recognizers | Medium | Medium |

---

## 17. Architecture-Level Recommendations

### 17.1. Budget stack - минимальная стоимость

| Component | Choice |
|-----------|--------|
| Search | pgvector or ChromaDB |
| Bus | RabbitMQ |
| Orchestration | LiteLLM + Instructor + existing prompts |
| Parsing | python-docx/openpyxl + PyMuPDF/pdfplumber |
| Embeddings | bge-m3 local |
| LLM serving | Ollama / llama.cpp |
| Rerank | FlashRank or none |
| Observability | Prometheus + Grafana + Loki minimal |
| Audit | PostgreSQL append-only |
| Object storage | Local FS or MinIO single node |
| Cache | local cache + Valkey/Redis |
| API gateway | FastAPI + NGINX |
| PII | custom regex |

**TCO Year 1:** roughly `$10k-40k` mostly labor + small infra.

**When:** offline pilot, one environment, no strict HA, maximum RU-residency.

### 17.2. Optimal stack - balanced production pilot

| Component | Choice |
|-----------|--------|
| Search | Qdrant or OpenSearch |
| Bus | NATS JetStream |
| Orchestration | LlamaIndex/Haystack + LiteLLM |
| Parsing | Docling + Unstructured + current structural parser contract |
| Embeddings | bge-m3 + multilingual-e5/Jina benchmark |
| LLM serving | vLLM |
| Rerank | bge-reranker-base/large |
| Observability | OpenTelemetry + Grafana stack + Sentry |
| Audit | PostgreSQL + ClickHouse |
| Object storage | MinIO HA or RU S3-compatible provider |
| Cache | Valkey/Redis or Dragonfly |
| API gateway | Kong/APISIX/Envoy |
| PII | Presidio + RU recognizers |

**TCO Year 1:** roughly `$60k-180k` including infra, DevOps, and validation.

**When:** Sprint 6/7 production pilot with replaceable components and local PII path.

### 17.3. Enterprise stack - maximum SLA and governance

| Component | Choice |
|-----------|--------|
| Search | Elasticsearch / OpenSearch managed / Vespa / Pinecone if approved |
| Bus | Kafka / Pulsar / managed cloud bus |
| Orchestration | LangGraph + LangSmith/Portkey/Braintrust |
| Parsing | Azure DI / Textract / Document AI / LlamaParse with local fallback |
| Embeddings | OpenAI/Cohere/Voyage/RU provider + local fallback |
| LLM serving | TensorRT-LLM + KServe/BentoML |
| Rerank | Cohere/Jina/Voyage API or ColBERT |
| Observability | Datadog/New Relic/Dynatrace/Honeycomb |
| Audit | ClickHouse Cloud / BigQuery / Snowflake |
| Object storage | S3/Azure/GCS/Ceph with object lock |
| Cache | Redis Cluster/Cloud, Hazelcast, Aerospike |
| API gateway | Kong Enterprise/Tyk/AWS API Gateway/Cloudflare |
| PII | Enterprise DLP + tokenization vault |

**TCO Year 1:** `$250k+` and contract work.

**When:** multi-tenant production, strict SLA, dedicated Infra/SRE, approved cloud/SaaS perimeter.

---

## 18. Risk Register

| ID | Risk | Probability | Impact | Mitigation |
|----|------|-------------|--------|------------|
| BL61-R01 | Prices change after research publication | High | Medium | Store access date, require vendor calculator before purchase |
| BL61-R02 | SaaS rejected by security/compliance | Medium | High | Keep local/self-host option for every PII-relevant component |
| BL61-R03 | Cheapest pilot stack cannot scale | Medium | High | Define migration path and dual-write/dual-index from day one |
| BL61-R04 | AGPL/SSPL/Elastic license conflict | Medium | High | Legal review before adopting MinIO/Garage/PyMuPDF/Elastic variants |
| BL61-R05 | GPU not provided | Medium | High | CPU-capable fallback: bge-m3 CPU, Ollama/llama.cpp, MiniLM/FlashRank |
| BL61-R06 | Elasticsearch unavailable despite BL-60 assumption | Medium | High | Validate Qdrant/OpenSearch/pgvector path in PoC |
| BL61-R07 | Overengineering microservices too early | Medium | Medium | Start with interfaces and worker split, not full platform rewrite |
| BL61-R08 | Audit/log costs grow unexpectedly | Medium | Medium | Retention tiers, compression, object archive, sampling for debug logs |
| BL61-R09 | Parser SaaS leaks sensitive documents | Low/Medium | High | Local-first parsing; route only approved sanitized samples to SaaS |
| BL61-R10 | Migration requires full re-embedding | High | Medium | Preserve raw chunks, embedding model version, text hash, batch jobs |

---

## 19. Sprint 6 Decision Checklist

- [ ] Choose **one primary** and **one fallback** for search: `Qdrant/OpenSearch/Elasticsearch/pgvector`.
- [ ] Decide whether `Elasticsearch` is actually available in customer infrastructure.
- [ ] Choose bus default: `NATS JetStream` unless team already operates RabbitMQ/Kafka.
- [ ] Approve local parser stack: `Docling + Unstructured + current structural parser`.
- [ ] Approve default embedding model and dimensions; avoid reindexing surprises.
- [ ] Decide GPU availability and serving target: `Ollama` for install simplicity or `vLLM` for production pilot.
- [ ] Define PII Gateway contract and make it mandatory before external API calls.
- [ ] Add `run_id`, `trace_id`, `provider`, `model`, `prompt_id`, `embedding_model`, `mask_hash` to audit schema.
- [ ] Require vendor legal/security review for every SaaS and non-permissive license.
- [ ] Before implementation BLs, create ADR-010: Microservices decomposition and provider abstraction.

---

## 20. Source Register

Access date for all links: **2026-05-21** unless page notes a later pricing effective date.

| Area | Source |
|------|--------|
| Elastic | https://www.elastic.co/pricing |
| OpenSearch | https://aws.amazon.com/opensearch-service/pricing/ |
| Pinecone | https://www.pinecone.io/pricing/ and https://docs.pinecone.io/guides/manage-cost/understanding-cost |
| Qdrant | https://qdrant.tech/pricing/ |
| Weaviate | https://weaviate.io/pricing |
| Milvus/Zilliz | https://zilliz.com/pricing |
| Vespa | https://vespa.ai/ and https://cloud.vespa.ai/ |
| AWS SQS/SNS | https://aws.amazon.com/sqs/pricing/ and https://aws.amazon.com/sns/pricing/ |
| Google Pub/Sub | https://cloud.google.com/pubsub/pricing |
| Azure Service Bus | https://azure.microsoft.com/pricing/details/service-bus/ |
| Confluent | https://www.confluent.io/pricing |
| CloudAMQP | https://www.cloudamqp.com/plans.html |
| StreamNative | https://streamnative.io/pricing |
| LangChain/LangSmith | https://www.langchain.com/pricing and https://python.langchain.com/ |
| LlamaIndex/LlamaParse | https://www.llamaindex.ai/pricing and https://cloud.llamaindex.ai/ |
| Haystack/deepset | https://haystack.deepset.ai/ and https://www.deepset.ai/deepset-cloud |
| LiteLLM | https://www.litellm.ai/ |
| Portkey | https://portkey.ai/pricing |
| Helicone | https://www.helicone.ai/pricing |
| Braintrust | https://www.braintrust.dev/pricing |
| Unstructured | https://unstructured.io/pricing and https://github.com/Unstructured-IO/unstructured |
| Docling | https://github.com/docling-project/docling |
| Azure Document Intelligence | https://azure.microsoft.com/pricing/details/ai-document-intelligence/ |
| Google Document AI | https://cloud.google.com/document-ai/pricing |
| Amazon Textract | https://aws.amazon.com/textract/pricing/ |
| OpenAI embeddings | https://platform.openai.com/docs/pricing and https://platform.openai.com/docs/models/text-embedding-3-large |
| Cohere | https://cohere.com/pricing and https://docs.cohere.com/docs/rerank |
| Voyage AI | https://www.voyageai.com/pricing |
| Jina AI | https://jina.ai/embeddings/ and https://jina.ai/reranker/ |
| GigaChat | https://developers.sber.ru/docs/ru/gigachat/api/tariffs |
| YandexGPT | https://yandex.cloud/ru/docs/foundation-models/pricing |
| vLLM | https://docs.vllm.ai/ |
| TGI | https://huggingface.co/docs/text-generation-inference |
| TensorRT-LLM | https://github.com/NVIDIA/TensorRT-LLM |
| BentoML | https://www.bentoml.com/pricing |
| Datadog | https://www.datadoghq.com/pricing/ |
| New Relic | https://newrelic.com/pricing |
| Dynatrace | https://www.dynatrace.com/pricing/ |
| Honeycomb | https://www.honeycomb.io/pricing |
| Grafana Cloud | https://grafana.com/pricing/ |
| Sentry | https://sentry.io/pricing/ |
| ClickHouse | https://clickhouse.com/cloud and https://clickhouse.com/pricing |
| InfluxDB | https://www.influxdata.com/influxdb-cloud-pricing |
| BigQuery | https://cloud.google.com/bigquery/pricing |
| Snowflake | https://www.snowflake.com/pricing/ |
| Amazon S3 | https://aws.amazon.com/s3/pricing/ |
| Google Cloud Storage | https://cloud.google.com/storage/pricing |
| Azure Blob | https://azure.microsoft.com/pricing/details/storage/blobs/ |
| Yandex Object Storage | https://yandex.cloud/ru/docs/storage/pricing |
| Selectel Storage | https://selectel.ru/services/cloud/storage/ |
| MinIO | https://min.io/pricing |
| Redis | https://redis.io/pricing/ |
| Dragonfly | https://www.dragonflydb.io/pricing |
| Hazelcast | https://hazelcast.com/pricing/ |
| Aerospike | https://aerospike.com/pricing/ |
| Kong | https://konghq.com/pricing |
| Tyk | https://tyk.io/pricing/ |
| AWS API Gateway | https://aws.amazon.com/api-gateway/pricing/ |
| Cloudflare Workers | https://developers.cloudflare.com/workers/platform/pricing/ |
| Presidio | https://microsoft.github.io/presidio/ |
| AWS Comprehend | https://aws.amazon.com/comprehend/pricing/ |
| Google Sensitive Data Protection | https://cloud.google.com/sensitive-data-protection/pricing |
| Azure AI Language PII | https://azure.microsoft.com/pricing/details/cognitive-services/language-service/ |
| Nightfall | https://www.nightfall.ai/pricing |
| Privacera | https://privacera.com/ |
| Immuta | https://www.immuta.com/pricing/ |
| TokenEx | https://www.tokenex.com/ |
| Delphix | https://www.perforce.com/products/delphix |
| IRI FieldShield | https://www.iri.com/products/fieldshield |
| Syntho | https://www.syntho.ai/ |

---

## 21. History

| Версия | Дата | Изменение |
|--------|------|-----------|
| v1 | 2026-05-21 | First BL-61 market research covering 13 microservices architecture components, recommendations, migration paths, risks and source register. |
