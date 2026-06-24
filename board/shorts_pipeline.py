"""숏폼공장 — Google AI 멀티모달 파이프라인 (BYOK)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, List, Optional

import security_utils

ALLOWED_STYLES = frozenset(
    {"Trendy & Dynamic", "Warm", "Cinematic", "Retro", "Minimal"}
)
ALLOWED_DURATIONS = frozenset({15, 30, 60})


@dataclass
class SceneScript:
    scene_number: int
    duration_ratio: float
    narration: str
    caption: str
    imagen_prompt: str
    veo_prompt: Optional[str] = None


@dataclass
class ShortsBlueprint:
    bgm_lyria_prompt: str
    scenes: List[SceneScript]


class GoogleAIShortsEngine:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_blueprint(self, name: str, concept: str, style: str, duration: int) -> ShortsBlueprint:
        scenes = [
            SceneScript(
                scene_number=1,
                duration_ratio=0.3,
                narration=f"치즈가 폭포처럼 흘러내리는 이곳, 바로 {name}입니다.",
                caption="치즈 폭포의 향연!",
                imagen_prompt=(
                    f"Cinematic close-up of crispy premium pork cutlet cut in half, rich melted mozzarella "
                    f"cheese stretching out elegantly, steam rising, gourmet restaurant lighting, 8k, "
                    f"aspect ratio 9:16, {style} style."
                ),
                veo_prompt="Slow motion zooming in, the cheese stretches continuously, steam moving gently up.",
            ),
            SceneScript(
                scene_number=2,
                duration_ratio=0.4,
                narration="제주산 청정 흑돼지만을 사용하여 겉은 바삭하고 속은 육즙으로 가득 차 있죠.",
                caption="겉바속촉의 정석, 100% 제주 흑돼지",
                imagen_prompt=(
                    f"A chef expertly frying golden brown pork cutlets in a clean modern commercial kitchen, "
                    f"professional lighting, action shot, aspect ratio 9:16, {style} style."
                ),
                veo_prompt="Medium panning shot, dynamic oil splashing lightly, golden texture glistening.",
            ),
            SceneScript(
                scene_number=3,
                duration_ratio=0.3,
                narration="오늘 점심은 입안 가득 행복해지는 돈까스 한 입 어떠세요? 지금 매장에서 만나요!",
                caption="오늘 점심은 돈까스 어때요? 매장에서 만나요!",
                imagen_prompt=(
                    f"A happy young couple smiling and taking a big bite of cheese cutlet at {name} restaurant, "
                    f"welcoming and warm atmosphere, cozy interior, aspect ratio 9:16, {style} style."
                ),
                veo_prompt="Slow zoom out, capturing the joyful expressions and cheerful environment.",
            ),
        ]
        return ShortsBlueprint(
            bgm_lyria_prompt=(
                f"A trendy, upbeat lo-fi hip-hop track with a warm acoustic guitar melody and smooth jazzy drums, "
                f"perfect for a modern food vlog, looping, high quality audio for {style} mood."
            ),
            scenes=scenes,
        )

    async def generate_imagen_asset(self, prompt: str) -> str:
        return "BASE64_MOCK_IMAGE_BYTES_FROM_IMAGEN_3"

    async def generate_veo_clip(self, image_bytes_b64: str, veo_prompt: str) -> str:
        return "BASE64_MOCK_VIDEO_BYTES_FROM_VEO_3_1"

    async def generate_lyria_bgm(self, prompt: str, duration: int) -> str:
        return "BASE64_MOCK_AUDIO_BYTES_FROM_LYRIA_3"


async def _run_async(payload: dict[str, Any], *, api_key: str) -> dict[str, Any]:
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

    engine = GoogleAIShortsEngine(api_key=api_key)
    blueprint = await engine.generate_blueprint(
        name=business_name,
        concept=business_concept,
        style=video_style,
        duration=duration_seconds,
    )
    bgm_bytes = await engine.generate_lyria_bgm(blueprint.bgm_lyria_prompt, duration_seconds)

    generated_scenes_assets = []
    for scene in blueprint.scenes:
        img_asset = await engine.generate_imagen_asset(scene.imagen_prompt)
        video_asset = None
        if scene.veo_prompt:
            video_asset = await engine.generate_veo_clip(img_asset, scene.veo_prompt)
        generated_scenes_assets.append(
            {
                "scene_number": scene.scene_number,
                "narration": scene.narration,
                "caption": scene.caption,
                "image_data_preview": img_asset,
                "video_data_render": video_asset if video_asset else "IMAGE_FALLBACK_PANNING",
            }
        )

    return {
        "status": "success",
        "message": "구글 멀티모달 프러덕션 파이프라인 자산 생성 완료.",
        "meta": {
            "business_name": business_name,
            "style": video_style,
            "total_duration": duration_seconds,
        },
        "assets": {
            "bgm_audio_b64": bgm_bytes,
            "timeline_scenes": generated_scenes_assets,
        },
    }


def run_pipeline(payload: dict[str, Any], *, api_key: str) -> dict[str, Any]:
    if not api_key:
        raise ValueError("AI service unavailable.")
    return asyncio.run(_run_async(payload, api_key=api_key))
