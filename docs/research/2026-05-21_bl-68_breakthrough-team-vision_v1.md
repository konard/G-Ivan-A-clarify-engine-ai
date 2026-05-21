# Research: Видение команды «Прорыва» — стратегия развития Clarify Engine (BL-68)

## Метаданные
- **Дата:** 2026-05-21
- **Версия:** v1
- **Тип документа:** `research`
- **Статус:** Сохранено для сверки вариантов
- **Автор:** konard (AI issue solver, по [issue #230](https://github.com/G-Ivan-A/clarify-engine-ai/issues/230))
- **Файл:** `docs/research/2026-05-21_bl-68_breakthrough-team-vision_v1.md`
- **Линкованный backlog:** [`docs/backlog/2026-05-17_backlog_rag-optimization_v1.5.md`](../backlog/2026-05-17_backlog_rag-optimization_v1.5.md) §BL-68
- **Depends on:** `BL-62`
- **Целевая аудитория:** Product Owner, Tech Lead, команды «Прорыва» и «Поддержки»
- **PR:** [`#231`](https://github.com/G-Ivan-A/clarify-engine-ai/pull/231)

> **Scope note.** Это исследовательский документ — независимое видение команды «Прорыва». **Не вносить в основную документацию.** Сохранён исключительно для дальнейшей сверки вариантов развития проекта.

---

## Ответ от команды «Прорыва»

Команда «Прорыва» проанализировала предложение команды поддержки и общую ситуацию проекта. Ниже — **независимое видение** архитектуры и стратегии развития Clarify Engine.

---

### Позиция команды «Прорыва»

Команда поддерживает общий вектор на **research-driven** и **контролируемую сложность**, но придерживается более амбициозного и долгосрочного взгляда.

**Ключевая философия:**
> **Строить не просто инструмент, а собственный data moat и интеллектуальный актив компании.**

Цель — не быть «ещё одним тонким клиентом к OpenRouter», а владеть своими embeddings, знаниями и возможностью работать полностью offline.

---

### 1. Что поддерживается из предложения команды поддержки

- Минимизация инфраструктурных затрат на старте.
- Feature toggles и switchability.
- Приоритет observability и reproducibility.
- Отказ от сложного multi-agent runtime в MVP.

---

### 2. Ключевые отличия позиций

| Аспект | Команда поддержки | Команда «Прорыва» |
|--------|-------------------|-------------------|
| **Основной приоритет** | Скорость экспериментов и минимализм | **Data ownership + long-term moat** |
| **LLM inference** | Внешние API как primary | **Hybrid** (external как основной, но self-hosted как стратегический) |
| **Embeddings** | Offline batch | **Стратегический актив**, который нужно активно собирать и защищать |
| **UI** | GitHub Pages + Streamlit | Streamlit как основной + постепенный переход к более мощному UI |
| **Архитектура** | Modular monolith | **Modular monolith + clear extension points** |

---

### 3. Видение архитектуры MVP — «Core + Extensible Shell»

#### Core (лёгкий, стабильный, полностью self-hosted capable)
- FastAPI backend
- ChromaDB (с возможностью миграции на PGVector)
- Offline embedding pipeline
- YAML + env-based configuration
- Strict error handling + audit trail

#### Shell (расширяемая часть)
- Режимы работы (Анализ ТЗ / Консультация / Обогащение БЗ)
- Плагин-подобная система экспортёров и парсеров
- Feature toggles для экспериментальных возможностей

**Ключевой принцип:**
> **Всё, что касается знаний (embeddings, canonical map, dependencies), должно быть под полным контролем.**

---

### 4. Рекомендуемый технический стек и roadmap

#### MVP (ближайшие 4–6 недель)
- Streamlit как основной UI (быстро, удобно для внутренних пользователей)
- Полная поддержка multi-format (xlsx + docx + md)
- Parent Document Retrieval (BL-10)
- STRICT_MODE (BL-03)
- Prompt Library + Decoding Config
- Режим «Обогащение Базы Знаний» (BL-26)

#### Sprint 3–4 (Pilot)
- Offline Dependency Extraction (BL-14)
- Query Expansion + Multi-hop (BL-11/12) с feature flag
- Canonical Mapping + Feature Dictionary
- Расширенная диагностика ошибок (BL-24b)

#### Долгосрочная цель (3–6 месяцев)
- Self-hosted inference (Ollama / vLLM) как first-class citizen
- Граф знаний (лёгкий) поверх embeddings
- API + интеграции
- Open-source релиз с хорошей документацией

---

### 5. Финальная рекомендация команды «Прорыва»

**Не бояться controlled complexity**, но **не усложнять runtime**.

**Что делать сейчас:**
1. Закрыть критические P0-блоки (multi-format, STRICT_MODE, Parent Retrieval).
2. Сделать **BL-26 (Обогащение БЗ)** одной из приоритетных задач — это будет главный конкурентный advantage.
3. Постепенно наращивать **self-hosted** возможности (Ollama config, local embeddings pipeline).
4. Сохранять **высокую observability** и **feature toggles** — это позволит экспериментировать безопасно.

Команда «Прорыва» считает, что Clarify Engine может стать **одним из лучших русскоязычных open-source RAG-инструментов** для технической документации и рекомендаций, если сохранить баланс между простотой и глубиной знаний.

---

*Документ сохранён для сверки вариантов. Не вносить в основную документацию проекта.*
