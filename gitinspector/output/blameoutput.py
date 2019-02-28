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

import json
import os
import string
import sys
import textwrap

from .. import format, gravatar, terminal
from ..blame import Blame
from .outputable import Outputable

BLAME_INFO_TEXT = lambda: _("Below are the number of rows from each author that have survived and "
                            "are still intact in the current revision")

class BlameOutput(Outputable):
    output_order = 200

    def __init__(self, runner):
        if runner.config.progress and format.is_interactive_format():
            print("")

        Outputable.__init__(self)
        self.changes = runner.changes
        self.blames = runner.blames
        self.display = bool(self.changes.all_commits())
        self.out = runner.out
        self.progress = runner.config.progress

    def output_html(self):
        blames_list = list(self.blames.get_summed_blames().items())
        blames_list.sort(key=lambda x: x[1].rows, reverse=True)
        total_blames = 0
        for i in blames_list:
            total_blames += i[1].rows

        data_array = []

        for entry in blames_list:
            (name, email) = entry[0]

            data_array.append({
                "avatar": "<img src=\"{0}\"/>".format(gravatar.get_url(email)),
                "color": self.changes.committers[entry[0]]["color"],
                "name":  name,
                "rows": entry[1].rows,
                "stability": round(Blame.get_stability(entry[0], entry[1].rows, self.changes),1),
                "age": round(float(entry[1].skew) / entry[1].rows,1),
                "comments": round(100.0 * entry[1].comments / entry[1].rows,2),
                "ownership": round(100.0 *  entry[1].rows / total_blames,2),
            })

        temp_file = os.path.join(os.path.dirname(__file__),
                                 "../templates/blames_output.html")
        with open(temp_file, 'r') as infile:
            src = string.Template( infile.read() )
            self.out.write(src.substitute(
                remains_data=str(data_array),
            ))

    def output_json(self):
        message_json = "\t\t\t\"message\": \"" + BLAME_INFO_TEXT() + "\",\n"
        blame_json = ""

        for i in sorted(self.blames.get_summed_blames().items()):
            (author_name, author_email) = i[0]

            name_json = "\t\t\t\t\"name\": \"" + author_name + "\",\n"
            email_json = "\t\t\t\t\"email\": \"" + author_email + "\",\n"
            gravatar_json = "\t\t\t\t\"gravatar\": \"" + gravatar.get_url(author_email) + "\",\n"
            rows_json = "\t\t\t\t\"rows\": " + str(i[1].rows) + ",\n"
            stability_json = ("\t\t\t\t\"stability\": " + "{0:.1f}".format(Blame.get_stability(i[0], i[1].rows,
                                                                                               self.changes)) + ",\n")
            age_json = ("\t\t\t\t\"age\": " + "{0:.1f}".format(float(i[1].skew) / i[1].rows) + ",\n")
            percentage_in_comments_json = ("\t\t\t\t\"percentage_in_comments\": " +
                                           "{0:.2f}".format(100.0 * i[1].comments / i[1].rows) + "\n")
            blame_json += ("{\n" + name_json + email_json + gravatar_json + rows_json + stability_json + age_json +
                           percentage_in_comments_json + "\t\t\t},")
        # Removing the last trailing ','
        blame_json = blame_json[:-1]

        self.out.write(",\n\t\t\"blame\": {\n" + message_json + "\t\t\t\"authors\": [\n\t\t\t" + blame_json + "]\n\t\t}")

    def output_text(self):
        if self.progress and sys.stdout.isatty() and format.is_interactive_format():
            terminal.clear_row()

        self.out.writeln(textwrap.fill(BLAME_INFO_TEXT() + ":", width=terminal.get_size()[0]) + "\n")
        terminal.writeb(self.out,
                        terminal.ljust(_("Author"), 21) + terminal.rjust(_("Rows"), 10) +
                        terminal.rjust(_("Stability"), 15) +
                        terminal.rjust(_("Age"), 13) + terminal.rjust(_("% in comments"), 20) + "\n")

        for i in sorted(self.blames.get_summed_blames().items()):
            committer = i[0]
            self.out.write(terminal.ljust(committer[0], 20)[0:20 - terminal.get_excess_column_count(committer[0])])
            self.out.write(str(i[1].rows).rjust(11))
            self.out.write("{0:.1f}".format(Blame.get_stability(i[0], i[1].rows, self.changes)).rjust(15))
            self.out.write("{0:.1f}".format(float(i[1].skew) / i[1].rows).rjust(13))
            self.out.writeln("{0:.2f}".format(100.0 * i[1].comments / i[1].rows).rjust(20))

    def output_xml(self):
        message_xml = "\t\t<message>" + BLAME_INFO_TEXT() + "</message>\n"
        blame_xml = ""

        for i in sorted(self.blames.get_summed_blames().items()):
            (author_name, author_email) = i[0]

            name_xml = "\t\t\t\t<name>" + author_name + "</name>\n"
            email_xml = "\t\t\t\t<email>" + author_email + "</email>\n"
            gravatar_xml = "\t\t\t\t<gravatar>" + gravatar.get_url(author_email) + "</gravatar>\n"
            rows_xml = "\t\t\t\t<rows>" + str(i[1].rows) + "</rows>\n"
            stability_xml = ("\t\t\t\t<stability>" + "{0:.1f}".format(Blame.get_stability(author_name, i[1].rows,
                                                                                          self.changes)) + "</stability>\n")
            age_xml = ("\t\t\t\t<age>" + "{0:.1f}".format(float(i[1].skew) / i[1].rows) + "</age>\n")
            percentage_in_comments_xml = ("\t\t\t\t<percentage-in-comments>" +
                                          "{0:.2f}".format(100.0 * i[1].comments / i[1].rows) + "</percentage-in-comments>\n")
            blame_xml += ("\t\t\t<author>\n" + name_xml + email_xml + gravatar_xml + rows_xml + stability_xml +
                          age_xml + percentage_in_comments_xml + "\t\t\t</author>\n")

        self.out.writeln("\t<blame>\n" + message_xml + "\t\t<authors>\n" +
                         blame_xml + "\t\t</authors>\n\t</blame>")
