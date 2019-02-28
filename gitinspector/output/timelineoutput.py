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
import textwrap

from .. import format, gravatar, terminal, timeline
from .outputable import Outputable

MODIFIED_ROWS_TEXT = lambda: _("Modified Rows:")
TIMELINE_INFO_TEXT = lambda: _("The following history timeline has been gathered from the repository")


class TimelineOutput(Outputable):
    output_order = 300

    def __init__(self, runner):
        Outputable.__init__(self)
        self.changes = runner.changes
        self.useweeks = runner.config.weeks
        self.display = bool(runner.changes.all_commits()) and \
            bool(runner.config.timeline) and bool(runner.config.legacy)
        self.out = runner.out

    def output_text(self):
        if self.changes.all_commits():
            self.out.writeln("\n" + textwrap.fill(TIMELINE_INFO_TEXT() +
                                                  ":", width=terminal.get_size()[0]))

            timeline_data = timeline.TimelineData(self.changes, self.useweeks)
            periods = timeline_data.get_periods()
            names = timeline_data.get_committers()
            (width, _unused) = terminal.get_size()
            max_periods_per_row = int((width - 21) / 11)

            for i in range(0, len(periods), max_periods_per_row):
                self.__output_row__text__(timeline_data, periods[i:i+max_periods_per_row], names)

    def output_html(self):
        timeline_xml = ""

        if self.changes.all_commits():
            timeline_data = timeline.TimelineData(self.changes, self.useweeks)

            periods = timeline_data.get_periods()
            names = timeline_data.get_committers()
            max_periods_per_row = 8

            for i in range(0, len(periods), max_periods_per_row):
                timeline_xml += self.__output_row__html__(timeline_data,
                                                          periods[i:i+max_periods_per_row],
                                                          names)

        temp_file = os.path.join(os.path.dirname(__file__),
                                 "../templates/timeline_output.html")
        with open(temp_file, 'r') as infile:
            src = string.Template( infile.read() )
            self.out.write(src.substitute(
                tim_info_text=TIMELINE_INFO_TEXT(),
                tim_inner_text=timeline_xml,
            ))

    def output_json(self):
        if self.changes.all_commits():
            message_json = "\t\t\t\"message\": \"" + TIMELINE_INFO_TEXT() + "\",\n"
            timeline_json = ""
            periods_json = "\t\t\t\"period_length\": \"{0}\",\n".format("week" if self.useweeks else "month")
            periods_json += "\t\t\t\"periods\": [\n\t\t\t"

            timeline_data = timeline.TimelineData(self.changes, self.useweeks)
            names = timeline_data.get_committers()

            for period in timeline_data.get_periods():
                name_json = "\t\t\t\t\"name\": \"" + str(period) + "\",\n"
                authors_json = "\t\t\t\t\"authors\": [\n\t\t\t\t"

                for name in names:
                    if timeline_data.is_author_in_period(period, name[0]):
                        multiplier = timeline_data.get_multiplier(period, 24)
                        signs = timeline_data.get_author_signs_in_period(name[0], period, multiplier)
                        signs_str = (signs[1] * "-" + signs[0] * "+")

                        if not signs_str:
                            signs_str = "."

                        authors_json += "{\n\t\t\t\t\t\"name\": \"" + name[0] + "\",\n"
                        authors_json += "\t\t\t\t\t\"email\": \"" + name[1] + "\",\n"
                        authors_json += "\t\t\t\t\t\"gravatar\": \"" + gravatar.get_url(name[1]) + "\",\n"
                        authors_json += "\t\t\t\t\t\"work\": \"" + signs_str + "\"\n\t\t\t\t},"
                # Removing the last trailing ','
                authors_json = authors_json[:-1]

                authors_json += "],\n"
                modified_rows_json = "\t\t\t\t\"modified_rows\": " + \
                            str(timeline_data.get_total_changes_in_period(period)[2]) + "\n"
                timeline_json += "{\n" + name_json + authors_json + modified_rows_json + "\t\t\t},"
            # Removing the last trailing ','
            timeline_json = timeline_json[:-1]

            self.out.write(",\n\t\t\"timeline\": {\n" + message_json + periods_json + timeline_json +
                           "]\n\t\t}")

    def output_xml(self):
        if self.changes.all_commits():
            message_xml = "\t\t<message>" + TIMELINE_INFO_TEXT() + "</message>\n"
            timeline_xml = ""
            periods_xml = "\t\t<periods length=\"{0}\">\n".format("week" if self.useweeks else "month")

            timeline_data = timeline.TimelineData(self.changes, self.useweeks)
            names = timeline_data.get_committers()

            for period in timeline_data.get_periods():
                name_xml = "\t\t\t\t<name>" + str(period) + "</name>\n"
                authors_xml = "\t\t\t\t<authors>\n"

                for name in names:
                    if timeline_data.is_author_in_period(period, name[0]):
                        multiplier = timeline_data.get_multiplier(period, 24)
                        signs = timeline_data.get_author_signs_in_period(name[0], period, multiplier)
                        signs_str = (signs[1] * "-" + signs[0] * "+")

                        if not signs_str:
                            signs_str = "."

                        authors_xml += "\t\t\t\t\t<author>\n\t\t\t\t\t\t<name>" + name[0] + "</name>\n"
                        authors_xml += "\t\t\t\t\t\t<email>" + name[1] + "</email>\n"
                        authors_xml += "\t\t\t\t\t\t<gravatar>" + gravatar.get_url(name[1]) + "</gravatar>\n"
                        authors_xml += "\t\t\t\t\t\t<work>" + signs_str + "</work>\n\t\t\t\t\t</author>\n"

                authors_xml += "\t\t\t\t</authors>\n"
                modified_rows_xml = "\t\t\t\t<modified_rows>" + \
                            str(timeline_data.get_total_changes_in_period(period)[2]) + "</modified_rows>\n"
                timeline_xml += "\t\t\t<period>\n" + name_xml + authors_xml + modified_rows_xml + "\t\t\t</period>\n"

            self.out.writeln("\t<timeline>\n" + message_xml + periods_xml + timeline_xml +
                             "\t\t</periods>\n\t</timeline>")

    def __output_row__text__(self, timeline_data, periods, names):
        self.out.write("\n" + terminal.__bold__ + terminal.ljust(_("Author"), 20) + " ")

        for period in periods:
            self.out.write(terminal.rjust(period, 10) + " ")

        self.out.writeln(terminal.__normal__)

        for name in names:
            if timeline_data.is_author_in_periods(periods, name[0]):
                self.out.write(terminal.ljust(name[0], 20)[0:20 - terminal.get_excess_column_count(name[0])])

                for period in periods:
                    multiplier = timeline_data.get_multiplier(period, 9)
                    signs = timeline_data.get_author_signs_in_period(name[0], period, multiplier)
                    signs_str = (signs[1] * "-" + signs[0] * "+")
                    self.out.write(("." if (timeline_data.is_author_in_period(period, name[0]) and \
                                            not signs_str) else signs_str).rjust(11))
                self.out.writeln("")

        terminal.writeb(self.out, terminal.ljust(MODIFIED_ROWS_TEXT(), 20))

        for period in periods:
            total_changes = str(timeline_data.get_total_changes_in_period(period)[2])

            if hasattr(total_changes, 'decode'):
                total_changes = total_changes.decode("utf-8", "replace")

            self.out.write(terminal.rjust(total_changes, 11))

        self.out.writeln("")

    def __output_row__html__(self, timeline_data, periods, names):
        timeline_xml = "<table class=\"git full\"><thead><tr><th>" + _("Author") + "</th>"

        for period in periods:
            timeline_xml += "<th>" + str(period) + "</th>"

        timeline_xml += "</tr></thead><tbody>"

        i = 0
        for name in names:
            if timeline_data.is_author_in_periods(periods, name[0]):
                timeline_xml += "<tr" + (" class=\"odd\">" if i % 2 == 1 else ">")

                if format.get_selected() == "html":
                    timeline_xml += "<td><img src=\"{0}\"/>{1}</td>".format(gravatar.get_url(name[1]), name[0])
                else:
                    timeline_xml += "<td>" + name[0] + "</td>"

                for period in periods:
                    multiplier = timeline_data.get_multiplier(period, 18)
                    signs = timeline_data.get_author_signs_in_period(name[0], period, multiplier)
                    signs_str = (signs[1] * "<div class=\"remove\">&nbsp;</div>" + signs[0] * "<div class=\"insert\">&nbsp;</div>")

                    timeline_xml += "<td>" + \
                                    ("." if (timeline_data.is_author_in_period(period, name[0]) and not signs_str) else signs_str) + \
                                    "</td>"
                timeline_xml += "</tr>"
                i += 1

        timeline_xml += "<tfoot><tr><td><strong>" + MODIFIED_ROWS_TEXT() + "</strong></td>"

        for period in periods:
            total_changes = timeline_data.get_total_changes_in_period(period)
            timeline_xml += "<td>" + str(total_changes[2]) + "</td>"

        timeline_xml += "</tr></tfoot></tbody></table>"
        return timeline_xml
