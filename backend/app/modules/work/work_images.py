"""업로드 이미지를 제한하고 Codex에 전달할 PNG로 정규화합니다."""

from io import BytesIO
from pathlib import PurePath

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps

MAX_IMAGES = 4
MAX_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 16_000_000
MAX_SIDE = 1600


def normalize(files: list[UploadFile]) -> list[tuple[str, bytes]]:
    """최대 네 장의 정적 PNG, JPEG, WebP에서 픽셀만 추출합니다."""
    if len(files) > MAX_IMAGES:
        raise HTTPException(422, "이미지는 최대 4장까지 첨부할 수 있습니다.")
    images = []
    total = 0
    for index, file in enumerate(files, 1):
        payload = file.file.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise HTTPException(413, "이미지는 한 장당 5MB까지 첨부할 수 있습니다.")
        total += len(payload)
        if total > MAX_TOTAL_BYTES:
            raise HTTPException(413, "첨부 이미지의 합계는 8MB까지 가능합니다.")
        try:
            with Image.open(
                BytesIO(payload), formats=["PNG", "JPEG", "WEBP"]
            ) as source:
                if source.width * source.height > MAX_PIXELS or getattr(
                    source, "is_animated", False
                ):
                    raise ValueError("Unsupported image dimensions or animation")
                image = ImageOps.exif_transpose(source)
                image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
                clean = Image.new("RGBA", image.size)
                clean.paste(image.convert("RGBA"), (0, 0))
                output = BytesIO()
                clean.save(output, format="PNG")
        except (
            Image.DecompressionBombError,
            OSError,
            ValueError,
            SyntaxError,
        ) as error:
            raise HTTPException(
                422, "정상적인 정적 PNG, JPEG 또는 WebP 이미지를 첨부해 주세요."
            ) from error
        name = PurePath((file.filename or "").replace(chr(92), "/")).name.strip()
        images.append((name[:255] or f"이미지 {index}", output.getvalue()))
    return images
