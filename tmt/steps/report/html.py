import os
import os.path
import webbrowser

import click

import tmt

HTML_TEMPLATE = """
<!DOCTYPE html>
<head>
    <title>Test results of {{ plan.name }}</title>
    <style>
        body {
            background: #eee;
            padding: 3em;
            font-family: sans-serif;
            text-align: center;
        }

        div {
            display: inline-block;
            text-align: left;
            background: white;
            padding: 2em;
            border-radius: 1ex;
        }

        a {
            color: #29f;
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }

        h1 {
            color: #aaa;
            margin: 0ex 0ex 1ex 7px;
        }

        h2 {
            color: #555;
            margin: -1ex 0ex 1ex 7px;
        }

        p.footer {
            margin: 30px 7px 0px 7px;
        }

        table {
            border-spacing: 7px;
        }

        td, th {
            padding: 0.7ex 1em;
        }

        td {
            background: #f8f8f8;
            border-radius: 0.5ex;
        }

        td.result {
            text-align: center;
            text-shadow: 0px 0px 5px #555;
            color: white;
        }

        td.pass {
            background: #0a0;
        }

        td.fail {
            background: #d30;
        }

        td.info {
            background: #58d;
        }

        td.warn {
            background: #fc5;
        }

        td.error {
            background: #b4d;
        }

        td.log {
            word-spacing: 1ex;
        }

        td.note {
            color: #c00;
        }
    </style>
</head>
<body>
<div>
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
            <a href="{{ base_dir | urlencode }}/{{ log | urlencode }}">{{ log | basename }}</a>
        {% endfor %}
        </td>
        {% if result.note %}
        <td class="note">{{ result.note|e }}</td>
        {% endif %}
    </tr>
    {% endfor %}
</table>
{% else %}
<b>No test results found.</b>
{% endif %}
<p class="footer">
    Links: <a href="{{ plan.my_run.workdir | urlencode }}/log.txt">full debug log</a>
</p>
</div>
</body>
</html>
""".strip()


def import_jinja2():
    """
    Import jinja2 module only when needed

    Until we have a separate package for each plugin.
    """
    global jinja2
    try:
        import jinja2
    except ImportError:
        raise tmt.utils.ReportError(
            "Missing 'jinja2', fixable by 'pip install tmt[report-html]'")


class ReportHtml(tmt.steps.report.ReportPlugin):
    """
    Format test results into an html report

    Example config:

        report:
            how: html
            open: true
    """

    # Supported methods
    _methods = [tmt.steps.Method(name='html', doc=__doc__, order=50)]

    # Supported keys
    _keys = ["open"]

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

        import_jinja2()

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
        if not self.get('open'):
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
