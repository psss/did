# coding: utf-8

""" Provision Step Classes """

import tmt


class Provision(tmt.steps.Step):
    """ Provision an environment for testing (or use localhost) """
    name = 'provision'
