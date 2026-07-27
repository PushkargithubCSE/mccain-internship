from sqlalchemy import create_engine, text


print("Starting connection test...")

try:
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print("Connected successfully!")

        result = conn.execute(text("SELECT version()"))
        print(result.fetchone())

except Exception as e:
    print("Connection failed:")
    print(repr(e))