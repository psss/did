import os

import jinja2
import os.path
import subprocess

import tmt
import click

class ReportHTML(tmt.steps.report.ReportPlugin):
    """
    Write HTML report of  results
    """

    # Supported methods
    _methods = [tmt.steps.Method(name='html', doc=__doc__, order=50)]

    HTML_TEMPLATE = """
<!DOCTYPE html>
<head>
    <title>Test results of {{ plan_name }}</title>
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

{% if results %}
<table>
    <thead>
        <td>Result</td>
        <td>Name</td>
        <td>Log files </td>
    </thead>
    {% for res in results %}
    <tr class="result {{ loop.cycle('odd', 'even') }}">
        <td class="result {{ res.result|e }}"> {{ res.result|e }}</td>
        <td class="name"> {{ res.name|e }}</td>
        <td class="log">
        {% for log in res.log %}
            <a href="{{base_dir }}/{{ log }}">{{ log | basename }}</a>
        {% endfor %}
        </td>
    </tr>
    {% endfor %}
</table>
{% else %}
<b>No results found</b>
{% endif %}
</body>
</html>
""".strip()

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for connect """
        return [
            click.option(
                '--open', is_flag=True,
                help='Open results in your preferred web browser'),
            ] + super().options(how)

    def go(self):
        """ Process results """
        super().go()

        env = jinja2.Environment()
        env.filters["basename"] = lambda x: os.path.basename(x)

        template_to_render = env.from_string(self.HTML_TEMPLATE)

        file_name = 'index.html'
        wrote = self.write(file_name, data=template_to_render.render(
                results=self.step.plan.execute.results(),
                base_dir=self.step.plan.execute.workdir,
                plan_name=self.step.plan.name
                ))
        if wrote is None: # --dry mode
            return

        target = os.path.join(self.workdir, file_name)
        self.info("Wrote report to", target)
        if not self.opt('open'):
            return

        # opening target using xdg-open, fallback to $BROWSER
        try:
            process = subprocess.Popen(["xdg-open", target])
            return
        except OSError as err:
            self.debug("Attempt to open via xdg-open not successful")
            self.debug(f"Returned exception: {err}")
        try:
            browser = os.environ.get('BROWSER')
            if not browser:
                browser = 'unset'
                raise KeyError("BROWSER empty")
            process = subprocess.Popen([browser, target])
            return
        except (OSError, KeyError) as err:
            self.debug(f"Attempt to open via $BROWSER ({browser}) not successful")
            self.debug(f"Returned exception: {err}")


        self.fail("Wasn't able to open browser, xdg-open nor $BROWSER worked")
