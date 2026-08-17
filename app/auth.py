import os
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

load_dotenv()

router = APIRouter(prefix="/auth", tags=["auth"])

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 30

# For local dev. Change to your deployed frontend URL later.
GITHUB_CALLBACK_URL = "http://localhost:8000/auth/callback"
FRONTEND_URL = "http://localhost:5500"  # wherever your HTML/JS frontend runs

bearer_scheme = HTTPBearer()


# ---------- JWT helpers ----------

def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    user_id = decode_access_token(credentials.credentials)
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ---------- OAuth routes ----------

@router.get("/login")
def login():
    """Redirect the user to GitHub's OAuth consent screen."""
    github_auth_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_CALLBACK_URL}"
        "&scope=read:user"
    )
    return RedirectResponse(github_auth_url)


@router.get("/callback")
async def callback(code: str, db: Session = Depends(get_db)):
    """GitHub redirects here after the user approves the app."""
    async with httpx.AsyncClient() as client:
        # 1. Exchange the temporary code for an access token
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_CALLBACK_URL,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()
        github_access_token = token_data.get("access_token")

        if not github_access_token:
            raise HTTPException(status_code=400, detail="GitHub OAuth failed")

        # 2. Use that token to fetch the user's GitHub profile
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {github_access_token}"},
        )
        gh_user = user_resp.json()

    github_id = str(gh_user["id"])
    username = gh_user.get("login")
    email = gh_user.get("email")
    avatar_url = gh_user.get("avatar_url")

    # 3. Find or create the local user record
    user = db.query(User).filter(User.github_id == github_id).first()
    if user is None:
        user = User(
            github_id=github_id,
            username=username,
            email=email,
            avatar_url=avatar_url,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 4. Issue our own JWT and send the user back to the frontend with it
    jwt_token = create_access_token(user.id)
    return RedirectResponse(f"{FRONTEND_URL}/?token={jwt_token}")


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "avatar_url": current_user.avatar_url,
        "is_verified_solver": current_user.is_verified_solver,
    }
