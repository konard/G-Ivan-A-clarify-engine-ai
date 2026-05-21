#!/usr/bin/env python
"""Build the BL-61.1 business-readable v2 research artifact from v1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "docs" / "research" / "2026-05-21_bl-61_market-research_ru-education_v1.md"
TARGET_PATH = ROOT / "docs" / "research" / "2026-05-21_bl-61_market-research_ru-education_v2.md"


@dataclass(frozen=True)
class Component:
    label: str
    business_problem: str
    business_value: str
    budget: str
    optimal: str
    enterprise: str
    why: str
    technical: tuple[str, str, str]
    links: tuple[tuple[str, str, str], tuple[str, str, str], tuple[str, str, str]]


COMPONENTS: dict[int, Component] = {
    4: Component(
        label="поискового слоя и vector storage",
        business_problem="быстро находить релевантные фрагменты Корпуса требований по словам, смыслу и метаданным",
        business_value="меньше ложных ответов `НД`, выше цитируемость и понятный путь миграции от MVP к production",
        budget="если корпус до 50k chunks, один стенд, offline-пилот и допустим ручной backup/reindex",
        optimal="если нужен production pilot без гарантированного доступа к corporate Elasticsearch",
        enterprise="если уже есть search-команда, RBAC, snapshots, backup и требования к высокой нагрузке",
        why="БА видит не название базы данных, а качество evidence: какие разделы попали в ответ, можно ли фильтровать по продукту/странице и почему система выбрала именно эти chunks.",
        technical=(
            "`SearchBackend` должен скрывать Elasticsearch, OpenSearch, Qdrant, pgvector и ChromaDB за единым контрактом.",
            "Смена embedding dimensions или search engine требует parallel index и retrieval-eval до переключения alias.",
            "Hybrid search должен сохранять BM25 + vectors + metadata filters, иначе short/sparse требования снова дадут `STRICT_MODE -> НД`.",
        ),
        links=(
            ("Elasticsearch dense vector field", "https://www.elastic.co/guide/en/elasticsearch/reference/current/dense-vector.html", "vector search и HNSW, EN"),
            ("Qdrant hybrid queries", "https://qdrant.tech/documentation/concepts/hybrid-queries/", "dense + sparse retrieval, EN"),
            ("pgvector README", "https://github.com/pgvector/pgvector", "embeddings в PostgreSQL, EN"),
        ),
    ),
    5: Component(
        label="асинхронной шины событий",
        business_problem="разносить долгие операции parsing, indexing, rerank и LLM calls по очередям без зависания UI",
        business_value="БА может загрузить документ и продолжать работу, а система получает retries, backpressure и DLQ для разборов сбоев",
        budget="если нужны простые worker queues, нет event sourcing и нет выделенного DevOps под Kafka",
        optimal="если сервисов становится несколько и важны low-latency events с простой эксплуатацией",
        enterprise="если нужны replay событий, streaming analytics, multi-tenant топики и высокая throughput-нагрузка",
        why="Для БА это превращает долгие фоновые операции в управляемый workflow: документ не потеряется, ошибка попадёт в DLQ, а статус можно показать в UI.",
        technical=(
            "События должны иметь стабильные поля `run_id`, `document_id`, `event_type`, `payload_version`.",
            "`MessageBus` adapter должен позволять dual-publish при миграции RabbitMQ -> NATS -> Kafka.",
            "DLQ и retry-policy нужно проектировать до нагрузки, иначе batch indexing будет чиниться вручную.",
        ),
        links=(
            ("NATS JetStream concepts", "https://docs.nats.io/nats-concepts/jetstream", "persistent streams и consumers, EN"),
            ("RabbitMQ tutorials", "https://www.rabbitmq.com/tutorials", "queues, acknowledgements и routing, EN"),
            ("Apache Kafka documentation", "https://kafka.apache.org/documentation/", "topics, partitions и replication, EN"),
        ),
    ),
    6: Component(
        label="LLM orchestration и provider routing",
        business_problem="управлять prompts, fallback-провайдерами, typed output, cache, budget и observability для LLM-вызовов",
        business_value="стоимость и качество LLM становятся управляемыми: типовые запросы идут дешёвым маршрутом, сложные - в более сильный workflow",
        budget="если нужен provider fallback и structured output без внедрения полноценного workflow framework",
        optimal="если появляются повторяемые RAG pipelines, ingestion/query engines и понятная component model",
        enterprise="если нужны multi-step graphs, human-in-loop, prompt governance, evals и audit по каждому шагу",
        why="БА получает стабильное поведение вместо набора разрозненных if/else: система объяснимо выбирает provider, prompt и fallback.",
        technical=(
            "`LiteLLM` нормализует provider API и budgets, `Instructor` фиксирует Pydantic output, frameworks добавляют workflow graph.",
            "Prompt/version metadata должны попадать в audit, иначе нельзя повторить спорный ответ.",
            "Новый framework нельзя внедрять поверх `Pipeline` без adapter-слоя, чтобы не сломать текущий UI/export contract.",
        ),
        links=(
            ("LiteLLM documentation", "https://docs.litellm.ai/docs/", "provider routing, fallback и budgets, EN"),
            ("LlamaIndex documentation", "https://docs.llamaindex.ai/", "RAG data framework, EN"),
            ("LangChain RAG tutorial", "https://python.langchain.com/docs/tutorials/rag/", "пример RAG workflow, EN"),
        ),
    ),
    7: Component(
        label="document parsing и ingestion",
        business_problem="превращать DOCX/XLSX/PDF/PPTX в структурированные блоки текста, таблицы и locators",
        business_value="система сохраняет страницы, разделы и таблицы, поэтому ответ можно проверить по источнику",
        budget="если документы в основном текстовые, без тяжёлого OCR, а локаторы можно получить текущими parser-библиотеками",
        optimal="если встречаются смешанные PDF/DOCX с таблицами и нужен local-first extraction без SaaS",
        enterprise="если много сканов, нужен managed OCR SLA и security/legal approval на передачу документов",
        why="Для БА parser определяет, можно ли доверять цитате: если таблица или номер раздела потеряны на входе, LLM уже не восстановит доказательство.",
        technical=(
            "`load_requirements_by_extension` должен остаться фасадом, а новый parser добавляет поля additively.",
            "Raw file, extracted JSON и parser confidence нужно сохранять для повторной проверки.",
            "Managed OCR включается только через compliance gate и желательно только для failed/scanned documents.",
        ),
        links=(
            ("Docling GitHub repository", "https://github.com/docling-project/docling", "local-first document conversion, EN"),
            ("Unstructured open source overview", "https://docs.unstructured.io/open-source/introduction/overview", "partitioning и chunking, EN"),
            ("Azure Document Intelligence documentation", "https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/", "managed OCR/layout, EN"),
        ),
    ),
    8: Component(
        label="embedding models",
        business_problem="переводить chunks и queries в vectors для semantic и hybrid retrieval",
        business_value="поиск понимает разные формулировки одного требования и не требует ручного словаря для каждого синонима",
        budget="если нужна RU-resident модель без внешней передачи текста и достаточно CPU/GPU одной машины",
        optimal="если нужно сравнить качество bge-m3, multilingual-e5 и Jina на Golden Set без SaaS",
        enterprise="если внешние API approved, нужна managed throughput и есть бюджет на re-embedding",
        why="БА не видит embeddings напрямую, но именно они определяют, найдётся ли раздел про SSO по запросу 'единый вход'.",
        technical=(
            "Размерность vectors фиксирует schema индекса; 768, 1024 и 3072 нельзя смешивать в одном field.",
            "Смена модели требует parallel re-embedding, retrieval metrics и controlled switch.",
            "PII-sensitive chunks нельзя отправлять во внешний embedding API без masking/approval.",
        ),
        links=(
            ("BAAI/bge-m3 model card", "https://huggingface.co/BAAI/bge-m3", "multilingual dense/sparse embeddings, EN"),
            ("OpenAI embeddings guide", "https://platform.openai.com/docs/guides/embeddings", "API embeddings concepts, EN"),
            ("Jina embeddings documentation", "https://jina.ai/embeddings/", "multilingual embeddings, EN"),
        ),
    ),
    9: Component(
        label="local LLM serving",
        business_problem="запускать LLM внутри контролируемой инфраструктуры для PII-sensitive запросов и fallback",
        business_value="чувствительные документы не уходят во внешний API, а pilot не зависит полностью от доступности SaaS-провайдера",
        budget="если нужен single-node/offline pilot, простая установка на АРМ и допустима ограниченная concurrency",
        optimal="если у пилота несколько БА, нужна OpenAI-compatible API и batching на GPU",
        enterprise="если есть dedicated GPU platform, SLA latency и SRE/ML-infra команда",
        why="Для БА local serving означает понятную границу данных: sensitive prompts остаются внутри контура, но бизнес должен оплатить GPU/ops при росте нагрузки.",
        technical=(
            "`Ollama`/`llama.cpp` хороши для установки, `vLLM`/`TGI` - для throughput, `TensorRT-LLM` - для NVIDIA-оптимизации.",
            "Клиент должен говорить через стабильный OpenAI-compatible или adapter API, чтобы миграция была заменой endpoint/model.",
            "Model version, quantization и decoding params фиксируются в audit для повторяемости.",
        ),
        links=(
            ("Ollama API documentation", "https://github.com/ollama/ollama/blob/main/docs/api.md", "локальный HTTP API, EN"),
            ("vLLM documentation", "https://docs.vllm.ai/", "high-throughput serving, EN"),
            ("Hugging Face TGI documentation", "https://huggingface.co/docs/text-generation-inference/index", "production inference server, EN"),
        ),
    ),
    10: Component(
        label="rerank stage",
        business_problem="пересортировывать top-K найденных chunks по реальной полезности для конкретного запроса",
        business_value="в prompt попадает меньше похожих, но неверных фрагментов, поэтому ответы становятся точнее без замены основной LLM",
        budget="если нет GPU и нужен быстрый CPU precision boost поверх текущего retrieval",
        optimal="если нужен local RU-resident rerank top-20/top-50 для production pilot",
        enterprise="если approved SaaS или отдельная retrieval infra позволяют максимизировать precision",
        why="Для БА reranker уменьшает число спорных ответов: система не просто нашла похожие chunks, а проверила их соответствие запросу.",
        technical=(
            "Rerank stage должен быть optional feature flag после retrieval и до prompt assembly.",
            "Scoring contract лучше держать простым: `{chunk_id, score, provider, model_version}`.",
            "API-rerank требует de-identification snippets и score cache by query/chunk hash.",
        ),
        links=(
            ("BAAI/bge-reranker-large model card", "https://huggingface.co/BAAI/bge-reranker-large", "local multilingual reranker, EN"),
            ("Cohere Rerank documentation", "https://docs.cohere.com/docs/rerank-2", "managed reranking API, EN"),
            ("FlashRank GitHub repository", "https://github.com/PrithivirajDamodaran/FlashRank", "CPU reranking library, EN"),
        ),
    ),
    11: Component(
        label="observability stack",
        business_problem="собирать logs, metrics и traces для поиска причин плохих ответов, timeouts и ошибок pipeline",
        business_value="команда видит, где сломался запрос: parser, retrieval, provider, cache, gateway или prompt",
        budget="если нужен self-host pilot с базовыми dashboards и без платного SaaS",
        optimal="если микросервисы требуют portable traces, Sentry errors и Grafana dashboards",
        enterprise="если нужен 24/7 operations, advanced alerting и low-ops managed platform",
        why="Для БА observability сокращает время разбора инцидента: плохой ответ перестаёт быть 'магией LLM' и раскладывается на конкретные сигналы.",
        technical=(
            "`OpenTelemetry` должен быть нейтральным сборщиком traces/metrics/logs до выбора backend.",
            "`run_id` и `trace_id` должны проходить через UI, bus, retrieval, generation и audit.",
            "Retention и sampling нужно задать сразу, иначе logs быстро становятся дорогими.",
        ),
        links=(
            ("OpenTelemetry documentation", "https://opentelemetry.io/docs/", "vendor-neutral signals, EN"),
            ("Grafana Loki documentation", "https://grafana.com/docs/loki/latest/", "log aggregation, EN"),
            ("Sentry documentation", "https://docs.sentry.io/", "error tracking, EN"),
        ),
    ),
    12: Component(
        label="audit database",
        business_problem="хранить immutable evidence: кто запустил анализ, какая model ответила, какие chunks и masks использовались",
        business_value="спорный результат можно повторить, объяснить и проверить на compliance",
        budget="если нужен pilot audit с простыми SQL-отчётами и append-only политикой",
        optimal="если событий много и нужны быстрые аналитические запросы без потери PostgreSQL metadata",
        enterprise="если audit становится частью BI/compliance reporting и approved managed warehouse",
        why="Для БА audit trail превращает AI-ответ в проверяемый процесс: можно увидеть источники, параметры и причины fallback.",
        technical=(
            "Audit rows должны быть append-only; UPDATE/DELETE закрываются ролями, triggers или WORM archive.",
            "PostgreSQL удобен для metadata, ClickHouse - для большого потока events и дешёвых аналитических запросов.",
            "Raw prompt/context хранить опасно; нужны masks, hashes и retention policy.",
        ),
        links=(
            ("PostgreSQL trigger documentation", "https://www.postgresql.org/docs/current/sql-createtrigger.html", "append-only rules, EN"),
            ("ClickHouse introduction", "https://clickhouse.com/docs/en/intro", "columnar analytics, EN"),
            ("Amazon S3 Object Lock", "https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html", "WORM archive concept, EN"),
        ),
    ),
    13: Component(
        label="object storage",
        business_problem="сохранять raw uploads, parser artifacts, extracted JSON, reports, snapshots и audit archives",
        business_value="анализ можно воспроизвести: исходный файл и промежуточные артефакты не теряются и не перезаписываются без следа",
        budget="если offline demo допускает single-node storage и ручной backup",
        optimal="если нужен production pilot с RU residency, S3 API, lifecycle и нормальным backup",
        enterprise="если нужны object lock, disaster recovery, lifecycle tiers и enterprise backup",
        why="Для БА object storage отвечает за доказуемость: если raw document или extracted JSON потеряны, проверить ответ уже невозможно.",
        technical=(
            "`ObjectStore` interface должен работать с local FS, MinIO и S3-compatible providers одинаково.",
            "Ключи лучше строить по content hash/document_id, чтобы избежать перезаписи и дубликатов.",
            "Audit archives требуют immutability/versioning, а не просто общей папки.",
        ),
        links=(
            ("MinIO object storage documentation", "https://min.io/docs/minio/linux/index.html", "self-hosted S3-compatible storage, EN"),
            ("Amazon S3 User Guide", "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html", "managed object storage, EN"),
            ("Yandex Object Storage documentation", "https://yandex.cloud/ru/docs/storage/", "RU cloud S3-compatible option, RU"),
        ),
    ),
    14: Component(
        label="cache layer",
        business_problem="хранить повторяемые LLM responses, retrieval results, sessions, locks и rate-limit counters",
        business_value="повторные сценарии БА становятся быстрее и дешевле, а provider limits не приводят к лавине ошибок",
        budget="если single-node pilot может жить с local cache или простым Valkey/Memcached",
        optimal="если нужны shared sessions, LLM cache и rate limits между сервисами",
        enterprise="если требуется HA, multi-tenant quotas и очень высокая throughput-нагрузка",
        why="Для БА cache снижает latency и стоимость повторных вопросов, но должен быть прозрачен: stale answer нельзя выдавать как новое evidence.",
        technical=(
            "Cache key должен включать prompt/model/config hash, иначе ответы разных режимов смешаются.",
            "Local cache самый быстрый, но не работает между replicas; Redis/Valkey дают shared TTL storage.",
            "Session/auth state нельзя мигрировать как disposable cache без отдельного плана.",
        ),
        links=(
            ("Redis caching patterns", "https://redis.io/solutions/caching/", "типовые cache use cases, EN"),
            ("Valkey documentation", "https://valkey.io/docs/", "Redis-compatible open source cache, EN"),
            ("Dragonfly documentation", "https://www.dragonflydb.io/docs", "high-performance datastore, EN"),
        ),
    ),
    15: Component(
        label="API gateway",
        business_problem="давать единую входную точку, auth, rate limits и route governance для UI/API и внутренних сервисов",
        business_value="пользователь видит стабильный API, даже если внутри система постепенно разделяется на сервисы",
        budget="если текущий Python stack закрывается FastAPI + NGINX и нужны простые auth/routing правила",
        optimal="если сервисов уже несколько и нужны plugins, route policies, service discovery и circuit breakers",
        enterprise="если нужны developer portal, WAF, глобальный edge, SLA и paid support",
        why="Для БА gateway убирает хаос внутренних endpoints: ingestion, retrieval и generation остаются внутренними деталями.",
        technical=(
            "External OpenAPI должен быть стабильным, а внутренние service routes могут меняться постепенно.",
            "Rate limit и auth лучше централизовать на edge, чтобы сервисы не реализовывали их по-разному.",
            "Gateway migration делается DNS/route cutover с сохранением app routes.",
        ),
        links=(
            ("FastAPI deployment concepts", "https://fastapi.tiangolo.com/deployment/concepts/", "Python API behind proxy, EN"),
            ("NGINX rate limiting", "https://docs.nginx.com/nginx/admin-guide/security-controls/controlling-access-proxied-http/", "access control, EN"),
            ("Kong Gateway documentation", "https://docs.konghq.com/gateway/", "plugins, routing и auth, EN"),
        ),
    ),
    16: Component(
        label="PII masking и data anonymization",
        business_problem="находить и маскировать персональные данные перед external API, logs и analytics",
        business_value="реальные документы можно анализировать с меньшим compliance risk и контролем над тем, что покидает контур",
        budget="если известны deterministic RU patterns и достаточно regex + tests для MVP logs/RAG context",
        optimal="если нужен local PII Gateway с custom RU recognizers и token vault",
        enterprise="если compliance требует broad DLP, governance, reversible tokenization и централизованные policies",
        why="Для БА это доверие к продукту: sensitive поля не должны случайно попасть в provider logs или CI artifacts.",
        technical=(
            "Masking должен стоять перед каждым external LLM/API call, а не только в одном месте pipeline.",
            "Regex ловит точные patterns, Presidio даёт recognizer framework, cloud DLP включается только после approval.",
            "Token vault нужен заранее, если бизнесу потребуется обратимая деперсонализация.",
        ),
        links=(
            ("Microsoft Presidio documentation", "https://microsoft.github.io/presidio/", "self-hosted PII detection/anonymization, EN"),
            ("Google Sensitive Data Protection de-identification", "https://cloud.google.com/sensitive-data-protection/docs/deidentify-sensitive-data", "managed DLP patterns, EN"),
            ("Azure AI Language PII detection", "https://learn.microsoft.com/en-us/azure/ai-services/language-service/personally-identifiable-information/overview", "PII detection concepts, EN"),
        ),
    ),
}


def split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def format_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def ba_note(component: Component, row: list[str]) -> str:
    solution = row[1]
    risk = row[3]
    return (
        f"{solution} — вариант для {component.label}.<br>"
        f"Зачем нужен: {component.business_problem}.<br>"
        f"Бизнес-смысл: {component.business_value}.<br>"
        f"Что проверить: {risk}."
    )


def insert_ba_column(section: str, component: Component) -> str:
    lines = section.splitlines()
    table_start = next(
        index for index, line in enumerate(lines) if line.startswith("| № | Решение |")
    )
    table_end = table_start
    while table_end < len(lines) and lines[table_end].startswith("|"):
        table_end += 1

    updated: list[str] = []
    for offset, line in enumerate(lines[table_start:table_end]):
        cells = split_row(line)
        if offset == 0:
            cells.insert(2, "Пояснение для БА")
        elif offset == 1:
            cells.insert(2, "---")
        elif len(cells) > 2 and cells[0].strip(":").isdigit():
            cells.insert(2, ba_note(component, cells))
        updated.append(format_row(cells))

    return "\n".join(lines[:table_start] + updated + lines[table_end:])


def recommendation_text(tier: str, component: Component) -> str:
    context = {
        "Budget": component.budget,
        "Optimal": component.optimal,
        "Enterprise": component.enterprise,
    }[tier]
    anti_case = {
        "Budget": "нужны HA, multi-tenant, replay, SLA 99.9% или нагрузка >100 запросов/мин",
        "Optimal": "нет владельца эксплуатации, нет stage-gate на migration или объём пока похож на offline demo",
        "Enterprise": "ещё не подтверждены SLA, бюджет, security approval и выделенная Infra/SRE-команда",
    }[tier]
    return (
        "✅ Для пилота Clarify Engine:<br>"
        "• 1-3 БА одновременно<br>"
        "• Нагрузка ≤15 запросов/мин<br>"
        f"• {context}<br>"
        "• есть rollback к текущему monolith/MVP path<br>"
        "❌ Не подходит, если:<br>"
        f"• {anti_case}"
    )


def expand_recommendations(section: str, component: Component) -> str:
    lines = section.splitlines()
    rec_heading = lines.index("**Рекомендации**")
    table_start = next(
        index
        for index in range(rec_heading + 1, len(lines))
        if lines[index].startswith("| Tier |")
    )
    table_end = table_start
    while table_end < len(lines) and lines[table_end].startswith("|"):
        table_end += 1

    updated: list[str] = []
    for offset, line in enumerate(lines[table_start:table_end]):
        cells = split_row(line)
        if offset >= 2 and cells and cells[0] in {"Budget", "Optimal", "Enterprise"}:
            cells[3] = recommendation_text(cells[0], component)
        updated.append(format_row(cells))

    return "\n".join(lines[:table_start] + updated + lines[table_end:])


def education_block(component: Component) -> str:
    links = "\n".join(
        f"- [{title}]({url}) — {description}."
        for title, url, description in component.links
    )
    technical = "\n".join(f"- {item}" for item in component.technical)
    return f"""<!-- AUTO-GENERATED: do not edit education blocks manually -->

💡 **Для БА: что это значит для проекта?**

**Что это значит для проекта:** этот компонент закрывает задачу: {component.business_problem}. В контексте Clarify Engine это влияет не на "красоту архитектуры", а на скорость, проверяемость и стоимость анализа требований.

**Почему важно для БА:** {component.why}

**Технически:**
{technical}

**Когда выбирать:**
- 🟢 **Budget:** для пилота Clarify Engine на 1-3 БА с нагрузкой ≤15 запросов/мин, {component.budget}.
- 🟡 **Optimal:** для production pilot на 1-3 БА с нагрузкой ≤15 запросов/мин и ростом до нескольких сервисов, {component.optimal}.
- 🔵 **Enterprise:** после подтверждения SLA, бюджета, security approval и нагрузки >100 запросов/мин, {component.enterprise}.

📚 **Читать далее:**
{links}
"""


def replace_education_block(section: str, component: Component) -> str:
    start = section.index("<!-- AUTO-GENERATED: do not edit education blocks manually -->")
    end = section.index("\n---", start)
    return section[:start] + education_block(component) + section[end:]


def section_bounds(text: str, number: int) -> tuple[int, int]:
    marker = f"\n## {number}. "
    start = text.index(marker)
    next_marker = f"\n## {number + 1}. "
    end = text.find(next_marker, start + len(marker))
    return start, len(text) if end == -1 else end


def update_metadata(text: str) -> str:
    replacements = {
        "# Research: RU-education adaptation for BL-61 Market Comparison (BL-67)": "# Research: Business-readable RU education adaptation for BL-61 Market Comparison (BL-61.1)",
        "- **Версия:** v1": "- **Версия:** v2",
        "- **Статус:** Draft -> готов к ревью BA / PO / Tech Lead / Infra": "- **Статус:** Draft -> готов к ревью BA / PO / Tech Lead / Infra по issue #224",
        "- **Автор:** konard (AI issue solver, по [issue #220](https://github.com/G-Ivan-A/clarify-engine-ai/issues/220))": "- **Автор:** konard (AI issue solver, по [issue #224](https://github.com/G-Ivan-A/clarify-engine-ai/issues/224))",
        "- **PR:** [`#221`](https://github.com/G-Ivan-A/clarify-engine-ai/pull/221)": "- **PR:** [`#225`](https://github.com/G-Ivan-A/clarify-engine-ai/pull/225)",
        "- **Depends on:** BL-61 (Market Research for Microservices Architecture Components)": "- **Depends on:** BL-61 (Market Research for Microservices Architecture Components), BL-67 (RU education adaptation v1)",
        "> **Scope note.** Это образовательная RU-адаптация BL-61, не реализация.\n> Исходный файл BL-61 не изменяется. Документ не меняет `src/`, `configs/`,\n> `prompts/` и не фиксирует необратимый vendor lock-in. Цель BL-67 - дать BA /\n> PO понятное объяснение, зачем нужны компоненты микросервисной AI/RAG\n> архитектуры, какие бизнес-риски они закрывают и куда можно углубиться через\n> внешние источники.": "> **Scope note.** Это образовательная RU-адаптация BL-61, не реализация.\n> Исходный файл BL-61 не изменяется. Документ не меняет `src/`, `configs/`,\n> `prompts/` и не фиксирует необратимый vendor lock-in. Цель BL-61.1 - сделать\n> market research читаемым для BA / PO: добавить RU-пояснение к каждому решению,\n> конкретизировать сценарии `Когда применять` и обеспечить перенос строк в HTML.\n>\n> **HTML readability contract.** Companion HTML v2 генерируется через\n> `scripts/tools/md_to_html_fullwidth.py` и использует `white-space: normal`,\n> `overflow-wrap: anywhere`, `word-break: normal`; `text-overflow: ellipsis` и\n> `white-space: nowrap` запрещены для ячеек таблиц.",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = text.replace(
        "- **Исходный артефакт:** [`docs/research/2026-05-21_bl-61_market-research_v1.md`](2026-05-21_bl-61_market-research_v1.md)",
        "- **Исходный артефакт:** [`docs/research/2026-05-21_bl-61_market-research_v1.md`](2026-05-21_bl-61_market-research_v1.md)\n- **Предыдущая RU-адаптация:** [`docs/research/2026-05-21_bl-61_market-research_ru-education_v1.md`](2026-05-21_bl-61_market-research_ru-education_v1.md)",
    )
    text = text.replace(
        "| Версия | Дата | Изменение |\n|--------|------|-----------|",
        "| Версия | Дата | Изменение |\n|--------|------|-----------|\n| v2-business-readable | 2026-05-21 | BL-61.1: добавлены RU-пояснения к решениям в таблицах, конкретные сценарии `Когда применять` для Clarify Engine и HTML contract для переносов строк без ellipsis. |",
    )
    return text


def build() -> str:
    text = update_metadata(SOURCE_PATH.read_text(encoding="utf-8"))
    for number, component in COMPONENTS.items():
        start, end = section_bounds(text, number)
        section = text[start:end]
        section = insert_ba_column(section, component)
        section = expand_recommendations(section, component)
        section = replace_education_block(section, component)
        text = text[:start] + section + text[end:]
    return text


def main() -> int:
    TARGET_PATH.write_text(build(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
