# coding: utf-8

""" Base Executor Provider Class """

from tmt.steps import Plugin


class ExecutorBase(Plugin):
    """ This is base executor class """

    def go(self, plan_workdir):
        """ Run tests """
        super(ExecutorBase, self).go()

    # API
    def requires(self):
        """ Returns packages required to run tests"""
        pass

    def results(self):
        """ Returns results from executed tests """
        pass
