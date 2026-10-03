import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

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
        assert "Dad" in names

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
        new_b_res = await client.post(
            "/api/badges",
            headers={"X-Parent-PIN": "0000"},
            json={
                "badge_key": "TEST_READING_AUTO",
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
                f"/api/badges/TEST_READING_AUTO/toggle/{bot_id}",
                headers={"X-Parent-PIN": "0000"},
                json={"unlock": True},
            )
            assert toggle_res.status_code == 200
            assert toggle_res.json()["unlocked"] is True

            toggle_off_res = await client.post(
                f"/api/badges/TEST_READING_AUTO/toggle/{bot_id}",
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
        # 1. 取得現有成員 (Dad, Ian, Lily)
        members_res = await client.get("/api/members")
        assert members_res.status_code == 200
        members = members_res.json()
        dad = next(m for m in members if m["name"] == "Dad")
        ian = next(m for m in members if m["name"] == "Ian")
        lily = next(m for m in members if m["name"] == "Lily")

        # 2. 以 Ian 身分解鎖 (小孩帳號)
        # 錯誤 PIN 碼應被拒絕 (403)
        bad_unlock = await client.post(
            "/api/system/verify-pin",
            json={"member_id": ian["id"], "pin": "9999"}
        )
        assert bad_unlock.status_code == 403

        # 正確 PIN 碼解鎖成功，簽發 child session
        ian_unlock = await client.post(
            "/api/system/verify-pin",
            json={"member_id": ian["id"], "pin": "0000"}
        )
        assert ian_unlock.status_code == 200
        ian_sess = ian_unlock.json()
        assert ian_sess["role"] == "child"
        assert str(ian_sess["member_id"]) == str(ian["id"])
        assert ian_sess["member_name"] == "Ian"
        ian_token = ian_sess["session_token"]
        assert ian_token and ian_token.startswith("fks_")

        # 3. Ian 專屬功能驗證：
        # A. 申請增加 Ian 自己的點數 (+5) -> 允許
        ian_kudos_ok = await client.post(
            "/api/kudos/record",
            headers={"X-Session-Token": ian_token},
            json={
                "member_id": ian["id"],
                "target_name": "自主做家事",
                "condition_value": "折棉被",
                "points_awarded": 5,
                "recorded_by": "Ian",
            }
        )
        assert ian_kudos_ok.status_code == 200

        # B. 嘗試幫手足 Lily 登記點數 -> 嚴格阻擋 (403 Forbidden)
        cross_kudos_fail = await client.post(
            "/api/kudos/record",
            headers={"X-Session-Token": ian_token},
            json={
                "member_id": lily["id"],
                "target_name": "寫作業",
                "condition_value": "完成",
                "points_awarded": 10,
                "recorded_by": "Ian",
            }
        )
        assert cross_kudos_fail.status_code == 403

        # C. 嘗試自行扣點 (-10) -> 嚴格阻擋 (403 Forbidden: 小孩僅能申請增加自身點數，不可自訂扣點)
        deduct_fail = await client.post(
            "/api/kudos/record",
            headers={"X-Session-Token": ian_token},
            json={
                "member_id": ian["id"],
                "target_name": "吵鬧罰點",
                "condition_value": "扣點",
                "points_awarded": -10,
                "recorded_by": "Ian",
            }
        )
        assert deduct_fail.status_code == 403

        # D. 取得一個上架中的商品
        items_res = await client.get("/api/items")
        assert items_res.status_code == 200
        items = items_res.json()
        assert len(items) > 0
        test_item = items[0]

        # E. Ian 申請兌換自己點數的心願獎品 -> 允許
        ian_redeem_ok = await client.post(
            "/api/redemptions",
            headers={"X-Session-Token": ian_token},
            json={
                "member_id": ian["id"],
                "item_id": test_item["id"],
                "note": "自主心願兌換",
            }
        )
        assert ian_redeem_ok.status_code == 200
        redemption_id = ian_redeem_ok.json()["id"]

        # F. Ian 嘗試幫 Lily 兌換獎品 -> 嚴格阻擋 (403 Forbidden)
        cross_redeem_fail = await client.post(
            "/api/redemptions",
            headers={"X-Session-Token": ian_token},
            json={
                "member_id": lily["id"],
                "item_id": test_item["id"],
                "note": "幫妹妹兌換",
            }
        )
        assert cross_redeem_fail.status_code == 403

        # G. Ian 嘗試自行審核核銷兌換申請 -> 嚴格阻擋 (403 Forbidden)
        ian_review_fail = await client.post(
            f"/api/redemptions/{redemption_id}/review",
            headers={"X-Session-Token": ian_token},
            json={"action": "COMPLETE", "review_note": "小孩自審"}
        )
        assert ian_review_fail.status_code == 403

        # H. Ian 嘗試管理規則或系統設定 -> 嚴格阻擋 (403 Forbidden)
        rule_fail = await client.post(
            "/api/rules",
            headers={"X-Session-Token": ian_token},
            json={
                "target_name": "偷改規則",
                "match_type": "EXACT",
                "condition_value": "100",
                "reward_points": 9999,
            }
        )
        assert rule_fail.status_code == 403

        # 4. 以 Dad 身分解鎖 (家長帳號)
        dad_unlock = await client.post(
            "/api/system/verify-pin",
            json={"member_id": dad["id"], "pin": "0000"}
        )
        assert dad_unlock.status_code == 200
        dad_sess = dad_unlock.json()
        assert dad_sess["role"] == "parent"
        dad_token = dad_sess["session_token"]

        # 家長審核 Ian 的兌換申請 -> 成功
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
                "member_id": lily["id"],
                "target_name": "主動收拾玩具",
                "condition_value": "整齊",
                "points_awarded": 15,
                "recorded_by": "Dad",
            }
        )
        assert dad_kudos_ok.status_code == 200

        # 清理剛才由測試所增加的紀錄以維持資料完整
        from app.core.database import engine
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text(f"DELETE FROM kudos_records WHERE id = '{ian_kudos_ok.json()['id']}';"))
            await conn.execute(text(f"DELETE FROM kudos_records WHERE id = '{dad_kudos_ok.json()['id']}';"))
            await conn.execute(text(f"DELETE FROM redemptions WHERE id = '{redemption_id}';"))
            # 復原 Ian 與 Lily 點數
            await conn.execute(text(f"UPDATE members SET current_points = 720, total_earned_points = 720 WHERE id = '{ian['id']}';"))
            await conn.execute(text(f"UPDATE members SET current_points = 950, total_earned_points = 950 WHERE id = '{lily['id']}';"))



