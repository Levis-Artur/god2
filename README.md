# Telegram Bot MVP для аналізу відкритих Telegram-даних

Це практичний MVP Telegram-бота на `Python 3.11`, `aiogram v3` і `Telethon`.

Бот приймає:

- публічний `username`
- публічне Telegram-посилання
- номер телефону лише як текстовий індикатор для пошуку публічних згадок

Бот повертає короткий підсумок прямо в чаті та зберігає історію запитів у `SQLite`.

## Що робить бот

- показує український інтерфейс і меню
- приймає запити через `/start`, `/help` і кнопки меню
- нормалізує `username`, публічні Telegram-посилання і номери телефонів
- для `username` і публічних посилань отримує дані з Telegram через `Telethon`
- у режимі `Номер` перевіряє лише публічні текстові згадки в заздалегідь налаштованих відкритих Telegram-джерелах
- аналізує лише текст публічних повідомлень
- витягує `@mentions`, `URL`, `#hashtags`, email, домени і телефони як явні текстові артефакти
- формує короткі українські відповіді без JSON і технічного шуму

## Чого бот не робить

- не працює з приватними чатами
- не працює з приватними групами
- не обходить обмеження Telegram
- не виконує деанонімізацію
- не витягує приховані ідентифікатори
- не збирає IP-адреси
- не використовує злиті бази даних
- не шукає особу за номером телефону
- не виконує глобальний пошук по всьому Telegram
- не додає web scraping або іншу небезпечну логіку

## Як працює режим «Номер»

Режим `Номер`:

- не шукає людину
- не встановлює власника номера
- перевіряє лише текстові згадки номера
- працює лише всередині джерел, які ви явно вкажете в `TG_PUBLIC_PHONE_SOURCES`

Приклад:

```env
TG_PUBLIC_PHONE_SOURCES=@source_one,https://t.me/source_two,@source_three
```

У такому режимі бот пройде лише по цих відкритих Telegram-джерелах, візьме останні повідомлення згідно з глибиною пошуку і покаже:

- де знайдено номер
- скільки є збігів
- короткий підсумок

## Змінні середовища

У `.env` потрібні такі змінні:

- `BOT_TOKEN` токен Telegram-бота
- `DATABASE_URL` URL бази даних, за замовчуванням можна лишити `sqlite:///./bot.db`
- `LOG_LEVEL` рівень логування, наприклад `INFO`
- `TG_API_ID` ваш `api_id` з Telegram API
- `TG_API_HASH` ваш `api_hash` з Telegram API
- `TG_SESSION_NAME` ім’я Telethon-сесії, за замовчуванням `robocop_session`
- `TG_PUBLIC_PHONE_SOURCES` список публічних Telegram-джерел через кому для режиму `Номер`

Приклад є у `.env.example`.

## Як отримати `TG_API_ID` і `TG_API_HASH`

1. Перейдіть на `https://my.telegram.org`
2. Увійдіть у свій Telegram-акаунт
3. Відкрийте `API development tools`
4. Створіть застосунок
5. Скопіюйте `api_id` і `api_hash` у `.env`

## Перший запуск Telethon-сесії

Перший запуск потрібно робити в інтерактивному терміналі.

Під час першого старту Telethon попросить:

- номер телефону Telegram-акаунта
- код підтвердження
- пароль 2FA, якщо він увімкнений

Після успішної авторизації буде створено файл сесії `TG_SESSION_NAME.session`.

За замовчуванням файл з’явиться в корені проєкту, наприклад:

- `robocop_session.session`

Після цього бот можна запускати повторно без повторного вводу коду, доки сесія дійсна.

## Як запустити

1. Створіть віртуальне середовище:

```bash
python -m venv .venv
```

2. Активуйте його.

3. Встановіть залежності:

```bash
pip install -r requirements.txt
```

4. Створіть `.env` на основі `.env.example` і заповніть:

- `BOT_TOKEN`
- `TG_API_ID`
- `TG_API_HASH`
- `TG_PUBLIC_PHONE_SOURCES`

5. Запустіть бота:

```bash
python -m app.main
```

6. Для перевірки тестів:

```bash
python -m pytest -q
```

## Структура проєкту

```text
app/
  bot/
    handlers/
      analysis.py
      common.py
      history.py
      settings.py
      utils.py
    keyboards/
      inline.py
      reply.py
  core/
    config.py
    constants.py
    logging.py
    texts.py
  db/
    models.py
    repo.py
  services/
    analyzer.py
    collector.py
    extractor.py
    formatter.py
    normalizer.py
    telegram_client.py
  main.py
tests/
  test_config.py
  test_extractor.py
  test_formatter.py
  test_normalizer.py
  test_phone_pipeline.py
```

## Ключові модулі

- `app/services/telegram_client.py` керує одним Telethon-клієнтом і його сесією
- `app/services/collector.py` збирає публічні повідомлення з Telegram, включно з phone mention search по налаштованих джерелах
- `app/services/analyzer.py` запускає нормалізацію, збір і витяг артефактів
- `app/services/extractor.py` витягує URL, домени, email, телефони, `@mentions` і `#hashtags`
- `app/services/formatter.py` формує короткі українські відповіді для чату
- `app/db/repo.py` зберігає історію пошуку і налаштування користувача
