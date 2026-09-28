import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

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
        # 1. 取得預設種子成員清單
        res = await client.get("/api/members")
        assert res.status_code == 200
        members = res.json()
        names = [m["name"] for m in members]
        assert "Dad" in names
        assert "Ian" in names

        # 2. 測試家長安全鎖：錯誤 PIN 應被阻擋 (403)
        bad_res = await client.post(
            "/api/members",
            json={"name": "TestChild", "role": "child", "avatar": "👶", "parent_pin": "9999"},
        )
        assert bad_res.status_code == 403

        # 3. 正確 PIN (0000) 新增成員
        add_res = await client.post(
            "/api/members",
            json={"name": "Amy", "role": "child", "avatar": "👧", "parent_pin": "0000"},
        )
        assert add_res.status_code == 200
        amy = add_res.json()
        amy_id = amy["id"]
        assert amy["name"] == "Amy"
        assert amy["current_points"] == 0

        # 4. 新成員無紀錄時執行實體刪除
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

        # 2. 取得 Ian 的 ID
        m_res = await client.get("/api/members")
        ian = next(m for m in m_res.json() if m["name"] == "Ian")
        ian_id = ian["id"]

        # 3. 新增 Ian 專屬規則：社會科 >= 100 分 -> 50 點
        rule_res = await client.post(
            "/api/rules",
            headers={"X-Parent-PIN": "0000"},
            json={
                "member_id": ian_id,
                "category_id": academic_cat["id"],
                "target_name": "社會科",
                "match_type": "NUM_GTE",
                "condition_value": "100",
                "reward_points": 50,
                "description": "段考滿分獎勵",
            },
        )
        assert rule_res.status_code == 200
        rule = rule_res.json()
        assert rule["reward_points"] == 50

        # 4. 新增全家通用規則：整理房間 == 完成 -> 10 點
        global_rule_res = await client.post(
            "/api/rules",
            headers={"X-Parent-PIN": "0000"},
            json={
                "member_id": None,
                "category_id": None,
                "target_name": "整理房間",
                "match_type": "EXACT",
                "condition_value": "完成",
                "reward_points": 10,
                "description": "維持房間整潔",
            },
        )
        assert global_rule_res.status_code == 200

        # 5. 測試智慧推導預覽 (Rule Engine)
        # Case A: 數值達標命中專屬規則
        prev_a = await client.post(
            "/api/kudos/preview",
            json={"member_id": ian_id, "target_name": "社會科", "condition_value": "100"},
        )
        assert prev_a.status_code == 200
        assert prev_a.json()["matched"] is True
        assert prev_a.json()["suggested_points"] == 50

        # Case B: 輸入文字安全防呆降級 (非純數字文字不拋 500)
        prev_b = await client.post(
            "/api/kudos/preview",
            json={"member_id": ian_id, "target_name": "社會科", "condition_value": "優等"},
        )
        assert prev_b.status_code == 200
        assert prev_b.json()["matched"] is False
        assert prev_b.json()["suggested_points"] == 0

        # Case C: 命中全家通用規則
        prev_c = await client.post(
            "/api/kudos/preview",
            json={"member_id": ian_id, "target_name": "整理房間", "condition_value": "完成"},
        )
        assert prev_c.status_code == 200
        assert prev_c.json()["matched"] is True
        assert prev_c.json()["suggested_points"] == 10

@pytest.mark.asyncio
async def test_kudos_points_and_badges_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 取得 Ian
        m_res = await client.get("/api/members")
        ian = next(m for m in m_res.json() if m["name"] == "Ian")
        ian_id = ian["id"]
        init_curr = ian["current_points"]
        init_total = ian["total_earned_points"]

        # 2. 發放點數 50 點 (第 1 次段考滿分)
        rec1_res = await client.post(
            "/api/kudos/record",
            headers={"X-Parent-PIN": "0000"},
            json={
                "member_id": ian_id,
                "target_name": "社會科",
                "condition_value": "100",
                "points_awarded": 50,
                "note": "第一次段考滿分",
            },
        )
        assert rec1_res.status_code == 200

        # 3. 發放點數 50 點 (累計達到 100 點門檻)
        rec2_res = await client.post(
            "/api/kudos/record",
            headers={"X-Parent-PIN": "0000"},
            json={
                "member_id": ian_id,
                "target_name": "社會科",
                "condition_value": "100",
                "points_awarded": 50,
                "note": "第二次段考滿分",
            },
        )
        assert rec2_res.status_code == 200
        rec2_data = rec2_res.json()

        # 檢查是否自動解鎖 FIRST_100_PTS 勳章 (FR-18)
        badges_res = await client.get(f"/api/members/{ian_id}/badges")
        assert badges_res.status_code == 200
        badges = badges_res.json()
        first_100_badge = next(b for b in badges if b["badge_key"] == "FIRST_100_PTS")
        assert first_100_badge["unlocked"] is True

        # 4. 違規扣點 Penalty (FR-14)
        pen_res = await client.post(
            "/api/kudos/record",
            headers={"X-Parent-PIN": "0000"},
            json={
                "member_id": ian_id,
                "target_name": "違規未完成功課",
                "condition_value": "自訂",
                "points_awarded": -10,
                "note": "未寫完作業偷看電視扣點",
            },
        )
        assert pen_res.status_code == 200

        # 檢查雙軌帳本約束：current_points 減少 10 點，但 total_earned_points 絕不扣除
        m_res2 = await client.get("/api/members")
        ian_after = next(m for m in m_res2.json() if m["name"] == "Ian")
        assert ian_after["current_points"] == init_curr + 50 + 50 - 10
        assert ian_after["total_earned_points"] == init_total + 50 + 50

        # 5. 防呆安全：超額扣點至負數應被拒絕 (HTTP 400)
        over_pen = await client.post(
            "/api/kudos/record",
            headers={"X-Parent-PIN": "0000"},
            json={
                "member_id": ian_id,
                "target_name": "惡意扣點測試",
                "points_awarded": -99999,
            },
        )
        assert over_pen.status_code == 400

@pytest.mark.asyncio
async def test_redemption_and_refund_lifecycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 取得 Ian
        m_res = await client.get("/api/members")
        ian = next(m for m in m_res.json() if m["name"] == "Ian")
        ian_id = ian["id"]
        start_points = ian["current_points"]

        # 2. 新增商城獎品
        item_res = await client.post(
            "/api/items",
            headers={"X-Parent-PIN": "0000"},
            json={
                "title": "玩 Switch 1小時",
                "cost_points": 30,
                "icon": "🎮",
                "description": "週末放鬆",
            },
        )
        assert item_res.status_code == 200
        item_id = item_res.json()["id"]

        # 3. 發起兌換申請 (扣除可用點數，狀態為 PENDING)
        red_res = await client.post(
            "/api/redemptions",
            json={"member_id": ian_id, "item_id": item_id, "note": "本週末想玩遊戲"},
        )
        assert red_res.status_code == 200
        redemption = red_res.json()
        assert redemption["status"] == "PENDING"
        red_id = redemption["id"]

        m_res2 = await client.get("/api/members")
        ian_mid = next(m for m in m_res2.json() if m["name"] == "Ian")
        assert ian_mid["current_points"] == start_points - 30

        # 4. 家長退回申請並全額退款 (REJECT -> Refund) (FR-15)
        rev_res = await client.post(
            f"/api/redemptions/{red_id}/review",
            headers={"X-Parent-PIN": "0000"},
            json={"action": "REJECT", "review_note": "作業尚未完成，暫不開放兌換"},
        )
        assert rev_res.status_code == 200
        assert rev_res.json()["status"] == "REJECTED"

        # 檢查點數是否已全額退還
        m_res3 = await client.get("/api/members")
        ian_refunded = next(m for m in m_res3.json() if m["name"] == "Ian")
        assert ian_refunded["current_points"] == start_points

        # 5. 再次兌換並核銷 (COMPLETE)
        red_res2 = await client.post(
            "/api/redemptions",
            json={"member_id": ian_id, "item_id": item_id},
        )
        red_id2 = red_res2.json()["id"]

        approve_res = await client.post(
            f"/api/redemptions/{red_id2}/review",
            headers={"X-Parent-PIN": "0000"},
            json={"action": "COMPLETE", "review_note": "已兌現玩遊戲"},
        )
        assert approve_res.status_code == 200
        assert approve_res.json()["status"] == "COMPLETED"

@pytest.mark.asyncio
async def test_ledger_and_export():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 取得 Ian
        m_res = await client.get("/api/members")
        ian = next(m for m in m_res.json() if m["name"] == "Ian")
        ian_id = ian["id"]

        # 2. 查詢綜合存摺流水帳
        hist_res = await client.get(f"/api/kudos/history?member_id={ian_id}&limit=20")
        assert hist_res.status_code == 200
        history = hist_res.json()
        assert len(history) > 0

        # 3. 匯出 CSV
        export_res = await client.get(f"/api/kudos/export?member_id={ian_id}")
        assert export_res.status_code == 200
        assert export_res.headers["content-type"].startswith("text/csv")
        csv_text = export_res.text
        assert "時間,成員姓名,紀錄類型,項目名稱,點數異動" in csv_text
        assert "社會科" in csv_text

@pytest.mark.asyncio
async def test_batch_adjustment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 取得 Ian
        m_res = await client.get("/api/members")
        ian = next(m for m in m_res.json() if m["name"] == "Ian")
        ian_id = ian["id"]

        # 2. 批次調整預覽
        prev_res = await client.post(
            "/api/kudos/batch-preview",
            json={
                "member_id": ian_id,
                "target_name": "社會科",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "mode": "OFFSET",
                "value": 5,
            },
        )
        assert prev_res.status_code == 200
        prev_data = prev_res.json()
        assert prev_data["affected_count"] >= 2
        assert prev_data["delta"] == prev_data["affected_count"] * 5

        # 3. 執行批次調整
        adj_res = await client.post(
            "/api/kudos/batch-adjust",
            headers={"X-Parent-PIN": "0000"},
            json={
                "member_id": ian_id,
                "target_name": "社會科",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "mode": "OFFSET",
                "value": 5,
                "reason": "學期末加碼調增 5 點",
            },
        )
        assert adj_res.status_code == 200
        adj_data = adj_res.json()
        assert adj_data["affected_count"] == prev_data["affected_count"]

@pytest.mark.asyncio
async def test_system_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 取得系統設定 (密碼強制脫敏)
        cfg_res = await client.get("/api/system/config")
        assert cfg_res.status_code == 200
        cfg = cfg_res.json()
        assert "db_name" in cfg
        assert "db_password" not in cfg  # NFR-4 機敏密碼零洩漏
        assert "password" not in cfg

        # 2. 版本檢查
        ver_res = await client.get("/api/system/version")
        assert ver_res.status_code == 200
        ver_data = ver_res.json()
        assert "current_version" in ver_data

        # 3. 升級狀態
        status_res = await client.get("/api/system/upgrade-status")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["status"] in ("IDLE", "RUNNING", "COMPLETED", "FAILED")
