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

import datetime
import multiprocessing
import re
import subprocess
import threading

from .changes import FileDiff
from .filtering import Filters, is_filtered, is_acceptable_file_name
from . import comment, format, git_utils, interval, terminal

NUM_THREADS = multiprocessing.cpu_count()

class BlameEntry(object):
    """A simple record class that stores informations about a blame. All
    BlameEntry objects are stored into hashes (author, file) -> BlameEntry.
    """
    rows = 0
    skew = 0 # Used when calculating average code age.
    comments = 0

__thread_lock__ = threading.BoundedSemaphore(NUM_THREADS)
__blame_lock__ = threading.Lock()

AVG_DAYS_PER_MONTH = 30.4167

class BlameThread(threading.Thread):
    """A class that launches a thread counting the blames for a given
    file. The class is supposed to be somewhat thread-safe, and can be
    applied a multiple number of times for the same file if needed.
    """
    blamechunk_author = None
    blamechunk_email = None
    blamechunk_is_last = False
    blamechunk_is_prior = False
    blamechunk_revision = None
    blamechunk_time = None

    def __init__(self, config, changes, blame_command, extension, blames, filename):
        __thread_lock__.acquire() # Lock controlling the number of threads running
        threading.Thread.__init__(self)

        self.useweeks = config.weeks
        self.changes = changes
        self.blame_command = blame_command
        self.extension = extension
        self.blames = blames
        self.filename = filename

        self.is_inside_comment = False

    def __clear_blamechunk_info__(self):
        self.blamechunk_email = None
        self.blamechunk_is_last = False
        self.blamechunk_is_prior = False
        self.blamechunk_revision = None
        self.blamechunk_time = None

    def __handle_blamechunk_content__(self, content):
        author = None
        (comments, self.is_inside_comment) = comment.handle_comment_block(self.is_inside_comment,
                                                                          self.extension, content)

        if self.blamechunk_is_prior and interval.get_since():
            return
        try:
            author = self.blamechunk_author
            email = self.blamechunk_email
        except KeyError:
            return

        if not is_filtered(author, Filters.AUTHOR) and \
           not is_filtered(self.blamechunk_email, Filters.EMAIL) and \
           not is_filtered(self.blamechunk_revision, Filters.REVISION):

            __blame_lock__.acquire() # Global lock used to protect calls from here...

            if (author, email) not in self.changes.committers:
                self.changes.committers[(author, email)] = { "color" : "#aaaaaa",
                                                             "committer" : False }

            if self.blames.get(((author, email), self.filename), None) is None:
                self.blames[((author, email), self.filename)] = BlameEntry()

            self.blames[((author, email), self.filename)].comments += comments
            self.blames[((author, email), self.filename)].rows += 1

            if (self.blamechunk_time - self.changes.first_commit_date).days > 0:
                new_skew = ((self.changes.last_commit_date - self.blamechunk_time).days /
                            (7.0 if self.useweeks else AVG_DAYS_PER_MONTH))
                self.blames[((author, email), self.filename)].skew += new_skew

            __blame_lock__.release() # ...to here.

    def run(self):
        git_blame_cmd = subprocess.Popen(self.blame_command, bufsize=1, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        rows = git_blame_cmd.stdout.readlines()
        git_blame_cmd.wait()
        git_blame_cmd.stdout.close()
        git_blame_cmd.stderr.close()

        self.__clear_blamechunk_info__()

        #pylint: disable=W0201
        for row in rows:
            row = row.decode("utf-8", "replace").strip()
            keyval = row.split(" ", 2)

            if self.blamechunk_is_last:
                self.__handle_blamechunk_content__(row)
                self.__clear_blamechunk_info__()
            elif keyval[0] == "boundary":
                self.blamechunk_is_prior = True
            elif keyval[0] == "author":
                self.blamechunk_author = " ".join(keyval[1:])
            elif keyval[0] == "author-mail":
                self.blamechunk_email = keyval[1].lstrip("<").rstrip(">")
            elif keyval[0] == "author-time":
                self.blamechunk_time = datetime.date.fromtimestamp(int(keyval[1]))
            elif keyval[0] == "filename":
                self.blamechunk_is_last = True
            elif Blame.is_revision(keyval[0]):
                self.blamechunk_revision = keyval[0]

        __thread_lock__.release() # Lock controlling the number of threads running


PROGRESS_TEXT_START = _("Starting the computation of the rows (2 of 2): {0:.0f}%")
PROGRESS_TEXT_GOING = _("Checking how many rows belong to each author (2 of 2): {0:.0f}%")


class Blame(object):
    """The global file that enumerates all the files in the current
    repository and associates one BlameEntry to each of them.
    """
    @classmethod
    def empty(cls):
        blame = Blame.__new__(Blame)
        blame.blames = {}
        return blame

    def __init__(self, repo, changes, config):
        self.blames = {}
        self.config = config

        if config.progress:
            terminal.output_progress(PROGRESS_TEXT_START, 0, 1)

        if self.config.branch == "--all":
            # Apply an heuristic to compute the blames on all the
            # branches : The files taken into account are the most
            # recent ones over all the branches.
            branches = self.config.branches
            lines = {} # Associates files to branch
            times = {} # Associates files to time
            for b in branches:
                # for f in git_utils.files(b):
                for f in changes.files:
                    if f in lines:
                        if not(f in times):
                            times[f] = git_utils.last_commit(lines[f], f)
                        new_time = git_utils.last_commit(b, f)
                        if new_time > times[f]:
                            times[f] = new_time
                            lines[f] = b
                    else:
                        lines[f] = b
        else:
            lines = {l: self.config.branch for l in git_utils.files(config.branch)}

        if lines:
            progress_text = _(PROGRESS_TEXT_GOING)

            if repo is not None:
                progress_text = "[%s] " % repo.name + progress_text

            cpt = 0
            for filename, branch in lines.items():
                cpt += 1

                if is_acceptable_file_name(filename):
                    blame_command = filter(None,
                                           ["git", "blame",
                                            "--line-porcelain", "-w"] +
                                           (["-C", "-C", "-M"] if config.hard else []) +
                                           [interval.get_since(), branch,
                                            "--", filename])
                    thread = BlameThread(config, changes, blame_command,
                                         FileDiff.get_extension(filename),
                                         self.blames, filename)
                    thread.daemon = True
                    thread.start()

                    if config.progress:
                        terminal.output_progress(progress_text, cpt, len(lines))

            # Make sure all threads have completed.
            for i in range(0, NUM_THREADS):
                __thread_lock__.acquire()

            # We also have to release them for future use.
            for i in range(0, NUM_THREADS):
                __thread_lock__.release()


    def __iadd__(self, other):
        try:
            self.blames.update(other.blames)
            return self
        except AttributeError:
            return other

    @staticmethod
    def is_revision(string):
        revision = re.search("([0-9a-f]{40})", string)

        if revision is None:
            return False

        return revision.group(1).strip()

    @staticmethod
    def get_stability(author, blamed_rows, changes):
        if author in changes.get_authorinfo_list():
            author_insertions = changes.get_authorinfo_list()[author].insertions
            return 100 if author_insertions == 0 else 100.0 * blamed_rows / author_insertions
        return 100

    def get_summed_blames(self):
        summed_blames = {}
        for i in self.blames.items():
            if summed_blames.get(i[0][0], None) is None:
                summed_blames[i[0][0]] = BlameEntry()

            summed_blames[i[0][0]].rows += i[1].rows
            summed_blames[i[0][0]].skew += i[1].skew
            summed_blames[i[0][0]].comments += i[1].comments

        return summed_blames

    def committers_by_responsibilities(self):
        wrk = [ (k[0],v.rows) for (k,v) in self.blames.items()]
        aut = set([k[0] for k in wrk])
        res = sorted(aut,
                     key=lambda a: -sum([w for (b,w) in wrk if b == a]))
        return res
