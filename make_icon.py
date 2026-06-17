"""生成 app.ico —— Vercel 风格的「R」徽章，含多尺寸图层。"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Vercel 设计系统主色
INK = (23, 23, 23, 255)        # #171717
CANVAS = (255, 255, 255, 255)  # #ffffff
SUBTLE = (0, 112, 243, 255)    # #0070f3  link 蓝
RING = (0, 0, 0, 30)           # 1px 描边（淡）

SIZES = (16, 24, 32, 48, 64, 128, 256)


def _find_font(size: int) -> ImageFont.FreeTypeFont:
    """优先使用系统等宽字体；找不到则 fallback 到 default。"""
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf",   # Segoe UI Bold
        r"C:\Windows\Fonts\arialbd.ttf",    # Arial Bold
        r"C:\Windows\Fonts\consolab.ttf",   # Consolas Bold
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size=int(size * 0.7))
            except Exception:
                pass
    return ImageFont.load_default()


def _draw_icon(size: int) -> Image.Image:
    """在 size×size 的画布上画一个圆角方形 + 居中的「R」。"""
    # 上采样到 4× 再降采样，AA 更平滑
    scale = 4
    big = size * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 圆角矩形底
    radius = int(big * 0.22)
    draw.rounded_rectangle((0, 0, big - 1, big - 1), radius=radius, fill=INK)

    # 中心位置描一个小蓝点（呼应 link 蓝）
    dot_r = int(big * 0.08)
    cx, cy = big // 2, int(big * 0.22)
    draw.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), fill=SUBTLE)

    # 字母 R
    font = _find_font(size)
    text = "R"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    # 字母略偏下，蓝点在上方
    tx = (big - tw) // 2 - bbox[0]
    ty = int(big * 0.42) - bbox[1]
    draw.text((tx, ty), text, fill=CANVAS, font=font)

    return img.resize((size, size), Image.LANCZOS)


def main() -> int:
    out = Path(__file__).resolve().parent / "app.ico"
    frames = [_draw_icon(s) for s in SIZES]
    # Pillow 会自动把最大尺寸当 256 源，存为多分辨率 ICO
    frames[-1].save(
        out,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=frames[:-1],
    )
    print(f"[make_icon] wrote {out} ({out.stat().st_size} bytes, sizes={SIZES})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
