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
import multiprocessing
import os
import re
import subprocess
import threading
from .filtering import Filters, is_filtered, is_acceptable_file_name
from . import format, git_utils, interval, terminal
from enum import Enum

CHANGES_PER_THREAD = 200
NUM_THREADS = multiprocessing.cpu_count()

__thread_lock__ = threading.BoundedSemaphore(NUM_THREADS)
__changes_lock__ = threading.Lock()


class CommitType(Enum):
    """
    An enumeration class representing the different commit types
    """
    RELEVANT = "relevant"
    FILTERED = "filtered"
    MERGE = "merge"


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
    def __init__(self, string):
        commit_line = string.split("|")

        if commit_line.__len__() == 2:
            self.name = commit_line[0].strip()
            self.insertions = commit_line[1].count("+")
            self.deletions = commit_line[1].count("-")

    @staticmethod
    def is_filediff_line(string):
        string = string.split("|")
        return string.__len__() == 2 and string[1].find("Bin") == -1 and ('+' in string[1] or '-' in string[1])

    @staticmethod
    def get_extension(string):
        string = string.split("|")[0].strip().strip("{}").strip("\"").strip("'")
        return os.path.splitext(string)[1][1:]

    @staticmethod
    def get_filename(string):
        file_name = string.split("|")[0].strip()
        file_name = re.sub(r"^([^\{]*)\{([^\}]*) => ([^\}]*)\}.*$", r"\1\3", file_name)
        return file_name.strip("{}").strip("\"").strip("'")


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
            for line in chunk:
                line = line.strip().\
                    decode("unicode_escape", "ignore").\
                    encode("latin-1", "replace").\
                    decode("utf-8", "replace")
                if FileDiff.is_filediff_line(line) and not has_been_filtered:
                    file_name = FileDiff.get_filename(line)
                    if is_acceptable_file_name(FileDiff.get_filename(line)):
                        changes.files.append(file_name)
                        found_valid_extension = True
                        filediff = FileDiff(line)
                        commit.add_filediff(filediff)
            if found_valid_extension:
                commit.type = CommitType.RELEVANT
            else:
                commit.type = CommitType.FILTERED

        bisect.insort(commits, commit)

    @staticmethod
    def get_alias(author, email, config):
        author_mail = "{0} <{1}>".format(author, email)
        if author_mail in config.aliases.keys():
            new_author_mail = config.aliases[author_mail].split("<")
            return (new_author_mail[0].strip(), new_author_mail[1][0:-1])

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
    email = None
    insertions = 0
    deletions = 0
    commits = 0


class ChangesThread(threading.Thread):
    def __init__(self, config, changes, first_hash, second_hash, offset):
        __thread_lock__.acquire() # Lock controlling the number of threads running
        threading.Thread.__init__(self)

        self.config = config
        self.changes = changes
        self.first_hash = first_hash
        self.second_hash = second_hash
        self.offset = offset

    @staticmethod
    def create(config, changes, first_hash, second_hash, offset):
        thread = ChangesThread(config, changes, first_hash, second_hash, offset)
        thread.daemon = True
        thread.start()

    def run(self):
        chunks =  git_utils.commit_chunks("--all" if (self.config.branch == "--all") \
                                          else (self.first_hash + self.second_hash), \
                                          interval.get_since(), interval.get_until(), \
                                          self.config.hard)
        commits = []

        __changes_lock__.acquire() # Global lock used to protect calls from here...

        for chunk in chunks:
            Commit.handle_diff_chunk(self.config, self.changes, commits, chunk)

        self.changes.__commits__[self.offset // CHANGES_PER_THREAD] = commits
        __changes_lock__.release() # ...to here.
        __thread_lock__.release() # Lock controlling the number of threads running


PROGRESS_TEXT = _("Fetching and calculating primary statistics (1 of 2): {0:.0f}%")


class Changes(object):

    @classmethod
    def empty(cls):
        changes = Changes.__new__(Changes)
        changes.__commits__ = []
        changes.authors = {}
        changes.authors_dateinfo = {}
        changes.committers = {}
        changes.files = []
        return changes

    def __init__(self, repo, config):
        self.__commits__ = []
        self.authors = {}
        self.authors_dateinfo = {}
        self.committers = {}
        self.files = []
        self.config = config

        interval.set_ref("HEAD")
        lines = git_utils.commits(interval.get_since(),
                                  interval.get_until(), config.branch)

        if lines:
            progress_text = _(PROGRESS_TEXT)
            if repo is not None:
                progress_text = "[%s] " % repo.name + progress_text

            chunks = len(lines) // CHANGES_PER_THREAD
            self.__commits__ = [None] * (chunks if len(lines) % CHANGES_PER_THREAD == 0 else chunks + 1)
            first_hash = ""

            for i, entry in enumerate(lines):
                if i % CHANGES_PER_THREAD == CHANGES_PER_THREAD - 1:
                    entry = entry.decode("utf-8", "replace").strip()
                    second_hash = entry
                    ChangesThread.create(self.config, self, first_hash, second_hash, i)
                    first_hash = entry + ".."

                    if self.config.progress and format.is_interactive_format():
                        terminal.output_progress(progress_text, i, len(lines))
            else: # Create one last thread
                if CHANGES_PER_THREAD - 1 != i % CHANGES_PER_THREAD:
                    entry = entry.decode("utf-8", "replace").strip()
                    second_hash = entry
                    ChangesThread.create(self.config, self, first_hash, second_hash, i)

        # Make sure all threads have completed.
        for i in range(0, NUM_THREADS):
            __thread_lock__.acquire()

        # We also have to release them for future use.
        for i in range(0, NUM_THREADS):
            __thread_lock__.release()

        self.__commits__ = [item for sublist in self.__commits__ for item in sublist]

        if self.__commits__:
            if interval.has_interval(): # or self.config.branch != "master":
                interval.set_ref(self.__commits__[-1].sha)

            self.first_commit_date = datetime.date(int(self.__commits__[0].date[0:4]),
                                                   int(self.__commits__[0].date[5:7]),
                                                   int(self.__commits__[0].date[8:10]))
            self.last_commit_date = datetime.date(int(self.__commits__[-1].date[0:4]),
                                                  int(self.__commits__[-1].date[5:7]),
                                                  int(self.__commits__[-1].date[8:10]))

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

    def all_commits(self):
        return self.__commits__
    def relevant_commits(self):
        return [ c for c in self.__commits__ if c.type == CommitType.RELEVANT ]
    def merge_commits(self):
        return [ c for c in self.__commits__ if c.type == CommitType.MERGE ]

    def update_dict_commit(self, dict, key, commit):
        if dict.get(key, None) is None:
            dict[key] = AuthorInfo()

        if commit.get_filediffs():
            dict[key].commits += 1

        for j in commit.get_filediffs():
            dict[key].insertions += j.insertions
            dict[key].deletions += j.deletions

    def get_authorinfo_list(self):
        if not self.authors:
            for i in self.__commits__:
                self.update_dict_commit(self.authors, (i.author, i.email), i)

        return copy.deepcopy(self.authors)

    def get_authordateinfo_list(self):
        if not self.authors_dateinfo:
            for i in self.__commits__:
                self.update_dict_commit(self.authors_dateinfo, (i.date, (i.author, i.email)), i)

        return copy.deepcopy(self.authors_dateinfo)

    def authors_by_responsibilities(self):
        wrk = [((c.author, c.email), sum([f.insertions + f.deletions for f in c.filediffs]))
               for c in self.__commits__]
        aut = set([k[0] for k in wrk])
        res = sorted(aut,
                     key=lambda a: -sum([w for (b,w) in wrk if b == a]))
        return res
