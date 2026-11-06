# Веб-мессенджер

Учебный проект для производственной практики ПМ01.

## Запуск backend в Windows

Требуется Python 3.11 или новее.

```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Проверка: открыть `http://127.0.0.1:8000/health`. Документация API доступна
по адресу `http://127.0.0.1:8000/docs`.

## Этапы разработки

1. Каркас проекта и проверка запуска API.
2. Подключение SQLAlchemy и модели пользователей, чатов и сообщений.
3. Регистрация, вход пользователей и проверка JWT.
4. Чаты, история и обмен сообщениями через WebSocket.
5. Клиент на React и TypeScript.
6. Проверки Pytest и описание результата.

По умолчанию backend создаёт локальную базу SQLite. Для PostgreSQL задайте
`DATABASE_URL` по образцу `backend/.env.example` в файле `backend/.env`.

Проверки backend запускаются командой `python -m pytest` из папки `backend`.

Каждый завершённый этап фиксируется отдельным коммитом.

## Регистрация и вход

- `POST /auth/register` — создать пользователя.
- `POST /auth/login` — получить JWT-токен.
- `GET /auth/me` — получить профиль с заголовком `Authorization: Bearer <токен>`.
- `POST /chats` — создать чат и добавить участников по именам пользователей.
- `GET /chats` — получить список чатов пользователя.
- `GET /chats/{id}/messages` — получить последние сообщения чата.
- `WS /ws/chats/{id}?token=<токен>` — подключиться к чату и обмениваться сообщениями.

Секрет для JWT задаётся переменной `SECRET_KEY` в `backend/.env`.
WebSocket-рассылка хранит активные подключения в памяти и рассчитана на один
процесс backend.
