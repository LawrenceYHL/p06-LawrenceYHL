# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

# Regression test for issue #2: transparent round_corner leaves a dark ring.
# The arc pixels stay fully opaque and are darkened toward black. The fix
# must smooth the arc through the alpha channel, so partly transparent
# pixels appear along the corner.

from tornado.testing import gen_test

from tests.base import FilterTestCase

CORNER_RADIUS = 60


class RoundCornerFringeTestCase(FilterTestCase):
    @gen_test
    async def test_transparent_round_corner_edge_is_smoothed_by_alpha(self):
        image = await self.get_filtered(
            "source.jpg",
            "thumbor.filters.round_corner",
            f"round_corner({CORNER_RADIUS},255,255,255,1)",
            mode="RGBA",
        )

        pixels = image.load()
        width, height = image.size
        corner_box = [
            (x, y)
            for x in range(CORNER_RADIUS)
            for y in range(CORNER_RADIUS)
            if x < width and y < height
        ]

        partly_transparent = [
            (x, y)
            for (x, y) in corner_box
            if 0 < pixels[x, y][3] < 255
        ]

        assert partly_transparent, (
            "no partly transparent pixels along the rounded corner; "
            "the arc edge is fully opaque, which leaves the dark ring"
        )
