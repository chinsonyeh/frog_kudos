-- ==============================================================================
-- Frog Kudos - PostgreSQL Database Schema & Seed Data (schema.sql)
-- ==============================================================================

-- 1. 啟用 UUID 與密碼雜湊擴充功能
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. 成員表
CREATE TABLE IF NOT EXISTS members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    role VARCHAR(20) NOT NULL DEFAULT 'child',
    avatar VARCHAR(100) DEFAULT '🐸',
    current_points INTEGER NOT NULL DEFAULT 0 CHECK (current_points >= 0),
    total_earned_points INTEGER NOT NULL DEFAULT 0 CHECK (total_earned_points >= 0),
    pin_code VARCHAR(60),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. 分類表
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    icon VARCHAR(50) DEFAULT '📚',
    sort_order INTEGER NOT NULL DEFAULT 0
);

-- 4. 獎勵規則表 (支援特定成員或全家通用)
CREATE TABLE IF NOT EXISTS reward_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID REFERENCES members(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    target_name VARCHAR(100) NOT NULL,
    match_type VARCHAR(20) NOT NULL DEFAULT 'NUM_GTE', -- 'NUM_GTE', 'NUM_EQ', 'EXACT'
    condition_value VARCHAR(50) NOT NULL,
    reward_points INTEGER NOT NULL CHECK (reward_points >= 0),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. 點數獲得快照紀錄表 (核心快照，不可溯及修改，支援家長批次統一調整)
CREATE TABLE IF NOT EXISTS kudos_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
    rule_id UUID REFERENCES reward_rules(id) ON DELETE SET NULL,
    target_name_snapshot VARCHAR(100) NOT NULL,
    condition_snapshot VARCHAR(100) NOT NULL DEFAULT '自訂',
    points_awarded INTEGER NOT NULL,
    rule_detail_snapshot JSONB,
    note TEXT,
    adjustment_note TEXT,
    recorded_by VARCHAR(50) NOT NULL DEFAULT 'Parent',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. 兌換商城品項表
CREATE TABLE IF NOT EXISTS reward_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(100) NOT NULL,
    description TEXT,
    cost_points INTEGER NOT NULL CHECK (cost_points > 0),
    icon VARCHAR(50) DEFAULT '🎁',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. 兌換紀錄表
CREATE TABLE IF NOT EXISTS redemptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
    item_id UUID REFERENCES reward_items(id) ON DELETE SET NULL,
    item_title_snapshot VARCHAR(100) NOT NULL,
    points_spent INTEGER NOT NULL CHECK (points_spent > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'COMPLETED', 'REJECTED'
    review_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ
);

-- 8. 成員成就勳章解鎖紀錄表 (FR-18)
CREATE TABLE IF NOT EXISTS member_badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    badge_key VARCHAR(50) NOT NULL,
    unlocked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (member_id, badge_key)
);

-- 9. 效能索引
CREATE INDEX IF NOT EXISTS idx_rules_member_active ON reward_rules(member_id, is_active);
CREATE INDEX IF NOT EXISTS idx_kudos_records_member_created ON kudos_records(member_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_kudos_batch_filter ON kudos_records(member_id, target_name_snapshot, created_at);
CREATE INDEX IF NOT EXISTS idx_redemptions_member_created ON redemptions(member_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_member_badges_member ON member_badges(member_id);

-- 10. 系統預設種子分類資料 (Categories Initial Seed Data)
INSERT INTO categories (name, icon, sort_order) VALUES
    ('學業成績', '📚', 1),
    ('生活常規', '🌱', 2),
    ('家事協助', '🧹', 3),
    ('運動健康', '🏃', 4)
ON CONFLICT (name) DO NOTHING;

-- 11. 系統冷啟動預設種子成員 (Bootstrap Seed Members)
-- Dad 預設 PIN 為 0000 (透過 pgcrypto crypt 函數產生標準 bcrypt 雜湊，與後端 bcrypt 驗證相容)
INSERT INTO members (name, role, avatar, pin_code) VALUES
    ('Dad', 'parent', '👨', crypt('0000', gen_salt('bf', 12))),
    ('Ian', 'child', '🐸', NULL)
ON CONFLICT (name) DO NOTHING;
