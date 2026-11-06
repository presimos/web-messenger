# Backend

FastAPI-приложение. Для локального запуска используется Python 3.11 или новее.

Из папки `backend` выполните:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Проверка: `http://127.0.0.1:8000/health`. Страница API: `/docs`.
