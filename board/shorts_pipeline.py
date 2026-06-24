"""숏폼공장 — Google AI 멀티모달 파이프라인 (BYOK).

파이프라인 순서:
  1. Gemini → 씬별 이미지·영상 프롬프트 + BGM 프롬프트 생성
  2. Imagen 3 → 씬 이미지 생성 (base64)
  3. Veo 2 → 이미지 기반 영상 클립 생성 (폴링, base64)
  4. Lyria → BGM 생성 (base64)
  5. 결과 반환 → 프론트엔드에서 재생
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import urllib.request
import urllib.error
import urllib.parse

import security_utils

ALLOWED_STYLES = frozenset(
    {"Trendy & Dynamic", "Warm", "Cinematic", "Retro", "Minimal"}
)
ALLOWED_DURATIONS = frozenset({15, 30, 60})

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
IMAGEN_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
VEO_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Veo 폴링 최대 대기 시간 (초)
VEO_POLL_TIMEOUT = 180
VEO_POLL_INTERVAL = 5


@dataclass
class SceneScript:
    scene_number: int
    duration_ratio: float
    narration: str
    caption: str
    imagen_prompt: str
    veo_prompt: str = ""


@dataclass
class ShortsBlueprint:
    bgm_lyria_prompt: str
    scenes: List[SceneScript] = field(default_factory=list)


# ─────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────

def _post_json(url: str, body: dict) -> dict:
    """urllib 기반 JSON POST (외부 의존성 없음)."""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body_txt[:300]}") from e


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ─────────────────────────────────────────
# 1. Gemini — 프롬프트 생성
# ─────────────────────────────────────────

def _gemini_generate_blueprint(
    api_key: str, name: str, concept: str, style: str, duration: int
) -> ShortsBlueprint:
    """Gemini 2.5 Flash로 씬 구성 + 프롬프트 JSON 생성."""
    num_scenes = 3 if duration <= 30 else 5
    sec_per_scene = duration // num_scenes

    system_prompt = (
        "You are a professional short-form video director specializing in 9:16 social media ads. "
        "Always respond ONLY with a valid JSON object, no markdown fences."
    )
    user_prompt = f"""Create a {duration}-second shortform video plan for a local business ad.

Business name: {name}
Business concept / signature menu: {concept}
Visual style: {style}
Number of scenes: {num_scenes} (each ~{sec_per_scene}s)

Return EXACTLY this JSON structure:
{{
  "bgm_prompt": "<Lyria BGM prompt in English, ~30 words, matches {style} mood>",
  "scenes": [
    {{
      "scene_number": 1,
      "duration_ratio": 0.33,
      "narration": "<Korean narration 1–2 sentences>",
      "caption": "<Korean caption ≤15 chars>",
      "imagen_prompt": "<Imagen 3 prompt in English, aspect_ratio:9:16, {style} style, ≤60 words>",
      "veo_prompt": "<Veo 2 motion prompt in English, describes camera movement & action, ≤30 words>"
    }}
  ]
}}

Rules:
- imagen_prompt must include "aspect ratio 9:16", photorealistic, no text overlays
- veo_prompt describes only movement/animation, no story
- narration and caption must be in Korean
- BGM prompt in English only
"""

    url = f"{GEMINI_API_BASE}/models/gemini-2.5-flash:generateContent?key={api_key}"
    body = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048},
    }
    resp = _post_json(url, body)
    raw = resp["candidates"][0]["content"]["parts"][0]["text"]

    # JSON 파싱 (마크다운 펜스 제거)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    parsed = json.loads(raw.strip())

    scenes = []
    for s in parsed.get("scenes", []):
        scenes.append(SceneScript(
            scene_number=s["scene_number"],
            duration_ratio=float(s.get("duration_ratio", 1 / num_scenes)),
            narration=s.get("narration", ""),
            caption=s.get("caption", ""),
            imagen_prompt=s.get("imagen_prompt", ""),
            veo_prompt=s.get("veo_prompt", ""),
        ))

    return ShortsBlueprint(
        bgm_lyria_prompt=parsed.get("bgm_prompt", ""),
        scenes=scenes,
    )


# ─────────────────────────────────────────
# 2. Imagen 3 — 이미지 생성
# ─────────────────────────────────────────

def _imagen_generate(api_key: str, prompt: str) -> str:
    """Imagen 3으로 이미지를 생성하고 base64 반환."""
    url = f"{IMAGEN_API_BASE}/models/imagen-3.0-generate-002:predict?key={api_key}"
    body = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": "9:16",
            "safetyFilterLevel": "block_some",
            "personGeneration": "allow_adult",
        },
    }
    resp = _post_json(url, body)
    predictions = resp.get("predictions", [])
    if not predictions:
        raise RuntimeError("Imagen returned no predictions.")
    img_b64 = predictions[0].get("bytesBase64Encoded", "")
    if not img_b64:
        raise RuntimeError("Imagen returned empty image bytes.")
    return img_b64


# ─────────────────────────────────────────
# 3. Veo 2 — 영상 생성 (비동기 폴링)
# ─────────────────────────────────────────

def _veo_generate(api_key: str, image_b64: str, veo_prompt: str, duration_sec: int = 6) -> str:
    """Veo 2로 영상을 생성하고 base64 반환. 없으면 빈 문자열."""
    try:
        url = f"{VEO_API_BASE}/models/veo-2.0-generate-001:predictLongRunning?key={api_key}"
        body = {
            "instances": [{
                "prompt": veo_prompt,
                "image": {
                    "bytesBase64Encoded": image_b64,
                    "mimeType": "image/png",
                },
            }],
            "parameters": {
                "aspectRatio": "9:16",
                "durationSeconds": min(duration_sec, 8),
                "sampleCount": 1,
                "personGeneration": "allow_adult",
            },
        }
        op = _post_json(url, body)
        op_name = op.get("name", "")
        if not op_name:
            return ""

        # 폴링
        poll_url = f"{VEO_API_BASE}/{op_name}?key={api_key}"
        deadline = time.time() + VEO_POLL_TIMEOUT
        while time.time() < deadline:
            time.sleep(VEO_POLL_INTERVAL)
            result = _get_json(poll_url)
            if result.get("done"):
                predictions = result.get("response", {}).get("predictions", [])
                if predictions:
                    return predictions[0].get("bytesBase64Encoded", "")
                return ""
        return ""  # 타임아웃
    except Exception:
        return ""  # Veo 실패 시 이미지 폴백으로 처리


# ─────────────────────────────────────────
# 4. Lyria — BGM 생성
# ─────────────────────────────────────────

def _lyria_generate(api_key: str, prompt: str, duration: int) -> str:
    """Lyria RealTime으로 BGM 생성. 실패 시 빈 문자열."""
    try:
        url = f"{GEMINI_API_BASE}/models/lyria-realtime-exp:generateContent?key={api_key}"
        body = {
            "contents": [{
                "parts": [{"text": f"Generate {duration} seconds of background music: {prompt}"}]
            }],
            "generationConfig": {"responseModalities": ["AUDIO"]},
        }
        resp = _post_json(url, body)
        parts = resp.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        for part in parts:
            inline = part.get("inlineData", {})
            if inline.get("mimeType", "").startswith("audio"):
                return inline.get("data", "")
        return ""
    except Exception:
        return ""


# ─────────────────────────────────────────
# 메인 파이프라인
# ─────────────────────────────────────────

def run_pipeline(payload: dict[str, Any], *, api_key: str) -> dict[str, Any]:
    if not api_key:
        raise ValueError("AI service unavailable.")

    business_name = security_utils.clamp_text(payload.get("business_name"), 80)
    business_concept = security_utils.clamp_text(payload.get("business_concept"), 500)
    if not business_name or not business_concept:
        raise ValueError("Business name and concept are required.")

    video_style = security_utils.clamp_text(payload.get("video_style"), 40) or "Trendy & Dynamic"
    if video_style not in ALLOWED_STYLES:
        video_style = "Trendy & Dynamic"

    try:
        duration_seconds = int(payload.get("duration_seconds") or 15)
    except (TypeError, ValueError):
        duration_seconds = 15
    if duration_seconds not in ALLOWED_DURATIONS:
        duration_seconds = 15

    clip_duration = max(5, duration_seconds // 3)

    # ── Step 1: Gemini로 씬 구성 ──
    blueprint = _gemini_generate_blueprint(
        api_key, business_name, business_concept, video_style, duration_seconds
    )

    # ── Step 2 & 3 & 4: 씬별 이미지 + 영상 생성 ──
    timeline_scenes = []
    for scene in blueprint.scenes:
        # 이미지 생성
        try:
            img_b64 = _imagen_generate(api_key, scene.imagen_prompt)
        except Exception as exc:
            img_b64 = ""
            scene.caption = f"[이미지 생성 실패: {exc}]"

        # 영상 생성 (이미지 기반)
        video_b64 = ""
        if img_b64 and scene.veo_prompt:
            video_b64 = _veo_generate(api_key, img_b64, scene.veo_prompt, clip_duration)

        timeline_scenes.append({
            "scene_number": scene.scene_number,
            "narration": scene.narration,
            "caption": scene.caption,
            "imagen_prompt": scene.imagen_prompt,
            "veo_prompt": scene.veo_prompt,
            "image_b64": img_b64,         # Imagen 결과
            "video_b64": video_b64,        # Veo 결과 (없으면 빈 문자열 → 이미지 폴백)
        })

    # ── Step 4: BGM 생성 ──
    bgm_b64 = _lyria_generate(api_key, blueprint.bgm_lyria_prompt, duration_seconds)

    return {
        "status": "success",
        "message": f"✅ {len(timeline_scenes)}개 씬 · 이미지 · 영상 · 음악 생성 완료!",
        "meta": {
            "business_name": business_name,
            "style": video_style,
            "total_duration": duration_seconds,
            "scene_count": len(timeline_scenes),
            "bgm": bool(bgm_b64),
        },
        "assets": {
            "bgm_b64": bgm_b64,
            "bgm_mime": "audio/wav",
            "timeline_scenes": timeline_scenes,
        },
    }
