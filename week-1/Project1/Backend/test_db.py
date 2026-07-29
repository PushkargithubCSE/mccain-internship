from sqlalchemy import create_engine, text

from app.core.config import settings


print("Starting connection test...")

try:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
    )

    with engine.connect() as connection:
        result = connection.execute(text("SELECT version()"))

        print("Connected successfully!")
        print(result.scalar())

except Exception as exc:
    print("Connection failed:")
    print(repr(exc))