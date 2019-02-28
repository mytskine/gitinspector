# coding: utf-8
#
# Copyright © 2012-2015 Ejwa Software. All rights reserved.
#
# This file is part of gitinspector.
#
# gitinspector is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gitinspector is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gitinspector. If not, see <http://www.gnu.org/licenses/>.

import os
import string

from ..changes import FileDiff
from ..metrics import (__metric_eloc__, METRIC_CYCLOMATIC_COMPLEXITY_THRESHOLD, METRIC_CYCLOMATIC_COMPLEXITY_DENSITY_THRESHOLD)
from .outputable import Outputable

ELOC_INFO_TEXT = lambda: _("The following files are suspiciously big (in order of severity)")
CYCLOMATIC_COMPLEXITY_TEXT = lambda: _("The following files have an elevated cyclomatic complexity (in order of severity)")
CYCLOMATIC_COMPLEXITY_DENSITY_TEXT = lambda: _("The following files have an elevated cyclomatic complexity density " \
                    "(in order of severity)")
METRICS_MISSING_INFO_TEXT = lambda: _("No metrics violations were found in the repository")

METRICS_VIOLATION_SCORES = [[1.0, "minimal"], [1.25, "minor"], [1.5, "medium"], [2.0, "bad"], [3.0, "severe"]]


def __get_metrics_score__(ceiling, value):
    for i in reversed(METRICS_VIOLATION_SCORES):
        if value > ceiling * i[0]:
            return i[1]
    return ""


class MetricsOutput(Outputable):
    output_order = 400

    def __init__(self, runner):
        Outputable.__init__(self)
        self.metrics = runner.metrics
        self.display = bool(runner.changes.all_commits()) and bool(runner.config.metrics)
        self.out = runner.out

    def output_text(self):
        if not self.metrics.eloc and not self.metrics.cyclomatic_complexity and \
           not self.metrics.cyclomatic_complexity_density:
            self.out.writeln("\n" + METRICS_MISSING_INFO_TEXT() + ".")

        if self.metrics.eloc:
            self.out.writeln("\n" + ELOC_INFO_TEXT() + ":")
            for i in sorted(set([(j, i) for (i, j) in self.metrics.eloc.items()]), reverse=True):
                self.out.writeln(_("{0} ({1} estimated lines of code)").format(i[1], str(i[0])))

        if self.metrics.cyclomatic_complexity:
            self.out.writeln("\n" + CYCLOMATIC_COMPLEXITY_TEXT() + ":")
            for i in sorted(set([(j, i) for (i, j) in self.metrics.cyclomatic_complexity.items()]), reverse=True):
                self.out.writeln(_("{0} ({1} in cyclomatic complexity)").format(i[1], str(i[0])))

        if self.metrics.cyclomatic_complexity_density:
            self.out.writeln("\n" + CYCLOMATIC_COMPLEXITY_DENSITY_TEXT() + ":")
            for i in sorted(set([(j, i) for (i, j) in self.metrics.cyclomatic_complexity_density.items()]), reverse=True):
                self.out.writeln(_("{0} ({1:.3f} in cyclomatic complexity density)").format(i[1], i[0]))

    def output_html(self):
        if not self.metrics.eloc and not self.metrics.cyclomatic_complexity and \
           not self.metrics.cyclomatic_complexity_density:
            metrics_info_str = METRICS_MISSING_INFO_TEXT()
        else:
            metrics_info_str = ""

        metrics_eloc_dict = []
        if self.metrics.eloc:
            metrics_items = sorted(set([(j, i) for (i, j) in self.metrics.eloc.items()]), reverse=True)
            for num, i in enumerate(metrics_items):
                metrics_eloc_dict.append({
                    "severity": __get_metrics_score__(__metric_eloc__[FileDiff.get_extension(i[1])], i[0]),
                    "name": i[1],
                    "score": _("{0} estimated lines of code").format(i[0]),
                })

        metrics_cyclo_dict = []
        if self.metrics.cyclomatic_complexity:
            cyclo_items = sorted(set([(j, i) for (i, j) in self.metrics.cyclomatic_complexity.items()]), reverse=True)
            for num, i in enumerate(cyclo_items):
                metrics_cyclo_dict.append({
                    "severity": __get_metrics_score__(METRIC_CYCLOMATIC_COMPLEXITY_THRESHOLD, i[0]),
                    "name": i[1],
                    "score": _("{0} in cyclomatic complexity").format(i[0]),
                })

        metrics_comp_dict = []
        if self.metrics.cyclomatic_complexity_density:
            dens_items = sorted(set([(j, i) for (i, j) in self.metrics.cyclomatic_complexity_density.items()]), reverse=True)
            for num, i in enumerate(dens_items):
                metrics_comp_dict.append({
                    "severity": __get_metrics_score__(METRIC_CYCLOMATIC_COMPLEXITY_DENSITY_THRESHOLD, i[0]),
                    "name": i[1],
                    "score": _("{0:.3f} in cyclomatic complexity density").format(i[0]),
                })

        temp_file = os.path.join(os.path.dirname(__file__),
                                 "../templates/metrics_output.html")
        with open(temp_file, 'r') as infile:
            src = string.Template( infile.read() )
            self.out.write(src.substitute(
                # metrics_no_info_text=metrics_info_str,
                metrics_eloc_head=ELOC_INFO_TEXT(),
                metrics_eloc=metrics_eloc_dict,
                metrics_cyclo_head=CYCLOMATIC_COMPLEXITY_TEXT(),
                metrics_cyclo=metrics_cyclo_dict,
                metrics_comp_head= CYCLOMATIC_COMPLEXITY_DENSITY_TEXT(),
                metrics_comp=metrics_comp_dict,
            ))

    def output_json(self):
        if not self.metrics.eloc and not self.metrics.cyclomatic_complexity and not self.metrics.cyclomatic_complexity_density:
            self.out.write(",\n\t\t\"metrics\": {\n\t\t\t\"message\": \"" + METRICS_MISSING_INFO_TEXT() +
                           "\"\n\t\t}")
        else:
            eloc_json = ""

            if self.metrics.eloc:
                for i in sorted(set([(j, i) for (i, j) in self.metrics.eloc.items()]), reverse=True):
                    eloc_json += "{\n\t\t\t\t\"type\": \"estimated-lines-of-code\",\n"
                    eloc_json += "\t\t\t\t\"file_name\": \"" + i[1] + "\",\n"
                    eloc_json += "\t\t\t\t\"value\": " + str(i[0]) + "\n"
                    eloc_json += "\t\t\t},"
                # Removing the last trailing ','
                if not self.metrics.cyclomatic_complexity:
                    eloc_json = eloc_json[:-1]

            if self.metrics.cyclomatic_complexity:
                for i in sorted(set([(j, i) for (i, j) in self.metrics.cyclomatic_complexity.items()]), reverse=True):
                    eloc_json += "{\n\t\t\t\t\"type\": \"cyclomatic-complexity\",\n"
                    eloc_json += "\t\t\t\t\"file_name\": \"" + i[1] + "\",\n"
                    eloc_json += "\t\t\t\t\"value\": " + str(i[0]) + "\n"
                    eloc_json += "\t\t\t},"
                # Removing the last trailing ','
                if not self.metrics.cyclomatic_complexity_density:
                    eloc_json = eloc_json[:-1]

            if self.metrics.cyclomatic_complexity_density:
                for i in sorted(set([(j, i) for (i, j) in self.metrics.cyclomatic_complexity_density.items()]), reverse=True):
                    eloc_json += "{\n\t\t\t\t\"type\": \"cyclomatic-complexity-density\",\n"
                    eloc_json += "\t\t\t\t\"file_name\": \"" + i[1] + "\",\n"
                    eloc_json += "\t\t\t\t\"value\": {0:.3f}\n".format(i[0])
                    eloc_json += "\t\t\t},"
                # Removing the last trailing ','
                eloc_json = eloc_json[:-1]

            self.out.write(",\n\t\t\"metrics\": {\n\t\t\t\"violations\": [\n\t\t\t" + eloc_json +
                           "]\n\t\t}")

    def output_xml(self):
        if not self.metrics.eloc and not self.metrics.cyclomatic_complexity and not self.metrics.cyclomatic_complexity_density:
            self.out.writeln("\t<metrics>\n\t\t<message>" + METRICS_MISSING_INFO_TEXT() +
                             "</message>\n\t</metrics>")
        else:
            eloc_xml = ""

            if self.metrics.eloc:
                for i in sorted(set([(j, i) for (i, j) in self.metrics.eloc.items()]), reverse=True):
                    eloc_xml += "\t\t\t<estimated-lines-of-code>\n"
                    eloc_xml += "\t\t\t\t<file-name>" + i[1] + "</file-name>\n"
                    eloc_xml += "\t\t\t\t<value>" + str(i[0]) + "</value>\n"
                    eloc_xml += "\t\t\t</estimated-lines-of-code>\n"

            if self.metrics.cyclomatic_complexity:
                for i in sorted(set([(j, i) for (i, j) in self.metrics.cyclomatic_complexity.items()]), reverse=True):
                    eloc_xml += "\t\t\t<cyclomatic-complexity>\n"
                    eloc_xml += "\t\t\t\t<file-name>" + i[1] + "</file-name>\n"
                    eloc_xml += "\t\t\t\t<value>" + str(i[0]) + "</value>\n"
                    eloc_xml += "\t\t\t</cyclomatic-complexity>\n"

            if self.metrics.cyclomatic_complexity_density:
                for i in sorted(set([(j, i) for (i, j) in self.metrics.cyclomatic_complexity_density.items()]), reverse=True):
                    eloc_xml += "\t\t\t<cyclomatic-complexity-density>\n"
                    eloc_xml += "\t\t\t\t<file-name>" + i[1] + "</file-name>\n"
                    eloc_xml += "\t\t\t\t<value>{0:.3f}</value>\n".format(i[0])
                    eloc_xml += "\t\t\t</cyclomatic-complexity-density>\n"

            self.out.writeln("\t<metrics>\n\t\t<violations>\n" + eloc_xml + "\t\t</violations>\n\t</metrics>")
