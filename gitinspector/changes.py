# coding: utf-8
#
# Copyright © 2012-2017 Ejwa Software. All rights reserved.
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

import bisect
import copy
import datetime
import os
import re
from .filtering import Filters, is_filtered, is_acceptable_file_name
from . import format, git_utils, interval
from enum import Enum, auto


class CommitType(Enum):
    """
    An enumeration class representing the different commit types
    """
    CODE = "code"
    FILTERED = "filtered"
    MERGE = "merge"


class FileType(Enum):
    """
    An enumeration class representing the different commit types.
    """
    OTHER  = auto()
    BUILD  = auto()
    CPP    = auto()
    CSHARP = auto()
    GIT    = auto()
    GO     = auto()
    HTML   = auto()
    JAVA   = auto()
    JAVASCRIPT = auto()
    OCAML  = auto()
    PHP    = auto()
    PYTHON = auto()
    RUBY   = auto()
    RUST   = auto()
    SCHEME = auto()
    SHELL  = auto()
    TEX    = auto()
    TXT    = auto()
    VISUALBASIC = auto()

    __types__ = {
        "bib"      : TEX,
        "c"        : CPP,
        "cc"       : CPP,
        "cpp"      : CPP,
        "cxx"      : CPP,
        "cmake"    : BUILD,
        "cs"       : CSHARP,
        ".gitignore" : GIT,
        "go"       : GO,
        "h"        : CPP,
        "hh"       : CPP,
        "hpp"      : CPP,
        "html"     : HTML,
        "hxx"      : CPP,
        "i"        : CPP,
        "ii"       : CPP,
        "inl"      : CPP,
        "ipp"      : CPP,
        "ixx"      : CPP,
        "java"     : JAVA,
        "js"       : JAVASCRIPT,
        "Makefile" : BUILD,
        "md"       : TXT,
        "ml"       : OCAML,
        "mli"      : OCAML,
        "php"      : PHP,
        "py"       : PYTHON,
        "Rakefile" : BUILD,
        "README"   : TXT,
        "rb"       : RUBY,
        "rkt"      : SCHEME,
        "rs"       : RUST,
        "sh"       : SHELL,
        "tex"      : TEX,
        "txt"      : TXT,
        "vb"       : VISUALBASIC,
        "xml"      : TXT,
    }

    @staticmethod
    def create(file):
        _, rfile = os.path.split(file)
        _, ext = os.path.splitext(rfile)
        if ext:
            key = ext[1:]
        else:
            key = rfile
        type = FileType.__types__.get(key)
        if (type is None):
            return FileType.OTHER
        else:
            return FileType(type)

class AuthorColors(object):
    """
    A class providing different colors for the authors
    """
    colors =  [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#5f5fdf", "#bcbd22", "#17becf",
        "#77b41f", "#7f0eff", "#a02c2c", "#2728d6", "#67bd94",
        "#564b8c", "#77c2e3", "#bd22bc", "#becf17",
        "#b41f77", "#0eff7f", "#2c2ca0", "#28d627", "#bd9467",
        "#4b8c56", "#c2e377", "#22bcbd", "#cf17be",
    ]
    index = -1

    @staticmethod
    def get_new_color():
        AuthorColors.index += 1
        return AuthorColors.colors[AuthorColors.index % len(AuthorColors.colors)]


class FileDiff(object):
    def __init__(self, name, line):
        commit_line = line.split("|")

        if commit_line.__len__() == 2:
            self.name = name
            if is_acceptable_file_name(self.name):
                self.type = FileType.create(self.name)
            else:
                self.type = FileType.OTHER
            self.insertions = commit_line[1].count("+")
            self.deletions = commit_line[1].count("-")

    def __repr__(self):
        return "FileDiff(name: \033[93m{0}\033[0m, ins: \033[92m{1}\033[0m, del: \033[91m{2}\033[0m)".\
            format(self.name, self.insertions, self.deletions)

    @staticmethod
    def is_filediff_line(string):
        pattern = re.compile("^[^\|]+\|[ ]*(Bin[ ].*|[0-9]+[ ]*[+-]*)$")
        return pattern.match(string) is not None

    @staticmethod
    def get_extension(string):
        string = string.split("|")[0].strip().strip("{}").strip("\"").strip("'")
        return os.path.splitext(string)[1][1:]

    @staticmethod
    def get_filename(string):
        file_name = string.split("|")[0].strip()
        file_name = re.sub(r"^(.*)\{([^\}]*) => ([^\}]*)\}(.*)$", r"\1\3\4", file_name)
        file_name = re.sub(r"^(.*) => (.*)$", r"\2", file_name)
        file_name = file_name.strip("{}").strip("\"").strip("'")
        return file_name


class Commit(object):
    def __init__(self, string, config):
        self.filediffs = []
        self.config = config
        commit_line = string.split("|")

        if commit_line.__len__() == 5:
            self.timestamp = commit_line[0]
            self.date = commit_line[1]
            self.sha = commit_line[2]
            author = commit_line[3].strip()
            email = commit_line[4].strip()
            (self.author, self.email) = Commit.get_alias(author, email, self.config)

    def __lt__(self, other): # only used for sorting; we just consider the timestamp.
        return self.timestamp.__lt__(other.timestamp)

    def __repr__(self):
        if (self.type == CommitType.MERGE):
            return " Merge(sha: {0}, author: {1} <{2}>)".\
                format(self.sha[0:8], self.author, self.email)
        else:
            return "Commit(sha: {0}, author: {1} <{2}>, diffs: {3})".\
                format(self.sha[0:8], self.author, self.email, self.filediffs)

    def add_filediff(self, filediff):
        self.filediffs.append(filediff)

    def get_filediffs(self):
        return self.filediffs

    @staticmethod
    def handle_diff_chunk(config, changes, commits, chunk):
        commit_line = chunk.pop(0).strip().\
            decode("unicode_escape", "ignore").\
            encode("latin-1", "replace").\
            decode("utf-8", "replace")
        (author, email) = Commit.get_author_and_email(config, changes, commit_line)
        if (author, email) not in changes.committers:
            changes.committers[(author, email)] = {
                "color": AuthorColors.get_new_color() }
        found_valid_extension = False
        commit = Commit(commit_line, config)
        has_been_filtered = (is_filtered(commit.author, Filters.AUTHOR) or \
                             is_filtered(commit.email,  Filters.EMAIL) or \
                             is_filtered(commit.sha,    Filters.REVISION) or \
                             is_filtered(commit.sha,    Filters.MESSAGE))

        if has_been_filtered:
            commit.type = CommitType.FILTERED
        elif not chunk: # Chunk is [], it is a pure merge
            commit.type = CommitType.MERGE
        else:
            commit.type = CommitType.FILTERED # if all files are filtered
            for line in chunk:
                line = line.strip().\
                    decode("unicode_escape", "ignore").\
                    encode("latin-1", "replace").\
                    decode("utf-8", "replace")
                if FileDiff.is_filediff_line(line):
                    file_name = FileDiff.get_filename(line)
                    changes.files.add(file_name)
                    filediff = FileDiff(file_name, line)
                    commit.add_filediff(filediff)
                    commit.type = CommitType.CODE

        bisect.insort(commits, commit)

    @staticmethod
    def get_alias(author, email, config):
        if email in config.aliases.keys():
            new_author_mail = config.aliases[email].split("<")
            return (new_author_mail[0].strip(), new_author_mail[1][0:-1])
        else:
            if config.merge_authors:
                config.aliases[email] = "{0} <{1}>".format(author, email)
            return (author, email)

    @staticmethod
    def get_author_and_email(config, changes, string):
        commit_line = string.split("|")
        try:
            author = commit_line[3].strip()
            email = commit_line[4].strip()
            (real_author, real_email) = Commit.get_alias(author, email, config)
            return (real_author, real_email)
        except IndexError:
            return "Unknown Author"


class AuthorInfo(object):
    def __init__(self):
        # self.email = None
        self.insertions = 0
        self.deletions = 0
        self.commits = 0
        self.types = { FileType.OTHER: set() }

    def __repr__(self):
        return "Info(ins: \033[92m{0}\033[0m, del: \033[91m{1}\033[0m, commits: {2})".\
            format(self.insertions, self.deletions, self.commits)


PROGRESS_TEXT = _("Fetching and calculating primary statistics (1 of 2): {0:.0f}%")


class Changes(object):

    @classmethod
    def empty(cls):
        changes = Changes.__new__(Changes)
        changes.__commits__ = []
        changes.authors = {}
        changes.authors_dateinfo = {}
        changes.committers = {}
        changes.files = set()
        return changes

    def __init__(self, repo, config):
        self.__commits__ = []
        self.authors = {}
        self.authors_dateinfo = {}
        self.committers = {}
        self.files = set()
        self.config = config

        interval.set_ref("HEAD")

        progress_text = _(PROGRESS_TEXT)
        if repo is not None:
            progress_text = "[%s] " % repo.name + progress_text

        chunks =  git_utils.commit_chunks(self.config.branch, \
                                          interval.get_since(), interval.get_until(), \
                                          self.config)

        commits = []
        for chunk in chunks:
            Commit.handle_diff_chunk(self.config, self, commits, chunk)
        self.__commits__ = commits

        if self.__commits__:
            if interval.has_interval(): # or self.config.branch != "master":
                interval.set_ref(self.__commits__[-1].sha)

            self.first_commit_date = datetime.date(int(self.__commits__[0].date[0:4]),
                                                   int(self.__commits__[0].date[5:7]),
                                                   int(self.__commits__[0].date[8:10]))
            self.last_commit_date = datetime.date(int(self.__commits__[-1].date[0:4]),
                                                  int(self.__commits__[-1].date[5:7]),
                                                  int(self.__commits__[-1].date[8:10]))

    def __repr__(self):
        comm_str = "\n".join([ str(s) for s in self.__commits__ ])
        return "Changes(commits: {0})\n{1}".format(len(self.__commits__),
                                                   comm_str)

    def __iadd__(self, other):
        try:
            self.authors.update(other.authors)
            self.authors_dateinfo.update(other.authors_dateinfo)
            self.committers.update(other.committers)

            for commit in other.__commits__:
                bisect.insort(self.__commits__, commit)
            if not self.__commits__ and not other.__commits__:
                self.__commits__ = []

            self.changes.files.update(other.files)

            return self
        except AttributeError:
            return other

    def __update_dict_commit__(self, dict, key, commit):
        """
        Given `dict` whose values are AuthorInfos, add to dict[key] the
        properties of `commit` (insertions, deletions).
        """
        if key not in dict:
            dict[key] = AuthorInfo()

        # Even commits with no diffs (for example merges) are counted
        dict[key].commits += 1

        for j in commit.get_filediffs():
            if (j.type == FileType.OTHER):
                dict[key].types[j.type].add(j.name)
            else:
                dict[key].insertions += j.insertions
                dict[key].deletions += j.deletions
                if (j.type in dict[key].types):
                    dict[key].types[j.type] += j.insertions + j.deletions
                else:
                    dict[key].types[j.type] = j.insertions + j.deletions

    def all_commits(self):
        return self.__commits__

    def relevant_commits(self):
        return [c for c in self.__commits__
                if c.type == CommitType.CODE or c.type == CommitType.MERGE]

    def code_commits(self):
        return [c for c in self.__commits__ if c.type == CommitType.CODE]

    def merge_commits(self):
        return [c for c in self.__commits__ if c.type == CommitType.MERGE]

    def commits_for_author(self, author):
        return [c for c in self.__commits__ if c.author == author]

    def first_commit(self):
        return self.__commits__[0]

    def last_commit(self):
        return self.__commits__[-1]

    def diffs_for_file(self, file):
        return [d for c in self.__commits__ for d in c.filediffs if d.name == file]

    def get_authorinfo_list(self):
        """
        Returns a hash associating authors to AuthorInfo objects,
        technically a number of insertions, deletions and commits.
        """
        if not self.authors:
            for i in self.__commits__:
                self.__update_dict_commit__(self.authors, (i.author, i.email), i)

        return copy.deepcopy(self.authors)

    def get_total_types(self):
        author_list = self.get_authorinfo_list()
        total_types = set([FileType(k).name for c in author_list
                           for k in author_list.get(c).types
                           if k != FileType.OTHER])
        return total_types

    def get_authordateinfo_list(self):
        """
        Returns a hash associating (authors * dates) to AuthorInfo objects.
        Basically splits the return of get_authorinfo_list() on the dates.
        """
        if not self.authors_dateinfo:
            for i in self.__commits__:
                self.__update_dict_commit__(self.authors_dateinfo, (i.date, (i.author, i.email)), i)

        return copy.deepcopy(self.authors_dateinfo)

    def authors_by_responsibilities(self):
        """
        Returns a list of authors sorted according to their amount of
        work, namely the sum of their insertions and deletions.
        """
        wrk = [((c.author, c.email), sum([f.insertions + f.deletions for f in c.filediffs]))
               for c in self.__commits__]
        aut = set([k[0] for k in wrk])
        res = sorted(aut,
                     key=lambda a: -sum([w for (b,w) in wrk if b == a]))
        return res

    def filtered_files(self, author):
        """
        Returns a list of files that have been filtered during the run,
        given an (author,email) key.
        """
        authorinfo_dict = self.get_authorinfo_list()
        if (author in authorinfo_dict):
            return authorinfo_dict[author].types[FileType.OTHER]
        else:
            raise "Incorrect author key in 'Changes.filtered_files'"
