# coding: utf-8

""" Execute Step Classes """

import tmt


class Execute(tmt.steps.Step):
    """ Run the tests (using the specified framework and its settings) """
    name = 'execute'

    def __init__(self, data, plan):
        """ Initialize the execute step """
        super(Execute, self).__init__(data, plan)
        if not 'how' in self.data:
            self.data['how'] = 'shell'

    def show(self):
        """ Show execute details """
        super(Execute, self).show(keys=['how', 'script', 'isolate'])
