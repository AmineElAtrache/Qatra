from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.domain.models import Farmer

bearer = HTTPBearer(auto_error=False)

ALLOWED_ROLES = frozenset({"farmer", "advisor"})


def get_current_farmer(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Farmer:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    farmer = db.get(Farmer, int(payload["sub"]))
    if not farmer:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if farmer.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid role")
    return farmer


def require_advisor(user: Farmer = Depends(get_current_farmer)) -> Farmer:
    if user.role != "advisor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Advisor role required")
    return user
