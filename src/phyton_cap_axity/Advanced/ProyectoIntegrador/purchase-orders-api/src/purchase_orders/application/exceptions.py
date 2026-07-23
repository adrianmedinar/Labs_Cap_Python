"""Excepciones de la capa de aplicación.

Se distinguen de las excepciones de dominio porque representan fallos
propios de la orquestación de casos de uso (credenciales inválidas,
recurso no encontrado desde la perspectiva del caso de uso, etc), no
violaciones de reglas de negocio puras del agregado.
"""

from __future__ import annotations


class ApplicationError(Exception):
    """Excepción base para errores de la capa de aplicación."""


class InvalidCredentialsError(ApplicationError):
    def __init__(self) -> None:
        super().__init__("Usuario o contraseña inválidos.")


class UsernameAlreadyExistsError(ApplicationError):
    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__(f"El nombre de usuario '{username}' ya existe.")


class ResourceNotFoundError(ApplicationError):
    def __init__(self, resource: str, identifier: object) -> None:
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} no encontrado: {identifier}.")
