from firebase_admin import auth
from fastapi import Request, HTTPException


async def verify_session_token(request: Request):
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        decoded_token = auth.verify_session_cookie(session_cookie, check_revoked=True)
        return decoded_token
    except auth.InvalidSessionCookieError:
        raise HTTPException(status_code=401, detail="Session expired or invalid")