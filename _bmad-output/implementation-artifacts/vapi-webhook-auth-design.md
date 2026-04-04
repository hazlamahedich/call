# Vapi Webhook Authentication Design

**Status:** Approved — Design complete
**Date:** 2026-03-31
**Epic:** Epic 2 prerequisite

## Problem

Vapi sends server-to-server webhooks (`call.started`, `call.ended`, `call.transcription`, etc.) to `apps/api`. These requests come from Vapi's infrastructure, not Clerk-authenticated users. The auth middleware (`apps/api/middleware/auth.py`) validates Clerk JWTs on every request, which is the — whichhook auth is impossible for Vapi since Call's webhook handlers.

## Solution: HMAC-SHA256 Signature Verification

Vapi signs webhook payloads using a shared secret. The shared secret is configured as an environment variable (`VAPI_WEBHOOK_SECRET`).

### Implementation

1. **Environment Variable**: Add `VAPI_WEBHOOK_SECRET` to `apps/api/config/settings.py`:
   ```python
   VAPI_WEBHOOK_SECRET: str = ""
   ```

2. **Auth Middleware Skip Path**: Add `/webhooks/vapi` to `SKIP_AUTH_PATHS` in `apps/api/middleware/auth.py`.

3. **Webhook Signature Validation Helper**: Create `apps/api/middleware/vapi_auth.py`:
   ```python
   import hashlib
   import hmac
   from fastapi import Request, HTTPException, status
   from config.settings import settings

   async def verify_vapi_signature(request: Request) -> None:
       """
       Verify Vapi webhook signature using HMAC-SHA256.

       Vapi sends the header 'vapi-signature' with the HMAC-SHA256
       of the base64 of the the raw body.

       Raises HTTPException(status.HTTP_401) if verification fails.
       """
       signature = request.headers.get("vapi-signature")
       if not signature:
           raise HTTPException(
               status_code=status.HTTP_401,
               detail={"code": "VAPI_SIGNATURE_MISSING", "message": "Missing vapi-signature header"},
           )

       if not settings.VAPI_WEBHOOK_SECRET:
           raise HTTPException(
               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
               detail={"code": "VAPI_NOT_CONFIGURED", "message": "VAPI_WEBHOOK_SECRET not configured"},
           )

       body = await request.body()
       expected = hmac.new(
           settings.VAPI_WEBHOOK_SECRET.encode(),
           body,
           hashlib.sha256,
       ).hexdigest()

       if not hmac.compare_digest(signature, expected):
           raise HTTPException(
               status_code=status.HTTP_401,
               detail={"code": "VAPI_SIGNATURE_INVALID", "message": "Invalid webhook signature"},
           )
   ```

4. **Webhook Route Usage**: Apply `verify_vapi_signature` as a dependency:
   ```python
   from fastapi import APIRouter, Depends
   from middleware.vapi_auth import verify_vapi_signature

   router = APIRouter(prefix="/webhooks/vapi")

   @router.post("/call-events")
   async def handle_call_event(
       request: Request,
       _ = Depends(verify_vapi_signature),
   ):
       ...
   ```

5. **Error Codes**: Add to `packages/constants/index.ts`:
   ```typescript
   export const VAPI_ERROR_CODES = {
     VAPI_SIGNATURE_MISSING: "VAPI_SIGNATURE_MISSING",
     VAPI_SIGNATURE_INVALID: "VAPI_SIGNATURE_INVALID",
     VAPI_NOT_CONFIGURED: "VAPI_NOT_CONFIGURED",
   } as const;
   ```

## Security Considerations

- **Timing Attack Prevention**: Use `hmac.compare_digest()` (constant-time comparison) to prevent timing attacks.
- **Replay Protection**: Include a timestamp or nonce in webhook processing to detect replays.
- **Secret Rotation**: Support `VAPI_WEBHOOK_SECRET` rotation without downtime by accepting both old and new secrets during validation.

## Integration with Existing Auth

- Vapi webhook routes: **NO Clerk JWT** — uses `verify_vapi_signature` dependency only
- All other routes: Continue using Clerk JWT via `AuthMiddleware`
- Usage guard: Vapi's `POST /calls/trigger` (Epic 2) should use `check_call_cap` dependency
