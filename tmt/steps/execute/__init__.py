# coding: utf-8

""" Execute Step Classes """

import tmt


class Execute(tmt.steps.Step):
    """ Run the tests (using the specified framework and its settings) """

    def __init__(self, data, plan):
        """ Initialize the execute step """
        super(Execute, self).__init__(data, plan)
        if len(self.data) > 1:
            raise tmt.utils.SpecificationError(
                "Multiple execute steps defined in '{}'.".format(self.plan))

    def show(self):
        """ Show execute details """
        super(Execute, self).show(keys=['how', 'script', 'isolate'])
