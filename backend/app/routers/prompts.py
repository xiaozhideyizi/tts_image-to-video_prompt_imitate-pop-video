import json
import secrets
import random
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app import models
from app.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

# ========== 动态起手库 ==========
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
    "china": "现代亚洲本土模特（非参考视频中人物，原创本土化形象）",
    "usa": "多元背景的美国本土模特（非参考视频中人物，原创本土化形象）",
    "europe": "欧洲时尚本土模特（非参考视频中人物，原创本土化形象）",
    "japan": "日本潮流本土模特（非参考视频中人物，原创本土化形象）",
    "korea": "韩系精致本土模特（非参考视频中人物，原创本土化形象）",
    "southeast_asia": "东南亚活力本土模特（非参考视频中人物，原创本土化形象）",
    "global": "国际多元化本土模特（非参考视频中人物，原创本土化形象）",
}

# ========== 平台档案 ==========
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
    "voice_no_sub":      {"voiceover": True,  "subtitle": False, "label": "口播无字幕"},
    "voice_with_sub":    {"voiceover": True,  "subtitle": True,  "label": "口播有字幕"},
    "no_voice_with_sub": {"voiceover": False, "subtitle": True,  "label": "无口播有字幕"},
    "no_voice_no_sub":   {"voiceover": False, "subtitle": False, "label": "无口播无字幕"},
}

# 卖点选项（预设 + 支持自定义）
SELLING_POINT_OPTIONS = [
    "高品质", "性价比", "新品首发", "限时优惠", "独家设计",
    "功效显著", "便携轻巧", "耐用可靠", "智能科技", "环保健康",
    "快速见效", "高端奢华", "口碑爆款", "定制服务", "送礼首选",
]

# 投放市场选项
MARKET_OPTIONS = [
    {"value": "china", "label": "中国大陆", "lang": "chinese"},
    {"value": "usa", "label": "美国", "lang": "english"},
    {"value": "europe", "label": "欧洲", "lang": "english"},
    {"value": "japan", "label": "日本", "lang": "japanese"},
    {"value": "korea", "label": "韩国", "lang": "korean"},
    {"value": "southeast_asia", "label": "东南亚", "lang": "chinese"},
    {"value": "global", "label": "全球", "lang": "english"},
]


# ========== 分组分段逻辑 ==========
def _split_prompt_by_duration(final_prompt: str, duration_sec: int) -> list:
    """
    如果平台推荐时长 ≤12s，直接传完整提示词；
    如果 >12s，按12s为单位分组，不足12s按12s算。
    返回分组后的提示词列表。
    """
    if duration_sec <= 12:
        return [final_prompt]

    groups = []
    num_groups = (duration_sec + 11) // 12  # 向上取整
    for i in range(num_groups):
        start_s = i * 12
        end_s = min((i + 1) * 12, duration_sec)
        group_prompt = (
            f"[Segment {i+1}/{num_groups} | {start_s}-{end_s}s]\n"
            f"This is segment {i+1} of {num_groups}. "
            f"Time range: {start_s}s to {end_s}s.\n\n"
            f"{final_prompt}\n\n"
            f"IMPORTANT: Only render the {start_s}-{end_s}s portion. "
            f"This segment must flow {'from the previous segment' if i > 0 else 'as the opening hook'}."
        )
        groups.append(group_prompt)
    return groups


# ========== 本地提示词生成 ==========
def _build_single_prompt(params: dict, index: int, has_video: bool = False, has_image: bool = False) -> dict:
    camera = random.choice(DYNAMIC_STARTERS["camera"])
    physics = random.choice(DYNAMIC_STARTERS["physics"])
    action = random.choice(DYNAMIC_STARTERS["action"])

    points = [p.strip() for p in params["selling_points"].split(",") if p.strip()]
    market_actor = MARKET_ACTORS.get(params["target_market"], MARKET_ACTORS["china"])

    platform = params.get("platform", "douyin")
    profile = PLATFORM_PROFILES.get(platform, PLATFORM_PROFILES["douyin"])

    vs_key = params.get("voiceover_subtitle", "voice_with_sub")
    vs_config = VOICEOVER_SUBTITLE_MAP.get(vs_key, VOICEOVER_SUBTITLE_MAP["voice_with_sub"])

    ratio = profile["ratio"]
    resolution = profile["resolution"]
    duration = profile["duration"]
    orientation = profile["orientation"]
    vibe = profile["vibe"]
    dur_sec = int(duration.replace("s", ""))

    # 根据时长计算分段
    if dur_sec <= 15:
        s1_end = dur_sec // 3
        s2_end = s1_end * 2
        sections = {f"0-{s1_end}s": "hook", f"{s1_end}-{s2_end}s": "showcase", f"{s2_end}-{dur_sec}s": "closing"}
    elif dur_sec <= 30:
        s1 = dur_sec // 4; s2 = s1 * 2; s3 = s1 * 3
        sections = {f"0-{s1}s": "hook", f"{s1}-{s2}s": "showcase_1", f"{s2}-{s3}s": "showcase_2", f"{s3}-{dur_sec}s": "closing"}
    else:
        s1 = dur_sec // 5; s2 = s1 * 2; s3 = s1 * 3; s4 = s1 * 4
        sections = {f"0-{s1}s": "hook", f"{s1}-{s2}s": "showcase_1", f"{s2}-{s3}s": "showcase_2", f"{s3}-{s4}s": "demo", f"{s4}-{dur_sec}s": "closing"}

    voice_tag = "With voiceover" if vs_config["voiceover"] else "No voiceover (visual-only)"
    sub_tag = "With on-screen subtitles" if vs_config["subtitle"] else "No subtitles"
    subtitle_hint = "On-screen subtitles overlay required. " if vs_config["subtitle"] else "No subtitles overlay. "

    # 参考视频风格指引：模仿风格/分镜/转场/动效/画面渲染，不抄人物
    video_style_note = ""
    if has_video:
        video_style_note = (
            "REFERENCE VIDEO STYLE: Analyze and replicate the reference video's "
            "cinematography style, shot composition, editing rhythm, transitions, "
            "motion effects, and visual rendering quality. "
            "DO NOT copy any human models, actors, or people from the reference video. "
            "All human figures must be ORIGINAL and LOCALLY ADAPTED for the target market. "
        )

    # 产品图片指引
    image_note = ""
    if has_image:
        image_note = "Strictly animate the provided product image. Maintain visual fidelity to the product's actual appearance. "

    # 构建 hook 段
    hook_content = f"{video_style_note}{subtitle_hint}"
    if not vs_config["voiceover"]:
        hook_content += "NO voiceover. Visual storytelling only. "
    hook_content += f"{camera} as {physics}. {action}. {market_actor} interacts with {params['product_name']} with high energy motion."

    # showcase 段
    showcase_content = "The camera continues dynamic movement. "
    if points:
        showcase_content += f"Showcasing {' and '.join(points[:2])} with rapid cuts and flowing transitions. "
    showcase_content += f"{market_actor} demonstrates the product with swift, confident movements."

    # closing 段
    closing_content = f"Epic final reveal. {params['product_name']} in perfect lighting. Dynamic slow-mo finale. Brand imprint, call to action."

    # 组装分段
    section_texts = {}
    for sk, st in sections.items():
        if st == "hook":
            section_texts[sk] = f"[IMMEDIATE ACTION] {hook_content}"
        elif st.startswith("showcase"):
            section_texts[sk] = f"[Transition] {showcase_content}"
        elif st == "demo":
            section_texts[sk] = "[Deep Demo] Detailed product interaction. Feature close-ups with smooth camera movement."
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
    sections_text = "\n\n".join(f"[{k}] {v}" for k, v in section_texts.items())

    final_prompt = (
        f"{image_note}"
        f"Format: {orientation} {ratio}, {resolution}, {duration}, 30fps, MP4.\n"
        f"Platform: {profile['label']} | {voice_tag} | {sub_tag}\n"
        f"Vibe: {vibe}\n"
        f"Dynamic strategy: {dynamic_strategy}\n\n"
        f"{sections_text}\n\n"
        f"Style tags: High motion, cinematic movement, 4k, no static shots.\n"
        f"CRITICAL: All human figures must be ORIGINAL, locally adapted for {params['target_market']} market. Never copy reference video people."
    )

    # 分组分段
    prompt_groups = _split_prompt_by_duration(final_prompt, dur_sec)

    return {
        "index": index + 1,
        "audit": f"图片: {'✅' if has_image else '❌'} | 视频: {'✅' if has_video else '❌'}",
        "audioPlan": audio_plan,
        "dynamicStrategy": dynamic_strategy,
        "sections": section_texts,
        "finalPrompt": final_prompt,
        "promptGroups": prompt_groups,
        "totalGroups": len(prompt_groups),
    }


# ========== AI 提示词生成 ==========
async def _build_ai_prompts(params: dict, count: int, has_video: bool = False, has_image: bool = False) -> list:
    """调用智谱 GLM 生成提示词"""
    from zhipuai import ZhipuAI

    client = ZhipuAI(api_key=settings.ZHIPUAI_API_KEY)

    points_str = params.get("selling_points") or "优质品质"
    script_str = params.get("video_script") or ""
    bgm_str = params.get("bgm_style") or "电影感配乐"
    market = MARKET_ACTORS.get(params["target_market"], MARKET_ACTORS["china"])

    platform = params.get("platform", "douyin")
    profile = PLATFORM_PROFILES.get(platform, PLATFORM_PROFILES["douyin"])

    vs_key = params.get("voiceover_subtitle", "voice_with_sub")
    vs_config = VOICEOVER_SUBTITLE_MAP.get(vs_key, VOICEOVER_SUBTITLE_MAP["voice_with_sub"])

    dur_sec = int(profile["duration"].replace("s", ""))

    # 参考视频指令
    video_instruction = ""
    if has_video:
        video_instruction = (
            "\n\nCRITICAL REFERENCE VIDEO RULES:\n"
            "- ANALYZE and REPLICATE the reference video's: cinematography style, shot composition, "
            "editing rhythm, transition effects, motion dynamics, and visual rendering quality.\n"
            "- DO NOT copy any human models, actors, or people from the reference video.\n"
            "- All human figures must be ORIGINAL and LOCALLY ADAPTED for the target market.\n"
            "- The模特/演员 must match the target market's local ethnicity and aesthetic preferences.\n"
        )

    image_instruction = ""
    if has_image:
        image_instruction = "\n- The provided product image must be strictly animated and maintained with visual fidelity.\n"

    # 分组分段指令
    group_instruction = ""
    if dur_sec > 12:
        num_groups = (dur_sec + 11) // 12
        group_instruction = (
            f"\n\nSEGMENT GROUPING RULE (Duration {dur_sec}s > 12s):\n"
            f"- Split into {num_groups} groups, each covering 12 seconds.\n"
            f"- Each group must be a complete, self-contained prompt segment.\n"
            f"- Groups must flow naturally from one to the next.\n"
            f"- Include a 'promptGroups' array field in each result, with {num_groups} string elements.\n"
        )
    else:
        group_instruction = "\n- Include a 'promptGroups' array with 1 element (the full prompt).\n"

    system_prompt = (
        "你是一位专业的短视频广告创意总监，擅长为电商产品生成高质量的AI视频提示词（prompt）。"
        "你生成的提示词需要：1.英文输出 2.强调动态感、镜头运动 3.按时间段分段 "
        "4.视频时长和画面格式严格按目标平台调性适配 "
        "5.finalPrompt首行必须包含格式参数 "
        "6.参考视频只模仿风格/分镜/转场/动效/画面渲染，绝不抄人物 7.模特必须本土化原创"
    )
    user_prompt = (
        f"为以下产品生成{count}条不同风格的AI视频提示词：\n"
        f"- 商品名称：{params['product_name']}\n"
        f"- 核心卖点：{points_str}\n"
        f"- 目标受众/模特：{market}\n"
        f"- 目标平台：{profile['label']}\n"
        f"  画面比例：{profile['ratio']}  分辨率：{profile['resolution']}  时长：{profile['duration']}  方向：{profile['orientation']}\n"
        f"  平台调性：{profile['vibe']}\n"
        f"- 口播字幕：{'有口播' if vs_config['voiceover'] else '无口播'} + {'有字幕' if vs_config['subtitle'] else '无字幕'}\n"
        f"- 口播文案：{script_str or '无'}\n"
        f"- 背景音乐：{bgm_str}"
        f"{video_instruction}"
        f"{image_instruction}"
        f"{group_instruction}"
        f"\n\n每条提示词的 finalPrompt 格式：\n"
        f"第1行：Format: {profile['orientation']} {profile['ratio']}, {profile['resolution']}, {profile['duration']}, 30fps, MP4.\n"
        f"第2行：Platform: {profile['label']} | {'With voiceover' if vs_config['voiceover'] else 'No voiceover'} | {'With subtitles' if vs_config['subtitle'] else 'No subtitles'}\n"
        f"第3行：Vibe: {profile['vibe']}\n"
        f"然后是动态策略和分段时间轴。末尾加: CRITICAL: All human figures must be ORIGINAL, locally adapted. Never copy reference video people.\n\n"
        f"以JSON数组格式返回，每个元素包含 index(1-{count})、finalPrompt、dynamicStrategy、audioPlan、promptGroups(数组) 字段。"
        f"只返回JSON，不要其他说明。"
    )

    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.9,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    ai_prompts = json.loads(raw)
    for p in ai_prompts:
        p.setdefault("audit", f"图片: {'✅' if has_image else '❌'} | 视频: {'✅' if has_video else '❌'}")
        # 确保 promptGroups 存在
        if "promptGroups" not in p:
            dur = int(profile["duration"].replace("s", ""))
            p["promptGroups"] = _split_prompt_by_duration(p.get("finalPrompt", ""), dur)
        p["totalGroups"] = len(p.get("promptGroups", [p.get("finalPrompt", "")]))
    return ai_prompts


# ========== 配置选项端点 ==========
@router.get("/options")
async def get_options():
    """返回前端需要的选项配置（卖点、市场等）"""
    return {
        "selling_points": SELLING_POINT_OPTIONS,
        "markets": MARKET_OPTIONS,
        "platforms": {k: {"label": v["label"], "ratio": v["ratio"], "resolution": v["resolution"],
                          "duration": v["duration"], "orientation": v["orientation"],
                          "lang": v["lang"]}
                      for k, v in PLATFORM_PROFILES.items()},
        "voiceover_subtitle": [{"value": k, **v} for k, v in VOICEOVER_SUBTITLE_MAP.items()],
    }


# ========== 生成端点（multipart/form-data）==========
@router.post("/generate")
async def generate_prompts(
    product_name: str = Form(...),
    target_market: str = Form("china"),
    target_language: str = Form("chinese"),
    platform: str = Form("douyin"),
    voiceover_subtitle: str = Form("voice_with_sub"),
    selling_points: str = Form(""),
    video_script: str = Form(""),
    bgm_style: str = Form(""),
    audio_option: str = Form("voiceover"),
    count: int = Form(3),
    use_ai: bool = Form(True),
    video: UploadFile = File(None),
    image: UploadFile = File(None),
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 读取上传文件
    video_data = None
    video_filename = None
    video_content_type = None
    image_data = None
    image_filename = None
    image_content_type = None

    if video:
        video_bytes = await video.read()
        if len(video_bytes) > 100 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="视频文件不能超过 100MB")
        video_data = video_bytes
        video_filename = video.filename
        video_content_type = video.content_type

    if image:
        image_bytes = await image.read()
        if len(image_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="图片文件不能超过 10MB")
        image_data = image_bytes
        image_filename = image.filename
        image_content_type = image.content_type

    has_video = video_data is not None
    has_image = image_data is not None

    params = {
        "product_name": product_name,
        "target_market": target_market,
        "target_language": target_language,
        "platform": platform,
        "voiceover_subtitle": voiceover_subtitle,
        "selling_points": selling_points,
        "video_script": video_script,
        "bgm_style": bgm_style,
        "audio_option": audio_option,
    }

    # 获取用户历史风格权重
    style_weights = {}
    # （后续可从用户最近采纳记录中读取权重）

    # 生成提示词
    if use_ai and settings.ZHIPUAI_API_KEY:
        try:
            prompts = await _build_ai_prompts(params, count, has_video, has_image)
        except Exception as e:
            print(f"[AI ERROR] {e}")
            prompts = [_build_single_prompt(params, i, has_video, has_image) for i in range(count)]
    else:
        prompts = [_build_single_prompt(params, i, has_video, has_image) for i in range(count)]

    # 保存历史记录
    history = models.PromptHistory(
        user_id=current_user.id,
        product_name=product_name,
        target_market=target_market,
        target_language=target_language,
        platform=platform,
        voiceover_subtitle=voiceover_subtitle,
        selling_points=selling_points,
        video_script=video_script,
        bgm_style=bgm_style,
        audio_option=audio_option,
        prompts_json=json.dumps(prompts, ensure_ascii=False),
        video_data=video_data,
        video_filename=video_filename,
        video_content_type=video_content_type,
        image_data=image_data,
        image_filename=image_filename,
        image_content_type=image_content_type,
        generated_count=len(prompts),
        adopted_count=0,
        style_weights=json.dumps(style_weights) if style_weights else None,
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)

    return {"prompts": prompts, "history_id": history.id}


# ========== 文件服务端点 ==========
@router.get("/history/{history_id}/video")
async def get_history_video(
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
    if not history or not history.video_data:
        raise HTTPException(status_code=404, detail="视频不存在")
    return Response(
        content=history.video_data,
        media_type=history.video_content_type or "video/mp4",
        headers={"Content-Disposition": f"inline; filename={history.video_filename or 'video.mp4'}"},
    )


@router.get("/history/{history_id}/image")
async def get_history_image(
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
    if not history or not history.image_data:
        raise HTTPException(status_code=404, detail="图片不存在")
    return Response(
        content=history.image_data,
        media_type=history.image_content_type or "image/jpeg",
        headers={"Content-Disposition": f"inline; filename={history.image_filename or 'image.jpg'}"},
    )


# ========== 评测端点 ==========
@router.post("/history/{history_id}/adopt")
async def adopt_prompt(
    history_id: int,
    prompt_index: int = Form(...),  # 采纳第几条提示词 (1-based)
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """用户采纳某条提示词 — 增加该风格权重"""
    result = await db.execute(
        select(models.PromptHistory).where(
            models.PromptHistory.id == history_id,
            models.PromptHistory.user_id == current_user.id,
        )
    )
    history = result.scalar_one_or_none()
    if not history:
        raise HTTPException(status_code=404, detail="记录不存在")

    history.adopted_count = (history.adopted_count or 0) + 1

    # 更新风格权重（采纳的风格增加权重）
    try:
        weights = json.loads(history.style_weights) if history.style_weights else {}
    except:
        weights = {}

    prompts = json.loads(history.prompts_json) if history.prompts_json else []
    if 0 < prompt_index <= len(prompts):
        p = prompts[prompt_index - 1]
        strategy = p.get("dynamicStrategy", "")
        for token in strategy.split("+"):
            token = token.strip()
            if token:
                weights[token] = weights.get(token, 1.0) * 1.2  # 采纳增加20%权重

    history.style_weights = json.dumps(weights)
    await db.commit()

    # 计算采纳率
    adoption_rate = (history.adopted_count / history.generated_count * 100) if history.generated_count else 0
    return {"ok": True, "adopted_count": history.adopted_count, "adoption_rate": round(adoption_rate, 1)}


@router.post("/history/{history_id}/violation")
async def report_violation(
    history_id: int,
    prompt_index: int = Form(...),  # 违规的第几条
    reason: str = Form(...),         # 违规原因
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """违规一票否决 — 违规原因作为前置条件，风格降低权重"""
    result = await db.execute(
        select(models.PromptHistory).where(
            models.PromptHistory.id == history_id,
            models.PromptHistory.user_id == current_user.id,
        )
    )
    history = result.scalar_one_or_none()
    if not history:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 追加违规原因
    existing = history.violation_reason or ""
    history.violation_reason = f"{existing};[{prompt_index}]{reason}" if existing else f"[{prompt_index}]{reason}"

    # 降低该风格权重
    try:
        weights = json.loads(history.style_weights) if history.style_weights else {}
    except:
        weights = {}

    prompts = json.loads(history.prompts_json) if history.prompts_json else []
    if 0 < prompt_index <= len(prompts):
        p = prompts[prompt_index - 1]
        strategy = p.get("dynamicStrategy", "")
        for token in strategy.split("+"):
            token = token.strip()
            if token:
                weights[token] = weights.get(token, 1.0) * 0.6  # 违规降低40%权重

    history.style_weights = json.dumps(weights)
    await db.commit()

    return {"ok": True, "violation_reason": history.violation_reason, "message": "违规已记录，原因将作为后续生成的前置约束条件"}


# ========== 评测统计端点 ==========
@router.get("/stats")
async def get_user_stats(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户评测统计：采纳率、违规率、质量率"""
    result = await db.execute(
        select(models.PromptHistory).where(
            models.PromptHistory.user_id == current_user.id,
        ).order_by(desc(models.PromptHistory.created_at)).limit(100)
    )
    histories = result.scalars().all()

    total_generated = sum(h.generated_count or 0 for h in histories)
    total_adopted = sum(h.adopted_count or 0 for h in histories)
    violation_count = sum(1 for h in histories if h.violation_reason)

    adoption_rate = (total_adopted / total_generated * 100) if total_generated else 0
    violation_rate = (violation_count / len(histories) * 100) if histories else 0
    quality_rate = ((len(histories) - violation_count) / len(histories) * 100) if histories else 0

    # 收集所有风格权重
    all_weights = {}
    for h in histories:
        try:
            w = json.loads(h.style_weights) if h.style_weights else {}
            for k, v in w.items():
                all_weights[k] = all_weights.get(k, 0) + v
        except:
            pass

    return {
        "total_sessions": len(histories),
        "total_generated": total_generated,
        "total_adopted": total_adopted,
        "violation_count": violation_count,
        "adoption_rate": round(adoption_rate, 1),
        "violation_rate": round(violation_rate, 1),
        "quality_rate": round(quality_rate, 1),
        "style_weights": all_weights,
        "violation_reasons": [h.violation_reason for h in histories if h.violation_reason],
    }


# ========== 历史记录 ==========
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
                "platform": h.platform,
                "target_market": h.target_market,
                "prompts_json": h.prompts_json,
                "created_at": h.created_at.isoformat(),
                "share_token": h.share_token,
                "has_video": h.video_data is not None,
                "has_image": h.image_data is not None,
                "generated_count": h.generated_count,
                "adopted_count": h.adopted_count,
                "violation_reason": h.violation_reason,
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
