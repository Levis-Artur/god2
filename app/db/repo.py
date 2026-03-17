from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, desc, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.constants import DEFAULT_DEPTH, DEPTH_OPTIONS
from app.db.models import Base, SearchRequest, User


class HistoryRepo:
    """Minimal repository for users, search history, and per-user settings."""

    def __init__(self, database_url: str) -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine = create_engine(
            database_url,
            echo=False,
            future=True,
            connect_args=connect_args,
        )
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    def init_db(self) -> None:
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_or_get_user(
        self,
        telegram_user_id: int,
        username: str | None = None,
        first_name: str | None = None,
    ) -> User:
        with self.session() as session:
            user = self._get_or_create_user(
                session=session,
                telegram_user_id=telegram_user_id,
                username=username,
                first_name=first_name,
            )
            session.commit()
            session.refresh(user)
            return user

    def save_search_request(
        self,
        telegram_user_id: int,
        search_type: str,
        original_query: str,
        normalized_query: str,
        result_status: str,
        short_result_preview: str,
        username: str | None = None,
        first_name: str | None = None,
    ) -> SearchRequest:
        with self.session() as session:
            user = self._get_or_create_user(
                session=session,
                telegram_user_id=telegram_user_id,
                username=username,
                first_name=first_name,
            )
            item = SearchRequest(
                user_id=user.id,
                search_type=search_type,
                original_query=original_query,
                normalized_query=normalized_query,
                result_status=result_status,
                short_result_preview=short_result_preview,
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def get_last_searches_for_user(self, telegram_user_id: int, limit: int = 5) -> list[SearchRequest]:
        with self.session() as session:
            statement = (
                select(SearchRequest)
                .join(User, SearchRequest.user_id == User.id)
                .where(User.telegram_user_id == telegram_user_id)
                .order_by(desc(SearchRequest.created_at))
                .limit(limit)
            )
            return list(session.scalars(statement).all())

    def get_search_request_for_user(
        self,
        request_id: int,
        telegram_user_id: int,
    ) -> SearchRequest | None:
        with self.session() as session:
            statement = (
                select(SearchRequest)
                .join(User, SearchRequest.user_id == User.id)
                .where(SearchRequest.id == request_id, User.telegram_user_id == telegram_user_id)
            )
            return session.scalar(statement)

    def get_search_depth(
        self,
        telegram_user_id: int,
        username: str | None = None,
        first_name: str | None = None,
    ) -> int:
        with self.session() as session:
            user = self._get_or_create_user(
                session=session,
                telegram_user_id=telegram_user_id,
                username=username,
                first_name=first_name,
            )
            session.commit()
            return user.search_depth

    def update_search_depth(
        self,
        telegram_user_id: int,
        depth: int,
        username: str | None = None,
        first_name: str | None = None,
    ) -> int:
        if depth not in DEPTH_OPTIONS:
            raise ValueError(f"Unsupported depth: {depth}")

        with self.session() as session:
            user = self._get_or_create_user(
                session=session,
                telegram_user_id=telegram_user_id,
                username=username,
                first_name=first_name,
                default_depth=depth,
            )
            user.search_depth = depth
            session.commit()
            return depth

    def _get_or_create_user(
        self,
        session: Session,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
        default_depth: int = DEFAULT_DEPTH,
    ) -> User:
        user = self._get_user_by_telegram_id(session, telegram_user_id)
        if user is None:
            user = User(
                telegram_user_id=telegram_user_id,
                username=username,
                first_name=first_name,
                search_depth=default_depth,
            )
            session.add(user)
            session.flush()
            return user

        self._sync_user_fields(user=user, username=username, first_name=first_name)
        return user

    def _sync_user_fields(
        self,
        user: User,
        username: str | None,
        first_name: str | None,
    ) -> None:
        if username is not None and username != user.username:
            user.username = username
        if first_name is not None and first_name != user.first_name:
            user.first_name = first_name

    def _get_user_by_telegram_id(self, session: Session, telegram_user_id: int) -> User | None:
        statement = select(User).where(User.telegram_user_id == telegram_user_id)
        return session.scalar(statement)
