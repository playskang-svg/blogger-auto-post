#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blogger Multi-Blog Auto Publisher with Gemini AI & Irregular Scheduler
"""

import os
import sys
import json
import random
import argparse
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import google.generativeai as genai

# 1. 다중 블로그 설정
BLOGS_CONFIG = {
    "atttrip": {
        "id": "3287113241520886880",
        "name": "아토트립 (반려견 동반 여행정보)",
        "default_labels": ["반려견 숙소", "반려견 여행", "애견동반 펜션", "아토트립"],
        "persona": (
            "당신은 대한민국 1등 반려견 동반 여행 전문 에디터 '아토 아빠'입니다. "
            "친절하고 신뢰감 넘치는 따뜻한 어조로 작성합니다. "
            "견주들이 가장 궁금해하는 [안전 펜스(울타리) 높이], [체중/견종 제한], [전용 어메니티 및 오프리시 잔디마당], "
            "[실내 미끄럼 방지 매트] 정보를 반드시 구체적인 수치와 함께 상세히 분석해야 합니다."
        )
    },
    "suriwiki": {
        "id": "5571572496232571585",
        "name": "수리위키 / 꿀팁뉴스",
        "default_labels": ["생활 수리", "생활 꿀팁", "비용 절약", "가전 점검"],
        "persona": (
            "당신은 실생활 기술 수리 및 살림 비용 절약 꿀팁을 전하는 20년 경력의 '수리 마스터'입니다. "
            "[자가 점검 체크리스트], [필요 공구], [업체 호출 비용 vs 셀프 수리 비용 비교], "
            "[주의해야 할 안전 수칙]을 단계별(Step-by-Step)로 깔끔하게 정리해야 합니다."
        )
    },
    "vpn_adbles": {
        "id": "5571572496232571585",
        "name": "VPN-Adbles",
        "default_labels": ["VPN 추천", "네트워크 보안", "할인 프로모션", "해외 스트리밍"],
        "persona": (
            "당신은 글로벌 IT 인프라 및 사이버 보안 전문가입니다. "
            "[암호화 프로토콜 성능], [국가별 서버 속도(Ping/Mbps)], [OTT 스트리밍 언락 호환성], "
            "[최대 할인 프로모션 혜택 적용법]을 전문적이면서도 쉽게 설명해야 합니다."
        )
    }
}

SCOPES = ["https://www.googleapis.com/auth/blogger"]

def get_credentials():
    token_json_str = os.environ.get("BLOGGER_TOKEN_JSON")
    if not token_json_str:
        print("[ERROR] BLOGGER_TOKEN_JSON 환경변수가 없습니다.", file=sys.stderr)
        sys.exit(1)
    token_info = json.loads(token_json_str)
    return Credentials.from_authorized_user_info(token_info, SCOPES)

def calculate_natural_schedule_time(base_hours=4.0, apply_jitter=True):
    now_kst = datetime.utcnow() + timedelta(hours=9)
    jitter_minutes = random.randint(-20, 25) if apply_jitter else 0
    target_kst = (now_kst + timedelta(hours=base_hours, minutes=jitter_minutes)).replace(second=0, microsecond=0)
    
    rfc3339_str = target_kst.strftime("%Y-%m-%dT%H:%M:00+09:00")
    readable_str = target_kst.strftime("%Y년 %m월 %d일 %p %I시 %M분")
    return rfc3339_str, readable_str, jitter_minutes

def generate_post_content(blog_cfg, user_topic):
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        return f"<h2>{user_topic} 핵심 총정리</h2><p>본 포스팅은 {blog_cfg['name']} 공식 가이드입니다.</p>"

    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-3.6-flash")

    prompt = f"""
    당신은 블로그 글 작성 최고 전문가입니다.
    아래 [블로그 페르소나]와 [작성 지침]에 맞춰 네이버/구글 검색 상위 노출에 최적화된 고품질 블로그 글(HTML 본문)을 작성하세요.

    [대상 블로그]: {blog_cfg['name']}
    [블로그 페르소나]: {blog_cfg['persona']}
    [요청 주제]: {user_topic}

    [HTML 필수 규칙]:
    1. <html>, <body> 없이 <h2>, <h3>, <p>, <ul>, <li>, <strong>, <div> 본문 조각만 출력할 것.
    2. 수동 목차 박스는 절대 넣지 말 것 (스킨이 자동 목차 생성).
    3. 최소 4개 이상의 <h2> 섹션으로 심층 비교 및 핵심 정보 제공.
    4. 본문 중간에 고화질 관련 Unsplash 사진 태그 1~2개 포함 (alt 태그에 검색 키워드 완벽 반영).
    5. 마지막에 독자를 위한 요약 체크리스트(<ul>) 및 격려 맺음말 포함.

    [문체 규칙 - 키워드/수치/조건 중심으로 간결하게]:
    - "~라고 할 수 있습니다", "정말 좋은" 같은 상투적이고 장식적인 문구는 쓰지 말고, 구체적인 수치·기준·조건·절차 중심으로 간결하게 쓸 것.
    - 모든 문장은 실질적 정보를 담을 것. 장식적인 미사여구나 반복적인 문장 구조는 피할 것.

    [디자인 스타일 규칙 - 아래 인라인 style을 모든 해당 태그에 그대로 적용할 것. 절대 생략하거나 다른 폰트/색상으로 바꾸지 말 것]:
    - 문단(p): <p style="font-family:'Noto Sans KR','Malgun Gothic','Apple SD Gothic Neo',sans-serif;font-size:18px;line-height:1.85;color:#3d3d42;margin:0 0 20px;">...</p>
    - 큰 소제목(h2): <h2 style="font-family:'Noto Sans KR','Malgun Gothic','Apple SD Gothic Neo',sans-serif;font-size:24px;font-weight:700;color:#2b2d33;margin:36px 0 16px;">...</h2>
    - 작은 소제목(h3): <h3 style="font-family:'Noto Sans KR','Malgun Gothic','Apple SD Gothic Neo',sans-serif;font-size:20px;font-weight:700;color:#2b2d33;margin:28px 0 12px;">...</h3>
    - 목록(ul): <ul style="font-family:'Noto Sans KR','Malgun Gothic','Apple SD Gothic Neo',sans-serif;font-size:18px;line-height:1.85;color:#3d3d42;padding-left:20px;margin:0 0 20px;">...</ul> (li는 스타일 없이 그대로)
    - 강조(strong): <strong style="color:#16181d;">...</strong>
    - 사진(img): <img style="width:85%;max-width:85%;height:auto;display:block;margin:24px auto;border-radius:8px;" src="..." alt="..."/>
    - 핵심 포인트/팁 강조 박스 (섹션당 1개 정도 활용): <div style="background:#f8f8f9;border-left:4px solid #0f9d7a;border-radius:8px;padding:16px 20px;margin:24px 0;font-family:'Noto Sans KR','Malgun Gothic',sans-serif;font-size:16px;line-height:1.7;color:#2b2d33;"><strong style="color:#0f9d7a;">💡 TIP</strong><br/>...내용...</div>
    - 요약/체크리스트 박스 (글 마지막에 1개): <div style="background:#fefaf3;border:1px solid #f0e4d0;border-radius:8px;padding:20px 24px;margin:28px 0;font-family:'Noto Sans KR','Malgun Gothic',sans-serif;"><strong style="color:#2b2d33;font-size:17px;">✅ 핵심 체크리스트</strong><ul style="margin:12px 0 0;padding-left:20px;color:#3d3d42;line-height:1.8;">...</ul></div>
    """
    resp = model.generate_content(prompt)
    content = resp.text.strip()
    if content.startswith("```html"): content = content[7:]
    if content.startswith("```"): content = content[3:]
    if content.endswith("```"): content = content[:-3]
    return content.strip()

def publish_to_blogger(blog_id, title, html_content, labels, schedule_iso=None, is_draft=False):
    creds = get_credentials()
    service = build("blogger", "v3", credentials=creds)

    body = {
        "kind": "blogger#post",
        "blog": {"id": blog_id},
        "title": title,
        "content": html_content,
        "labels": labels
    }
    if schedule_iso:
        body["published"] = schedule_iso
        is_draft = True

    req = service.posts().insert(blogId=blog_id, body=body, isDraft=is_draft)
    return req.execute()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blog", choices=list(BLOGS_CONFIG.keys()), default="atttrip")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--schedule-hours", type=float, default=4.0)
    parser.add_argument("--no-jitter", action="store_true")
    parser.add_argument("--draft", action="store_true")
    args = parser.parse_args()

    blog_cfg = BLOGS_CONFIG[args.blog]
    blog_id = os.environ.get("BLOG_ID") or blog_cfg["id"]

    schedule_iso = None
    if args.schedule_hours > 0 and not args.draft:
        schedule_iso, readable_time, jitter = calculate_natural_schedule_time(args.schedule_hours, not args.no_jitter)
        print(f"⏰ 예약 발행 시간: {readable_time} (지터: {jitter:+d}분)")

    html_content = generate_post_content(blog_cfg, args.topic)
    res = publish_to_blogger(blog_id, args.topic, html_content, blog_cfg["default_labels"], schedule_iso, args.draft)

    print(f"🎉 발행 완료! 글 ID: {res.get('id')} | 제목: {res.get('title')}")

if __name__ == "__main__":
    main()
