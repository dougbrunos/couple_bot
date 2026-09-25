import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import app.database.database as db_mod

# Banco de testes isolado em SQLite em memória para garantir velocidade e segurança
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Sobrescreve o engine e SessionLocal do módulo para os testes
db_mod.engine = test_engine
db_mod.SessionLocal = TestingSessionLocal


@pytest.fixture(autouse=True)
def clean_database():
    """Limpa e recria todas as tabelas no banco de testes em memória antes de cada teste."""
    db_mod.Base.metadata.drop_all(bind=test_engine)
    db_mod.Base.metadata.create_all(bind=test_engine)
    yield
