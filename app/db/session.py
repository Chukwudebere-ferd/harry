from app.core.config import settings
from app.db.base import create_engine, create_session_factory

engine = create_engine(settings.database_url)
SessionLocal = create_session_factory(engine)
