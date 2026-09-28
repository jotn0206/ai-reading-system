# -*- coding: utf-8 -*-
"""把 ImageGen 产出的 1024 方图处理成 512x512 技能图标：
1) 内缩裁掉生成图外圈的白色圆角留白 -> 让图标满幅
2) 抹掉右下角水印（用正上方同宽的干净背景块覆盖）
3) 重采样到 512x512，输出到技能根目录 icon.png
"""
from pathlib import Path
from PIL import Image

SRC = Path(r'D:/jotnbook/reading-system-skill/dist/Flat_vector_app_icon__1_1_squa_2026-09-27T01-04-27.png')
DST_SKILL = Path(r'D:/jotnbook/reading-system-skill/ai-reading-system/icon.png')
DST_PREVIEW = Path(r'D:/jotnbook/reading-system-skill/dist/icon-512.png')

INSET = 38                      # 内缩像素，去掉外圈留白
img = Image.open(SRC).convert('RGB')
w, h = img.size
img = img.crop((INSET, INSET, w - INSET, h - INSET))
W, H = img.size
print('crop ->', img.size)

# 抹水印：右下角 (W-110, H-70) 起的 110x70 区域，用其正上方 100px 处的背景覆盖
pw, ph = 130, 80
box = (W - pw, H - ph, W, H)
src_box = (W - pw, H - ph - 110, W, H - 110)
img.paste(img.crop(src_box), box)
print('watermark patched')

# 顺手把四角像素统一（裁切后边缘可能有半透明白边残留）
out = img.resize((512, 512), Image.LANCZOS)


def flatten_corners(im, band=14, thr=190):
    """外圈 band 像素里凡是接近白色的（原来是圆角外的留白），用向内 16px 处的背景色填掉。"""
    px = im.load()
    src = im.copy().load()
    fixed = 0
    for y in range(im.height):
        for x in range(im.width):
            if not (x < band or y < band or x >= im.width - band or y >= im.height - band):
                continue
            r, g, b = src[x, y]
            if min(r, g, b) > thr:
                sx = 16 if x < 16 else (im.width - 17 if x >= im.width - 16 else x)
                sy = 16 if y < 16 else (im.height - 17 if y >= im.height - 16 else y)
                px[x, y] = src[sx, sy]
                fixed += 1
    return fixed


print('corner px patched:', flatten_corners(out))
DST_SKILL.parent.mkdir(parents=True, exist_ok=True)
out.save(DST_SKILL, 'PNG', optimize=True)
out.save(DST_PREVIEW, 'PNG', optimize=True)
print('saved ->', DST_SKILL, out.size, f'{DST_SKILL.stat().st_size/1024:.1f} KB')
print('saved ->', DST_PREVIEW, f'{DST_PREVIEW.stat().st_size/1024:.1f} KB')
