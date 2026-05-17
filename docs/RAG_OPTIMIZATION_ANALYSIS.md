# RAG Pipeline Analysis & Optimization Roadmap

> Аналитический отчёт по текущему состоянию RAG-пайплайна Clarify Engine и
> дорожной карте его оптимизации для технической документации SaaS-решений
> (LK ВАТС, VPBX API, Quality Monitoring, Речевая аналитика, SIP Trunk).
>
> Документ зафиксирован в корне `docs/` намеренно — он адресует кросс-модульную
> доработку и должен быть легко обнаружим из ROOT-уровня репозитория, как и
> `docs/CONCEPT.md` и `docs/DEV_NOTES.md`. Версия `v1` подготовлена для
> обсуждения с PO; финальная редакция переедет в `docs/analysis/` по
> [naming-convention](standards/naming-convention.md).

## 🗂 Метаданные
- **Дата:** 2026-05-16
- **Версия:** v1
- **Автор:** konard (AI issue solver)
- **Статус:** Draft → Review
- **Связанные документы:**
  - [`docs/CONCEPT.md`](CONCEPT.md) — концепция MVP (раздел 4 НФТ).
  - [`docs/ADR/001-rag-architecture.md`](ADR/001-rag-architecture.md) — выбор Hybrid RAG (BM25 + Dense + RRF, ChromaDB, `BAAI/bge-m3`).
  - [`docs/analysis/2026-05-15_analysis_repo-state-and-mvp-recommendations_v1.md`](analysis/2026-05-15_analysis_repo-state-and-mvp-recommendations_v1.md) — анализ состояния репозитория.
  - [`configs/embedding_config.yaml`](../configs/embedding_config.yaml) — параметры чанкинга и vector store.
  - [`src/rag/chunker.py`](../src/rag/chunker.py), [`src/rag/retriever.py`](../src/rag/retriever.py), [`knowledge_base/indexing/build_index.py`](../knowledge_base/indexing/build_index.py), [`src/llm/client.py`](../src/llm/client.py), [`src/ui/app.py`](../src/ui/app.py).
  - GitHub issue [#75](https://github.com/G-Ivan-A/clarify-engine-ai/issues/75) — постановка задачи.

---

## 0. TL;DR

| Срез | Текущее состояние | Целевое состояние (P0–P2) |
|------|--------------------|---------------------------|
| Chunking | Фиксированные 250 токенов × overlap 50, без секционной структуры | Раздел-aware splitter (Layer 1) + Parent Document Retrieval (Layer 2) + соседи (Layer 3) |
| Metadata | Только `source` + `chunk_idx` | Базовые (page, section_title, section_number) + семантические (content_type, product, version) + структурные (parent_section, depth) |
| Retrieval | Один проход `ChromaRetriever.search` в UI; `HybridRetriever.search` неактивен в production-пути | Multi-stage: Hybrid (BM25 + Dense + RRF) → Rerank → Multi-hop (2 итерации) |
| Generation | Stateless вызов LLM с базовым system prompt | Prompt library + STRICT_MODE + цитирование с гиперссылками |
| Memory | Stateless Streamlit | `st.session_state` + Last-N с summarization fallback |
| Grounding | Markdown упоминание `[filename.pdf]` | Faithfulness-check + кликабельные ссылки `file#page=N` |
| Evaluation | `evaluate_quality.py` только для классификации ТЗ | Golden Set 30–50 Q/A + RAGAS (Faithfulness / Answer Relevance / Context Recall / Hit Rate@K) |
| Ollama | `qwen2.5:7b` дефолт, синхронные вызовы | Профилирование `qwen2.5:7b-instruct-q4_K_M` / `llama3.1:8b-instruct-q4_K_M` + async-очередь |

**Главный риск, который мы предлагаем снять P0:** связанные разделы документации
(`«Настройка …» + «Зависимости …» + «Если не работает …»`) разрываются текущим
fixed-window chunker и теряются при one-shot retrieval. Это напрямую бьёт по
KPI «цитируемость ≥ 95 %» из ADR-001.

---

## 1. Понимание контекста

### 1.1 Цели и ограничения
- **Бизнес-задача:** автоматическая классификация требований ТЗ (Да / Частично / Нет / НД) с обязательным цитированием и ответ на свободные вопросы инженеров по знаниевой базе из 11 PDF (66.7 МБ, MANGO OFFICE стек: ЛК ВАТС, VPBX, QM, Речевая аналитика, SIP, Click2Call) — см. [`knowledge_base/SOURCES_MANIFEST.md`](../knowledge_base/SOURCES_MANIFEST.md).
- **НФТ:** F1 ≥ 0.75, цитируемость ≥ 95 %, длительность одного RAG-ответа в UI «комфортная для интерактива» (целевой p95 < 30 с с учётом fallback цепочки).
- **Жёсткие ограничения:**
  - Резидентность: чувствительные данные не покидают контур; зарубежные API только при `use_test_data_mode: true` (CONCEPT §5).
  - Запрет на framework lock-in: только `streamlit`, `chromadb`, `requests`, `sentence-transformers`, `yaml`, `dotenv` (см. `src/ui/app.py:15-19`). Это исключает прямое внедрение LangChain/LlamaIndex как зависимости, но не запрещает заимствовать их паттерны и реализовать их «на тонком слое» вручную.

### 1.2 Анализируемая область
Этот документ покрывает **RAG-пайплайн целиком** — от индексации до выдачи
ответа, включая семь срезов (1) фрагментация контекста и зависимости, (2)
multi-hop retrieval, (3) метаданные, (4) многоходовый диалог, (5) валидация
и цитирование, (6) оценка качества, (7) оптимизация локального Ollama.

### 1.3 За пределами этого документа
- Конкретные изменения схемы экспорта Excel — это [ADR-002](ADR/002-export-schema-extension.md).
- Безопасность каналов передачи (TLS, OAuth2 GigaChat) — покрывается [`SECURITY.md`](../SECURITY.md).
- Дизайн UX чат-интерфейса (визуальный) — за исключением минимально необходимого описания `st.session_state`.

---

## 2. Анализ текущего состояния (Diagnostics)

### 2.1 Карта текущего пайплайна

```
PDF (11 файлов, 66.7 МБ)
    │
    ▼
build_index.py ─── pypdf.PdfReader().extract_text()  (page-aware,
    │                       но page boundaries отбрасываются)
    ▼
TokenChunker (bge-m3, 250 tok × overlap 50)
    │   metadata = {source, chunk_idx}        ← ТОЛЬКО ЭТО
    ▼
ChromaDB (clarify_engine_kb, 1024 dim)
    │
    ▼
ChromaRetriever.search(query, top_k=5)        ← pure dense, без BM25
    │
    ▼
LLMClient.generate_rag_response()             ← GigaChat → OpenRouter → Ollama
    │
    ▼
Streamlit UI (stateless)
```

### 2.2 Проблема №1 — фрагментация контекста

**Где смотреть:** `src/rag/chunker.py:147-169`.

```python
step = max(1, self.chunk_size - self.chunk_overlap)  # 200 для 250/50
while start < len(token_ids):
    end = min(start + self.chunk_size, len(token_ids))
    ...
    start += step
```

Чанкер «слепой» — он не знает ни про границы PDF-страниц, ни про
заголовки разделов «7.3.6 Настройка SSO», ни про маркеры «Зависимости»,
«Предварительные условия», «Если не работает». При среднем
техническом разделе MANGO OFFICE 600–1200 токенов это означает:

1. Заголовок раздела попадает в один чанк, а критичный блок «Зависимости» —
   в следующий, разорванный посередине предложения.
2. Запрос «как настроить SSO в ЛК ВАТС?» с top_k=5 может вытащить пять
   соседних чанков из MIDDLE параграфов, ни в одном из которых нет
   ключевого заголовка `7.3.6`, на который БА должен сослаться.
3. Кросс-документные зависимости (`«см. SIP_trunk-1.23.43.pdf §4.2»`)
   полностью теряются — текстовая ссылка попадает в один чанк, целевой
   раздел физически в другом файле, и retrieval их не связывает.

**Эмпирический прокси-замер (без выкладки реального индекса):** 11 PDF × ≈
4500 токенов на страницу (грубо) × ≈ 200 страниц = ~1.0 М токенов → при шаге
200 токенов это ~5000 чанков. С `top_k=5` UI показывает <0.1 % корпуса за
один проход. Шанс собрать всю зависимость одним запросом невелик.

### 2.3 Проблема №2 — отсутствие метаданных

**Где смотреть:** `knowledge_base/indexing/build_index.py:238`.

```python
metadatas.append({"source": path.name, "chunk_idx": idx})
```

Это **минимум миниморум.** Чего нет:

| Категория | Поля, которые НЕ извлекаются |
|-----------|------------------------------|
| Базовые | `page_number`, `section_title`, `section_number`, `paragraph_idx` |
| Семантические | `content_type` (instruction / troubleshooting / dependencies / reference), `product`, `version`, `audience` (admin / user / integrator) |
| Структурные | `parent_section`, `depth`, `has_prerequisites`, `has_dependencies`, `related_sections` |

Последствия:
- **Невозможно цитировать страницу и раздел** — UI выводит только имя файла.
- **Невозможно отфильтровать поиск по продукту** (`product = "QM"`) — а это первое, чего попросит БА.
- **Невозможно построить «See also»** — список связанных разделов.

### 2.4 Проблема №3 — pure-dense retrieval в production-пути

**Расхождение:** в репозитории реализованы **два** retrieval-класса
([`src/rag/retriever.py:364-510`](../src/rag/retriever.py) — `HybridRetriever`
с BM25 + Dense + RRF, и `ChromaRetriever` с pure dense, начало на строке 515).
UI ([`src/ui/app.py:97-107`](../src/ui/app.py)) использует **только**
`ChromaRetriever`. То есть BM25-канал, который ADR-001 признал обязательным
для «точных терминов и артикулов», в живом UI-пути не работает.

Это особенно болезненно для технической документации: артикул `MNG-VATS-001`,
имя поля `sip_trunk_id`, URL `/api/v1/calls` — всё это плохо ищется
плотными векторами и хорошо — BM25.

### 2.5 Проблема №4 — отсутствие multi-hop

Один проход `retriever.search(query)` → один батч контекста → один LLM-вызов.
Если ответ на «Можно ли подключить SSO для ЛК ВАТС, если у нас Active
Directory?» требует двух разделов («Настройка SSO» **и** «Поддерживаемые
IdP»), второй раздел не будет найден, пока LLM не сформулирует подзапрос —
а такой возможности у него нет.

### 2.6 Проблема №5 — stateless UI

`src/ui/app.py` не использует `st.session_state` для истории диалога.
Каждый клик «Search KB» — независимая сессия. Пользователь не может
сказать «уточни ответ» или «а что если AD внешний?», не повторяя весь
контекст.

### 2.7 Проблема №6 — слабое grounding

Текущий system prompt в `src/ui/app.py:59-65`:

```python
"Quote source filenames in square brackets (e.g. [filename.pdf]) when you
rely on a chunk. If the context is insufficient, say so explicitly."
```

Это не обеспечивает:
- **Verifiable citations:** нет требования цитировать дословно (`"..."`).
- **Page-level / section-level granularity:** только имя файла.
- **STRICT_MODE:** нет явного перехода в «не нашёл» при пустом контексте — модель может «дорисовать» из своих весов.

### 2.8 Проблема №7 — нет метрик качества RAG

`scripts/evaluate/evaluate_quality.py` (см. `tests/test_quality.py`)
закрывает только классификационный путь (Macro-F1 по `[Статус]` против
`test_data/gold_standard.json`). Для RAG-Q&A нет ни golden set, ни метрик
faithfulness / context recall / hit rate.

### 2.9 Сводная таблица проблем

| # | Проблема | Сегодня | Влияние на KPI |
|---|----------|---------|----------------|
| P1 | Фиксированный чанкер игнорирует структуру | `chunker.py:147-169` | F1 ↓, citation precision ↓ |
| P2 | Метаданные = {source, chunk_idx} | `build_index.py:238` | citation granularity ↓ (≠95 %) |
| P3 | UI использует pure-dense, BM25-канал мёртв | `ui/app.py:97-107` vs `retriever.py:515` | Recall на терминах/артикулах ↓ |
| P4 | Нет multi-hop | one-shot in UI | Покрытие зависимых разделов ↓ |
| P5 | Stateless диалог | `ui/app.py:259-300` | UX, нельзя «уточни» |
| P6 | Поверхностное grounding | `ui/app.py:59-65` | Риск галлюцинаций |
| P7 | Нет RAG-метрик | `scripts/evaluate/` only ТЗ | Нельзя замерять регрессии |

---

## 3. Рекомендации по чанкингу (3 уровня)

Каждый «уровень» — это самостоятельный инкремент. Перейти на Уровень 2 без
Уровня 1 невозможно (нужны метаданные раздела); Уровень 3 — оптимизация
поверх Уровня 2.

### 3.1 Уровень 1 — Базовая оптимизация (`SHOULD`, ≈ 1–2 дня)

**Что меняем:**
- `chunk_size = 512`, `chunk_overlap = 64` (12.5 %).
- `MIN_CHUNK_SIZE = 384`, `MAX_CHUNK_SIZE = 768` (расширяем guardrails в `src/rag/chunker.py:32-33`).
- Включаем **section-aware preprocessing:** перед токенизацией режем по `\n#{1,6} `, `^\d+(\.\d+)+\s` (нумерованные разделы), `^\s*[A-ZА-Я][А-ЯA-Z ]{4,}$` (CAPS-заголовки PDF). Заголовок становится частью первого чанка раздела.

**Обоснование выбора:**
- Текущие 250 токенов оптимизированы под «короткие требования ТЗ» (CONCEPT §4.6) — оправдано для классификации. Для документации SaaS типичный «атомарный» раздел = 400–700 токенов; 512 ± 25 % перекрывает оба сценария.
- bge-m3 эффективно работает на чанках 256–1024 токенов (декларация авторов модели, см. [BGE-M3 paper, табл. 3](https://arxiv.org/abs/2402.03216)). 512 — sweet spot между retrieval precision и context recall.
- Overlap 12.5 % статистически достаточен для сохранения связности (см. LlamaIndex experiments report, рекомендация 10–20 %); большего не нужно, так как структурные связи мы сохраняем не через overlap, а через `parent_section` (Уровень 2).

**Конкретный патч:**
```python
# src/rag/chunker.py
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 64
MIN_CHUNK_SIZE = 384
MAX_CHUNK_SIZE = 768

# configs/embedding_config.yaml
chunk_size: 512
chunk_overlap: 64
```

**Точка боли:** меняется ширина чанка → нужно **переиндексировать ChromaDB**
с нуля (`build_index.py`). В CHANGELOG это `BREAKING (KB schema)`.

### 3.2 Уровень 2 — Parent Document Retrieval (`SHOULD`, ≈ 3–4 дня)

**Идея:** искать по «мелким» чанкам (точность поиска), возвращать «крупные»
родительские блоки (контекст для LLM).

**Двухслойная индексация:**
```
PDF → SectionExtractor → секции (~512 ток) ──► ChromaDB collection "parents"
                              │
                              └─► TokenChunker(256, 32) ──► "children"
                                  metadata = {parent_id, section_title,
                                              page_number, section_number, ...}
```

**Search flow:**
1. `child_results = children.query(query, top_k=20)`
2. `parent_ids = unique(c.metadata.parent_id for c in child_results)`
3. `parents = parents.get(ids=parent_ids[:5])`
4. Дальше LLM получает 5 родительских блоков (≈ 2500 токенов), а не 5 узких 250-токенных кусков.

**Скетч имплементации (без LangChain):**
```python
class ParentDocumentRetriever:
    def __init__(self, parents: ChromaRetriever, children: ChromaRetriever,
                 parent_top_k: int = 5, child_top_k: int = 20):
        self.parents = parents
        self.children = children
        self.parent_top_k = parent_top_k
        self.child_top_k = child_top_k

    def search(self, query: str) -> List[Dict[str, Any]]:
        child_hits = self.children.search(query, top_k=self.child_top_k)
        # сохраняем порядок «лучший родитель — первым»
        seen, parent_ids = set(), []
        for h in child_hits:
            pid = h["metadata"].get("parent_id")
            if pid and pid not in seen:
                seen.add(pid)
                parent_ids.append(pid)
            if len(parent_ids) >= self.parent_top_k:
                break
        return self.parents.fetch_by_ids(parent_ids)
```

**Зачем это нужно конкретно нам:** в MANGO OFFICE манулах раздел
«7.3.6 Настройка SSO» содержит подразделы «Active Directory», «Azure AD»,
«Условия» — точный child-chunk попадает в «Условия», но LLM нужен весь
параграф, чтобы ответить корректно.

### 3.3 Уровень 3 — Агрегация соседних чанков (`MAY`, ≈ 1–2 дня)

**Идея:** даже после Уровня 2 бывают случаи, когда смысл «растекается» на
два соседних раздела. Дешёвый трюк — после retrieval добавлять `chunk_idx ± 1`.

**Алгоритм:**
```
1. results = retriever.search(query, top_k=K)
2. for each hit h:
       neighbors = collection.get(where={
           "source": h.source,
           "chunk_idx": {"$in": [h.chunk_idx - 1, h.chunk_idx + 1]}
       })
       hits.extend(neighbors)
3. dedup by (source, chunk_idx), keep highest score, sort by chunk_idx
4. merge contiguous runs into one «context block»
```

Это не альтернатива Уровню 2, а дополнение к нему. Включается тоглом
`expand_neighbors: true` в `configs/embedding_config.yaml`.

### 3.4 Сводная таблица «3 уровней»

| Уровень | Трудозатраты | Выигрыш по recall (ожидание) | Risk |
|---------|--------------|------------------------------|------|
| L1 — 512/64 + section split | 1–2 д | +10–15 % | reindex required |
| L2 — Parent Document | 3–4 д | +15–25 % | два индекса вместо одного, дисковое место × 1.4 |
| L3 — Neighbour expansion | 1–2 д | +5–10 % | риск «разбавления» контекста; tradeoff на размер промпта |

Рекомендация — катить L1 → L2 → L3 в три последовательных PR, между ними
прогонять Golden Set (см. §7).

---

## 4. Multi-hop Retrieval Strategy

### 4.1 Когда multi-hop оправдан

Multi-hop нужен, **когда ответ на вопрос требует объединить факты из ≥ 2
разных разделов**, и при этом второй раздел невозможно найти, не сделав
первого поиска. Примеры из MANGO OFFICE-домена:

| Вопрос | Hop 1 | Hop 2 |
|--------|-------|-------|
| «Можно ли поднять SSO для ЛК ВАТС с Active Directory?» | Найти раздел «Настройка SSO» | Узнать о поддержке AD конкретно |
| «Какие лимиты на VPBX API при тарифе X?» | Найти базовый раздел лимитов | Найти исключения для тарифа X |
| «Что нужно настроить в SIP-trunk, чтобы Речевая аналитика начала писать?» | Найти раздел SIP-trunk | Найти раздел Recording в QM |

### 4.2 Архитектура «Iterative Retrieval»

```
                ┌─────────────────────────────────────┐
                │  Initial query Q₀                   │
                └─────────────┬───────────────────────┘
                              │
                              ▼
                ┌─────────────────────────────────────┐
                │  Hybrid retrieve → context C₀       │
                └─────────────┬───────────────────────┘
                              │
                              ▼
              ┌──────────────────────────────────────┐
              │  Reflection LLM call:                │
              │  «Достаточно ли C₀ для ответа?       │
              │  Если нет — какой подвопрос Q₁?»     │
              └──────────────┬───────────────────────┘
                             │
              ┌──────────────┴──────────────┐
        STOP  ▼                             ▼  CONTINUE
         (LLM «достаточно»)        Hybrid retrieve(Q₁) → C₁
                                            │
                                            ▼
                                       (повтор до N)
                                            │
                                            ▼
                                ┌────────────────────────┐
                                │  Final answer LLM call │
                                │  context = C₀ ∪ C₁     │
                                └────────────────────────┘
```

### 4.3 Параметры по умолчанию (рекомендация)

| Параметр | Значение | Обоснование |
|----------|----------|-------------|
| `max_hops` | **2** | Каждый hop = +1 LLM call. На фолбэк-цепочке `GigaChat→OpenRouter→Ollama` третий hop взрывает p95. Литература (Self-RAG, ReAct, IRCoT) сходится на 2–3. |
| `min_confidence_to_stop` | 0.8 | Если reflection-LLM отдал `{"sufficient": true, "confidence": ≥0.8}` — стоп. |
| `dedup_strategy` | by `(source, chunk_idx)` | См. `_result_key` в `retriever.py:229`. |
| `aggregation` | concat по hop с разделителем `--- HOP N ---` | LLM легче «ориентируется» в источнике. |

### 4.4 Реализационный скетч (без LangChain)

```python
class IterativeRetriever:
    def __init__(self, retriever, llm, max_hops: int = 2):
        self.retriever = retriever
        self.llm = llm
        self.max_hops = max_hops

    def answer(self, question: str) -> Tuple[str, List[Dict]]:
        context: List[Dict] = []
        history_q: List[str] = [question]

        for hop in range(self.max_hops):
            current_q = history_q[-1]
            hits = self.retriever.search(current_q, top_k=5)
            context = self._merge(context, hits)
            reflection = self.llm.generate_rag_response(
                system_prompt=REFLECTION_PROMPT,
                user_prompt=_format(current_q, context),
            )
            decision = _parse_reflection(reflection)  # {sufficient, follow_up}
            if decision["sufficient"]:
                break
            history_q.append(decision["follow_up"])

        answer = self.llm.generate_rag_response(
            system_prompt=ANSWER_PROMPT, user_prompt=_format(question, context)
        )
        return answer, context
```

`REFLECTION_PROMPT` хранится в `prompts/system_rag_reflection_v1.md` —
шаблон в §5.

### 4.5 Альтернативы (когда лучше НЕ multi-hop)

| Подход | Когда выбрать | Когда НЕ выбрать |
|--------|---------------|------------------|
| **Query Expansion** (3–5 синонимических переформулировок до поиска) | Вопросы с терминологическими вариациями («ВАТС / VPBX») | Вопросы, требующие СВЯЗИ двух разделов |
| **HyDE** (LLM генерит гипотетический ответ → им ищем) | Узкие технические термины, по которым в KB точная цитата | Когда KB маленькая (gallop hallucinations) |
| **Step-back Prompting** | «Сначала найди концепцию, потом детали» | Когда вопрос уже узкий и атомарный |

**Наша ставка для P0:** одна итерация `Query Expansion` (дешёвая,
синхронная) **+** опциональный `max_hops=2` под флагом `MULTIHOP_ENABLED`.
HyDE откладываем — для нашей KB (66.7 МБ, 11 PDF) точность hybrid + parent
retrieval должна быть достаточной без галлюцинаций.

---

## 5. Стратегия метаданных

### 5.1 Целевая схема для ChromaDB

ChromaDB хранит `metadata: dict[str, str | int | float | bool]` рядом с
embedding. Целевая схема:

```json
{
  "source_file": "LK_manual_v-119_compressed.pdf",
  "page_number": 142,
  "section_title": "7.3.6 Настройка SSO",
  "section_number": "7.3.6",
  "parent_section": "7.3 Безопасность",
  "depth": 3,

  "chunk_idx": 87,
  "parent_id": "LK_manual_v-119_compressed.pdf::7.3.6",
  "char_start": 412,
  "char_end": 924,

  "product": "LK_VATS",
  "version": "1.19",
  "content_type": "configuration",
  "audience": "admin",

  "has_prerequisites": true,
  "has_dependencies": true,
  "related_sections": "7.3.5;9.2.1"
}
```

> ⚠️ ChromaDB ограничивает значения скалярами. `related_sections` хранится
> как `;`-разделённая строка, не как список. См. [ChromaDB docs — Metadata](https://docs.trychroma.com/docs/collections/manage-collections#using-metadata-when-adding-collections).

### 5.2 Категоризация по приоритету

| Поле | Приоритет | Где извлекать |
|------|-----------|---------------|
| `source_file`, `chunk_idx` | P0 (уже есть) | `build_index.py:238` |
| `page_number` | P0 | `pypdf.PdfReader().pages[i]` — индекс страницы доступен в цикле |
| `section_title`, `section_number` | P0 | Regex по началу разделов + heuristic «CAPS заголовок» |
| `parent_section`, `depth` | P1 | Стек разделов в один проход по тексту |
| `product` | P1 | Mapping по `source_file` (LK_manual* → `LK_VATS`, QM_manual* → `QM`, и т.д.) |
| `version` | P1 | Regex по имени файла (`v-119` → `1.19`) |
| `content_type` | P2 | Few-shot LLM classification offline-этап (раз в индексацию, не онлайн) |
| `audience` | P2 | Аналогично — offline LLM heuristic |
| `has_prerequisites`, `has_dependencies` | P2 | Regex по `\b(предварительные условия|необходимо|зависит от|см\. раздел)\b` |
| `related_sections` | P2 | Regex по `см\.\s*(?:раздел|п\.|пункт)\s*(\d+(?:\.\d+)+)` |

### 5.3 Как извлекать (3 техники, скомбинировать)

1. **Regex / эвристики (cheap, deterministic).** Подходят для всех структурных
   полей, кроме `content_type` / `audience`.
2. **Page-aware PDF parser.** Заменить «склейку всех страниц» в
   `build_index.py:113` на:
   ```python
   for page_num, page in enumerate(reader.pages, start=1):
       text = page.extract_text() or ""
       yield {"text": text, "page_number": page_num}
   ```
   Чанкер должен принимать поток «секций со страницами», а не сплошную строку.
3. **Offline LLM enrichment (один прогон на индексацию).** Только для
   `content_type` и `audience`. Бюджет: 1 GigaChat-запрос на родительский
   блок × ~500 родителей = ~500 запросов на reindex. Это часы, не минуты.

### 5.4 Использование метаданных при поиске

| Сценарий | Реализация |
|----------|-----------|
| «Только ЛК ВАТС» | `where={"product": "LK_VATS"}` в `collection.query()` |
| «Только инструкции, без troubleshooting» | `where={"content_type": "instruction"}` |
| Бустинг свежей версии | post-filter: добавить ε к score, если `version == latest_for_product[product]` |
| Точная цитата | `[LK_manual_v-119_compressed.pdf, стр. 142, §7.3.6 «Настройка SSO»]` — собирается из метаданных при рендере |

### 5.5 Совместимость с существующим индексом

Существующая коллекция `clarify_engine_kb` не имеет нужных полей. Варианты:

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| Полный reindex | Чистая схема | Время и риск регрессий |
| Backfill metadata (`collection.update()`) | Без потери эмбеддингов | ChromaDB `update` лимитирован, придётся batching |

**Рекомендация:** полный reindex. Корпус маленький (66.7 МБ × bge-m3 ≈ 20 мин
на CPU). Не стоит сложности backfill.

---

## 6. Многоходовый диалог и память

### 6.1 Минимально работающий вариант (P0, ≈ 1 день)

`st.session_state` — встроенный механизм Streamlit, не требует Redis/SQLite.

```python
# src/ui/app.py
if "history" not in st.session_state:
    st.session_state.history = []  # list[dict(role, content, chunks)]

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Спросите про KB…"):
    st.session_state.history.append({"role": "user", "content": prompt})
    chunks = search_kb(prompt, settings["top_k"])
    answer = client.generate_rag_response(
        SYSTEM_PROMPT,
        build_user_prompt_with_history(prompt, chunks, st.session_state.history),
    )
    st.session_state.history.append({"role": "assistant", "content": answer,
                                     "chunks": chunks})
```

### 6.2 Стратегия обрезки истории

| Стратегия | Когда применять | Реализация |
|-----------|------------------|------------|
| **Last-N** (N=6 пар) | По умолчанию | Срез `history[-12:]` |
| **Sliding window по токенам** | Когда чат длинный | Считать токены bge-m3 tokenizer, держать ≤ 2000 |
| **Summarization** | Когда история > 20 пар | LLM-summary в `system_history` сообщение |

Рекомендация — Last-6 + autosummarization после 12-й пары (триггер на длину).

### 6.3 Хранилище

| Хранилище | Когда | Скоро ли в MVP |
|-----------|-------|-----------------|
| `st.session_state` (RAM процесса) | Single-user UI testing | ✅ P0 |
| SQLite (`data/sessions.db`) | Multi-session, persistence между перезапусками | P1 |
| Redis | Multi-user / multi-instance | P2, не нужен на пилоте |

### 6.4 Гарантии резидентности

История диалога — потенциально содержит PII (имена БА, имена клиентов).
Перед каждым LLM-вызовом она должна проходить через `mask_text` (см.
`src/llm/masking.py`). Сейчас `generate_rag_response` маскирование **не
применяет** (в отличие от `classify_requirement`). Это — отдельная
рекомендация:

> **MUST (P0):** добавить опциональное маскирование `mask=True` в
> `LLMClient.generate_rag_response` и включить по умолчанию в UI.

---

## 7. Валидация, цитирование и Grounding

### 7.1 STRICT_MODE

Целевое поведение:
- Если `len(context_chunks) == 0` → ответ автоматически
  `«В базе знаний не найдено информации, отвечающей вопросу. Уточните запрос или см. SOURCES_MANIFEST.md.»` Никакого LLM-вызова.
- Если retrieval вернул чанки, но LLM не смог процитировать → пометить ответ
  баннером «⚠️ Ответ не подтверждён цитатами» (см. §7.3 Faithfulness-check).

Реализация: переменная окружения `STRICT_RAG_MODE=true` (по умолчанию `true`
в проде, `false` в `use_test_data_mode`).

### 7.2 Кликабельные цитаты

Целевой формат в ответе:

> Для включения SSO необходимо настроить IdP в разделе **Безопасность →
> SSO** ([LK_manual v1.19, стр. 142, §7.3.6]).

В Streamlit:
```python
url = f"file://{abspath('knowledge_base/sources/' + source)}#page={page}"
markdown_link = f"[{source}, стр. {page}, §{section_number}]({url})"
```

> ⚠️ `file://` работает только когда PDF доступен на той же машине, где
> запущен браузер. Для пилота на сервере нужен альтернативный путь:
> загрузить PDF в S3-совместимое хранилище или Streamlit-static `serve`.

### 7.3 Faithfulness check (post-generation)

Простейшая проверка без RAGAS:

```python
def faithfulness_check(answer: str, chunks: list[dict],
                       min_overlap: int = 8) -> bool:
    """Считает, что ответ «обоснован», если ≥ N токенов любой длинной фразы
    из ответа дословно содержатся в одном из чанков."""
    answer_ngrams = _ngrams(_tokenize(answer), n=min_overlap)
    chunk_text = " ".join(c["text"] for c in chunks)
    return any(ng in chunk_text for ng in answer_ngrams)
```

Это «дешёвая» проверка для тревоги в UI. «Дорогая» проверка через LLM-as-a-judge
выносится в §8 (evaluation).

### 7.4 Обновлённый system prompt (черновик `prompts/system_rag_v1.md`)

```
Ты — ассистент Clarify Engine для технической документации MANGO OFFICE.

Правила:
1. ОТВЕЧАЙ ТОЛЬКО ПО КОНТЕКСТУ. Если контекста недостаточно — скажи это явно
   и предложи уточнить запрос. Никогда не используй знания из обучения.
2. ЦИТИРУЙ КАЖДОЕ УТВЕРЖДЕНИЕ. Формат:
   «… утверждение … [source.pdf, стр. N, §X.Y.Z]».
3. Если в контексте есть «См. раздел X.Y» — не выдумывай его содержание,
   скажи: «требуется уточнить в разделе X.Y».
4. Если контекст противоречив — перечисли оба варианта с цитатами.
5. Формат ответа — Markdown, на языке вопроса. Технические термины не переводи.
```

---

## 8. Оценка качества (RAG Evaluation)

### 8.1 Golden Set

| Параметр | Значение |
|----------|----------|
| Размер | 30–50 Q/A для пилота, целевые 150 для пред-релиза |
| Файл | `test_data/rag_golden_set.json` |
| Схема | `{question, expected_answer, expected_sources: [{source, section}], category}` |
| Категории | `factual`, `procedural`, `cross_doc`, `troubleshooting`, `negative` (вопросы, на которые KB не отвечает) |

### 8.2 Метрики

| Метрика | Формула / способ | Целевое |
|---------|------------------|---------|
| **Hit Rate@K** | Доля Q, где хотя бы один `expected_sources[i].source` в top-K retrieved | ≥ 0.85 @ K=5 |
| **MRR** | mean(1/rank первого совпавшего источника) | ≥ 0.6 |
| **Context Recall** | Доля `expected_sources`, попавших в top-K | ≥ 0.75 |
| **Faithfulness** | LLM-judge: «Подтверждён ли каждый факт ответа цитатами?» | ≥ 0.9 |
| **Answer Relevance** | LLM-judge: «Отвечает ли ответ на вопрос?» | ≥ 0.85 |
| **Negative Rejection Rate** | Доля Q категории `negative`, на которые ассистент ответил «не нашёл» | ≥ 0.95 |

### 8.3 Инструментарий

- **Не зависим от RAGAS-пакета** (избегаем тяжёлой зависимости). Реализуем
  Hit Rate / MRR / Context Recall чистым Python — это десятки строк.
- LLM-judge (Faithfulness, Answer Relevance) — отдельный вызов GigaChat /
  OpenRouter с детерминированным prompt.

### 8.4 Автоматизация

`scripts/evaluate/evaluate_rag.py` (новый, рядом с `evaluate_quality.py`):

```bash
python scripts/evaluate/evaluate_rag.py \
    --golden test_data/rag_golden_set.json \
    --top-k 5 \
    --report reports/rag_$(date +%F).json
```

CI: добавить отдельный job `rag-eval-smoke` на маленьком подмножестве (5 Q),
который должен укладываться в < 2 минут с stub-LLM.

---

## 9. Ollama: локальная оптимизация

### 9.1 Выбор модели

Целевые семейства (исключая lock-in на одного вендора):

| Модель | Плюсы | Минусы | Когда |
|--------|-------|--------|-------|
| `qwen2.5:7b-instruct-q4_K_M` | Хорош на русском, ≈ 4.7 ГБ RAM | Менее «креативен» на свободных вопросах | **По умолчанию для нашего домена** |
| `llama3.1:8b-instruct-q4_K_M` | Сильное reasoning, ≈ 5.4 ГБ | Слабее в чисто русских заголовках | Reasoning-heavy multi-hop |
| `deepseek-r1:8b-distill-q4_K_M` | Reasoning-traces | Длинные ответы, нужен post-process | Только для off-UI bench |
| `phi-3.5-mini-instruct-q4_K_M` | 3.8 ГБ, быстрый на CPU | Слабее на узких технических доменах | Только fallback |

**Дефолт — `qwen2.5:7b-instruct-q4_K_M`** (см. `src/llm/client.py:52`,
сейчас уже `qwen2.5:7b` — нужно уточнить квантование явно).

### 9.2 Квантование

| Квант | RAM (для 7B) | Качество (rel. fp16) | Когда |
|-------|--------------|----------------------|-------|
| `q4_K_M` | ~4.5 ГБ | ≈ 98 % | По умолчанию |
| `q5_K_M` | ~5.7 ГБ | ≈ 99 % | Если ноут позволяет |
| `q3_K_L` | ~3.5 ГБ | ≈ 94 % | Только если жмёт RAM |
| `q8_0` | ~7.6 ГБ | ≈ 99.5 % | Сервер с ≥ 16 ГБ |

### 9.3 Асинхронная очередь

Текущий `_call_ollama_rag` (`client.py:641-695`) — синхронный POST. Для UI с
одним пользователем это нормально, но при росте сценариев (evaluate_rag.py
прогоняет 50 Q подряд) синхрон бьёт по wall-clock.

Минимальный паттерн (без `asyncio` рефакторинга всего клиента):

```python
from concurrent.futures import ThreadPoolExecutor

class OllamaBatchRunner:
    def __init__(self, max_workers: int = 4):
        self.pool = ThreadPoolExecutor(max_workers=max_workers)

    def run_batch(self, prompts: list[tuple[str, str]],
                  caller, config) -> list[str]:
        futures = [self.pool.submit(caller, sp, up, config)
                   for sp, up in prompts]
        return [f.result() for f in futures]
```

`max_workers = 4` подобрано под однопроцессорный Ollama (он сам сериализует
GPU-вычисление). Для CPU-only хостов лучше `max_workers = 2`.

### 9.4 KV-cache и `num_ctx`

Установить в env / конфиге провайдера:

```yaml
providers:
  ollama:
    model: "qwen2.5:7b-instruct-q4_K_M"
    options:
      num_ctx: 4096          # достаточно для multi-hop concat
      num_thread: 0          # auto = все ядра
      keep_alive: "10m"      # держим модель в RAM между запросами
      temperature: 0.1
```

`keep_alive: 10m` — критично: иначе Ollama выгружает модель из RAM через
5 минут idle, и следующий вызов ждёт ~30 с на загрузку.

---

## 10. Prompt Library

### 10.1 Структура `prompts/`

```
prompts/
├── system_classifier_v1.0.md           ← уже есть (для ТЗ-классификации)
├── system_rag_v1.md                    ← новый (см. §7.4)
├── system_rag_reflection_v1.md         ← новый (multi-hop reflection)
├── system_rag_query_expansion_v1.md    ← новый (query expansion)
├── system_rag_evaluator_v1.md          ← новый (LLM-as-judge)
└── prompt_changelog.md                 ← уже есть, обновляем
```

### 10.2 `system_rag_reflection_v1.md` (черновик)

```
Роль: Ты — модератор RAG-цикла. Тебе дан вопрос пользователя и
накопленный контекст из нескольких поисков.

Задача:
1. Оцени, достаточно ли контекста для прямого, точного и цитируемого ответа.
2. Если ДА — верни {"sufficient": true, "follow_up": null, "confidence": x}.
3. Если НЕТ — сформулируй ОДИН подвопрос, который заполнил бы пробел.
   Верни {"sufficient": false, "follow_up": "...", "confidence": x}.

Правила:
- НЕ отвечай на вопрос. Только решай, нужен ли ещё один поиск.
- Подвопрос должен быть конкретным и searchable, не «расскажи больше».
- confidence — твоя уверенность в решении (0.0–1.0).
- Формат — строго JSON, без markdown.
```

### 10.3 `system_rag_query_expansion_v1.md` (черновик)

```
Роль: Эксперт по технической документации MANGO OFFICE.
Сгенерируй 3 переформулировки вопроса для векторного поиска.

Правила:
1. Сохрани семантику исходного вопроса.
2. Замени синонимы (ВАТС / VPBX, аналитика / QM, …).
3. Добавь технические термины, если в исходном вопросе бытовая речь.
4. Формат — JSON array из 3 строк.
```

---

## 11. Архитектура целевого пайплайна

```
┌────────────────────────────────────────────────────────────┐
│                   Streamlit Chat UI                         │
│  st.session_state.history (Last-N + summarization)          │
└─────────────────────────────┬──────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────┐
│            Query Expansion (1 LLM call, optional)           │
│            -> [Q, Q', Q''] (3 переформулировки)             │
└─────────────────────────────┬──────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────┐
│                Hybrid Retrieval (BM25 + Dense + RRF)        │
│  - children collection (256/32), top_k=20                   │
│  - dedup, RRF k=60                                          │
└─────────────────────────────┬──────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────┐
│           Parent Document Expansion                         │
│  - children → parent_id → parents collection                │
│  - top 5 parent chunks (≈ 2500 tok)                         │
└─────────────────────────────┬──────────────────────────────┘
                              │
                              ▼
            ┌─────────────────┴──────────────────┐
            │  Reflection LLM (sufficient?)      │  ── loop 0..max_hops
            └─────────────────┬──────────────────┘
                  STOP ▼           CONTINUE ▼
                       │              (follow_up Q₁ → back to Hybrid)
                       ▼
┌────────────────────────────────────────────────────────────┐
│        Final Answer LLM (GigaChat → OpenRouter → Ollama)    │
│        STRICT_MODE, mask_text=true, цитирование по         │
│        формату «[source.pdf, стр. N, §X.Y]».                │
└─────────────────────────────┬──────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────┐
│           Faithfulness Check (lightweight n-gram)           │
│  ⚠️  баннер, если ни одна фраза ответа не найдена в чанках │
└────────────────────────────────────────────────────────────┘
```

---

## 12. Рекомендации (Roadmap)

### 12.1 Доработки

| # | Приоритет | Рекомендация | Обоснование | Усилия |
|---|-----------|--------------|-------------|--------|
| 1 | **MUST (P0)** | Включить BM25-канал в production UI: переключить `src/ui/app.py:99` на `HybridRetriever` с подключением к Chroma | ADR-001 требует hybrid; pure-dense теряет recall на артикулах / терминах | S (1 д) |
| 2 | **MUST (P0)** | Расширить метаданные: `page_number`, `section_title`, `section_number`, `product` (см. §5) | Без этого нельзя выполнить требование цитируемости ≥ 95 % | M (2–3 д) |
| 3 | **MUST (P0)** | Добавить маскирование в `LLMClient.generate_rag_response` и включить в UI по умолчанию | Резидентность данных (CONCEPT §5) — сейчас RAG-канал течёт | S (0.5 д) |
| 4 | **MUST (P0)** | STRICT_MODE для пустого retrieval (короткий ответ «не нашёл» без LLM-вызова) | Прямая защита от галлюцинаций | S (0.5 д) |
| 5 | **MUST (P0)** | Golden Set ≥ 30 Q/A в `test_data/rag_golden_set.json` + `scripts/evaluate/evaluate_rag.py` (Hit Rate@K, MRR, Context Recall) | Без метрик невозможно валидировать изменения | M (2 д) |
| 6 | **SHOULD (P1)** | Chunker L1: chunk_size=512, overlap=64, section-aware split | Базовая оптимизация под раздел SaaS-документации | S (1 д) |
| 7 | **SHOULD (P1)** | Parent Document Retrieval (L2) | Закрывает фрагментацию контекста | L (3–4 д) |
| 8 | **SHOULD (P1)** | `st.session_state` для истории + Last-6 + auto-summarization | Минимальный диалоговый UX | S (1 д) |
| 9 | **SHOULD (P1)** | Prompt library: `system_rag_v1.md`, `system_rag_reflection_v1.md`, `system_rag_query_expansion_v1.md` | Структурированное хранение промптов, версионирование | S (1 д) |
| 10 | **SHOULD (P1)** | Кликабельные цитаты `[source.pdf, стр. N, §X.Y]` в UI | Прямая поддержка KPI «цитируемость» | S (0.5 д) |
| 11 | **MAY (P2)** | Multi-hop iterative retrieval (max_hops=2) под флагом `MULTIHOP_ENABLED` | Помогает на cross-doc вопросах, но удорожает p95 | M (2 д) |
| 12 | **MAY (P2)** | Query Expansion (3 переформулировки) | Дешёвый прирост recall | S (1 д) |
| 13 | **MAY (P2)** | Семантические метаданные (`content_type`, `audience`) через offline LLM enrichment | Лучшее фильтрование и бустинг | M (2–3 д) |
| 14 | **MAY (P2)** | Neighbour expansion (L3) | Полезно в граничных случаях, риск разбавления контекста | S (1 д) |
| 15 | **MAY (P2)** | Faithfulness LLM-as-judge в evaluate_rag.py | Метрика «честности» ответа | S (1 д) |
| 16 | **MAY (P2)** | Ollama: явное квантование + `keep_alive` + ThreadPoolExecutor batch | Ускорение eval-прогонов | S (1 д) |

### 12.2 План спринтов (предложение)

| Спринт | Содержимое | Выход |
|--------|-----------|-------|
| Sprint 1 (1 нед) | #1, #2, #3, #4, #5 | UI на hybrid + базовые метаданные + Golden Set + первые метрики |
| Sprint 2 (1 нед) | #6, #7, #8, #9, #10 | L1+L2 chunker, диалог, prompt library, кликабельные цитаты |
| Sprint 3 (1 нед) | #11, #12, #15, #16 | Multi-hop, query expansion, LLM-judge, Ollama-tuning |
| Sprint 4 (по запросу) | #13, #14 | Семантические метаданные, neighbour expansion |

---

## 13. Открытые вопросы

1. **Кому подчинены параметры по умолчанию?** `chunk_size=512` — это
   «инвазивное» изменение для уже индексированной коллекции. Согласуем
   reindex-окно с PO?
2. **Каков бюджет на инференс GigaChat-tokens?** Multi-hop x 2 + reflection
   = +2 LLM-вызова на каждый user-запрос. Это до × 3 по токенам.
3. **PDF-доступ для кликабельных цитат на сервере пилота.** `file://` не
   подходит — нужен Streamlit `serve` или S3-bucket. Кто провисит infra?
4. **Где хранить Golden Set?** Сейчас `test_data/` пустой для RAG. Заполнять
   вручную (БА × 2) или сгенерировать LLM-черновик и валидировать?
5. **Стоит ли вообще включать `MULTIHOP_ENABLED` по умолчанию на пилоте?**
   Тradeoff: +recall vs +latency и +cost. Рекомендация — оставить флагом
   `false`, включать вручную в UI.

---

## 14. Что не вошло в этот документ (Out of scope)

- **Switch на другой vector store** (Qdrant, Weaviate) — ADR-001 явно
  закрепил ChromaDB; смена требует нового ADR.
- **Reranking с cross-encoder** (e.g. `bge-reranker-v2-m3`) — потенциально
  «следующий шаг» после Parent Retrieval, но не вписан в P0–P2 для
  пилота (требует ещё одной модели в RAM ~2 ГБ).
- **GraphRAG / Knowledge Graph** — слишком тяжёлый для 11 PDF, не
  оправдан ROI.
- **Fine-tuning embedding model.** bge-m3 уже multilingual; затраты на
  fine-tune несоизмеримы с выигрышем на корпусе 66.7 МБ.
- **Streaming-ответы** в UI — оптимизация UX, не RAG-качества; отдельный
  бэклог.

---

## 15. История изменений

| Версия | Дата | Изменение |
|--------|------|-----------|
| v1 | 2026-05-16 | Первая версия: диагностика, 3 уровня chunking, multi-hop strategy, metadata schema, dialog memory, grounding, evaluation, Ollama-tuning, roadmap по 16 пунктам в трёх спринтах (issue #75). |
