# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

from io import BytesIO
from unittest import TestCase

from PIL import Image, ImageDraw

from thumbor.config import Config
from thumbor.context import Context
from thumbor.engines.pil import Engine


def make_transparent_palette_gif():
    # Palette GIF: index 0 is the transparent background, index 1 is a disc.
    img = Image.new("P", (100, 100), 0)
    palette = [0, 0, 0, 0, 0, 255] + [0, 0, 0] * 254
    img.putpalette(palette)
    draw = ImageDraw.Draw(img)
    draw.ellipse([20, 20, 80, 80], fill=1)

    buffer = BytesIO()
    img.save(buffer, "GIF", transparency=0)
    return buffer.getvalue()


class GifTransparencyResizeTestCase(TestCase):
    def get_context(self):
        cfg = Config(
            SECURITY_KEY="ACME-SEC",
            ENGINE="thumbor.engines.pil",
        )
        cfg.LOADER = "thumbor.loaders.file_loader"
        cfg.STORAGE = "thumbor.storages.no_storage"

        return Context(config=cfg)

    def test_resized_gif_keeps_transparent_background(self):
        source = make_transparent_palette_gif()
        source_img = Image.open(BytesIO(source))
        assert "transparency" in source_img.info
        assert source_img.convert("RGBA").getpixel((0, 0))[3] == 0

        engine = Engine(self.get_context())
        engine.load(source, ".gif")
        assert engine.original_mode == "P"

        engine.resize(50, 40)
        result = engine.read(".gif")

        out = Image.open(BytesIO(result))
        assert out.format == "GIF"
        assert "transparency" in out.info

        rgba = out.convert("RGBA")
        # Corner was transparent in the source and must stay transparent.
        assert rgba.getpixel((0, 0))[3] == 0
        # Centre of the disc was opaque in the source and must stay opaque.
        assert rgba.getpixel((25, 20))[3] == 255

    def test_resized_png_keeps_partial_alpha(self):
        # Palette PNG with alpha 0, 128 and 255 entries, one band each.
        img = Image.new("P", (90, 30), 0)
        img.putpalette([0, 0, 0, 255, 0, 0, 0, 0, 255] + [0, 0, 0] * 253)
        draw = ImageDraw.Draw(img)
        draw.rectangle([30, 0, 59, 29], fill=1)
        draw.rectangle([60, 0, 89, 29], fill=2)
        buffer = BytesIO()
        img.save(buffer, "PNG", transparency=bytes([0, 128, 255]))

        engine = Engine(self.get_context())
        engine.load(buffer.getvalue(), ".png")
        assert engine.original_mode == "P"

        engine.resize(60, 20)
        result = engine.read(".png")

        out = Image.open(BytesIO(result))
        assert out.format == "PNG"
        alpha = out.convert("RGBA").getchannel("A").histogram()
        assert alpha[0] > 0
        # Quantization maps the opaque band to 254, not 255, on main too.
        assert sum(alpha[250:256]) > 0
        # Partial alpha from the source palette must survive the resize.
        assert sum(alpha[1:255]) > 0
