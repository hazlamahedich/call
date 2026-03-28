from datetime import datetime
from typing import Generic, List, Optional, TypeVar, Type

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import TenantContextError
from models.base import TenantModel

T = TypeVar("T", bound=TenantModel)


class TenantService(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model
        self.table_name = model.__tablename__

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

    async def create(self, session: AsyncSession, record: T) -> T:
        await self._ensure_tenant_context(session)
        columns = []
        values = []
        params = {}
        for idx, (col_name, col_value) in enumerate(record.__dict__.items()):
            if col_name.startswith("_") or col_name == "id":
                continue
            if col_value is not None:
                columns.append(col_name)
                values.append(f":p{idx}")
                params[f"p{idx}"] = col_value

        cols_str = ", ".join(columns)
        vals_str = ", ".join(values)
        stmt = text(
            f"INSERT INTO {self.table_name} ({cols_str}) VALUES ({vals_str}) "
            f"RETURNING id, org_id"
        )
        result = await session.execute(stmt.bindparams(**params))
        row = result.first()
        if row:
            record.id = row[0]
            record.org_id = row[1]
        await session.flush()
        return record

    async def get_by_id(self, session: AsyncSession, record_id: int) -> Optional[T]:
        stmt = text(
            f"SELECT id, org_id, name, email, phone, status, created_at, updated_at, soft_delete "
            f"FROM {self.table_name} WHERE id = :record_id"
        )
        result = await session.execute(stmt.bindparams(record_id=record_id))
        row = result.first()
        if row is None:
            return None
        instance = self.model(
            id=row[0],
            org_id=row[1],
            name=row[2],
            email=row[3],
            phone=row[4],
            status=row[5],
            created_at=row[6],
            updated_at=row[7],
            soft_delete=row[8],
        )
        return instance

    async def list_all(
        self, session: AsyncSession, *, limit: int = 100, offset: int = 0
    ) -> List[T]:
        stmt = text(
            f"SELECT id, org_id, name, email, phone, status, created_at, updated_at, soft_delete "
            f"FROM {self.table_name} LIMIT :lim OFFSET :off"
        )
        result = await session.execute(stmt.bindparams(lim=limit, off=offset))
        rows = result.fetchall()
        return [
            self.model(
                id=row[0],
                org_id=row[1],
                name=row[2],
                email=row[3],
                phone=row[4],
                status=row[5],
                created_at=row[6],
                updated_at=row[7],
                soft_delete=row[8],
            )
            for row in rows
        ]

    async def update(self, session: AsyncSession, record: T) -> T:
        updates = []
        params = {"record_id": record.id}
        for col_name, col_value in record.__dict__.items():
            if col_name.startswith("_") or col_name in (
                "id",
                "org_id",
                "updated_at",
                "created_at",
            ):
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
            return record
        await session.flush()
        return record

    async def delete(self, session: AsyncSession, record_id: int) -> bool:
        stmt = text(f"DELETE FROM {self.table_name} WHERE id = :record_id")
        result = await session.execute(stmt.bindparams(record_id=record_id))
        await session.flush()
        return result.rowcount > 0

    async def soft_delete(self, session: AsyncSession, record_id: int) -> bool:
        stmt = text(
            f"UPDATE {self.table_name} SET soft_delete = true, updated_at = NOW() "
            f"WHERE id = :record_id AND (soft_delete = false OR soft_delete IS NULL)"
        )
        result = await session.execute(stmt.bindparams(record_id=record_id))
        await session.flush()
        return result.rowcount > 0
