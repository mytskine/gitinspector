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

from .. import format, gravatar, terminal
from .. import responsibilities as resp
from .outputable import Outputable

RESPONSIBILITIES_INFO_TEXT = lambda: _("The following responsibilities, by author, were found in the current "
                                       "revision of the repository (comments are excluded from the line count, "
                                       "if possible)")
MOSTLY_RESPONSIBLE_FOR_TEXT = lambda: _("is mostly responsible for")

class ResponsibilitiesOutput(Outputable):
    output_order = 500

    def __init__(self, runner):
        Outputable.__init__(self)
        self.changes = runner.changes
        self.blame = runner.blames
        self.display = bool(runner.changes.all_commits()) and bool(runner.config.responsibilities)
        self.out = runner.out

    def output_text(self):
        self.out.writeln("\n" + textwrap.fill(RESPONSIBILITIES_INFO_TEXT() + ":",
                                              width=terminal.get_size()[0]))

        for committer in self.blame.committers_by_responsibilities():
            responsibilities = sorted(((resp[1], resp[0])
                                       for resp in resp.Responsibilities.get(self.blame, committer)),
                                      reverse=True)

            if responsibilities:
                self.out.writeln("\n" + committer[0] + " " + MOSTLY_RESPONSIBLE_FOR_TEXT() + ":")

                for j, entry in enumerate(responsibilities):
                    (width, _unused) = terminal.get_size()
                    width -= 7

                    self.out.write(str(entry[0]).rjust(6) + " ")
                    self.out.writeln("...%s" % entry[1][-width+3:] if len(entry[1]) > width else entry[1])

                    if j >= 9:
                        break

    def output_html(self):
        resp_xml = ""
        for committer in self.blame.committers_by_responsibilities():
            responsibilities = sorted(((resp[1], resp[0])
                                       for resp in resp.Responsibilities.get(self.blame, committer)),
                                      reverse=True)
            if responsibilities:
                resp_xml += "<div>"
                color = self.changes.committers[committer]["color"]
                rect = ("<svg width='16' height='16'><rect x='5' y='5' "
                        "width='16' height='16' fill='{0}'></rect></svg>").\
                        format(color)

                resp_xml += "<h4>{0} &nbsp; {1} {2}</h4>".\
                    format(rect, committer[0], MOSTLY_RESPONSIBLE_FOR_TEXT())

                for j, entry in enumerate(responsibilities):
                    resp_xml += "<div" + (" class=\"odd\">" if j % 2 == 1 else ">") + \
                        entry[1] + " (" + str(entry[0]) + " eloc)</div>"
                    if j >= 9:
                        break

                resp_xml += "</div>"

        temp_file = os.path.join(os.path.dirname(__file__),
                                 "../templates/responsibilities_output.html")
        with open(temp_file, 'r') as infile:
            src = string.Template( infile.read() )
            self.out.write(src.substitute(
                resp_info_text=RESPONSIBILITIES_INFO_TEXT(),
                resp_inner_text=resp_xml,
            ))

    def output_json(self):
        message_json = "\t\t\t\"message\": \"" + RESPONSIBILITIES_INFO_TEXT() + "\",\n"
        resp_json = ""

        for committer in self.blame.committers_by_responsibilities():
            responsibilities = sorted(((resp[1], resp[0])
                                       for resp in resp.Responsibilities.get(self.blame, committer)),
                                      reverse=True)

            if responsibilities:
                (author_name, author_email) = committer

                resp_json += "{\n"
                resp_json += "\t\t\t\t\"name\": \"" + author_name + "\",\n"
                resp_json += "\t\t\t\t\"email\": \"" + author_email + "\",\n"
                resp_json += "\t\t\t\t\"gravatar\": \"" + gravatar.get_url(author_email) + "\",\n"
                resp_json += "\t\t\t\t\"files\": [\n\t\t\t\t"

                for j, entry in enumerate(responsibilities):
                    resp_json += "{\n"
                    resp_json += "\t\t\t\t\t\"name\": \"" + entry[1] + "\",\n"
                    resp_json += "\t\t\t\t\t\"rows\": " + str(entry[0]) + "\n"
                    resp_json += "\t\t\t\t},"

                    if j >= 9:
                        break

                resp_json = resp_json[:-1]
                resp_json += "]\n\t\t\t},"

        resp_json = resp_json[:-1]
        self.out.write(",\n\t\t\"responsibilities\": {\n" + message_json + "\t\t\t\"authors\": [\n\t\t\t" +
                       resp_json + "]\n\t\t}")

    def output_xml(self):
        message_xml = "\t\t<message>" + RESPONSIBILITIES_INFO_TEXT() + "</message>\n"
        resp_xml = ""

        for committer in self.blame.committers_by_responsibilities():
            (author_name, author_email) = committer
            responsibilities = sorted(((resp[1], resp[0])
                                       for resp in resp.Responsibilities.get(self.blame, committer)),
                                      reverse=True)
            if responsibilities:
                resp_xml += "\t\t\t<author>\n"
                resp_xml += "\t\t\t\t<name>" + author_name + "</name>\n"
                resp_xml += "\t\t\t\t<email>" + author_email + "</email>\n"
                resp_xml += "\t\t\t\t<gravatar>" + gravatar.get_url(author_email) + "</gravatar>\n"
                resp_xml += "\t\t\t\t<files>\n"

                for j, entry in enumerate(responsibilities):
                    resp_xml += "\t\t\t\t\t<file>\n"
                    resp_xml += "\t\t\t\t\t\t<name>" + entry[1] + "</name>\n"
                    resp_xml += "\t\t\t\t\t\t<rows>" + str(entry[0]) + "</rows>\n"
                    resp_xml += "\t\t\t\t\t</file>\n"

                    if j >= 9:
                        break

                resp_xml += "\t\t\t\t</files>\n"
                resp_xml += "\t\t\t</author>\n"

        self.out.writeln("\t<responsibilities>\n" + message_xml + "\t\t<authors>\n" + resp_xml +
                         "\t\t</authors>\n\t</responsibilities>")
