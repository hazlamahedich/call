class ComplianceBlockError(Exception):
    def __init__(
        self,
        code: str,
        phone_number: str,
        call_id: int | None = None,
        source: str = "",
        retry_after_seconds: int | None = None,
    ):
        self.code = code
        self.phone_number = phone_number
        self.call_id = call_id
        self.source = source
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            f"[{code}] Phone {phone_number} blocked by {source}"
            + (f" (call_id={call_id})" if call_id else "")
            + (f" — retry after {retry_after_seconds}s" if retry_after_seconds else "")
        )
