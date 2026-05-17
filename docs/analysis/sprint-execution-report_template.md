# Sprint [N] Execution Report

**Период:** YYYY-MM-DD → YYYY-MM-DD
**Бэклог-источник:** `docs/backlog/[дата]_backlog_[slug]_v[X].md`
**GitHub Issue:** #[номер]
**Статус:** Completed / Partially Completed / Blocked

> Скопируйте этот файл в `docs/analysis/` под именем
> `YYYY-MM-DD_sprint-[N]-execution-report_v1.md` (см. [`docs/standards/naming-convention.md`](../standards/naming-convention.md)).
> Удалите этот блок-цитату и поясняющие комментарии после копирования.
> Правила использования и ответственность — см. [`docs/CONCEPT.md §8.1`](../CONCEPT.md#81-этапы) и [`docs/standards/roles.md §2.4`](../standards/roles.md).

## 🗂 Метаданные
- **Дата:** YYYY-MM-DD
- **Версия:** v1
- **Автор:** Code Agent (@konard)
- **Ревьюер:** Product Owner (@G-Ivan-A)
- **Статус:** Draft | Reviewed | Approved | Archived

---

## 1. Executive Summary
_Краткое резюме (3–5 предложений):_
- Сколько задач из плана выполнено.
- Достигнуты ли целевые метрики.
- Ключевые достижения и блокеры.
- Готовность к следующему спринту.

## 2. Поэлементная верификация задач
| ID | Задача | Статус | Ключевые файлы/PR | Метрики/Результат | Принято? |
|:---|:---|:---:|:---|:---|:---:|
| BL-XX | [Название задачи] | ✅ / 🟡 / ❌ | `path/to/file.py`, PR #[N] | [Конкретные метрики] | ✅ / ❌ |
| ... | ... | ... | ... | ... | ... |

_Легенда статусов:_
- ✅ Выполнено полностью.
- 🟡 Выполнено частично / требует доработки.
- ❌ Не выполнено / заблокировано.

## 3. Изменения в конфигурации и документации
_Перечень обновлённых файлов:_
- `configs/[file].yaml`: [что изменено].
- `docs/CONCEPT.md §X.Y`: [что обновлено].
- `docs/ADR/[NNN]-[slug].md`: [статус ADR].
- `CHANGELOG.md`: [ключевые записи].

## 4. Метрики и бенчмарки
| Метрика | Baseline | Текущее | Целевое | Статус |
|:---|:---|:---:|:---|:---|
| [Название метрики] | X.XX | X.XX | ≥ X.XX | ✅ / ⚠️ / ❌ |
| Hit Rate@5 | X.XX | X.XX | ≥ baseline | ✅ |
| F1 (Golden Set) | 0.XX | 0.XX | ≥ 0.70 | ✅ |
| p95 Retrieval Latency | X с | X с | < 1 с | ✅ |
| Citation Presence | XX % | XX % | ≥ 80 % (MVP) | ✅ |

## 5. Блокеры, риски и отклонения
_Описание проблем:_
- [ ] [Отклонение от плана с обоснованием].
- [ ] [Технический долг, требующий внимания].
- [ ] [Необходимость пересмотра промптов/конфигов].

## 6. Готовность к следующему спринту
- [ ] Индекс перестроен, ChromaDB стабилен.
- [ ] CI-пайплайн зелёный, smoke-тесты проходят.
- [ ] Документация синхронизирована.
- [ ] [Дополнительные критерии].

## 7. Ссылки
- PR: #[номер]
- Commits: `sha1..shaN`
- Issue: #[номер]
- Golden Set: `test_data/rag_golden_set.json`
- Отчёт оценки: `reports/rag_eval_[дата].json`

---

## 📝 Правила использования

### Когда заполнять
- **Срок:** в течение 1 рабочего дня после завершения спринта.
- **Ответственный:** Code Agent ([@konard](https://github.com/konard)).
- **Ревью:** Product Owner ([@G-Ivan-A](https://github.com/G-Ivan-A)).

### Где хранить
Файл создаётся в [`docs/analysis/`](.) с именем по стандарту
[`docs/standards/naming-convention.md`](../standards/naming-convention.md):

```
YYYY-MM-DD_sprint-[N]-execution-report_v1.md
```

Пример: `2026-05-24_sprint-1-execution-report_v1.md`.

### Как использовать для анализа
1. Product Owner копирует содержимое заполненного файла.
2. Передаёт внешнему аналитику (AI/человеку) для архитектурного ревью.
3. Получает рекомендации для следующего спринта.
4. Вносит корректировки в бэклог.

---

## 🔗 Связанные документы
- [`docs/CONCEPT.md §8`](../CONCEPT.md#8-план-внедрения) — План внедрения и Definition of Done спринта.
- [`docs/backlog/2026-05-17_backlog_rag-optimization_v1.md`](../backlog/2026-05-17_backlog_rag-optimization_v1.md) — Актуальный бэклог задач.
- [`docs/standards/roles.md`](../standards/roles.md) — Роли и ответственность.
- [`docs/standards/naming-convention.md`](../standards/naming-convention.md) — Стандарт именования файлов.

> 📌 **Примечание:** этот шаблон не заменяет GitHub Issues/PR, а дополняет их агрегированным представлением для архитектурного анализа и ретроспективы.

## История изменений
| Версия | Дата | Изменение |
|--------|------|-----------|
| v1 | 2026-05-17 | Первая версия шаблона Sprint Execution Report ([issue #85](https://github.com/G-Ivan-A/clarify-engine-ai/issues/85)). |
