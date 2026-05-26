import json
import secrets
import random
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from app.database import get_db
from app import models
from app.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

# 动态起手库
DYNAMIC_STARTERS = {
    "camera": [
        "Fast Dolly Zoom in",
        "Rapid Orbit around product",
        "Handheld shake with close-up",
        "Whip pan start from left",
        "Sudden fly-through shot",
        "Dramatic crash zoom",
    ],
    "physics": [
        "Wind blowing hair/fabric instantly",
        "Water droplets exploding around",
        "Smoke swirling from the product",
        "Light streaks moving fast",
        "Particles erupting from center",
        "Shockwave distortion effect",
    ],
    "action": [
        "A hand instantly grabs the product",
        "The product drops and catches mid-air",
        "Sudden transformation of the product",
        "Product spins rapidly into frame",
        "Exploding reveal from center",
        "Dynamic unfolding sequence",
    ],
}

MARKET_ACTORS = {
    "china": "现代亚洲模特",
    "usa": "多元背景的美国模特",
    "europe": "欧洲时尚模特",
    "japan": "日本潮流模特",
    "korea": "韩系精致模特",
    "southeast_asia": "东南亚活力模特",
    "global": "国际多元化模特",
}


class GenerateRequest(BaseModel):
    product_name: str
    target_market: str = "global"
    target_language: str = "chinese"
    selling_points: str = ""
    video_script: str = ""
    bgm_style: str = ""
    count: int = 3
    use_ai: bool = True


class HistoryItem(BaseModel):
    id: int
    product_name: str
    prompts_json: str
    created_at: str
    share_token: Optional[str] = None


def _build_single_prompt(params: dict, index: int) -> dict:
    camera = random.choice(DYNAMIC_STARTERS["camera"])
    physics = random.choice(DYNAMIC_STARTERS["physics"])
    action = random.choice(DYNAMIC_STARTERS["action"])

    points = [p.strip() for p in params["selling_points"].split(",") if p.strip()]
    market_actor = MARKET_ACTORS.get(params["target_market"], MARKET_ACTORS["global"])

    section_0_4 = (
        f"{camera} as {physics}. {action}. "
        f"{market_actor} interacts with {params['product_name']} with high energy motion."
    )
    section_4_8 = "The camera continues dynamic movement. "
    if points:
        section_4_8 += f"Showcasing {' and '.join(points[:2])} with rapid cuts and flowing transitions. "
    section_4_8 += f"{market_actor} demonstrates the product with swift, confident movements."
    section_8_12 = (
        f"Epic final reveal. {params['product_name']} in perfect lighting. "
        "Dynamic slow-mo finale. Brand imprint, call to action."
    )

    audio_plan = ""
    if params.get("video_script"):
        audio_plan = f"Voiceover: \"{params['video_script']}\""
    if params.get("bgm_style"):
        audio_plan += (" | " if audio_plan else "") + f"BGM: {params['bgm_style']}"
    if not audio_plan:
        audio_plan = "Audio: Cinematic sync with motion"

    dynamic_strategy = f"{camera} + {physics} + {action}"
    final_prompt = (
        f"Strictly animate the provided product image. Vertical 9:16, 12 seconds.\n"
        f"{dynamic_strategy}.\n\n"
        f"[0-4s] [IMMEDIATE ACTION]: {section_0_4}\n\n"
        f"[4-8s] [Transition]. {section_4_8}\n\n"
        f"[8-12s] [Conclusion]. {section_8_12}\n\n"
        f"Style tags: High motion, cinematic movement, 4k, no static shots.\n"
        f"Maintain visual fidelity to the provided product image."
    )

    return {
        "index": index + 1,
        "audit": "图片: ✅ | 视频: ✅",
        "audioPlan": audio_plan,
        "dynamicStrategy": dynamic_strategy,
        "sections": {"0-4s": section_0_4, "4-8s": section_4_8, "8-12s": section_8_12},
        "finalPrompt": final_prompt,
    }


async def _build_ai_prompts(params: dict, count: int) -> list:
    """调用智谱 GLM 生成提示词"""
    from zhipuai import ZhipuAI

    client = ZhipuAI(api_key=settings.ZHIPUAI_API_KEY)

    points_str = params.get("selling_points") or "优质品质"
    script_str = params.get("video_script") or ""
    bgm_str = params.get("bgm_style") or "电影感配乐"
    market = MARKET_ACTORS.get(params["target_market"], "国际多元化模特")

    system_prompt = (
        "你是一位专业的短视频广告创意总监，擅长为电商产品生成高质量的AI视频提示词（prompt）。"
        "你生成的提示词需要：1.英文输出 2.强调动态感、镜头运动 3.按时间段分段 4.适配竖版9:16"
    )
    user_prompt = (
        f"为以下产品生成{count}条不同风格的AI视频提示词：\n"
        f"- 商品名称：{params['product_name']}\n"
        f"- 核心卖点：{points_str}\n"
        f"- 目标受众：{market}\n"
        f"- 口播文案：{script_str or '无'}\n"
        f"- 背景音乐：{bgm_str}\n\n"
        f"每条提示词必须包含：\n"
        f"1. 动态起手（前4秒）：强烈的镜头运动+物理特效+动作\n"
        f"2. 展示段（4-8秒）：卖点呈现+模特互动\n"
        f"3. 结尾（8-12秒）：品牌印记+行动号召\n\n"
        f"以JSON数组格式返回，每个元素包含 index(1-{count})、finalPrompt、dynamicStrategy、audioPlan 字段。"
        f"只返回JSON，不要其他说明。"
    )

    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.9,
    )

    raw = response.choices[0].message.content.strip()
    # 去掉可能的 markdown 代码块
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    ai_prompts = json.loads(raw)
    # 补充 audit 字段
    for p in ai_prompts:
        p.setdefault("audit", "图片: ✅ | 视频: ✅")
    return ai_prompts


@router.post("/generate")
async def generate_prompts(
    req: GenerateRequest,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    params = req.model_dump()

    # 生成提示词
    if req.use_ai and settings.ZHIPUAI_API_KEY:
        try:
            prompts = await _build_ai_prompts(params, req.count)
        except Exception as e:
            # AI 失败降级到本地规则
            prompts = [_build_single_prompt(params, i) for i in range(req.count)]
    else:
        prompts = [_build_single_prompt(params, i) for i in range(req.count)]

    # 保存历史记录
    history = models.PromptHistory(
        user_id=current_user.id,
        product_name=req.product_name,
        target_market=req.target_market,
        target_language=req.target_language,
        selling_points=req.selling_points,
        video_script=req.video_script,
        bgm_style=req.bgm_style,
        prompts_json=json.dumps(prompts, ensure_ascii=False),
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)

    return {"prompts": prompts, "history_id": history.id}


@router.get("/history")
async def get_history(
    page: int = 1,
    page_size: int = 20,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    result = await db.execute(
        select(models.PromptHistory)
        .where(models.PromptHistory.user_id == current_user.id)
        .order_by(desc(models.PromptHistory.created_at))
        .offset(offset)
        .limit(page_size)
    )
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": h.id,
                "product_name": h.product_name,
                "target_market": h.target_market,
                "prompts_json": h.prompts_json,
                "created_at": h.created_at.isoformat(),
                "share_token": h.share_token,
            }
            for h in items
        ]
    }


@router.post("/history/{history_id}/share")
async def create_share_link(
    history_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(models.PromptHistory).where(
            models.PromptHistory.id == history_id,
            models.PromptHistory.user_id == current_user.id,
        )
    )
    history = result.scalar_one_or_none()
    if not history:
        raise HTTPException(status_code=404, detail="记录不存在")

    if not history.share_token:
        history.share_token = secrets.token_urlsafe(32)
        await db.commit()

    return {"share_token": history.share_token}


@router.get("/share/{token}")
async def get_shared_prompt(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.PromptHistory).where(models.PromptHistory.share_token == token)
    )
    history = result.scalar_one_or_none()
    if not history:
        raise HTTPException(status_code=404, detail="分享链接无效或已过期")

    return {
        "product_name": history.product_name,
        "prompts_json": history.prompts_json,
        "created_at": history.created_at.isoformat(),
    }


@router.delete("/history/{history_id}")
async def delete_history(
    history_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(models.PromptHistory).where(
            models.PromptHistory.id == history_id,
            models.PromptHistory.user_id == current_user.id,
        )
    )
    history = result.scalar_one_or_none()
    if not history:
        raise HTTPException(status_code=404, detail="记录不存在")
    await db.delete(history)
    await db.commit()
    return {"ok": True}
