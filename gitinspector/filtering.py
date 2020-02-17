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

import fnmatch
import re
from . import git_utils
from enum import Enum
import os

# TODO: We definitely need to rewrite the 'filtering' module to be part
# of the Runner context and NOT BEING GLOBAL! (for our own sake!)...

class Filters(Enum):
    """
    An enumeration class representing the different filter types
    """
    FILE_IN  = "file_in"   # positive match for filenames (include)
    FILE_OUT = "file_out"  # negative match for filenames (exclude)
    AUTHOR   = "author"
    EMAIL    = "email"
    REVISION = "revision"
    MESSAGE  = "message"

"""
The first set containes compiled regexps.
The second set contains matching strings.
"""
__filters__ = {
    Filters.FILE_IN:  [set(), set()],
    Filters.FILE_OUT: [set(), set()],
    Filters.AUTHOR:   [set(), set()],
    Filters.EMAIL:    [set(), set()],
    Filters.REVISION: [set(), set()],
    Filters.MESSAGE : [set(), None]
}

class InvalidRegExpError(ValueError):
    def __init__(self, msg):
        super(InvalidRegExpError, self).__init__(msg)
        self.msg = msg

def __add_one_filter__(string,is_globbing=False):
    """
    Function that takes a string and records the corresponding filter
    inside __filters__.
    Syntax: <filter_prefix>:<globbing_pattern>
    """
    split_rule = string.strip().split(":")
    if len(split_rule) != 2:
        raise ValueError("Invalid filter : %s"%string)
    for filter in Filters:
        if filter.value == split_rule[0]:
            if is_globbing:
                pattern = fnmatch.translate(split_rule[1])
            else:
                pattern = split_rule[1]
            __filters__[filter][0].add(re.compile(pattern))
            return
    raise ValueError("Invalid filter : %s"%string)

def add_filters(string):
    """
    Add a set of filters, separated by commas. The syntax corresponds
    to the --exclude option on the command-line. If KEY is missing
    somehow, the filter is automatically Filters.FILE_IN".
    """
    rules = string.split(",")
    for rule in rules:
        __add_one_filter__(rule)

def clear():
    for filter in Filters:
        __filters__[filter] = [set(), set()]

def get_filtered(filter_type=Filters.FILE_IN):
    return __filters__[filter_type][1]

def has_filtered():
    """
    Returns True iff there is at least one active filter.
    """
    for filter in Filters:
        if __filters__[filter][1]:
            return True
    return False

def is_filtered(string, filter_type):
    """
    The function that tests whether 'string' passes the filters
    defined in __filters__. The test on the string parameter depends
    on the filter_type. This function should not be used with the
    filters on file names (cf. is_acceptable_file_name).
    """

    if (filter_type == Filters("file_in")) or (filter_type == Filters("file_out")):
        raise "Should not use that filter this way"

    string = string.strip()
    if not string:
        return False

    for regexp in __filters__[filter_type][0]:
        if filter_type == Filters.MESSAGE:
            search_for = git_utils.commit_message(string)
        else:
            search_for = string

        try:
            if regexp.search(search_for) is not None:
                if filter_type == Filters.MESSAGE:
                    __add_one_filter__("revision:" + string) # ??
                else:
                    __filters__[filter_type][1].add(string)
                return True
        except:
            raise InvalidRegExpError(_("Invalid regular expression specified"))

    return False

def is_acceptable_file_name(string):
    """
    The function that tests whether 'string' passes the filters
    according to the configuration for file names. First, the filename
    must pass at least one positive check (in FILE_IN), and second, it
    must not belong to any negative check (in FILE_OUT)
    """
    search_for = string.strip()
    if not(_matches_filter(search_for, Filters.FILE_IN)):
        return False
    if _matches_filter(search_for, Filters.FILE_OUT):
        __filters__[Filters.FILE_OUT][1].add(_find_excluded_top_dir(search_for))
        return False
    return True

def _matches_filter(string, filter):
    try:
        for regexp in __filters__[filter][0]:
            if regexp.search(string) is not None:
                return True
    except:
        raise InvalidRegExpError(_("Invalid regular expression specified"))
    return False

def _find_excluded_top_dir(path):
    previous_path = path
    new_path = os.path.dirname(path)
    while len(new_path) > 0 and _matches_filter(new_path + "/", Filters.FILE_OUT):
        previous_path = new_path
        new_path = os.path.dirname(new_path)
    return previous_path
