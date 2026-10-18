from sqlalchemy import Column, Integer, String
from database import engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    password_hash = Column(String)
    # Base.metadata.create_all(engine) does not automatically add a new column to an existing table 

Base.metadata.create_all(engine)