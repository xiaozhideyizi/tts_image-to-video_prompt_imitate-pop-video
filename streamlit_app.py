````python name=app/streamlit_app.py
"""
Streamlit UI: 优化版提示词生成器前端（单文件）

说明:
- 美化了布局与样式，增加了素材审计预览、生成多条 Prompt、每条结果的复制与 regenerate（重生）流程。
- 依赖: streamlit, requests, pillow
- 假设后端提供以下接口（需后端实现）:
  - POST {BACKEND_URL}/generate
    接收 multipart/form-data: image (file, optional), video (file, optional), product_name, selling_points (文本, 换行分隔), target_market, target_language, output_count, audio_option, bgm_style
    返回 JSON: {"results":[{"id":"r1","audit":{...},"tradeoff":"...","av_plan":"...","final_prompt":"...","tags":["..."]}, ...]}
  - POST {BACKEND_URL}/regenerate
    接收 JSON: {"result_id": "...", "original_prompt": "...", "adjustment_type": "...", "note": "..."}
    返回 JSON: {"result": {"id":"r1-v2","final_prompt":"...","note":"..."}}
- 若后端不可用，UI 会显示友好错误并给出示例占位 prompt 以便继续 UX 流程。

部署:
- 把本文件放到仓库的 app/streamlit_app.py，Streamlit 部署页面 Main file path 填 app/streamlit_app.py
"""

import streamlit as st
import requests
from PIL import Image
import io
import re
import uuid
import json
from typing import List, Dict

# 后端地址（生产环境用真实地址或通过 env 配置）
BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")

# ------ 样式 ------
st.set_page_config(page_title="提示词生成器（高动态 12s 视频）", layout="wide")
st.markdown(
    """
    <style>
    .header {
        display:flex; align-items:center; gap:12px;
    }
    .app-title { font-size:22px; font-weight:700; }
    .sub { color: #6c757d; font-size:13px; }
    .card { padding:14px; border-radius:8px; background:#ffffff; box-shadow:0 1px 4px rgba(16,24,40,0.04); }
    .chip { display:inline-block; padding:4px 8px; border-radius:999px; background:#eef2ff; color:#4338ca; font-size:12px; margin-right:6px; }
    .warn { color:#b45309; font-weight:600; }
    .ok { color:#065f46; font-weight:600; }
    .prompt-area { background:#0f172a10; padding:10px; border-radius:6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------ 会话状态初始化 ------
if "results" not in st.session_state:
    st.session_state["results"] = []  # 每项: dict 包含 id, final_prompt, audit, tradeoff, av_plan, tags, versions
if "last_request" not in st.session_state:
    st.session_state["last_request"] = {}
if "regenerate_target" not in st.session_state:
    st.session_state["regenerate_target"] = None
if "upload_preview" not in st.session_state:
    st.session_state["upload_preview"] = {"image": None, "video": None, "image_info": None}

# ------ 辅助函数 ------
BANNED_TOKENS = ["is placed", "stands", "sits", "is shown", "is displayed", "is on"]

def check_dynamic_first(final_prompt_text: str):
    """
    检查 Final Prompt 中 [0-4s] 段是否包含禁止静态词汇，并是否包含至少一个动态关键词。
    返回 (ok:bool, reasons:list)
    """
    reasons = []
    if not final_prompt_text:
        reasons.append("Prompt 为空")
        return False, reasons
    lower = final_prompt_text.lower()
    m = re.search(r"\[0-4s\](.*?)(?=\[4-8s\]|\[8-12s\]|$)", lower, re.S)
    first_segment = m.group(1) if m else lower.splitlines()[:5]
    # 检查禁止词
    for token in BANNED_TOKENS:
        if token in first_segment:
            reasons.append(f"包含禁止静态词汇: '{token}'")
    # 动态关键词检测
    dynamic_keywords = ["fast dolly", "rapid orbit", "handheld shake", "whip pan", "water", "explod", "grab", "drops", "transformation", "wind blowing", "smoke swirling", "light streaks"]
    if not any(k in first_segment for k in dynamic_keywords):
        reasons.append("开头缺少强动作/强物理/强运镜等动态关键词")
    return (len(reasons) == 0), reasons

def render_copy_button(text: str, key: str):
    """在 Streamlit 中通过 small JS 实现复制到剪贴板"""
    escaped = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")
    html = f"""
    <button onclick="navigator.clipboard.writeText('{escaped}')" style="background:#2563eb;color:white;padding:6px 10px;border-radius:6px;border:none;cursor:pointer;">
      Copy
    </button>
    """
    st.markdown(html, unsafe_allow_html=True)

def call_backend_generate(form_data: dict, files: dict, timeout=180):
    url = f"{BACKEND_URL.rstrip('/')}/generate"
    try:
        resp = requests.post(url, data=form_data, files=files, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"调用后端生成失败: {e}")
        return None

def call_backend_regenerate(result_id: str, original_prompt: str, adjustment_type: str, note: str):
    url = f"{BACKEND_URL.rstrip('/')}/regenerate"
    payload = {"result_id": result_id, "original_prompt": original_prompt, "adjustment_type": adjustment_type, "note": note}
    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"调用后端重生/regenerate 失败: {e}")
        return None

def sample_prompt_stub(product_name="Product"):
    return (
        "Strictly animate the provided product image. Vertical 9:16, 12 seconds.\n"
        "[Dynamic Start Command: High motion velocity, no static frames].\n\n"
        "[0-4s] [IMMEDIATE ACTION]: Fast Dolly Zoom in towards the product; water explodes and splashes around the product instantly, camera performs a rapid orbit while handheld shake adds micro-jerk.\n"
        "[4-8s] [Transition]: Rapid whip pan to a close-up; product rotates revealing texture and selling point.\n"
        "[8-12s] [Conclusion]: Product glows and shoots light streaks upward; final hero pull-away shot with cinematic rack focus.\n\n"
        "Style tags: High motion, cinematic, 4k, no static shots.\n"
        "Maintain visual fidelity to the provided product image."
    )

def safe_read_image(file_uploader):
    if not file_uploader:
        return None, None
    try:
        b = file_uploader.getvalue()
        im = Image.open(io.BytesIO(b))
        return im, b
    except Exception:
        return None, None

# ------ UI: Header ------
col1, col2 = st.columns([0.8, 0.2])
with col1:
    st.markdown('<div class="header"><div class="app-title">提示词生成器（高动态 12s 视频）</div><div class="sub">生成适配图生视频的 12s 强动态 Prompt — 可重生/微调</div></div>', unsafe_allow_html=True)
with col2:
    st.button("Help", key="help_btn")

st.write("")  # spacing

# ------ 左侧栏: 表单 ------
with st.sidebar:
    st.header("素材 & 参数")
    image_file = st.file_uploader("上传商品图片 (png/jpg/webp)", type=["png", "jpg", "jpeg", "webp"], help="建议竖屏 1080x1920 以上")
    video_file = st.file_uploader("上传参考视频 (mp4,mov)", type=["mp4", "mov"], help="可选，作为节奏参考")
    product_name = st.text_input("商品名称", value="")
    selling_points = st.text_area("商品卖点（每行一条，最多6条）", value="", height=120)
    target_market = st.selectbox("投放市场", ["US", "China", "Japan", "EU", "Other"])
    target_language = st.selectbox("投放语言", ["English", "中文", "日本語"])
    output_count = st.slider("输出条数", 1, 5, 3)
    audio_option = st.selectbox("音频选项", ["TTS", "Human voice", "None"])
    bgm_style = st.text_input("BGM 风格 (例如: energetic pop)", value="energetic pop")
    motion_intensity = st.selectbox("运动强度", ["Light", "Medium", "Heavy"], index=2)
    generate_btn = st.button("生成提示词", type="primary")

# ------ 素材审计预览 ------
with st.container():
    st.markdown("### 素材审计 (Audit)")
    col_a, col_b = st.columns([1, 2])
    with col_a:
        if image_file:
            im, raw = safe_read_image(image_file)
            if im:
                st.image(im, caption="商品图片预览", use_column_width=True)
                w, h = im.size
                st.write(f"分辨率: {w} x {h}")
                if w < 720 or h < 1280:
                    st.markdown("<div class='warn'>⚠️ 建议使用更高分辨率（推荐 ≥1080x1920）以保证渲染质量</div>", unsafe_allow_html=True)
                st.session_state["upload_preview"]["image"] = raw
                st.session_state["upload_preview"]["image_info"] = {"w": w, "h": h, "mode": im.mode}
            else:
                st.warning("无法读取图片（可能格式不支持）")
        else:
            st.info("尚未上传商品图片。")

        if video_file:
            st.video(video_file)
            st.session_state["upload_preview"]["video"] = video_file.getvalue()
        else:
            st.info("参考视频（可选）未上传。")

    with col_b:
        st.markdown("#### 审计摘要")
        audit_summary = {}
        audit_summary["image"] = "✅" if image_file else "⚠️ 无图片（强烈建议上传）"
        if image_file and st.session_state["upload_preview"]["image_info"]:
            info = st.session_state["upload_preview"]["image_info"]
            audit_summary["resolution"] = f'{info["w"]}x{info["h"]}, mode={info["mode"]}'
        if video_file:
            audit_summary["video"] = "✅ 已上传参考视频"
        st.json(audit_summary)

# ------ 生成按钮逻辑 ------
if generate_btn:
    # 验证必要字段
    if not product_name:
        st.error("请填写商品名称。")
    elif not selling_points.strip():
        st.error("请填写至少一条商品卖点。")
    else:
        with st.spinner("正在提交生成请求…（可能需要几秒到几十秒）"):
            # 准备表单与文件
            form = {
                "product_name": product_name,
                "selling_points": selling_points,
                "target_market": target_market,
                "target_language": target_language,
                "output_count": str(output_count),
                "audio_option": audio_option,
                "bgm_style": bgm_style,
                "motion_intensity": motion_intensity,
            }
            files = {}
            if image_file:
                files["image"] = (image_file.name, image_file.getvalue())
            if video_file:
                files["video"] = (video_file.name, video_file.getvalue())

            resp = call_backend_generate(form, files)
            if resp and isinstance(resp, dict) and "results" in resp:
                results = resp["results"]
                # 规范化并存入 session_state
                for r in results:
                    # ensure id exists
                    r_id = r.get("id") or str(uuid.uuid4())
                    entry = {
                        "id": r_id,
                        "final_prompt": r.get("final_prompt", ""),
                        "audit": r.get("audit", {}),
                        "tradeoff": r.get("tradeoff", ""),
                        "av_plan": r.get("av_plan", ""),
                        "tags": r.get("tags", []),
                        "versions": [r.get("final_prompt", "")],
                    }
                    st.session_state["results"].append(entry)
                st.success(f"生成完成，共 {len(results)} 条结果已添加。")
            else:
                # 后端不可用或返回异常：使用占位示例以保持流程
                st.warning("后端不可用或返回异常，已使用示例 Prompt 填充以便继续体验。")
                for i in range(output_count):
                    entry = {
                        "id": f"stub-{uuid.uuid4().hex[:6]}",
                        "final_prompt": sample_prompt_stub(product_name),
                        "audit": {"image": "OK" if image_file else "NO_IMAGE"},
                        "tradeoff": "示例 Trade-off（后端不可用）",
                        "av_plan": "示例 AV Plan",
                        "tags": ["demo", "sample"],
                        "versions": [sample_prompt_stub(product_name)],
                    }
                    st.session_state["results"].append(entry)

# ------ Regenerate panel: 当用户点击某条结果的 Regenerate 后在页面顶部显示选项面板 ------
if st.session_state["regenerate_target"] is not None:
    idx = st.session_state["regenerate_target"]
    if 0 <= idx < len(st.session_state["results"]):
        target = st.session_state["results"][idx]
        st.markdown("---")
        st.markdown(f"### 重新生成: Prompt #{idx+1}")
        st.markdown("选择重生预设或填写自定义说明，系统会基于原 Prompt 进行微调（保留原结构）。")
        colx1, colx2 = st.columns([2, 1])
        with colx1:
            preset = st.selectbox("快速预设", ["increase_motion", "slower_pacing", "emphasize_texture", "localize_dialogue", "only_change_audio"], index=0, key=f"preset_{idx}")
            note = st.text_area("额外说明（可选）", value="", key=f"note_{idx}", height=80)
        with colx2:
            st.markdown("原始 Prompt（只读）")
            st.text_area("原 Prompt", value=target["final_prompt"], height=200, key=f"orig_prompt_{idx}", disabled=True)
            if st.button("确认重新生成", key=f"confirm_regen_{idx}"):
                with st.spinner("正在请求重生…"):
                    resp = call_backend_regenerate(target["id"], target["final_prompt"], preset, note)
                    if resp and "result" in resp:
                        new = resp["result"]
                        # append version and update
                        target["versions"].append(new.get("final_prompt", ""))
                        target["final_prompt"] = new.get("final_prompt", "")
                        # set back
                        st.session_state["results"][idx] = target
                        st.success("重生成功，已替换当前 Prompt（历史版本保留）。")
                    else:
                        st.warning("后端重生失败，已使用示例变体填充。")
                        new_prompt = target["final_prompt"] + "\n\n# Regenerated (示例变体: " + preset + ")"
                        target["versions"].append(new_prompt)
                        target["final_prompt"] = new_prompt
                        st.session_state["results"][idx] = target
                st.session_state["regenerate_target"] = None
        st.markdown("---")

# ------ 结果展示区 ------
st.markdown("## 生成结果")
if not st.session_state["results"]:
    st.info("尚无生成结果。点击侧栏的“生成提示词”以开始。")
else:
    for i, res in enumerate(st.session_state["results"]):
        with st.container():
            st.markdown(f"<div class='card'><div style='display:flex;justify-content:space-between;align-items:flex-start'>"
                        f"<div><strong>Prompt #{i+1}</strong> <span style='color:#6b7280'>| id: {res['id']}</span></div>"
                        f"<div>{' '.join([f'<span class=\"chip\">{t}</span>' for t in res.get('tags',[])])}</div>"
                        f"</div></div>", unsafe_allow_html=True)
            cols = st.columns([3, 1])
            with cols[0]:
                ok, reasons = check_dynamic_first(res.get("final_prompt",""))
                if ok:
                    st.markdown("<div class='ok'>✅ 动态检测通过</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='warn'>⚠️ 动态检测未通过</div>", unsafe_allow_html=True)
                    for r in reasons:
                        st.markdown(f"- {r}")
                with st.expander("查看 Final Prompt / AV Plan / Trade-offs", expanded=True):
                    st.markdown("<div class='prompt-area'>", unsafe_allow_html=True)
                    st.code(res.get("final_prompt",""), language="text")
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown("**AV Plan**")
                    st.write(res.get("av_plan","(无)"))
                    st.markdown("**Trade-off（合规/风格说明）**")
                    st.write(res.get("tradeoff","(无)"))
                # copy + download
                render_copy_button(res.get("final_prompt",""), key=f"copy_{i}")
                st.download_button(label="下载 Prompt (.txt)", data=res.get("final_prompt",""), file_name=f"prompt_{res['id']}.txt", mime="text/plain")
            with cols[1]:
                # actions: Regenerate, View versions
                if st.button("Regenerate", key=f"regen_{i}"):
                    st.session_state["regenerate_target"] = i
                    st.experimental_rerun()
                if st.button("Edit & Optimize", key=f"edit_{i}"):
                    # put editable text into session and show below in expander
                    st.session_state["edit_idx"] = i
                if st.button("Show versions", key=f"ver_{i}"):
                    with st.expander(f"版本历史 #{i+1}", expanded=True):
                        for vi, v in enumerate(res.get("versions", [])):
                            st.markdown(f"**v{vi+1}**")
                            st.code(v, language="text")
                            st.download_button(label=f"下载 v{vi+1}", data=v, file_name=f"prompt_{res['id']}_v{vi+1}.txt", mime="text/plain")

    # 编辑并优化（在结果列表下方显示可编辑 panel）
    if st.session_state.get("edit_idx", None) is not None:
        idx = st.session_state["edit_idx"]
        if 0 <= idx < len(st.session_state["results"]):
            st.markdown("---")
            st.markdown(f"### 编辑并优化 Prompt #{idx+1}")
            txt = st.text_area("编辑 Prompt（你可以直接修改文本，然后点击“Optimize & Validate”请求后端优化并保证合规）", value=st.session_state["results"][idx]["final_prompt"], height=300, key=f"editor_{idx}")
            coly1, coly2 = st.columns([1,1])
            with coly1:
                if st.button("Optimize & Validate", key=f"opt_{idx}"):
                    # 这里调用后端验证并优化（假设后端实现 validate_and_optimize）
                    try:
                        resp = requests.post(f"{BACKEND_URL.rstrip('/')}/validate_and_optimize", json={"prompt": txt}, timeout=120)
                        resp.raise_for_status()
                        data = resp.json()
                        new_prompt = data.get("optimized_prompt", txt)
                        st.session_state["results"][idx]["versions"].append(st.session_state["results"][idx]["final_prompt"])
                        st.session_state["results"][idx]["final_prompt"] = new_prompt
                        st.success("优化完成并已替换当前 Prompt（历史版本保留）。")
                        st.session_state["edit_idx"] = None
                    except Exception as e:
                        st.error(f"调用后端优化接口失败: {e}. 已本地保存编辑结果为新版本（不保证合规）。")
                        st.session_state["results"][idx]["versions"].append(st.session_state["results"][idx]["final_prompt"])
                        st.session_state["results"][idx]["final_prompt"] = txt
                        st.session_state["edit_idx"] = None
            with coly2:
                if st.button("Cancel Edit", key=f"cancel_edit_{idx}"):
                    st.session_state["edit_idx"] = None
        st.markdown("---")

# ------ 底部说明 ------
st.markdown(
    """
    ---
    **说明**: 本前端示例强调 UX：素材审计、生成、查看 Prompt、复制、下载与重生（Regenerate）。  
    - 若你已有后端，请确保 BACKEND_URL 指向后端并实现 /generate, /regenerate, /validate_and_optimize 接口。  
    - 若部署到 Streamlit Cloud，请在 Secrets 中配置 BACKEND_URL（或在后端同域部署）。  
    """
)
````
