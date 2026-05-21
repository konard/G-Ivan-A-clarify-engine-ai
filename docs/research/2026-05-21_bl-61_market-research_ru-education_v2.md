# Research: Business-readable RU education adaptation for BL-61 Market Comparison (BL-61.1)

## Метаданные
- **Дата:** 2026-05-21
- **Версия:** v2
- **Тип документа:** `research_adaptation`
- **Статус:** Draft -> готов к ревью BA / PO / Tech Lead / Infra по issue #224
- **Автор:** konard (AI issue solver, по [issue #224](https://github.com/G-Ivan-A/clarify-engine-ai/issues/224))
- **Спринт:** Sprint 6 - Architecture Foundation
- **PR:** [`#225`](https://github.com/G-Ivan-A/clarify-engine-ai/pull/225)
- **Исходный артефакт:** [`docs/research/2026-05-21_bl-61_market-research_v1.md`](2026-05-21_bl-61_market-research_v1.md)
- **Предыдущая RU-адаптация:** [`docs/research/2026-05-21_bl-61_market-research_ru-education_v1.md`](2026-05-21_bl-61_market-research_ru-education_v1.md)
- **Depends on:** BL-61 (Market Research for Microservices Architecture Components), BL-67 (RU education adaptation v1)
- **Целевая аудитория:** Business Analyst, Product Owner, Tech Lead, Infra Lead, ML-инженер, BA Lead
- **Связанные документы:**
  - [`docs/research/2026-05-20_bl-60_next-gen-architecture_v1.md`](2026-05-20_bl-60_next-gen-architecture_v1.md)
  - [`docs/CONCEPT.md`](../CONCEPT.md)
  - [`docs/ADR/001-rag-architecture.md`](../ADR/001-rag-architecture.md)
  - [`docs/ADR/005-audit-trail.md`](../ADR/005-audit-trail.md)
  - [`docs/research/2026-05-21_bl-57_retrieval-architecture_v1.md`](2026-05-21_bl-57_retrieval-architecture_v1.md)
  - [`docs/research/2026-05-20_bl-59_requirement-parsing_v1.md`](2026-05-20_bl-59_requirement-parsing_v1.md)

> **Scope note.** Это образовательная RU-адаптация BL-61, не реализация.
> Исходный файл BL-61 не изменяется. Документ не меняет `src/`, `configs/`,
> `prompts/` и не фиксирует необратимый vendor lock-in. Цель BL-61.1 - сделать
> market research читаемым для BA / PO: добавить RU-пояснение к каждому решению,
> конкретизировать сценарии `Когда применять` и обеспечить перенос строк в HTML.
>
> **HTML readability contract.** Companion HTML v2 генерируется через
> `scripts/tools/md_to_html_fullwidth.py` и использует `white-space: normal`,
> `overflow-wrap: anywhere`, `word-break: normal`; `text-overflow: ellipsis` и
> `white-space: nowrap` запрещены для ячеек таблиц.

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

## 4. Компонент 1 - Vector Database / Search Engine

**Ответственность:** хранение embeddings, лексический поиск, hybrid search, metadata filtering, incremental updates и production retrieval.

| № | Решение | Пояснение для БА | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Metadata filtering / Hybrid / Updates / Scale / Support |
| ---: | --------- | --- | ------------ | ------- | -------------- | ----------- | --------- | -------------- | ---------- | ------------------ | ---------------------------------------------------------- |
| 1 | Elasticsearch 8.x | Elasticsearch 8.x — вариант для поискового слоя и vector storage.<br>Зачем нужен: быстро находить релевантные фрагменты Корпуса требований по словам, смыслу и метаданным.<br>Бизнес-смысл: меньше ложных ответов `НД`, выше цитируемость и понятный путь миграции от MVP к production.<br>Что проверить: Elastic License / SSPL options, tuning complexity, JVM ops. | BM25, dense vectors, hybrid RRF, filters, security | Elastic License / SSPL options, tuning complexity, JVM ops | Mature enterprise search, rich query DSL, snapshots, RBAC | Self-managed `$0 basic` + infra; Elastic Cloud usage/resource pricing | Pilot 4-8 vCPU, 16-32 GB RAM, SSD; production 3+ nodes | M/H, needs ES skills | Elastic License v2 / SSPL / AGPL options by distribution/version | Yes self-host; managed cloud may violate residency | Strong filters, strong hybrid, bulk updates, high scale, enterprise support |
| 2 | OpenSearch 2.x/3.x | OpenSearch 2.x/3.x — вариант для поискового слоя и vector storage.<br>Зачем нужен: быстро находить релевантные фрагменты Корпуса требований по словам, смыслу и метаданным.<br>Бизнес-смысл: меньше ложных ответов `НД`, выше цитируемость и понятный путь миграции от MVP к production.<br>Что проверить: Fork compatibility gaps, plugin/version drift. | ES-like search + kNN + BM25 | Fork compatibility gaps, plugin/version drift | Apache 2.0, AWS-managed path, familiar Lucene model | `$0 license`; AWS examples: c6g.large.search `$0.113/h`, semantic OCU `$0.24/h` | 3 nodes recommended for HA, 8-64 GB RAM/node | M/H | Apache 2.0 | Yes self-host; AWS region residency depends on approval | Strong filters, strong hybrid with custom query, bulk updates, high support |
| 3 | Qdrant 1.x | Qdrant 1.x — вариант для поискового слоя и vector storage.<br>Зачем нужен: быстро находить релевантные фрагменты Корпуса требований по словам, смыслу и метаданным.<br>Бизнес-смысл: меньше ложных ответов `НД`, выше цитируемость и понятный путь миграции от MVP к production.<br>Что проверить: BM25 less native than Lucene, separate lexical stack may be needed. | Vector DB with payload filters and hybrid sparse+dense | BM25 less native than Lucene, separate lexical stack may be needed | Simple ops, Rust performance, good payload filtering, cloud/free tier | OSS `$0`; Qdrant Cloud free 0.5 vCPU/1 GB/4 GB, paid usage-based | Pilot 2-4 vCPU, 8-16 GB RAM; HA 3 nodes | S/M | Apache 2.0 | Yes self-host/hybrid cloud | Strong filters, good hybrid, upsert, medium-high scale, active community |
| 4 | Weaviate | Weaviate — вариант для поискового слоя и vector storage.<br>Зачем нужен: быстро находить релевантные фрагменты Корпуса требований по словам, смыслу и метаданным.<br>Бизнес-смысл: меньше ложных ответов `НД`, выше цитируемость и понятный путь миграции от MVP к production.<br>Что проверить: Higher memory footprint, GraphQL/schema learning. | Vector DB, hybrid search, modules | Higher memory footprint, GraphQL/schema learning | Built-in hybrid, multi-tenancy, modules | OSS `$0`; Weaviate Cloud serverless/enterprise usage or quote | 4-8 vCPU, 16-32 GB RAM pilot | M | BSD-3-Clause core | Yes self-host; WCD depends region | Good filters, native hybrid, batch updates, high support |
| 5 | Milvus | Milvus — вариант для поискового слоя и vector storage.<br>Зачем нужен: быстро находить релевантные фрагменты Корпуса требований по словам, смыслу и метаданным.<br>Бизнес-смысл: меньше ложных ответов `НД`, выше цитируемость и понятный путь миграции от MVP к production.<br>Что проверить: Operationally heavy (etcd, object store, query/data nodes). | High-scale vector DB | Operationally heavy (etcd, object store, query/data nodes) | Very high scale, GPU/index options, Zilliz Cloud | OSS `$0`; Zilliz Cloud usage/quote | Pilot complex; production 3+ services, object store | H | Apache 2.0 | Yes self-host | Good filters, hybrid improving, batch updates, very high scale |
| 6 | pgvector | pgvector — вариант для поискового слоя и vector storage.<br>Зачем нужен: быстро находить релевантные фрагменты Корпуса требований по словам, смыслу и метаданным.<br>Бизнес-смысл: меньше ложных ответов `НД`, выше цитируемость и понятный путь миграции от MVP к production.<br>Что проверить: Recall/latency limits at high cardinality, DB bloat. | Vectors inside PostgreSQL | Recall/latency limits at high cardinality, DB bloat | Reuses Postgres, transactional metadata, simplest governance | `$0 license`; Postgres infra already likely needed | 4-16 vCPU, 16-64 GB RAM, SSD | S/M | PostgreSQL License | Yes self-host | Excellent relational filters, BM25 requires extension/sidecar, easy updates, medium scale |
| 7 | ChromaDB | ChromaDB — вариант для поискового слоя и vector storage.<br>Зачем нужен: быстро находить релевантные фрагменты Корпуса требований по словам, смыслу и метаданным.<br>Бизнес-смысл: меньше ложных ответов `НД`, выше цитируемость и понятный путь миграции от MVP к production.<br>Что проверить: Not ideal for HA, limited enterprise governance. | Local/dev vector store | Not ideal for HA, limited enterprise governance | Simple tests/offline, current ecosystem familiarity | `$0 license`; infra only | 2-4 vCPU, 8-16 GB RAM for small pilot | XS/S | Apache 2.0 | Yes local | Basic filters, hybrid mostly app-side, simple updates, low-medium scale |
| 8 | Pinecone | Pinecone — вариант для поискового слоя и vector storage.<br>Зачем нужен: быстро находить релевантные фрагменты Корпуса требований по словам, смыслу и метаданным.<br>Бизнес-смысл: меньше ложных ответов `НД`, выше цитируемость и понятный путь миграции от MVP к production.<br>Что проверить: SaaS/data residency, usage surprises, vendor lock-in. | Managed vector DB and inference | SaaS/data residency, usage surprises, vendor lock-in | Low ops, serverless, read/write/storage unit model, DRN | Free/start credits; paid plan has `$50` monthly minimum, WU examples `$4-$6.75/M` by tier/region | No local infra | S | Commercial SaaS | No self-host; residency by cloud region only | Good metadata, sparse+dense/full-text options, managed scale/support |
| 9 | Vespa | Vespa — вариант для поискового слоя и vector storage.<br>Зачем нужен: быстро находить релевантные фрагменты Корпуса требований по словам, смыслу и метаданным.<br>Бизнес-смысл: меньше ложных ответов `НД`, выше цитируемость и понятный путь миграции от MVP к production.<br>Что проверить: Steep learning curve, ops complexity. | Search + vector + ranking platform | Steep learning curve, ops complexity | Powerful ranking, hybrid, large-scale serving | OSS `$0`; Vespa Cloud usage/quote | 3+ nodes recommended, 16-64 GB RAM/node | H | Apache 2.0 | Yes self-host | Strong filters/hybrid/ranking, streaming updates, very high scale |
| 10 | LanceDB | LanceDB — вариант для поискового слоя и vector storage.<br>Зачем нужен: быстро находить релевантные фрагменты Корпуса требований по словам, смыслу и метаданным.<br>Бизнес-смысл: меньше ложных ответов `НД`, выше цитируемость и понятный путь миграции от MVP к production.<br>Что проверить: Young ecosystem for HA/ops, search feature depth. | Embedded/table vector storage | Young ecosystem for HA/ops, search feature depth | Cheap local/lakehouse path, Arrow/Lance format | OSS `$0`; LanceDB Cloud usage/quote | 2-8 vCPU, object store optional | S/M | Apache 2.0 | Yes self-host | Basic-good filters, hybrid available, easy batch, medium scale |
| 11 | Redis Stack Vector | Redis Stack Vector — вариант для поискового слоя и vector storage.<br>Зачем нужен: быстро находить релевантные фрагменты Корпуса требований по словам, смыслу и метаданным.<br>Бизнес-смысл: меньше ложных ответов `НД`, выше цитируемость и понятный путь миграции от MVP к production.<br>Что проверить: RAM cost, persistence/search limits vs search engines. | Cache + vector similarity | RAM cost, persistence/search limits vs search engines | Low latency, reuses Redis, good for cache/RAG hotset | Redis OSS/RSAL mix; Redis Cloud usage | RAM-heavy: dataset must fit memory | S/M | Redis source licenses vary; modules not pure OSS in all editions | Yes self-host if license approved | Good filters, hybrid limited, fast updates, medium scale |
| 12 | MongoDB Atlas Vector Search | MongoDB Atlas Vector Search — вариант для поискового слоя и vector storage.<br>Зачем нужен: быстро находить релевантные фрагменты Корпуса требований по словам, смыслу и метаданным.<br>Бизнес-смысл: меньше ложных ответов `НД`, выше цитируемость и понятный путь миграции от MVP к production.<br>Что проверить: SaaS lock-in, self-host vector search limitations. | Document DB + vector search | SaaS lock-in, self-host vector search limitations | If MongoDB already exists, simple metadata model | Atlas cluster usage-based | Managed infra | S/M | Commercial / SSPL server | Atlas region residency only | Good document filters, vector + text search, managed scale |
| 13 | Azure AI Search | Azure AI Search — вариант для поискового слоя и vector storage.<br>Зачем нужен: быстро находить релевантные фрагменты Корпуса требований по словам, смыслу и метаданным.<br>Бизнес-смысл: меньше ложных ответов `НД`, выше цитируемость и понятный путь миграции от MVP к production.<br>Что проверить: Azure lock-in, data residency approval, cost. | Managed hybrid search and vector | Azure lock-in, data residency approval, cost | Mature managed search, semantic ranking, RBAC | Usage by SKU/replicas/partitions | Managed infra | S/M | Commercial SaaS | Region-dependent, not local | Strong filters/hybrid, managed updates, enterprise support |
| 14 | DataStax Astra DB | DataStax Astra DB — вариант для поискового слоя и vector storage.<br>Зачем нужен: быстро находить релевантные фрагменты Корпуса требований по словам, смыслу и метаданным.<br>Бизнес-смысл: меньше ложных ответов `НД`, выше цитируемость и понятный путь миграции от MVP к production.<br>Что проверить: SaaS lock-in, less lexical search depth. | Cassandra + vector | SaaS lock-in, less lexical search depth | Serverless vector on Cassandra, scalable writes | Serverless usage/quote | Managed infra | S/M | Commercial SaaS / Apache Cassandra core | Region-dependent | Good metadata, vector search, high write scale |

**Рекомендации**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
| ------ | --------- | --------------------- | ----------------- |
| Budget | pgvector or ChromaDB | `$1k-6k` infra + part-time ops | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если корпус до 50k chunks, один стенд, offline-пилот и допустим ручной backup/reindex<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нужны HA, multi-tenant, replay, SLA 99.9% или нагрузка >100 запросов/мин |
| Optimal | Qdrant or OpenSearch | `$4k-20k` infra/managed + ops | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нужен production pilot без гарантированного доступа к corporate Elasticsearch<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нет владельца эксплуатации, нет stage-gate на migration или объём пока похож на offline demo |
| Enterprise | Elasticsearch or Vespa | `$20k-100k+` infra/license/support | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если уже есть search-команда, RBAC, snapshots, backup и требования к высокой нагрузке<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• ещё не подтверждены SLA, бюджет, security approval и выделенная Infra/SRE-команда |

**Пути миграции**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| ChromaDB -> Qdrant/OpenSearch/ES | Export chunks + metadata, reuse embeddings if dim/model unchanged, bulk upsert | Low with dual-write | Medium |
| pgvector -> ES/OpenSearch | Dump rows, map metadata fields, bulk index, preserve `chunk_id` | Low | Medium |
| Qdrant -> ES/OpenSearch | Export collection payload/vector, add lexical analyzer, re-run quality eval | Low-medium | Medium |
| ES/OpenSearch -> Qdrant | Export `_source`, keep embeddings, move BM25 to sidecar or sparse vectors | Medium | Medium-high |

<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**

**Что это значит для проекта:** этот компонент закрывает задачу: быстро находить релевантные фрагменты Корпуса требований по словам, смыслу и метаданным. В контексте Clarify Engine это влияет не на "красоту архитектуры", а на скорость, проверяемость и стоимость анализа требований.

**Почему важно для БА:** БА видит не название базы данных, а качество evidence: какие разделы попали в ответ, можно ли фильтровать по продукту/странице и почему система выбрала именно эти chunks.

**Технически:**
- `SearchBackend` должен скрывать Elasticsearch, OpenSearch, Qdrant, pgvector и ChromaDB за единым контрактом.
- Смена embedding dimensions или search engine требует parallel index и retrieval-eval до переключения alias.
- Hybrid search должен сохранять BM25 + vectors + metadata filters, иначе short/sparse требования снова дадут `STRICT_MODE -> НД`.

**Когда выбирать:**
- 🟢 **Budget:** для пилота Clarify Engine на 1-3 БА с нагрузкой ≤15 запросов/мин, если корпус до 50k chunks, один стенд, offline-пилот и допустим ручной backup/reindex.
- 🟡 **Optimal:** для production pilot на 1-3 БА с нагрузкой ≤15 запросов/мин и ростом до нескольких сервисов, если нужен production pilot без гарантированного доступа к corporate Elasticsearch.
- 🔵 **Enterprise:** после подтверждения SLA, бюджета, security approval и нагрузки >100 запросов/мин, если уже есть search-команда, RBAC, snapshots, backup и требования к высокой нагрузке.

📚 **Читать далее:**
- [Elasticsearch dense vector field](https://www.elastic.co/guide/en/elasticsearch/reference/current/dense-vector.html) — vector search и HNSW, EN.
- [Qdrant hybrid queries](https://qdrant.tech/documentation/concepts/hybrid-queries/) — dense + sparse retrieval, EN.
- [pgvector README](https://github.com/pgvector/pgvector) — embeddings в PostgreSQL, EN.

---
## 5. Компонент 2 - Message Bus / Event Streaming

**Ответственность:** асинхронная коммуникация сервисов, ingestion jobs, backpressure, retries и delivery guarantees.

| № | Решение | Пояснение для БА | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Latency / Throughput / Persistence / Delivery / DLQ / Routing / Cluster |
| ---: | --------- | --- | ------------ | ------- | -------------- | ----------- | --------- | -------------- | ---------- | ------------------ | ------------------------------------------------------------------------ |
| 1 | NATS JetStream | NATS JetStream — вариант для асинхронной шины событий.<br>Зачем нужен: разносить долгие операции parsing, indexing, rerank и LLM calls по очередям без зависания UI.<br>Бизнес-смысл: БА может загрузить документ и продолжать работу, а система получает retries, backpressure и DLQ для разборов сбоев.<br>Что проверить: Smaller enterprise bench than Kafka, stream retention tuning. | Lightweight messaging + persistent streams | Smaller enterprise bench than Kafka, stream retention tuning | Very low latency, simple ops, request/reply, KV/object store | OSS `$0`; Synadia Cloud quote/usage | 2-4 vCPU/node, 4-16 GB RAM, 3 nodes HA | S/M | Apache 2.0 | Yes self-host | p95 low ms, high throughput, file persistence, at-least-once, DLQ by consumer, subjects |
| 2 | RabbitMQ | RabbitMQ — вариант для асинхронной шины событий.<br>Зачем нужен: разносить долгие операции parsing, indexing, rerank и LLM calls по очередям без зависания UI.<br>Бизнес-смысл: БА может загрузить документ и продолжать работу, а система получает retries, backpressure и DLQ для разборов сбоев.<br>Что проверить: Throughput lower than Kafka, quorum queue tuning. | AMQP queues, routing, worker jobs | Throughput lower than Kafka, quorum queue tuning | Mature, simple DLQ/routing, great for task queues | OSS `$0`; CloudAMQP free/paid tiers | 2-8 vCPU, 4-32 GB RAM, 3 nodes HA | S/M | MPL 2.0 | Yes self-host | Low ms, medium throughput, durable queues, at-least-once, DLQ native, exchanges |
| 3 | Apache Kafka | Apache Kafka — вариант для асинхронной шины событий.<br>Зачем нужен: разносить долгие операции parsing, indexing, rerank и LLM calls по очередям без зависания UI.<br>Бизнес-смысл: БА может загрузить документ и продолжать работу, а система получает retries, backpressure и DLQ для разборов сбоев.<br>Что проверить: High ops complexity, partition/rebalance pain. | Durable event streaming | High ops complexity, partition/rebalance pain | Standard for high throughput streams, replay, ecosystem | OSS `$0`; Confluent Cloud eCKU/CKU/storage/network | 3+ brokers, 16-64 GB RAM/node, SSD | H | Apache 2.0 | Yes self-host | Low-medium latency, very high throughput, log persistence, at-least/exactly-once producer semantics |
| 4 | Apache Pulsar | Apache Pulsar — вариант для асинхронной шины событий.<br>Зачем нужен: разносить долгие операции parsing, indexing, rerank и LLM calls по очередям без зависания UI.<br>Бизнес-смысл: БА может загрузить документ и продолжать работу, а система получает retries, backpressure и DLQ для разборов сбоев.<br>Что проверить: More components (BookKeeper/ZK/metadata), smaller talent pool. | Multi-tenant streaming + queueing | More components (BookKeeper/ZK/metadata), smaller talent pool | Tiered storage, geo-replication, queue/stream unification | OSS `$0`; StreamNative quote | Brokers + BookKeeper, 3+ nodes | H | Apache 2.0 | Yes self-host | Low latency, high throughput, durable ledger, strong multi-tenancy |
| 5 | Redis Streams | Redis Streams — вариант для асинхронной шины событий.<br>Зачем нужен: разносить долгие операции parsing, indexing, rerank и LLM calls по очередям без зависания UI.<br>Бизнес-смысл: БА может загрузить документ и продолжать работу, а система получает retries, backpressure и DLQ для разборов сбоев.<br>Что проверить: Memory pressure, limited replay governance. | Lightweight persistent streams | Memory pressure, limited replay governance | Simple if Redis exists, consumer groups | OSS/Redis licensing varies; infra only | RAM-heavy, 1-3 nodes | S | BSD/RSAL variants by package | Yes self-host if license approved | Low latency, medium throughput, in-memory + AOF/RDB, at-least-once |
| 6 | Amazon SQS/SNS | Amazon SQS/SNS — вариант для асинхронной шины событий.<br>Зачем нужен: разносить долгие операции parsing, indexing, rerank и LLM calls по очередям без зависания UI.<br>Бизнес-смысл: БА может загрузить документ и продолжать работу, а система получает retries, backpressure и DLQ для разборов сбоев.<br>Что проверить: External cloud, no local residency, limited ordering unless FIFO. | Managed queues/topics | External cloud, no local residency, limited ordering unless FIFO | No ops, mature DLQ, cheap per request | SQS: 1M requests/month free, Standard `$0.40/M`, FIFO `$0.50/M`; SNS publish `$0.50/M` | Managed | XS/S | Commercial SaaS | Region-dependent, not local | Medium latency, high scale, durable, at-least-once, DLQ native |
| 7 | Google Pub/Sub | Google Pub/Sub — вариант для асинхронной шины событий.<br>Зачем нужен: разносить долгие операции parsing, indexing, rerank и LLM calls по очередям без зависания UI.<br>Бизнес-смысл: БА может загрузить документ и продолжать работу, а система получает retries, backpressure и DLQ для разборов сбоев.<br>Что проверить: External cloud, egress, ordering constraints. | Managed pub/sub streaming | External cloud, egress, ordering constraints | Global managed scale, push/pull, BigQuery integration | First 10 GiB/month basic delivery free; then `$40/TiB`; import topics `$80/TiB`; storage `$0.27/GiB-month` | Managed | XS/S | Commercial SaaS | Region-dependent | Medium latency, very high scale, durable, at-least-once/exactly-once options |
| 8 | Azure Service Bus | Azure Service Bus — вариант для асинхронной шины событий.<br>Зачем нужен: разносить долгие операции parsing, indexing, rerank и LLM calls по очередям без зависания UI.<br>Бизнес-смысл: БА может загрузить документ и продолжать работу, а система получает retries, backpressure и DLQ для разборов сбоев.<br>Что проверить: Azure lock-in, throughput by tier. | Enterprise managed queues/topics | Azure lock-in, throughput by tier | Sessions, DLQ, topics, enterprise support | Basic/Standard/Premium; Standard includes first 13M ops/month; Premium bills Messaging Units/hour; geo-replication `$0.09-$0.23/GB` | Managed | XS/S | Commercial SaaS | Region-dependent | Medium latency, high reliability, DLQ native, filters/topics |
| 9 | ZeroMQ | ZeroMQ — вариант для асинхронной шины событий.<br>Зачем нужен: разносить долгие операции parsing, indexing, rerank и LLM calls по очередям без зависания UI.<br>Бизнес-смысл: БА может загрузить документ и продолжать работу, а система получает retries, backpressure и DLQ для разборов сбоев.<br>Что проверить: No broker persistence, app owns reliability. | Embedded messaging library | No broker persistence, app owns reliability | Very fast, minimal dependency, good for internal IPC | `$0 license` | App-local | M | MPL 2.0 | Yes | Very low latency, no built-in persistence/DLQ |
| 10 | NSQ | NSQ — вариант для асинхронной шины событий.<br>Зачем нужен: разносить долгие операции parsing, indexing, rerank и LLM calls по очередям без зависания UI.<br>Бизнес-смысл: БА может загрузить документ и продолжать работу, а система получает retries, backpressure и DLQ для разборов сбоев.<br>Что проверить: Smaller ecosystem, fewer enterprise features. | Simple distributed queue | Smaller ecosystem, fewer enterprise features | Easy ops, decentralized topology | `$0 license` | 2-4 vCPU nodes | S/M | MIT | Yes | Low latency, medium throughput, at-least-once, simple routing |
| 11 | ActiveMQ Artemis | ActiveMQ Artemis — вариант для асинхронной шины событий.<br>Зачем нужен: разносить долгие операции parsing, indexing, rerank и LLM calls по очередям без зависания UI.<br>Бизнес-смысл: БА может загрузить документ и продолжать работу, а система получает retries, backpressure и DLQ для разборов сбоев.<br>Что проверить: Java ops, less cloud-native mindshare. | JMS/AMQP/MQTT/STOMP broker | Java ops, less cloud-native mindshare | Protocol rich, mature enterprise messaging | `$0 license` | 2-8 vCPU, 8-32 GB RAM | M | Apache 2.0 | Yes | Low-medium latency, durable, DLQ, JMS semantics |
| 12 | Solace PubSub+ | Solace PubSub+ — вариант для асинхронной шины событий.<br>Зачем нужен: разносить долгие операции parsing, indexing, rerank и LLM calls по очередям без зависания UI.<br>Бизнес-смысл: БА может загрузить документ и продолжать работу, а система получает retries, backpressure и DLQ для разборов сбоев.<br>Что проверить: Commercial quote, lock-in. | Enterprise event broker | Commercial quote, lock-in | Strong enterprise routing, appliances, support | Quote / free developer tier | Managed/appliance/self-managed | M/H | Commercial | Possible self-host/private cloud | Low latency, high throughput, strong routing/governance |

**Рекомендации**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
| ------ | --------- | --------------------- | ----------------- |
| Budget | RabbitMQ or Redis Streams | `$1k-8k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нужны простые worker queues, нет event sourcing и нет выделенного DevOps под Kafka<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нужны HA, multi-tenant, replay, SLA 99.9% или нагрузка >100 запросов/мин |
| Optimal | NATS JetStream | `$2k-15k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если сервисов становится несколько и важны low-latency events с простой эксплуатацией<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нет владельца эксплуатации, нет stage-gate на migration или объём пока похож на offline demo |
| Enterprise | Kafka or Pulsar | `$25k-150k+` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нужны replay событий, streaming analytics, multi-tenant топики и высокая throughput-нагрузка<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• ещё не подтверждены SLA, бюджет, security approval и выделенная Infra/SRE-команда |

**Пути миграции**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| RabbitMQ -> NATS | Introduce bus abstraction, dual-publish ingestion events, drain queues | Low | Medium |
| NATS -> Kafka | Map subjects to topics, define partitions/keys, run dual-write, replay from object/audit store | Medium | Medium-high |
| Redis Streams -> RabbitMQ/NATS | Consumer group offset export is custom; replay from durable source preferred | Medium | Medium |
| Cloud bus -> self-host | Wrap SDK calls behind interface, replay dead-letter/archive events | Medium | Medium |

<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**

**Что это значит для проекта:** этот компонент закрывает задачу: разносить долгие операции parsing, indexing, rerank и LLM calls по очередям без зависания UI. В контексте Clarify Engine это влияет не на "красоту архитектуры", а на скорость, проверяемость и стоимость анализа требований.

**Почему важно для БА:** Для БА это превращает долгие фоновые операции в управляемый workflow: документ не потеряется, ошибка попадёт в DLQ, а статус можно показать в UI.

**Технически:**
- События должны иметь стабильные поля `run_id`, `document_id`, `event_type`, `payload_version`.
- `MessageBus` adapter должен позволять dual-publish при миграции RabbitMQ -> NATS -> Kafka.
- DLQ и retry-policy нужно проектировать до нагрузки, иначе batch indexing будет чиниться вручную.

**Когда выбирать:**
- 🟢 **Budget:** для пилота Clarify Engine на 1-3 БА с нагрузкой ≤15 запросов/мин, если нужны простые worker queues, нет event sourcing и нет выделенного DevOps под Kafka.
- 🟡 **Optimal:** для production pilot на 1-3 БА с нагрузкой ≤15 запросов/мин и ростом до нескольких сервисов, если сервисов становится несколько и важны low-latency events с простой эксплуатацией.
- 🔵 **Enterprise:** после подтверждения SLA, бюджета, security approval и нагрузки >100 запросов/мин, если нужны replay событий, streaming analytics, multi-tenant топики и высокая throughput-нагрузка.

📚 **Читать далее:**
- [NATS JetStream concepts](https://docs.nats.io/nats-concepts/jetstream) — persistent streams и consumers, EN.
- [RabbitMQ tutorials](https://www.rabbitmq.com/tutorials) — queues, acknowledgements и routing, EN.
- [Apache Kafka documentation](https://kafka.apache.org/documentation/) — topics, partitions и replication, EN.

---
## 6. Компонент 3 - LLM Orchestration Framework

**Ответственность:** prompt management, provider routing, chains/graphs, RAG workflow, caching, fallback и observability hooks.

| № | Решение | Пояснение для БА | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | RAG / Agents / Providers / Prompt versioning / Cache / Observability / Maturity |
| ---: | --------- | --- | ------------ | ------- | -------------- | ----------- | --------- | -------------- | ---------- | ------------------ | -------------------------------------------------------------------------------- |
| 1 | LangChain | LangChain — вариант для LLM orchestration и provider routing.<br>Зачем нужен: управлять prompts, fallback-провайдерами, typed output, cache, budget и observability для LLM-вызовов.<br>Бизнес-смысл: стоимость и качество LLM становятся управляемыми: типовые запросы идут дешёвым маршрутом, сложные - в более сильный workflow.<br>Что проверить: Abstraction churn, dependency weight. | Chains, tools, integrations | Abstraction churn, dependency weight | Huge ecosystem, many provider integrations | OSS `$0`; LangSmith paid for tracing/evals | App-level | M | MIT | Yes for OSS | Strong RAG, agents, many providers, LangSmith for versioning/observability |
| 2 | LlamaIndex | LlamaIndex — вариант для LLM orchestration и provider routing.<br>Зачем нужен: управлять prompts, fallback-провайдерами, typed output, cache, budget и observability для LLM-вызовов.<br>Бизнес-смысл: стоимость и качество LLM становятся управляемыми: типовые запросы идут дешёвым маршрутом, сложные - в более сильный workflow.<br>Что проверить: Can duplicate existing retriever abstractions. | RAG data framework | Can duplicate existing retriever abstractions | Strong indexing/query abstractions, doc loaders | OSS `$0`; LlamaCloud/LlamaParse paid | App-level | M | MIT | Yes for OSS | Excellent RAG, agents improving, many providers, good evals |
| 3 | Haystack | Haystack — вариант для LLM orchestration и provider routing.<br>Зачем нужен: управлять prompts, fallback-провайдерами, typed output, cache, budget и observability для LLM-вызовов.<br>Бизнес-смысл: стоимость и качество LLM становятся управляемыми: типовые запросы идут дешёвым маршрутом, сложные - в более сильный workflow.<br>Что проверить: Smaller ecosystem than LangChain. | Production RAG pipelines | Smaller ecosystem than LangChain | Clean pipeline components, search integration | OSS `$0`; deepset Cloud quote | App-level | M | Apache 2.0 | Yes OSS | Strong RAG, provider integrations, production-friendly |
| 4 | Semantic Kernel | Semantic Kernel — вариант для LLM orchestration и provider routing.<br>Зачем нужен: управлять prompts, fallback-провайдерами, typed output, cache, budget и observability для LLM-вызовов.<br>Бизнес-смысл: стоимость и качество LLM становятся управляемыми: типовые запросы идут дешёвым маршрутом, сложные - в более сильный workflow.<br>Что проверить: Microsoft ecosystem bias. | Planner/orchestration SDK | Microsoft ecosystem bias | Good enterprise patterns, C#/Python/Java | OSS `$0`; Azure services billed separately | App-level | M | MIT | Yes OSS | Good orchestration, agents, Azure integrations |
| 5 | LangGraph | LangGraph — вариант для LLM orchestration и provider routing.<br>Зачем нужен: управлять prompts, fallback-провайдерами, typed output, cache, budget и observability для LLM-вызовов.<br>Бизнес-смысл: стоимость и качество LLM становятся управляемыми: типовые запросы идут дешёвым маршрутом, сложные - в более сильный workflow.<br>Что проверить: Adds complexity if simple chain enough. | Stateful agent/workflow graphs | Adds complexity if simple chain enough | Deterministic graph execution, durable workflows | OSS `$0`; LangSmith optional | App-level | M/H | MIT | Yes OSS | Strong agents/workflows, checkpointing, observability via LangSmith |
| 6 | DSPy | DSPy — вариант для LLM orchestration и provider routing.<br>Зачем нужен: управлять prompts, fallback-провайдерами, typed output, cache, budget и observability для LLM-вызовов.<br>Бизнес-смысл: стоимость и качество LLM становятся управляемыми: типовые запросы идут дешёвым маршрутом, сложные - в более сильный workflow.<br>Что проверить: Requires dataset/eval discipline. | Prompt/program optimization | Requires dataset/eval discipline | Declarative optimization, useful for prompt tuning | OSS `$0` | App-level, eval infra | M/H | MIT | Yes OSS | Good for optimization, not primary RAG runtime |
| 7 | Guidance | Guidance — вариант для LLM orchestration и provider routing.<br>Зачем нужен: управлять prompts, fallback-провайдерами, typed output, cache, budget и observability для LLM-вызовов.<br>Бизнес-смысл: стоимость и качество LLM становятся управляемыми: типовые запросы идут дешёвым маршрутом, сложные - в более сильный workflow.<br>Что проверить: Smaller ecosystem, less production governance. | Structured generation control | Smaller ecosystem, less production governance | Fine-grained constrained decoding | OSS `$0` | App-level | M | MIT | Yes OSS | Useful for schema/structured output |
| 8 | Instructor | Instructor — вариант для LLM orchestration и provider routing.<br>Зачем нужен: управлять prompts, fallback-провайдерами, typed output, cache, budget и observability для LLM-вызовов.<br>Бизнес-смысл: стоимость и качество LLM становятся управляемыми: типовые запросы идут дешёвым маршрутом, сложные - в более сильный workflow.<br>Что проверить: Narrow scope, provider compatibility varies. | Typed structured outputs | Narrow scope, provider compatibility varies | Simple Pydantic extraction, low dependency | OSS `$0` | App-level | S | MIT | Yes OSS | Great structured output, not full orchestration |
| 9 | LiteLLM | LiteLLM — вариант для LLM orchestration и provider routing.<br>Зачем нужен: управлять prompts, fallback-провайдерами, typed output, cache, budget и observability для LLM-вызовов.<br>Бизнес-смысл: стоимость и качество LLM становятся управляемыми: типовые запросы идут дешёвым маршрутом, сложные - в более сильный workflow.<br>Что проверить: Another service in path, config governance. | Provider gateway, fallback, budgets | Another service in path, config governance | OpenAI-compatible proxy, routing, budget caps | OSS `$0`; LiteLLM Cloud paid/quote | 1-2 vCPU proxy + DB optional | S/M | MIT for OSS | Yes self-host | Strong provider abstraction/cache/logging |
| 10 | Portkey | Portkey — вариант для LLM orchestration и provider routing.<br>Зачем нужен: управлять prompts, fallback-провайдерами, typed output, cache, budget и observability для LLM-вызовов.<br>Бизнес-смысл: стоимость и качество LLM становятся управляемыми: типовые запросы идут дешёвым маршрутом, сложные - в более сильный workflow.<br>Что проверить: SaaS/commercial lock-in if cloud. | AI gateway, routing, observability | SaaS/commercial lock-in if cloud | Guardrails, cache, retries, analytics | OSS gateway + paid cloud/enterprise | Proxy service | S/M | Mixed OSS/commercial | Self-host options need review | Strong gateway features |
| 11 | Helicone | Helicone — вариант для LLM orchestration и provider routing.<br>Зачем нужен: управлять prompts, fallback-провайдерами, typed output, cache, budget и observability для LLM-вызовов.<br>Бизнес-смысл: стоимость и качество LLM становятся управляемыми: типовые запросы идут дешёвым маршрутом, сложные - в более сильный workflow.<br>Что проверить: SaaS residency unless self-host. | LLM observability/gateway | SaaS residency unless self-host | Simple logs, cache, cost analytics | OSS/self-host; cloud plans | Proxy + ClickHouse/Postgres | S/M | Apache 2.0 / commercial | Yes self-host | Strong observability, not workflow engine |
| 12 | Braintrust | Braintrust — вариант для LLM orchestration и provider routing.<br>Зачем нужен: управлять prompts, fallback-провайдерами, typed output, cache, budget и observability для LLM-вызовов.<br>Бизнес-смысл: стоимость и качество LLM становятся управляемыми: типовые запросы идут дешёвым маршрутом, сложные - в более сильный workflow.<br>Что проверить: SaaS data/compliance, price quote at scale. | Evals, prompt management, observability | SaaS data/compliance, price quote at scale | Strong evaluation workflow | Free/paid tiers, enterprise quote | SaaS/self-host options vary | M | Commercial | Depends on deployment | Strong eval/prompt governance |

**Рекомендации**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
| ------ | --------- | --------------------- | ----------------- |
| Budget | LiteLLM + Instructor + existing prompt files | `$0-5k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нужен provider fallback и structured output без внедрения полноценного workflow framework<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нужны HA, multi-tenant, replay, SLA 99.9% или нагрузка >100 запросов/мин |
| Optimal | LlamaIndex or Haystack + LiteLLM | `$5k-25k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если появляются повторяемые RAG pipelines, ingestion/query engines и понятная component model<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нет владельца эксплуатации, нет stage-gate на migration или объём пока похож на offline demo |
| Enterprise | LangGraph + LangSmith/Portkey/Braintrust | `$25k-100k+` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нужны multi-step graphs, human-in-loop, prompt governance, evals и audit по каждому шагу<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• ещё не подтверждены SLA, бюджет, security approval и выделенная Infra/SRE-команда |

**Пути миграции**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| Current hand-written pipeline -> LiteLLM | Keep `LLMClient` API, route provider calls through proxy | Low | Low |
| LiteLLM -> LangChain/LlamaIndex/Haystack | Wrap existing retriever/generator as components | Low-medium | Medium |
| LangChain -> LangGraph | Convert linear chain to graph nodes gradually | Low | Medium |
| SaaS observability -> self-host | Export logs/evals, standardize `run_id` and OpenTelemetry spans | Medium | Medium |

<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**

**Что это значит для проекта:** этот компонент закрывает задачу: управлять prompts, fallback-провайдерами, typed output, cache, budget и observability для LLM-вызовов. В контексте Clarify Engine это влияет не на "красоту архитектуры", а на скорость, проверяемость и стоимость анализа требований.

**Почему важно для БА:** БА получает стабильное поведение вместо набора разрозненных if/else: система объяснимо выбирает provider, prompt и fallback.

**Технически:**
- `LiteLLM` нормализует provider API и budgets, `Instructor` фиксирует Pydantic output, frameworks добавляют workflow graph.
- Prompt/version metadata должны попадать в audit, иначе нельзя повторить спорный ответ.
- Новый framework нельзя внедрять поверх `Pipeline` без adapter-слоя, чтобы не сломать текущий UI/export contract.

**Когда выбирать:**
- 🟢 **Budget:** для пилота Clarify Engine на 1-3 БА с нагрузкой ≤15 запросов/мин, если нужен provider fallback и structured output без внедрения полноценного workflow framework.
- 🟡 **Optimal:** для production pilot на 1-3 БА с нагрузкой ≤15 запросов/мин и ростом до нескольких сервисов, если появляются повторяемые RAG pipelines, ingestion/query engines и понятная component model.
- 🔵 **Enterprise:** после подтверждения SLA, бюджета, security approval и нагрузки >100 запросов/мин, если нужны multi-step graphs, human-in-loop, prompt governance, evals и audit по каждому шагу.

📚 **Читать далее:**
- [LiteLLM documentation](https://docs.litellm.ai/docs/) — provider routing, fallback и budgets, EN.
- [LlamaIndex documentation](https://docs.llamaindex.ai/) — RAG data framework, EN.
- [LangChain RAG tutorial](https://python.langchain.com/docs/tutorials/rag/) — пример RAG workflow, EN.

---
## 7. Компонент 4 - Document Parsing / Ingestion

**Ответственность:** извлекать текст, layout, таблицы и ссылки из DOCX/XLSX/PDF/PPTX, сохраняя locators.

| № | Решение | Пояснение для БА | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Formats / Layout / Tables / OCR / Speed / GPU / Multilingual |
| ---: | --------- | --- | ------------ | ------- | -------------- | ----------- | --------- | -------------- | ---------- | ------------------ | --------------------------------------------------------------- |
| 1 | Unstructured.io | Unstructured.io — вариант для document parsing и ingestion.<br>Зачем нужен: превращать DOCX/XLSX/PDF/PPTX в структурированные блоки текста, таблицы и locators.<br>Бизнес-смысл: система сохраняет страницы, разделы и таблицы, поэтому ответ можно проверить по источнику.<br>Что проверить: Some features/API commercial, parser variability. | Multi-format partitioning | Some features/API commercial, parser variability | Broad formats, chunking strategies | OSS `$0`; hosted API/platform paid/quote | CPU, optional OCR deps | M | Apache 2.0 core | Yes OSS self-host | DOCX/XLSX/PDF/PPTX, good layout, OCR optional |
| 2 | Docling (IBM) | Docling (IBM) — вариант для document parsing и ingestion.<br>Зачем нужен: превращать DOCX/XLSX/PDF/PPTX в структурированные блоки текста, таблицы и locators.<br>Бизнес-смысл: система сохраняет страницы, разделы и таблицы, поэтому ответ можно проверить по источнику.<br>Что проверить: Young but active, model downloads. | PDF/DOCX structure extraction | Young but active, model downloads | Strong layout/table pipeline, local-first | `$0 license` | CPU works; GPU helps OCR/layout models | M | MIT | Yes | PDF/DOCX/HTML/images, good layout/tables/OCR |
| 3 | Marker | Marker — вариант для document parsing и ingestion.<br>Зачем нужен: превращать DOCX/XLSX/PDF/PPTX в структурированные блоки текста, таблицы и locators.<br>Бизнес-смысл: система сохраняет страницы, разделы и таблицы, поэтому ответ можно проверить по источнику.<br>Что проверить: GPU recommended for speed/quality, PDF-focused. | PDF to Markdown/JSON | GPU recommended for speed/quality, PDF-focused | High-quality PDF markdown extraction | OSS `$0` | GPU preferred, CPU slower | M | GPL/other components need review | Yes if license accepted | PDF/images, good layout/OCR |
| 4 | MinerU | MinerU — вариант для document parsing и ingestion.<br>Зачем нужен: превращать DOCX/XLSX/PDF/PPTX в структурированные блоки текста, таблицы и locators.<br>Бизнес-смысл: система сохраняет страницы, разделы и таблицы, поэтому ответ можно проверить по источнику.<br>Что проверить: Heavier ML stack, ops complexity. | Document parsing/OCR | Heavier ML stack, ops complexity | Strong academic/enterprise doc parsing | OSS `$0` | GPU preferred | M/H | AGPL/Apache mix depending package, review required | Yes if license accepted | PDF/images, OCR/layout strong |
| 5 | olmOCR | olmOCR — вариант для document parsing и ingestion.<br>Зачем нужен: превращать DOCX/XLSX/PDF/PPTX в структурированные блоки текста, таблицы и locators.<br>Бизнес-смысл: система сохраняет страницы, разделы и таблицы, поэтому ответ можно проверить по источнику.<br>Что проверить: OCR-only layer, model/runtime cost. | OCR for documents | OCR-only layer, model/runtime cost | Local OCR for scanned PDFs | OSS `$0` | GPU recommended | M | Apache 2.0 | Yes | OCR strong, combine with parser |
| 6 | PyMuPDF | PyMuPDF — вариант для document parsing и ingestion.<br>Зачем нужен: превращать DOCX/XLSX/PDF/PPTX в структурированные блоки текста, таблицы и locators.<br>Бизнес-смысл: система сохраняет страницы, разделы и таблицы, поэтому ответ можно проверить по источнику.<br>Что проверить: Manual structure logic needed. | PDF text/images/layout primitives | Manual structure logic needed | Fast, reliable, simple | OSS/commercial dual; AGPL/commercial review | CPU | S | AGPL/commercial | Yes if license accepted | PDF only, layout primitives, no OCR |
| 7 | pdfplumber | pdfplumber — вариант для document parsing и ingestion.<br>Зачем нужен: превращать DOCX/XLSX/PDF/PPTX в структурированные блоки текста, таблицы и locators.<br>Бизнес-смысл: система сохраняет страницы, разделы и таблицы, поэтому ответ можно проверить по источнику.<br>Что проверить: Slower, PDF quirks. | PDF text/tables | Slower, PDF quirks | Good table/debug extraction | `$0 license` | CPU | S | MIT | Yes | PDF tables/layout, no OCR |
| 8 | Camelot | Camelot — вариант для document parsing и ingestion.<br>Зачем нужен: превращать DOCX/XLSX/PDF/PPTX в структурированные блоки текста, таблицы и locators.<br>Бизнес-смысл: система сохраняет страницы, разделы и таблицы, поэтому ответ можно проверить по источнику.<br>Что проверить: Works best on text PDFs, Java/Ghostscript deps. | PDF table extraction | Works best on text PDFs, Java/Ghostscript deps | Focused table extraction | `$0 license` | CPU | S/M | MIT | Yes | PDF tables strong for lattice/stream |
| 9 | Tabula-py | Tabula-py — вариант для document parsing и ingestion.<br>Зачем нужен: превращать DOCX/XLSX/PDF/PPTX в структурированные блоки текста, таблицы и locators.<br>Бизнес-смысл: система сохраняет страницы, разделы и таблицы, поэтому ответ можно проверить по источнику.<br>Что проверить: Java dependency, scanned PDFs need OCR. | PDF table extraction | Java dependency, scanned PDFs need OCR | Mature simple table extraction | `$0 license` | CPU + Java | S/M | MIT | Yes | PDF tables |
| 10 | LlamaParse | LlamaParse — вариант для document parsing и ingestion.<br>Зачем нужен: превращать DOCX/XLSX/PDF/PPTX в структурированные блоки текста, таблицы и locators.<br>Бизнес-смысл: система сохраняет страницы, разделы и таблицы, поэтому ответ можно проверить по источнику.<br>Что проверить: SaaS, data residency, usage cost. | Managed parsing API | SaaS, data residency, usage cost | Fast high-quality parsing, integrates LlamaIndex | Paid credits/subscription | Managed | XS/S | Commercial SaaS | No local by default | Broad formats, strong layout, OCR managed |
| 11 | Azure Document Intelligence | Azure Document Intelligence — вариант для document parsing и ingestion.<br>Зачем нужен: превращать DOCX/XLSX/PDF/PPTX в структурированные блоки текста, таблицы и locators.<br>Бизнес-смысл: система сохраняет страницы, разделы и таблицы, поэтому ответ можно проверить по источнику.<br>Что проверить: Azure lock-in, residency approval. | OCR/forms/layout/tables | Azure lock-in, residency approval | Mature enterprise OCR/layout | Free 500 pages/month; Read `$1.50/1k pages`, Layout/Prebuilt `$10/1k`, custom extraction `$30/1k` | Managed | S/M | Commercial SaaS | Region-dependent | Broad docs, strong OCR/tables |
| 12 | Google Document AI | Google Document AI — вариант для document parsing и ingestion.<br>Зачем нужен: превращать DOCX/XLSX/PDF/PPTX в структурированные блоки текста, таблицы и locators.<br>Бизнес-смысл: система сохраняет страницы, разделы и таблицы, поэтому ответ можно проверить по источнику.<br>Что проверить: GCP lock-in, custom processor cost. | OCR/processors/extractors | GCP lock-in, custom processor cost | Strong managed extraction, human review options | OCR `$1.50/1k pages`, Layout `$10/1k`, Form Parser/Custom Extractor `$30/1k` | Managed | S/M | Commercial SaaS | Region-dependent | Broad docs, strong OCR/layout |
| 13 | Amazon Textract | Amazon Textract — вариант для document parsing и ingestion.<br>Зачем нужен: превращать DOCX/XLSX/PDF/PPTX в структурированные блоки текста, таблицы и locators.<br>Бизнес-смысл: система сохраняет страницы, разделы и таблицы, поэтому ответ можно проверить по источнику.<br>Что проверить: AWS lock-in, per-page cost. | OCR/forms/tables/queries | AWS lock-in, per-page cost | Mature OCR, forms/tables, async jobs | Detect text starts around `$1.50/1k pages`; tables/forms/queries higher by feature and region | Managed | S/M | Commercial SaaS | Region-dependent | PDF/images, strong OCR/tables |
| 14 | python-docx + openpyxl | python-docx + openpyxl — вариант для document parsing и ingestion.<br>Зачем нужен: превращать DOCX/XLSX/PDF/PPTX в структурированные блоки текста, таблицы и locators.<br>Бизнес-смысл: система сохраняет страницы, разделы и таблицы, поэтому ответ можно проверить по источнику.<br>Что проверить: Limited PDFs/OCR, custom layout logic. | DOCX/XLSX custom parser | Limited PDFs/OCR, custom layout logic | Already fits current code, deterministic | `$0 license` | CPU | S | MIT | Yes | DOCX/XLSX good enough, no OCR |

**Рекомендации**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
| ------ | --------- | --------------------- | ----------------- |
| Budget | python-docx/openpyxl + PyMuPDF/pdfplumber | `$0-5k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если документы в основном текстовые, без тяжёлого OCR, а локаторы можно получить текущими parser-библиотеками<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нужны HA, multi-tenant, replay, SLA 99.9% или нагрузка >100 запросов/мин |
| Optimal | Docling + Unstructured + custom locator layer | `$5k-20k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если встречаются смешанные PDF/DOCX с таблицами и нужен local-first extraction без SaaS<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нет владельца эксплуатации, нет stage-gate на migration или объём пока похож на offline demo |
| Enterprise | Azure DI / Textract / Document AI / LlamaParse | `$20k-100k+` usage | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если много сканов, нужен managed OCR SLA и security/legal approval на передачу документов<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• ещё не подтверждены SLA, бюджет, security approval и выделенная Infra/SRE-команда |

**Пути миграции**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| Current parsers -> Docling/Unstructured | Keep `load_requirements_by_extension`, enrich locator fields additively | Low | Medium |
| Local parsers -> managed OCR | Route only scanned/failed docs to SaaS, store raw + extracted JSON | Low | Medium |
| Managed OCR -> local | Preserve canonical `DocumentBlock` JSON, re-run extraction asynchronously | Medium | Medium |
| One parser -> ensemble | Add confidence and provenance per block, keep best block by type | Low | Medium |

<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**

**Что это значит для проекта:** этот компонент закрывает задачу: превращать DOCX/XLSX/PDF/PPTX в структурированные блоки текста, таблицы и locators. В контексте Clarify Engine это влияет не на "красоту архитектуры", а на скорость, проверяемость и стоимость анализа требований.

**Почему важно для БА:** Для БА parser определяет, можно ли доверять цитате: если таблица или номер раздела потеряны на входе, LLM уже не восстановит доказательство.

**Технически:**
- `load_requirements_by_extension` должен остаться фасадом, а новый parser добавляет поля additively.
- Raw file, extracted JSON и parser confidence нужно сохранять для повторной проверки.
- Managed OCR включается только через compliance gate и желательно только для failed/scanned documents.

**Когда выбирать:**
- 🟢 **Budget:** для пилота Clarify Engine на 1-3 БА с нагрузкой ≤15 запросов/мин, если документы в основном текстовые, без тяжёлого OCR, а локаторы можно получить текущими parser-библиотеками.
- 🟡 **Optimal:** для production pilot на 1-3 БА с нагрузкой ≤15 запросов/мин и ростом до нескольких сервисов, если встречаются смешанные PDF/DOCX с таблицами и нужен local-first extraction без SaaS.
- 🔵 **Enterprise:** после подтверждения SLA, бюджета, security approval и нагрузки >100 запросов/мин, если много сканов, нужен managed OCR SLA и security/legal approval на передачу документов.

📚 **Читать далее:**
- [Docling GitHub repository](https://github.com/docling-project/docling) — local-first document conversion, EN.
- [Unstructured open source overview](https://docs.unstructured.io/open-source/introduction/overview) — partitioning и chunking, EN.
- [Azure Document Intelligence documentation](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/) — managed OCR/layout, EN.

---
## 8. Компонент 5 - Embedding Models

**Ответственность:** превращать chunks и queries в векторы для semantic и hybrid retrieval.

| № | Решение | Пояснение для БА | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Dim / RU+EN / Max length / Speed / Size / Benchmark / API cost |
| ---: | --------- | --- | ------------ | ------- | -------------- | ----------- | --------- | -------------- | ---------- | ------------------ | ---------------------------------------------------------------- |
| 1 | BAAI/bge-m3 | BAAI/bge-m3 — вариант для embedding models.<br>Зачем нужен: переводить chunks и queries в vectors для semantic и hybrid retrieval.<br>Бизнес-смысл: поиск понимает разные формулировки одного требования и не требует ручного словаря для каждого синонима.<br>Что проверить: Local model ops, CPU latency. | Multilingual dense+sparse embeddings | Local model ops, CPU latency | Strong multilingual/RU, current candidate, long context | `$0 license`; infra only | CPU usable, GPU faster; ~2 GB model class | S/M | MIT | Yes local | 1024 dim, RU/EN strong, 8192 tokens |
| 2 | all-MiniLM-L6-v2 | all-MiniLM-L6-v2 — вариант для embedding models.<br>Зачем нужен: переводить chunks и queries в vectors для semantic и hybrid retrieval.<br>Бизнес-смысл: поиск понимает разные формулировки одного требования и не требует ручного словаря для каждого синонима.<br>Что проверить: English-biased, lower RU/domain quality. | Cheap small embeddings | English-biased, lower RU/domain quality | Very fast CPU baseline | `$0 license` | CPU, small memory | XS/S | Apache 2.0 | Yes | 384 dim, short max length, fast |
| 3 | OpenAI text-embedding-3-large | OpenAI text-embedding-3-large — вариант для embedding models.<br>Зачем нужен: переводить chunks и queries в vectors для semantic и hybrid retrieval.<br>Бизнес-смысл: поиск понимает разные формулировки одного требования и не требует ручного словаря для каждого синонима.<br>Что проверить: External SaaS, data residency, token cost. | High-quality API embeddings | External SaaS, data residency, token cost | Strong multilingual, dimensions shortening | `$0.13 / 1M tokens`, batch `$0.065` | Managed | S | Commercial API | No local; region/data policy approval needed | 3072 dim default, strong RU/EN |
| 4 | OpenAI text-embedding-3-small | OpenAI text-embedding-3-small — вариант для embedding models.<br>Зачем нужен: переводить chunks и queries в vectors для semantic и hybrid retrieval.<br>Бизнес-смысл: поиск понимает разные формулировки одного требования и не требует ручного словаря для каждого синонима.<br>Что проверить: Same SaaS risks. | Cheap API embeddings | Same SaaS risks | Very low price, good baseline | `$0.02 / 1M tokens`, batch `$0.01` | Managed | S | Commercial API | No local | 1536 dim default |
| 5 | Cohere embed-multilingual-v3/v4 | Cohere embed-multilingual-v3/v4 — вариант для embedding models.<br>Зачем нужен: переводить chunks и queries в vectors для semantic и hybrid retrieval.<br>Бизнес-смысл: поиск понимает разные формулировки одного требования и не требует ручного словаря для каждого синонима.<br>Что проверить: SaaS/commercial, pricing/version changes. | Multilingual enterprise embeddings | SaaS/commercial, pricing/version changes | Strong multilingual, enterprise support | Public pricing page; commonly per-token usage, verify quote | Managed | S | Commercial API | No local unless private deployment agreed | RU/EN strong, API |
| 6 | Voyage AI voyage-3 | Voyage AI voyage-3 — вариант для embedding models.<br>Зачем нужен: переводить chunks и queries в vectors для semantic и hybrid retrieval.<br>Бизнес-смысл: поиск понимает разные формулировки одного требования и не требует ручного словаря для каждого синонима.<br>Что проверить: SaaS, smaller enterprise footprint. | Retrieval-optimized API embeddings | SaaS, smaller enterprise footprint | Strong retrieval benchmarks, rerank pairing | Public usage pricing, verify current model rate | Managed | S | Commercial API | No local | Dim/model-dependent |
| 7 | Nomic embed-text | Nomic embed-text — вариант для embedding models.<br>Зачем нужен: переводить chunks и queries в vectors для semantic и hybrid retrieval.<br>Бизнес-смысл: поиск понимает разные формулировки одного требования и не требует ручного словаря для каждого синонима.<br>Что проверить: Quality varies by language/domain. | Open/local embeddings | Quality varies by language/domain | Open weights, local/private | `$0 license` for open model; Nomic API paid | CPU/GPU local | S/M | Apache 2.0 for model variants | Yes local | Good EN, RU must benchmark |
| 8 | jina-embeddings-v3/v4/v5 | jina-embeddings-v3/v4/v5 — вариант для embedding models.<br>Зачем нужен: переводить chunks и queries в vectors для semantic и hybrid retrieval.<br>Бизнес-смысл: поиск понимает разные формулировки одного требования и не требует ручного словаря для каждого синонима.<br>Что проверить: API/local version selection, license review. | Multilingual long-context embeddings | API/local version selection, license review | Strong multilingual, long context, API or local | Open weights/API paid tiers | CPU/GPU local or managed | M | CC BY-NC / Apache/commercial varies by model, review required | Local possible if license accepted | RU/EN strong, long context |
| 9 | e5-mistral-7b-instruct | e5-mistral-7b-instruct — вариант для embedding models.<br>Зачем нужен: переводить chunks и queries в vectors для semantic и hybrid retrieval.<br>Бизнес-смысл: поиск понимает разные формулировки одного требования и не требует ручного словаря для каждого синонима.<br>Что проверить: Large/slow, GPU-heavy. | High-quality instruct embeddings | Large/slow, GPU-heavy | Strong benchmark quality | `$0 license` | GPU recommended, 7B class | M/H | MIT/Apache model-card review | Yes local | 4096 dim class, high quality |
| 10 | intfloat/multilingual-e5-large | intfloat/multilingual-e5-large — вариант для embedding models.<br>Зачем нужен: переводить chunks и queries в vectors для semantic и hybrid retrieval.<br>Бизнес-смысл: поиск понимает разные формулировки одного требования и не требует ручного словаря для каждого синонима.<br>Что проверить: Older vs bge-m3, local ops. | Multilingual retrieval embeddings | Older vs bge-m3, local ops | Strong multilingual baseline | `$0 license` | CPU/GPU, ~1 GB class | S/M | MIT | Yes local | 1024 dim, RU/EN strong |
| 11 | GigaChat embeddings | GigaChat embeddings — вариант для embedding models.<br>Зачем нужен: переводить chunks и queries в vectors для semantic и hybrid retrieval.<br>Бизнес-смысл: поиск понимает разные формулировки одного требования и не требует ручного словаря для каждого синонима.<br>Что проверить: Provider access/pricing, external API. | RU provider embeddings | Provider access/pricing, external API | RU ecosystem, local compliance may be easier than US SaaS | Provider tariff/quote | Managed | S | Commercial API | RU provider, contract-dependent | RU strong, API |
| 12 | YandexGPT embeddings | YandexGPT embeddings — вариант для embedding models.<br>Зачем нужен: переводить chunks и queries в vectors для semantic и hybrid retrieval.<br>Бизнес-смысл: поиск понимает разные формулировки одного требования и не требует ручного словаря для каждого синонима.<br>Что проверить: Provider lock-in, tariff changes. | RU provider embeddings | Provider lock-in, tariff changes | RU cloud ecosystem, possible data residency | Provider tariff/quote | Managed | S | Commercial API | RU cloud/contract-dependent | RU strong, API |

**Рекомендации**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
| ------ | --------- | --------------------- | ----------------- |
| Budget | bge-m3 local | `$1k-8k` infra | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нужна RU-resident модель без внешней передачи текста и достаточно CPU/GPU одной машины<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нужны HA, multi-tenant, replay, SLA 99.9% или нагрузка >100 запросов/мин |
| Optimal | bge-m3 + multilingual-e5/Jina benchmark fallback | `$5k-20k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нужно сравнить качество bge-m3, multilingual-e5 и Jina на Golden Set без SaaS<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нет владельца эксплуатации, нет stage-gate на migration или объём пока похож на offline demo |
| Enterprise | OpenAI/Cohere/Voyage/RU provider API with local fallback | `$10k-100k+` usage | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если внешние API approved, нужна managed throughput и есть бюджет на re-embedding<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• ещё не подтверждены SLA, бюджет, security approval и выделенная Infra/SRE-команда |

**Пути миграции**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| Any embedding model -> another | Re-embed corpus into parallel index, run retrieval eval, switch alias | Low with dual index | Medium |
| Local -> API | Add batch embedding worker, redact PII before calls, cache by text hash | Low | Medium-high compliance |
| API -> local | Keep original text/chunk IDs, re-embed asynchronously, compare recall/MRR | Low-medium | Medium |
| 768 dim -> 1024/3072 dim | Requires new vector index/schema; cannot mix dims in same field | Medium | Medium |

<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**

**Что это значит для проекта:** этот компонент закрывает задачу: переводить chunks и queries в vectors для semantic и hybrid retrieval. В контексте Clarify Engine это влияет не на "красоту архитектуры", а на скорость, проверяемость и стоимость анализа требований.

**Почему важно для БА:** БА не видит embeddings напрямую, но именно они определяют, найдётся ли раздел про SSO по запросу 'единый вход'.

**Технически:**
- Размерность vectors фиксирует schema индекса; 768, 1024 и 3072 нельзя смешивать в одном field.
- Смена модели требует parallel re-embedding, retrieval metrics и controlled switch.
- PII-sensitive chunks нельзя отправлять во внешний embedding API без masking/approval.

**Когда выбирать:**
- 🟢 **Budget:** для пилота Clarify Engine на 1-3 БА с нагрузкой ≤15 запросов/мин, если нужна RU-resident модель без внешней передачи текста и достаточно CPU/GPU одной машины.
- 🟡 **Optimal:** для production pilot на 1-3 БА с нагрузкой ≤15 запросов/мин и ростом до нескольких сервисов, если нужно сравнить качество bge-m3, multilingual-e5 и Jina на Golden Set без SaaS.
- 🔵 **Enterprise:** после подтверждения SLA, бюджета, security approval и нагрузки >100 запросов/мин, если внешние API approved, нужна managed throughput и есть бюджет на re-embedding.

📚 **Читать далее:**
- [BAAI/bge-m3 model card](https://huggingface.co/BAAI/bge-m3) — multilingual dense/sparse embeddings, EN.
- [OpenAI embeddings guide](https://platform.openai.com/docs/guides/embeddings) — API embeddings concepts, EN.
- [Jina embeddings documentation](https://jina.ai/embeddings/) — multilingual embeddings, EN.

---
## 9. Компонент 6 - Local LLM Serving

**Ответственность:** обслуживать локальные модели для PII-sensitive generation, routing/classification, fallback и batch jobs.

| № | Решение | Пояснение для БА | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Quant / Throughput / TTFT / GPU / CPU / Multi-GPU / Batching / API / Formats |
| ---: | --------- | --- | ------------ | ------- | -------------- | ----------- | --------- | -------------- | ---------- | ------------------ | -------------------------------------------------------------------------------- |
| 1 | Ollama | Ollama — вариант для local LLM serving.<br>Зачем нужен: запускать LLM внутри контролируемой инфраструктуры для PII-sensitive запросов и fallback.<br>Бизнес-смысл: чувствительные документы не уходят во внешний API, а pilot не зависит полностью от доступности SaaS-провайдера.<br>Что проверить: Lower throughput, limited production controls. | Simple local model serving | Lower throughput, limited production controls | Fast install, GGUF, local dev | `$0 license` | CPU or GPU, 8-24 GB VRAM for 7B-13B | XS/S | MIT | Yes local | Good quant, CPU/GPU, OpenAI-compatible partial |
| 2 | vLLM | vLLM — вариант для local LLM serving.<br>Зачем нужен: запускать LLM внутри контролируемой инфраструктуры для PII-sensitive запросов и fallback.<br>Бизнес-смысл: чувствительные документы не уходят во внешний API, а pilot не зависит полностью от доступности SaaS-провайдера.<br>Что проверить: GPU-first, ops tuning. | High-throughput inference | GPU-first, ops tuning | PagedAttention, continuous batching, OpenAI API | `$0 license` | NVIDIA GPU, 16-80 GB VRAM | M | Apache 2.0 | Yes local | Excellent throughput/batching, multi-GPU |
| 3 | TGI | TGI — вариант для local LLM serving.<br>Зачем нужен: запускать LLM внутри контролируемой инфраструктуры для PII-sensitive запросов и fallback.<br>Бизнес-смысл: чувствительные документы не уходят во внешний API, а pilot не зависит полностью от доступности SaaS-провайдера.<br>Что проверить: GPU ops, model compatibility. | HF production serving | GPU ops, model compatibility | Mature server, streaming, quantization | `$0 license` | GPU recommended | M | Apache 2.0 | Yes local | Good throughput, safetensors |
| 4 | llama.cpp | llama.cpp — вариант для local LLM serving.<br>Зачем нужен: запускать LLM внутри контролируемой инфраструктуры для PII-sensitive запросов и fallback.<br>Бизнес-смысл: чувствительные документы не уходят во внешний API, а pilot не зависит полностью от доступности SaaS-провайдера.<br>Что проверить: Lower throughput for high concurrency. | CPU/GPU GGUF inference | Lower throughput for high concurrency | Very portable, quantization, edge/offline | `$0 license` | CPU viable, Metal/CUDA/Vulkan | S/M | MIT | Yes local | Excellent quant, CPU-only strong, GGUF |
| 5 | TensorRT-LLM | TensorRT-LLM — вариант для local LLM serving.<br>Зачем нужен: запускать LLM внутри контролируемой инфраструктуры для PII-sensitive запросов и fallback.<br>Бизнес-смысл: чувствительные документы не уходят во внешний API, а pilot не зависит полностью от доступности SaaS-провайдера.<br>Что проверить: NVIDIA lock-in, complex build. | NVIDIA optimized inference | NVIDIA lock-in, complex build | Best latency/throughput on NVIDIA | `$0 license` | NVIDIA GPU, high VRAM | H | Apache 2.0 | Yes local | Excellent throughput, multi-GPU |
| 6 | DeepSpeed-MII/Inference | DeepSpeed-MII/Inference — вариант для local LLM serving.<br>Зачем нужен: запускать LLM внутри контролируемой инфраструктуры для PII-sensitive запросов и fallback.<br>Бизнес-смысл: чувствительные документы не уходят во внешний API, а pilot не зависит полностью от доступности SaaS-провайдера.<br>Что проверить: Complex, less simple than vLLM. | Distributed inference | Complex, less simple than vLLM | Large model distributed serving | `$0 license` | Multi-GPU | H | MIT | Yes local | Multi-GPU strong |
| 7 | HF Transformers native | HF Transformers native — вариант для local LLM serving.<br>Зачем нужен: запускать LLM внутри контролируемой инфраструктуры для PII-sensitive запросов и fallback.<br>Бизнес-смысл: чувствительные документы не уходят во внешний API, а pilot не зависит полностью от доступности SaaS-провайдера.<br>Что проверить: Not optimized serving by default. | Baseline model execution | Not optimized serving by default | Maximum compatibility, easy experiments | `$0 license` | CPU/GPU | S/M | Apache 2.0 | Yes local | Good for experiments, not high QPS |
| 8 | CTranslate2 | CTranslate2 — вариант для local LLM serving.<br>Зачем нужен: запускать LLM внутри контролируемой инфраструктуры для PII-sensitive запросов и fallback.<br>Бизнес-смысл: чувствительные документы не уходят во внешний API, а pilot не зависит полностью от доступности SaaS-провайдера.<br>Что проверить: Model conversion required, less LLM-chat ecosystem. | Efficient CPU/GPU inference | Model conversion required, less LLM-chat ecosystem | Fast CPU/GPU, quantized | `$0 license` | CPU/GPU | M | MIT | Yes local | Strong CPU, model format conversion |
| 9 | MLX | MLX — вариант для local LLM serving.<br>Зачем нужен: запускать LLM внутри контролируемой инфраструктуры для PII-sensitive запросов и fallback.<br>Бизнес-смысл: чувствительные документы не уходят во внешний API, а pilot не зависит полностью от доступности SaaS-провайдера.<br>Что проверить: Mac-only, not server standard. | Apple Silicon local inference | Mac-only, not server standard | Great developer laptops/M-series | `$0 license` | Apple Silicon unified memory | S | MIT | Local only | Metal, local dev |
| 10 | Exo | Exo — вариант для local LLM serving.<br>Зачем нужен: запускать LLM внутри контролируемой инфраструктуры для PII-sensitive запросов и fallback.<br>Бизнес-смысл: чувствительные документы не уходят во внешний API, а pilot не зависит полностью от доступности SaaS-провайдера.<br>Что проверить: Young, production maturity risk. | Decentralized local inference | Young, production maturity risk | Multi-device local experiments | OSS `$0` | Multiple local devices | M/H | Apache/MIT review | Yes local | Experimental distributed serving |
| 11 | Replicate self-host / Cog | Replicate self-host / Cog — вариант для local LLM serving.<br>Зачем нужен: запускать LLM внутри контролируемой инфраструктуры для PII-sensitive запросов и fallback.<br>Бизнес-смысл: чувствительные документы не уходят во внешний API, а pilot не зависит полностью от доступности SaaS-провайдера.<br>Что проверить: SaaS path external, self-host ops. | Model packaging/deploy | SaaS path external, self-host ops | Reproducible model containers | OSS tools + cloud paid | Docker/GPU | M | Apache 2.0 tools / commercial cloud | Self-host possible | Good packaging |
| 12 | BentoML | BentoML — вариант для local LLM serving.<br>Зачем нужен: запускать LLM внутри контролируемой инфраструктуры для PII-sensitive запросов и fallback.<br>Бизнес-смысл: чувствительные документы не уходят во внешний API, а pilot не зависит полностью от доступности SaaS-провайдера.<br>Что проверить: Need infra decisions, not LLM-specific enough alone. | Model service packaging | Need infra decisions, not LLM-specific enough alone | API packaging, deployment, scaling | OSS `$0`; BentoCloud paid | CPU/GPU | M | Apache 2.0 | Yes self-host | Good service framework |

**Рекомендации**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
| ------ | --------- | --------------------- | ----------------- |
| Budget | Ollama / llama.cpp | `$1k-8k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нужен single-node/offline pilot, простая установка на АРМ и допустима ограниченная concurrency<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нужны HA, multi-tenant, replay, SLA 99.9% или нагрузка >100 запросов/мин |
| Optimal | vLLM or TGI | `$10k-60k` GPU infra | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если у пилота несколько БА, нужна OpenAI-compatible API и batching на GPU<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нет владельца эксплуатации, нет stage-gate на migration или объём пока похож на offline demo |
| Enterprise | TensorRT-LLM + KServe/BentoML | `$60k-300k+` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если есть dedicated GPU platform, SLA latency и SRE/ML-infra команда<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• ещё не подтверждены SLA, бюджет, security approval и выделенная Infra/SRE-команда |

**Пути миграции**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| Ollama -> vLLM | Keep OpenAI-compatible client, change base URL/model names, validate prompts | Low | Medium |
| vLLM -> TGI | Abstract streaming/chat payload differences | Low-medium | Medium |
| Local -> managed API | Route through LiteLLM, retain local fallback for PII | Low | Compliance high |
| Single GPU -> multi-GPU | Benchmark tensor/pipeline parallelism, pin model versions | Medium | High |

<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**

**Что это значит для проекта:** этот компонент закрывает задачу: запускать LLM внутри контролируемой инфраструктуры для PII-sensitive запросов и fallback. В контексте Clarify Engine это влияет не на "красоту архитектуры", а на скорость, проверяемость и стоимость анализа требований.

**Почему важно для БА:** Для БА local serving означает понятную границу данных: sensitive prompts остаются внутри контура, но бизнес должен оплатить GPU/ops при росте нагрузки.

**Технически:**
- `Ollama`/`llama.cpp` хороши для установки, `vLLM`/`TGI` - для throughput, `TensorRT-LLM` - для NVIDIA-оптимизации.
- Клиент должен говорить через стабильный OpenAI-compatible или adapter API, чтобы миграция была заменой endpoint/model.
- Model version, quantization и decoding params фиксируются в audit для повторяемости.

**Когда выбирать:**
- 🟢 **Budget:** для пилота Clarify Engine на 1-3 БА с нагрузкой ≤15 запросов/мин, если нужен single-node/offline pilot, простая установка на АРМ и допустима ограниченная concurrency.
- 🟡 **Optimal:** для production pilot на 1-3 БА с нагрузкой ≤15 запросов/мин и ростом до нескольких сервисов, если у пилота несколько БА, нужна OpenAI-compatible API и batching на GPU.
- 🔵 **Enterprise:** после подтверждения SLA, бюджета, security approval и нагрузки >100 запросов/мин, если есть dedicated GPU platform, SLA latency и SRE/ML-infra команда.

📚 **Читать далее:**
- [Ollama API documentation](https://github.com/ollama/ollama/blob/main/docs/api.md) — локальный HTTP API, EN.
- [vLLM documentation](https://docs.vllm.ai/) — high-throughput serving, EN.
- [Hugging Face TGI documentation](https://huggingface.co/docs/text-generation-inference/index) — production inference server, EN.

---
## 10. Компонент 7 - Cross-Encoder Reranker

**Ответственность:** переупорядочивать top-K retrieval candidates, чтобы повысить precision и grounding.

| № | Решение | Пояснение для БА | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Accuracy / Latency / Size / GPU vs CPU / API cost / Languages / Integration |
| ---: | --------- | --- | ------------ | ------- | -------------- | ----------- | --------- | -------------- | ---------- | ------------------ | ---------------------------------------------------------------------------- |
| 1 | BAAI/bge-reranker-large | BAAI/bge-reranker-large — вариант для rerank stage.<br>Зачем нужен: пересортировывать top-K найденных chunks по реальной полезности для конкретного запроса.<br>Бизнес-смысл: в prompt попадает меньше похожих, но неверных фрагментов, поэтому ответы становятся точнее без замены основной LLM.<br>Что проверить: CPU latency, GPU needed for p95. | Local high-quality rerank | CPU latency, GPU needed for p95 | Strong multilingual, popular | `$0 license` | GPU recommended; CPU slower | S/M | MIT | Yes local | High accuracy, medium-high latency |
| 2 | BAAI/bge-reranker-base | BAAI/bge-reranker-base — вариант для rerank stage.<br>Зачем нужен: пересортировывать top-K найденных chunks по реальной полезности для конкретного запроса.<br>Бизнес-смысл: в prompt попадает меньше похожих, но неверных фрагментов, поэтому ответы становятся точнее без замены основной LLM.<br>Что проверить: Lower quality than large. | Local balanced rerank | Lower quality than large | Better latency/cost | `$0 license` | CPU/GPU | S | MIT | Yes local | Good accuracy, medium latency |
| 3 | Cohere Rerank API | Cohere Rerank API — вариант для rerank stage.<br>Зачем нужен: пересортировывать top-K найденных chunks по реальной полезности для конкретного запроса.<br>Бизнес-смысл: в prompt попадает меньше похожих, но неверных фрагментов, поэтому ответы становятся точнее без замены основной LLM.<br>Что проверить: SaaS/residency, usage cost. | Managed reranking | SaaS/residency, usage cost | Strong multilingual, simple API | Public pricing/check current rate; OpenRouter lists rerank-v3.5 per search | Managed | S | Commercial API | No local | High accuracy, low integration cost |
| 4 | Jina Reranker | Jina Reranker — вариант для rerank stage.<br>Зачем нужен: пересортировывать top-K найденных chunks по реальной полезности для конкретного запроса.<br>Бизнес-смысл: в prompt попадает меньше похожих, но неверных фрагментов, поэтому ответы становятся точнее без замены основной LLM.<br>Что проверить: License/model/version review. | API/local reranker | License/model/version review | Multilingual, listwise models | API paid; local model possible | Managed or GPU local | M | Mixed model licenses | Local possible | High multilingual quality |
| 5 | Voyage AI rerank | Voyage AI rerank — вариант для rerank stage.<br>Зачем нужен: пересортировывать top-K найденных chunks по реальной полезности для конкретного запроса.<br>Бизнес-смысл: в prompt попадает меньше похожих, но неверных фрагментов, поэтому ответы становятся точнее без замены основной LLM.<br>Что проверить: SaaS/residency. | Managed reranking | SaaS/residency | Strong retrieval stack | Usage pricing, verify current | Managed | S | Commercial API | No local | High accuracy, simple API |
| 6 | cross-encoder/ms-marco-MiniLM-L-6-v2 | cross-encoder/ms-marco-MiniLM-L-6-v2 — вариант для rerank stage.<br>Зачем нужен: пересортировывать top-K найденных chunks по реальной полезности для конкретного запроса.<br>Бизнес-смысл: в prompt попадает меньше похожих, но неверных фрагментов, поэтому ответы становятся точнее без замены основной LLM.<br>Что проверить: English-biased, RU lower. | Small local reranker | English-biased, RU lower | Very fast CPU baseline | `$0 license` | CPU | XS/S | Apache 2.0 | Yes local | Medium accuracy, low latency |
| 7 | cross-encoder/ms-marco-TinyBERT-L-2-v2 | cross-encoder/ms-marco-TinyBERT-L-2-v2 — вариант для rerank stage.<br>Зачем нужен: пересортировывать top-K найденных chunks по реальной полезности для конкретного запроса.<br>Бизнес-смысл: в prompt попадает меньше похожих, но неверных фрагментов, поэтому ответы становятся точнее без замены основной LLM.<br>Что проверить: Lower quality. | Tiny local reranker | Lower quality | Very low latency | `$0 license` | CPU | XS/S | Apache 2.0 | Yes local | Low-medium accuracy |
| 8 | NV-RerankQA | NV-RerankQA — вариант для rerank stage.<br>Зачем нужен: пересортировывать top-K найденных chunks по реальной полезности для конкретного запроса.<br>Бизнес-смысл: в prompt попадает меньше похожих, но неверных фрагментов, поэтому ответы становятся точнее без замены основной LLM.<br>Что проверить: Hardware/vendor dependence. | NVIDIA reranker | Hardware/vendor dependence | Optimized enterprise AI stack | API/NVIDIA platform quote | GPU/API | M | Commercial/model license | Local possible with NVIDIA stack | High performance, enterprise support |
| 9 | RankGPT | RankGPT — вариант для rerank stage.<br>Зачем нужен: пересортировывать top-K найденных chunks по реальной полезности для конкретного запроса.<br>Бизнес-смысл: в prompt попадает меньше похожих, но неверных фрагментов, поэтому ответы становятся точнее без замены основной LLM.<br>Что проверить: Expensive/slow, hallucination risk. | LLM-based reranking | Expensive/slow, hallucination risk | Strong reasoning over candidates | Depends on LLM tokens | LLM API/local | M | Method, not product | Local if local LLM | High accuracy, high latency |
| 10 | ColBERT v2 | ColBERT v2 — вариант для rerank stage.<br>Зачем нужен: пересортировывать top-K найденных chunks по реальной полезности для конкретного запроса.<br>Бизнес-смысл: в prompt попадает меньше похожих, но неверных фрагментов, поэтому ответы становятся точнее без замены основной LLM.<br>Что проверить: Index/storage complexity. | Late-interaction retrieval/rerank | Index/storage complexity | Strong precision with token-level matching | `$0 license`; infra | GPU for indexing, larger index | H | MIT | Yes local | High quality, higher storage |
| 11 | FlashRank | FlashRank — вариант для rerank stage.<br>Зачем нужен: пересортировывать top-K найденных chunks по реальной полезности для конкретного запроса.<br>Бизнес-смысл: в prompt попадает меньше похожих, но неверных фрагментов, поэтому ответы становятся точнее без замены основной LLM.<br>Что проверить: Model choices limited. | Lightweight reranking library | Model choices limited | Simple CPU rerank for app | `$0 license` | CPU | XS/S | Apache 2.0 | Yes local | Good budget quality |
| 12 | Pinecone hosted rerank | Pinecone hosted rerank — вариант для rerank stage.<br>Зачем нужен: пересортировывать top-K найденных chunks по реальной полезности для конкретного запроса.<br>Бизнес-смысл: в prompt попадает меньше похожих, но неверных фрагментов, поэтому ответы становятся точнее без замены основной LLM.<br>Что проверить: Vendor lock-in/SaaS. | Managed rerank inside vector platform | Vendor lock-in/SaaS | Integrated with Pinecone retrieval | Included quotas + usage | Managed | S | Commercial SaaS | Region-dependent | Simple if already Pinecone |

**Рекомендации**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
| ------ | --------- | --------------------- | ----------------- |
| Budget | FlashRank or MiniLM | `$0-3k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нет GPU и нужен быстрый CPU precision boost поверх текущего retrieval<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нужны HA, multi-tenant, replay, SLA 99.9% или нагрузка >100 запросов/мин |
| Optimal | bge-reranker-base/large | `$5k-30k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нужен local RU-resident rerank top-20/top-50 для production pilot<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нет владельца эксплуатации, нет stage-gate на migration или объём пока похож на offline demo |
| Enterprise | Cohere/Jina/Voyage or ColBERT | `$15k-100k+` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если approved SaaS или отдельная retrieval infra позволяют максимизировать precision<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• ещё не подтверждены SLA, бюджет, security approval и выделенная Infra/SRE-команда |

**Пути миграции**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| No reranker -> local reranker | Add optional rerank stage after top-K retrieval, feature flag | Low | Low |
| Local -> API | Route only de-identified snippets, cache scores by query/chunk hash | Low | Compliance medium-high |
| Cross-encoder -> ColBERT | Requires new indexing pipeline and storage, A/B side-by-side | Medium-high | High |
| API -> local | Keep scoring contract `{chunk_id, score}`, replace provider | Low | Medium |

<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**

**Что это значит для проекта:** этот компонент закрывает задачу: пересортировывать top-K найденных chunks по реальной полезности для конкретного запроса. В контексте Clarify Engine это влияет не на "красоту архитектуры", а на скорость, проверяемость и стоимость анализа требований.

**Почему важно для БА:** Для БА reranker уменьшает число спорных ответов: система не просто нашла похожие chunks, а проверила их соответствие запросу.

**Технически:**
- Rerank stage должен быть optional feature flag после retrieval и до prompt assembly.
- Scoring contract лучше держать простым: `{chunk_id, score, provider, model_version}`.
- API-rerank требует de-identification snippets и score cache by query/chunk hash.

**Когда выбирать:**
- 🟢 **Budget:** для пилота Clarify Engine на 1-3 БА с нагрузкой ≤15 запросов/мин, если нет GPU и нужен быстрый CPU precision boost поверх текущего retrieval.
- 🟡 **Optimal:** для production pilot на 1-3 БА с нагрузкой ≤15 запросов/мин и ростом до нескольких сервисов, если нужен local RU-resident rerank top-20/top-50 для production pilot.
- 🔵 **Enterprise:** после подтверждения SLA, бюджета, security approval и нагрузки >100 запросов/мин, если approved SaaS или отдельная retrieval infra позволяют максимизировать precision.

📚 **Читать далее:**
- [BAAI/bge-reranker-large model card](https://huggingface.co/BAAI/bge-reranker-large) — local multilingual reranker, EN.
- [Cohere Rerank documentation](https://docs.cohere.com/docs/rerank-2) — managed reranking API, EN.
- [FlashRank GitHub repository](https://github.com/PrithivirajDamodaran/FlashRank) — CPU reranking library, EN.

---
## 11. Компонент 8 - Observability Stack

**Ответственность:** logs, metrics, traces, alerting, dashboards и incident/debug workflow.

| № | Решение | Пояснение для БА | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Signals / Storage / Query / Alerting / Dashboards / Self-host / Cost / Community |
| ---: | --------- | --- | ------------ | ------- | -------------- | ----------- | --------- | -------------- | ---------- | ------------------ | -------------------------------------------------------------------------------- |
| 1 | Prometheus + Grafana + Loki + Jaeger | Prometheus + Grafana + Loki + Jaeger — вариант для observability stack.<br>Зачем нужен: собирать logs, metrics и traces для поиска причин плохих ответов, timeouts и ошибок pipeline.<br>Бизнес-смысл: команда видит, где сломался запрос: parser, retrieval, provider, cache, gateway или prompt.<br>Что проверить: Multi-tool ops, retention tuning. | OSS metrics/logs/traces | Multi-tool ops, retention tuning | Standard stack, self-hosted, broad community | `$0 license`; infra only | 2-8 vCPU, 8-32 GB RAM + storage | M | Apache 2.0 / AGPL for Grafana | Yes | All signals with components, PromQL/LogQL |
| 2 | ELK Stack | ELK Stack — вариант для observability stack.<br>Зачем нужен: собирать logs, metrics и traces для поиска причин плохих ответов, timeouts и ошибок pipeline.<br>Бизнес-смысл: команда видит, где сломался запрос: parser, retrieval, provider, cache, gateway или prompt.<br>Что проверить: Elastic license, resource-heavy. | Logs/search/dashboards | Elastic license, resource-heavy | Strong logs/search, mature | Self-managed basic + infra; Elastic Cloud usage | JVM/storage heavy | M/H | Elastic License/SSPL/AGPL options | Yes self-host | Logs strong, metrics/traces via integrations |
| 3 | OpenTelemetry + Tempo + Grafana | OpenTelemetry + Tempo + Grafana — вариант для observability stack.<br>Зачем нужен: собирать logs, metrics и traces для поиска причин плохих ответов, timeouts и ошибок pipeline.<br>Бизнес-смысл: команда видит, где сломался запрос: parser, retrieval, provider, cache, gateway или prompt.<br>Что проверить: Requires instrumentation discipline. | Standard traces/metrics/logs pipeline | Requires instrumentation discipline | Vendor-neutral, future-proof | `$0 license`; infra | Collector + backend storage | M | Apache 2.0 / AGPL | Yes | All signals via OTel, good traces |
| 4 | Datadog | Datadog — вариант для observability stack.<br>Зачем нужен: собирать logs, metrics и traces для поиска причин плохих ответов, timeouts и ошибок pipeline.<br>Бизнес-смысл: команда видит, где сломался запрос: parser, retrieval, provider, cache, gateway или prompt.<br>Что проверить: Cost growth, SaaS residency. | Full SaaS observability | Cost growth, SaaS residency | Fast setup, great UX, broad integrations | Per host/container/log/APM usage | Managed agents | S | Commercial SaaS | Region/contract-dependent | All signals, strong alerting |
| 5 | New Relic | New Relic — вариант для observability stack.<br>Зачем нужен: собирать logs, metrics и traces для поиска причин плохих ответов, timeouts и ошибок pipeline.<br>Бизнес-смысл: команда видит, где сломался запрос: parser, retrieval, provider, cache, gateway или prompt.<br>Что проверить: Ingest/user pricing, SaaS. | SaaS observability | Ingest/user pricing, SaaS | Unified data platform, good APM | Usage/user based, free tier | Managed agents | S | Commercial SaaS | Region/contract-dependent | All signals |
| 6 | Dynatrace | Dynatrace — вариант для observability stack.<br>Зачем нужен: собирать logs, metrics и traces для поиска причин плохих ответов, timeouts и ошибок pipeline.<br>Бизнес-смысл: команда видит, где сломался запрос: parser, retrieval, provider, cache, gateway или prompt.<br>Что проверить: Expensive/quote, lock-in. | Enterprise observability | Expensive/quote, lock-in | Strong AIOps, enterprise support | DPS/quote | Managed/agents | M | Commercial SaaS/self-host options | Contract-dependent | All signals, strong automation |
| 7 | Honeycomb | Honeycomb — вариант для observability stack.<br>Зачем нужен: собирать logs, metrics и traces для поиска причин плохих ответов, timeouts и ошибок pipeline.<br>Бизнес-смысл: команда видит, где сломался запрос: parser, retrieval, provider, cache, gateway или prompt.<br>Что проверить: SaaS, less log-storage focus. | Event/tracing observability | SaaS, less log-storage focus | Excellent high-cardinality traces | Events/usage plans | Managed | S/M | Commercial SaaS | Region-dependent | Traces/events strong |
| 8 | SigNoz | SigNoz — вариант для observability stack.<br>Зачем нужен: собирать logs, metrics и traces для поиска причин плохих ответов, timeouts и ошибок pipeline.<br>Бизнес-смысл: команда видит, где сломался запрос: parser, retrieval, provider, cache, gateway или prompt.<br>Что проверить: ClickHouse ops, younger than Grafana. | OSS observability on ClickHouse | ClickHouse ops, younger than Grafana | Single OSS observability platform | OSS `$0`; cloud paid | ClickHouse + services | M | MIT/Apache mix | Yes self-host | Logs/metrics/traces |
| 9 | Grafana Cloud | Grafana Cloud — вариант для observability stack.<br>Зачем нужен: собирать logs, metrics и traces для поиска причин плохих ответов, timeouts и ошибок pipeline.<br>Бизнес-смысл: команда видит, где сломался запрос: parser, retrieval, provider, cache, gateway или prompt.<br>Что проверить: SaaS residency/cost. | Managed Grafana stack | SaaS residency/cost | Familiar Grafana without ops | Free/usage tiers | Managed agents | S | Commercial SaaS | Region-dependent | Metrics/logs/traces/profiles |
| 10 | ClickHouse + Grafana | ClickHouse + Grafana — вариант для observability stack.<br>Зачем нужен: собирать logs, metrics и traces для поиска причин плохих ответов, timeouts и ошибок pipeline.<br>Бизнес-смысл: команда видит, где сломался запрос: parser, retrieval, provider, cache, gateway или prompt.<br>Что проверить: Build/maintain own schemas. | Custom logs/metrics analytics | Build/maintain own schemas | Very cost-effective high-volume logs | OSS `$0`; ClickHouse Cloud credits/usage | CPU/storage for ClickHouse | M/H | Apache 2.0 | Yes self-host | Logs/events analytics strong |
| 11 | VictoriaMetrics | VictoriaMetrics — вариант для observability stack.<br>Зачем нужен: собирать logs, metrics и traces для поиска причин плохих ответов, timeouts и ошибок pipeline.<br>Бизнес-смысл: команда видит, где сломался запрос: parser, retrieval, provider, cache, gateway или prompt.<br>Что проверить: Logs/traces need other tools. | Metrics TSDB | Logs/traces need other tools | Simple, efficient Prometheus-compatible metrics | OSS `$0`; enterprise/cloud paid | Low-medium | S/M | Apache 2.0 / enterprise | Yes | Metrics strong |
| 12 | Sentry | Sentry — вариант для observability stack.<br>Зачем нужен: собирать logs, metrics и traces для поиска причин плохих ответов, timeouts и ошибок pipeline.<br>Бизнес-смысл: команда видит, где сломался запрос: parser, retrieval, provider, cache, gateway или prompt.<br>Что проверить: Not full infra observability. | Error tracking/performance | Not full infra observability | Best app exception workflow | Free/paid per event/user | Managed or self-host | S | Business Source License / commercial | Self-host possible | Errors/performance, not logs TSDB |

**Рекомендации**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
| ------ | --------- | --------------------- | ----------------- |
| Budget | Prometheus + Grafana + Loki | `$2k-12k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нужен self-host pilot с базовыми dashboards и без платного SaaS<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нужны HA, multi-tenant, replay, SLA 99.9% или нагрузка >100 запросов/мин |
| Optimal | OpenTelemetry + Grafana/Tempo/Loki + Sentry | `$5k-30k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если микросервисы требуют portable traces, Sentry errors и Grafana dashboards<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нет владельца эксплуатации, нет stage-gate на migration или объём пока похож на offline demo |
| Enterprise | Datadog/New Relic/Dynatrace/Honeycomb | `$30k-200k+` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нужен 24/7 operations, advanced alerting и low-ops managed platform<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• ещё не подтверждены SLA, бюджет, security approval и выделенная Infra/SRE-команда |

**Пути миграции**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| Logs only -> OTel | Add trace IDs and OpenTelemetry SDK/exporter | Low | Medium |
| Grafana OSS -> Grafana Cloud | Point remote_write/log export to cloud, keep dashboards as code | Low | Low-medium |
| SaaS -> self-host | Export dashboards/alerts where possible, keep OTel as neutral pipeline | Medium | Medium |
| ELK -> Loki/ClickHouse | Re-emit logs through collector, preserve `run_id`/`trace_id` fields | Medium | Medium |

<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**

**Что это значит для проекта:** этот компонент закрывает задачу: собирать logs, metrics и traces для поиска причин плохих ответов, timeouts и ошибок pipeline. В контексте Clarify Engine это влияет не на "красоту архитектуры", а на скорость, проверяемость и стоимость анализа требований.

**Почему важно для БА:** Для БА observability сокращает время разбора инцидента: плохой ответ перестаёт быть 'магией LLM' и раскладывается на конкретные сигналы.

**Технически:**
- `OpenTelemetry` должен быть нейтральным сборщиком traces/metrics/logs до выбора backend.
- `run_id` и `trace_id` должны проходить через UI, bus, retrieval, generation и audit.
- Retention и sampling нужно задать сразу, иначе logs быстро становятся дорогими.

**Когда выбирать:**
- 🟢 **Budget:** для пилота Clarify Engine на 1-3 БА с нагрузкой ≤15 запросов/мин, если нужен self-host pilot с базовыми dashboards и без платного SaaS.
- 🟡 **Optimal:** для production pilot на 1-3 БА с нагрузкой ≤15 запросов/мин и ростом до нескольких сервисов, если микросервисы требуют portable traces, Sentry errors и Grafana dashboards.
- 🔵 **Enterprise:** после подтверждения SLA, бюджета, security approval и нагрузки >100 запросов/мин, если нужен 24/7 operations, advanced alerting и low-ops managed platform.

📚 **Читать далее:**
- [OpenTelemetry documentation](https://opentelemetry.io/docs/) — vendor-neutral signals, EN.
- [Grafana Loki documentation](https://grafana.com/docs/loki/latest/) — log aggregation, EN.
- [Sentry documentation](https://docs.sentry.io/) — error tracking, EN.

---
## 12. Компонент 9 - Audit Database

**Ответственность:** immutable audit events: кто что вызвал, когда, через какую model/provider, prompt/version, retrieval evidence и PII mask hash.

| № | Решение | Пояснение для БА | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Write / Query / Compression / Retention / WORM / SQL / Scale / Cost / Compliance |
| ---: | --------- | --- | ------------ | ------- | -------------- | ----------- | --------- | -------------- | ---------- | ------------------ | -------------------------------------------------------------------------------- |
| 1 | PostgreSQL | PostgreSQL — вариант для audit database.<br>Зачем нужен: хранить immutable evidence: кто запустил анализ, какая model ответила, какие chunks и masks использовались.<br>Бизнес-смысл: спорный результат можно повторить, объяснить и проверить на compliance.<br>Что проверить: Large log analytics can bloat, retention tuning. | Transactional audit + metadata | Large log analytics can bloat, retention tuning | Already familiar, ACID, simple WORM via roles/triggers | `$0 license`; managed/self-host cost | 2-8 vCPU, 8-32 GB RAM | S/M | PostgreSQL | Yes | Medium write, strong SQL, WORM by design |
| 2 | ClickHouse | ClickHouse — вариант для audit database.<br>Зачем нужен: хранить immutable evidence: кто запустил анализ, какая model ответила, какие chunks и masks использовались.<br>Бизнес-смысл: спорный результат можно повторить, объяснить и проверить на compliance.<br>Что проверить: Needs schema discipline, less OLTP. | Append-only analytics/logs | Needs schema discipline, less OLTP | Very fast analytics, compression, cheap storage | OSS `$0`; Cloud $300 credits/usage | 4-16 vCPU, SSD/object storage | M | Apache 2.0 | Yes | High write, fast analytics, TTL |
| 3 | TimescaleDB | TimescaleDB — вариант для audit database.<br>Зачем нужен: хранить immutable evidence: кто запустил анализ, какая model ответила, какие chunks и masks использовались.<br>Бизнес-смысл: спорный результат можно повторить, объяснить и проверить на compliance.<br>Что проверить: License/compression features review. | Time-series on Postgres | License/compression features review | Hypertables, retention, SQL | OSS/community + cloud paid | Postgres-like | M | Timescale license / Apache components | Yes self-host | Medium-high write, SQL |
| 4 | InfluxDB | InfluxDB — вариант для audit database.<br>Зачем нужен: хранить immutable evidence: кто запустил анализ, какая model ответила, какие chunks и masks использовались.<br>Бизнес-смысл: спорный результат можно повторить, объяснить и проверить на compliance.<br>Что проверить: Less natural relational audit joins. | Time-series metrics/events | Less natural relational audit joins | Fast time-series ingestion, retention | Cloud usage examples: data in `$0.0025/MB`, query `$0.012/100`, storage `$0.002/GB-hour`, out `$0.09/GB`; OSS options | 2-8 vCPU | M | MIT/Commercial depending version | Yes self-host | High write, retention |
| 5 | Elasticsearch | Elasticsearch — вариант для audit database.<br>Зачем нужен: хранить immutable evidence: кто запустил анализ, какая model ответила, какие chunks и masks использовались.<br>Бизнес-смысл: спорный результат можно повторить, объяснить и проверить на compliance.<br>Что проверить: Cost/resource heavy, license. | Audit log search | Cost/resource heavy, license | Powerful text search and Kibana | Self-managed/cloud pricing | JVM/storage | M/H | Elastic licenses | Yes self-host | High write, search strong |
| 6 | MongoDB | MongoDB — вариант для audit database.<br>Зачем нужен: хранить immutable evidence: кто запустил анализ, какая model ответила, какие chunks и masks использовались.<br>Бизнес-смысл: спорный результат можно повторить, объяснить и проверить на compliance.<br>Что проверить: Analytics less efficient than columnar. | Document audit events | Analytics less efficient than columnar | Flexible schema, easy JSON events | Community `$0`; Atlas paid | 2-8 vCPU | S/M | SSPL/community/commercial | Yes self-host if license approved | Medium write, flexible |
| 7 | Apache Doris | Apache Doris — вариант для audit database.<br>Зачем нужен: хранить immutable evidence: кто запустил анализ, какая model ответила, какие chunks и masks использовались.<br>Бизнес-смысл: спорный результат можно повторить, объяснить и проверить на compliance.<br>Что проверить: Less common locally, ops. | OLAP analytics | Less common locally, ops | MPP SQL analytics | OSS `$0`; cloud paid | Cluster, 3+ nodes | H | Apache 2.0 | Yes | High write/query |
| 8 | DuckDB | DuckDB — вариант для audit database.<br>Зачем нужен: хранить immutable evidence: кто запустил анализ, какая model ответила, какие chunks и masks использовались.<br>Бизнес-смысл: спорный результат можно повторить, объяснить и проверить на compliance.<br>Что проверить: Not concurrent production DB. | Embedded analytics | Not concurrent production DB | Cheap local reports over parquet | `$0 license` | Local CPU | XS/S | MIT | Yes | Small-scale analytics |
| 9 | Amazon Athena | Amazon Athena — вариант для audit database.<br>Зачем нужен: хранить immutable evidence: кто запустил анализ, какая model ответила, какие chunks и masks использовались.<br>Бизнес-смысл: спорный результат можно повторить, объяснить и проверить на compliance.<br>Что проверить: AWS lock-in, data lake governance. | Serverless SQL over S3 | AWS lock-in, data lake governance | No servers, cheap occasional queries | Per TB scanned | Managed + S3 | S | Commercial SaaS | Region-dependent | Good analytics, no OLTP |
| 10 | Google BigQuery | Google BigQuery — вариант для audit database.<br>Зачем нужен: хранить immutable evidence: кто запустил анализ, какая model ответила, какие chunks и masks использовались.<br>Бизнес-смысл: спорный результат можно повторить, объяснить и проверить на compliance.<br>Что проверить: GCP lock-in, cost if bad queries. | Serverless data warehouse | GCP lock-in, cost if bad queries | Mature analytics, IAM, scale | On-demand `$6.25/TiB` scanned after free tier; storage extra | Managed | S/M | Commercial SaaS | Region-dependent | Very high scale |
| 11 | Snowflake | Snowflake — вариант для audit database.<br>Зачем нужен: хранить immutable evidence: кто запустил анализ, какая model ответила, какие chunks и masks использовались.<br>Бизнес-смысл: спорный результат можно повторить, объяснить и проверить на compliance.<br>Что проверить: Quote/credit complexity, SaaS. | Data warehouse | Quote/credit complexity, SaaS | Enterprise governance, sharing | Credit/storage usage, quote | Managed | M | Commercial SaaS | Region-dependent | High scale/compliance |
| 12 | Azure Synapse | Azure Synapse — вариант для audit database.<br>Зачем нужен: хранить immutable evidence: кто запустил анализ, какая model ответила, какие chunks и masks использовались.<br>Бизнес-смысл: спорный результат можно повторить, объяснить и проверить на compliance.<br>Что проверить: Azure lock-in, complexity. | Azure analytics | Azure lock-in, complexity | Enterprise data platform | DWU/serverless usage | Managed | M/H | Commercial SaaS | Region-dependent | High scale |

**Рекомендации**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
| ------ | --------- | --------------------- | ----------------- |
| Budget | PostgreSQL append-only | `$1k-8k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нужен pilot audit с простыми SQL-отчётами и append-only политикой<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нужны HA, multi-tenant, replay, SLA 99.9% или нагрузка >100 запросов/мин |
| Optimal | PostgreSQL metadata + ClickHouse events | `$5k-25k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если событий много и нужны быстрые аналитические запросы без потери PostgreSQL metadata<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нет владельца эксплуатации, нет stage-gate на migration или объём пока похож на offline demo |
| Enterprise | ClickHouse Cloud/BigQuery/Snowflake | `$30k-200k+` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если audit становится частью BI/compliance reporting и approved managed warehouse<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• ещё не подтверждены SLA, бюджет, security approval и выделенная Infra/SRE-команда |

**Пути миграции**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| PostgreSQL -> ClickHouse | CDC or batch copy audit rows, keep Postgres as source of truth first | Low | Medium |
| ClickHouse -> BigQuery/Snowflake | Export parquet to object storage, load partitions by date | Low-medium | Medium |
| Elasticsearch logs -> ClickHouse | Reindex `_source` to columnar schema, preserve IDs | Medium | Medium |
| Any -> WORM archive | Periodic parquet/JSONL signed export to object storage with retention lock | Low | Low |

<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**

**Что это значит для проекта:** этот компонент закрывает задачу: хранить immutable evidence: кто запустил анализ, какая model ответила, какие chunks и masks использовались. В контексте Clarify Engine это влияет не на "красоту архитектуры", а на скорость, проверяемость и стоимость анализа требований.

**Почему важно для БА:** Для БА audit trail превращает AI-ответ в проверяемый процесс: можно увидеть источники, параметры и причины fallback.

**Технически:**
- Audit rows должны быть append-only; UPDATE/DELETE закрываются ролями, triggers или WORM archive.
- PostgreSQL удобен для metadata, ClickHouse - для большого потока events и дешёвых аналитических запросов.
- Raw prompt/context хранить опасно; нужны masks, hashes и retention policy.

**Когда выбирать:**
- 🟢 **Budget:** для пилота Clarify Engine на 1-3 БА с нагрузкой ≤15 запросов/мин, если нужен pilot audit с простыми SQL-отчётами и append-only политикой.
- 🟡 **Optimal:** для production pilot на 1-3 БА с нагрузкой ≤15 запросов/мин и ростом до нескольких сервисов, если событий много и нужны быстрые аналитические запросы без потери PostgreSQL metadata.
- 🔵 **Enterprise:** после подтверждения SLA, бюджета, security approval и нагрузки >100 запросов/мин, если audit становится частью BI/compliance reporting и approved managed warehouse.

📚 **Читать далее:**
- [PostgreSQL trigger documentation](https://www.postgresql.org/docs/current/sql-createtrigger.html) — append-only rules, EN.
- [ClickHouse introduction](https://clickhouse.com/docs/en/intro) — columnar analytics, EN.
- [Amazon S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html) — WORM archive concept, EN.

---
## 13. Компонент 10 - Object Storage

**Ответственность:** raw uploaded files, parser artifacts, extracted JSON, reports, snapshots и audit archives.

| № | Решение | Пояснение для БА | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | S3 API / Cost / Transfer / Durability / Versioning / Lifecycle / Encryption / Managed |
| ---: | --------- | --- | ------------ | ------- | -------------- | ----------- | --------- | -------------- | ---------- | ------------------ | ------------------------------------------------------------------------------------ |
| 1 | MinIO | MinIO — вариант для object storage.<br>Зачем нужен: сохранять raw uploads, parser artifacts, extracted JSON, reports, snapshots и audit archives.<br>Бизнес-смысл: анализ можно воспроизвести: исходный файл и промежуточные артефакты не теряются и не перезаписываются без следа.<br>Что проверить: Ops/backups/erasure coding, AGPL/commercial implications. | Self-hosted S3-compatible storage | Ops/backups/erasure coding, AGPL/commercial implications | Local S3 API, simple, high performance | OSS/commercial; infra only | 4+ disks for HA, 4-16 vCPU | M | AGPL v3 / commercial | Yes | Strong S3, versioning/lifecycle/encryption |
| 2 | Amazon S3 | Amazon S3 — вариант для object storage.<br>Зачем нужен: сохранять raw uploads, parser artifacts, extracted JSON, reports, snapshots и audit archives.<br>Бизнес-смысл: анализ можно воспроизвести: исходный файл и промежуточные артефакты не теряются и не перезаписываются без следа.<br>Что проверить: External cloud, egress, residency. | Managed object storage | External cloud, egress, residency | Mature, durable, lifecycle, object lock | Standard storage example around `$0.023/GB-month` in us-east-1 + requests/egress | Managed | XS/S | Commercial SaaS | Region-dependent | Strongest managed S3 |
| 3 | Yandex Object Storage | Yandex Object Storage — вариант для object storage.<br>Зачем нужен: сохранять raw uploads, parser artifacts, extracted JSON, reports, snapshots и audit archives.<br>Бизнес-смысл: анализ можно воспроизвести: исходный файл и промежуточные артефакты не теряются и не перезаписываются без следа.<br>Что проверить: Provider lock-in, tariff changes. | RU cloud S3-compatible | Provider lock-in, tariff changes | RU residency path, S3 API | RUB tariff by storage/requests/traffic | Managed | S | Commercial SaaS | Yes RU cloud | S3-compatible, lifecycle/encryption |
| 4 | Selectel Cloud Storage | Selectel Cloud Storage — вариант для object storage.<br>Зачем нужен: сохранять raw uploads, parser artifacts, extracted JSON, reports, snapshots и audit archives.<br>Бизнес-смысл: анализ можно воспроизвести: исходный файл и промежуточные артефакты не теряются и не перезаписываются без следа.<br>Что проверить: Contract/tariff dependency. | RU provider object storage | Contract/tariff dependency | RU residency, S3 API | Provider tariff | Managed | S | Commercial SaaS | Yes RU | S3-compatible |
| 5 | Ceph | Ceph — вариант для object storage.<br>Зачем нужен: сохранять raw uploads, parser artifacts, extracted JSON, reports, snapshots и audit archives.<br>Бизнес-смысл: анализ можно воспроизвести: исходный файл и промежуточные артефакты не теряются и не перезаписываются без следа.<br>Что проверить: High ops complexity. | Self-hosted distributed storage | High ops complexity | Enterprise self-host, S3/RBD/CephFS | `$0 license`; hardware/ops | 3+ storage nodes, disks/network | H | LGPL/GPL mix | Yes | S3 via RGW, high durability if operated well |
| 6 | Azure Blob Storage | Azure Blob Storage — вариант для object storage.<br>Зачем нужен: сохранять raw uploads, parser artifacts, extracted JSON, reports, snapshots и audit archives.<br>Бизнес-смысл: анализ можно воспроизвести: исходный файл и промежуточные артефакты не теряются и не перезаписываются без следа.<br>Что проверить: Azure lock-in, region approval. | Managed object/blob storage | Azure lock-in, region approval | Tiers, lifecycle, immutability | Hot/cool/archive GB-month + operations/egress | Managed | S | Commercial SaaS | Region-dependent | Strong lifecycle/encryption |
| 7 | Google Cloud Storage | Google Cloud Storage — вариант для object storage.<br>Зачем нужен: сохранять raw uploads, parser artifacts, extracted JSON, reports, snapshots и audit archives.<br>Бизнес-смысл: анализ можно воспроизвести: исходный файл и промежуточные артефакты не теряются и не перезаписываются без следа.<br>Что проверить: GCP lock-in, egress. | Managed object storage | GCP lock-in, egress | Tiers, IAM, lifecycle | Standard regional examples around `$0.020-0.026/GB-month` by region | Managed | S | Commercial SaaS | Region-dependent | Strong lifecycle/encryption |
| 8 | OpenStack Swift | OpenStack Swift — вариант для object storage.<br>Зачем нужен: сохранять raw uploads, parser artifacts, extracted JSON, reports, snapshots и audit archives.<br>Бизнес-смысл: анализ можно воспроизвести: исходный файл и промежуточные артефакты не теряются и не перезаписываются без следа.<br>Что проверить: Ops complexity, smaller modern ecosystem. | Self-hosted object storage | Ops complexity, smaller modern ecosystem | Open-source object storage for private cloud | `$0 license`; infra | 3+ nodes | H | Apache 2.0 | Yes | S3-compatible via gateways, native Swift |
| 9 | SeaweedFS | SeaweedFS — вариант для object storage.<br>Зачем нужен: сохранять raw uploads, parser artifacts, extracted JSON, reports, snapshots и audit archives.<br>Бизнес-смысл: анализ можно воспроизвести: исходный файл и промежуточные артефакты не теряются и не перезаписываются без следа.<br>Что проверить: Smaller enterprise support. | Simple distributed file/object store | Smaller enterprise support | Lightweight, S3 API, fast | `$0 license` | 3+ nodes for HA | M | Apache 2.0 | Yes | S3-compatible, simple ops |
| 10 | GarageFS | GarageFS — вариант для object storage.<br>Зачем нужен: сохранять raw uploads, parser artifacts, extracted JSON, reports, snapshots и audit archives.<br>Бизнес-смысл: анализ можно воспроизвести: исходный файл и промежуточные артефакты не теряются и не перезаписываются без следа.<br>Что проверить: Younger ecosystem. | Lightweight geo-distributed object store | Younger ecosystem | Simple self-hosted S3-compatible storage | `$0 license` | Small nodes possible | M | AGPL v3 | Yes | S3-compatible, versioning limited |
| 11 | Local filesystem | Local filesystem — вариант для object storage.<br>Зачем нужен: сохранять raw uploads, parser artifacts, extracted JSON, reports, snapshots и audit archives.<br>Бизнес-смысл: анализ можно воспроизвести: исходный файл и промежуточные артефакты не теряются и не перезаписываются без следа.<br>Что проверить: No HA, backup risk, path coupling. | Single-node files | No HA, backup risk, path coupling | Cheapest and simplest for offline pilot | Existing disk | Single server | XS | N/A | Yes | No S3 unless wrapped |
| 12 | NFS/SMB share | NFS/SMB share — вариант для object storage.<br>Зачем нужен: сохранять raw uploads, parser artifacts, extracted JSON, reports, snapshots и audit archives.<br>Бизнес-смысл: анализ можно воспроизвести: исходный файл и промежуточные артефакты не теряются и не перезаписываются без следа.<br>Что проверить: Locking/perf/HA issues. | Shared filesystem | Locking/perf/HA issues | Reuses enterprise NAS | Existing NAS/license | NAS/server | S/M | N/A | Yes if on-prem | No object semantics |

**Рекомендации**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
| ------ | --------- | --------------------- | ----------------- |
| Budget | Local FS or MinIO single node | `$0-5k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если offline demo допускает single-node storage и ручной backup<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нужны HA, multi-tenant, replay, SLA 99.9% или нагрузка >100 запросов/мин |
| Optimal | MinIO HA or RU S3-compatible provider | `$5k-30k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нужен production pilot с RU residency, S3 API, lifecycle и нормальным backup<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нет владельца эксплуатации, нет stage-gate на migration или объём пока похож на offline demo |
| Enterprise | S3/Azure/GCS/Ceph | `$20k-150k+` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нужны object lock, disaster recovery, lifecycle tiers и enterprise backup<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• ещё не подтверждены SLA, бюджет, security approval и выделенная Infra/SRE-команда |

**Пути миграции**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| Local FS -> S3/MinIO | Introduce object store interface, upload files by content hash, keep path alias | Low | Low-medium |
| MinIO -> S3/Yandex/Selectel | `mc mirror`/S3 sync, preserve bucket/key layout | Low | Low |
| Cloud S3 -> self-host | S3 batch export/sync, verify object hashes and metadata | Medium | Medium |
| NFS -> object storage | Convert path references to object keys, update report links | Medium | Medium |

<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**

**Что это значит для проекта:** этот компонент закрывает задачу: сохранять raw uploads, parser artifacts, extracted JSON, reports, snapshots и audit archives. В контексте Clarify Engine это влияет не на "красоту архитектуры", а на скорость, проверяемость и стоимость анализа требований.

**Почему важно для БА:** Для БА object storage отвечает за доказуемость: если raw document или extracted JSON потеряны, проверить ответ уже невозможно.

**Технически:**
- `ObjectStore` interface должен работать с local FS, MinIO и S3-compatible providers одинаково.
- Ключи лучше строить по content hash/document_id, чтобы избежать перезаписи и дубликатов.
- Audit archives требуют immutability/versioning, а не просто общей папки.

**Когда выбирать:**
- 🟢 **Budget:** для пилота Clarify Engine на 1-3 БА с нагрузкой ≤15 запросов/мин, если offline demo допускает single-node storage и ручной backup.
- 🟡 **Optimal:** для production pilot на 1-3 БА с нагрузкой ≤15 запросов/мин и ростом до нескольких сервисов, если нужен production pilot с RU residency, S3 API, lifecycle и нормальным backup.
- 🔵 **Enterprise:** после подтверждения SLA, бюджета, security approval и нагрузки >100 запросов/мин, если нужны object lock, disaster recovery, lifecycle tiers и enterprise backup.

📚 **Читать далее:**
- [MinIO object storage documentation](https://min.io/docs/minio/linux/index.html) — self-hosted S3-compatible storage, EN.
- [Amazon S3 User Guide](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html) — managed object storage, EN.
- [Yandex Object Storage documentation](https://yandex.cloud/ru/docs/storage/) — RU cloud S3-compatible option, RU.

---
## 14. Компонент 11 - Cache Layer

**Ответственность:** LLM response cache, retrieval result cache, sessions, rate limits, locks и ephemeral state.

| № | Решение | Пояснение для БА | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | Throughput / p99 / Persistence / Eviction / Cluster / Memory / PubSub / Redis API |
| ---: | --------- | --- | ------------ | ------- | -------------- | ----------- | --------- | -------------- | ---------- | ------------------ | ---------------------------------------------------------------------------- |
| 1 | Redis | Redis — вариант для cache layer.<br>Зачем нужен: хранить повторяемые LLM responses, retrieval results, sessions, locks и rate-limit counters.<br>Бизнес-смысл: повторные сценарии БА становятся быстрее и дешевле, а provider limits не приводят к лавине ошибок.<br>Что проверить: License changes, memory cost. | General cache, sessions, queues | License changes, memory cost | Standard ecosystem, TTL, pub/sub, streams | Source available/OSS variants; Redis Cloud paid | RAM sized to hotset | S/M | BSD for older, RSAL/SSPL for newer Redis Ltd; Valkey Apache 2.0 alternative | Yes if self-host/license approved | Very high throughput, low p99 |
| 2 | Memcached | Memcached — вариант для cache layer.<br>Зачем нужен: хранить повторяемые LLM responses, retrieval results, sessions, locks и rate-limit counters.<br>Бизнес-смысл: повторные сценарии БА становятся быстрее и дешевле, а provider limits не приводят к лавине ошибок.<br>Что проверить: No persistence/structures. | Simple cache | No persistence/structures | Extremely simple, fast | `$0 license` | RAM | XS/S | BSD | Yes | High throughput, no persistence |
| 3 | Dragonfly | Dragonfly — вариант для cache layer.<br>Зачем нужен: хранить повторяемые LLM responses, retrieval results, sessions, locks и rate-limit counters.<br>Бизнес-смысл: повторные сценарии БА становятся быстрее и дешевле, а provider limits не приводят к лавине ошибок.<br>Что проверить: Younger than Redis. | Redis-compatible high-performance cache | Younger than Redis | Efficient multi-threaded, Redis API | OSS `$0`; cloud paid/quote | RAM, fewer nodes | S/M | BSL/Apache terms by version, review | Yes self-host if license ok | Very high throughput |
| 4 | KeyDB | KeyDB — вариант для cache layer.<br>Зачем нужен: хранить повторяемые LLM responses, retrieval results, sessions, locks и rate-limit counters.<br>Бизнес-смысл: повторные сценарии БА становятся быстрее и дешевле, а provider limits не приводят к лавине ошибок.<br>Что проверить: Ecosystem uncertainty. | Redis fork | Ecosystem uncertainty | Multi-threaded Redis-compatible | `$0 license` | RAM | S/M | BSD | Yes | High throughput |
| 5 | Redis Cluster | Redis Cluster — вариант для cache layer.<br>Зачем нужен: хранить повторяемые LLM responses, retrieval results, sessions, locks и rate-limit counters.<br>Бизнес-смысл: повторные сценарии БА становятся быстрее и дешевле, а provider limits не приводят к лавине ошибок.<br>Что проверить: Cluster ops, client behavior. | Sharded Redis | Cluster ops, client behavior | Scale hotset, HA | infra/license | Multiple RAM nodes | M | Redis licensing as above | Yes | High throughput/HA |
| 6 | Hazelcast | Hazelcast — вариант для cache layer.<br>Зачем нужен: хранить повторяемые LLM responses, retrieval results, sessions, locks и rate-limit counters.<br>Бизнес-смысл: повторные сценарии БА становятся быстрее и дешевле, а provider limits не приводят к лавине ошибок.<br>Что проверить: Java/cluster ops, overkill for simple cache. | Distributed in-memory data grid | Java/cluster ops, overkill for simple cache | Enterprise clustering, compute near data | OSS + enterprise quote | RAM cluster | M/H | Apache 2.0 core / commercial | Yes | High throughput, rich cluster |
| 7 | Apache Ignite | Apache Ignite — вариант для cache layer.<br>Зачем нужен: хранить повторяемые LLM responses, retrieval results, sessions, locks и rate-limit counters.<br>Бизнес-смысл: повторные сценарии БА становятся быстрее и дешевле, а provider limits не приводят к лавине ошибок.<br>Что проверить: Complexity, heavier ops. | In-memory compute/data grid | Complexity, heavier ops | SQL, compute grid, persistence | `$0 license` | RAM/SSD cluster | H | Apache 2.0 | Yes | High throughput, complex |
| 8 | Aerospike | Aerospike — вариант для cache layer.<br>Зачем нужен: хранить повторяемые LLM responses, retrieval results, sessions, locks и rate-limit counters.<br>Бизнес-смысл: повторные сценарии БА становятся быстрее и дешевле, а provider limits не приводят к лавине ошибок.<br>Что проверить: Commercial for enterprise features. | Low-latency KV | Commercial for enterprise features | Very high scale, SSD/RAM hybrid | Community/enterprise quote | RAM+SSD nodes | H | AGPL/commercial | Yes if license accepted | Very high throughput |
| 9 | etcd | etcd — вариант для cache layer.<br>Зачем нужен: хранить повторяемые LLM responses, retrieval results, sessions, locks и rate-limit counters.<br>Бизнес-смысл: повторные сценарии БА становятся быстрее и дешевле, а provider limits не приводят к лавине ошибок.<br>Что проверить: Not for high-volume cache. | Coordination KV | Not for high-volume cache | Strong consistency, locks/config | `$0 license` | 3 small nodes | M | Apache 2.0 | Yes | Low throughput cache, strong consistency |
| 10 | Consul KV | Consul KV — вариант для cache layer.<br>Зачем нужен: хранить повторяемые LLM responses, retrieval results, sessions, locks и rate-limit counters.<br>Бизнес-смысл: повторные сценарии БА становятся быстрее и дешевле, а provider limits не приводят к лавине ошибок.<br>Что проверить: Not hot cache. | Service discovery/config KV | Not hot cache | Service discovery + KV | OSS/enterprise | 3 nodes | M | BUSL/commercial changes, review | Yes if license approved | Moderate KV |
| 11 | In-memory local cache | In-memory local cache — вариант для cache layer.<br>Зачем нужен: хранить повторяемые LLM responses, retrieval results, sessions, locks и rate-limit counters.<br>Бизнес-смысл: повторные сценарии БА становятся быстрее и дешевле, а provider limits не приводят к лавине ошибок.<br>Что проверить: No sharing, cold restarts. | Per-process LRU/TTL | No sharing, cold restarts | Zero infra, fastest | `$0` | App memory | XS | N/A | Yes | Very low latency, no persistence |
| 12 | CDN cache (Cloudflare) | CDN cache (Cloudflare) — вариант для cache layer.<br>Зачем нужен: хранить повторяемые LLM responses, retrieval results, sessions, locks и rate-limit counters.<br>Бизнес-смысл: повторные сценарии БА становятся быстрее и дешевле, а provider limits не приводят к лавине ошибок.<br>Что проверить: External, not private LLM cache. | Edge HTTP cache | External, not private LLM cache | Great static/API edge cache | Free/paid tiers | Managed | S | Commercial SaaS | Region-dependent | HTTP cache/rate limits |

**Рекомендации**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
| ------ | --------- | --------------------- | ----------------- |
| Budget | local cache + Memcached/Valkey | `$0-3k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если single-node pilot может жить с local cache или простым Valkey/Memcached<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нужны HA, multi-tenant, replay, SLA 99.9% или нагрузка >100 запросов/мин |
| Optimal | Redis/Valkey or Dragonfly | `$3k-20k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нужны shared sessions, LLM cache и rate limits между сервисами<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нет владельца эксплуатации, нет stage-gate на migration или объём пока похож на offline demo |
| Enterprise | Redis Cluster/Cloud, Hazelcast, Aerospike | `$20k-120k+` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если требуется HA, multi-tenant quotas и очень высокая throughput-нагрузка<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• ещё не подтверждены SLA, бюджет, security approval и выделенная Infra/SRE-команда |

**Пути миграции**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| Local cache -> Redis/Valkey | Add cache interface and TTL policy, accept cold start | None | Low |
| Redis -> Dragonfly/KeyDB/Valkey | Verify command compatibility, run shadow traffic | Low | Low-medium |
| Redis single -> cluster | Add key hash tags and cluster-aware client | Medium | Medium |
| Cache provider switch | Cache is disposable; preserve only session/auth if used | Low | Low |

<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**

**Что это значит для проекта:** этот компонент закрывает задачу: хранить повторяемые LLM responses, retrieval results, sessions, locks и rate-limit counters. В контексте Clarify Engine это влияет не на "красоту архитектуры", а на скорость, проверяемость и стоимость анализа требований.

**Почему важно для БА:** Для БА cache снижает latency и стоимость повторных вопросов, но должен быть прозрачен: stale answer нельзя выдавать как новое evidence.

**Технически:**
- Cache key должен включать prompt/model/config hash, иначе ответы разных режимов смешаются.
- Local cache самый быстрый, но не работает между replicas; Redis/Valkey дают shared TTL storage.
- Session/auth state нельзя мигрировать как disposable cache без отдельного плана.

**Когда выбирать:**
- 🟢 **Budget:** для пилота Clarify Engine на 1-3 БА с нагрузкой ≤15 запросов/мин, если single-node pilot может жить с local cache или простым Valkey/Memcached.
- 🟡 **Optimal:** для production pilot на 1-3 БА с нагрузкой ≤15 запросов/мин и ростом до нескольких сервисов, если нужны shared sessions, LLM cache и rate limits между сервисами.
- 🔵 **Enterprise:** после подтверждения SLA, бюджета, security approval и нагрузки >100 запросов/мин, если требуется HA, multi-tenant quotas и очень высокая throughput-нагрузка.

📚 **Читать далее:**
- [Redis caching patterns](https://redis.io/solutions/caching/) — типовые cache use cases, EN.
- [Valkey documentation](https://valkey.io/docs/) — Redis-compatible open source cache, EN.
- [Dragonfly documentation](https://www.dragonflydb.io/docs) — high-performance datastore, EN.

---
## 15. Компонент 12 - API Gateway

**Ответственность:** ingress, routing, auth, rate limiting, request transforms, OpenAPI и WebSocket/gRPC edge.

| № | Решение | Пояснение для БА | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | RPS / Auth / Rate limit / Transform / Circuit breaker / Discovery / WS / gRPC / OpenAPI |
| ---: | --------- | --- | ------------ | ------- | -------------- | ----------- | --------- | -------------- | ---------- | ------------------ | ------------------------------------------------------------------------------------- |
| 1 | FastAPI | FastAPI — вариант для API gateway.<br>Зачем нужен: давать единую входную точку, auth, rate limits и route governance для UI/API и внутренних сервисов.<br>Бизнес-смысл: пользователь видит стабильный API, даже если внутри система постепенно разделяется на сервисы.<br>Что проверить: Not full gateway alone. | App API + lightweight gateway | Not full gateway alone | Already Python, OpenAPI built-in, fast | `$0 license` | App server | S | MIT | Yes | Good RPS, JWT/OAuth libs, OpenAPI |
| 2 | NGINX + Lua | NGINX + Lua — вариант для API gateway.<br>Зачем нужен: давать единую входную точку, auth, rate limits и route governance для UI/API и внутренних сервисов.<br>Бизнес-смысл: пользователь видит стабильный API, даже если внутри система постепенно разделяется на сервисы.<br>Что проверить: Lua/plugin maintenance. | Reverse proxy/gateway | Lua/plugin maintenance | Mature, fast, simple edge | OSS `$0`; NGINX Plus paid | 1-2 vCPU | S/M | BSD-like / commercial Plus | Yes | High RPS, rate limit, TLS |
| 3 | Kong Gateway | Kong Gateway — вариант для API gateway.<br>Зачем нужен: давать единую входную точку, auth, rate limits и route governance для UI/API и внутренних сервисов.<br>Бизнес-смысл: пользователь видит стабильный API, даже если внутри система постепенно разделяется на сервисы.<br>Что проверить: DB/plugin ops, enterprise features paid. | API gateway/plugins | DB/plugin ops, enterprise features paid | Mature plugins, auth/rate limit, hybrid mode | OSS + Enterprise quote/cloud | 2-4 vCPU + DB | M | Apache 2.0 core / commercial | Yes self-host | Strong gateway features |
| 4 | Traefik | Traefik — вариант для API gateway.<br>Зачем нужен: давать единую входную точку, auth, rate limits и route governance для UI/API и внутренних сервисов.<br>Бизнес-смысл: пользователь видит стабильный API, даже если внутри система постепенно разделяется на сервисы.<br>Что проверить: Less enterprise API governance than Kong. | Cloud-native ingress | Less enterprise API governance than Kong | Simple Docker/K8s routing, auto TLS | OSS + Enterprise | 1-2 vCPU | S | MIT | Yes | Good routing, middleware |
| 5 | Envoy Proxy | Envoy Proxy — вариант для API gateway.<br>Зачем нужен: давать единую входную точку, auth, rate limits и route governance для UI/API и внутренних сервисов.<br>Бизнес-смысл: пользователь видит стабильный API, даже если внутри система постепенно разделяется на сервисы.<br>Что проверить: Config complexity. | L7 proxy/service mesh building block | Config complexity | High performance, gRPC, xDS | `$0 license` | 1-4 vCPU | M/H | Apache 2.0 | Yes | Strong gRPC/circuit breaker |
| 6 | Apache APISIX | Apache APISIX — вариант для API gateway.<br>Зачем нужен: давать единую входную точку, auth, rate limits и route governance для UI/API и внутренних сервисов.<br>Бизнес-смысл: пользователь видит стабильный API, даже если внутри система постепенно разделяется на сервисы.<br>Что проверить: Plugin/control-plane ops. | API gateway on NGINX/OpenResty | Plugin/control-plane ops | High performance, dynamic config | `$0 license`; enterprise/cloud paid | 2-4 vCPU + etcd | M | Apache 2.0 | Yes | Strong auth/rate/plugins |
| 7 | Tyk | Tyk — вариант для API gateway.<br>Зачем нужен: давать единую входную точку, auth, rate limits и route governance для UI/API и внутренних сервисов.<br>Бизнес-смысл: пользователь видит стабильный API, даже если внутри система постепенно разделяется на сервисы.<br>Что проверить: Commercial features, ops. | API management | Commercial features, ops | Strong API management and portal | OSS gateway + paid dashboard/cloud | 2-4 vCPU + DB | M | MPL/commercial | Yes self-host | Strong management |
| 8 | AWS API Gateway | AWS API Gateway — вариант для API gateway.<br>Зачем нужен: давать единую входную точку, auth, rate limits и route governance для UI/API и внутренних сервисов.<br>Бизнес-смысл: пользователь видит стабильный API, даже если внутри система постепенно разделяется на сервисы.<br>Что проверить: AWS lock-in, latency/cost. | Managed API gateway | AWS lock-in, latency/cost | No ops, auth/throttling, Lambda integration | HTTP API example `$1.00/M requests`; REST API example `$3.50/M` first tier, plus data/cache/private link | Managed | XS/S | Commercial SaaS | Region-dependent | Strong managed features |
| 9 | Cloudflare Workers | Cloudflare Workers — вариант для API gateway.<br>Зачем нужен: давать единую входную точку, auth, rate limits и route governance для UI/API и внутренних сервисов.<br>Бизнес-смысл: пользователь видит стабильный API, даже если внутри система постепенно разделяется на сервисы.<br>Что проверить: External edge/data path. | Edge gateway/functions | External edge/data path | Global edge, WAF, rate limits | Free 100k requests/day; Standard includes 10M/month, then `$0.30/M` requests and `$0.02/M` CPU-ms | Managed | S | Commercial SaaS | Global, not local | Edge scale |
| 10 | Express.js | Express.js — вариант для API gateway.<br>Зачем нужен: давать единую входную точку, auth, rate limits и route governance для UI/API и внутренних сервисов.<br>Бизнес-смысл: пользователь видит стабильный API, даже если внутри система постепенно разделяется на сервисы.<br>Что проверить: Another stack, less type safety. | Node API gateway | Another stack, less type safety | Simple JS ecosystem | `$0 license` | App server | S | MIT | Yes | Good for JS teams |
| 11 | Go Fiber/Gin | Go Fiber/Gin — вариант для API gateway.<br>Зачем нужен: давать единую входную точку, auth, rate limits и route governance для UI/API и внутренних сервисов.<br>Бизнес-смысл: пользователь видит стабильный API, даже если внутри система постепенно разделяется на сервисы.<br>Что проверить: Go stack required. | High-performance API | Go stack required | Very high RPS, low memory | `$0 license` | App server | M | MIT | Yes | High RPS |
| 12 | Spring Cloud Gateway | Spring Cloud Gateway — вариант для API gateway.<br>Зачем нужен: давать единую входную точку, auth, rate limits и route governance для UI/API и внутренних сервисов.<br>Бизнес-смысл: пользователь видит стабильный API, даже если внутри система постепенно разделяется на сервисы.<br>Что проверить: JVM ops/heavy for Python project. | JVM enterprise gateway | JVM ops/heavy for Python project | Strong enterprise Java ecosystem | `$0 license` | JVM server | M/H | Apache 2.0 | Yes | Good enterprise integration |

**Рекомендации**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
| ------ | --------- | --------------------- | ----------------- |
| Budget | FastAPI + NGINX | `$0-5k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если текущий Python stack закрывается FastAPI + NGINX и нужны простые auth/routing правила<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нужны HA, multi-tenant, replay, SLA 99.9% или нагрузка >100 запросов/мин |
| Optimal | Kong/APISIX or Envoy | `$5k-30k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если сервисов уже несколько и нужны plugins, route policies, service discovery и circuit breakers<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нет владельца эксплуатации, нет stage-gate на migration или объём пока похож на offline demo |
| Enterprise | Kong Enterprise/Tyk/AWS API Gateway/Cloudflare | `$30k-150k+` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нужны developer portal, WAF, глобальный edge, SLA и paid support<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• ещё не подтверждены SLA, бюджет, security approval и выделенная Infra/SRE-команда |

**Пути миграции**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| FastAPI only -> NGINX/Kong | Put gateway in front, keep app routes unchanged | Low | Low |
| NGINX -> Kong/APISIX | Translate routes/rate limits, migrate auth plugins | Low-medium | Medium |
| Self-host gateway -> cloud gateway | Preserve OpenAPI, DNS cutover, staged traffic | Low | Medium compliance |
| REST -> gRPC/internal | Keep REST external, introduce internal gRPC gradually | Medium | Medium |

<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**

**Что это значит для проекта:** этот компонент закрывает задачу: давать единую входную точку, auth, rate limits и route governance для UI/API и внутренних сервисов. В контексте Clarify Engine это влияет не на "красоту архитектуры", а на скорость, проверяемость и стоимость анализа требований.

**Почему важно для БА:** Для БА gateway убирает хаос внутренних endpoints: ingestion, retrieval и generation остаются внутренними деталями.

**Технически:**
- External OpenAPI должен быть стабильным, а внутренние service routes могут меняться постепенно.
- Rate limit и auth лучше централизовать на edge, чтобы сервисы не реализовывали их по-разному.
- Gateway migration делается DNS/route cutover с сохранением app routes.

**Когда выбирать:**
- 🟢 **Budget:** для пилота Clarify Engine на 1-3 БА с нагрузкой ≤15 запросов/мин, если текущий Python stack закрывается FastAPI + NGINX и нужны простые auth/routing правила.
- 🟡 **Optimal:** для production pilot на 1-3 БА с нагрузкой ≤15 запросов/мин и ростом до нескольких сервисов, если сервисов уже несколько и нужны plugins, route policies, service discovery и circuit breakers.
- 🔵 **Enterprise:** после подтверждения SLA, бюджета, security approval и нагрузки >100 запросов/мин, если нужны developer portal, WAF, глобальный edge, SLA и paid support.

📚 **Читать далее:**
- [FastAPI deployment concepts](https://fastapi.tiangolo.com/deployment/concepts/) — Python API behind proxy, EN.
- [NGINX rate limiting](https://docs.nginx.com/nginx/admin-guide/security-controls/controlling-access-proxied-http/) — access control, EN.
- [Kong Gateway documentation](https://docs.konghq.com/gateway/) — plugins, routing и auth, EN.

---
## 16. Компонент 13 - PII Masking / Data Anonymization

**Ответственность:** находить и маскировать PII перед external calls/logging, поддерживать RU-specific identifiers и reversible/irreversible tokenization, где это нужно.

| № | Решение | Пояснение для БА | Что решает | Риски | Преимущества | Стоимость | Ресурсы | Трудоемкость | Лицензия | RU-резидентность | RU PII / Accuracy / Latency / Custom patterns / Self-host / Cost / Reversible / Compliance |
| ---: | --------- | --- | ------------ | ------- | -------------- | ----------- | --------- | -------------- | ---------- | ------------------ | ----------------------------------------------------------------------------------------- |
| 1 | Custom regex-based | Custom regex-based — вариант для PII masking и data anonymization.<br>Зачем нужен: находить и маскировать персональные данные перед external API, logs и analytics.<br>Бизнес-смысл: реальные документы можно анализировать с меньшим compliance risk и контролем над тем, что покидает контур.<br>Что проверить: False positives/negatives, maintenance. | Known patterns: email, phone, IP, INN/SNILS/passport | False positives/negatives, maintenance | Deterministic, auditable, current BL-23 style | `$0` | CPU | S | Project code | Yes | Strong for exact RU patterns, weak semantic |
| 2 | Microsoft Presidio | Microsoft Presidio — вариант для PII masking и data anonymization.<br>Зачем нужен: находить и маскировать персональные данные перед external API, logs и analytics.<br>Бизнес-смысл: реальные документы можно анализировать с меньшим compliance risk и контролем над тем, что покидает контур.<br>Что проверить: RU recognizers must be custom. | PII detection/anonymization framework | RU recognizers must be custom | Self-host, extensible recognizers, anonymizers | `$0 license` | CPU, optional NLP models | M | MIT | Yes | Good custom patterns, reversible tokenization possible |
| 3 | Amazon Comprehend PII | Amazon Comprehend PII — вариант для PII masking и data anonymization.<br>Зачем нужен: находить и маскировать персональные данные перед external API, logs и analytics.<br>Бизнес-смысл: реальные документы можно анализировать с меньшим compliance risk и контролем над тем, что покидает контур.<br>Что проверить: External cloud, RU support limitations. | Managed PII detection | External cloud, RU support limitations | No ops, mature API | Per unit/character/request pricing | Managed | S | Commercial SaaS | Region-dependent | Good EN, RU must verify |
| 4 | Google Cloud Sensitive Data Protection (DLP) | Google Cloud Sensitive Data Protection (DLP) — вариант для PII masking и data anonymization.<br>Зачем нужен: находить и маскировать персональные данные перед external API, logs и analytics.<br>Бизнес-смысл: реальные документы можно анализировать с меньшим compliance risk и контролем над тем, что покидает контур.<br>Что проверить: External cloud, cost, data transfer. | DLP inspection/de-identification | External cloud, cost, data transfer | Broad detectors, de-identification, templates | Usage-based by bytes/requests | Managed | S/M | Commercial SaaS | Region-dependent | Strong generic DLP, custom infoTypes |
| 5 | Azure AI Language PII / Purview | Azure AI Language PII / Purview — вариант для PII masking и data anonymization.<br>Зачем нужен: находить и маскировать персональные данные перед external API, logs и analytics.<br>Бизнес-смысл: реальные документы можно анализировать с меньшим compliance risk и контролем над тем, что покидает контур.<br>Что проверить: Azure lock-in, language support must be tested. | PII detection/governance | Azure lock-in, language support must be tested | Enterprise compliance stack | Usage-based/quote | Managed | S/M | Commercial SaaS | Region-dependent | Good enterprise governance |
| 6 | Nightfall AI | Nightfall AI — вариант для PII masking и data anonymization.<br>Зачем нужен: находить и маскировать персональные данные перед external API, logs и analytics.<br>Бизнес-смысл: реальные документы можно анализировать с меньшим compliance risk и контролем над тем, что покидает контур.<br>Что проверить: Quote/SaaS, data residency. | SaaS DLP/PII | Quote/SaaS, data residency | Strong DLP workflows, SaaS integrations | Quote | Managed | S/M | Commercial SaaS | Contract-dependent | Broad DLP, custom detectors |
| 7 | Privacera | Privacera — вариант для PII masking и data anonymization.<br>Зачем нужен: находить и маскировать персональные данные перед external API, logs и analytics.<br>Бизнес-смысл: реальные документы можно анализировать с меньшим compliance risk и контролем над тем, что покидает контур.<br>Что проверить: Heavy enterprise platform. | Data governance/access control | Heavy enterprise platform | Policy governance across data estate | Quote | Managed/self-host options | H | Commercial | Contract-dependent | Compliance/governance strong |
| 8 | Immuta | Immuta — вариант для PII masking и data anonymization.<br>Зачем нужен: находить и маскировать персональные данные перед external API, logs и analytics.<br>Бизнес-смысл: реальные документы можно анализировать с меньшим compliance risk и контролем над тем, что покидает контур.<br>Что проверить: Overkill for simple masking. | Data access governance | Overkill for simple masking | Dynamic data policies, governance | Quote | Managed/self-host options | H | Commercial | Contract-dependent | Governance strong |
| 9 | TokenEx | TokenEx — вариант для PII masking и data anonymization.<br>Зачем нужен: находить и маскировать персональные данные перед external API, logs и analytics.<br>Бизнес-смысл: реальные документы можно анализировать с меньшим compliance risk и контролем над тем, что покидает контур.<br>Что проверить: Commercial dependency, integration. | Tokenization | Commercial dependency, integration | PCI/tokenization expertise | Quote | Managed | M | Commercial SaaS | Contract-dependent | Reversible tokenization strong |
| 10 | Delphix | Delphix — вариант для PII masking и data anonymization.<br>Зачем нужен: находить и маскировать персональные данные перед external API, logs и analytics.<br>Бизнес-смысл: реальные документы можно анализировать с меньшим compliance risk и контролем над тем, что покидает контур.<br>Что проверить: Heavy enterprise suite. | Data masking for databases | Heavy enterprise suite | Non-prod data masking, enterprise workflows | Quote | Managed/self-host | H | Commercial | Contract-dependent | Batch masking strong |
| 11 | IRI FieldShield | IRI FieldShield — вариант для PII masking и data anonymization.<br>Зачем нужен: находить и маскировать персональные данные перед external API, logs и analytics.<br>Бизнес-смысл: реальные документы можно анализировать с меньшим compliance risk и контролем над тем, что покидает контур.<br>Что проверить: Commercial tooling. | Data masking/anonymization | Commercial tooling | Broad masking formats, on-prem | Quote | Self-host | M/H | Commercial | Yes if deployed on-prem | Strong batch masking |
| 12 | Syntho | Syntho — вариант для PII masking и data anonymization.<br>Зачем нужен: находить и маскировать персональные данные перед external API, logs и analytics.<br>Бизнес-смысл: реальные документы можно анализировать с меньшим compliance risk и контролем над тем, что покидает контур.<br>Что проверить: Not request-time masking. | Synthetic data | Not request-time masking | Synthetic datasets for test/dev | Quote | SaaS/self-host options | M/H | Commercial | Contract-dependent | Synthetic data, privacy testing |

**Рекомендации**

| Tier | Решение | Year-1 TCO estimate | Когда применять |
| ------ | --------- | --------------------- | ----------------- |
| Budget | Custom regex + tests | `$0-5k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если известны deterministic RU patterns и достаточно regex + tests для MVP logs/RAG context<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нужны HA, multi-tenant, replay, SLA 99.9% или нагрузка >100 запросов/мин |
| Optimal | Presidio + custom RU recognizers + token vault | `$5k-25k` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если нужен local PII Gateway с custom RU recognizers и token vault<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• нет владельца эксплуатации, нет stage-gate на migration или объём пока похож на offline demo |
| Enterprise | Google/Azure/AWS DLP or Nightfall/Immuta/Privacera | `$30k-250k+` | ✅ Для пилота Clarify Engine:<br>• 1-3 БА одновременно<br>• Нагрузка ≤15 запросов/мин<br>• если compliance требует broad DLP, governance, reversible tokenization и централизованные policies<br>• есть rollback к текущему monolith/MVP path<br>❌ Не подходит, если:<br>• ещё не подтверждены SLA, бюджет, security approval и выделенная Infra/SRE-команда |

**Пути миграции**

| From -> To | Path | Downtime | Risk |
|------------|------|----------|------|
| Regex -> Presidio | Convert regexes to recognizers, preserve mask token format | Low | Low-medium |
| Presidio -> cloud DLP | Add provider adapter, route only approved data classes | Low | Compliance high |
| Irreversible mask -> tokenization | Introduce token vault and key management; old masks cannot be reversed | Medium | High |
| SaaS DLP -> local | Export detector config where possible, recreate custom recognizers | Medium | Medium |

<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**

**Что это значит для проекта:** этот компонент закрывает задачу: находить и маскировать персональные данные перед external API, logs и analytics. В контексте Clarify Engine это влияет не на "красоту архитектуры", а на скорость, проверяемость и стоимость анализа требований.

**Почему важно для БА:** Для БА это доверие к продукту: sensitive поля не должны случайно попасть в provider logs или CI artifacts.

**Технически:**
- Masking должен стоять перед каждым external LLM/API call, а не только в одном месте pipeline.
- Regex ловит точные patterns, Presidio даёт recognizer framework, cloud DLP включается только после approval.
- Token vault нужен заранее, если бизнесу потребуется обратимая деперсонализация.

**Когда выбирать:**
- 🟢 **Budget:** для пилота Clarify Engine на 1-3 БА с нагрузкой ≤15 запросов/мин, если известны deterministic RU patterns и достаточно regex + tests для MVP logs/RAG context.
- 🟡 **Optimal:** для production pilot на 1-3 БА с нагрузкой ≤15 запросов/мин и ростом до нескольких сервисов, если нужен local PII Gateway с custom RU recognizers и token vault.
- 🔵 **Enterprise:** после подтверждения SLA, бюджета, security approval и нагрузки >100 запросов/мин, если compliance требует broad DLP, governance, reversible tokenization и централизованные policies.

📚 **Читать далее:**
- [Microsoft Presidio documentation](https://microsoft.github.io/presidio/) — self-hosted PII detection/anonymization, EN.
- [Google Sensitive Data Protection de-identification](https://cloud.google.com/sensitive-data-protection/docs/deidentify-sensitive-data) — managed DLP patterns, EN.
- [Azure AI Language PII detection](https://learn.microsoft.com/en-us/azure/ai-services/language-service/personally-identifiable-information/overview) — PII detection concepts, EN.

---
## 17. Рекомендации на уровне архитектуры

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

<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**
- Три architecture stacks — это не "три разных продукта", а три уровня зрелости: дешёвый offline/pilot, сбалансированный production pilot и enterprise stack с SLA/governance.
- Для проекта это важно, потому что бизнес-решение о стеке должно учитывать не только цену лицензии, но и людей, инфраструктуру, compliance, migration cost и скорость проверки гипотезы.
- Технически: каждый компонент должен иметь provider interface и migration path, чтобы Sprint 6 мог начать с replaceable defaults, а не с необратимой привязки к Elasticsearch, SaaS LLM или GPU platform.
- Когда выбирать: Budget stack — для проверки ценности; Optimal stack — для Sprint 6/7 pilot с несколькими БА; Enterprise stack — после подтверждённой нагрузки, SLA и выделенного Infra/SRE.

📚 **Читать далее:**
- [Strangler Fig Application](https://martinfowler.com/bliki/StranglerFigApplication.html) — подход к постепенной миграции без Big Bang rewrite, EN.
- [OpenTelemetry documentation](https://opentelemetry.io/docs/) — нейтральный observability layer для заменяемых компонентов, EN.
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) — рамка управления AI-рисками на уровне организации, EN.

---

## 18. Реестр рисков

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

<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**
- Risk Register переводит технические неопределённости в управляемые бизнес-риски: цена может измениться, SaaS могут запретить, GPU могут не дать, а самая дешёвая пилотная технология может плохо масштабироваться.
- Для проекта это важно, потому что эти риски нужно закрывать решениями до разработки: approval gates, local fallbacks, migration paths, legal review лицензий и clear rollback.
- Технически: каждый high-impact risk должен иметь owner, signal и mitigation в backlog/ADR, иначе он останется "известной проблемой" без контроля.
- Когда использовать: перед Sprint 6 planning, перед закупкой/approval SaaS, перед выбором embedding model и перед переводом PoC в production pilot.

📚 **Читать далее:**
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) — системный подход к AI risk governance, EN.
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/) — практические risks для LLM/RAG систем, EN.

---

## 19. Decision Checklist для Sprint 6

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

<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**
- Decision Checklist — это список решений, которые нельзя оставлять "на потом", потому что от них зависят budget, compliance, latency и план работ команды.
- Для проекта это важно, потому что Sprint 6 должен начинаться не с разработки всех компонентов сразу, а с выбора primary/fallback options и clear contracts: search, bus, parsing, embeddings, serving, PII Gateway и audit fields.
- Технически: checklist должен быть входом в ADR-010 и новые BL-задачи, где у каждого решения есть acceptance criteria, rollout и rollback.
- Когда использовать: на Sprint planning и stage-gate review с PO/Tech Lead/Infra, чтобы зафиксировать, что все vendor/security вопросы видимы до implementation.

📚 **Читать далее:**
- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html) — как фиксировать API contracts между сервисами, EN.
- [Architecture Decision Records](https://adr.github.io/) — lightweight формат для фиксации архитектурных решений, EN.
- [GitHub Docs: About projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects) — tracking decisions и backlog work items, EN.

---

## 20. Реестр источников

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

<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**
- Source Register — это evidence trail исследования: по нему ревьюер видит, откуда взяты цены, лицензии, capabilities и ограничения каждого vendor.
- Для проекта это важно, потому что vendor pages меняются. Перед закупкой или implementation нельзя полагаться только на research snapshot; нужно перепроверить дату доступа, тариф, регион, license и support model.
- Технически: ссылки в этом документе проверены как внешние web sources на дату BL-67; future updates должны сохранять access date и не смешивать official docs, pricing и community обзоры без пометки.
- Когда использовать: при security/legal review, перед budget approval и перед обновлением backlog/ADR после изменения vendor pricing или license terms.

📚 **Читать далее:**
- [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/) — как фиксировать изменения документации и решений, RU.
- [Semantic Versioning](https://semver.org/lang/ru/) — подход к versioning артефактов и контрактов, RU.
- [W3C Link Checker](https://validator.w3.org/checklink) — инструментальная проверка ссылок, EN.

---

## 21. История изменений

| Версия | Дата | Изменение |
|--------|------|-----------|
| v2-business-readable | 2026-05-21 | BL-61.1: добавлены RU-пояснения к решениям в таблицах, конкретные сценарии `Когда применять` для Clarify Engine и HTML contract для переносов строк без ellipsis. |
| v1-ru-education | 2026-05-21 | BL-67 RU adaptation for BA/PO stakeholders: sections 4-20 keep BL-61 technical names and add `Для БА` explanations plus external reading links. |
| v1 | 2026-05-21 | First BL-61 market research covering 13 microservices architecture components, recommendations, migration paths, risks and source register. |
