import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.core.database import get_db
from app.core.security import verify_parent_pin, require_parent_pin_dep
from app.models.reward_rule import RewardRule
from app.schemas.rule import RuleCreate, RuleUpdate, RuleOut

router = APIRouter(prefix="/rules", tags=["Rules"])

@router.get("", response_model=List[RuleOut])
async def list_rules(
    member_id: Optional[uuid.UUID] = Query(None, description="過濾特定成員規則 (包含全家通用規則)"),
    only_active: bool = Query(True, description="是否僅列出有效規則"),
    db: AsyncSession = Depends(get_db),
):
    """取得規則清單（可過濾專屬或通用規則）"""
    stmt = select(RewardRule)
    if only_active:
        stmt = stmt.where(RewardRule.is_active == True)
    if member_id:
        stmt = stmt.where(
            or_(
                RewardRule.member_id == member_id,
                RewardRule.member_id.is_(None),
            )
        )
    stmt = stmt.order_by(RewardRule.target_name.asc(), RewardRule.reward_points.desc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("", response_model=RuleOut)
async def create_rule(
    rule_in: RuleCreate,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """新增獎勵規則（需家長安全鎖）"""
    pin = rule_in.parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    rule = RewardRule(
        member_id=rule_in.member_id,
        category_id=rule_in.category_id,
        target_name=rule_in.target_name.strip(),
        match_type=rule_in.match_type,
        condition_value=rule_in.condition_value.strip(),
        reward_points=rule_in.reward_points,
        description=rule_in.description,
        is_active=True,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule

@router.put("/{rule_id}", response_model=RuleOut)
async def update_rule(
    rule_id: uuid.UUID,
    rule_in: RuleUpdate,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """修改獎勵規則（不溯及既往，需家長安全鎖）"""
    pin = rule_in.parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    rule = await db.get(RewardRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="規則不存在")

    if rule_in.member_id is not None:
        rule.member_id = rule_in.member_id
    if rule_in.category_id is not None:
        rule.category_id = rule_in.category_id
    if rule_in.target_name is not None:
        rule.target_name = rule_in.target_name.strip()
    if rule_in.match_type is not None:
        rule.match_type = rule_in.match_type
    if rule_in.condition_value is not None:
        rule.condition_value = rule_in.condition_value.strip()
    if rule_in.reward_points is not None:
        rule.reward_points = rule_in.reward_points
    if rule_in.description is not None:
        rule.description = rule_in.description
    if rule_in.is_active is not None:
        rule.is_active = rule_in.is_active

    await db.commit()
    await db.refresh(rule)
    return rule

@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: uuid.UUID,
    parent_pin: Optional[str] = None,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """停用或刪除規則（需家長安全鎖）"""
    pin = parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    rule = await db.get(RewardRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="規則不存在")

    await db.delete(rule)
    await db.commit()
    return {"success": True, "message": "規則已刪除"}
