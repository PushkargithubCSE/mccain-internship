from app.core.exceptions import AppException
@router.get("/ping")
async def ping():

    raise AppException(
        status_code=400,
        message="Demo Exception",
        error_code="DEMO_EXCEPTION"
    )