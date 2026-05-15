"""Test regex patterns from issue #38 against expected outputs."""

import re

LEGAL = re.compile(r'(?i)\b(ООО|АО|ПАО|ЗАО|НАО|ОАО)\s*"?([^"]+)"?')
IE = re.compile(r'(?i)\b(ИП)\s+(\S+)')

cases = [
    ('Поставка для ООО "Вектор"', LEGAL, r'\1 [LEGAL_ENTITY]', 'Поставка для ООО [LEGAL_ENTITY]'),
    ('Заказчик: АО Прогресс', LEGAL, r'\1 [LEGAL_ENTITY]', 'Заказчик: АО [LEGAL_ENTITY]'),
    ('Ответственный: ИП Смирнов', IE, r'\1 [IE_SURNAME]', 'Ответственный: ИП [IE_SURNAME]'),
    ('ИП "Петров"', IE, r'\1 [IE_SURNAME]', 'ИП [IE_SURNAME]'),
    ('Работа с ооо "тест"', LEGAL, r'\1 [LEGAL_ENTITY]', 'Работа с ооо [LEGAL_ENTITY]'),
]

for text, pat, repl, expected in cases:
    got = pat.sub(repl, text)
    status = "OK" if got == expected else "FAIL"
    print(f"{status}: '{text}' -> '{got}' (expected: '{expected}')")
