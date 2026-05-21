# Документация `clarify-engine-ai`

Этот индекс связывает основные документы проекта для PO, BA, Tech Lead и Infra
review. Детальные README внутри подпапок остаются владельцами локальной
навигации.

## Основные документы

| Раздел | Документ | Для кого |
|--------|----------|----------|
| Концепция MVP | [`CONCEPT.md`](CONCEPT.md) | PO, BA, Tech Lead |
| ADR | [`ADR/README.md`](ADR/README.md) | Tech Lead, разработчики |
| Standards | [`standards/README.md`](standards/README.md) | Все контрибьюторы |
| Runbooks | [`runbooks/README.md`](runbooks/README.md) | DevOps, support, pilot users |
| User Guide | [`user_guide/README.md`](user_guide/README.md) | BA, pilot users |

## Research и адаптации

| ID | Документ | Назначение |
|----|----------|------------|
| BL-60 | [`docs/research/2026-05-20_bl-60_next-gen-architecture_v1.md`](research/2026-05-20_bl-60_next-gen-architecture_v1.md) | Next-gen RAG architecture, Dynamic LLM Routing, microservices и infrastructure tiers. |
| BL-60-ru | [`docs/research/2026-05-20_bl-60_next-gen-architecture_v1.md`](research/2026-05-20_bl-60_next-gen-architecture_v1.md#4-предлагаемые-решения-бизнес-уровень) | Русская адаптация разделов 4-15 с блоками `🧠 Пояснение для БА`, `📚 Что почитать` и backward-compat notes для технических ревьюеров. |
| BL-61 | [`research/2026-05-21_bl-61_market-research_v1.md`](research/2026-05-21_bl-61_market-research_v1.md) | Market research по альтернативам микросервисных компонентов. |
| BL-67 | [`research/2026-05-21_bl-61_market-research_ru-education_v1.md`](research/2026-05-21_bl-61_market-research_ru-education_v1.md) | RU-education adaptation BL-61 для BA/PO: разделы 4-20 с блоками `💡 Для БА` и `📚 Читать далее`. |
| BL-61.1 | [`research/2026-05-21_bl-61_market-research_ru-education_v2.md`](research/2026-05-21_bl-61_market-research_ru-education_v2.md) | Business-readable v2: RU-пояснения в таблицах, конкретные сценарии `Когда применять`, HTML contract без ellipsis. |
| BL-61 HTML | [`research/html/2026-05-21_bl-61_market-research_ru-education_v1.html`](research/html/2026-05-21_bl-61_market-research_ru-education_v1.html) | Full-width HTML export для ревью сравнительных таблиц BL-61 без потери контекста. |
| BL-61.1 HTML | [`research/html/2026-05-21_bl-61_market-research_ru-education_v2.html`](research/html/2026-05-21_bl-61_market-research_ru-education_v2.html) | HTML v2 с переносом строк в ячейках таблиц (`white-space: normal`, без `text-overflow: ellipsis`). |
| BL-58 | [`research/2026-05-21_bl-57_retrieval-architecture_v1.md`](research/2026-05-21_bl-57_retrieval-architecture_v1.md) | Retrieval architecture experiments и query-expansion recommendation. |
| BL-59 | [`research/2026-05-20_bl-59_requirement-parsing_v1.md`](research/2026-05-20_bl-59_requirement-parsing_v1.md) | Requirement parsing research и two-layer parser design. |

## Просмотр research-документов в HTML

Для таблиц с большим числом колонок используйте full-width HTML export:

```bash
python scripts/tools/md_to_html_fullwidth.py \
  docs/research/2026-05-21_bl-61_market-research_ru-education_v2.md \
  -o docs/research/html/2026-05-21_bl-61_market-research_ru-education_v2.html
```
