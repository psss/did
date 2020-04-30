import tmt

class ReportDisplay(tmt.steps.report.ReportPlugin):
    """
    Show test results on the terminal

    Give a concise summary of test results directly on the terminal.
    List individual test results in verbose mode.
    """

    # Supported methods
    _methods = [tmt.steps.Method(name='display', doc=__doc__, order=50)]

    def go(self):
        """ Discover available tests """
        super().go()
        # Show individual test results only in verbose mode
        if not self.opt('verbose'):
            return
        for result in self.step.plan.execute.results():
            self.verbose(result.show(), shift=1)
