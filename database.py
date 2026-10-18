from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:mini_postgres@localhost/photo_retrieval"

engine = create_engine(DATABASE_URL)

with engine.connect() as connection:
    result = connection.execute(text("SELECT 1"))
    print(result.fetchone())


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)