# coding: utf-8
#
# Copyright © 2013-2015 Ejwa Software. All rights reserved.
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

import ast
import os
from . import filtering, format, git_utils, interval


class GitConfig(object):
    def __init__(self, run, repo, global_only=False):
        self.run = run
        self.repo = repo
        self.global_only = global_only

    def __read_git_config__(self, variable):
        return git_utils.config(self.repo, variable, self.global_only)

    def __read_git_config_bool__(self, variable):
        variable = self.__read_git_config__(variable)
        arg = (False if variable == "" else variable)
        if isinstance(arg, bool):
            return arg
        elif arg is None or arg.lower() == "false" or arg.lower() == "f" or arg == "0":
            return False
        elif arg.lower() == "true" or arg.lower() == "t" or arg == "1":
            return True
        return False

    def __read_git_config_string__(self, variable):
        string = self.__read_git_config__(variable)
        return (True, string) if string else (False, None)

    def read(self):
        var = self.__read_git_config_string__("file-types")
        if var[0]:
            self.run.config.file_types = var[1]
            for f in var[1].split(','):
                filtering.__add_one_filter__("file_in:" + f, True)

        var = self.__read_git_config_string__("exclude")
        if var[0]:
            filtering.add_filters(var[1])

        var = self.__read_git_config_string__("format")
        if var[0] and not format.select(var[1]):
            raise format.InvalidFormatError(_("specified output format not supported."))

        var = self.__read_git_config_string__("aliases")
        if var[0]:
            self.run.config.aliases = ast.literal_eval(var[1])

        if self.__read_git_config_bool__("hard"):
            self.run.config.hard = True
        if self.__read_git_config_bool__("list-file-types"):
            self.run.config.list_file_types = True
        if self.__read_git_config_bool__("localize-output"):
            self.run.config.localize_output = True
        if self.__read_git_config_bool__("metrics"):
            self.run.config.metrics = True
        if self.__read_git_config_bool__("responsibilities"):
            self.run.config.responsibilities = True
        if self.__read_git_config_bool__("weeks"):
            self.run.config.useweeks = True

        var = self.__read_git_config_string__("since")
        if var[0]:
            interval.set_since(var[1])

        var = self.__read_git_config_string__("until")
        if var[0]:
            interval.set_until(var[1])

        if self.__read_git_config_bool__("timeline"):
            self.run.config.timeline = True

        if self.__read_git_config_bool__("grading"):
            self.run.config.hard = True
            self.run.config.list_file_types = True
            self.run.config.metrics = True
            self.run.config.responsibilities = True
            self.run.config.timeline = True
            self.run.config.useweeks = True
