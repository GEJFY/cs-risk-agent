"""デモデータをPostgreSQLに投入するシードスクリプト.

Usage:
    python -m cs_risk_agent.scripts.seed_db
"""

from __future__ import annotations

import logging
import sys
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from cs_risk_agent.config import get_settings
from cs_risk_agent.data.models import Base, Company, RiskScore, Subsidiary, User
from cs_risk_agent.demo_loader import DemoData

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def seed_database() -> None:
    """デモデータをDBに投入."""
    settings = get_settings()
    engine = create_engine(settings.database.sync_url)

    # テーブル存在確認
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'companies'")
        )
        if result.scalar() == 0:
            logger.error("テーブルが存在しません。先に 'alembic upgrade head' を実行してください。")
            sys.exit(1)

    demo = DemoData.get()
    if not demo.companies:
        logger.error("デモデータが見つかりません。先に 'python scripts/generate_demo_data.py' を実行してください。")
        sys.exit(1)

    with Session(engine) as session:
        # 既存データチェック
        existing = session.execute(text("SELECT COUNT(*) FROM companies")).scalar()
        if existing and existing > 0:
            logger.info("企業データが既に存在します (%d件)。スキップします。", existing)
            return

        # 親会社
        for comp in demo.companies:
            company = Company(
                id=comp["id"],
                edinet_code=comp.get("edinet_code"),
                securities_code=comp.get("securities_code"),
                name=comp["name"],
                name_en=comp.get("name_en"),
                industry_code=comp.get("industry_code"),
                industry_name=comp.get("industry_name"),
                fiscal_year_end=comp.get("fiscal_year_end"),
                is_listed=comp.get("is_listed", True),
                country=comp.get("country", "JPN"),
            )
            session.add(company)
        session.flush()
        logger.info("親会社: %d件投入", len(demo.companies))

        # 子会社
        for sub in demo.subsidiaries:
            subsidiary = Subsidiary(
                id=sub["id"],
                parent_company_id=sub["parent_company_id"],
                name=sub["name"],
                name_en=sub.get("name_en"),
                country=sub.get("country", "JPN"),
                ownership_ratio=sub.get("ownership_ratio"),
                consolidation_method=sub.get("consolidation_method"),
                segment=sub.get("segment"),
                is_active=sub.get("is_active", True),
            )
            session.add(subsidiary)
        session.flush()
        logger.info("子会社: %d件投入", len(demo.subsidiaries))

        # リスクスコア
        for rs in demo.risk_scores:
            risk_score = RiskScore(
                id=str(uuid4()),
                company_id=rs["entity_id"],
                fiscal_year=rs.get("fiscal_year", 2025),
                fiscal_quarter=rs.get("fiscal_quarter", 4),
                total_score=rs["total_score"],
                risk_level=rs["risk_level"],
                da_score=rs.get("da_score"),
                fraud_score=rs.get("fraud_score"),
                rule_score=rs.get("rule_score"),
                benford_score=rs.get("benford_score"),
                risk_factors=rs.get("risk_factors", []),
                component_details=rs.get("component_details", {}),
            )
            session.add(risk_score)
        session.flush()
        logger.info("リスクスコア: %d件投入", len(demo.risk_scores))

        # デモユーザー
        from passlib.hash import bcrypt

        demo_users = [
            ("admin", "admin@example.com", "admin123", "admin", "管理者"),
            ("auditor", "auditor@example.com", "audit123", "auditor", "監査担当者"),
            ("viewer", "viewer@example.com", "view123", "viewer", "閲覧ユーザー"),
        ]
        for username, email, password, role, full_name in demo_users:
            user = User(
                id=str(uuid4()),
                username=username,
                email=email,
                hashed_password=bcrypt.hash(password),
                role=role,
                full_name=full_name,
            )
            session.add(user)
        logger.info("デモユーザー: %d件投入", len(demo_users))

        session.commit()
        logger.info("シード完了!")


if __name__ == "__main__":
    seed_database()
