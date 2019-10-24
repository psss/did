# coding: utf-8

""" Report Step Classes """

import tmt


class Report(tmt.steps.Step):
    """ Provide an overview of test results and send notifications """

    # Default implementation for report is display
    how = 'display'
