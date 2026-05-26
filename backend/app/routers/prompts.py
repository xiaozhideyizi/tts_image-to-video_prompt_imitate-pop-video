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

# 平台档案：画面比例、像素分辨率、推荐时长、适配语言、视频调性描述
PLATFORM_PROFILES = {
    "taobao": {
        "ratio": "3:4", "resolution": "1080x1440", "duration": "15s",
        "lang": "chinese", "label": "淘系（淘宝/天猫）",
        "orientation": "portrait",
        "vibe": "polished product showcase, studio lighting, clean aesthetic, e-commerce conversion focused",
    },
    "pinduoduo": {
        "ratio": "1:1", "resolution": "1080x1080", "duration": "15s",
        "lang": "chinese", "label": "拼多多",
        "orientation": "square",
        "vibe": "eye-catching deal highlight, bold price tags, fast-paced demo, urgency-driven",
    },
    "jd": {
        "ratio": "3:4", "resolution": "1080x1440", "duration": "20s",
        "lang": "chinese", "label": "京东",
        "orientation": "portrait",
        "vibe": "premium brand feel, quality assurance vibe, professional demo, trust-building",
    },
    "douyin_ec": {
        "ratio": "9:16", "resolution": "1080x1920", "duration": "20s",
        "lang": "chinese", "label": "抖音电商",
        "orientation": "vertical",
        "vibe": "viral hook energy, trendy effects, scroll-stopping opening, social commerce style",
    },
    "xiaohongshu": {
        "ratio": "3:4", "resolution": "1080x1440", "duration": "25s",
        "lang": "chinese", "label": "小红书",
        "orientation": "portrait",
        "vibe": "lifestyle aesthetic, soft warm tones, relatable daily-use scenario,种草 style",
    },
    "douyin": {
        "ratio": "9:16", "resolution": "1080x1920", "duration": "20s",
        "lang": "chinese", "label": "抖音",
        "orientation": "vertical",
        "vibe": "viral hook, trending transitions, energetic pacing, meme-ready, scroll-stopping",
    },
    "shipinhao": {
        "ratio": "9:16", "resolution": "1080x1920", "duration": "25s",
        "lang": "chinese", "label": "视频号",
        "orientation": "vertical",
        "vibe": "social sharing vibe, trustworthy feel, informative yet engaging, WeChat ecosystem",
    },
    "bilibili": {
        "ratio": "16:9", "resolution": "1920x1080", "duration": "45s",
        "lang": "chinese", "label": "B站",
        "orientation": "landscape",
        "vibe": "nerd-culture appeal, detailed review style, creative storytelling, longer-form content",
    },
    "tiktok": {
        "ratio": "9:16", "resolution": "1080x1920", "duration": "15s",
        "lang": "english", "label": "TikTok",
        "orientation": "vertical",
        "vibe": "viral hook, trending sound-sync, fast cuts, Gen Z energy, challenge-ready",
    },
    "instagram": {
        "ratio": "9:16", "resolution": "1080x1920", "duration": "15s",
        "lang": "english", "label": "Instagram Reels",
        "orientation": "vertical",
        "vibe": "aesthetic visual, smooth transitions, aspirational lifestyle, polished branding",
    },
    "youtube": {
        "ratio": "9:16", "resolution": "1080x1920", "duration": "30s",
        "lang": "english", "label": "YouTube Shorts",
        "orientation": "vertical",
        "vibe": "informative hook, clear value proposition, YouTube creator style, SEO-friendly opening",
    },
    "facebook": {
        "ratio": "9:16", "resolution": "1080x1920", "duration": "20s",
        "lang": "english", "label": "Facebook Reels",
        "orientation": "vertical",
        "vibe": "broad appeal, community feel, shareable moment, attention-grabbing first frame",
    },
}

# 口播字幕配置
VOICEOVER_SUBTITLE_MAP = {
    "voice_no_sub":    {"voiceover": True,  "subtitle": False, "label": "口播无字幕"},
    "voice_with_sub":  {"voiceover": True,  "subtitle": True,  "label": "口播有字幕"},
    "no_voice_with_sub": {"voiceover": False, "subtitle": True,  "label": "无口播有字幕"},
    "no_voice_no_sub": {"voiceover": False, "subtitle": False, "label": "无口播无字幕"},
}


class GenerateRequest(BaseModel):
    product_name: str
    target_market: str = "china"
    target_language: str = "chinese"
    platform: str = "douyin"
    voiceover_subtitle: str = "voice_with_sub"
    selling_points: str = ""
    video_script: str = ""
    bgm_style: str = ""
    audio_option: str = "voiceover"
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
    market_actor = MARKET_ACTORS.get(params["target_market"], MARKET_ACTORS["china"])

    # 平台档案
    platform = params.get("platform", "douyin")
    profile = PLATFORM_PROFILES.get(platform, PLATFORM_PROFILES["douyin"])

    # 口播字幕配置
    vs_key = params.get("voiceover_subtitle", "voice_with_sub")
    vs_config = VOICEOVER_SUBTITLE_MAP.get(vs_key, VOICEOVER_SUBTITLE_MAP["voice_with_sub"])

    # 从平台档案读取精确参数
    ratio = profile["ratio"]
    resolution = profile["resolution"]
    duration = profile["duration"]
    orientation = profile["orientation"]
    vibe = profile["vibe"]

    # 根据时长计算分段（动态分配）
    dur_sec = int(duration.replace("s", ""))
    if dur_sec <= 15:
        # 短视频：3段均分
        s1_end = dur_sec // 3
        s2_end = s1_end * 2
        sections = {
            f"0-{s1_end}s": "hook",
            f"{s1_end}-{s2_end}s": "showcase",
            f"{s2_end}-{dur_sec}s": "closing",
        }
    elif dur_sec <= 30:
        # 中视频：4段
        s1 = dur_sec // 4
        s2 = s1 * 2
        s3 = s1 * 3
        sections = {
            f"0-{s1}s": "hook",
            f"{s1}-{s2}s": "showcase_1",
            f"{s2}-{s3}s": "showcase_2",
            f"{s3}-{dur_sec}s": "closing",
        }
    else:
        # 长视频：5段
        s1 = dur_sec // 5
        s2 = s1 * 2
        s3 = s1 * 3
        s4 = s1 * 4
        sections = {
            f"0-{s1}s": "hook",
            f"{s1}-{s2}s": "showcase_1",
            f"{s2}-{s3}s": "showcase_2",
            f"{s3}-{s4}s": "demo",
            f"{s4}-{dur_sec}s": "closing",
        }

    # 字幕 & 口播标记
    voice_tag = "With voiceover" if vs_config["voiceover"] else "No voiceover (visual-only)"
    sub_tag = "With on-screen subtitles" if vs_config["subtitle"] else "No subtitles"
    subtitle_hint = "On-screen subtitles overlay required. " if vs_config["subtitle"] else "No subtitles overlay. "

    # 构建 hook 段
    if vs_config["voiceover"]:
        hook_content = f"{subtitle_hint}{camera} as {physics}. {action}. {market_actor} interacts with {params['product_name']} with high energy motion."
    else:
        hook_content = f"NO voiceover. {subtitle_hint}{camera} as {physics}. {action}. Visual storytelling only. {market_actor} interacts with {params['product_name']} with high energy motion."

    # 构建 showcase 段
    showcase_content = "The camera continues dynamic movement. "
    if points:
        showcase_content += f"Showcasing {' and '.join(points[:2])} with rapid cuts and flowing transitions. "
    showcase_content += f"{market_actor} demonstrates the product with swift, confident movements."

    # 构建 closing 段
    closing_content = f"Epic final reveal. {params['product_name']} in perfect lighting. Dynamic slow-mo finale. Brand imprint, call to action."

    # 组装分段文本
    section_texts = {}
    section_keys = list(sections.keys())
    section_types = list(sections.values())
    for sk, st in zip(section_keys, section_types):
        if st == "hook":
            section_texts[sk] = f"[IMMEDIATE ACTION] {hook_content}"
        elif st.startswith("showcase"):
            section_texts[sk] = f"[Transition] {showcase_content}"
        elif st == "demo":
            section_texts[sk] = f"[Deep Demo] Detailed product interaction. Feature close-ups with smooth camera movement."
        elif st == "closing":
            section_texts[sk] = f"[Conclusion] {closing_content}"

    # 音频方案
    audio_plan = ""
    if vs_config["voiceover"] and params.get("video_script"):
        audio_plan = f"Voiceover: \"{params['video_script']}\""
    elif vs_config["voiceover"]:
        audio_plan = "Voiceover: dynamic product narration"
    if params.get("bgm_style"):
        audio_plan += (" | " if audio_plan else "") + f"BGM: {params['bgm_style']}"
    if not audio_plan:
        audio_plan = "Audio: Cinematic sync with motion"

    dynamic_strategy = f"{camera} + {physics} + {action}"

    # finalPrompt：英文，时长+画面比例+分辨率均根据平台调性
    sections_text = "\n\n".join(f"[{k}] {v}" for k, v in section_texts.items())
    final_prompt = (
        f"Strictly animate the provided product image.\n"
        f"Format: {orientation} {ratio}, {resolution}, {duration}, 30fps, MP4.\n"
        f"Platform: {profile['label']} | {voice_tag} | {sub_tag}\n"
        f"Vibe: {vibe}\n"
        f"Dynamic strategy: {dynamic_strategy}\n\n"
        f"{sections_text}\n\n"
        f"Style tags: High motion, cinematic movement, 4k, no static shots.\n"
        f"Maintain visual fidelity to the provided product image."
    )

    return {
        "index": index + 1,
        "audit": "图片: ✅ | 视频: ✅",
        "audioPlan": audio_plan,
        "dynamicStrategy": dynamic_strategy,
        "sections": section_texts,
        "finalPrompt": final_prompt,
    }


async def _build_ai_prompts(params: dict, count: int) -> list:
    """调用智谱 GLM 生成提示词"""
    from zhipuai import ZhipuAI

    client = ZhipuAI(api_key=settings.ZHIPUAI_API_KEY)

    points_str = params.get("selling_points") or "优质品质"
    script_str = params.get("video_script") or ""
    bgm_str = params.get("bgm_style") or "电影感配乐"
    market = MARKET_ACTORS.get(params["target_market"], "现代亚洲模特")

    # 平台档案
    platform = params.get("platform", "douyin")
    profile = PLATFORM_PROFILES.get(platform, PLATFORM_PROFILES["douyin"])

    # 口播字幕
    vs_key = params.get("voiceover_subtitle", "voice_with_sub")
    vs_config = VOICEOVER_SUBTITLE_MAP.get(vs_key, VOICEOVER_SUBTITLE_MAP["voice_with_sub"])

    system_prompt = (
        "你是一位专业的短视频广告创意总监，擅长为电商产品生成高质量的AI视频提示词（prompt）。"
        "你生成的提示词需要：1.英文输出 2.强调动态感、镜头运动 3.按时间段分段 "
        "4.视频时长和画面格式严格按目标平台调性适配 "
        "5.finalPrompt首行必须包含格式参数：orientation、ratio、resolution、duration、fps"
    )
    user_prompt = (
        f"为以下产品生成{count}条不同风格的AI视频提示词：\n"
        f"- 商品名称：{params['product_name']}\n"
        f"- 核心卖点：{points_str}\n"
        f"- 目标受众：{market}\n"
        f"- 目标平台：{profile['label']}\n"
        f"  画面比例：{profile['ratio']}  分辨率：{profile['resolution']}  时长：{profile['duration']}  方向：{profile['orientation']}\n"
        f"  平台调性：{profile['vibe']}\n"
        f"- 口播字幕：{'有口播' if vs_config['voiceover'] else '无口播'} + {'有字幕' if vs_config['subtitle'] else '无字幕'}\n"
        f"- 口播文案：{script_str or '无'}\n"
        f"- 背景音乐：{bgm_str}\n\n"
        f"每条提示词的 finalPrompt 必须按以下格式输出：\n"
        f"第1行：Strictly animate the provided product image.\n"
        f"第2行：Format: {profile['orientation']} {profile['ratio']}, {profile['resolution']}, {profile['duration']}, 30fps, MP4.\n"
        f"第3行：Platform: {profile['label']} | {'With voiceover' if vs_config['voiceover'] else 'No voiceover (visual-only)'} | {'With on-screen subtitles' if vs_config['subtitle'] else 'No subtitles'}\n"
        f"第4行：Vibe: {profile['vibe']}\n"
        f"然后是动态策略和分段时间轴。\n\n"
        f"分段规则：时长{profile['duration']}，根据时长均分为3-5段，每段标注时间区间。\n"
        f"首段为 [IMMEDIATE ACTION] hook，末段为 [Conclusion] closing，中间为展示段。\n\n"
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
        platform=req.platform,
        voiceover_subtitle=req.voiceover_subtitle,
        selling_points=req.selling_points,
        video_script=req.video_script,
        bgm_style=req.bgm_style,
        audio_option=req.audio_option,
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
