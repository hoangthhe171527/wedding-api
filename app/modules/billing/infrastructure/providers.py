"""Lắp ráp phụ thuộc của `billing` — nơi DUY NHẤT biết `template` và MoMo tồn tại."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.billing.application.use_cases import (
    CancelOrder,
    ConfirmOrder,
    CreateOrder,
    GetBilling,
    GetOrder,
    GrantPlan,
    ListOrders,
    ListPaymentEvents,
    RecordBankTransfer,
    RecordMomoIpn,
    SimulatePayment,
    StudioPlans,
    VerifyApplePurchase,
)
from app.modules.billing.infrastructure.external.apple_iap import AppleIapVerifier
from app.modules.billing.infrastructure.external.momo import HttpMomoGateway
from app.modules.billing.infrastructure.external.plan_waiver import AdminPlanWaiver
from app.modules.billing.infrastructure.persistence.repositories import (
    BeanieApplePurchaseRepository,
    BeanieOrderRepository,
    BeaniePaymentEventRepository,
)
from app.modules.identity import build_studio_directory


def provide_get_billing() -> GetBilling:
    return GetBilling(BeanieOrderRepository(), HttpMomoGateway(), AdminPlanWaiver())


def provide_create_order() -> CreateOrder:
    return CreateOrder(BeanieOrderRepository(), HttpMomoGateway())


def provide_get_order() -> GetOrder:
    return GetOrder(BeanieOrderRepository())


def provide_cancel_order() -> CancelOrder:
    return CancelOrder(BeanieOrderRepository())


def provide_simulate_payment() -> SimulatePayment:
    return SimulatePayment(BeanieOrderRepository())


def provide_record_bank_transfer() -> RecordBankTransfer:
    return RecordBankTransfer(BeanieOrderRepository(), BeaniePaymentEventRepository())


def provide_record_momo_ipn() -> RecordMomoIpn:
    return RecordMomoIpn(BeanieOrderRepository(), BeaniePaymentEventRepository())


def provide_list_orders() -> ListOrders:
    return ListOrders(BeanieOrderRepository())


def provide_list_payment_events() -> ListPaymentEvents:
    return ListPaymentEvents(BeaniePaymentEventRepository())


def provide_confirm_order() -> ConfirmOrder:
    return ConfirmOrder(BeanieOrderRepository())


def provide_grant_plan() -> GrantPlan:
    return GrantPlan(BeanieOrderRepository(), build_studio_directory())


def provide_studio_plans() -> StudioPlans:
    return StudioPlans(BeanieOrderRepository())


def provide_verify_apple_purchase() -> VerifyApplePurchase:
    return VerifyApplePurchase(
        BeanieOrderRepository(),
        BeanieApplePurchaseRepository(),
        AppleIapVerifier(),
    )


GrantPlanDep = Annotated[GrantPlan, Depends(provide_grant_plan)]
StudioPlansDep = Annotated[StudioPlans, Depends(provide_studio_plans)]
VerifyApplePurchaseDep = Annotated[VerifyApplePurchase, Depends(provide_verify_apple_purchase)]
GetBillingDep = Annotated[GetBilling, Depends(provide_get_billing)]
CreateOrderDep = Annotated[CreateOrder, Depends(provide_create_order)]
GetOrderDep = Annotated[GetOrder, Depends(provide_get_order)]
CancelOrderDep = Annotated[CancelOrder, Depends(provide_cancel_order)]
SimulatePaymentDep = Annotated[SimulatePayment, Depends(provide_simulate_payment)]
RecordBankTransferDep = Annotated[RecordBankTransfer, Depends(provide_record_bank_transfer)]
RecordMomoIpnDep = Annotated[RecordMomoIpn, Depends(provide_record_momo_ipn)]
ListOrdersDep = Annotated[ListOrders, Depends(provide_list_orders)]
ListPaymentEventsDep = Annotated[ListPaymentEvents, Depends(provide_list_payment_events)]
ConfirmOrderDep = Annotated[ConfirmOrder, Depends(provide_confirm_order)]

__all__ = [
    "CancelOrderDep",
    "ConfirmOrderDep",
    "CreateOrderDep",
    "GetBillingDep",
    "GetOrderDep",
    "GrantPlanDep",
    "ListOrdersDep",
    "ListPaymentEventsDep",
    "RecordBankTransferDep",
    "RecordMomoIpnDep",
    "SimulatePaymentDep",
    "StudioPlansDep",
    "VerifyApplePurchaseDep",
]
