#!/usr/bin/python
# Copyright 2013 Intranet AG / Thomas Jarosch
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

"""
Frontend with serialization compatible API allowing the use of Pyro4 modified
:py:class:`guibender.GuiBender` object (creating and running the same object
remotely and manipulating it locally). All the methods delegate their calls to
this object with some additional postprocessing to make the execution remote so
for information about the API please refer to it and :py:class:`region.Region`.
"""

import re

import Pyro4

import errors
from guibender import GuiBender


class GuiBenderProxy(GuiBender):
    """
    The proxy guibender object is just a wrapper around the actual guibender
    object that takes care of returning easily serializable Pyro4 proxy objects
    instead of the real ones or their serialized copies.

    It allows you to move the mouse, type text and do any other GuiBender action
    from code which is executed on another machine somewhere on the network.
    """

    def __init__(self, dc=None, cv=None):
        super(GuiBenderProxy, self).__init__(dc=dc, cv=cv)
        # NOTE: the following attribute is set by Pyro when registering
        # this as a remote object
        self._pyroDaemon = None

    def _proxify(self, obj):
        if isinstance(obj, (int, float, bool, basestring)) or obj is None:
            return obj
        if obj not in self._pyroDaemon.objectsById.values():
            self._pyroDaemon.register(obj)
        return obj

    def get_mouse_location(self):
        # override a property
        return self._proxify(super(GuiBenderProxy, self).get_mouse_location())

    def find(self, image, timeout=10):
        return self._proxify(super(GuiBenderProxy, self).find(image, timeout))

    def find_all(self, image, timeout=10, allow_zero=False):
        matches = super(GuiBenderProxy, self).find_all(image, timeout, allow_zero)
        proxified = []
        for match in matches:
            proxified.append(self._proxify(match))
        return proxified

    def sample(self, image):
        return self._proxify(super(GuiBenderProxy, self).sample(image))

    def exists(self, image, timeout=0):
        return self._proxify(super(GuiBenderProxy, self).exists(image, timeout))

    def wait(self, image, timeout=30):
        return self._proxify(super(GuiBenderProxy, self).wait(image, timeout))

    def wait_vanish(self, image, timeout=30):
        return self._proxify(super(GuiBenderProxy, self).wait_vanish(image, timeout))

    def hover(self, image_or_location):
        return self._proxify(super(GuiBenderProxy, self).hover(image_or_location))

    def click(self, image_or_location, modifiers=None):
        return self._proxify(super(GuiBenderProxy, self).click(image_or_location, modifiers))

    def right_click(self, image_or_location, modifiers=None):
        return self._proxify(super(GuiBenderProxy, self).right_click(image_or_location, modifiers))

    def double_click(self, image_or_location, modifiers=None):
        return self._proxify(super(GuiBenderProxy, self).double_click(image_or_location, modifiers))

    def mouse_down(self, image_or_location, button=None):
        return self._proxify(super(GuiBenderProxy, self).mouse_down(image_or_location, button))

    def mouse_up(self, image_or_location, button=None):
        return self._proxify(super(GuiBenderProxy, self).mouse_up(image_or_location, button))

    def drag_drop(self, src_image_or_location, dst_image_or_location, modifiers=None):
        return self._proxify(super(GuiBenderProxy, self).drag_drop(src_image_or_location,
                                                                   dst_image_or_location, modifiers))

    def drag_from(self, image_or_location, modifiers=None):
        return self._proxify(super(GuiBenderProxy, self).drag(image_or_location, modifiers))

    def drop_at(self, image_or_location, modifiers=None):
        return self._proxify(super(GuiBenderProxy, self).drop_at(image_or_location, modifiers))

    def press_keys(self, keys):
        return self._proxify(super(GuiBenderProxy, self).press(keys))

    def press_at(self, image_or_location=None, keys=None):
        return self._proxify(super(GuiBenderProxy, self).press_at(image_or_location, keys))

    def type_text(self, text, modifiers=None):
        return self._proxify(super(GuiBenderProxy, self).type_text(text, modifiers))

    def type_at(self, image_or_location=None, text='', modifiers=None):
        return self._proxify(super(GuiBenderProxy, self).type_at(image_or_location, text, modifiers))


"""
We put here any exceptions that are too complicated for the default serialization
and define their serialization methods.

.. note:: This would not be needed if we were using the Pickle serializer but its
    security problems at the moment made us prefer the serpent serializer paying
    for it with some extra setup steps and functions below.
"""
exceptions = [errors.UnsupportedBackendError]

def serialize_custom_error(class_obj):
    """
    Serialization method for the :py:class:`errors.UnsupportedBackendError`
    which was chosen just as a sample.

    :param class_obj: class object for the serialized error class
    :type class_obj: classobj
    :returns: serialization dictionary with the class name, arguments, and attributes
    :rtype: {str, str or getset_descriptor or dictproxy}
    """
    serialized = {}
    serialized["__class__"] = re.search("<class '(.+)'>", str(type(class_obj))).group(1)
    serialized["args"] = class_obj.args
    serialized["attributes"] = class_obj.__dict__
    return serialized

for exception in exceptions:
    Pyro4.util.SerializerBase.register_class_to_dict(exception, serialize_custom_error)
