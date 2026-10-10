import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest_asyncio.fixture(autouse=True)
async def setup_test_parent():
    from app.core.database import engine
    from app.core.security import hash_pin
    from sqlalchemy import text
    test_parent_id = str(uuid.uuid4())
    hashed = hash_pin("0000")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                f"INSERT INTO members (id, name, role, avatar, pin_code, is_active) "
                f"VALUES ('{test_parent_id}', '__TestParentRunner__', 'parent', '👨', '{hashed}', TRUE) "
                f"ON CONFLICT (name) DO UPDATE SET pin_code = '{hashed}';"
            )
        )
    try:
        yield
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM members WHERE name = '__TestParentRunner__';"))




async def create_isolated_test_child(client: AsyncClient, name_prefix="TestBot"):
    name = f"{name_prefix}_{uuid.uuid4().hex[:8]}"
    res = await client.post(
        "/api/members",
        headers={"X-Parent-PIN": "0000"},
        json={"name": name, "role": "child", "avatar": "🤖", "parent_pin": "0000"},
    )
    assert res.status_code == 200
    return res.json()

async def cleanup_test_child(client: AsyncClient, member_id: str):
    # 先清理關聯資料（若有）並刪除成員
    from app.core.database import engine
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.execute(text(f"DELETE FROM kudos_records WHERE member_id = '{member_id}';"))
        await conn.execute(text(f"DELETE FROM redemptions WHERE member_id = '{member_id}';"))
        await conn.execute(text(f"DELETE FROM member_badges WHERE member_id = '{member_id}';"))
        await conn.execute(text(f"DELETE FROM reward_rules WHERE member_id = '{member_id}';"))
        await conn.execute(text(f"DELETE FROM members WHERE id = '{member_id}';"))

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["app"] == "Frog Kudos"

@pytest.mark.asyncio
async def test_members_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 取得成員清單
        res = await client.get("/api/members")
        assert res.status_code == 200
        members = res.json()
        names = [m["name"] for m in members]
        assert any(m["role"] == "parent" for m in members)

        # 2. 測試家長安全鎖：錯誤 PIN 應被阻擋 (403)
        bad_res = await client.post(
            "/api/members",
            json={"name": "TestChild", "role": "child", "avatar": "👶", "parent_pin": "9999"},
        )
        assert bad_res.status_code == 403

        # 3. 正確 PIN (0000) 新增成員
        add_res = await client.post(
            "/api/members",
            json={"name": "AmyTest", "role": "child", "avatar": "👧", "parent_pin": "0000"},
        )
        assert add_res.status_code == 200
        amy = add_res.json()
        amy_id = amy["id"]
        assert amy["name"] == "AmyTest"
        assert amy["current_points"] == 0

        # 4. 測試未解鎖狀態更換頭像 (無須 PIN 碼) (PUT 與 PATCH)
        # 4-1: PUT 僅變更 avatar
        put_av_res = await client.put(
            f"/api/members/{amy_id}",
            json={"avatar": "🦄"},
        )
        assert put_av_res.status_code == 200
        assert put_av_res.json()["avatar"] == "🦄"

        # 4-2: PATCH 變更 avatar
        patch_av_res = await client.patch(
            f"/api/members/{amy_id}/avatar",
            json={"avatar": "🦁"},
        )
        assert patch_av_res.status_code == 200
        assert patch_av_res.json()["avatar"] == "🦁"

        # 4-3: 未帶 PIN 嘗試修改姓名或管理屬性應被阻擋 (403 Forbidden)
        bad_name_res = await client.put(
            f"/api/members/{amy_id}",
            json={"name": "HackedName"},
        )
        assert bad_name_res.status_code == 403

        # 4-4: 帶正確 PIN 碼修改姓名成功
        ok_name_res = await client.put(
            f"/api/members/{amy_id}",
            headers={"X-Parent-PIN": "0000"},
            json={"name": "AmyUpdated"},
        )
        assert ok_name_res.status_code == 200
        assert ok_name_res.json()["name"] == "AmyUpdated"

        # 5. 新成員無紀錄時執行實體刪除
        del_res = await client.delete(
            f"/api/members/{amy_id}?parent_pin=0000"
        )
        assert del_res.status_code == 200
        assert del_res.json()["action"] == "DELETED"

@pytest.mark.asyncio
async def test_categories_and_rules():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 檢查種子分類
        res = await client.get("/api/categories")
        assert res.status_code == 200
        cats = res.json()
        cat_names = [c["name"] for c in cats]
        assert "學業成績" in cat_names
        academic_cat = next(c for c in cats if c["name"] == "學業成績")

        # 2. 建立獨立測試成員（絕不污染真實成員）
        test_bot = await create_isolated_test_child(client, "BotRule")
        bot_id = test_bot["id"]

        try:
            # 3. 新增測試專屬規則：測試科目 >= 100 分 -> 50 點
            rule_res = await client.post(
                "/api/rules",
                headers={"X-Parent-PIN": "0000"},
                json={
                    "member_id": bot_id,
                    "category_id": academic_cat["id"],
                    "target_name": "測試科目",
                    "match_type": "NUM_GTE",
                    "condition_value": "100",
                    "reward_points": 50,
                    "description": "測試獎勵",
                },
            )
            assert rule_res.status_code == 200
            rule = rule_res.json()
            rule_id = rule["id"]
            assert rule["reward_points"] == 50

            # 4. 測試智慧推導預覽 (Rule Engine)
            # Case A: 數值達標命中專屬規則
            prev_a = await client.post(
                "/api/kudos/preview",
                json={"member_id": bot_id, "target_name": "測試科目", "condition_value": "100"},
            )
            assert prev_a.status_code == 200
            assert prev_a.json()["matched"] is True
            assert prev_a.json()["suggested_points"] == 50

            # Case B: 輸入文字安全防呆降級
            prev_b = await client.post(
                "/api/kudos/preview",
                json={"member_id": bot_id, "target_name": "測試科目", "condition_value": "優等"},
            )
            assert prev_b.status_code == 200
            assert prev_b.json()["matched"] is False
            assert prev_b.json()["suggested_points"] == 0
        finally:
            await cleanup_test_child(client, bot_id)

@pytest.mark.asyncio
async def test_kudos_points_and_badges_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 建立獨立測試成員
        test_bot = await create_isolated_test_child(client, "BotKudos")
        bot_id = test_bot["id"]

        try:
            # 1. 發放點數 50 點
            rec1_res = await client.post(
                "/api/kudos/record",
                headers={"X-Parent-PIN": "0000"},
                json={
                    "member_id": bot_id,
                    "target_name": "自訂測試項目",
                    "condition_value": "100",
                    "points_awarded": 50,
                    "note": "測試滿分",
                },
            )
            assert rec1_res.status_code == 200

            # 2. 發放點數 50 點 (累計達到 100 點門檻)
            rec2_res = await client.post(
                "/api/kudos/record",
                headers={"X-Parent-PIN": "0000"},
                json={
                    "member_id": bot_id,
                    "target_name": "自訂測試項目",
                    "condition_value": "100",
                    "points_awarded": 50,
                    "note": "測試第二次滿分",
                },
            )
            assert rec2_res.status_code == 200

            # 檢查是否自動解鎖 FIRST_100_PTS 勳章 (FR-18)
            badges_res = await client.get(f"/api/members/{bot_id}/badges")
            assert badges_res.status_code == 200
            badges = badges_res.json()
            first_100_badge = next(b for b in badges if b["badge_key"] == "FIRST_100_PTS")
            assert first_100_badge["unlocked"] is True

            # 3. 違規扣點 Penalty (FR-14)
            pen_res = await client.post(
                "/api/kudos/record",
                headers={"X-Parent-PIN": "0000"},
                json={
                    "member_id": bot_id,
                    "target_name": "違規未完成功課",
                    "condition_value": "自訂",
                    "points_awarded": -10,
                    "note": "違規扣點測試",
                },
            )
            assert pen_res.status_code == 200

            # 檢查雙軌帳本約束
            m_res = await client.get("/api/members")
            bot_after = next(m for m in m_res.json() if m["id"] == bot_id)
            assert bot_after["current_points"] == 50 + 50 - 10
            assert bot_after["total_earned_points"] == 50 + 50

            # 4. 防呆安全：超額扣點至負數應被拒絕 (HTTP 400)
            over_pen = await client.post(
                "/api/kudos/record",
                headers={"X-Parent-PIN": "0000"},
                json={
                    "member_id": bot_id,
                    "target_name": "惡意扣點測試",
                    "points_awarded": -99999,
                },
            )
            assert over_pen.status_code == 400
        finally:
            await cleanup_test_child(client, bot_id)

@pytest.mark.asyncio
async def test_redemption_and_refund_lifecycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 建立獨立測試成員並先給予 100 點
        test_bot = await create_isolated_test_child(client, "BotRedeem")
        bot_id = test_bot["id"]

        item_id = None
        try:
            await client.post(
                "/api/kudos/record",
                headers={"X-Parent-PIN": "0000"},
                json={
                    "member_id": bot_id,
                    "target_name": "初始贈點",
                    "condition_value": "自訂",
                    "points_awarded": 100,
                },
            )

            # 新增測試商城獎品
            item_res = await client.post(
                "/api/items",
                headers={"X-Parent-PIN": "0000"},
                json={
                    "title": "測試遊戲時間",
                    "cost_points": 30,
                    "icon": "🎮",
                    "description": "測試獎品",
                },
            )
            assert item_res.status_code == 200
            item_id = item_res.json()["id"]

            # 發起兌換申請 (扣除可用點數，狀態為 PENDING)
            red_res = await client.post(
                "/api/redemptions",
                json={"member_id": bot_id, "item_id": item_id, "note": "兌換測試", "pin": "0000"},
            )
            assert red_res.status_code == 200
            redemption = red_res.json()
            assert redemption["status"] == "PENDING"
            red_id = redemption["id"]

            m_res2 = await client.get("/api/members")
            bot_mid = next(m for m in m_res2.json() if m["id"] == bot_id)
            assert bot_mid["current_points"] == 100 - 30

            # 家長退回申請並全額退款 (REJECT -> Refund) (FR-15)
            rev_res = await client.post(
                f"/api/redemptions/{red_id}/review",
                headers={"X-Parent-PIN": "0000"},
                json={"action": "REJECT", "review_note": "測試退點"},
            )
            assert rev_res.status_code == 200
            assert rev_res.json()["status"] == "REJECTED"

            # 檢查點數是否已全額退還
            m_res3 = await client.get("/api/members")
            bot_refunded = next(m for m in m_res3.json() if m["id"] == bot_id)
            assert bot_refunded["current_points"] == 100

            # 再次兌換並核銷 (COMPLETE)
            red_res2 = await client.post(
                "/api/redemptions",
                json={"member_id": bot_id, "item_id": item_id, "pin": "0000"},
            )
            red_id2 = red_res2.json()["id"]

            approve_res = await client.post(
                f"/api/redemptions/{red_id2}/review",
                headers={"X-Parent-PIN": "0000"},
                json={"action": "COMPLETE", "review_note": "已核銷"},
            )
            assert approve_res.status_code == 200
            assert approve_res.json()["status"] == "COMPLETED"
        finally:
            await cleanup_test_child(client, bot_id)
            if item_id:
                await client.delete(f"/api/items/{item_id}?permanent=true", headers={"X-Parent-PIN": "0000"})

@pytest.mark.asyncio
async def test_ledger_and_export():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        test_bot = await create_isolated_test_child(client, "BotLedger")
        bot_id = test_bot["id"]

        try:
            # 建立一筆點數紀錄
            await client.post(
                "/api/kudos/record",
                headers={"X-Parent-PIN": "0000"},
                json={
                    "member_id": bot_id,
                    "target_name": "流水帳測試項目",
                    "condition_value": "自訂",
                    "points_awarded": 20,
                },
            )

            # 查詢綜合存摺流水帳
            hist_res = await client.get(f"/api/kudos/history?member_id={bot_id}&limit=20")
            assert hist_res.status_code == 200
            history = hist_res.json()
            assert len(history) > 0

            # 匯出 CSV
            export_res = await client.get(f"/api/kudos/export?member_id={bot_id}")
            assert export_res.status_code == 200
            assert export_res.headers["content-type"].startswith("text/csv")
            csv_text = export_res.text
            assert "時間,成員姓名,紀錄類型,項目名稱,點數異動" in csv_text
            assert "流水帳測試項目" in csv_text
        finally:
            await cleanup_test_child(client, bot_id)

@pytest.mark.asyncio
async def test_batch_adjustment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        test_bot = await create_isolated_test_child(client, "BotBatch")
        bot_id = test_bot["id"]

        try:
            # 建立 2 筆紀錄
            for i in range(2):
                await client.post(
                    "/api/kudos/record",
                    headers={"X-Parent-PIN": "0000"},
                    json={
                        "member_id": bot_id,
                        "target_name": "批次測試項目",
                        "condition_value": "100",
                        "points_awarded": 50,
                    },
                )

            # 批次調整預覽
            prev_res = await client.post(
                "/api/kudos/batch-preview",
                json={
                    "member_id": bot_id,
                    "target_name": "批次測試項目",
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                    "mode": "OFFSET",
                    "value": 5,
                },
            )
            assert prev_res.status_code == 200
            prev_data = prev_res.json()
            assert prev_data["affected_count"] == 2
            assert prev_data["delta"] == 10

            # 執行批次調整
            adj_res = await client.post(
                "/api/kudos/batch-adjust",
                headers={"X-Parent-PIN": "0000"},
                json={
                    "member_id": bot_id,
                    "target_name": "批次測試項目",
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                    "mode": "OFFSET",
                    "value": 5,
                    "reason": "批次調整測試",
                },
            )
            assert adj_res.status_code == 200
            adj_data = adj_res.json()
            assert adj_data["affected_count"] == 2
        finally:
            await cleanup_test_child(client, bot_id)

@pytest.mark.asyncio
async def test_system_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        cfg_res = await client.get("/api/system/config")
        assert cfg_res.status_code == 200
        cfg = cfg_res.json()
        assert "db_name" in cfg
        assert "db_password" not in cfg

        ver_res = await client.get("/api/system/version")
        assert ver_res.status_code == 200

        status_res = await client.get("/api/system/upgrade-status")
        assert status_res.status_code == 200

        # 4. 即時驗證 PIN 碼 (FR-13)
        # 正確 PIN (JSON payload)
        ok_pin_res = await client.post(
            "/api/system/verify-pin",
            json={"parent_pin": "0000"},
        )
        assert ok_pin_res.status_code == 200
        assert ok_pin_res.json()["valid"] is True

        # 正確 PIN (Header)
        ok_header_res = await client.post(
            "/api/system/verify-pin",
            headers={"X-Parent-PIN": "0000"},
        )
        assert ok_header_res.status_code == 200
        assert ok_header_res.json()["valid"] is True

        # 錯誤 PIN 應立即回傳 403 Forbidden
        bad_pin_res = await client.post(
            "/api/system/verify-pin",
            json={"parent_pin": "9999"},
        )
        assert bad_pin_res.status_code == 403

        # 空白 PIN 應立即回傳 403 Forbidden
        empty_pin_res = await client.post(
            "/api/system/verify-pin",
            json={"parent_pin": ""},
        )
        assert empty_pin_res.status_code == 403

@pytest.mark.asyncio
async def test_badge_management_and_milestones():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 查詢所有勳章定義清單
        b_res = await client.get("/api/badges")
        assert b_res.status_code == 200
        badges = b_res.json()
        assert len(badges) >= 15

        # 驗證包含 5000 點至 100000 點之所有里程碑
        keys = [b["badge_key"] for b in badges]
        for milestone_key in [
            "FIRST_100_PTS", "MILLIONAIRE_1000", "POINTS_5000", "POINTS_10000",
            "POINTS_20000", "POINTS_30000", "POINTS_40000", "POINTS_50000",
            "POINTS_60000", "POINTS_70000", "POINTS_80000", "POINTS_90000", "POINTS_100000"
        ]:
            assert milestone_key in keys

        # 2. 家長新增自訂成就勳章
        custom_key = f"TEST_READING_{uuid.uuid4().hex[:6]}"
        new_b_res = await client.post(
            "/api/badges",
            headers={"X-Parent-PIN": "0000"},
            json={
                "badge_key": custom_key,
                "title": "晨讀書香蛙",
                "description": "連續晨讀 10 次",
                "icon": "📖",
                "condition_type": "CUSTOM",
                "target_value": 10,
                "sort_order": 99,
            },
        )
        assert new_b_res.status_code == 200
        badge_id = new_b_res.json()["id"]

        test_bot = await create_isolated_test_child(client, "BotBadge")
        bot_id = test_bot["id"]

        try:
            # 3. 手動為測試成員頒發勳章與收回
            toggle_res = await client.post(
                f"/api/badges/{custom_key}/toggle/{bot_id}",
                headers={"X-Parent-PIN": "0000"},
                json={"unlock": True},
            )
            assert toggle_res.status_code == 200
            assert toggle_res.json()["unlocked"] is True

            toggle_off_res = await client.post(
                f"/api/badges/{custom_key}/toggle/{bot_id}",
                headers={"X-Parent-PIN": "0000"},
                json={"unlock": False},
            )
            assert toggle_off_res.status_code == 200
            assert toggle_off_res.json()["unlocked"] is False
        finally:
            await client.delete(f"/api/badges/{badge_id}", headers={"X-Parent-PIN": "0000"})
            await cleanup_test_child(client, bot_id)

@pytest.mark.asyncio
async def test_child_pin_and_self_points_restrictions():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 建立兩個獨立測試小孩：ChildA (PIN 1111) 與 ChildB (PIN 2222)
        res_a = await client.post(
            "/api/members",
            headers={"X-Parent-PIN": "0000"},
            json={"name": f"ChildA_{uuid.uuid4().hex[:6]}", "role": "child", "avatar": "👦", "pin_code": "1111"},
        )
        assert res_a.status_code == 200
        child_a = res_a.json()
        a_id = child_a["id"]

        res_b = await client.post(
            "/api/members",
            headers={"X-Parent-PIN": "0000"},
            json={"name": f"ChildB_{uuid.uuid4().hex[:6]}", "role": "child", "avatar": "👧", "pin_code": "2222"},
        )
        assert res_b.status_code == 200
        child_b = res_b.json()
        b_id = child_b["id"]

        item_id = None
        try:
            # 2. 驗證成員 PIN 碼 API (/api/system/verify-member-pin)
            v_ok = await client.post(
                "/api/system/verify-member-pin",
                json={"member_id": a_id, "pin": "1111"},
            )
            assert v_ok.status_code == 200
            assert v_ok.json()["valid"] is True
            assert v_ok.json()["role"] == "child"

            v_bad = await client.post(
                "/api/system/verify-member-pin",
                json={"member_id": a_id, "pin": "9999"},
            )
            assert v_bad.status_code == 403

            # 3. 小孩為自己申請增加點數 (points_awarded > 0) -> 成功，recorded_by 為小孩姓名
            add_self = await client.post(
                "/api/kudos/record",
                json={
                    "member_id": a_id,
                    "target_name": "自主晨讀",
                    "condition_value": "完成",
                    "points_awarded": 30,
                    "pin": "1111",
                },
            )
            assert add_self.status_code == 200
            assert add_self.json()["recorded_by"] == child_a["name"]

            # 4. 小孩不可為自己登記違規扣點 (points_awarded <= 0) -> 403 Forbidden
            neg_self = await client.post(
                "/api/kudos/record",
                json={
                    "member_id": a_id,
                    "target_name": "自扣點數",
                    "points_awarded": -10,
                    "pin": "1111",
                },
            )
            assert neg_self.status_code == 403

            # 5. 小孩不可使用自己 PIN 為其他手足登記點數 -> 403 Forbidden
            hack_sibling = await client.post(
                "/api/kudos/record",
                json={
                    "member_id": b_id,
                    "target_name": "挪用登記",
                    "points_awarded": 30,
                    "pin": "1111",
                },
            )
            assert hack_sibling.status_code == 403

            # 6. 新增測試獎品
            item_res = await client.post(
                "/api/items",
                headers={"X-Parent-PIN": "0000"},
                json={"title": "小孩自選獎勵", "cost_points": 20, "icon": "🎁"},
            )
            assert item_res.status_code == 200
            item_id = item_res.json()["id"]

            # 7. 小孩使用自己 PIN 申請兌換自己的點數 -> 成功
            redeem_ok = await client.post(
                "/api/redemptions",
                json={"member_id": a_id, "item_id": item_id, "pin": "1111"},
            )
            assert redeem_ok.status_code == 200
            assert redeem_ok.json()["status"] == "PENDING"

            # 8. 小孩不可使用自己 PIN 兌換手足點數 -> 403 Forbidden
            redeem_bad = await client.post(
                "/api/redemptions",
                json={"member_id": b_id, "item_id": item_id, "pin": "1111"},
            )
            assert redeem_bad.status_code == 403

            # 9. 小孩修改自己的 PIN 碼 (/api/members/{member_id}/change-pin)
            change_bad = await client.post(
                f"/api/members/{a_id}/change-pin",
                json={"old_pin": "wrong", "new_pin": "3333"},
            )
            assert change_bad.status_code == 403

            change_ok = await client.post(
                f"/api/members/{a_id}/change-pin",
                json={"old_pin": "1111", "new_pin": "3333"},
            )
            assert change_ok.status_code == 200

            # 驗證新 PIN 碼生效
            v_new = await client.post(
                "/api/system/verify-member-pin",
                json={"member_id": a_id, "pin": "3333"},
            )
            assert v_new.status_code == 200

            # 舊 PIN 碼失效
            v_old = await client.post(
                "/api/system/verify-member-pin",
                json={"member_id": a_id, "pin": "1111"},
            )
            assert v_old.status_code == 403
        finally:
            await cleanup_test_child(client, a_id)
            await cleanup_test_child(client, b_id)
            if item_id:
                await client.delete(f"/api/items/{item_id}?permanent=true", headers={"X-Parent-PIN": "0000"})

@pytest.mark.asyncio
async def test_independent_browser_session_lifecycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 模擬瀏覽器 A 輸入正確 PIN 碼解鎖
        res_a = await client.post("/api/system/verify-pin", json={"parent_pin": "0000"})
        assert res_a.status_code == 200
        data_a = res_a.json()
        assert data_a["valid"] is True
        token_a = data_a["session_token"]
        assert token_a and token_a.startswith("fks_")
        assert data_a["expires_in"] == 15 * 60

        # 2. 模擬瀏覽器 B 未解鎖 (無 Token / 無 PIN) -> 嘗試執行家長操作 (如取得系統設定變更) 應被阻擋 (403)
        unauth_res = await client.put("/api/system/config", json={"auto_backup": True})
        assert unauth_res.status_code == 403

        # 3. 瀏覽器 A 使用專屬 Session Token 存取家長端點 -> 成功授權
        auth_res = await client.put(
            "/api/system/config",
            headers={"X-Parent-Session": token_a},
            json={"auto_backup": True},
        )
        assert auth_res.status_code == 200

        # 4. 模擬瀏覽器 B 也輸入 PIN 解鎖 -> 獲得獨立之 Session Token B
        res_b = await client.post("/api/system/verify-pin", json={"parent_pin": "0000"})
        assert res_b.status_code == 200
        token_b = res_b.json()["session_token"]
        assert token_b != token_a

        # 5. 瀏覽器 A 執行鎖定 -> 銷毀 Token A
        lock_a = await client.post("/api/system/lock-session", json={"session_token": token_a})
        assert lock_a.status_code == 200

        # 6. Token A 已失效，再用 Token A 操作應被拒絕 (403)
        fail_a = await client.put(
            "/api/system/config",
            headers={"X-Parent-Session": token_a},
            json={"auto_backup": True},
        )
        assert fail_a.status_code == 403

        # 7. 瀏覽器 B 的 Token B 依然獨立有效！不受瀏覽器 A 鎖定之影響
        ok_b = await client.put(
            "/api/system/config",
            headers={"X-Parent-Session": token_b},
            json={"auto_backup": True},
        )
        assert ok_b.status_code == 200

        # 8. 瀏覽器 B 鎖定 -> 銷毀 Token B
        await client.post("/api/system/lock-session", json={"session_token": token_b})
        fail_b = await client.put(
            "/api/system/config",
            headers={"X-Parent-Session": token_b},
            json={"auto_backup": True},
        )
        assert fail_b.status_code == 403

@pytest.mark.asyncio
async def test_role_based_unlock_and_permissions():
    """
    驗證角色解鎖與權限劃分安全機制：
    1. 小孩帳號解鎖獲得專屬 child session token
    2. 小孩僅能申請自身點數，不可幫其他手足登記 (403)
    3. 小孩不可自行扣點 (403)
    4. 小孩僅能申請兌換自身點數，不可幫其他手足兌換 (403)
    5. 小孩不可審核核銷兌換申請 (403)
    6. 小孩不可管理規則或系統設定 (403)
    7. 家長帳號解鎖保留完整管理、審核與跨成員操作權限
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 取得現有家長成員
        members_res = await client.get("/api/members")
        assert members_res.status_code == 200
        members = members_res.json()
        parent_member = next((m for m in members if m["name"] == "__TestParentRunner__"), None) or next(m for m in members if m["role"] == "parent")

        # 2. 建立兩個獨立測試小孩（完全隔離，絕不污染正式環境成員）
        child_a = await create_isolated_test_child(client, "RoleChildA")
        child_b = await create_isolated_test_child(client, "RoleChildB")
        a_id = child_a["id"]
        b_id = child_b["id"]
        a_name = child_a["name"]

        test_item_id = None
        try:
            # 3. 以 ChildA 身分解鎖 (小孩帳號)
            # 錯誤 PIN 碼應被拒絕 (403)
            bad_unlock = await client.post(
                "/api/system/verify-pin",
                json={"member_id": a_id, "pin": "9999"}
            )
            assert bad_unlock.status_code == 403

            # 正確 PIN 碼解鎖成功，簽發 child session
            a_unlock = await client.post(
                "/api/system/verify-pin",
                json={"member_id": a_id, "pin": "0000"}
            )
            assert a_unlock.status_code == 200
            a_sess = a_unlock.json()
            assert a_sess["role"] == "child"
            assert str(a_sess["member_id"]) == str(a_id)
            assert a_sess["member_name"] == a_name
            a_token = a_sess["session_token"]
            assert a_token and a_token.startswith("fks_")

            # 4. ChildA 專屬功能驗證：
            # A. 申請增加 ChildA 自己的點數 (+5) -> 允許
            a_kudos_ok = await client.post(
                "/api/kudos/record",
                headers={"X-Session-Token": a_token},
                json={
                    "member_id": a_id,
                    "target_name": "自主做家事",
                    "condition_value": "折棉被",
                    "points_awarded": 5,
                    "recorded_by": a_name,
                }
            )
            assert a_kudos_ok.status_code == 200

            # B. 嘗試幫手足 ChildB 登記點數 -> 嚴格阻擋 (403 Forbidden)
            cross_kudos_fail = await client.post(
                "/api/kudos/record",
                headers={"X-Session-Token": a_token},
                json={
                    "member_id": b_id,
                    "target_name": "寫作業",
                    "condition_value": "完成",
                    "points_awarded": 10,
                    "recorded_by": a_name,
                }
            )
            assert cross_kudos_fail.status_code == 403

            # C. 嘗試自行扣點 (-10) -> 嚴格阻擋 (403 Forbidden: 小孩僅能申請增加自身點數，不可自訂扣點)
            deduct_fail = await client.post(
                "/api/kudos/record",
                headers={"X-Session-Token": a_token},
                json={
                    "member_id": a_id,
                    "target_name": "吵鬧罰點",
                    "condition_value": "扣點",
                    "points_awarded": -10,
                    "recorded_by": a_name,
                }
            )
            assert deduct_fail.status_code == 403

            # D. 新增獨立測試商品
            item_res = await client.post(
                "/api/items",
                headers={"X-Parent-PIN": "0000"},
                json={"title": "角色測試獎品", "cost_points": 5, "icon": "🎁"},
            )
            assert item_res.status_code == 200
            test_item_id = item_res.json()["id"]

            # E. ChildA 申請兌換自己點數的心願獎品 -> 允許
            a_redeem_ok = await client.post(
                "/api/redemptions",
                headers={"X-Session-Token": a_token},
                json={
                    "member_id": a_id,
                    "item_id": test_item_id,
                    "note": "自主心願兌換",
                }
            )
            assert a_redeem_ok.status_code == 200
            redemption_id = a_redeem_ok.json()["id"]

            # F. ChildA 嘗試幫 ChildB 兌換獎品 -> 嚴格阻擋 (403 Forbidden)
            cross_redeem_fail = await client.post(
                "/api/redemptions",
                headers={"X-Session-Token": a_token},
                json={
                    "member_id": b_id,
                    "item_id": test_item_id,
                    "note": "幫手足兌換",
                }
            )
            assert cross_redeem_fail.status_code == 403

            # G. ChildA 嘗試自行審核核銷兌換申請 -> 嚴格阻擋 (403 Forbidden)
            a_review_fail = await client.post(
                f"/api/redemptions/{redemption_id}/review",
                headers={"X-Session-Token": a_token},
                json={"action": "COMPLETE", "review_note": "小孩自審"}
            )
            assert a_review_fail.status_code == 403

            # H. ChildA 嘗試管理規則或系統設定 -> 嚴格阻擋 (403 Forbidden)
            rule_fail = await client.post(
                "/api/rules",
                headers={"X-Session-Token": a_token},
                json={
                    "target_name": "偷改規則",
                    "match_type": "EXACT",
                    "condition_value": "100",
                    "reward_points": 9999,
                }
            )
            assert rule_fail.status_code == 403

            # 5. 以家長身分解鎖 (家長帳號)
            dad_unlock = await client.post(
                "/api/system/verify-pin",
                json={"member_id": parent_member["id"], "pin": "0000"}
            )
            assert dad_unlock.status_code == 200
            dad_sess = dad_unlock.json()
            assert dad_sess["role"] == "parent"
            dad_token = dad_sess["session_token"]

            # 家長審核 ChildA 的兌換申請 -> 成功
            dad_review_ok = await client.post(
                f"/api/redemptions/{redemption_id}/review",
                headers={"X-Session-Token": dad_token},
                json={"action": "COMPLETE", "review_note": "家長確認兌現"}
            )
            assert dad_review_ok.status_code == 200
            assert dad_review_ok.json()["status"] == "COMPLETED"

            # 家長可以為任意成員發放或調整點數
            dad_kudos_ok = await client.post(
                "/api/kudos/record",
                headers={"X-Session-Token": dad_token},
                json={
                    "member_id": b_id,
                    "target_name": "主動收拾玩具",
                    "condition_value": "整齊",
                    "points_awarded": 15,
                    "recorded_by": parent_member["name"],
                }
            )
            assert dad_kudos_ok.status_code == 200
        finally:
            await cleanup_test_child(client, a_id)
            await cleanup_test_child(client, b_id)
            if test_item_id:
                await client.delete(f"/api/items/{test_item_id}?permanent=true", headers={"X-Parent-PIN": "0000"})

@pytest.mark.asyncio
async def test_custom_pin_security_and_default_pin_invalidation():
    """
    驗證自訂 PIN 啟用後立即停用預設值 0000 之安全防護：
    1. 家長設定自訂 PIN 碼後，預設 PIN 0000 必須立即失效被拒絕 (403 / False)
    2. 小孩設定自訂 PIN 碼後，預設 PIN 0000 必須立即失效被拒絕 (403 / False)
    3. 未自訂 PIN 碼前（冷啟動或 pin_code=None），預設 PIN 0000 允許作為初次使用
    """
    from app.core.database import AsyncSessionLocal, engine
    from app.core.security import validate_parent_pin, verify_member_or_parent_pin, hash_pin
    from app.models.member import Member
    from sqlalchemy import select, text

    # 先清理掉測試夾具暫存的 __TestParentRunner__，以純粹的真實資料庫狀態進行驗證
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM members WHERE name = '__TestParentRunner__';"))

    async with AsyncSessionLocal() as db:
        # A. 家長自訂 PIN 安全驗證：
        # 當前家長為 Dad&Mom (已自訂 PIN，不為 0000)
        p_res = await db.execute(select(Member).where(Member.role == "parent", Member.is_active == True))
        active_parents = p_res.scalars().all()
        assert any(p.pin_code for p in active_parents)
        # 輸入 0000 必須回傳 False（不可使用預設值登入！）
        assert await validate_parent_pin(db, input_pin="0000") is False
        # 輸入 9999 亦為 False
        assert await validate_parent_pin(db, input_pin="9999") is False

        # B. 小孩自訂 PIN 安全驗證 (以 Lily 為例，Lily 已自訂非 0000 之 PIN)
        lily_res = await db.execute(select(Member).where(Member.name == "Lily"))
        lily = lily_res.scalars().first()
        if lily:
            assert lily.pin_code is not None
            # Lily 輸入 0000 必須失敗 (False, "none")，絕不能再被預設 0000 解鎖！
            valid, role = await verify_member_or_parent_pin(db, lily.id, input_pin="0000")
            assert valid is False
            assert role == "none"

        # C. 預設 PIN 碼設定在新增用戶的資料庫中，修改後預設 PIN 碼隨之覆蓋失效
        test_new_child = Member(
            name=f"NewChild_{uuid.uuid4().hex[:6]}",
            role="child",
            avatar="👶",
            pin_code=hash_pin("0000"),  # 系統建立新用戶時，將預設值 0000 寫入資料庫
        )
        db.add(test_new_child)
        await db.commit()
        await db.refresh(test_new_child)
        try:
            # 1. 新用戶資料庫中存有 0000 雜湊，允許 0000 初次登入
            ok_valid, ok_role = await verify_member_or_parent_pin(db, test_new_child.id, input_pin="0000")
            assert ok_valid is True
            assert ok_role == "child"

            # 2. 用戶修改為自訂 PIN "7777" (覆蓋資料庫中的 pin_code 欄位)
            test_new_child.pin_code = hash_pin("7777")
            await db.commit()

            # 3. 自訂後，資料庫不再存有 0000，且程式中無任何預設 PIN 碼，0000 立即徹底失效！
            expired_valid, expired_role = await verify_member_or_parent_pin(db, test_new_child.id, input_pin="0000")
            assert expired_valid is False
            assert expired_role == "none"

            # 4. 自訂 PIN "7777" 成功登入
            new_valid, new_role = await verify_member_or_parent_pin(db, test_new_child.id, input_pin="7777")
            assert new_valid is True
            assert new_role == "child"
        finally:
            await db.delete(test_new_child)
            await db.commit()


@pytest.mark.asyncio
async def test_member_avatar_update_and_upload():
    import io
    from PIL import Image
    from app.main import UPLOADS_DIR

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        child = await create_isolated_test_child(client, "AvatarTester")
        child_id = child["id"]
        uploaded_filepath = None
        try:
            # 1. 測試任意 Emoji 或文字頭像更新
            patch_res = await client.patch(
                f"/api/members/{child_id}/avatar",
                json={"avatar": "🎉"},
            )
            assert patch_res.status_code == 200
            assert patch_res.json()["avatar"] == "🎉"

            # 2. 測試 10 款原創青蛙公仔庫路徑更新
            gallery_res = await client.patch(
                f"/api/members/{child_id}/avatar",
                json={"avatar": "/icons/gallery/icon_4_vector.jpg"},
            )
            assert gallery_res.status_code == 200
            assert gallery_res.json()["avatar"] == "/icons/gallery/icon_4_vector.jpg"

            # 3. 測試本地照片上傳、自動縮放壓製為 WebP
            img_byte_arr = io.BytesIO()
            test_img = Image.new("RGB", (300, 200), color="green")
            test_img.save(img_byte_arr, format="PNG")
            img_bytes = img_byte_arr.getvalue()

            upload_res = await client.post(
                f"/api/members/{child_id}/avatar-upload",
                files={"file": ("avatar.png", img_bytes, "image/png")},
            )
            assert upload_res.status_code == 200
            new_avatar = upload_res.json()["avatar"]
            assert new_avatar.startswith("/uploads/avatars/")
            assert new_avatar.endswith(".webp")

            filename = new_avatar.replace("/uploads/avatars/", "")
            uploaded_filepath = UPLOADS_DIR / "avatars" / filename
            assert uploaded_filepath.exists()

            # 4. 測試頭像庫列表 API (GET /api/members/avatars/gallery)
            gallery_list_res = await client.get("/api/members/avatars/gallery")
            assert gallery_list_res.status_code == 200
            gallery_data = gallery_list_res.json()
            assert "total" in gallery_data
            assert gallery_data["max_allowed"] == 100
            urls = [item["url"] for item in gallery_data["avatars"]]
            assert new_avatar in urls

            # 5. 測試再次上傳不同照片，兩張照片皆被完整保留 (不覆蓋舊檔案)
            img_byte_arr2 = io.BytesIO()
            test_img2 = Image.new("RGB", (200, 200), color="blue")
            test_img2.save(img_byte_arr2, format="PNG")
            upload_res2 = await client.post(
                f"/api/members/{child_id}/avatar-upload",
                files={"file": ("avatar2.png", img_byte_arr2.getvalue(), "image/png")},
            )
            assert upload_res2.status_code == 200
            new_avatar2 = upload_res2.json()["avatar"]
            assert new_avatar2 != new_avatar

            filename2 = new_avatar2.replace("/uploads/avatars/", "")
            uploaded_filepath2 = UPLOADS_DIR / "avatars" / filename2
            assert uploaded_filepath.exists()  # 舊圖依然存在
            assert uploaded_filepath2.exists()  # 新圖亦被保存

            # 6. 測試刪除頭像 (DELETE /api/members/avatars/gallery/{filename})
            # 刪除 new_avatar2，該成員的 avatar 應自動復原為 '🐸'
            del_res = await client.delete(f"/api/members/avatars/gallery/{filename2}")
            assert del_res.status_code == 200
            assert not uploaded_filepath2.exists()

            # 驗證該成員頭像已自動重設為 🐸
            members_res = await client.get("/api/members")
            target_child = next((m for m in members_res.json() if m["id"] == child_id), None)
            assert target_child is not None
            assert target_child["avatar"] == "🐸"

            # 7. 測試相片上傳至相片庫但不立即套用 (POST /api/members/avatars/gallery/upload)
            img_byte_arr3 = io.BytesIO()
            test_img3 = Image.new("RGB", (250, 250), color="orange")
            test_img3.save(img_byte_arr3, format="PNG")
            upload_gallery_res = await client.post(
                "/api/members/avatars/gallery/upload",
                files={"file": ("gallery_avatar.png", img_byte_arr3.getvalue(), "image/png")},
            )
            assert upload_gallery_res.status_code == 200
            gallery_avatar_data = upload_gallery_res.json()
            assert "url" in gallery_avatar_data
            assert "filename" in gallery_avatar_data
            assert gallery_avatar_data["url"].startswith("/uploads/avatars/custom_")
            uploaded_filepath3 = UPLOADS_DIR / "avatars" / gallery_avatar_data["filename"]
            assert uploaded_filepath3.exists()

            # 驗證成員當前頭像「尚未被套用」，依然保持為 🐸
            members_res2 = await client.get("/api/members")
            target_child2 = next((m for m in members_res2.json() if m["id"] == child_id), None)
            assert target_child2["avatar"] == "🐸"

            # 驗證相片已出現在相片庫清單中
            gallery_list_res2 = await client.get("/api/members/avatars/gallery")
            assert gallery_list_res2.status_code == 200
            urls2 = [item["url"] for item in gallery_list_res2.json()["avatars"]]
            assert gallery_avatar_data["url"] in urls2

            # 模擬用戶按下「立即套用」：呼叫 PATCH /api/members/{member_id}/avatar
            apply_res = await client.patch(
                f"/api/members/{child_id}/avatar",
                json={"avatar": gallery_avatar_data["url"]},
            )
            assert apply_res.status_code == 200
            assert apply_res.json()["avatar"] == gallery_avatar_data["url"]

            # 驗證成員頭像已正式變更
            members_res3 = await client.get("/api/members")
            target_child3 = next((m for m in members_res3.json() if m["id"] == child_id), None)
            assert target_child3["avatar"] == gallery_avatar_data["url"]

            # 刪除測試相片
            del_gallery_res = await client.delete(f"/api/members/avatars/gallery/{gallery_avatar_data['filename']}")
            assert del_gallery_res.status_code == 200
            assert not uploaded_filepath3.exists()

        finally:
            if uploaded_filepath and uploaded_filepath.exists():
                uploaded_filepath.unlink(missing_ok=True)
            if 'uploaded_filepath2' in locals() and uploaded_filepath2 and uploaded_filepath2.exists():
                uploaded_filepath2.unlink(missing_ok=True)
            if 'uploaded_filepath3' in locals() and uploaded_filepath3 and uploaded_filepath3.exists():
                uploaded_filepath3.unlink(missing_ok=True)
            await cleanup_test_child(client, child_id)





