# Research: Предложения команды поддержки по архитектуре MVP Clarify Engine

## Метаданные
- **Дата:** 2026-05-21
- **Версия:** v1
- **Тип документа:** `research`
- **Статус:** Draft — к ознакомлению PO / Tech Lead
- **Автор:** Команда поддержки (сохранено по [issue #228](https://github.com/G-Ivan-A/clarify-engine-ai/issues/228))
- **Целевая аудитория:** Product Owner, Tech Lead, Команда разработки
- **Назначение:** Зафиксировать позицию команды поддержки по архитектуре MVP для дальнейшей сверки вариантов развития проекта. Документ только в папке исследований — **не переносить в основную документацию**.
- **Связанные документы:**
  - [`docs/research/2026-05-20_bl-60_next-gen-architecture_v1.md`](2026-05-20_bl-60_next-gen-architecture_v1.md) — BL-60, Next-Gen Architecture Research
  - [`docs/CONCEPT.md`](../CONCEPT.md) — концепция MVP

> **Scope Note.** Это исследовательский артефакт — зафиксированная позиция команды поддержки. Не является ADR, не обязателен к реализации. Учитывается при дальнейшей сверке архитектурных вариантов.

---

## Общая позиция

Команда поддержки поддерживает направление на:

- research-driven architecture,
- минимизацию постоянных инфраструктурных затрат,
- использование бесплатных или условно-бесплатных AI-каналов,
- модульную extensible-архитектуру,
- постепенное усложнение только после подтверждения ценности MVP.

**Ключевой принцип:**

> не строить enterprise-платформу раньше времени.

На текущем этапе проекту важнее:

- скорость экспериментов,
- архитектурная гибкость,
- controllable complexity,
- observability,
- возможность быстро менять AI-routing.

---

## 1. Что НЕ стоит делать в MVP

### Не превращать MVP в AI orchestration platform

На текущем этапе не рекомендуется:

- сложный multi-agent runtime,
- динамический orchestration engine,
- автоматическое self-healing routing,
- enterprise governance,
- distributed inference management,
- сложный UI управления AI-провайдерами,
- runtime policy engine.

**Причина:**

- резко возрастает complexity,
- падает тестируемость,
- усложняется debugging,
- растет technical debt,
- MVP превращается в infra-проект вместо продукта.

---

## 2. Что стоит заложить архитектурно, но упростить реализацию

### Подход: "Simple Core + Extensible Architecture"

Нужно разделить:

- текущую реализацию,
- и будущие capability.

---

## 3. AI routing: как реализовать без переусложнения

### Рекомендуемый подход

Не делать сложный orchestration UI.

Сделать: `Settings → AI Provider`

И несколько режимов:

| Режим | Назначение |
|-------|------------|
| Auto | автоматический выбор |
| OpenRouter | внешний free-tier |
| GigaChat | fallback/provider |
| Local Endpoint | локальная/дружественная модель |
| Disabled | offline/retrieval only |

---

## 10. Самая важная рекомендация

### Проектировать "switchability", а не "full functionality"

То есть:

- capability должна существовать,
- но может быть disabled.

**Пример:**

```
[ Local LLM ]
Status: Planned
Available in architecture: Yes
Runtime enabled: No
```

Это:

- сохраняет extensibility,
- не усложняет MVP,
- позволяет постепенно включать возможности.

---

## 11. Финальное мнение команды поддержки

Наиболее разумная стратегия:

### Сейчас

- GitHub Pages
- Minimal VPS
- External LLM APIs
- Offline embeddings
- Simple routing
- Feature toggles
- Retrieval-first architecture

### Потом

- local inference,
- hybrid orchestration,
- governance,
- masking,
- analytics,
- multi-agent workflows,
- intelligent routing.

---

## Итоговая рекомендация

**Цель MVP:**

- не доказать возможность локального AI inference,
- а доказать ценность AI-assisted analytical workflow.

**Поэтому:**

- inference должен быть максимально дешевым и гибким,
- архитектура — расширяемой,
- а complexity — строго контролируемой.
