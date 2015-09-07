#!/usr/bin/env python
# coding: utf-8
# Author: "Chris Ward" <cward@redhat.com>

'''
Mr.Bob Hooks

src: http://mrbob.readthedocs.org/en/latest/api.html#module-mrbob.hooks
'''


def pre_render(configurator):
    pass


def post_render(configurator):
    # remove unnecessary __init__.py, hooks.py
    pass


def pre_ask_question(configurator, question):
    pass


def post_ask_question(configurator, question, answer):
    pass


def set_name_email(configurator, question, answer):
    '''
    prepare "Full Name" <email@eg.com>" string
    '''
    name = configurator.variables['author.name']
    configurator.variables['author.name_email'] = '"{0}" <{1}>'.format(
        name, answer)
    return answer
