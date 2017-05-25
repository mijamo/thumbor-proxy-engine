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

import datetime
import importlib

from thumbor.engines import BaseEngine


class Engine(BaseEngine):
    def __init__(self, context):
        engines = context.config.PROXY_ENGINE_ENGINES

        # Create an object that will store local values
        # Setting it this way avoids hitting the __setattr__
        # proxying
        super(Engine, self).__setattr__('lcl', {})

        self.lcl['context'] = context
        self.lcl['engines'] = engines

        for engine in engines:
            self.init_engine(context, engine)

    def init_engine(self, context, module):
        mod = importlib.import_module(module)
        klass = getattr(mod, 'Engine')

        self.lcl[module] = klass(context)

    def select_engine(self):
        if self.lcl['selected_engine'] is not None:
            return self.lcl['selected_engine']

        for enginename in self.lcl['engines']:
            engine = self.lcl[enginename]
            try:
                if engine.should_run(
                    self.lcl['extension'],
                    self.lcl['buffer']
                ):
                    self.lcl['selected_engine'] = enginename
                    return enginename

            # Not implementing should_run means that the engine
            # should run unconditionally.
            # This is required for the stock PIL engine to act as a
            # fallback.
            except AttributeError:
                self.lcl['selected_engine'] = enginename
                return enginename

        raise Exception(
            'Unable to find a suitable engine, tried %r' % self.lcl['engines']
        )

    # This is our entry point for the proxy, it's the first call to the engine
    def load(self, buffer, extension):
        self.lcl['start'] = datetime.datetime.now()

        # buffer and extension are needed by select_engine
        self.lcl['extension'] = extension
        self.lcl['buffer'] = buffer
        self.lcl['selected_engine'] = None

        # Now that we'll select the right engine, let's initialize it
        self.lcl['context'].request_handler.set_header(
            'Engine',
            self.select_engine()
        )

        super(Engine, self).__init__(self.lcl['context'])
        super(Engine, self).load(buffer, extension)

    def __getattribute__(self, name):
        if name in vars(Engine):
            return object.__getattribute__(self, name)
        return getattr(self.lcl[self.select_engine()], name)

    def __delattr__(self, name):
        return delattr(self.lcl[self.select_engine()], name)

    def __setattr__(self, name, value):
        return setattr(self.lcl[self.select_engine()], name, value)

    # This is the exit point for requests, where the generated image is
    # converted to the target format
    def read(self, extension=None, quality=None):
        ret = self.__getattr__('read')(extension, quality)

        finish = datetime.datetime.now()
        duration = int(
            round(
                (finish - self.lcl['start']).total_seconds() * 1000,
                0
            )
        )

        self.lcl['context'].metrics.timing(
            'engine.process_time.' + self.select_engine(),
            duration
        )

        self.lcl['context'].request_handler.set_header(
            'ProcessingTime',
            duration
        )

        return ret
