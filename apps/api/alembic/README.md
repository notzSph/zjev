# Jevzoo database migrations

Schema changes are applied with Alembic, never with runtime `create_all()`.

```bash
alembic -c apps/api/alembic.ini upgrade head
```
