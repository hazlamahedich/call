from dependencies.org_context import (
    get_current_org_id,
    get_current_user_id,
    get_optional_org_id,
    get_optional_user_id,
)

from middleware.auth import AuthMiddleware

from routers.health import router as health_router
from routers.webhooks import router as webhooks_router

from database.session import set_tenant_context, TenantContextError

from services.base import TenantService

from models.lead import Lead
