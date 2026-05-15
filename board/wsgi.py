from app import app, init_db

init_db()

# mod_wsgi 등 일부 스택은 `application` 이름을 기대합니다.
application = app
