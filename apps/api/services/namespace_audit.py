"""Cross-tenant isolation audit service.

Automated verification that RLS policies correctly block cross-tenant access
on knowledge_bases and knowledge_chunks tables.
"""

import logging
from datetime import datetime, timezone
from typing import List

from pydantic import BaseModel, AliasGenerator, Field
from pydantic.alias_generators import to_camel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings

logger = logging.getLogger(__name__)


class AuditCheck(BaseModel):
    check_type: str
    org_a: str = Field(alias="orgA")
    org_b: str = Field(alias="orgB")
    passed: bool
    details: str

    class Config:
        alias_generator = AliasGenerator(to_camel)
        populate_by_name = True


class AuditReport(BaseModel):
    timestamp: str
    total_checks: int
    passed: int
    failed: int
    details: List[AuditCheck] = Field(default_factory=list)
    tenant_count: int
    pairs_checked: int
    pairs_skipped: int

    class Config:
        alias_generator = AliasGenerator(to_camel)
        populate_by_name = True


class NamespaceAuditService:
    async def run_isolation_audit(self, session: AsyncSession) -> AuditReport:
        active_orgs_result = await session.execute(
            text(
                "SELECT DISTINCT org_id FROM knowledge_bases "
                "WHERE status = 'ready' AND soft_delete = false"
            )
        )
        org_ids = [row[0] for row in active_orgs_result.fetchall()]

        if len(org_ids) < 2:
            return AuditReport(
                timestamp=datetime.now(timezone.utc).isoformat(),
                total_checks=0,
                passed=0,
                failed=0,
                details=[],
                tenant_count=len(org_ids),
                pairs_checked=0,
                pairs_skipped=0,
            )

        max_pairs = settings.NAMESPACE_AUDIT_MAX_PAIRS
        pairs: list[tuple[str, str]] = []
        for i, org_a in enumerate(org_ids):
            for org_b in org_ids[i + 1 :]:
                if len(pairs) >= max_pairs:
                    break
                pairs.append((org_a, org_b))
            if len(pairs) >= max_pairs:
                break

        total_possible_pairs = len(org_ids) * (len(org_ids) - 1) // 2
        pairs_skipped = max(0, total_possible_pairs - len(pairs))

        checks: List[AuditCheck] = []

        for org_a, org_b in pairs:
            kb_check = await self._verify_cross_tenant_kb(session, org_a, org_b)
            checks.append(kb_check)

            chunk_check = await self._verify_cross_tenant_chunk(session, org_a, org_b)
            checks.append(chunk_check)

            vector_check = await self._verify_cross_tenant_vector(session, org_a, org_b)
            checks.append(vector_check)

        passed = sum(1 for c in checks if c.passed)
        failed = sum(1 for c in checks if not c.passed)

        report = AuditReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_checks=len(checks),
            passed=passed,
            failed=failed,
            details=checks,
            tenant_count=len(org_ids),
            pairs_checked=len(pairs),
            pairs_skipped=pairs_skipped,
        )

        if failed > 0:
            logger.error(
                "Namespace isolation audit FAILED",
                extra={
                    "code": "NAMESPACE_AUDIT_FAILED",
                    "total_checks": len(checks),
                    "passed": passed,
                    "failed": failed,
                    "pairs_checked": len(pairs),
                },
            )
        else:
            logger.info(
                "Namespace isolation audit PASSED",
                extra={
                    "total_checks": len(checks),
                    "passed": passed,
                    "pairs_checked": len(pairs),
                },
            )

        return report

    async def _verify_cross_tenant_kb(
        self, session: AsyncSession, org_a: str, org_b: str
    ) -> AuditCheck:
        await session.execute(
            text("SELECT set_config('app.current_org_id', :org_id, false)"),
            {"org_id": org_a},
        )
        result = await session.execute(
            text(
                "SELECT COUNT(*) FROM knowledge_bases "
                "WHERE org_id = :other_org AND soft_delete = false AND status = 'ready'"
            ),
            {"other_org": org_b},
        )
        count = result.scalar()
        return AuditCheck(
            check_type="rls_cross_tenant_kb",
            org_a=org_a,
            org_b=org_b,
            passed=(count == 0),
            details=f"RLS returned {count} rows (expected 0)",
        )

    async def _verify_cross_tenant_chunk(
        self, session: AsyncSession, org_a: str, org_b: str
    ) -> AuditCheck:
        await session.execute(
            text("SELECT set_config('app.current_org_id', :org_id, false)"),
            {"org_id": org_a},
        )
        result = await session.execute(
            text(
                "SELECT COUNT(*) FROM knowledge_chunks "
                "WHERE org_id = :other_org AND soft_delete = false"
            ),
            {"other_org": org_b},
        )
        count = result.scalar()
        return AuditCheck(
            check_type="rls_cross_tenant_chunk",
            org_a=org_a,
            org_b=org_b,
            passed=(count == 0),
            details=f"RLS returned {count} rows (expected 0)",
        )

    async def _verify_cross_tenant_vector(
        self, session: AsyncSession, org_a: str, org_b: str
    ) -> AuditCheck:
        await session.execute(
            text("SELECT set_config('app.current_org_id', :org_id, false)"),
            {"org_id": org_a},
        )
        result = await session.execute(
            text(
                "SELECT COUNT(*) FROM knowledge_chunks kc "
                "JOIN knowledge_bases kb ON kc.knowledge_base_id = kb.id "
                "WHERE kc.org_id = :other_org "
                "AND kc.soft_delete = false "
                "AND kb.status = 'ready' "
                "AND kb.soft_delete = false"
            ),
            {"other_org": org_b},
        )
        count = result.scalar()
        return AuditCheck(
            check_type="vector_search_cross_tenant",
            org_a=org_a,
            org_b=org_b,
            passed=(count == 0),
            details=f"Cross-tenant vector search returned {count} rows (expected 0)",
        )
