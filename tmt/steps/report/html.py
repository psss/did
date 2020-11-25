import os
import os.path

import click
import jinja2
import webbrowser

import tmt


HTML_TEMPLATE = """
<!DOCTYPE html>
<head>
    <title>Test results of {{ plan.name }}</title>
    <style>
        td.pass {
            background: green;
        }
        td.fail{
            background: red;
        }
        td.info {
            background: blue;
        }
        td.warn {
            background: yellow;
        }
        td.error {
            background: magenta;
        }
    </style>
</head>
<body>

<h1>{{ plan.name }}</h1>
{% if plan.summary %}<h2>{{ plan.summary }}</h2>{% endif %}
{% if results %}
<table>
    <thead>
        <tr>
            <th>Result</th>
            <th>Test</th>
            <th>Logs</th>
        </tr>
    </thead>
    {% for result in results %}
    <tr class="result {{ loop.cycle('odd', 'even') }}">
        <td class="result {{ result.result|e }}"> {{ result.result|e }}</td>
        <td class="name"> {{ result.name|e }}</td>
        <td class="log">
        {% for log in result.log %}
            <a href="{{ base_dir }}/{{ log }}">{{ log | basename }}</a>
        {% endfor %}
        </td>
    </tr>
    {% endfor %}
</table>
{% else %}
<b>No test results found.</b>
{% endif %}
</body>
</html>
""".strip()


class ReportHTML(tmt.steps.report.ReportPlugin):
    """ Format test results into an html report """

    # Supported methods
    _methods = [tmt.steps.Method(name='html', doc=__doc__, order=50)]

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for the html report """
        return [
            click.option(
                '-o', '--open', is_flag=True,
                help='Open results in your preferred web browser.'),
            ] + super().options(how)

    def go(self):
        """ Process results """
        super().go()

        # Prepare the template
        environment = jinja2.Environment()
        environment.filters["basename"] = lambda x: os.path.basename(x)
        template = environment.from_string(HTML_TEMPLATE)

        # Write the report
        filename = 'index.html'
        self.write(
            filename,
            data=template.render(
                results=self.step.plan.execute.results(),
                base_dir=self.step.plan.execute.workdir,
                plan=self.step.plan))

        # Nothing more to do in dry mode
        if self.opt('dry'):
            return

        # Show output file path
        target = os.path.join(self.workdir, filename)
        self.info("output", target, color='yellow')
        if not self.opt('open'):
            return

        # Open target in webbrowser
        try:
            if webbrowser.open(f"file://{target}", new=0):
                self.info(
                    'open', 'Successfully opened in the web browser.',
                    color='green')
                return
            self.fail(f"Failed to open the web browser.")
        except Exception as error:
            self.fail(f"Failed to open the web browser: {error}")

        raise tmt.utils.ReportError("Unable to open the web browser.")
