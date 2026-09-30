"""Router HTTP của `billing`.

| Method | Path                                         | Quyền                          |
|--------|----------------------------------------------|--------------------------------|
| GET    | /api/v1/billing/plans                        | công khai (các gói, không giá) |
| GET    | /api/v1/billing/contact                      | công khai (Zalo tư vấn)        |
| GET    | /api/v1/billing                              | `studio.manage`                |
| POST   | /api/v1/billing/orders                       | `studio.manage`                |
| GET    | /api/v1/billing/orders/{id}                  | `studio.manage`                |
| POST   | /api/v1/billing/orders/{id}/cancel           | `studio.manage`                |
| POST   | /api/v1/billing/orders/{id}/simulate-paid    | `studio.manage`, chỉ giả lập   |
| POST   | /api/v1/billing/webhooks/bank                | khoá `Authorization: Apikey …` |
| POST   | /api/v1/billing/webhooks/momo                | chữ ký HMAC của MoMo           |
| GET    | /api/v1/admin/orders                         | `studio.oversee`               |
| POST   | /api/v1/admin/orders/{id}/confirm            | `studio.oversee`               |
| GET    | /api/v1/admin/payment-events                 | `studio.oversee`               |
| POST   | /api/v1/admin/studios/{id}/plan              | `studio.oversee` (cấp gói)     |
| GET    | /api/v1/admin/studio-plans?ids=              | `studio.oversee`               |
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status

from app.core import rate_limit
from app.core.context import ActorContext
from app.core.dependencies import require_permissions
from app.core.errors import ValidationError
from app.core.pagination import PageParams, page_params
from app.core.permissions import Permission
from app.core.responses import PaginatedEnvelope, ResponseEnvelope, ok, ok_list, ok_page
from app.modules.billing.application.use_cases import BankTransfer, PlanGrant
from app.modules.billing.domain.enums import PLAN_SPECS
from app.modules.billing.infrastructure.providers import (
    CancelOrderDep,
    ConfirmOrderDep,
    CreateOrderDep,
    GetBillingDep,
    GetOrderDep,
    GrantPlanDep,
    ListOrdersDep,
    ListPaymentEventsDep,
    RecordBankTransferDep,
    RecordMomoIpnDep,
    SimulatePaymentDep,
    StudioPlansDep,
    VerifyApplePurchaseDep,
)
from app.modules.billing.interfaces.http.schemas import (
    AppleIapVerifyIn,
    AppleIapVerifyOut,
    BankWebhookIn,
    BillingOut,
    ConfirmIn,
    ContactOut,
    GrantIn,
    LabelOut,
    OrderIn,
    OrderOut,
    OrderStatus,
    PaymentEventOut,
    PlanOut,
    StudioPlanOut,
    WebhookAckOut,
    all_plans,
    current_contact,
)

router = APIRouter(tags=["Gói dịch vụ"])

StudioEditor = Annotated[ActorContext, require_permissions(Permission.STUDIO_MANAGE)]
Operator = Annotated[ActorContext, require_permissions(Permission.STUDIO_OVERSEE)]

#: Tạo đơn là thao tác người thật; vài chục lần một giờ đã là bất thường.
_ORDER_LIMIT_PER_HOUR = 30


@router.get("/billing/plans", response_model=ResponseEnvelope[list[PlanOut]], summary="Bảng giá")
async def list_plans() -> dict[str, Any]:
    """Công khai — trang giới thiệu và bảng giá đọc từ đây, không hardcode giá ở web."""
    return ok_list(all_plans())


@router.get("/billing/contact", response_model=ResponseEnvelope[ContactOut], summary="Zalo tư vấn")
async def contact() -> dict[str, Any]:
    """Công khai — trang giới thiệu hiện nút nhắn Zalo tư vấn."""
    return ok(current_contact())


@router.get("/billing", response_model=ResponseEnvelope[BillingOut], summary="Gói của xưởng")
async def get_billing(actor: StudioEditor, use_case: GetBillingDep) -> dict[str, Any]:
    return ok(BillingOut.of(await use_case.execute(actor)))


@router.post(
    "/billing/iap/apple/verify",
    response_model=ResponseEnvelope[AppleIapVerifyOut],
    summary="Xác thực giao dịch App Store",
)
async def verify_apple_iap(
    payload: AppleIapVerifyIn,
    actor: StudioEditor,
    use_case: VerifyApplePurchaseDep,
) -> dict[str, Any]:
    grant = await use_case.execute(
        actor,
        product_id=payload.product_id,
        transaction_id=payload.transaction_id,
        signed_transaction=payload.signed_transaction,
    )
    return ok(
        AppleIapVerifyOut(
            transaction_id=grant.transaction_id,
            plan=LabelOut(slug=grant.plan.value, label=PLAN_SPECS[grant.plan].label),
            current_plan=LabelOut(
                slug=grant.current_plan.value,
                label=PLAN_SPECS[grant.current_plan].label,
            ),
            activated=grant.activated,
        )
    )


@router.post(
    "/billing/orders",
    response_model=ResponseEnvelope[OrderOut],
    status_code=status.HTTP_201_CREATED,
    summary="Mua hoặc nâng cấp gói",
)
async def create_order(
    payload: OrderIn, actor: StudioEditor, use_case: CreateOrderDep
) -> dict[str, Any]:
    await rate_limit.guard(
        "billing_order",
        str(actor.tenant_id),
        limit=_ORDER_LIMIT_PER_HOUR,
        window_seconds=3600,
        message="Bạn tạo đơn quá nhiều lần. Vui lòng thử lại sau.",
        code="order_rate_limited",
    )
    return ok(OrderOut.of(await use_case.execute(actor, payload.plan, payload.method)))


@router.get(
    "/billing/orders/{order_id}", response_model=ResponseEnvelope[OrderOut], summary="Một đơn"
)
async def get_order(order_id: UUID, actor: StudioEditor, use_case: GetOrderDep) -> dict[str, Any]:
    return ok(OrderOut.of(await use_case.execute(actor, order_id)))


@router.post(
    "/billing/orders/{order_id}/cancel",
    response_model=ResponseEnvelope[OrderOut],
    summary="Huỷ đơn chờ thanh toán",
)
async def cancel_order(
    order_id: UUID, actor: StudioEditor, use_case: CancelOrderDep
) -> dict[str, Any]:
    return ok(OrderOut.of(await use_case.execute(actor, order_id)))


@router.post(
    "/billing/orders/{order_id}/simulate-paid",
    response_model=ResponseEnvelope[OrderOut],
    summary="Giả lập đã thanh toán (chỉ local/test)",
)
async def simulate_paid(
    order_id: UUID, actor: StudioEditor, use_case: SimulatePaymentDep
) -> dict[str, Any]:
    return ok(OrderOut.of(await use_case.execute(actor, order_id)))


@router.post(
    "/billing/webhooks/bank",
    response_model=WebhookAckOut,
    summary="Webhook báo có của tài khoản nhận tiền",
)
async def bank_webhook(
    payload: BankWebhookIn,
    use_case: RecordBankTransferDep,
    authorization: Annotated[str, Header()] = "",
) -> dict[str, Any]:
    """Xác thực bằng `Authorization: Apikey <BANK_WEBHOOK_KEY>`.

    Trả 200 cả khi tiền không khớp đơn nào (đã ghi sổ để đối soát): trả lỗi thì
    dịch vụ sẽ gửi lại mãi cùng một giao dịch.
    """
    scheme, _, key = authorization.partition(" ")
    result = await use_case.execute(
        key.strip() if scheme.lower() == "apikey" else "",
        BankTransfer(
            external_id=str(payload.id),
            amount=payload.transfer_amount,
            content=payload.content,
            direction=payload.transfer_type.lower(),
            raw=payload.model_dump(by_alias=True),
        ),
    )
    return {"success": True, "status": result.value}


@router.post(
    "/billing/webhooks/momo",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="IPN của MoMo",
)
async def momo_ipn(request: Request, use_case: RecordMomoIpnDep) -> Response:
    try:
        payload = await request.json()
    except ValueError:
        raise ValidationError("Thân IPN không phải JSON.", code="momo_bad_body") from None
    if not isinstance(payload, dict):
        raise ValidationError("Thân IPN không hợp lệ.", code="momo_bad_body")
    await use_case.execute(payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/admin/orders",
    response_model=PaginatedEnvelope[OrderOut],
    tags=["Quản trị hệ thống"],
    summary="Đơn hàng (đối soát)",
)
async def admin_orders(
    actor: Operator,
    use_case: ListOrdersDep,
    params: Annotated[PageParams, Depends(page_params)],
    order_status: Annotated[OrderStatus | None, Query(alias="status")] = None,
) -> dict[str, Any]:
    del actor
    page = await use_case.execute(params, order_status)
    return ok_page(page.map(lambda item: OrderOut.of(item, admin=True)))


@router.post(
    "/admin/orders/{order_id}/confirm",
    response_model=ResponseEnvelope[OrderOut],
    tags=["Quản trị hệ thống"],
    summary="Xác nhận đã thanh toán bằng tay",
)
async def admin_confirm_order(
    order_id: UUID, payload: ConfirmIn, actor: Operator, use_case: ConfirmOrderDep
) -> dict[str, Any]:
    return ok(OrderOut.of(await use_case.execute(actor, order_id, payload.note), admin=True))


@router.get(
    "/admin/payment-events",
    response_model=ResponseEnvelope[list[PaymentEventOut]],
    tags=["Quản trị hệ thống"],
    summary="Sổ báo có (đối soát)",
)
async def admin_payment_events(actor: Operator, use_case: ListPaymentEventsDep) -> dict[str, Any]:
    del actor
    return ok_list([PaymentEventOut.of(item) for item in await use_case.execute()])


@router.post(
    "/admin/studios/{studio_id}/plan",
    response_model=ResponseEnvelope[OrderOut],
    status_code=status.HTTP_201_CREATED,
    tags=["Quản trị hệ thống"],
    summary="Cấp gói cho một xưởng (sau khi tư vấn qua Zalo)",
)
async def admin_grant_plan(
    studio_id: UUID, payload: GrantIn, actor: Operator, use_case: GrantPlanDep
) -> dict[str, Any]:
    grant = PlanGrant(plan=payload.plan, amount=payload.amount, note=payload.note)
    return ok(OrderOut.of(await use_case.execute(actor, studio_id, grant), admin=True))


@router.get(
    "/admin/studio-plans",
    response_model=ResponseEnvelope[list[StudioPlanOut]],
    tags=["Quản trị hệ thống"],
    summary="Gói hiện tại của nhiều xưởng",
)
async def admin_studio_plans(
    actor: Operator,
    use_case: StudioPlansDep,
    ids: Annotated[str, Query(max_length=4000, description="Id xưởng, cách nhau dấu phẩy.")] = "",
) -> dict[str, Any]:
    del actor
    studio_ids: list[UUID] = []
    for raw in ids.split(","):
        try:
            if raw.strip():
                studio_ids.append(UUID(raw.strip()))
        except ValueError:
            raise ValidationError("Id xưởng không hợp lệ.", code="bad_studio_id") from None
    plans = await use_case.execute(studio_ids[:200])
    return ok_list(
        [
            StudioPlanOut(
                studio_id=studio_id,
                plan=LabelOut(slug=plan.value, label=PLAN_SPECS[plan].label),
            )
            for studio_id, plan in plans.items()
        ]
    )


__all__ = ["router"]
