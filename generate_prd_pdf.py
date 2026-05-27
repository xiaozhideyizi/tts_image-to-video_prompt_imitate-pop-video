#!/usr/bin/env python3
"""Generate PRD PDF for TikTok爆款复刻机 using reportlab."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.flowables import HRFlowable
import os

# Register Chinese fonts
FONT_DIR = r"C:\Windows\Fonts"
pdfmetrics.registerFont(TTFont('MSYH', os.path.join(FONT_DIR, 'msyh.ttc'), subfontIndex=0))
pdfmetrics.registerFont(TTFont('MSYHBD', os.path.join(FONT_DIR, 'msyhbd.ttc'), subfontIndex=0))
pdfmetrics.registerFont(TTFont('SIMHEI', os.path.join(FONT_DIR, 'simhei.ttf')))

# Colors
PURPLE = HexColor('#667eea')
DARK_PURPLE = HexColor('#764ba2')
DARK = HexColor('#1a1a2e')
GRAY = HexColor('#666666')
LIGHT_GRAY = HexColor('#999999')
BG_LIGHT = HexColor('#f0f2ff')
BG_GREEN = HexColor('#e8f5e9')
BG_ORANGE = HexColor('#fff3e0')
BG_RED = HexColor('#fde8e8')
BG_PURPLE = HexColor('#f3e5f5')
BG_BLUE = HexColor('#e3f2fd')
RED = HexColor('#c62828')
ORANGE = HexColor('#e65100')
GREEN = HexColor('#2e7d32')
BLUE = HexColor('#1565c0')
PURPLE_TEXT = HexColor('#7b1fa2')

# Styles
sTitle = ParagraphStyle('Title', fontName='MSYHBD', fontSize=36, textColor=PURPLE, leading=44, alignment=TA_CENTER)
sSub = ParagraphStyle('Sub', fontName='MSYH', fontSize=16, textColor=GRAY, leading=24, alignment=TA_CENTER)
sMetaLabel = ParagraphStyle('MetaLabel', fontName='MSYH', fontSize=9, textColor=LIGHT_GRAY, leading=12)
sMetaValue = ParagraphStyle('MetaValue', fontName='MSYHBD', fontSize=11, textColor=DARK, leading=16)
sH2 = ParagraphStyle('H2', fontName='MSYHBD', fontSize=16, textColor=DARK, leading=24, spaceBefore=24, spaceAfter=10)
sH3 = ParagraphStyle('H3', fontName='MSYHBD', fontSize=13, textColor=HexColor('#333333'), leading=20, spaceBefore=16, spaceAfter=8)
sH4 = ParagraphStyle('H4', fontName='MSYHBD', fontSize=11, textColor=HexColor('#444444'), leading=16, spaceBefore=10, spaceAfter=4)
sBody = ParagraphStyle('Body', fontName='MSYH', fontSize=10, textColor=DARK, leading=16, spaceAfter=4)
sBodyBold = ParagraphStyle('BodyBold', fontName='MSYHBD', fontSize=10, textColor=DARK, leading=16, spaceAfter=4)
sSmall = ParagraphStyle('Small', fontName='MSYH', fontSize=9, textColor=GRAY, leading=14)
sTableHead = ParagraphStyle('TH', fontName='MSYHBD', fontSize=9, textColor=DARK, leading=13)
sTableCell = ParagraphStyle('TD', fontName='MSYH', fontSize=9, textColor=DARK, leading=13)
sCenter = ParagraphStyle('Center', fontName='MSYH', fontSize=9, textColor=GRAY, leading=14, alignment=TA_CENTER)
sHighlight = ParagraphStyle('Highlight', fontName='MSYH', fontSize=9.5, textColor=DARK, leading=15)
sTOC = ParagraphStyle('TOC', fontName='MSYHBD', fontSize=11, textColor=DARK, leading=18, spaceBefore=6, spaceAfter=2)
sTOCSub = ParagraphStyle('TOCSub', fontName='MSYH', fontSize=10, textColor=GRAY, leading=16, leftIndent=20, spaceAfter=1)
sTOCSubSub = ParagraphStyle('TOCSubSub', fontName='MSYH', fontSize=9, textColor=LIGHT_GRAY, leading=14, leftIndent=40, spaceAfter=1)

def tag(text, color, bg):
    return f'<font color="{color}"><b>[{text}]</b></font>'

def P(text, style=sBody):
    return Paragraph(text, style)

def make_table(headers, rows, col_widths=None):
    """Create a styled table."""
    header_cells = [P(h, sTableHead) for h in headers]
    data = [header_cells]
    for row in rows:
        data.append([P(str(c), sTableCell) for c in row])
    w = col_widths or [None] * len(headers)
    t = Table(data, colWidths=w, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BG_LIGHT),
        ('TEXTCOLOR', (0, 0), (-1, 0), DARK),
        ('FONTNAME', (0, 0), (-1, 0), 'MSYHBD'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#fafafa')]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return t

def highlight_box(text, border_color=PURPLE, bg_color=BG_LIGHT):
    """Create a highlight box using a table with colored left border."""
    p = P(text, sHighlight)
    t = Table([[p]], colWidths=[170*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEBEFOREDECOR', (0, 0), (0, -1), 3, border_color),
    ]))
    return t

def hr():
    return HRFlowable(width="100%", thickness=2, color=PURPLE, spaceBefore=6, spaceAfter=8)


def build_pdf():
    output_path = os.path.join(os.path.dirname(__file__), 'PRD.pdf')
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=20*mm, bottomMargin=20*mm
    )
    story = []

    # ==================== 封面 ====================
    story.append(Spacer(1, 60*mm))
    badge_style = ParagraphStyle('Badge', fontName='MSYHBD', fontSize=9, textColor=white, leading=14, alignment=TA_CENTER)
    badge = Paragraph('PRODUCT REQUIREMENTS DOCUMENT', badge_style)
    badge_table = Table([[badge]], colWidths=[80*mm])
    badge_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PURPLE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    story.append(badge_table)
    story.append(Spacer(1, 12*mm))
    story.append(P('TikTok爆款复刻机', sTitle))
    story.append(Spacer(1, 4*mm))
    story.append(P('上传对标视频，AI一键生成同款提示词', sSub))
    story.append(Spacer(1, 20*mm))

    meta_items = [
        ('文档版本', 'V2.0'),
        ('撰写日期', '2026-05-26'),
        ('产品负责人', 'Maggie'),
        ('文档状态', '已上线 / 持续迭代'),
        ('线上地址', 'https://advideo-imitate.netlify.app'),
        ('代码仓库', 'github.com/xiaozhideyizi/tts_image-to-video_prompt_imitate-pop-video'),
    ]
    meta_data = []
    for label, value in meta_items:
        meta_data.append([P(label, sMetaLabel), P(value, sMetaValue)])
    meta_table = Table(meta_data, colWidths=[40*mm, 90*mm])
    meta_table.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(meta_table)
    story.append(PageBreak())

    # ==================== 目录 ====================
    story.append(P('目录', sH2))
    story.append(hr())
    toc_items = [
        (0, '1. 产品概述'),
        (1, '1.1 产品定位与核心场景'),
        (1, '1.2 目标用户画像'),
        (1, '1.3 核心价值主张'),
        (0, '2. 核心功能流程'),
        (1, '2.1 爆款复刻主流程'),
        (1, '2.2 AI 双模式引擎'),
        (1, '2.3 生成输出结构'),
        (0, '3. 系统架构'),
        (1, '3.1 技术架构'),
        (1, '3.2 部署架构'),
        (1, '3.3 数据流'),
        (0, '4. 功能需求 — V1.0（已上线）'),
        (1, '4.1 用户认证模块'),
        (1, '4.2 提示词生成模块'),
        (1, '4.3 历史记录模块'),
        (1, '4.4 分享模块'),
        (0, '5. 功能需求 — V2.0（规划中）'),
        (1, '5.1 视频上传与解析'),
        (1, '5.2 产品图片上传'),
        (1, '5.3 多平台适配'),
        (1, '5.4 积分体系'),
        (1, '5.5 会员体系'),
        (0, '6. 功能需求 — V3.0（远期规划）'),
        (1, '6.1 视频生成模型接入'),
        (1, '6.2 多模型选择'),
        (0, '7. API 接口定义'),
        (0, '8. 数据模型'),
        (0, '9. 非功能需求'),
        (0, '10. 里程碑与版本规划'),
    ]
    for level, text in toc_items:
        if level == 0:
            story.append(P(text, sTOC))
        else:
            story.append(P(text, sTOCSub))
    story.append(PageBreak())

    # ==================== 1. 产品概述 ====================
    story.append(P('1. 产品概述', sH2))
    story.append(hr())

    story.append(P('1.1 产品定位与核心场景', sH3))
    story.append(P('<b>TikTok爆款复刻机</b>是一款面向短视频创作者和电商运营的 AI 提示词生成工具。核心能力是<b>复刻爆款视频</b>——用户上传一条对标爆款视频和自己的产品图片，系统通过 AI 大模型分析视频内容与产品特征，自动生成适配用户产品的视频提示词（Prompt），帮助用户快速产出同款风格的带货/种草短视频。'))
    story.append(Spacer(1, 4*mm))
    story.append(highlight_box(
        '<b>核心公式</b>：对标爆款视频 + 用户产品图片 → AI 分析 → 适配用户产品的爆款提示词'
    ))
    story.append(Spacer(1, 4*mm))
    story.append(P('核心场景：', sBodyBold))
    story.append(make_table(
        ['场景', '用户行为', '系统输出'],
        [
            ['爆款复刻', '上传对标视频 + 产品图片', '生成适配产品的同款风格视频提示词'],
            ['快速起量', '输入产品名称和卖点', 'AI 生成多组结构化提示词'],
            ['多平台分发', '选择目标平台', '生成符合平台调性的差异化提示词'],
            ['团队协作', '分享提示词链接', '团队成员查看和复用'],
        ]
    ))

    story.append(P('1.2 目标用户画像', sH3))
    story.append(make_table(
        ['用户画像', '典型场景', '核心痛点', '期望价值'],
        [
            ['电商运营', '拼多多/京东/淘系店铺做带货视频', '不会写提示词，视频效果差', '一键复刻爆款，降低制作门槛'],
            ['短视频博主', '抖音/小红书种草视频', '创作灵感枯竭，产出效率低', '快速产出多组高质量创意'],
            ['MCN 机构', '为多品牌批量生产内容', '人力成本高，风格难统一', '批量生成 + 团队共享'],
            ['品牌方', '视频号/B站品牌宣传', '外包贵，自研难', '低成本自研内容生产工具'],
        ],
        col_widths=[22*mm, 42*mm, 42*mm, 42*mm]
    ))

    story.append(P('1.3 核心价值主张', sH3))
    story.append(highlight_box(
        '<b>爆款复刻</b>：不再从零创作——找到对标视频，上传产品图片，AI 自动分析并输出适配你产品的提示词，让"爆款可复制"。<br/>'
        '<b>双引擎保障</b>：AI 模式优先生成高质量创意，AI 不可用时自动降级到本地规则引擎，100% 可用。<br/>'
        '<b>多平台覆盖</b>：一套产品信息，适配国内电商 + 社媒 + 海外平台，省去逐平台调整成本。',
        border_color=GREEN, bg_color=BG_GREEN
    ))

    # ==================== 2. 核心功能流程 ====================
    story.append(PageBreak())
    story.append(P('2. 核心功能流程', sH2))
    story.append(hr())

    story.append(P('2.1 爆款复刻主流程', sH3))
    # Flow diagram using table
    flow_cells = [
        P('<b>上传对标视频</b>', ParagraphStyle('fc', fontName='MSYHBD', fontSize=9, textColor=GREEN, alignment=TA_CENTER)),
        P('<b>+</b>', ParagraphStyle('fp', fontName='MSYHBD', fontSize=12, textColor=GRAY, alignment=TA_CENTER)),
        P('<b>上传产品图片</b>', ParagraphStyle('fc2', fontName='MSYHBD', fontSize=9, textColor=GREEN, alignment=TA_CENTER)),
        P('<b>→</b>', ParagraphStyle('fa', fontName='MSYHBD', fontSize=12, textColor=GRAY, alignment=TA_CENTER)),
        P('<b>AI 分析引擎</b>', ParagraphStyle('fm', fontName='MSYHBD', fontSize=9, textColor=white, alignment=TA_CENTER)),
        P('<b>→</b>', ParagraphStyle('fa2', fontName='MSYHBD', fontSize=12, textColor=GRAY, alignment=TA_CENTER)),
        P('<b>适配产品提示词</b>', ParagraphStyle('fo', fontName='MSYHBD', fontSize=9, textColor=ORANGE, alignment=TA_CENTER)),
    ]
    flow_table = Table([flow_cells], colWidths=[28*mm, 10*mm, 28*mm, 10*mm, 28*mm, 10*mm, 32*mm])
    flow_table.setStyle(TableStyle([
        ('BACKGROUND', (4, 0), (4, 0), PURPLE),
        ('BACKGROUND', (0, 0), (0, 0), BG_GREEN),
        ('BACKGROUND', (2, 0), (2, 0), BG_GREEN),
        ('BACKGROUND', (6, 0), (6, 0), BG_ORANGE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (0, 0), 1, GREEN),
        ('BOX', (2, 0), (2, 0), 1, GREEN),
        ('BOX', (4, 0), (4, 0), 1, PURPLE),
        ('BOX', (6, 0), (6, 0), 1, ORANGE),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    story.append(flow_table)
    story.append(Spacer(1, 4*mm))

    steps = [
        ('Step 1 — 视频解析', 'AI 提取对标视频的关键帧、视觉风格、运镜节奏、文案结构、BGM 风格'),
        ('Step 2 — 产品适配', '结合产品图片特征（外观、场景、卖点），将爆款元素映射到用户产品'),
        ('Step 3 — 提示词生成', '输出结构化视频提示词，包含画面描述、运镜指令、节奏安排、音效方案'),
    ]
    for title, desc in steps:
        story.append(P(f'<b>{title}</b>：{desc}', sSmall))
    story.append(Spacer(1, 4*mm))

    story.append(P('2.2 AI 双模式引擎', sH3))
    story.append(make_table(
        ['模式', '触发条件', '能力', '响应时间'],
        [
            ['AI 模式（主）', 'API Key 可用 + 用户开启 AI', '深度理解视频内容，创意性强，支持多语言', '3-10s'],
            ['本地规则（备）', 'AI 不可用或用户关闭 AI', '基于动态起手库 + 随机组合，保证基础可用', '<1s'],
        ],
        col_widths=[25*mm, 40*mm, 60*mm, 20*mm]
    ))

    story.append(P('2.3 生成输出结构', sH3))
    story.append(P('每条提示词包含以下结构化字段：'))
    story.append(make_table(
        ['字段', '类型', '说明'],
        [
            ['finalPrompt', 'Text', '完整提示词文本，可直接输入视频生成模型'],
            ['dynamicStrategy', 'Text', '去静止策略：镜头运动 + 物理特效 + 动作指令'],
            ['audioPlan', 'Text', '视听方案：口播配音方向 + BGM 风格'],
            ['audit', 'Text', '素材审计：图片/视频可用性检查与建议'],
            ['sections', 'JSON', '分时段内容：0-4s 动态起手 / 4-8s 产品展示 / 8-12s 转化结尾'],
        ]
    ))

    # ==================== 3. 系统架构 ====================
    story.append(PageBreak())
    story.append(P('3. 系统架构', sH2))
    story.append(hr())

    story.append(P('3.1 技术架构', sH3))
    arch_data = [
        [P('<b>Frontend</b><br/>React 18 + Vite<br/>SPA 单页应用 · React Router<br/>Axios HTTP · Context 状态<br/>响应式适配 · Netlify CDN', sSmall)],
        [P('<b>Backend</b><br/>Python FastAPI<br/>异步 API · SQLAlchemy async<br/>JWT 鉴权 · 智谱 GLM-4-flash<br/>本地规则降级 · 视频解析(规划)', sSmall)],
        [P('<b>Database</b><br/>PostgreSQL<br/>asyncpg 异步驱动<br/>SQLite 开发环境 · Railway PG<br/>对象存储(规划: S3/R2)', sSmall)],
    ]
    arch_table = Table([arch_data], colWidths=[56*mm, 56*mm, 56*mm])
    arch_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), BG_LIGHT),
        ('BACKGROUND', (1, 0), (1, 0), BG_LIGHT),
        ('BACKGROUND', (2, 0), (2, 0), BG_LIGHT),
        ('BOX', (0, 0), (0, 0), 1, PURPLE),
        ('BOX', (1, 0), (1, 0), 1, PURPLE),
        ('BOX', (2, 0), (2, 0), 1, PURPLE),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(arch_table)

    story.append(P('3.2 部署架构', sH3))
    story.append(make_table(
        ['服务', '平台', '域名/地址', '说明'],
        [
            ['前端', 'Netlify', 'advideo-imitate.netlify.app', '自动构建 + CDN + HTTPS'],
            ['后端 API', 'Railway', 'incredible-alignment-production-4ba5.up.railway.app', 'Nixpacks 构建 + 容器运行'],
            ['PostgreSQL', 'Railway', '内部网络', '托管数据库，自动备份'],
            ['代码仓库', 'GitHub', 'xiaozhideyizi/tts_image-to-video...', 'Push 自动触发部署'],
        ],
        col_widths=[20*mm, 18*mm, 55*mm, 45*mm]
    ))

    story.append(P('3.3 数据流', sH3))
    flow2_cells = [
        P('<b>用户输入</b>', ParagraphStyle('f1', fontName='MSYHBD', fontSize=8, textColor=GREEN, alignment=TA_CENTER)),
        P('→', ParagraphStyle('a1', fontName='MSYHBD', fontSize=10, textColor=GRAY, alignment=TA_CENTER)),
        P('<b>JWT 鉴权</b>', ParagraphStyle('f2', fontName='MSYHBD', fontSize=8, textColor=DARK, alignment=TA_CENTER)),
        P('→', ParagraphStyle('a2', fontName='MSYHBD', fontSize=10, textColor=GRAY, alignment=TA_CENTER)),
        P('<b>AI/本地双引擎</b>', ParagraphStyle('f3', fontName='MSYHBD', fontSize=8, textColor=white, alignment=TA_CENTER)),
        P('→', ParagraphStyle('a3', fontName='MSYHBD', fontSize=10, textColor=GRAY, alignment=TA_CENTER)),
        P('<b>PostgreSQL</b>', ParagraphStyle('f4', fontName='MSYHBD', fontSize=8, textColor=DARK, alignment=TA_CENTER)),
        P('→', ParagraphStyle('a4', fontName='MSYHBD', fontSize=10, textColor=GRAY, alignment=TA_CENTER)),
        P('<b>结构化提示词</b>', ParagraphStyle('f5', fontName='MSYHBD', fontSize=8, textColor=ORANGE, alignment=TA_CENTER)),
    ]
    flow2_table = Table([flow2_cells], colWidths=[22*mm, 8*mm, 20*mm, 8*mm, 28*mm, 8*mm, 22*mm, 8*mm, 26*mm])
    flow2_table.setStyle(TableStyle([
        ('BACKGROUND', (4, 0), (4, 0), PURPLE),
        ('BACKGROUND', (0, 0), (0, 0), BG_GREEN),
        ('BACKGROUND', (6, 0), (6, 0), BG_LIGHT),
        ('BACKGROUND', (8, 0), (8, 0), BG_ORANGE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('BOX', (0, 0), (0, 0), 0.5, GREEN),
        ('BOX', (4, 0), (4, 0), 0.5, PURPLE),
        ('BOX', (8, 0), (8, 0), 0.5, ORANGE),
    ]))
    story.append(flow2_table)
    story.append(P('AI 优先 → 失败降级本地规则 → 结果云存储 → 支持公开分享', sCenter))

    # ==================== 4. V1.0 功能需求 ====================
    story.append(PageBreak())
    story.append(P('4. 功能需求 — V1.0（已上线）', sH2))
    story.append(hr())

    story.append(P('4.1 用户认证模块', sH3))
    story.append(make_table(
        ['功能', '优先级', '状态', '描述'],
        [
            ['邮箱注册', tag('P0', RED, BG_RED), tag('已完成', GREEN, BG_GREEN), '邮箱+用户名+密码注册，bcrypt 加密存储'],
            ['邮箱登录', tag('P0', RED, BG_RED), tag('已完成', GREEN, BG_GREEN), 'OAuth2 Password Flow，JWT Token 7天有效期'],
            ['Token 鉴权', tag('P0', RED, BG_RED), tag('已完成', GREEN, BG_GREEN), '所有写操作 Bearer Token，自动 401 拦截'],
            ['用户信息', tag('P1', ORANGE, BG_ORANGE), tag('已完成', GREEN, BG_GREEN), 'GET /api/auth/me 获取当前用户信息'],
        ],
        col_widths=[22*mm, 16*mm, 18*mm, 90*mm]
    ))

    story.append(P('4.2 提示词生成模块', sH3))
    story.append(make_table(
        ['功能', '优先级', '状态', '描述'],
        [
            ['AI 智能生成', tag('P0', RED, BG_RED), tag('已完成', GREEN, BG_GREEN), '调用智谱 GLM-4-flash，按时间段生成结构化提示词'],
            ['本地规则生成', tag('P0', RED, BG_RED), tag('已完成', GREEN, BG_GREEN), 'AI 不可用时降级，动态起手库随机组合'],
            ['参数配置', tag('P0', RED, BG_RED), tag('已完成', GREEN, BG_GREEN), '商品名称、目标市场(7国)、语言(5种)、卖点、口播、BGM'],
            ['批量生成', tag('P1', ORANGE, BG_ORANGE), tag('已完成', GREEN, BG_GREEN), '1-5 条批量生成，滑块控制数量'],
            ['一键复制', tag('P1', ORANGE, BG_ORANGE), tag('已完成', GREEN, BG_GREEN), '复制最终提示词到剪贴板'],
        ],
        col_widths=[22*mm, 16*mm, 18*mm, 90*mm]
    ))

    story.append(P('4.3 历史记录模块', sH3))
    story.append(make_table(
        ['功能', '优先级', '状态', '描述'],
        [
            ['历史列表', tag('P0', RED, BG_RED), tag('已完成', GREEN, BG_GREEN), '分页查询，时间倒序，仅展示当前用户数据'],
            ['详情展开', tag('P1', ORANGE, BG_ORANGE), tag('已完成', GREEN, BG_GREEN), '展开查看完整提示词内容'],
            ['删除记录', tag('P1', ORANGE, BG_ORANGE), tag('已完成', GREEN, BG_GREEN), '仅可删除自己的记录'],
        ],
        col_widths=[22*mm, 16*mm, 18*mm, 90*mm]
    ))

    story.append(P('4.4 分享模块', sH3))
    story.append(make_table(
        ['功能', '优先级', '状态', '描述'],
        [
            ['生成分享链接', tag('P1', ORANGE, BG_ORANGE), tag('已完成', GREEN, BG_GREEN), '生成唯一 token URL，无需登录可查看'],
            ['分享页展示', tag('P1', ORANGE, BG_ORANGE), tag('已完成', GREEN, BG_GREEN), '公开页面展示提示词内容'],
        ],
        col_widths=[22*mm, 16*mm, 18*mm, 90*mm]
    ))

    # ==================== 5. V2.0 功能需求 ====================
    story.append(PageBreak())
    story.append(P('5. 功能需求 — V2.0（规划中）', sH2))
    story.append(hr())
    story.append(highlight_box(
        '<b>V2.0 核心升级方向</b>：从"文字输入生成提示词"升级为"视频+图片输入 → AI 爆款复刻"，加入多平台适配、积分体系和会员体系，构建商业化闭环。',
        border_color=ORANGE, bg_color=BG_ORANGE
    ))
    story.append(Spacer(1, 4*mm))

    story.append(P('5.1 视频上传与解析', sH3))
    story.append(make_table(
        ['功能', '优先级', '描述'],
        [
            ['对标视频上传', tag('P0', RED, BG_RED), '支持 MP4/MOV/AVI 格式，最大 200MB，拖拽上传'],
            ['关键帧提取', tag('P0', RED, BG_RED), '自动提取视频关键帧（5-10帧），用于 AI 分析画面风格'],
            ['视频内容分析', tag('P0', RED, BG_RED), 'AI 识别运镜方式、节奏、色调、文案结构、BGM 风格'],
            ['视频预览', tag('P1', ORANGE, BG_ORANGE), '上传后可在线预览，标注关键帧位置'],
        ],
        col_widths=[24*mm, 16*mm, 106*mm]
    ))

    story.append(P('5.2 产品图片上传', sH3))
    story.append(make_table(
        ['功能', '优先级', '描述'],
        [
            ['产品图片上传', tag('P0', RED, BG_RED), '支持 JPG/PNG/WebP，最多 5 张，单张最大 10MB'],
            ['产品特征识别', tag('P0', RED, BG_RED), 'AI 识别产品外观、颜色、使用场景，用于提示词适配'],
            ['图片裁剪标注', tag('P2', BLUE, BG_BLUE), '用户可标注产品主体区域，提高识别精度'],
        ],
        col_widths=[24*mm, 16*mm, 106*mm]
    ))

    story.append(P('5.3 多平台适配', sH3))
    story.append(P('生成提示词时，用户选择目标平台，系统自动适配该平台的内容调性、时长规范和风格偏好：'))
    story.append(Spacer(1, 2*mm))

    # Platform tags
    ecom = P('<b>国内电商平台</b>：拼多多 · 京东 · 淘系（淘宝/天猫）· 抖音电商', sSmall)
    social = P('<b>国内社媒平台</b>：小红书 · 抖音 · 视频号 · B站', sSmall)
    oversea = P('<b>海外平台</b>：TikTok · Instagram Reels · YouTube Shorts', sSmall)
    platform_table = Table([[ecom], [social], [oversea]], colWidths=[146*mm])
    platform_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), BG_ORANGE),
        ('BACKGROUND', (0, 1), (0, 1), HexColor('#fce4ec')),
        ('BACKGROUND', (0, 2), (0, 2), BG_BLUE),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(platform_table)
    story.append(Spacer(1, 3*mm))

    story.append(make_table(
        ['平台', '适配要点', '典型时长', '内容调性'],
        [
            ['拼多多', '价格敏感、促销话术、工厂/仓库场景', '15-30s', '接地气、实惠感'],
            ['京东', '品质背书、参数对比、品牌调性', '15-45s', '专业、可信赖'],
            ['淘系', '种草风格、场景化展示、测评对比', '30-60s', '精致、种草感'],
            ['抖音电商', '强节奏、爆款BGM、前3秒钩子', '15-60s', '快节奏、情绪驱动'],
            ['小红书', '生活化场景、图文视频化、真实感', '15-60s', '精致、生活化、真实'],
            ['视频号', '社交传播、情感共鸣、朋友圈适配', '15-60s', '温情、社交化'],
            ['B站', '硬核测评、梗文化、UP主风格', '60-300s', '专业、有趣、深度'],
            ['TikTok', 'Hook 3秒、挑战赛风格、全球调性', '15-60s', '潮流、病毒式传播'],
        ],
        col_widths=[20*mm, 52*mm, 20*mm, 30*mm]
    ))

    story.append(P('5.4 积分体系', sH3))
    story.append(make_table(
        ['功能', '优先级', '描述'],
        [
            ['积分账户', tag('P1', ORANGE, BG_ORANGE), '每位用户拥有积分账户，注册赠送初始积分'],
            ['积分消耗', tag('P1', ORANGE, BG_ORANGE), 'AI 生成消耗积分（本地规则免费），视频解析额外消耗'],
            ['积分获取', tag('P1', ORANGE, BG_ORANGE), '每日签到、分享赚积分、邀请好友、购买充值'],
            ['积分明细', tag('P2', BLUE, BG_BLUE), '查看积分收支记录，含类型、时间、余额变动'],
        ],
        col_widths=[24*mm, 16*mm, 106*mm]
    ))
    story.append(Spacer(1, 2*mm))
    story.append(highlight_box(
        '<b>积分定价参考</b>：<br/>'
        '· 本地规则生成：免费<br/>'
        '· AI 生成提示词：1 积分/条<br/>'
        '· 视频解析 + AI 生成：5 积分/次<br/>'
        '· 新用户注册赠送：20 积分<br/>'
        '· 每日签到：1-3 积分（连续签到递增）<br/>'
        '· 充值：¥0.1/积分（暂定）'
    ))

    story.append(P('5.5 会员体系', sH3))
    story.append(make_table(
        ['等级', '月费', '权益'],
        [
            ['免费版', '¥0', '本地规则无限次 + AI 生成 5 次/天 + 视频解析 1 次/天'],
            ['专业版', '¥29/月', 'AI 生成无限次 + 视频解析 20 次/天 + 多平台适配 + 历史导出'],
            ['团队版', '¥99/月', '专业版全部权益 + 5 人协作 + 共享工作区 + API 接口 + 优先客服'],
        ],
        col_widths=[20*mm, 20*mm, 106*mm]
    ))

    # ==================== 6. V3.0 功能需求 ====================
    story.append(PageBreak())
    story.append(P('6. 功能需求 — V3.0（远期规划）', sH2))
    story.append(hr())
    story.append(highlight_box(
        '<b>V3.0 核心升级方向</b>：从"生成提示词"升级为"生成视频"——直接接入视频生成大模型，实现从爆款视频到同款视频的全链路闭环。',
        border_color=ORANGE, bg_color=BG_ORANGE
    ))
    story.append(Spacer(1, 4*mm))

    story.append(P('6.1 视频生成模型接入', sH3))
    story.append(P('接入以下视频生成模型，用户可直接在平台内完成"对标视频 → 产品视频"的全流程：'))
    story.append(Spacer(1, 2*mm))
    video_models = P('<b>视频生成模型</b>：Kling (快手可灵) · Seedance 2.0 (字节) · Google Veo/Omni · Runway Gen-3', sSmall)
    vm_table = Table([[video_models]], colWidths=[146*mm])
    vm_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), BG_PURPLE),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(vm_table)
    story.append(Spacer(1, 3*mm))

    story.append(make_table(
        ['模型', '能力', '适用场景', '接入难度'],
        [
            ['Kling (快手可灵)', '国产领先视频生成，中文理解好', '国内电商/社媒视频', '中（API 待公测）'],
            ['Seedance 2.0 (字节)', '抖音生态深度适配，短视频优化', '抖音/西瓜带货视频', '中（内部 API）'],
            ['Google Veo/Omni', '多模态理解，全球调性', 'TikTok/海外平台视频', '高（需翻墙+海外账号）'],
            ['Runway Gen-3', '高质量视频生成，风格迁移', '高品质品牌视频', '低（API 已开放）'],
        ],
        col_widths=[30*mm, 38*mm, 35*mm, 30*mm]
    ))

    story.append(P('6.2 多模型选择', sH3))
    story.append(make_table(
        ['功能', '优先级', '描述'],
        [
            ['模型选择器', tag('P1', ORANGE, BG_ORANGE), '用户在生成时可选择目标视频模型，提示词自动适配模型格式'],
            ['模型对比', tag('P2', BLUE, BG_BLUE), '同一条提示词在多个模型下的效果预览对比'],
            ['提示词格式适配', tag('P0', RED, BG_RED), '不同模型提示词格式不同（Kling vs Runway），系统自动转换'],
            ['一键生成视频', tag('P1', ORANGE, BG_ORANGE), '提示词生成后可直接调用视频模型，产出成品视频'],
        ],
        col_widths=[24*mm, 16*mm, 106*mm]
    ))

    # ==================== 7. API 接口定义 ====================
    story.append(PageBreak())
    story.append(P('7. API 接口定义', sH2))
    story.append(hr())

    story.append(P('7.1 认证接口', sH3))
    story.append(make_table(
        ['方法', '路径', '说明', '鉴权'],
        [
            ['POST', '/api/auth/register', '用户注册，返回 JWT Token', '否'],
            ['POST', '/api/auth/token', '用户登录（OAuth2 表单）', '否'],
            ['GET', '/api/auth/me', '获取当前用户信息', '是'],
        ],
        col_widths=[16*mm, 42*mm, 52*mm, 16*mm]
    ))

    story.append(P('7.2 提示词接口', sH3))
    story.append(make_table(
        ['方法', '路径', '说明', '鉴权'],
        [
            ['POST', '/api/prompts/generate', '生成提示词（AI/本地双模式）', '是'],
            ['GET', '/api/prompts/history', '查询历史记录（分页）', '是'],
            ['POST', '/api/prompts/history/{id}/share', '生成分享链接', '是'],
            ['GET', '/api/prompts/share/{token}', '查看分享内容', '否'],
            ['DELETE', '/api/prompts/history/{id}', '删除历史记录', '是'],
        ],
        col_widths=[16*mm, 52*mm, 42*mm, 16*mm]
    ))

    story.append(P('7.3 V2.0 新增接口（规划）', sH3))
    story.append(make_table(
        ['方法', '路径', '说明', '鉴权'],
        [
            ['POST', '/api/upload/video', '上传对标视频，返回关键帧和分析结果', '是'],
            ['POST', '/api/upload/images', '上传产品图片，返回特征描述', '是'],
            ['POST', '/api/prompts/replicate', '爆款复刻：视频+图片 → 适配提示词', '是'],
            ['GET', '/api/credits/balance', '查询积分余额', '是'],
            ['POST', '/api/credits/consume', '积分消耗记录', '是'],
            ['GET', '/api/subscription/status', '查询会员状态', '是'],
        ],
        col_widths=[16*mm, 46*mm, 48*mm, 16*mm]
    ))

    story.append(P('7.4 系统接口', sH3))
    story.append(make_table(
        ['方法', '路径', '说明', '鉴权'],
        [
            ['GET', '/health', '健康检查', '否'],
            ['GET', '/', 'API 信息', '否'],
            ['GET', '/docs', 'Swagger 文档', '否'],
        ],
        col_widths=[16*mm, 42*mm, 52*mm, 16*mm]
    ))

    # ==================== 8. 数据模型 ====================
    story.append(PageBreak())
    story.append(P('8. 数据模型', sH2))
    story.append(hr())

    story.append(P('8.1 User 用户表', sH3))
    story.append(make_table(
        ['字段', '类型', '约束', '说明'],
        [
            ['id', 'Integer', 'PK, Auto', '用户 ID'],
            ['email', 'String(255)', 'Unique, Not Null', '登录邮箱'],
            ['username', 'String(100)', 'Not Null', '用户昵称'],
            ['hashed_password', 'String(255)', 'Not Null', 'bcrypt 加密密码'],
            ['is_active', 'Boolean', 'Default True', '账号状态'],
            ['credits', 'Integer', 'Default 20', '积分余额（V2.0）'],
            ['membership', 'String(20)', 'Default "free"', '会员等级：free/pro/team（V2.0）'],
            ['created_at', 'DateTime', 'Auto', '注册时间'],
        ],
        col_widths=[28*mm, 26*mm, 36*mm, 56*mm]
    ))

    story.append(P('8.2 PromptHistory 提示词历史表', sH3))
    story.append(make_table(
        ['字段', '类型', '约束', '说明'],
        [
            ['id', 'Integer', 'PK, Auto', '记录 ID'],
            ['user_id', 'Integer', 'FK → User.id', '所属用户'],
            ['product_name', 'String(255)', 'Not Null', '商品名称'],
            ['target_market', 'String(50)', 'Default "china"', '目标市场'],
            ['target_language', 'String(50)', 'Default "chinese"', '目标语言'],
            ['target_platform', 'String(50)', 'Default "tiktok"', '目标平台（V2.0 新增）'],
            ['selling_points', 'Text', '', '核心卖点'],
            ['video_script', 'Text', '', '口播文案'],
            ['bgm_style', 'String(255)', '', 'BGM 风格'],
            ['prompts_json', 'Text', 'Not Null', '生成结果 JSON'],
            ['video_url', 'String(500)', 'Nullable', '对标视频存储地址（V2.0）'],
            ['image_urls', 'Text', 'Nullable', '产品图片 JSON 数组（V2.0）'],
            ['credits_cost', 'Integer', 'Default 0', '消耗积分数（V2.0）'],
            ['share_token', 'String(64)', 'Unique, Nullable', '分享 token'],
            ['created_at', 'DateTime', 'Auto', '生成时间'],
        ],
        col_widths=[26*mm, 24*mm, 36*mm, 60*mm]
    ))

    story.append(P('8.3 CreditLog 积分流水表（V2.0 新增）', sH3))
    story.append(make_table(
        ['字段', '类型', '约束', '说明'],
        [
            ['id', 'Integer', 'PK, Auto', '流水 ID'],
            ['user_id', 'Integer', 'FK → User.id', '所属用户'],
            ['type', 'String(20)', 'Not Null', '类型：consume/earn/recharge/gift'],
            ['amount', 'Integer', 'Not Null', '变动数量（正=收入，负=支出）'],
            ['balance_after', 'Integer', 'Not Null', '变动后余额'],
            ['description', 'String(255)', '', '描述（如"AI生成提示词 x3"）'],
            ['created_at', 'DateTime', 'Auto', '记录时间'],
        ],
        col_widths=[26*mm, 24*mm, 36*mm, 60*mm]
    ))

    # ==================== 9. 非功能需求 ====================
    story.append(P('9. 非功能需求', sH2))
    story.append(hr())
    story.append(make_table(
        ['维度', '要求', '当前方案'],
        [
            ['可用性', '99.9% 服务可用', 'AI/本地双模式降级保证'],
            ['性能', 'API < 2s（本地）/ < 10s（AI）/ < 30s（视频解析）', 'FastAPI 异步 + asyncpg'],
            ['安全', '密码不可逆，Token 7 天有效期', 'bcrypt + JWT (HS256)'],
            ['数据隔离', '用户只能访问自己的数据', 'API 层 user_id 过滤'],
            ['CORS', '仅允许指定前端域名', '白名单机制'],
            ['HTTPS', '全链路加密传输', 'Netlify/Railway 自动 HTTPS'],
            ['文件存储', '视频/图片安全存储，CDN 加速', '规划 S3/R2 对象存储'],
            ['移动端', '响应式布局，手机可用', 'CSS 响应式适配'],
            ['支付', '积分充值、会员订阅', '规划接入微信/支付宝'],
        ],
        col_widths=[22*mm, 60*mm, 60*mm]
    ))

    # ==================== 10. 里程碑与版本规划 ====================
    story.append(PageBreak())
    story.append(P('10. 里程碑与版本规划', sH2))
    story.append(hr())

    # Milestone cards
    ms1_content = P(
        '<b>V1.0 — 基础版 · 已上线</b><br/>'
        '· 邮箱注册/登录 + JWT 鉴权<br/>'
        '· AI（智谱 GLM）+ 本地规则双引擎<br/>'
        '· 提示词生成（文字输入模式）<br/>'
        '· 历史记录云存储 + 分享链接',
        sSmall
    )
    ms2_content = P(
        '<b>V2.0 — 爆款复刻版 · 规划中</b><br/>'
        '· 对标视频上传 + 关键帧提取<br/>'
        '· 产品图片上传 + AI 特征识别<br/>'
        '· 多平台适配（电商+社媒+海外）<br/>'
        '· 积分体系 + 会员体系<br/>'
        '· 爆款复刻主流程',
        sSmall
    )
    ms3_content = P(
        '<b>V3.0 — 视频生成版 · 远期规划</b><br/>'
        '· 接入 Kling / Seedance 2.0<br/>'
        '· 接入 Google Veo/Omni<br/>'
        '· 提示词 → 视频一键生成<br/>'
        '· 多模型对比选择<br/>'
        '· 团队协作 + API 开放',
        sSmall
    )

    ms_table = Table(
        [[ms1_content, ms2_content, ms3_content]],
        colWidths=[50*mm, 50*mm, 50*mm]
    )
    ms_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), BG_GREEN),
        ('BACKGROUND', (1, 0), (1, 0), BG_ORANGE),
        ('BACKGROUND', (2, 0), (2, 0), HexColor('#fce4ec')),
        ('BOX', (0, 0), (0, 0), 1, GREEN),
        ('BOX', (1, 0), (1, 0), 1, ORANGE),
        ('BOX', (2, 0), (2, 0), 1, RED),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(ms_table)
    story.append(Spacer(1, 6*mm))

    story.append(P('版本时间线', sH3))
    story.append(make_table(
        ['版本', '目标时间', '核心交付', '商业化'],
        [
            ['V1.0', '2026 Q2 ✅', '文字输入 → 提示词生成', '免费'],
            ['V2.0', '2026 Q3', '视频+图片 → 爆款复刻 + 多平台', '积分 + 会员'],
            ['V2.5', '2026 Q4', '团队协作 + 数据分析 + 模板市场', '团队版订阅'],
            ['V3.0', '2027 Q1', '接入视频生成模型，全链路闭环', '按次/按时长付费'],
        ],
        col_widths=[16*mm, 24*mm, 56*mm, 40*mm]
    ))

    # Footer
    story.append(Spacer(1, 20*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor('#eeeeee')))
    story.append(P('TikTok爆款复刻机 PRD V2.0 · 2026-05-26 · Confidential · Maggie', sCenter))

    # Build PDF
    doc.build(story)
    print(f'PDF generated: {output_path}')
    return output_path

if __name__ == '__main__':
    build_pdf()
