import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.models.member import Member
from app.models.member_badge import MemberBadge
from app.models.kudos_record import KudosRecord
from app.models.reward_rule import RewardRule
from app.models.category import Category
from app.schemas.badge import MemberBadgeOut

BADGE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "FIRST_100_PTS": {
        "title": "初出茅廬蛙",
        "description": "累計獲得 100 點",
        "icon": "🌟",
        "target": 100,
    },
    "PERFECT_SCORE_5": {
        "title": "百分學霸蛙",
        "description": "科目滿分達 5 次",
        "icon": "🏆",
        "target": 5,
    },
    "CHORE_MASTER_200": {
        "title": "家事小達人",
        "description": "生活常規或家事協助累計獲得 200 點",
        "icon": "🧹",
        "target": 200,
    },
    "MILLIONAIRE_1000": {
        "title": "點數大富翁",
        "description": "累計獲得 1000 點",
        "icon": "👑",
        "target": 1000,
    },
}

async def calculate_badge_progress(db: AsyncSession, member: Member) -> Dict[str, Dict[str, Any]]:
    """計算指定成員當前所有勳章的進度數值與解鎖判定"""
    # 1. 滿分次數統計
    perfect_stmt = select(func.count(KudosRecord.id)).where(
        KudosRecord.member_id == member.id,
        or_(
            KudosRecord.condition_snapshot == "100",
            KudosRecord.condition_snapshot == "100分",
            KudosRecord.condition_snapshot == "滿分",
        ),
    )
    perfect_count = (await db.execute(perfect_stmt)).scalar() or 0

    # 2. 家事/生活常規點數累計
    chore_stmt = (
        select(func.coalesce(func.sum(KudosRecord.points_awarded), 0))
        .outerjoin(RewardRule, KudosRecord.rule_id == RewardRule.id)
        .outerjoin(Category, RewardRule.category_id == Category.id)
        .where(
            KudosRecord.member_id == member.id,
            KudosRecord.points_awarded > 0,
            or_(
                Category.name.in_(["生活常規", "家事協助"]),
                KudosRecord.target_name_snapshot.like("%家事%"),
                KudosRecord.target_name_snapshot.like("%常規%"),
                KudosRecord.target_name_snapshot.like("%房間%"),
                KudosRecord.target_name_snapshot.like("%洗碗%"),
            ),
        )
    )
    chore_points = (await db.execute(chore_stmt)).scalar() or 0

    return {
        "FIRST_100_PTS": {
            "progress": member.total_earned_points,
            "target": 100,
            "is_met": member.total_earned_points >= 100,
        },
        "PERFECT_SCORE_5": {
            "progress": perfect_count,
            "target": 5,
            "is_met": perfect_count >= 5,
        },
        "CHORE_MASTER_200": {
            "progress": chore_points,
            "target": 200,
            "is_met": chore_points >= 200,
        },
        "MILLIONAIRE_1000": {
            "progress": member.total_earned_points,
            "target": 1000,
            "is_met": member.total_earned_points >= 1000,
        },
    }

async def get_member_badges(db: AsyncSession, member_id: uuid.UUID) -> List[MemberBadgeOut]:
    """取得成員所有勳章清單（含進度與解鎖狀態）"""
    member = await db.get(Member, member_id)
    if not member:
        return []

    # 查詢已儲存之解鎖紀錄
    stmt = select(MemberBadge).where(MemberBadge.member_id == member_id)
    result = await db.execute(stmt)
    unlocked_map = {b.badge_key: b.unlocked_at for b in result.scalars().all()}

    # 計算當前進度
    progress_info = await calculate_badge_progress(db, member)

    badges_out = []
    for key, defs in BADGE_DEFINITIONS.items():
        prog = progress_info.get(key, {"progress": 0, "target": defs["target"], "is_met": False})
        is_unlocked = key in unlocked_map
        badges_out.append(
            MemberBadgeOut(
                badge_key=key,
                title=defs["title"],
                description=defs["description"],
                icon=defs["icon"],
                unlocked=is_unlocked,
                unlocked_at=unlocked_map.get(key),
                progress=min(prog["progress"], defs["target"]) if is_unlocked else prog["progress"],
                target=defs["target"],
            )
        )

    return badges_out

async def evaluate_and_unlock_badges(db: AsyncSession, member_id: uuid.UUID) -> List[MemberBadgeOut]:
    """
    評估成員是否有達成新勳章條件。若有達成且尚未解鎖，寫入 member_badges 表並回傳新解鎖之勳章清單。
    需在交易內部呼叫。
    """
    member = await db.get(Member, member_id)
    if not member:
        return []

    # 查詢已解鎖紀錄
    stmt = select(MemberBadge).where(MemberBadge.member_id == member_id)
    result = await db.execute(stmt)
    existing_keys = {b.badge_key for b in result.scalars().all()}

    # 計算條件判定
    progress_info = await calculate_badge_progress(db, member)

    newly_unlocked = []
    now = datetime.now(timezone.utc)

    for key, info in progress_info.items():
        if info["is_met"] and key not in existing_keys:
            # 寫入資料庫解鎖紀錄
            badge_record = MemberBadge(
                member_id=member_id,
                badge_key=key,
                unlocked_at=now,
            )
            db.add(badge_record)
            defs = BADGE_DEFINITIONS[key]
            newly_unlocked.append(
                MemberBadgeOut(
                    badge_key=key,
                    title=defs["title"],
                    description=defs["description"],
                    icon=defs["icon"],
                    unlocked=True,
                    unlocked_at=now,
                    progress=defs["target"],
                    target=defs["target"],
                )
            )

    return newly_unlocked
