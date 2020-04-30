import re
import fmf
import tmt
import click


class Report(tmt.steps.Step):
    """ Provide test results overview and send reports """

    # Default implementation for report is display
    how = 'display'

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        super().wake()

        # Choose the right plugin and wake it up
        for data in self.data:
            plugin = ReportPlugin.delegate(self, data)
            plugin.wake()
            self._plugins.append(plugin)

        # Nothing more to do if already done
        if self.status() == 'done':
            self.debug(
                'Report wake up complete (already done before).', level=2)
        # Save status and step data (now we know what to do)
        else:
            self.status('todo')
            self.save()

    def show(self):
        """ Show discover details """
        for data in self.data:
            ReportPlugin.delegate(self, data).show()

    def summary(self):
        """ Give a concise report summary """
        # Prepare stats
        stats = {}
        for result in self.plan.execute.results():
            try:
                stats[result.result] += 1
            except KeyError:
                stats[result.result] = 1

        # Prepare comments
        comments = []
        if stats.get('pass'):
            passed = ' ' + click.style('passed', fg='green')
            comments.append(fmf.utils.listed(stats['pass'], 'test') + passed)
        if stats.get('fail'):
            failed = ' ' + click.style('failed', fg='red')
            comments.append(fmf.utils.listed(stats['fail'], 'test') + failed)
        if stats.get('info'):
            count, comment = fmf.utils.listed(stats['info'], 'info').split()
            comments.append(count + ' ' + click.style(comment, fg='blue'))
        if stats.get('warn'):
            count, comment = fmf.utils.listed(stats['warn'], 'warn').split()
            comments.append(count + ' ' + click.style(comment, fg='yellow'))
        if stats.get('error'):
            count, comment = fmf.utils.listed(stats['error'], 'error').split()
            comments.append(count + ' ' + click.style(comment, fg='magenta'))

        # Give the summary
        comments = comments or ['no results found']
        self.info('summary', fmf.utils.listed(comments), 'green', shift=1)

    def go(self):
        """ Report the guests """
        super().go()

        # Nothing more to do if already done
        if self.status() == 'done':
            self.info('status', 'done', 'green', shift=1)
            self.summary()
            return

        # Perform the reporting
        for plugin in self.plugins():
            plugin.go()

        # Give a summary, update status and save
        self.summary()
        self.status('done')
        self.save()


class ReportPlugin(tmt.steps.Plugin):
    """ Common parent of report plugins """

    # List of all supported methods aggregated from all plugins
    _supported_methods = []

    @classmethod
    def base_command(cls, method_class=None, usage=None):
        """ Create base click command (common for all report plugins) """

        # Prepare general usage message for the step
        if method_class:
            usage = Report.usage(method_overview=usage)

        # Create the command
        @click.command(cls=method_class, help=usage)
        @click.pass_context
        @click.option(
            '-h', '--how', metavar='METHOD',
            help='Use specified method for results reporting.')
        def report(context, **kwargs):
            context.obj.steps.add('report')
            Report._save_context(context)

        return report
