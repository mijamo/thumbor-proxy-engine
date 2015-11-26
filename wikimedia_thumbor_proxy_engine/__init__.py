#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com
# Copyright (c) 2015 Wikimedia Foundation

# Proxy engine, redirects requests to other engines
# according to configurable logic

import importlib

from thumbor.engines import BaseEngine


class Engine(BaseEngine):
    def __init__(self, context):
        engines = context.config.PROXY_ENGINE_ENGINES

        object.__setattr__(self, 'context', context)
        object.__setattr__(self, 'engines', engines)

        for engine in engines:
            self.init_engine(context, engine)

    def init_engine(self, context, module):
        mod = importlib.import_module(module)
        klass = getattr(mod, 'Engine')
        object.__setattr__(self, module, klass(context))

    def select_engine(self):
        buffer = object.__getattribute__(self, 'buffer')
        extension = object.__getattribute__(self, 'extension')
        engines = object.__getattribute__(self, 'engines')

        for enginename in engines:
            engine = object.__getattribute__(self, enginename)
            try:
                if engine.should_run(extension, buffer):
                    return enginename

            # Not implementing should_run means that the engine
            # should run unconditionally.
            # This is required for the stock PIL engine to act as a
            # fallback.
            except AttributeError:
                return enginename

        raise Exception('Unable to find a suitable engine, tried %r' % engines)

    # This is our entry point for the proxy, it's the first call to the engine
    def load(self, buffer, extension):
        # buffer and extension are needed by select_engine
        object.__setattr__(self, 'extension', extension)
        object.__setattr__(self, 'buffer', buffer)

        # Now that we'll select the right engine, let's initialize it
        context = object.__getattribute__(self, 'context')
        super(Engine, self).__init__(context)
        super(Engine, self).load(buffer, extension)

    def __getattr__(self, name):
        engine = getattr(self, 'select_engine')()

        return getattr(object.__getattribute__(self, engine), name)

    def __delattr__(self, name):
        engine = self.select_engine()
        return delattr(object.__getattribute__(self, engine), name)

    def __setattr__(self, name, value):
        engine = self.select_engine()
        return setattr(object.__getattribute__(self, engine), name, value)

    # The following have to be redefined because their fallbacks in BaseEngine
    # don't have the right amount of parameters
    def create_image(self, buffer):
        return self.__getattr__('create_image')(buffer)

    def crop(self, left, top, right, bottom):
        return self.__getattr__('crop')(left, top, right, bottom)

    def image_data_as_rgb(self, update_image=True):
        return self.__getattr__('image_data_as_rgb')(update_image)

    def read(self, extension=None, quality=None):
        return self.__getattr__('read')(extension, quality)

    def resize(self, width, height):
        return self.__getattr__('resize')(width, height)

    def set_image_data(self, data):
        return self.__getattr__('set_image_data')(data)

    @property
    def size(self):
        return self.__getattr__('size')
