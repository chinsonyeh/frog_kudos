import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.member import Member
from app.models.reward_rule import RewardRule
from app.schemas.kudos import PreviewOut

async def match_rule(
    db: AsyncSession,
    member_id: uuid.UUID,
    target_name: str,
    condition_value: Optional[str] = None,
) -> PreviewOut:
    """
    智慧規則比對推導引擎演算法 (Rule Engine Matching Flow)
    1. 驗證成員有效狀態 (is_active == True)
    2. 成員專屬規則優先比對，無符合時回退至全家通用規則 (member_id IS NULL)
    3. 門檻型別安全轉換 (NUM_GTE, NUM_EQ, EXACT)，防呆異常降級
    4. 多筆符合時，以 reward_points 最高者勝出
    """
    clean_target = (target_name or "").strip()
    if not clean_target:
        return PreviewOut(matched=False, suggested_points=0)

    # 1. 驗證成員是否存在且為啟用狀態
    member = await db.get(Member, member_id)
    if not member or not member.is_active:
        return PreviewOut(matched=False, suggested_points=0)

    # 2. 查詢專屬規則
    member_rules_stmt = select(RewardRule).where(
        and_(
            RewardRule.member_id == member_id,
            RewardRule.is_active == True,
            RewardRule.target_name.ilike(clean_target),
        )
    )
    res = await db.execute(member_rules_stmt)
    candidate_rules = list(res.scalars().all())

    # 若無專屬規則，查詢全家通用規則
    if not candidate_rules:
        global_rules_stmt = select(RewardRule).where(
            and_(
                RewardRule.member_id.is_(None),
                RewardRule.is_active == True,
                RewardRule.target_name.ilike(clean_target),
            )
        )
        res_global = await db.execute(global_rules_stmt)
        candidate_rules = list(res_global.scalars().all())

    if not candidate_rules:
        return PreviewOut(matched=False, suggested_points=0)

    # 3. 條件門檻過濾
    matched_rules: List[RewardRule] = []
    clean_val = (condition_value or "").strip()

    for rule in candidate_rules:
        is_matched = False
        m_type = (rule.match_type or "NUM_GTE").upper()

        if m_type == "NUM_GTE":
            try:
                input_num = float(clean_val)
                rule_num = float(rule.condition_value)
                if input_num >= rule_num:
                    is_matched = True
            except (ValueError, TypeError):
                is_matched = False

        elif m_type == "NUM_EQ":
            try:
                input_num = float(clean_val)
                rule_num = float(rule.condition_value)
                if input_num == rule_num:
                    is_matched = True
            except (ValueError, TypeError):
                is_matched = False

        elif m_type == "EXACT":
            if clean_val.lower() == rule.condition_value.strip().lower():
                is_matched = True

        if is_matched:
            matched_rules.append(rule)

    if not matched_rules:
        return PreviewOut(matched=False, suggested_points=0)

    # 4. 取 reward_points 最高者勝出
    matched_rules.sort(key=lambda r: r.reward_points, reverse=True)
    best_rule = matched_rules[0]

    return PreviewOut(
        matched=True,
        suggested_points=best_rule.reward_points,
        rule_id=best_rule.id,
        rule_name=f"{best_rule.target_name} ({best_rule.condition_value}) - {best_rule.description or ''}".strip(" -"),
    )
