from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.crud.user import authenticate_user, create_user, get_user_by_email
from app.db.session import get_db
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo usuario",
)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese email",
        )
    user = await create_user(db, user_in)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Login (OAuth2 password flow) -> devuelve JWT",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Usa el flujo estándar OAuth2 password: recibe `username` (=email) y
    `password` como form-data, no JSON. Esto permite usar directamente
    el botón "Authorize" de Swagger UI.
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(subject=user.email)
    return Token(access_token=access_token)
