# -*- coding: utf-8 -*-

"""Make sure application installed have proper function interface."""

import pytest
import importlib
import inspect

app_names = ['lego', 'pingpong', 'face', 'pool', 'ikea']


def test_handler_func_interface():
    """Test app has handler()."""
    for app_name in app_names:
        app = importlib.import_module(app_name)
        assert hasattr(app, 'Handler')
        assert inspect.isclass(app.Handler)


def func_test_app_handler_has_func(func_name):
    """Test is app handler has the function specified by func_name."""
    for app_name in app_names:
        app = importlib.import_module(app_name)
        handler = app.Handler()
        assert hasattr(handler, func_name)
        assert inspect.ismethod(getattr(handler, func_name))


def test_add_symbolic_state_for_instruction_func_interface():
    return func_test_app_handler_has_func('add_symbolic_state_for_instruction')


def test_process_func_interface():
    return func_test_app_handler_has_func('process')
