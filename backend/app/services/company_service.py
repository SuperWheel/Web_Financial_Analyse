"""企业（Company）业务逻辑。

范式参照：所有领域 service 都应这样组织——
接收 Session 与 DTO，执行业务规则，返回 ORM 对象或抛出 ServiceError。
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.exceptions import ConflictError, NotFoundError


def list_companies(db: Session) -> list[Company]:
    """返回全部企业，按 id 升序。"""
    stmt = select(Company).order_by(Company.id.asc())
    return list(db.scalars(stmt).all())


def get_company(db: Session, company_id: int) -> Company:
    """按 id 获取企业，不存在抛 NotFoundError。"""
    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError(f"企业 id={company_id} 不存在")
    return company


def create_company(db: Session, payload: CompanyCreate) -> Company:
    """创建企业。code 冲突抛 ConflictError。"""
    company = Company(name=payload.name, code=payload.code, industry=payload.industry)
    db.add(company)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(f"企业代码 code={payload.code!r} 已存在") from exc
    db.refresh(company)
    return company


def update_company(db: Session, company_id: int, payload: CompanyUpdate) -> Company:
    """部分更新企业。"""
    company = get_company(db, company_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(company, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("企业代码冲突") from exc
    db.refresh(company)
    return company


def delete_company(db: Session, company_id: int) -> None:
    """删除企业（关联报表随级联删除）。"""
    company = get_company(db, company_id)
    db.delete(company)
    db.commit()
