"""FastAPI 依存性注入 - DI コンテナ."""

from __future__ import annotations

from typing import Any, AsyncIterator

from fastapi import Depends, Header, HTTPException, status

from cs_risk_agent.config import Settings, get_settings


# ---------------------------------------------------------------------------
# データベースセッション
# ---------------------------------------------------------------------------


async def get_db() -> AsyncIterator[Any]:
    """非同期DBセッションを提供するジェネレータ.

    TODO: SQLAlchemy AsyncSession に置き換える。
    現在はプレースホルダーとして辞書オブジェクトを返す。

    Yields:
        模擬非同期セッションオブジェクト（後で AsyncSession に差し替え）。
    """
    # TODO: 実装時は以下に差し替え
    # async with async_session_factory() as session:
    #     yield session
    session: dict[str, Any] = {"_placeholder": True}
    try:
        yield session
    finally:
        # セッションクリーンアップ処理
        pass


# ---------------------------------------------------------------------------
# 認証・認可
# ---------------------------------------------------------------------------


async def get_current_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """JWTトークンからユーザー情報を抽出する.

    Authorization ヘッダーの Bearer トークンを検証し、
    ユーザー情報を辞書として返す。

    TODO: 実際の JWT デコード・検証ロジックを実装する。

    Args:
        authorization: Authorization ヘッダー値（Bearer <token>）。
        settings: アプリケーション設定。

    Returns:
        ユーザー情報を含む辞書。

    Raises:
        HTTPException: トークンが欠落または無効な場合（401）。
    """
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Bearer プレフィックスの検証
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # TODO: 実際の JWT 検証ロジック
    # decoded = jwt.decode(
    #     token,
    #     settings.jwt.secret_key,
    #     algorithms=[settings.jwt.algorithm],
    # )
    # return decoded

    # プレースホルダー: 固定ユーザーを返す
    return {
        "sub": "placeholder-user-id",
        "email": "dev@example.com",
        "roles": ["analyst"],
        "token": token,
    }


# ---------------------------------------------------------------------------
# AI モデルルーター
# ---------------------------------------------------------------------------


class AIModelRouter:
    """AIモデルルーティングのプレースホルダー.

    TODO: マルチクラウドプロバイダーへのルーティングロジックを実装する。
    """

    def __init__(self, settings: Settings) -> None:
        """AIModelRouter を初期化する.

        Args:
            settings: アプリケーション設定。
        """
        self._settings = settings

    async def route(self, prompt: str, *, tier: str = "cost_effective") -> str:
        """プロンプトを適切なプロバイダーにルーティングする.

        Args:
            prompt: LLM に送信するプロンプト。
            tier: モデルティア（"sota" または "cost_effective"）。

        Returns:
            LLM からのレスポンステキスト。
        """
        # TODO: 実プロバイダーへのルーティング実装
        return f"[PLACEHOLDER] tier={tier}, prompt_len={len(prompt)}"


# シングルトンキャッシュ
_ai_router_instance: AIModelRouter | None = None


def get_ai_router(
    settings: Settings = Depends(get_settings),
) -> AIModelRouter:
    """AIModelRouter のシングルトンインスタンスを返す.

    Args:
        settings: アプリケーション設定。

    Returns:
        AIModelRouter インスタンス。
    """
    global _ai_router_instance  # noqa: PLW0603
    if _ai_router_instance is None:
        _ai_router_instance = AIModelRouter(settings)
    return _ai_router_instance
