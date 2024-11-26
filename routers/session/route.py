from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta, timezone
from firebase_admin import auth, exceptions



router = APIRouter()

@router.post('/sessionLogin')
async def session_login(request: Request):
    if request.cookies.get('session'):
        return JSONResponse(content={'status': 'already_logged_in'})
    
    body = await request.json()
    id_token = body.get('idToken')
    if not id_token:
        raise HTTPException(status_code=400, detail="ID token is required")

    expires_in = timedelta(hours=1)
    try:
        session_cookie = auth.create_session_cookie(id_token, expires_in=expires_in)
        response = JSONResponse(content={'status': 'success'})
        expires = datetime.now(timezone.utc) + expires_in  # Ensure expires is in UTC
        response.set_cookie(
            key='session', value=session_cookie, expires=expires, httponly=True, secure=True, samesite='None')
        return response
    except exceptions.FirebaseError:
        raise HTTPException(status_code=401, detail="Failed to create a session cookie")

@router.post('/check_session')
async def access_restricted_content(request: Request):
    session_cookie = request.cookies.get('session')
    if not session_cookie:
        # Session cookie is unavailable. Inform the frontend to handle login.
        return JSONResponse(content={'error': 'Session cookie is unavailable. Please login.'}, status_code=401)

    # Verify the session cookie. In this case an additional check is added to detect
    # if the user's Firebase session was revoked, user deleted/disabled, etc.
    try:
        decoded_claims = auth.verify_session_cookie(session_cookie, check_revoked=True)
        return serve_content_for_user(decoded_claims)
    except auth.InvalidSessionCookieError:
        # Session cookie is invalid, expired or revoked. Inform the frontend to handle login.
        return JSONResponse(content={'error': 'Invalid session cookie. Please login again.'}, status_code=401)

def serve_content_for_user(decoded_claims):
    # Implement the logic to serve content for the user based on decoded_claims
    return JSONResponse(content={'status': 'content_served', 'claims': decoded_claims})


@router.post('/sessionLogout')
async def session_logout():
    response = JSONResponse(content={'status': 'logged_out'})
    response.delete_cookie('session', samesite='None',httponly=True, secure=True)
    return response

