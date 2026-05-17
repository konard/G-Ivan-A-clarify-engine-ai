# 📂 docs/analysis/

Каталог для аналитических отчётов и ревью по проекту: ревью концепции, код-аудиты, рекомендации команды, аналитические заметки.

## Назначение
Здесь собираются документы, фиксирующие результаты анализа состояния проекта в определённый момент времени: оценка концепции, аудит кода и архитектуры, ревью процессов и предложения по доработкам.

## Правила
- Имена файлов следуют стандарту [`docs/standards/naming-convention.md`](../standards/naming-convention.md).
- Структура содержимого следует шаблону [`docs/standards/templates/analysis-template.md`](../standards/templates/analysis-template.md).
- Каждый документ обязан включать: контекст, анализ текущего состояния, рекомендации и метаданные (дата, версия, автор, статус).

## Типы документов
| Тип | Префикс в имени | Назначение |
|-----|-----------------|------------|
| Review | `review` | Ревью концепции, требований, PR |
| Analysis | `analysis` | Аналитические заметки по проблеме |
| Audit | `audit` | Аудит кода, архитектуры, безопасности |
| Decision | `decision` | Принятые решения вне ADR |
| Sprint Execution Report | `sprint-[N]-execution-report` | Итоговый отчёт о выполнении спринта (шаблон: [`sprint-execution-report_template.md`](sprint-execution-report_template.md)) |

## Шаблоны в этом каталоге
- [`sprint-execution-report_template.md`](sprint-execution-report_template.md) — шаблон итогового отчёта по спринту. Заполняется после каждого спринта, имя итогового файла: `YYYY-MM-DD_sprint-[N]-execution-report_v1.md`. Правила и ответственность — см. [`docs/CONCEPT.md §8.1`](../CONCEPT.md#81-этапы) и [`docs/standards/roles.md §2.4`](../standards/roles.md).

## Пример
- [`2026-05-12_review_mvp-context_v1.md`](2026-05-12_review_mvp-context_v1.md) — ревью концепции MVP в контексте задач классификации требований Да/Нет/Частично/НД.
- [`2026-05-13_analysis_next-docs-implementation-task_v1.md`](2026-05-13_analysis_next-docs-implementation-task_v1.md) — формулировка следующей приоритетной задачи по документации и коду на основе аудита репозитория.
- [`2026-05-15_analysis_repo-state-and-mvp-recommendations_v1.md`](2026-05-15_analysis_repo-state-and-mvp-recommendations_v1.md) — анализ состояния репозитория, оценка готовности MVP, профиль нагрузки и рекомендации по доработке (issue #35).
