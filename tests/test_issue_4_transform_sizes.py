# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

# Regression tests for issue #4: very wide or very short targets,
# and fit-in boxes smaller than the crop math allows.

import asyncio
from io import BytesIO
from types import SimpleNamespace
from unittest import TestCase

from PIL import Image, ImageDraw

from thumbor.config import Config
from thumbor.context import Context, RequestParameters
from thumbor.engines.pil import Engine
from thumbor.transformer import Transformer


def make_rainbow_png():
    # 16x16 square with transparent background and opaque vertical bars.
    colours = [
        (255, 0, 0),
        (255, 165, 0),
        (255, 255, 0),
        (0, 128, 0),
        (0, 0, 255),
        (75, 0, 130),
        (238, 130, 238),
        (255, 255, 255),
    ]
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for index, colour in enumerate(colours):
        draw.rectangle(
            [index * 2, 0, index * 2 + 1, 15], fill=colour + (255,)
        )
    buffer = BytesIO()
    img.save(buffer, "PNG")
    return buffer.getvalue()


def make_wide_png():
    # 940x2 opaque image, the shape used by the issue's fit-in requests.
    img = Image.new("RGBA", (940, 2), (0, 128, 255, 255))
    buffer = BytesIO()
    img.save(buffer, "PNG")
    return buffer.getvalue()


class Issue4TransformSizesTestCase(TestCase):
    def get_context(self):
        cfg = Config(
            SECURITY_KEY="ACME-SEC",
            ENGINE="thumbor.engines.pil",
        )
        cfg.LOADER = "thumbor.loaders.file_loader"
        cfg.STORAGE = "thumbor.storages.no_storage"
        context = Context(config=cfg)
        # Transformer reads context.modules.detectors even when smart is off.
        context.modules = SimpleNamespace(detectors=[], storage=None)
        return context

    def transform(self, buffer, extension, **params):
        context = self.get_context()
        engine = Engine(context)
        engine.load(buffer, extension)
        context.request = RequestParameters(
            smart=False,
            filters=[],
            **params,
        )
        context.request.engine = engine
        asyncio.run(Transformer(context).transform())
        return engine

    def test_wide_transparent_png_keeps_visible_content(self):
        engine = self.transform(
            make_rainbow_png(), ".png", width=800, height=20
        )
        out = Image.open(BytesIO(engine.read(".png")))
        assert out.size == (800, 20)
        alpha = out.convert("RGBA").getchannel("A")
        # The colour bars are opaque, so a blank result has no visible pixels.
        assert sum(alpha.histogram()[1:]) > 0

    def test_fit_in_1x1_returns_one_pixel_image(self):
        engine = self.transform(
            make_wide_png(), ".png", fit_in=True, width=1, height=1
        )
        out = Image.open(BytesIO(engine.read(".png")))
        assert out.size == (1, 1)

    def test_fit_in_width_only_returns_100x1_image(self):
        engine = self.transform(
            make_wide_png(), ".png", fit_in=True, width=100, height=0
        )
        out = Image.open(BytesIO(engine.read(".png")))
        assert out.size == (100, 1)
