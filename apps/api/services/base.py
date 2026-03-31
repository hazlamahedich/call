from typing import Generic, List, Optional, TypeVar, Type
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import TenantContextError
from models.base import TenantModel

T = TypeVar("T", bound=TenantModel)

_BASE_FIELDS: set[str] = {"id", "org_id", "created_at", "updated_at", "soft_delete"}
_SQLALCHEMY_INTERNALS: set[str] = {
    "_sa_instance_state",
    "_sa_instance_state_hash",
    "_sa_modified",
    "__table__",
    "__tablename__",
}


def _get_model_columns(model: Type[T]) -> List[str]:
    columns = []
    for name, _field_info in model.model_fields.items():
        if name not in _BASE_FIELDS:
            columns.append(name)
    return columns


def _build_select_columns(model: Type[T]) -> str:
    model_cols = _get_model_columns(model)
    return (
        "id, org_id, " + ", ".join(model_cols) + ", created_at, updated_at, soft_delete"
    )


class TenantService(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model
        self.table_name = model.__tablename__
        self._select_cols = _build_select_columns(model)

    async def _ensure_tenant_context(self, session: AsyncSession) -> None:
        result = await session.execute(
            text("SELECT current_setting('app.current_org_id', true)")
        )
        org_id = result.scalar()
        if not org_id:
            raise TenantContextError(
                error_code="TENANT_CONTEXT_MISSING",
                message="No tenant context set",
            )

    def _row_to_instance(self, row) -> T:
        model_cols = _get_model_columns(self.model)
        col_names = (
            ["id", "org_id"] + model_cols + ["created_at", "updated_at", "soft_delete"]
        )
        row_map = {}
        for idx, col_name in enumerate(col_names):
            if idx < len(row):
                row_map[col_name] = row[idx]
        return self.model.model_construct(**row_map)

    async def create(self, session: AsyncSession, record: T) -> T:
        await self._ensure_tenant_context(session)
        columns = []
        values = []
        params = {}
        for idx, (col_name, col_value) in enumerate(
            record.model_dump(exclude=_BASE_FIELDS | _SQLALCHEMY_INTERNALS).items()
        ):
            if col_name in _BASE_FIELDS or col_name in _SQLALCHEMY_INTERNALS:
                continue
            columns.append(col_name)
            if isinstance(col_value, dict):
                values.append(f"CAST(:p{idx} AS jsonb)")
                params[f"p{idx}"] = json.dumps(col_value)
            else:
                values.append(f":p{idx}")
                params[f"p{idx}"] = col_value

        if not columns:
            raise TenantContextError(
                error_code="TENANT_CONTEXT_MISSING",
                message="No columns to insert",
            )

        cols_str = ", ".join(columns)
        vals_str = ", ".join(values)
        stmt = text(
            f"INSERT INTO {self.table_name} ({cols_str}) VALUES ({vals_str}) "
            f"RETURNING id, org_id"
        )
        result = await session.execute(stmt.bindparams(**params))
        row = result.first()
        if not row:
            raise TenantContextError(
                error_code="TENANT_ACCESS_DENIED",
                message="Insert failed — no row returned",
            )
        record.id = row[0]
        record.org_id = row[1]
        await session.flush()
        return record

    async def get_by_id(self, session: AsyncSession, record_id: int) -> Optional[T]:
        stmt = text(
            f"SELECT {self._select_cols} FROM {self.table_name} WHERE id = :record_id"
        )
        result = await session.execute(stmt.bindparams(record_id=record_id))
        row = result.first()
        if row is None:
            return None
        return self._row_to_instance(row)

    async def list_all(
        self, session: AsyncSession, *, limit: int = 100, offset: int = 0
    ) -> List[T]:
        await self._ensure_tenant_context(session)
        stmt = text(
            f"SELECT {self._select_cols} FROM {self.table_name} LIMIT :lim OFFSET :off"
        )
        result = await session.execute(stmt.bindparams(lim=limit, off=offset))
        rows = result.fetchall()
        return [self._row_to_instance(row) for row in rows]

    async def update(self, session: AsyncSession, record: T) -> T:
        if record.id is None:
            raise TenantContextError(
                error_code="TENANT_INVALID_ORG_ID",
                message="Cannot update record with no id",
            )
        updates = []
        params = {"record_id": record.id}
        for col_name, col_value in record.model_dump(
            exclude=_BASE_FIELDS | _SQLALCHEMY_INTERNALS
        ).items():
            if col_name in _BASE_FIELDS or col_name in _SQLALCHEMY_INTERNALS:
                continue
            updates.append(f"{col_name} = :u_{col_name}")
            params[f"u_{col_name}"] = col_value

        updates.append("updated_at = NOW()")
        set_clause = ", ".join(updates)
        stmt = text(
            f"UPDATE {self.table_name} SET {set_clause} "
            f"WHERE id = :record_id RETURNING id"
        )
        result = await session.execute(stmt.bindparams(**params))
        row = result.first()
        if row is None:
            raise TenantContextError(
                error_code="TENANT_ACCESS_DENIED",
                message=f"Update failed for id={record.id} — record not found or RLS blocked",
            )
        await session.flush()
        return record

    async def hard_delete(self, session: AsyncSession, record_id: int) -> bool:
        stmt = text(f"DELETE FROM {self.table_name} WHERE id = :record_id")
        result = await session.execute(stmt.bindparams(record_id=record_id))
        await session.flush()
        return result.rowcount > 0  # type: ignore[union-attr]

    async def mark_soft_deleted(self, session: AsyncSession, record_id: int) -> bool:
        stmt = text(
            f"UPDATE {self.table_name} SET soft_delete = true, updated_at = NOW() "
            f"WHERE id = :record_id AND (soft_delete = false OR soft_delete IS NULL)"
        )
        result = await session.execute(stmt.bindparams(record_id=record_id))
        await session.flush()
        return result.rowcount > 0  # type: ignore[union-attr]
