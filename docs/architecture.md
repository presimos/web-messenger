# Архитектура мессенджера

Проект разделён на браузерный клиент и HTTP API. Клиент написан на React и TypeScript; API реализован на FastAPI. Оба модуля обмениваются JSON по HTTP, а сообщения чата передаются по WebSocket. Слой доступа к данным использует SQLAlchemy; локально по умолчанию применяется SQLite. Подключение PostgreSQL поддерживается через `DATABASE_URL`, но в этой версии не проверялось.

Схема архитектуры подготовлена как [architecture.png](architecture.png). Связи классов и последовательности запросов ниже приведены в Mermaid-формате.

```mermaid
flowchart LR
  U[Пользователь] --> B[Браузер]
  B --> R[React + TypeScript<br/>App.tsx]
  R -->|HTTP JSON<br/>регистрация, вход, чаты, история| F[FastAPI<br/>main.py]
  R <-->|WebSocket<br/>сообщения чата| W[WebSocket router<br/>messaging.py]
  F --> A[auth.py<br/>JWT и профиль]
  F --> M[messaging.py<br/>чаты и история]
  A --> S[security.py<br/>Argon2 и JWT]
  A --> D[SQLAlchemy session<br/>database.py]
  M --> D
  W --> D
  D --> DB[(SQLite<br/>по умолчанию)]
```

## Модули и границы ответственности

| Модуль | Ответственность |
|---|---|
| `frontend/client/src/App.tsx` | Формы входа и регистрации, список чатов, история и WebSocket-клиент |
| `backend/app/main.py` | Создание FastAPI-приложения, CORS, подключение маршрутизаторов, системные маршруты |
| `backend/app/auth.py` | Регистрация, вход, получение профиля и проверка текущего пользователя |
| `backend/app/messaging.py` | Создание чатов, проверка членства, история, соединения и рассылка сообщений |
| `backend/app/schemas.py` | Валидация и сериализация запросов/ответов на Pydantic |
| `backend/app/models.py` | ORM-модели `User`, `Chat`, `ChatMember`, `Message` |
| `backend/app/database.py` | Настройка SQLAlchemy Engine и фабрики сессий из `DATABASE_URL` |
| `backend/app/security.py` | Хеширование Argon2 и создание/проверка JWT |

## Связи данных

```mermaid
classDiagram
  User "1" --> "*" ChatMember : user_id
  Chat "1" --> "*" ChatMember : chat_id
  Chat "1" --> "*" Message : chat_id
  User "1" --> "*" Message : sender_id
  class User {
    +int id
    +str username
    +str password_hash
    +datetime created_at
  }
  class Chat {
    +int id
    +str title
    +datetime created_at
  }
  class ChatMember {
    +int chat_id
    +int user_id
  }
  class Message {
    +int id
    +int chat_id
    +int sender_id
    +str body
    +datetime created_at
  }
```

Поля с `+` перечислены как публичные поля ORM-моделей. Отдельных приватных полей или схем наследования между бизнес-моделями в текущей реализации нет. Связь пользователя с чатом реализована таблицей `ChatMember` с составным первичным ключом.

## Основные потоки

```mermaid
sequenceDiagram
  actor U as Пользователь
  participant C as React-клиент
  participant A as FastAPI auth.py
  participant S as security.py
  participant DB as SQLAlchemy/SQLite
  U->>C: ввод имени и пароля
  C->>A: POST /auth/register (при регистрации)
  A->>S: хешировать пароль Argon2
  A->>DB: сохранить пользователя
  C->>A: POST /auth/login
  A->>DB: найти пользователя
  A->>S: проверить пароль и подписать JWT
  A-->>C: access_token
  C->>A: GET /auth/me и GET /chats с Bearer JWT
  A->>S: проверить JWT
  A->>DB: прочитать профиль и список чатов
  A-->>C: JSON-ответы
```

```mermaid
sequenceDiagram
  actor U as Участник чата
  participant C as React-клиент
  participant W as WebSocket router
  participant DB as SQLAlchemy/SQLite
  participant CM as ConnectionManager
  U->>C: выбрать чат
  C->>W: WS /ws/chats/{id}?token=JWT
  W->>W: проверить подпись и срок JWT
  W->>DB: проверить пользователя и членство в чате
  W-->>C: принять соединение либо закрыть 4401/4403
  U->>C: отправить текст
  C->>W: JSON {body}
  W->>DB: сохранить Message
  W->>CM: разослать сохранённое сообщение участникам
  CM-->>C: JSON MessageResponse
```

WebSocket-соединения хранятся в памяти одного процесса. Сообщение сохраняется до рассылки; проверка членства выполняется при соединении. Аутентификация WebSocket использует JWT из query-параметра.
