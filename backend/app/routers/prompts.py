import json
import secrets
import random
import base64
import re
import os
import uuid
import asyncio
from typing import Optional, Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app import models
from app.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

# ========== 文件存储（本地文件系统，避免数据库 BYTEA 存大文件导致500）==========
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _save_uploaded_file(file_bytes: bytes, filename: str, content_type: str) -> Dict:
    """保存上传文件到本地磁盘，数据库只存JSON元信息"""
    ext = os.path.splitext(filename or "file")[1] or ".bin"
    file_id = uuid.uuid4().hex[:12]
    safe_name = f"{file_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    print(f"[FILE SAVE] {filename} -> {safe_name} ({len(file_bytes)} bytes)")
    return {
        "file_path": file_path,
        "file_id": file_id,
        "filename": filename,
        "content_type": content_type,
        "size": len(file_bytes),
    }


def _read_saved_file(file_meta: Dict) -> Optional[bytes]:
    """从本地磁盘读取文件"""
    path = file_meta.get("file_path")
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    return None


# ========== JSON 解析辅助函数 ==========
def _parse_ai_json_response(raw: str) -> list:
    """
    健壮地解析AI返回的JSON响应
    处理：markdown代码块、额外文字、单引号、尾随逗号等
    """
    if not raw:
        raise ValueError("AI返回空内容")

    raw = raw.strip()
    print(f"[AI JSON PARSER] Raw length: {len(raw)}")

    # 1. 移除markdown代码块
    if raw.startswith("```"):
        # 找到第一个换行后的内容
        first_newline = raw.find("\n")
        if first_newline != -1:
            raw = raw[first_newline+1:]
        # 移除结尾的 ```
        last_backticks = raw.rfind("```")
        if last_backticks != -1:
            raw = raw[:last_backticks]
        raw = raw.strip()

    # 2. 提取JSON数组（查找第一个 [ 和最后一个 ]）
    json_start = raw.find('[')
    json_end = raw.rfind(']')
    if json_start != -1 and json_end != -1 and json_end > json_start:
        json_str = raw[json_start:json_end+1]
    else:
        json_str = raw

    # 3. 尝试直接解析
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"[AI JSON PARSER] First parse failed: {e}")

    # 4. 尝试修复常见问题
    try:
        # 移除尾随逗号
        fixed = re.sub(r',\s*([\]}])', r'\1', json_str)
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        print(f"[AI JSON PARSER] Fix attempt 1 failed: {e}")

    # 5. 尝试修复单引号
    try:
        fixed = json_str.replace("'", '"')
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        print(f"[AI JSON PARSER] Fix attempt 2 failed: {e}")

    # 6. 最后尝试：使用正则提取对象
    try:
        # 尝试提取 {...} 模式
        pattern = r'\{[^{}]*\}'
        matches = re.findall(pattern, json_str)
        if matches:
            results = []
            for m in matches:
                try:
                    obj = json.loads(m)
                    results.append(obj)
                except:
                    continue
            if results:
                return results
    except Exception as e:
        print(f"[AI JSON PARSER] Regex extraction failed: {e}")

    raise ValueError(f"无法解析AI返回的JSON: {str(e)}")

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

# 投放市场选项 — 级联结构：国家 → 语言
MARKET_CASCADE = {
    "singapore":    {"label": "新加坡", "languages": [{"value": "english", "label": "英语"}, {"value": "chinese", "label": "中文"}, {"value": "malay", "label": "马来语"}]},
    "uk":           {"label": "英国", "languages": [{"value": "english", "label": "英语"}]},
    "usa":          {"label": "美国", "languages": [{"value": "english", "label": "英语"}, {"value": "spanish", "label": "西班牙语"}]},
    "saudi":        {"label": "沙特阿拉伯", "languages": [{"value": "arabic", "label": "阿拉伯语"}, {"value": "english", "label": "英语"}]},
    "uae":          {"label": "阿联酋", "languages": [{"value": "arabic", "label": "阿拉伯语"}, {"value": "english", "label": "英语"}]},
    "france":       {"label": "法国", "languages": [{"value": "french", "label": "法语"}, {"value": "english", "label": "英语"}]},
    "germany":      {"label": "德国", "languages": [{"value": "german", "label": "德语"}, {"value": "english", "label": "英语"}]},
    "italy":        {"label": "意大利", "languages": [{"value": "italian", "label": "意大利语"}, {"value": "english", "label": "英语"}]},
    "spain":        {"label": "西班牙", "languages": [{"value": "spanish", "label": "西班牙语"}, {"value": "english", "label": "英语"}]},
    "russia":       {"label": "俄罗斯", "languages": [{"value": "russian", "label": "俄语"}, {"value": "english", "label": "英语"}]},
    "japan":        {"label": "日本", "languages": [{"value": "japanese", "label": "日语"}, {"value": "english", "label": "英语"}]},
    "korea":        {"label": "韩国", "languages": [{"value": "korean", "label": "韩语"}, {"value": "english", "label": "英语"}]},
    "china":        {"label": "中国大陆", "languages": [{"value": "chinese", "label": "中文"}]},
    "taiwan":       {"label": "中国台湾", "languages": [{"value": "chinese", "label": "中文"}, {"value": "english", "label": "英语"}]},
    "hongkong":     {"label": "中国香港", "languages": [{"value": "chinese", "label": "中文"}, {"value": "english", "label": "英语"}]},
    "thailand":     {"label": "泰国", "languages": [{"value": "thai", "label": "泰语"}, {"value": "english", "label": "英语"}]},
    "vietnam":      {"label": "越南", "languages": [{"value": "vietnamese", "label": "越南语"}, {"value": "english", "label": "英语"}]},
    "indonesia":    {"label": "印尼", "languages": [{"value": "indonesian", "label": "印尼语"}, {"value": "english", "label": "英语"}]},
    "philippines":  {"label": "菲律宾", "languages": [{"value": "english", "label": "英语"}, {"value": "filipino", "label": "菲律宾语"}]},
    "malaysia":     {"label": "马来西亚", "languages": [{"value": "malay", "label": "马来语"}, {"value": "chinese", "label": "中文"}, {"value": "english", "label": "英语"}]},
    "brazil":       {"label": "巴西", "languages": [{"value": "portuguese", "label": "葡萄牙语"}, {"value": "english", "label": "英语"}]},
    "mexico":       {"label": "墨西哥", "languages": [{"value": "spanish", "label": "西班牙语"}, {"value": "english", "label": "英语"}]},
    "australia":    {"label": "澳大利亚", "languages": [{"value": "english", "label": "英语"}]},
    "canada":       {"label": "加拿大", "languages": [{"value": "english", "label": "英语"}, {"value": "french", "label": "法语"}]},
    "india":        {"label": "印度", "languages": [{"value": "english", "label": "英语"}, {"value": "hindi", "label": "印地语"}]},
    "turkey":       {"label": "土耳其", "languages": [{"value": "turkish", "label": "土耳其语"}, {"value": "english", "label": "英语"}]},
    "global":       {"label": "全球", "languages": [{"value": "english", "label": "英语"}]},
}

# 兼容旧版单选结构
MARKET_OPTIONS = [
    {"value": k, "label": v["label"], "lang": v["languages"][0]["value"]}
    for k, v in MARKET_CASCADE.items()
]


# ========== 视频模型配置 ==========
VIDEO_MODELS = {
    "kling":      {"label": "Kling",         "segment_unit": 15, "description": "快手可灵AI视频模型"},
    "seedance":   {"label": "Seedance 2.0",  "segment_unit": 15, "description": "字节即梦AI视频模型"},
    "google_omni":{"label": "Google Omni",    "segment_unit": 10, "description": "Google Veo/Omni视频模型"},
}


# ========== 提示词风格标签 ==========
STYLE_LABELS = [
    "痛点解决流",
    "UGC种草风",
    "产品场景展示",
    "暴力测试风",
    "情绪共鸣流",
    "极速快剪流",
    "高端大片风",
    "搞笑反转风",
]


# ========== 两段式分组分段逻辑 ==========
def _split_prompt_by_duration(final_prompt: str, duration_sec: int, video_model: str = "seedance", supplement: str = "") -> list:
    """
    两段式分段结构（按视频模型能力）：
    - kling / seedance: ≤15s直接传完整提示词, >15s按15s分段
    - google_omni: ≤10s直接传完整提示词, >10s按10s分段

    返回分组列表，每个元素包含 prompt/startTime/endTime/duration

    两段式结构：
    - 第一个分段（0-unit）: header + 所有分镜描述(0-5s+5-10s+...+最后一段) + Transition to NNs + footer
    - 最后一个分段（unit-end）: header + 后续分镜(bullet格式) + footer + supplement
    """
    import re

    unit = VIDEO_MODELS.get(video_model, VIDEO_MODELS["seedance"])["segment_unit"]

    if duration_sec <= unit:
        return [{
            "prompt": final_prompt,
            "startTime": 0,
            "endTime": duration_sec,
            "duration": duration_sec,
        }]

    time_breakdown_marker = "=== TIME SEGMENT BREAKDOWN ==="
    product_fidelity_marker = "=== PRODUCT FIDELITY REQUIREMENTS ==="

    header_end = final_prompt.find(time_breakdown_marker)
    footer_start = final_prompt.find(product_fidelity_marker)

    if header_end == -1 or footer_start == -1:
        print(f"[WARN] _split_prompt_by_duration: 未找到时间分段标记，使用完整提示词")
        return [{
            "prompt": final_prompt,
            "startTime": 0,
            "endTime": duration_sec,
            "duration": duration_sec,
        }]

    header = final_prompt[:header_end].strip()
    footer = final_prompt[footer_start:].strip()
    time_sections_raw = final_prompt[header_end + len(time_breakdown_marker):footer_start].strip()

    time_sections = {}
    current_range = None
    current_content = []

    for line in time_sections_raw.split('\n'):
        range_match = re.match(r'\s*\[?(\d+)\s*-\s*(\d+)s\]?\s*[:：]?', line)
        if range_match:
            if current_range and current_content:
                time_sections[current_range] = '\n'.join(current_content)
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            current_range = f"{start}-{end}"
            current_content = [line]
        elif current_range:
            current_content.append(line)

    if current_range and current_content:
        time_sections[current_range] = '\n'.join(current_content)

    print(f"[_split_prompt_by_duration] 解析到 {len(time_sections)} 个时间段: {list(time_sections.keys())}")

    # ---- 分段1（0 到 unit 秒）----
    group1_sections = []
    group2_sections = {}
    transition_hint = ""

    sorted_ranges = sorted(time_sections.items(), key=lambda x: int(x[0].split('-')[0]))

    for time_range, content in sorted_ranges:
        tr_start = int(time_range.split('-')[0])
        tr_end_str = time_range.split('-')[1]
        tr_end = int(tr_end_str) if tr_end_str else 0

        if tr_end <= unit:
            group1_sections.append(content)
        elif tr_start >= unit:
            adjusted_lines = []
            for line in content.split('\n'):
                adjusted = re.sub(
                    r'\[?(\d+)\s*-\s*(\d+)s\]?\s*[:：]?',
                    lambda m: f"[{int(m.group(1)) - unit}s-{int(m.group(2)) - unit}s]:",
                    line
                )
                adjusted_lines.append(adjusted)
            group2_sections[f"{tr_start - unit}-{tr_end - unit}"] = '\n'.join(adjusted_lines)
        else:
            lines = content.split('\n')
            part1_lines = []
            part2_lines = []
            capturing_part2 = False

            for line in lines:
                tmatch = re.match(r'\s*\[?(\d+)\s*-\s*(\d+)s\]?\s*[:：]?', line)
                if tmatch:
                    e = int(tmatch.group(2))
                    if e <= unit:
                        capturing_part2 = False
                        part1_lines.append(line)
                    else:
                        capturing_part2 = True
                        adj_line = re.sub(
                            r'\[?(\d+)\s*-\s*(\d+)s\]?\s*[:：]?',
                            lambda m: f"[{int(m.group(1)) - unit}s-{int(m.group(2)) - unit}s]:",
                            line
                        )
                        part2_lines.append(adj_line)
                elif capturing_part2:
                    part2_lines.append(line)
                else:
                    part1_lines.append(line)

            if part1_lines:
                group1_sections.append('\n'.join(part1_lines))
            if part2_lines:
                group2_sections[f"{unit - unit}-{tr_end - unit}"] = '\n'.join(part2_lines)

    # 从 group1 最后一段提取 Transition to
    if group1_sections:
        last_section = group1_sections[-1]
        last_lines = last_section.split('\n')
        clean_lines = []
        transition_parts = []
        in_transition = False

        for line in last_lines:
            stripped = line.strip()
            if not stripped:
                continue
            is_transition = bool(re.search(
                r'transition|fade to|cut to|then a|接着|然后|随后|next segment|continuing|延续',
                stripped, re.IGNORECASE
            ))
            is_time_marker = bool(re.match(r'\s*\[?\d+\s*-\s*\d+s\]?\s*[:：]?', stripped))

            if is_transition and not is_time_marker:
                transition_parts.append(stripped)
                in_transition = True
            elif is_time_marker:
                in_transition = False
                clean_lines.append(line)
            elif in_transition:
                transition_parts.append(stripped)
            else:
                clean_lines.append(line)

        group1_sections[-1] = '\n'.join(clean_lines)
        if transition_parts:
            transition_hint = "Transition to " + str(duration_sec) + "s: " + ' '.join(transition_parts)

    group1_parts = [header, "", '\n\n'.join(group1_sections)]
    if transition_hint:
        group1_parts.extend(["", transition_hint])
    group1_parts.extend(["", footer])

    groups = [{
        "prompt": '\n'.join(group1_parts),
        "startTime": 0,
        "endTime": unit,
        "duration": unit,
    }]

    # ---- 分段2（unit 到 duration_sec）：bullet 格式 ----
    remaining = duration_sec - unit
    offset = unit

    while remaining > 0:
        seg_dur = min(unit, remaining)
        start_s = offset
        end_s = offset + seg_dur

        segment_sections = []
        # group2_sections 的键是相对时间 (减去了 unit)，用相对范围比较
        rel_start = start_s - unit  # 此段的相对起始
        rel_end = end_s - unit      # 此段的相对结束
        for time_range, content in sorted(group2_sections.items(), key=lambda x: int(x[0].split('-')[0])):
            tr_start = int(time_range.split('-')[0])
            tr_end_str = time_range.split('-')[1]
            tr_end = int(tr_end_str) if tr_end_str else 0
            if tr_start >= rel_start and tr_end <= rel_end:
                segment_sections.append(content)

        bullet_lines = []
        for sec in segment_sections:
            for l in sec.split('\n'):
                l = l.strip()
                if not l:
                    continue
                tmatch = re.match(r'\[?(\d+)\s*-\s*(\d+)s\]?\s*[:：]?(.*)', l)
                if tmatch:
                    bullet_lines.append(f"- [{tmatch.group(1)}s-{tmatch.group(2)}s]: {tmatch.group(3).strip()}")
                elif l.startswith('-') or l.startswith('*'):
                    bullet_lines.append(l)
                else:
                    bullet_lines.append(f"- {l}")

        bullet_content = '\n'.join(bullet_lines)

        seg_parts = [header, "", bullet_content if bullet_content else "[No time sections in this range]", "", footer]
        if supplement:
            seg_parts.extend(["", supplement])

        groups.append({
            "prompt": '\n'.join(seg_parts),
            "startTime": start_s,
            "endTime": end_s,
            "duration": seg_dur,
        })

        remaining -= seg_dur
        offset = end_s

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

    # 根据时长计算分段（确保所有分支都定义 s1_end, s2_end）
    s1_end = dur_sec // 3
    s2_end = s1_end * 2
    if dur_sec <= 15:
        sections = {f"0-{s1_end}s": "hook", f"{s1_end}-{s2_end}s": "showcase", f"{s2_end}-{dur_sec}s": "closing"}
    elif dur_sec <= 30:
        s1 = dur_sec // 4; s2 = s1 * 2; s3 = s1 * 3
        s1_end = s2; s2_end = s3
        sections = {f"0-{s1}s": "hook", f"{s1}-{s2}s": "showcase_1", f"{s2}-{s3}s": "showcase_2", f"{s3}-{dur_sec}s": "closing"}
    else:
        s1 = dur_sec // 5; s2 = s1 * 2; s3 = s1 * 3; s4 = s1 * 4
        s1_end = s3; s2_end = s4
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

    # 产品图片强约束（1:1还原，不允许失真）
    image_note = ""
    if has_image:
        image_note = (
            "CRITICAL PRODUCT IMAGE FIDELITY RULE:\n"
            "- The uploaded product image MUST be faithfully replicated at 1:1 ratio without ANY distortion.\n"
            "- Product shape, color, texture, logo, and details MUST be 100% preserved.\n"
            "- NO creative alteration, NO style transfer, NO deformation of the product.\n"
            "- The product must appear EXACTLY as shown in the reference image, only animated.\n"
            "- Any AI-generated product that deviates from the uploaded image is STRICTLY FORBIDDEN.\n"
        )

    # 构建 hook 段（详细分镜描述）
    hook_content = f"{video_style_note}{subtitle_hint}"
    if not vs_config["voiceover"]:
        hook_content += "NO voiceover. Visual storytelling only. "
    hook_content += (
        f"{camera} as {physics}. {action}. \n"
        f"  DETAILED HOOK (0-{s1_end}s): \n"
        f"  - Camera: {camera}, rapid approach to {params['product_name']}.\n"
        f"  - Action: {action}, product revealed with {physics}.\n"
        f"  - {market_actor} appears with high energy, grabs attention in <2 seconds.\n"
        f"  - Product is positioned centrally, 1:1 ratio, no distortion.\n"
        f"  - Lighting: dramatic key light from top-right, rim light on product edges.\n"
        f"  - Transition: fast whip-pan into next segment.\n"
    )

    # showcase 段（详细分镜描述）
    showcase_content = ""
    for seg_idx, (sk, st) in enumerate(sections.items()):
        if st.startswith("showcase"):
            t_start = sk.split('-')[0]
            t_end = sk.split('-')[1].replace('s', '')
            pts_text = ', '.join(points[:3]) if points else 'premium quality'
            showcase_content += (
                f"  DETAILED SHOWCASE ({t_start}-{t_end}s):\n"
                f"  - Camera: smooth orbit around product, revealing {pts_text}.\n"
                f"  - Action: product rotates 45°, close-up on key features.\n"
                f"  - {market_actor} demonstrates with swift confident movements.\n"
                f"  - Product texture and material MUST match reference image exactly.\n"
                f"  - Lighting: soft fill + rim, product appears premium and polished.\n"
                f"  - Motion: flowing transitions, no abrupt cuts, 不超过3个镜头.\n"
            )

    # closing 段（详细分镜描述）
    closing_content = (
        f"  DETAILED CLOSING ({s2_end}-{dur_sec}s):\n"
        f"  - Camera: slow pull-back, epic reveal of {params['product_name']} in perfect lighting.\n"
        f"  - Action: product settles into hero shot position, 1:1 ratio, center frame.\n"
        f"  - Dynamic slow-mo finale (0.5x speed), water/smoke particles swirl around product.\n"
        f"  - Brand imprint fades in bottom-right, call to action top-left.\n"
        f"  - Final frame holds for 1.5s, product image EXACTLY matches uploaded reference.\n"
    )

    # 组装分段（每个时间段都有详细分镜描述）
    section_texts = {}
    for sk, st in sections.items():
        if st == "hook":
            section_texts[sk] = f"[IMMEDIATE ACTION] {hook_content}"
        elif st.startswith("showcase"):
            section_texts[sk] = f"[Transition] {showcase_content}"
        elif st == "demo":
            section_texts[sk] = (
                "[Deep Demo] Detailed product interaction with extreme close-ups. "
                "Camera moves in <10cm distance, revealing texture, material, craftsmanship. "
                "Lighting emphasizes premium feel. 4K macro shots, no distortion of product shape."
            )
        elif st == "closing":
            section_texts[sk] = f"[Conclusion] {closing_content}"

    # 音频方案（详细描述）
    audio_plan = ""
    if vs_config["voiceover"] and params.get("video_script"):
        audio_plan = f"Voiceover: \"{params['video_script']}\" (spoken with confident, energetic tone)"
    elif vs_config["voiceover"]:
        audio_plan = "Voiceover: dynamic product narration with native-speaking local actor, energetic and persuasive"
    if params.get("bgm_style"):
        audio_plan += (" | " if audio_plan else "") + f"BGM: {params['bgm_style']} (mixed at -12dB, ducking on voiceover)"
    if not audio_plan:
        audio_plan = "Audio: Cinematic sync with motion,  film-grade Foley effects, no voiceover"

    # 组装最终提示词（强制要求500+词，详细分镜描述）
    dynamic_strategy = f"{camera} + {physics} + {action}"
    sections_text = "\n\n".join(f"[{k}]\n{v}" for k, v in section_texts.items())

    # 计算目标词数（15s=500词，按比例调整）
    target_words = max(500, int(dur_sec * 33))  # 约33词/秒

    # 先构建 final_prompt（不含 style_label，避免 f-string 反斜杠错误）
    final_prompt = (
        "【产品场景展示】\n"
        f"{image_note}"
        f"Format: {orientation} {ratio}, {resolution}, {duration}, 30fps, MP4.\n"
        f"Platform: {profile['label']} | {voice_tag} | {sub_tag}\n"
        f"Vibe: {vibe}\n"
        f"Dynamic strategy: {dynamic_strategy}\n\n"
        f"=== TIME SEGMENT BREAKDOWN ===\n"
        f"{sections_text}\n\n"
        f"=== PRODUCT FIDELITY REQUIREMENTS ===\n"
        f"- Product MUST appear EXACTLY as in the uploaded reference image.\n"
        f"- 1:1 ratio, no distortion, no creative alteration of product shape/color/logo.\n"
        f"- Animate ONLY the product's presentation (rotation, lighting, particles), NOT its appearance.\n\n"
        f"Style tags: High motion, cinematic movement, 4k, no static shots, commercial-grade rendering.\n"
        f"CRITICAL: All human figures must be ORIGINAL, locally adapted for {params['target_market']} market. "
        f"Never copy reference video people.\n"
        f"FINAL CHECK: Before rendering verify product image matches uploaded reference 1:1. If not, regenerate."
    )

    # 根据提示词内容智能匹配风格标签
    style_label = _match_style_label("产品场景展示", final_prompt)
    # 把智能匹配的标签拼到 final_prompt 前面（用 + 拼接，避免 f-string 反斜杠错误）
    final_prompt = "【" + style_label + "】\n" + final_prompt

    # 分组分段（按视频模型能力）
    video_model = params.get("video_model", "seedance")
    prompt_groups = _split_prompt_by_duration(final_prompt, dur_sec, video_model, supplement="")

    return {
        "index": index + 1,
        "styleLabel": style_label,
        "audit": f"图片: {'✅' if has_image else '❌'} | 视频: {'✅' if has_video else '❌'}",
        "audioPlan": audio_plan,
        "dynamicStrategy": dynamic_strategy,
        "sections": section_texts,
        "finalPrompt": final_prompt,
        "promptGroups": prompt_groups,
        "totalGroups": len(prompt_groups),
        "videoModel": video_model,
        "segmentUnit": VIDEO_MODELS.get(video_model, VIDEO_MODELS["seedance"])["segment_unit"],
    }


def _build_detail_supplement(params: dict, profile: dict, dur_sec: int, needed_words: int) -> str:
    """生成镜头语言和氛围补充内容（不重复已有分镜描述），确保总词数达标"""
    atmosphere_descs = [
        "Ambient soundscape enhances the mood: soft fabric rustle, gentle ambient music building emotional resonance.",
        "Color grading: warm, inviting palette with high saturation on product highlights, slightly desaturated background.",
        "Camera movement follows product naturally: handheld feel with subtle shake for authenticity, stabilized in post.",
        "Pacing: starts slow and contemplative, gradually building momentum to an energetic climax.",
        "Lens: shallow depth of field throughout, product tack-sharp against smooth bokeh background.",
        "Aspect ratio: 9:16 vertical for mobile-first consumption, product occupies upper 2/3 of frame.",
        "Music: upbeat, trend-driven track with a clean beat drop at the climax moment.",
        "Transitions between scenes use natural motion: the product's movement dictates cut timing.",
        "Close-up inserts highlight texture and material quality of the product.",
        "Wide establishing shots place the product in aspirational lifestyle context.",
        "Slow-motion inserts at key emotional moments to amplify impact.",
        "Product reflection and shadow work are physically accurate and consistent throughout.",
    ]
    product_animation = [
        "Product rotates gently on a turntable: 360° in 3 seconds, then settles into hero pose.",
        "Fabric texture detail: macro shot of material weave, captured with focus stacking technique.",
        "Elastic band flex test: product stretched and released to demonstrate recovery properties.",
        "Color swatch comparison: product next to reference shades showing perfect color match.",
        "Packaging reveal: elegant unboxing sequence with slow pull-back to show full set.",
    ]

    parts = []
    words_generated = 0

    # 打乱顺序，避免每次都一样
    all_items = random.sample(atmosphere_descs + product_animation, len(atmosphere_descs + product_animation))

    for item in all_items:
        parts.append(item)
        words_generated += len(item.split())
        if words_generated >= needed_words:
            break

    return "\n".join(parts)


def _match_style_label(raw_label: str, final_prompt: str) -> str:
    """根据提示词内容智能匹配风格标签（不再随机）"""
    import re
    
    # 1. 如果AI返回的标签有效，直接使用
    if raw_label and raw_label in STYLE_LABELS:
        return raw_label
    
    # 2. 基于关键词匹配风格
    fp_lower = final_prompt.lower()
    
    # 定义每种风格的关键词
    style_keywords = {
        "痛点解决流": ["pain", "problem", "solution", "before", "after", "fix", "repair", "痛苦", "解决", "方案"],
        "UGC种草风": ["ugc", "user", "authentic", "real", "testimonial", "review", "用户", "真实", "测评"],
        "产品场景展示": ["scene", "lifestyle", "context", "usage", "scenario", "场景", "生活", "使用场景"],
        "暴力测试风": ["test", "durability", "extreme", "torture", "stress", "durable", "测试", "耐用", "极限"],
        "情绪共鸣流": ["emotion", "feeling", "relatable", "mood", "atmospheric", "情绪", "情感", "共鸣"],
        "极速快剪流": ["fast", "rapid", "dynamic", "energetic", "quick", "fast cut", "快剪", "动感", "快速"],
        "高端大片风": ["cinematic", "premium", "luxury", "high-end", "film", "高端", "大片", "质感"],
        "搞笑反转风": ["comedy", "humor", "funny", "twist", "surprise", "搞笑", "反转", "幽默"],
    }
    
    # 计算每种风格的匹配分数
    scores = {}
    for style, keywords in style_keywords.items():
        score = 0
        for keyword in keywords:
            if keyword in fp_lower:
                score += 1
        scores[style] = score
    
    # 返回分数最高的风格
    best_style = max(scores, key=scores.get)
    
    # 如果所有分数都是0，使用默认值（基于产品类型推测）
    if scores[best_style] == 0:
        # 默认返回"产品场景展示"（最通用）
        return "产品场景展示"
    
    return best_style


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

    # 分组分段指令（按视频模型能力）
    video_model = params.get("video_model", "seedance")
    unit = VIDEO_MODELS.get(video_model, VIDEO_MODELS["seedance"])["segment_unit"]
    model_label = VIDEO_MODELS.get(video_model, VIDEO_MODELS["seedance"])["label"]

    group_instruction = ""
    if dur_sec > unit:
        # 计算分组
        remaining = dur_sec
        groups_info = []
        offset = 0
        while remaining > 0:
            seg = min(unit, remaining)
            groups_info.append(f"{offset}-{offset+seg}s ({seg}s)")
            remaining -= seg
            offset += seg
        groups_desc = ", ".join(groups_info)
        group_instruction = (
            f"\n\nSEGMENT GROUPING RULE (Video model: {model_label}, unit: {unit}s, Duration: {dur_sec}s):\n"
            f"- Split into {len(groups_info)} groups: {groups_desc}\n"
            f"- Each group must be a complete, self-contained prompt segment with specific time range.\n"
            f"- For the LAST segment of each group, include: 'Transition to {next_group_start}s: [brief transition description]'\n"
            f"- Groups must flow naturally from one to the next.\n"
            f"- Include a 'promptGroups' array field in each result, with {len(groups_info)} string elements.\n"
        )
    else:
        group_instruction = "\n- Include a 'promptGroups' array with 1 element (the full prompt).\n"

    target_words = max(500, int(dur_sec * 33))  # 约33词/秒

    system_prompt = (
        "You are a world-class short-form video ad creative director specializing in AI video prompts for e-commerce products. "
        "Your prompts MUST meet these NON-NEGOTIABLE quality standards:\n\n"
        "🔴 LENGTH REQUIREMENT (MANDATORY):\n"
        f"   - Each finalPrompt MUST contain at least {target_words} words (minimum). No exceptions. No shortcuts.\n"
        "   - If you write less than the required word count, your output is REJECTED.\n"
        "   - Write EXTREMELY detailed, frame-by-frame cinematographic descriptions.\n"
        "   - Describe every camera movement, lighting change, particle effect, transition, and product interaction.\n\n"
        "🔴 PRODUCT IMAGE FIDELITY RULE (MANDATORY):\n"
        "   - The uploaded product image MUST be reproduced EXACTLY in the video (1:1 ratio, no distortion).\n"
        "   - Do NOT alter the product's shape, color, logo, packaging, or design in any way.\n"
        "   - You may ONLY animate its presentation (rotation, lighting, particles, zoom), NOT its appearance.\n"
        "   - Include this EXACT text in every finalPrompt: 'CRITICAL PRODUCT IMAGE FIDELITY RULE: Product MUST appear EXACTLY as in the uploaded reference image.'\n\n"
        "🔴 NO COPY PEOPLE RULE (MANDATORY):\n"
        "   - Reference videos are for STYLE REFERENCE ONLY (cinematography, shot composition, editing rhythm, transitions, motion dynamics, visual rendering).\n"
        "   - NEVER copy any human models, actors, faces, or people from reference videos.\n"
        "   - All human figures MUST be ORIGINAL creations, locally adapted for the target market's ethnicity and aesthetic.\n"
        "   - Include this EXACT text in every finalPrompt: 'CRITICAL: All human figures must be ORIGINAL and LOCALLY ADAPTED. Never copy reference video people.'\n\n"
        "🔴 OUTPUT FORMAT (MANDATORY):\n"
        "   - Output language: ENGLISH only for all prompt content.\n"
        "   - styleLabel MUST be one of these Chinese labels exactly: 痛点解决流, UGC种草风, 产品场景展示, 暴力测试风, 情绪共鸣流, 极速快剪流, 高端大片风, 搞笑反转风\n"
        "   - Return ONLY valid JSON array. No markdown, no explanation, no code blocks.\n"
    )

    user_prompt = (
        f"Generate {count} DIFFERENT style AI video prompts for this e-commerce product:\n\n"
        f"PRODUCT INFO:\n"
        f"- Name: {params['product_name']}\n"
        f"- Selling Points: {points_str}\n"
        f"- Target Market / Models: {market}\n\n"
        f"PLATFORM SPECIFICATIONS:\n"
        f"- Platform: {profile['label']}\n"
        f"- Aspect Ratio: {profile['ratio']} | Resolution: {profile['resolution']} | Duration: {profile['duration']} | Orientation: {profile['orientation']}\n"
        f"- Platform Vibe: {profile['vibe']}\n\n"
        f"AUDIO CONFIG:\n"
        f"- Voiceover: {'Yes' if vs_config['voiceover'] else 'No'} | Subtitles: {'Yes' if vs_config['subtitle'] else 'No'}\n"
        f"- Voiceover Script: {script_str or 'None'}\n"
        f"- BGM Style: {bgm_str}\n"
        f"{video_instruction}"
        f"{image_instruction}"
        f"{group_instruction}\n\n"
        f"=== REQUIRED finalPrompt STRUCTURE FOR EACH RESULT ===\n"
        f"Line 1: 【styleLabel】(choose one: 痛点解决流/UGC种草风/产品场景展示/暴力测试风/情绪共鸣流/极速快剪流/高端大片风/搞笑反转风)\n"
        f"Line 2: Format: {profile['orientation']} {profile['ratio']}, {profile['resolution']}, {profile['duration']}, 30fps, MP4.\n"
        f"Line 3: Platform: {profile['label']} | {'Voiceover + Subtitles' if vs_config['voiceover'] and vs_config['subtitle'] else 'Voiceover' if vs_config['voiceover'] else 'Subtitles' if vs_config['subtitle'] else 'No voiceover'}\n"
        f"Line 4: Vibe: {profile['vibe']}\n"
        f"Line 5: Dynamic strategy: [camera type] + [physics effect] + [action pattern]\n"
        f"Line 6+: DETAILED TIME SEGMENT BREAKDOWN ({target_words}+ words total minimum)\n"
        f"  - For EACH time segment, describe in extreme detail:\n"
        f"    * Camera movement (push/pull/pan/tilt/orbit/dolly/truck/crane) with speed and angle\n"
        f"    * Lighting changes (key/fill/back light, color temperature shifts)\n"
        f"    * Product presentation (rotation, zoom, particle effects around product)\n"
        f"    * Scene composition (foreground/midground/background elements)\n"
        f"    * Transitions between segments (cut/dissolve/wipe/zoom/match-cut)\n"
        f"    * Text/overlay placement and animation\n"
        f"    * Color grading mood for each segment\n"
        f"    * TRANSITION HINT: For the LAST segment of each group (e.g. 10-15s in a 20s video), append a transition line: 'Transition to {next_segment}s: [brief natural transition description]'\n"
        f"\n=== MANDATORY CLOSING SECTIONS (must appear verbatim in EVERY finalPrompt) ===\n"
        f"\n=== PRODUCT FIDELITY REQUIREMENTS ===\n"
        f"- Product MUST appear EXACTLY as in the uploaded reference image.\n"
        f"- 1:1 ratio, no distortion, no creative alteration of product shape/color/logo.\n"
        f"- Animate ONLY the product's presentation (rotation, lighting, particles), NOT its appearance.\n"
        f"\nStyle tags: High motion, cinematic movement, 4k, no static shots, commercial-grade rendering.\n"
        f"CRITICAL: All human figures must be ORIGINAL, locally adapted for {params['target_market']} market. Never copy reference video people.\n"
        f"FINAL CHECK: Before rendering verify product image matches uploaded reference 1:1. If not, regenerate.\n\n"
        f"Return JSON array with {count} elements. Each element MUST have fields: index(int), styleLabel(string), finalPrompt(string,{target_words}+ words), dynamicStrategy(string), audioPlan(string), promptGroups(array of strings).\n"
        f"ONLY return raw JSON. No markdown fences, no explanation."
    )

    response = await asyncio.to_thread(
        client.chat.completions.create,
        model="glm-4-flash",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.9,
    )

    raw = response.choices[0].message.content.strip()
    print(f"[AI RAW RESPONSE] Length={len(raw)}, Preview: {raw[:500]}...")

    # 使用健壮的JSON解析函数
    ai_prompts = _parse_ai_json_response(raw)

    # 后处理：校验并补充每条提示词的质量
    MANDATORY_SUFFIX = (
        "\n\n=== PRODUCT FIDELITY REQUIREMENTS ===\n"
        "- Product MUST appear EXACTLY as in the uploaded reference image.\n"
        "- 1:1 ratio, no distortion, no creative alteration of product shape/color/logo.\n"
        "- Animate ONLY the product's presentation (rotation, lighting, particles), NOT its appearance.\n\n"
        "Style tags: High motion, cinematic movement, 4k, no static shots, commercial-grade rendering.\n"
        f"CRITICAL: All human figures must be ORIGINAL, locally adapted for {params['target_market']} market. Never copy reference video people.\n"
        "FINAL CHECK: Before rendering verify product image matches uploaded reference 1:1. If not, regenerate."
    )

    for p in ai_prompts:
        fp = p.get("finalPrompt", "")
        word_count = len(fp.split())

        # 智能匹配风格标签（不再随机）
        raw_label = p.get("styleLabel", "")
        p["styleLabel"] = _match_style_label(raw_label, fp)

        p["audit"] = f"图片: {'✅' if has_image else '❌'} | 视频: {'✅' if has_video else '❌'} | AI词数: {word_count}"

        # 🔴 关键约束校验与自动补充
        needs_fidelity = "PRODUCT FIDELITY" not in fp.upper()
        needs_no_copy = "NEVER COPY" not in fp.upper() and "ORIGINAL" not in fp.upper()
        needs_min_words = word_count < target_words

        if needs_fidelity or needs_no_copy or needs_min_words:
            print(f"[AI POST-PROCESS] 提示词{p.get('index', '?')}校验: 词数={word_count}/{target_words}, 缺还原={needs_fidelity}, 缺不抄人物={needs_no_copy}")
            # 补充缺失的关键约束
            if needs_fidelity or needs_no_copy:
                fp = fp + MANDATORY_SUFFIX
                print(f"[AI POST-PROCESS] 已补充产品还原+不抄人物约束")

            # 如果词数仍不足，补充详细分镜描述
            if len(fp.split()) < target_words:
                supplement = _build_detail_supplement(params, profile, dur_sec, target_words - len(fp.split()))
                fp = fp + "\n\n" + supplement
                print(f"[AI POST-PROCESS] 已补充分镜描述，最终词数≈{len(fp.split())}")

            p["finalPrompt"] = fp

        # 确保 promptGroups 存在且内容完整
        if "promptGroups" not in p or not p["promptGroups"]:
            dur = int(profile["duration"].replace("s", ""))
            p["promptGroups"] = _split_prompt_by_duration(p.get("finalPrompt", ""), dur, video_model, supplement="")
        elif isinstance(p["promptGroups"][0], str):
            raw_groups = p["promptGroups"]
            structured = _split_prompt_by_duration(p.get("finalPrompt", ""), dur_sec, video_model, supplement="")
            for i, g in enumerate(structured):
                if i < len(raw_groups) and raw_groups[i]:
                    g["prompt"] = raw_groups[i]
                # 如果AI返回的分组提示词太短，用完整的finalPrompt分段替代
                if len(g.get("prompt", "").split()) < 30:
                    g["prompt"] = p["finalPrompt"]
            p["promptGroups"] = structured

        p["totalGroups"] = len(p.get("promptGroups", []))
        p["videoModel"] = video_model
        p["segmentUnit"] = unit

    return ai_prompts


# ========== AI 图片分析 ==========
async def _analyze_product_image(image_bytes: bytes) -> dict:
    """调用智谱 GLM-4V 分析产品图片，提取产品名称、描述、卖点"""
    from zhipuai import ZhipuAI

    client = ZhipuAI(api_key=settings.ZHIPUAI_API_KEY)

    # base64 编码图片
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    # 探测 MIME 类型（简单判断）
    mime = "image/jpeg"
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        mime = "image/png"
    elif image_bytes[:4] == b'RIFF':
        mime = "image/webp"

    system_prompt = (
        "你是一位资深电商产品分析师。请根据上传的产品图片，分析并输出以下信息（JSON格式）：\n"
        "1. product_name: 产品名称（简短，2-6个字）\n"
        "2. product_desc: 产品描述（一句话概括产品是什么、有什么特点）\n"
        "3. selling_points: 数组，3个最突出的营销卖点（每个4-8个字）\n"
        "只返回纯JSON，不要任何其他文字。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "请分析这张产品图片，输出产品名称、描述和3个核心卖点。"},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        },
    ]

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="glm-4v-flash",
            messages=messages,
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        print(f"[AI IMAGE ANALYSIS RAW] {raw[:500]}...")

        # 清理JSON响应
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        # 提取JSON对象
        json_start = raw.find('{')
        json_end = raw.rfind('}')
        if json_start != -1 and json_end != -1:
            raw = raw[json_start:json_end+1]

        result = json.loads(raw)
        return {
            "product_name": result.get("product_name", ""),
            "product_desc": result.get("product_desc", ""),
            "selling_points": result.get("selling_points", []),
        }
    except Exception as e:
        print(f"[AI IMAGE ANALYZE ERROR] {e}")
        return {
            "product_name": "",
            "product_desc": "",
            "selling_points": [],
        }


@router.post("/analyze-image")
async def analyze_image(
    image: UploadFile = File(...),
    # 临时去掉登录验证，方便测试
    # current_user: models.User = Depends(get_current_user),
):
    """上传产品图片，AI自动分析产品名称、描述和卖点"""
    image_bytes = await image.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片文件不能超过 10MB")

    if not settings.ZHIPUAI_API_KEY:
        raise HTTPException(status_code=503, detail="AI分析服务未配置")

    try:
        # 60秒超时保护（图片分析不需要生成提示词，60s足够）
        result = await asyncio.wait_for(
            _analyze_product_image(image_bytes),
            timeout=60.0
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="AI分析超时，请稍后重试")


# ========== AI 服务状态检查 ==========
@router.get("/check-ai")
async def check_ai_service():
    """检查智谱 AI 服务是否可用"""
    has_key = bool(settings.ZHIPUAI_API_KEY and settings.ZHIPUAI_API_KEY != "your-zhipuai-api-key-here")
    return {
        "ai_available": has_key,
        "message": "AI分析服务已就绪" if has_key else "AI分析服务未配置，请在 Railway 环境变量中设置 ZHIPUAI_API_KEY",
    }


# ========== 配置选项端点 ==========
@router.get("/options")
async def get_options():
    """返回前端需要的选项配置（卖点、市场等）"""
    return {
        "selling_points": SELLING_POINT_OPTIONS,
        "markets": MARKET_OPTIONS,
        "market_cascade": MARKET_CASCADE,
        "platforms": {k: {"label": v["label"], "ratio": v["ratio"], "resolution": v["resolution"],
                          "duration": v["duration"], "orientation": v["orientation"],
                          "lang": v["lang"]}
                      for k, v in PLATFORM_PROFILES.items()},
        "voiceover_subtitle": [{"value": k, **v} for k, v in VOICEOVER_SUBTITLE_MAP.items()],
        "video_models": VIDEO_MODELS,
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
    video_model: str = Form("seedance"),
    count: int = Form(3),
    use_ai: bool = Form(True),
    video: UploadFile = File(None),
    image: UploadFile = File(None),
    # 临时去掉登录验证，方便测试
    # current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 读取上传文件 → 存到本地文件系统（不存数据库 BYTEA）
    video_meta = None
    image_meta = None

    if video:
        video_bytes = await video.read()
        if len(video_bytes) > 100 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="视频文件不能超过 100MB")
        video_meta = _save_uploaded_file(video_bytes, video.filename or "video.mp4", video.content_type or "video/mp4")
        print(f"[UPLOAD] 视频已保存: {video_meta['filename']} ({video_meta['size']} bytes)")

    if image:
        image_bytes = await image.read()
        if len(image_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="图片文件不能超过 10MB")
        image_meta = _save_uploaded_file(image_bytes, image.filename or "image.jpg", image.content_type or "image/jpeg")
        print(f"[UPLOAD] 图片已保存: {image_meta['filename']} ({image_meta['size']} bytes)")

    has_video = video_meta is not None
    has_image = image_meta is not None

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
        "video_model": video_model,
    }

    # 获取用户历史风格权重
    style_weights = {}
    # （后续可从用户最近采纳记录中读取权重）

    # 生成提示词 - AI模式优先（强化提示词+后处理校验），失败则fallback本地模式
    if use_ai and settings.ZHIPUAI_API_KEY:
        try:
            # 90秒超时保护，避免智谱API响应慢导致前端120s超时
            prompts = await asyncio.wait_for(
                _build_ai_prompts(params, count, has_video, has_image),
                timeout=90.0
            )
            print(f"[GENERATE] AI生成成功，共{len(prompts)}条")
        except asyncio.TimeoutError:
            import traceback
            print(f"[AI TIMEOUT] 智谱API响应超时（90s），回退本地模式")
            traceback.print_exc()
            try:
                prompts = [_build_single_prompt(params, i, has_video, has_image) for i in range(count)]
                print(f"[FALLBACK] 本地生成成功，共{len(prompts)}条（AI超时已自动回退）")
            except Exception as e2:
                import traceback
                print(f"[LOCAL FALLBACK ERROR] {e2}")
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"生成失败: {str(e2)}")
        except Exception as e:
            import traceback
            print(f"[AI ERROR] {e}")
            traceback.print_exc()
            try:
                prompts = [_build_single_prompt(params, i, has_video, has_image) for i in range(count)]
                print(f"[FALLBACK] 本地生成成功，共{len(prompts)}条（AI失败已自动回退）")
            except Exception as e2:
                import traceback
                print(f"[LOCAL FALLBACK ERROR] {e2}")
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"生成失败: {str(e2)}")
    else:
        if use_ai and not settings.ZHIPUAI_API_KEY:
            print(f"[WARN] 用户选择AI模式但ZHIPUAI_API_KEY未配置，使用本地模式")
        try:
            prompts = [_build_single_prompt(params, i, has_video, has_image) for i in range(count)]
            print(f"[GENERATE] 本地生成成功，共{len(prompts)}条")
        except Exception as e:
            import traceback
            print(f"[LOCAL GENERATE ERROR] {e}")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")

    # 保存历史记录（文件存本地，数据库只存JSON元信息）
    try:
        history = models.PromptHistory(
            user_id=1,  # TODO: 恢复登录后改回 current_user.id
            product_name=product_name,
            target_market=target_market,
            target_language=target_language,
            platform=platform,
            voiceover_subtitle=voiceover_subtitle,
            selling_points=selling_points,
            video_script=video_script,
            bgm_style=bgm_style,
            audio_option=audio_option,
            video_model=video_model,
            prompts_json=json.dumps(prompts, ensure_ascii=False),
            video_data=None,  # 不再存BYTEA
            video_filename=json.dumps(video_meta, ensure_ascii=False) if video_meta else None,
            video_content_type=video_meta.get("content_type") if video_meta else None,
            image_data=None,  # 不再存BYTEA
            image_filename=json.dumps(image_meta, ensure_ascii=False) if image_meta else None,
            image_content_type=image_meta.get("content_type") if image_meta else None,
            generated_count=len(prompts),
            adopted_count=0,
            style_weights=json.dumps(style_weights) if style_weights else None,
        )
        db.add(history)
        await db.commit()
        await db.refresh(history)
        print(f"[DB SAVE] 历史记录保存成功, id={history.id}")
    except Exception as db_err:
        import traceback
        print(f"[DB SAVE ERROR] {db_err}")
        traceback.print_exc()
        await db.rollback()
        # 数据库保存失败仍返回结果，不阻断用户
        history = None

    return {"prompts": prompts, "history_id": history.id if history else None}


# ========== 文件服务端点（从本地文件系统读取）==========
@router.get("/history/{history_id}/video")
async def get_history_video(
    history_id: int,
    # current_user: models.User = Depends(get_current_user),  # 临时去掉登录验证
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(models.PromptHistory).where(models.PromptHistory.id == history_id)
    )
    history = result.scalar_one_or_none()
    if not history or not history.video_filename:
        raise HTTPException(status_code=404, detail="视频不存在")
    # video_filename 现在存的是JSON元信息
    try:
        video_meta = json.loads(history.video_filename)
    except (TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=404, detail="视频文件信息损坏")
    file_bytes = _read_saved_file(video_meta)
    if not file_bytes:
        raise HTTPException(status_code=404, detail="视频文件已过期（服务重启后临时文件已清除）")
    return Response(
        content=file_bytes,
        media_type=video_meta.get("content_type", "video/mp4"),
        headers={"Content-Disposition": f"inline; filename={video_meta.get('filename', 'video.mp4')}"},
    )


@router.get("/history/{history_id}/image")
async def get_history_image(
    history_id: int,
    # current_user: models.User = Depends(get_current_user),  # 临时去掉登录验证
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(models.PromptHistory).where(models.PromptHistory.id == history_id)
    )
    history = result.scalar_one_or_none()
    if not history or not history.image_filename:
        raise HTTPException(status_code=404, detail="图片不存在")
    # image_filename 现在存的是JSON元信息
    try:
        image_meta = json.loads(history.image_filename)
    except (TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=404, detail="图片文件信息损坏")
    file_bytes = _read_saved_file(image_meta)
    if not file_bytes:
        raise HTTPException(status_code=404, detail="图片文件已过期（服务重启后临时文件已清除）")
    return Response(
        content=file_bytes,
        media_type=image_meta.get("content_type", "image/jpeg"),
        headers={"Content-Disposition": f"inline; filename={image_meta.get('filename', 'image.jpg')}"},
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
    # current_user: models.User = Depends(get_current_user),  # 临时去掉登录验证
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    result = await db.execute(
        select(models.PromptHistory)
        # .where(models.PromptHistory.user_id == current_user.id)  # 临时去掉
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
                "has_video": h.video_filename is not None,  # 改为检查filename字段
                "has_image": h.image_filename is not None,  # 改为检查filename字段
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
