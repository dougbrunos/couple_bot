import pytest
from app.database.database import engine, Base


@pytest.fixture(autouse=True)
def clean_database():
    """Limpa e recria todas as tabelas antes de cada teste."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
