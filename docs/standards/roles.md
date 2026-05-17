# 👥 Roles & Responsibilities — Команда проекта

**Версия:** 1.1 | **Дата:** 2026-05-17 | **Статус:** Approved

---

## 1. Назначение
Документ фиксирует роли, владельцев и зоны ответственности в проекте `clarify-engine-ai`. Используется как единая точка ссылок на роли в концепции, ADR и аналитических документах.

Связанные документы:
- [`docs/CONCEPT.md`](../CONCEPT.md) — концепция MVP.
- [`docs/ADR/001-rag-architecture.md`](../ADR/001-rag-architecture.md) — архитектурное решение по RAG.
- [`docs/analysis/2026-05-12_review_mvp-context_v1.md`](../analysis/2026-05-12_review_mvp-context_v1.md) — ревью концепции MVP.

---

## 2. Роли

### 2.1. Founder, Product Owner (Владелец продукта)
- **Имя:** Ivan Gulienko
- **GitHub:** [@G-Ivan-A](https://github.com/G-Ivan-A)
- **Ответственность:**
  - Стратегия продукта от концепции до production.
  - Приоритизация задач и приёмка MVP.
  - Утверждение архитектурных решений (ADR).
  - Владелец [`docs/CONCEPT.md`](../CONCEPT.md) и бизнес-требований.
  - **Коммитит все Pull Requests в репозиторий.**

### 2.2. Code Agent (Исполнитель)
- **Имя:** Konstantin Diachenko
- **GitHub:** [@konard](https://github.com/konard)
- **Роль:** AI-агент / Code Generator.
- **Ответственность:**
  - Генерация кода по Issues из репозитория.
  - Техническая реализация требований.
  - Поддержка CI/CD пайплайнов.
  - **НЕ является владельцем бизнес-логики, НЕ коммитит в `main`.**

### 2.3. Prompt Owner (Владелец промптов)
- **Имя:** Ivan Gulienko
- **GitHub:** [@G-Ivan-A](https://github.com/G-Ivan-A)
- **Ответственность:**
  - Версионирование промптов в [`prompts/`](../../prompts/).
  - A/B-тестирование и обновление `prompt_changelog.md`.
  - Валидация качества классификации (целевая метрика F1 ≥ 75%, см. раздел 4 концепции).

### 2.4. Sprint Execution Report (отчёт о выполнении спринта)
- **Шаблон:** [`docs/analysis/sprint-execution-report_template.md`](../analysis/sprint-execution-report_template.md).
- **Заполняет (Responsible):** Code Agent ([@konard](https://github.com/konard)) — в течение 1 рабочего дня после завершения спринта.
- **Ревью и приёмка (Accountable):** Product Owner ([@G-Ivan-A](https://github.com/G-Ivan-A)).
- **Куда сохранять:** [`docs/analysis/`](../analysis/), имя файла — `YYYY-MM-DD_sprint-[N]-execution-report_v1.md` ([`naming-convention.md`](naming-convention.md)).
- **Definition of Done спринта** включает наличие заполненного отчёта (см. [`docs/CONCEPT.md §8.1`](../CONCEPT.md#81-этапы)).

---

## 3. Матрица ответственности (RACI, сокращённая)

| Активность | Product Owner | Code Agent | Prompt Owner |
|------------|--------------:|-----------:|-------------:|
| Концепция, бизнес-требования | **A/R** | C | C |
| Архитектурные решения (ADR) | **A** | R | C |
| Реализация кода (Issues → PR) | A | **R** | C |
| Промпты и их версионирование | A | C | **R** |
| Коммит PR в `main` | **R** | — | — |
| Приёмка MVP / валидация качества | **A/R** | C | **R** |
| Заполнение Sprint Execution Report | **A** | **R** | C |

> Обозначения: **R** — Responsible (исполнитель), **A** — Accountable (отвечающий), **C** — Consulted (консультируемый).

---

## 4. Эксплуатационные инструкции (Runbooks)
На этапе MVP каталог [`docs/runbooks/`](../runbooks/) создан как заглушка. **Наполнение начнётся на этапе «Пилот»** (раздел 7 концепции, недели 3–5) силами Product Owner совместно с Code Agent. До этого момента эксплуатационные инструкции не считаются обязательными артефактами MVP.

---

## 5. История изменений
| Версия | Дата | Изменение |
|--------|------|-----------|
| 1.0 | 2026-05-12 | Первая версия документа ролей: Product Owner, Code Agent, Prompt Owner. |
| 1.1 | 2026-05-17 | Добавлен §2.4 — ответственность за Sprint Execution Report ([issue #85](https://github.com/G-Ivan-A/clarify-engine-ai/issues/85)). |
