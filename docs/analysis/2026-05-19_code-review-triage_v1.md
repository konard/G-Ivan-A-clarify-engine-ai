# Верификация замечаний Code Review (BL-26)

**Дата:** 2026-05-19  
**Issue:** [#142](https://github.com/G-Ivan-A/clarify-engine-ai/issues/142)  
**Scope:** экспертная проверка 4 пунктов автоматического Code Review без расширения MVP-контрактов.

## Матрица триажа

| Item | Вердикт | Обоснование | Действие |
|------|---------|-------------|----------|
| `_load_dense_embedder` fallback | Подтверждено частично | Production-поведение уже было fail-fast, что соответствует ADR-001 и риску R-06. Но флаг `strict_embedder` не был явно закреплён в `configs/embedding_config.yaml`, а non-production fallback не был управляемым. | Добавлен `strict_embedder: true` в production-конфиг. `_load_dense_embedder()` теперь документирует контракт: при `true` бросает `RuntimeError`, при явном `false` использует `_hash_embedding` с WARNING-логом. |
| `page_number` для `.docx` | False positive | `.docx` является flow-layout форматом и не хранит стабильную физическую нумерацию страниц без рендеринга в PDF. FR-01 требует трассируемый `locator`, а не `page_number`: для параграфов и таблиц достаточно структурной ссылки. `test_data/sample_tz_1.DOCX` состоит из таблиц и вложенных текстовых блоков, где page-based locator архитектурно некорректен. | `page_number` не добавляется. Усилен тестовый контракт: DOCX locator не содержит `page_number`; table locator сохраняет `table` / `row` / `col`; списочные элементы получают `list_path`. |
| `@st.cache_resource` без инвалидации YAML | Подтверждено | `get_retriever()` кешировался только по имени функции, поэтому ручное изменение `configs/embedding_config.yaml` могло оставить UI со старым retriever до перезапуска процесса. Hot-reload не требуется для MVP, но ключ должен отражать конфиг. | Добавлен `embedding_config_hash()` на основе `hashlib.md5(config_bytes).hexdigest()`. Хэш передаётся в `get_retriever(config_hash)` и становится частью ключа Streamlit cache. |
| `masking_rules.yaml` / `exclude_sections` | Подтверждено частично | Runtime-маскирование не использует `exclude_sections`, поэтому текущий код не пропускал PII из-за этих секций. Риск был в конфиге: широкие значения `email` / `телефон` стали бы опасны, если skip-логика появится позже. Regex-аудит выявил false negative для телефонов РФ с префиксом `8` и частичное маскирование многоуровневых внутренних доменов. | Regex для email/phone/IP/domain расширены. `exclude_sections` сужен до явных блоков `контактные данные заказчика/исполнителя` и помечен как audit-only; runtime продолжает маскировать все исходящие тексты ради FR-05 / NFR-05. |

## Проверки

- `tests/test_retriever.py::test_embedding_config_ships_strict_embedder_enabled`
- `tests/test_retriever.py::test_non_strict_embedder_falls_back_to_hash`
- `tests/test_docx_parser.py::test_docx_table_list_locator_uses_structural_path_without_page_number`
- `tests/test_ui_modes.py::test_embedding_config_hash_tracks_file_bytes`
- `tests/test_masking.py::TestPhoneRUMasking::test_mask_phone_with_eight_prefix`
- `tests/test_masking.py::TestInternalDomainMasking::test_mask_multilevel_internal_domain`

