"""企业（Company）路由 —— CRUD 切片。

只做请求/响应转换与依赖注入，业务逻辑在 services/company_service.py。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.services import company_service
from app.services.exceptions import ConflictError, NotFoundError, ServiceError

router = APIRouter(prefix="/companies", tags=["企业"])


@router.get("", response_model=list[CompanyRead])
def list_companies(db: Session = Depends(get_session)) -> list[CompanyRead]:
    """获取企业列表。"""
    companies = company_service.list_companies(db)
    return [CompanyRead.model_validate(c) for c in companies]


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreate, db: Session = Depends(get_session)
) -> CompanyRead:
    """创建企业。code 冲突返回 409。"""
    try:
        company = company_service.create_company(db, payload)
    except ConflictError as exc:
        raise _to_http(exc)
    return CompanyRead.model_validate(company)


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(company_id: int, db: Session = Depends(get_session)) -> CompanyRead:
    """获取单个企业。不存在返回 404。"""
    try:
        company = company_service.get_company(db, company_id)
    except NotFoundError as exc:
        raise _to_http(exc)
    return CompanyRead.model_validate(company)


@router.patch("/{company_id}", response_model=CompanyRead)
def update_company(
    company_id: int, payload: CompanyUpdate, db: Session = Depends(get_session)
) -> CompanyRead:
    """部分更新企业。"""
    try:
        company = company_service.update_company(db, company_id, payload)
    except (NotFoundError, ConflictError) as exc:
        raise _to_http(exc)
    return CompanyRead.model_validate(company)


@router.delete("/{company_id}", response_class=Response, status_code=status.HTTP_204_NO_CONTENT)
def delete_company(company_id: int, db: Session = Depends(get_session)) -> Response:
    """删除企业。返回 204 无响应体。"""
    try:
        company_service.delete_company(db, company_id)
    except NotFoundError as exc:
        raise _to_http(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _to_http(exc: ServiceError):
    """把业务异常转换为 HTTPException，避免在 service 里引入 fastapi。"""
    from fastapi import HTTPException

    return HTTPException(status_code=exc.status_code, detail=exc.detail)
