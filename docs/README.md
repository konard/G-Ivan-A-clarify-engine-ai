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
| BL-58 | [`research/2026-05-21_bl-57_retrieval-architecture_v1.md`](research/2026-05-21_bl-57_retrieval-architecture_v1.md) | Retrieval architecture experiments и query-expansion recommendation. |
| BL-59 | [`research/2026-05-20_bl-59_requirement-parsing_v1.md`](research/2026-05-20_bl-59_requirement-parsing_v1.md) | Requirement parsing research и two-layer parser design. |
