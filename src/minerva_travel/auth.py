from __future__ import annotations

from typing import Annotated, Any

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from pydantic import BaseModel

from minerva_travel.config import (
    auth_required,
    supabase_jwt_audience,
    supabase_publishable_key,
    supabase_url,
)

ASYMMETRIC_ALGORITHMS = {"RS256", "ES256"}
bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    id: str
    email: str | None = None
    role: str = "authenticated"


class SupabaseTokenVerifier:
    def __init__(
        self,
        *,
        project_url: str,
        publishable_key: str | None,
        audience: str = "authenticated",
    ) -> None:
        self.project_url = project_url.rstrip("/")
        self.publishable_key = publishable_key
        self.audience = audience
        self.issuer = f"{self.project_url}/auth/v1"
        self.jwks_url = f"{self.issuer}/.well-known/jwks.json"

    async def verify(self, token: str) -> AuthenticatedUser:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as error:
            raise unauthorized("Token de acesso malformado.") from error

        algorithm = str(header.get("alg") or "")
        key_id = header.get("kid")
        if algorithm in ASYMMETRIC_ALGORITHMS and key_id:
            claims = await run_in_threadpool(
                self._verify_asymmetric,
                token,
                algorithm,
            )
            return self._user_from_claims(claims)

        return await self._verify_with_auth_server(token)

    def _verify_asymmetric(self, token: str, algorithm: str) -> dict[str, Any]:
        try:
            signing_key = PyJWKClient(
                self.jwks_url,
                cache_keys=True,
                lifespan=600,
                timeout=5,
            ).get_signing_key_from_jwt(token)
            return decode_verified_token(
                token,
                signing_key.key,
                algorithm=algorithm,
                audience=self.audience,
                issuer=self.issuer,
            )
        except jwt.PyJWTError as error:
            raise unauthorized("Token de acesso inválido ou expirado.") from error
        except (OSError, ValueError) as error:
            raise auth_unavailable() from error

    async def _verify_with_auth_server(self, token: str) -> AuthenticatedUser:
        if not self.publishable_key:
            raise auth_unavailable()
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
                response = await client.get(
                    f"{self.issuer}/user",
                    headers={
                        "apikey": self.publishable_key,
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                    },
                )
        except httpx.HTTPError as error:
            raise auth_unavailable() from error

        if response.status_code != 200:
            raise unauthorized("Token de acesso inválido ou expirado.")
        payload = response.json()
        user_id = str(payload.get("id") or "").strip()
        if not user_id:
            raise unauthorized("Token de acesso sem identificação de usuário.")
        return AuthenticatedUser(
            id=user_id,
            email=payload.get("email"),
            role=str(payload.get("role") or "authenticated"),
        )

    def _user_from_claims(self, claims: dict[str, Any]) -> AuthenticatedUser:
        role = str(claims.get("role") or "")
        if role != "authenticated":
            raise unauthorized("Token sem papel de usuário autenticado.")
        return AuthenticatedUser(
            id=str(claims["sub"]),
            email=claims.get("email"),
            role=role,
        )


def decode_verified_token(
    token: str,
    key: Any,
    *,
    algorithm: str,
    audience: str,
    issuer: str,
) -> dict[str, Any]:
    if algorithm not in ASYMMETRIC_ALGORITHMS:
        raise unauthorized("Algoritmo de assinatura não permitido.")
    try:
        return jwt.decode(
            token,
            key=key,
            algorithms=[algorithm],
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "iss", "sub", "role", "aud"]},
        )
    except jwt.PyJWTError as error:
        raise unauthorized("Token de acesso inválido ou expirado.") from error


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> AuthenticatedUser:
    if not auth_required():
        return AuthenticatedUser(id="development-user", role="authenticated")
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized("Autenticação obrigatória.")

    project_url = supabase_url()
    if not project_url:
        raise auth_unavailable()
    verifier = SupabaseTokenVerifier(
        project_url=project_url,
        publishable_key=supabase_publishable_key(),
        audience=supabase_jwt_audience(),
    )
    return await verifier.verify(credentials.credentials)


def unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "unauthorized", "message": message},
        headers={"WWW-Authenticate": "Bearer"},
    )


def auth_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "auth_unavailable",
            "message": "O serviço de autenticação está temporariamente indisponível.",
        },
    )


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
