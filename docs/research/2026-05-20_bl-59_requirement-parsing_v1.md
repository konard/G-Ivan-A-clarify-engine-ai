# 🔬 Research: Requirement Atomization & Document Structure Recognition (BL-59)

## Метаданные
- **Дата:** 2026-05-20
- **Версия:** v1
- **Автор:** konard (AI issue solver, по [issue #211](https://github.com/G-Ivan-A/clarify-engine-ai/issues/211))
- **Статус:** Draft → готов к ревью PO
- **Спринт:** Sprint 5 — Pilot Readiness & Advanced Parsing
- **Связанный backlog:** новая ветка `BL-59` для следующей редакции
  [`docs/backlog/2026-05-17_backlog_rag-optimization_v1.5.md`](../backlog/2026-05-17_backlog_rag-optimization_v1.5.md).
- **Депенденс:** `BL-57` (Retrieval Architecture Research),
  `BL-41` (UI Refactor — отображение `[Ref]`),
  `BL-45` (ARM Runbook — тестовая среда).
- **Связанные документы:**
  - [`src/parsers/docx_parser.py`](../../src/parsers/docx_parser.py) — текущая (наивная) реализация атомизации.
  - [`src/parsers/excel_parser.py`](../../src/parsers/excel_parser.py) — текущая реализация для `.xlsx`/`.xls`.
  - [`scripts/tools/enrich_docx_structure.py`](../../scripts/tools/enrich_docx_structure.py) — пост-парсинговый LLM-обогатитель (BL-31).
  - [`configs/parsing_config.yaml`](../../configs/parsing_config.yaml) — конфигурация парсеров (расширяется в этой задаче).
  - [`docs/standards/export-markup.md`](../standards/export-markup.md) — контракт `[Ref]` (`§3`).
  - [`docs/analysis/2026-05-17_analysis_tz-structure_samples.md`](../analysis/2026-05-17_analysis_tz-structure_samples.md) — анализ структуры реальных ТЗ.

---

## 1. Executive Summary

Текущий пайплайн извлечения требований (`DocxParser`, `ExcelParser`) использует
наивное разбиение по абзацам/ячейкам/строкам без учёта структурного контекста.
Это приводит к четырём систематическим проблемам, документально подтверждённым
в [issue #211](https://github.com/G-Ivan-A/clarify-engine-ai/issues/211):
гипер-атомизация, потеря заголовков/перекрёстных ссылок, ложный
`empty_context → НД`, неинформативный `[Ref]`.

Исследование рассматривает четыре класса решений и завершается рекомендацией
гибридного подхода:

| Подход | Сильные стороны | Слабые стороны | Применимость BL-59 |
|--------|------------------|----------------|--------------------|
| **(A) Layout-aware парсеры** (Unstructured.io, Docling, PyMuPDF) | Готовая поддержка таблиц/заголовков/списков; модели предобучены на тендерных документах | Тяжёлые ML-зависимости (≥1 GiB); требуют GPU/высокого CPU; нарушают NFR-04 (RU-резидентность) при онлайн-моделях | ❌ Избыточно для пилотного АРМ |
| **(B) Semantic chunking** (LangChain `SemanticChunker`, LlamaIndex SentenceWindow) | Учитывает семантическую близость; устраняет «обезглавленные» фрагменты | Требует эмбеддинг-модель в процессе парсинга (двойная стоимость); сложно валидировать детерминистично | ⚠️ Полезно для постобработки, не для границ |
| **(C) Rule-based структурный анализ** (XPath по DOCX, регулярки нумерации, отступы) | Детерминистично, тестируемо, CPU-only, 0 внешних зависимостей; легко аудируется | Хрупкость к нестандартной разметке; покрытие edge-cases растёт линейно | ✅ **Базовый слой BL-59** |
| **(D) LLM-валидация границ** (qwen2.5:7b через Ollama) | Понимает семантику; ловит «непрерывное требование, разорванное парсером»; работает офлайн | Замедляет парсинг (+10–30 сек на документ); требует prompt-инжиниринга и кэширования | ✅ **Опциональный слой BL-59** (toggle, off-by-default) |

**Рекомендация:** двухслойный гибрид:

- **Слой 1 (MUST, default):** `RequirementBoundaryDetector` — детерминистичный
  структурный анализ поверх существующих парсеров. Распознаёт заголовки
  разделов, нумерацию, перекрёстные ссылки, наследует контекст в дочерние
  фрагменты, объединяет «оборванные» абзацы.
- **Слой 2 (SHOULD, opt-in):** LLM-валидация границ через локальный
  `qwen2.5:7b` (Ollama). Активируется флагом
  `parsing.use_llm_boundary_check: true` для документов, где Слой 1 даёт
  неуверенные границы (например, плотные таблицы со смешанной нумерацией).

Дизайн сохраняет публичный контракт `load_requirements_by_extension`
(`[{id, text, locator}]`), что гарантирует backward compat для `ExportRouter`
и `Pipeline`.

---

## 2. Постановка задачи и текущее состояние

### 2.1. Контракт «до» (наивный)

`DocxParser.load_requirements(path)` возвращает список
`[{id, text, locator}]`, где локатор имеет одну из форм:

```json
{"type": "paragraph", "index": 12}
{"type": "table", "table": 1, "row": 6, "col": 3, "paragraph": 98}
{"type": "cell", "sheet_name": "Sheet1", "row": 7, "column": "Требование"}
```

**Атомизация — один абзац / одна ячейка → одно требование.** Никакого
структурного контекста (заголовок раздела, нумерация, перекрёстные ссылки)
в локаторе нет. Это и есть корень проблемы.

### 2.2. Контракт «после»

`load_requirements_by_extension(path)` сохраняет ту же сигнатуру и тип
возврата, но локатор обогащается опциональными полями:

```json
{
  "type": "table",
  "table": 1,
  "row": 6,
  "col": 3,
  "paragraph": 98,
  "section_number": "7.2.39",
  "section_title": "Функциональные требования / Статистика реального времени",
  "parent_id": 42,
  "cross_refs": ["7.4", "9.1"],
  "block_type": "requirement",
  "span": ["para98", "para99", "para100"]
}
```

Гарантии:
1. **Backward compat.** Все исходные ключи локатора сохраняются. Новые ключи
   добавляются только если структурная информация распознана.
2. **Стабильность `[Ref]`.** Поле локатора, по которому строится `[Ref]`
   (см. [`docs/standards/export-markup.md`](../standards/export-markup.md) §3),
   остаётся неизменным; `section_number` добавляется в `[Ref]` как
   человекочитаемая надстройка, не заменяя машинный путь.
3. **Контракт `[{id, text, locator}]` сохранён.** `ExportRouter` (FR-06) не
   требует правок.

---

## 3. Сравнение библиотек и подходов

### 3.1. Layout-aware DOCX-парсеры

| Библиотека | Лицензия | Размер | Поддержка таблиц | Headings detection | Применимость |
|------------|----------|--------|------------------|---------------------|---------------|
| `python-docx` | MIT | ~1 MiB | Базовая (через `tables`) | Только по стилю `Heading N` | ✅ **Уже используется**, минимально достаточно для structural-слоя |
| `unstructured` | Apache-2.0 | ~150 MiB + ML deps | Хорошая | Хорошая, но требует sentence-transformers | ❌ Избыточные зависимости |
| `docling` (IBM) | MIT | ~500 MiB с моделями | Отличная, layout-aware | Отличная, ML-based | ❌ Требует GPU для скорости; nfr-04 |
| `lxml` + XPath | BSD | ~5 MiB | Полный доступ к OOXML | Через CSS-классы / `w:pStyle` | ✅ **Дополняет** `python-docx` для тонкого извлечения нумерации |

**Решение:** остаёмся на `python-docx`; точечно используем `lxml` через уже
загруженный `python-docx` API (`paragraph._element`, `paragraph.style`) для
извлечения нумерации списков и стилей заголовков. Не добавляем тяжёлых
зависимостей (NFR-04, NFR-08 — RU-резидентность и CPU-only).

### 3.2. Semantic chunking подходы

| Подход | Идея | Применимость в BL-59 |
|--------|------|----------------------|
| LangChain `SemanticChunker` | Эмбеддинг каждого предложения → разбиение по «семантическим перепадам» | ❌ Эмбеддинг внутри парсера дублирует BL-32 |
| LlamaIndex `SentenceWindowNodeParser` | Окно из N предложений вокруг каждого | ⚠️ Полезно для retrieval, не для атомизации |
| Hierarchical chunking (parent-child retention) | Сохранение родительских блоков для каждого чанка | ✅ **Используем концепцию** через `parent_id` в локаторе |

**Решение:** не вводим эмбеддинг-зависимости в парсер. Концепция
`parent_id` (заголовок раздела → требование) реализуется детерминистично
через rule-based слой.

### 3.3. Rule-based boundary detection

Базовая эвристика, отработанная в индустрии для тендерной документации:

1. **Распознавание заголовков:**
   - Стиль `Heading 1..6` (через `python-docx` style API).
   - Регулярное выражение `^(\d+(?:\.\d+)*)\s+(.+)` для нумерованных секций.
   - Текст в CAPS длиной 5–60 символов без точки в конце.
2. **Распознавание атомарных требований:**
   - Совпадение с шаблоном `^\d+(?:\.\d+)+\s+.{50,}` (нумерация + длинный текст).
   - Наличие модальных глаголов `должен`, `должны`, `обеспечить`,
     `поддерживать`, `предоставлять`, `позволять`, `иметь` (BL-22/BL-27).
3. **Распознавание продолжений (continuation):**
   - Абзац без маркера/нумерации сразу после требования.
   - Если предыдущий блок заканчивается на `:`/`;` — высокая вероятность
     продолжения списка/требования.
4. **Перекрёстные ссылки:**
   - Регулярки: `см\.?\s*(?:п\.?|пункт|раздел)\s*(\d+(?:\.\d+)*)`,
     `согласно\s*п\.?\s*(\d+(?:\.\d+)*)`.

### 3.4. LLM-assisted boundary validation

Промпт-стратегия для `qwen2.5:7b` (Ollama):

```
Ты — структурный анализатор тендерных требований. Получи JSON с фрагментами
парсера. Для каждого фрагмента ответь:
{
  "fragment_id": int,
  "is_complete_requirement": bool,
  "merge_with": [int],  // индексы соседних фрагментов для объединения
  "section_number": string | null,
  "reason": string  // 1 предложение
}
Не выдумывай содержание. Если не уверен — оставь как есть.
```

**Кэширование:** sha256(текст блока + контекст) → результат. Хранится в
`data/cache/parsing/`. Инвалидация — при изменении промпта или модели.

**Тайм-аут:** 10 сек на блок, общий лимит 30 сек на документ. При превышении
— fallback на rule-based результат (Слой 1).

---

## 4. Архитектурное решение

### 4.1. Контракт `RequirementBoundaryDetector`

```python
class RequirementBoundaryDetector:
    """
    Apply structural boundary detection to raw parser candidates.

    Input:  List[{"id": int, "text": str, "locator": dict}]
    Output: List[{"id": int, "text": str, "locator": dict}]
            (с обогащённым locator)
    """

    def refine(self, raw_blocks: list[dict]) -> list[dict]: ...
```

Стратегии:
- `naive` — pass-through (текущее поведение).
- `structural` — rule-based merge + context propagation.
- `hybrid` — `structural` + опциональный LLM-чек (по
  `use_llm_boundary_check`).

### 4.2. Интеграция с парсерами

`src/parsers/__init__.py::load_requirements_by_extension(path)`:
1. Запустить базовый парсер (`DocxParser` или `ExcelParser`) — получить raw
   `[{id, text, locator}]`.
2. Загрузить `RequirementBoundaryDetector(config)` из
   `configs/parsing_config.yaml::parsing`.
3. Вернуть `detector.refine(raw_blocks)`.

Backward compat достигается тем, что `strategy: naive` возвращает
исходный список без изменений (с переприсвоением `id` для непрерывности).

### 4.3. Конфигурация `configs/parsing_config.yaml`

```yaml
parsing:
  strategy: "structural"           # naive | structural | hybrid
  use_llm_boundary_check: false    # активирует Слой 2 (Ollama qwen2.5:7b)
  llm_model: "qwen2.5:7b"
  max_context_window_chars: 4000
  min_requirement_length: 50
  preserve_original_fragments: true  # debug: исходные фрагменты в locator.span
  requirement_verbs:
    - "должен"
    - "должны"
    - "должна"
    - "должно"
    - "обеспеч"
    - "поддерж"
    - "предостав"
    - "позвол"
    - "иметь"
    - "выполн"
  section_number_pattern: '^(\d+(?:\.\d+)*)\s*\.?\s*(.+)'
  cross_ref_patterns:
    - 'см\.?\s*(?:п\.?\s*|пункт\s*|раздел\s*)?(\d+(?:\.\d+)+)'
    - 'согласно\s*п\.?\s*(\d+(?:\.\d+)*)'
```

### 4.4. Контракт обогащённого локатора

```python
locator = {
    # Исходные поля (backward compat):
    "type": "paragraph" | "table" | "cell",
    "index": int,         # для paragraph
    "table": int, "row": int, "col": int, "paragraph": int,  # для table
    "sheet_name": str, "row": int, "column": str,            # для cell

    # Опциональные поля (добавляются только если найдены):
    "section_number": "7.2.39",
    "section_title": "Функциональные требования / Статистика",
    "parent_id": 42,        # id блока-заголовка
    "cross_refs": ["7.4", "9.1"],
    "block_type": "requirement" | "heading" | "list_item" | "continuation",
    "span": ["para98", "para99"],  # список исходных фрагментов
    "llm_validated": false,  # true когда Слой 2 подтвердил границу
}
```

### 4.5. Поведение Слоя 1 (structural)

Алгоритм (детерминированный):

1. Пройти `raw_blocks` в порядке `id`.
2. Для каждого блока:
   - Применить регулярку `section_number_pattern`. Если совпадение и
     остаток текста короткий (< 80 символов) и нет requirement-глаголов —
     это **заголовок** (`block_type: heading`). Сохранить как текущий
     `current_section`.
   - Иначе если найдены requirement-глаголы и блок длиннее
     `min_requirement_length` — это **атомарное требование**
     (`block_type: requirement`). Обогатить локатор `section_number`,
     `section_title`, `parent_id` из `current_section`.
   - Иначе если блок без маркера, длиной < `min_requirement_length`, и
     предыдущий блок — `requirement` или `list_item` — это
     **продолжение** (`block_type: continuation`). Объединить с предыдущим.
   - Иначе — оставить как есть, `block_type: requirement` по умолчанию.
3. Распознать перекрёстные ссылки в тексте: `cross_ref_patterns` →
   `locator.cross_refs`.
4. Удалить блоки с `block_type: heading` из выходного списка (заголовки
   несут контекст, но не являются требованиями).
5. Переприсвоить `id` непрерывно.

### 4.6. Поведение Слоя 2 (LLM, опционально)

Только при `strategy: hybrid` и `use_llm_boundary_check: true`:

1. Для каждого блока с `block_type: requirement` и неопределёнными
   границами (например, нет `section_number`) — отправить промпт в Ollama.
2. Если LLM подтверждает границу — пометить `llm_validated: true`.
3. Если LLM предлагает merge — выполнить merge, сохранить
   `llm_validated: true`.
4. При тайм-ауте / сбое — fallback на Слой 1.

### 4.7. Backward compat

- Сигнатура `load_requirements_by_extension(file_path, config_path, run_id)`
  не меняется.
- Контракт возврата `[{id, text, locator}]` сохранён.
- Ключи локатора **только добавляются**, не удаляются и не переименовываются.
- При `strategy: naive` или при отсутствии секции `parsing` в config —
  поведение идентично текущему.
- `ExportRouter` (FR-06) и `Pipeline` не требуют правок.

---

## 5. Промпт для LLM (Слой 2)

```
Ты анализируешь фрагменты, извлечённые парсером из тендерного ТЗ
(.docx/.xlsx). Для каждого фрагмента определи:

1. Является ли фрагмент завершённым атомарным требованием.
2. Если нет — какие соседние фрагменты нужно объединить (по индексу).
3. К какому разделу (section_number) он относится.

Возвращай строго JSON:
[
  {
    "fragment_id": 1,
    "is_complete": true,
    "merge_with": [],
    "section_number": "7.2",
    "reason": "Полное требование с глаголом 'должен'."
  }
]

Правила:
- Не выдумывай текст. Не меняй содержание фрагментов.
- Если не уверен — пометь is_complete=true и не merge.
- Не объединяй фрагменты разных разделов.
```

Параметры запроса (BL-22 lock):
- `temperature=0.0`
- `top_p=1.0`
- `seed=42`
- `max_tokens=2048`
- `timeout=10` сек на блок, общий лимит 30 сек.

---

## 6. Метрики и валидация

### 6.1. Golden Set (BL-59)

`data/parsing_golden_set_v1.jsonl` — 20 примеров с ручной разметкой:

```json
{
  "source": "fixtures/sample_1.docx",
  "expected_requirements": [
    {
      "text": "7.2.39. Статистика реального времени должна предоставлять данные...",
      "section_number": "7.2.39",
      "section_title": "Функциональные требования",
      "cross_refs": []
    }
  ]
}
```

### 6.2. Метрики приёмки

| Метрика | Цель | Метод замера |
|---------|------|--------------|
| **Boundary Accuracy** | ≥ 90 % | precision/recall на границах vs Golden Set |
| **Context Propagation Rate** | 100 % | все non-heading блоки имеют `section_title` если в документе есть нумерованные секции |
| **Ref Stability** | 100 % | существующие тесты `test_docx_parser.py`, `test_export_router.py` зелёные |
| **False ND Reduction** | ≥ 60 % | прогон pipeline на тестовом наборе с/без BL-59, замер `empty_context → НД` |
| **Latency** | ≤ 30 сек / 50 стр. | `tests/test_requirement_parsing.py::test_performance_50_pages_docx` |
| **Backward Compat** | 100 % | `pytest tests/test_export_router.py tests/test_pipeline.py` |

### 6.3. Тесты

`tests/test_requirement_parsing.py` (новый файл):

1. `test_strategy_naive_returns_raw_blocks_unchanged` — pass-through.
2. `test_strategy_structural_propagates_section_context` — заголовок
   `7.2 Функциональные требования` → дочерние блоки получают
   `section_number: "7.2"`, `section_title: "..."`, `parent_id`.
3. `test_strategy_structural_detects_cross_refs` — текст «см. п. 7.4» →
   `cross_refs: ["7.4"]`.
4. `test_strategy_structural_merges_continuation` — короткий «обезглавленный»
   блок после требования объединяется с предыдущим.
5. `test_strategy_hybrid_falls_back_when_llm_disabled` —
   `use_llm_boundary_check: false` → идентично structural.
6. `test_backward_compat_naive_default` — без секции `parsing` в конфиге →
   результат идентичен текущему `DocxParser` (для backward compat в CI).
7. `test_locator_preserves_original_keys` — все исходные ключи
   (`type`, `index`, `table`, `row`, `col`, `paragraph`, `sheet_name`)
   сохранены.
8. `test_golden_set_boundary_accuracy` — прогон на Golden Set, accuracy ≥ 90%.
9. `test_performance_50_pages_docx` — синтетический документ 50 страниц,
   парсинг ≤ 30 сек на CPU.

---

## 7. План внедрения (Implementation Steps)

1. **Step 1 (этот PR):**
   - Создать `src/parsers/requirement_boundary_detector.py` — структурный слой.
   - Обновить `configs/parsing_config.yaml` — секция `parsing`.
   - Интегрировать в `src/parsers/__init__.py::load_requirements_by_extension`.
   - Создать `data/parsing_golden_set_v1.jsonl` — 20 примеров.
   - Создать `tests/test_requirement_parsing.py` — все 9 тестов выше.
   - Обновить `CHANGELOG.md` — `CODE: BL-59 ...`.
   - Опубликовать этот research-документ.
2. **Step 2 (последующий PR, optional):**
   - Реализовать LLM-валидацию (Слой 2) с реальным `qwen2.5:7b`-клиентом
     и кэшированием.
   - A/B-замер `False ND Reduction` на тестовом наборе.

---

## 8. Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| **Hyper-merge:** два независимых требования сольются в одно из-за слабых эвристик | Средняя | Высокое | `min_requirement_length` + проверка маркеров; LLM-чек (Слой 2) ловит ошибки |
| **Нестандартные заголовки** (CAPS-only без нумерации, заголовки в таблицах) | Высокая | Среднее | Регулярка CAPS + `python-docx` style API; edge-cases в Golden Set |
| **Сломанные исходные `[Ref]`** | Низкая | Высокое | Locator preserves original keys; CI-тест `test_locator_preserves_original_keys`; контрактный тест `test_export_router.py` |
| **LLM медленный / недоступен** | Средняя | Среднее | Toggle `use_llm_boundary_check: false` по умолчанию; fallback на Слой 1 |
| **Регрессия в `Pipeline`** | Низкая | Высокое | Контракт `[{id, text, locator}]` не меняется; CI прогоняет `test_pipeline.py` |

---

## 9. Открытые вопросы для PO

1. **Дефолтная стратегия:** включить `structural` сразу или оставить `naive`
   до подтверждения на pilot-документах? **Рекомендация:** включить
   `structural` (без LLM), потому что (а) поведение полностью аддитивно,
   (б) даёт мгновенное улучшение `[Ref]` без рисков.
2. **LLM-кэш в репозитории:** хранить `data/cache/parsing/` в git или
   `.gitignore`? **Рекомендация:** `.gitignore` (бинарные кэши не должны
   попадать в историю; cache rebuild < 30 сек на 50 стр.).
3. **Golden Set:** 20 примеров достаточно или нужно расширить до 50–100?
   **Рекомендация:** 20 для v1, расширение до 50 — в Sprint 6 (после
   первой обратной связи с пилота).

---

## 10. Acceptance Criteria (для PR #213)

- [x] Документ опубликован, ссылается на правильные исходные документы.
- [x] Сравнение подходов (A/B/C/D) с явной рекомендацией.
- [x] Контракт `RequirementBoundaryDetector` зафиксирован.
- [x] Контракт обогащённого локатора зафиксирован.
- [x] Backward compat явно описан.
- [x] Промпт для LLM зафиксирован (для Step 2).
- [x] Метрики приёмки сформулированы с порогами.
- [x] План внедрения разбит на 2 шага.
- [x] Риски + митигация.

---

## Источники

- [`docs/CONCEPT.md`](../CONCEPT.md) v2.3 — FR-01 (парсинг ТЗ), NFR-04
  (RU-резидентность), NFR-08 (CPU-only).
- [`docs/ADR/001-rag-architecture.md`](../ADR/001-rag-architecture.md) —
  гибридный поиск (контекст «зачем нам полноценные требования»).
- [`docs/standards/export-markup.md`](../standards/export-markup.md) §3 —
  контракт `[Ref]`.
- [`docs/analysis/2026-05-17_analysis_tz-structure_samples.md`](../analysis/2026-05-17_analysis_tz-structure_samples.md) —
  типология реальных ТЗ.
- LangChain `SemanticChunker`:
  https://python.langchain.com/docs/modules/data_connection/document_transformers/semantic-chunker.
- LlamaIndex SentenceWindowNodeParser:
  https://docs.llamaindex.ai/en/stable/api_reference/node_parsers/sentence_window.
- Unstructured.io DOCX partitioner:
  https://unstructured-io.github.io/unstructured/core/partition.html#docx.
- Docling (IBM): https://github.com/DS4SD/docling.
