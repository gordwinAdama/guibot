#!/usr/bin/python
# Copyright 2013 Intranet AG / Thomas Jarosch and Plamen Dimitrov
#
# guibender is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# guibender is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with guibender.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import unittest
import time
import shutil
import subprocess
import common_test

from settings import GlobalSettings
from imagepath import ImagePath
from location import Location
from region import Region
from match import Match
from desktopcontrol import AutoPyDesktopControl
from image import Image
from inputmap import Key
from errors import *


class RegionTest(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.imagepath = ImagePath()
        self.imagepath.add_path(os.path.join(common_test.unittest_dir, 'images'))

        self.script_img = os.path.join(common_test.unittest_dir, 'qt4_image.py')
        self.script_app = os.path.join(common_test.unittest_dir, 'qt4_application.py')

    def setUp(self):
        self.child_img = None
        self.child_app = None

    def tearDown(self):
        self.close_windows()
        if os.path.exists(GlobalSettings.image_logging_destination):
            shutil.rmtree(GlobalSettings.image_logging_destination)

    def test_basic(self):
        screen_width = AutoPyDesktopControl().width
        screen_height = AutoPyDesktopControl().height

        region = Region()
        self.assertEqual(0, region.x)
        self.assertEqual(0, region.y)
        self.assertEqual(screen_width, region.width)
        self.assertEqual(screen_height, region.height)

        region = Region(10, 20, 300, 200)
        self.assertEqual(10, region.x)
        self.assertEqual(20, region.y)
        self.assertEqual(300, region.width)
        self.assertEqual(200, region.height)

    def wait_end(self, subprocess_pipe, timeout=30):
        expires = time.time() + timeout

        while True:
            exit_code = subprocess_pipe.poll()
            if exit_code is not None:
                return exit_code

            if time.time() > expires:
                self.fail('Program did not close on time. Ignoring')
                break

            time.sleep(0.2)

    def show_image(self, filename):
        filename = self.imagepath.search(filename)
        self.child_img = subprocess.Popen(['python', self.script_img, filename])
        # HACK: avoid small variability in loading speed
        time.sleep(1)

    def show_application(self):
        self.child_app = subprocess.Popen(['python', self.script_app])
        # HACK: avoid small variability in loading speed
        time.sleep(1)

    def close_windows(self):
        if self.child_img is not None:
            self.child_img.terminate()
            self.wait_end(self.child_img)
            self.child_img = None

            # HACK: make sure app is really closed
            time.sleep(0.5)

        if self.child_app is not None:
            self.child_app.terminate()
            self.wait_end(self.child_app)
            self.child_app = None

            # HACK: make sure app is really closed
            time.sleep(0.5)

    def test_find(self):
        self.show_image('all_shapes')

        region = Region()
        match = region.find(Image('shape_blue_circle'))

        self.assertEqual(165, match.width)
        self.assertEqual(151, match.height)

        # Match again - this time just pass a filename
        match = region.find('shape_pink_box')
        self.assertEqual(69, match.width)
        self.assertEqual(48, match.height)

        # Test get_last_match()
        last_match = region.last_match
        self.assertEqual(last_match.x, match.x)
        self.assertEqual(last_match.y, match.y)
        self.assertEqual(last_match.width, match.width)
        self.assertEqual(last_match.height, match.height)

    def test_find_target_offset(self):
        self.show_image('all_shapes.png')

        match = Region().find(Image('shape_blue_circle.png'))

        # Positive target offset
        match_offset = Region().find(Image('shape_blue_circle.png').with_target_offset(200, 100))
        self.assertEqual(match.target.x + 200, match_offset.target.x)
        self.assertEqual(match.target.y + 100, match_offset.target.y)

        # Positive target offset
        match_offset = Region().find(Image('shape_blue_circle.png').with_target_offset(-50, -30))
        self.assertEqual(match.target.x - 50, match_offset.target.x)
        self.assertEqual(match.target.y - 30, match_offset.target.y)

    def test_find_error(self):
        try:
            Region().find(Image('shape_blue_circle.png'), 0)
            self.fail('exception was not thrown')
        except FindError, e:
            pass

        try:
            Region().find_all(Image('shape_blue_circle.png'), 0)
            self.fail('exception was not thrown')
        except FindError, e:
            pass

    def test_zero_matches(self):
        self.show_image('all_shapes')

        matches = Region().find_all(Image('shape_blue_circle'))
        self.assertEqual(len(matches), 1)

        self.close_windows()

        matches = Region().find_all(Image('shape_blue_circle'), allow_zero=True)
        self.assertEqual(len(matches), 0)

        self.close_windows()

    def test_find_all(self):
        self.show_image('all_shapes')
        # TODO: find should consider both autopy
        # and OpenCV but both may not be supported
        # at developer's platform
        greenbox = Image('shape_green_box')
        matches = Region().find_all(greenbox)
        self.assertEqual(len(matches), 1)
        self.assertEqual(67, matches[0].width)
        self.assertEqual(52, matches[0].height)

        redbox = Image('shape_red_box')
        matches = Region().find_all(redbox)
        self.assertEqual(len(matches), 3)
        for match in matches:
            Region().hover(match)
            time.sleep(0.5)
            self.assertEqual(68, match.width)
            self.assertEqual(56, match.height)

        pinkbox = Image('shape_pink_box')

        # pink is similar to red, so the best fuzzy matches also
        # include the three red boxes when considering color
        pinkbox.match_settings.p["find"]["similarity"].value = 0.5
        pinkbox.match_settings.p["find"]["nocolor"].value = False
        matches = Region().find_all(pinkbox)
        self.assertEqual(len(matches), 4)
        for match in matches:
            Region().hover(match)
            time.sleep(0.5)
            self.assertEqual(69, match.width)
            self.assertEqual(48, match.height)

        # ignore colors here so the best matches for the pink box
        # should be based on shape (the green and yellow box)
        pinkbox.match_settings.p["find"]["similarity"].value = 0.8
        pinkbox.match_settings.p["find"]["nocolor"].value = True
        matches = Region().find_all(pinkbox)
        self.assertEqual(len(matches), 3)
        for match in matches:
            Region().hover(match)
            time.sleep(0.5)
            self.assertEqual(69, match.width)
            self.assertEqual(48, match.height)

    def test_sample(self):
        self.show_image('all_shapes')
        # sampling is done only from the current haystack
        # so wait a bit to reach the correct haystack
        time.sleep(5)

        similarity = Region().sample(Image('shape_blue_circle'))
        self.assertAlmostEqual(similarity, 0.999999, delta=0.001)

        self.close_windows()

    def test_exists(self):
        self.show_image('all_shapes')

        match = Region().find(Image('shape_blue_circle'))
        self.assertTrue(isinstance(match, Match))

        self.close_windows()

        match = Region().exists(Image('shape_blue_circle'))
        self.assertEqual(None, match)

        # TODO: it is not clear what the following two lines do
        # since windows should already be closed?
        self.close_windows()

        Region().wait_vanish('all_shapes')

    def test_wait(self):
        self.show_image('all_shapes')
        match = Region().wait(Image('shape_blue_circle'), timeout=5)
        self.assertTrue(isinstance(match, Match))

        self.close_windows()

    def test_wait_vanish(self):
        self.show_image('all_shapes')
        time.sleep(3)
        self.assertRaises(NotFindError, Region().wait_vanish, 'all_shapes', timeout=30)
        # self.assertFalse()

        self.close_windows()
        # assert no NotFindError is raised now
        Region().wait_vanish('all_shapes', timeout=10)

    def test_hover(self):
        # Hover over Location
        self.show_image('all_shapes')
        region = Region()
        match = region.find(Image('shape_blue_circle'))
        match.hover(match.target)

        # Hover over Image with 50% similarity
        region.cv_backend.eq.p["find"]["similarity"].value = 0.5
        region.hover(Image('shape_pink_box'))

    def test_click(self):
        self.show_application()
        Region().click('qt4gui_button')
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_double_click(self):
        self.show_application()
        Region().idle(2).double_click('qt4gui_double_click')
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_right_click(self):
        self.show_application()
        Region().right_click('qt4gui_contextmenu_label').nearby(200).idle(3).click('qt4gui_contextmenu_quit')
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_press_keys(self):
        self.show_application()
        time.sleep(1)
        Region().press_keys(Region().ESC)
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

        self.show_application()
        time.sleep(1)
        Region().press_keys([Region().ALT, Region().F4])
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_press_at(self):
        self.show_application()
        Region().press_at([Region().ENTER], 'qt4gui_lineedit2')
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_type_text(self):
        self.show_application()
        Region().click('qt4gui_lineedit').idle(0.2).type_text('quit')
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_type_at(self):
        self.show_application()
        Region().type_at('quit', 'qt4gui_lineedit')
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_drag_drop(self):
        self.show_application()
        Region().drag_drop('qt4gui_textedit', 'qt4gui_lineedit')
        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_drag_from(self):
        self.show_application()

        # TODO: some bug does not allow for Region().drag_from().hover()
        Region().drag_from('qt4gui_textedit')
        Region().hover('qt4gui_label1')

        # toggled buttons cleanup
        Region().dc_backend.mouse_up(Region().LEFT_BUTTON)

        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_drop_at(self):
        self.show_application()

        # TODO: some bug does not allow for Region().drag().hover()
        Region().drag_from('qt4gui_textedit')
        Region().hover('qt4gui_label2')
        self.assertRaises(NotFindError, Region().wait_vanish, 'qt4gui_label2', timeout=3)

        Region().drop_at('qt4gui_label2')

        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_mouse_down(self):
        self.show_application()

        Region().idle(2).mouse_down('qt4gui_label3')

        # toggled buttons cleanup
        Region().dc_backend.mouse_up(Region().LEFT_BUTTON)

        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_mouse_up(self):
        self.show_application()

        Region().idle(2).mouse_down('qt4gui_label4')
        self.assertRaises(NotFindError, Region().wait_vanish, 'qt4gui_label4', timeout=3)

        Region().mouse_up('qt4gui_label4')

        self.assertEqual(0, self.wait_end(self.child_app))
        self.child_app = None

    def test_get_mouse_location(self):
        Region().hover(Location(0, 0))

        pos = Region().mouse_location
        # Exact match currently not possible, autopy is not pixel perfect.
        self.assertTrue(pos.x < 5)
        self.assertTrue(pos.y < 5)

        Region().hover(Location(30, 20))

        pos = Region().mouse_location
        # Exact match currently not possible, autopy is not pixel perfect.
        self.assertTrue(pos.x > 25 and pos.x < 35)
        self.assertTrue(pos.y > 15 and pos.y < 25)


if __name__ == '__main__':
    unittest.main()
