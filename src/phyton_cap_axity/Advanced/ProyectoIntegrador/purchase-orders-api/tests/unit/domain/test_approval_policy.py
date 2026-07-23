"""Pruebas unitarias: servicio de dominio ApprovalPolicy."""

from __future__ import annotations

import pytest

from purchase_orders.domain.exceptions.domain_exceptions import (
    UnauthorizedActionError,
)
from purchase_orders.domain.services.approval_policy import ApprovalPolicy

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("role", ["approver_junior", "approver_senior", "admin"])
def test_roles_con_permiso_pueden_aprobar(role: str) -> None:
    assert ApprovalPolicy.can_approve(role) is True


@pytest.mark.parametrize("role", ["requester", "guest", "unknown_role"])
def test_roles_sin_permiso_no_pueden_aprobar(role: str) -> None:
    assert ApprovalPolicy.can_approve(role) is False


def test_admin_tiene_mayor_limite_que_senior_y_junior() -> None:
    junior_limit = ApprovalPolicy.max_approvable_amount("approver_junior")
    senior_limit = ApprovalPolicy.max_approvable_amount("approver_senior")
    admin_limit = ApprovalPolicy.max_approvable_amount("admin")

    assert admin_limit > senior_limit
    assert senior_limit > junior_limit


def test_limite_respeta_la_moneda_solicitada() -> None:
    limit = ApprovalPolicy.max_approvable_amount("approver_senior", currency="EUR")
    assert limit.currency == "EUR"


def test_rol_desconocido_lanza_excepcion() -> None:
    with pytest.raises(UnauthorizedActionError):
        ApprovalPolicy.max_approvable_amount("rol_inexistente")
