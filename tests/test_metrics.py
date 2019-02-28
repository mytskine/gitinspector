# coding: utf-8
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

import hashlib
import locale
import os
import shutil
import tempfile
import unittest
import zipfile

from gitinspector.gitinspector import Runner, FileWriter, filtering, interval, __parse_arguments__
from gitinspector.changes import CommitType

class MetricsTest(unittest.TestCase):

    def setUp(self):
        zip_ref = zipfile.ZipFile("tests/resources/trie-repository.zip", 'r')
        zip_ref.extractall("build/tests")
        zip_ref.close()

    def tearDown(self):
        pass

    def test_all_changes(self):
        opts = __parse_arguments__(args=['--silent',
                                         'build/tests/trie-repository'])
        opts.progress = False

        # Launch runner
        r = Runner(opts, None)
        r.process()
        self.assertEqual(len(r.changes.commits), 31)  # 29 commits + 2 merges
        self.assertEqual(len(r.changes.relevant_commits()), 29)
        self.assertEqual(len(r.changes.merge_commits()), 2)
        b_commits = [c for c in r.changes.commits if c.author == "Bilbo Baggins"]
        self.assertEqual(len(b_commits), 12)  # 11 commits + 1 merge
        self.assertEqual(len([c for c in b_commits if c.type == CommitType.RELEVANT]), 11)
        self.assertEqual(len([c for c in b_commits if c.type == CommitType.MERGE]), 1)
        f_commits = [c for c in r.changes.commits if c.author == "Frodo Baggins"]
        self.assertEqual(len(f_commits), 6)   # 6 commits
        s_commits = [c for c in r.changes.commits if c.author == "Samwise Gamgee"]
        self.assertEqual(len(s_commits), 7)   # 6 commits + 1 merge
        self.assertEqual(len([c for c in s_commits if c.type == CommitType.RELEVANT]), 6)

    def test_small_changes(self):
        opts = __parse_arguments__(args=['--silent', '--since=2015-10-20', '--until=2015-10-22',
                                         'build/tests/trie-repository'])
        opts.progress = False

        # Launch runner
        r = Runner(opts, None)
        r.process()
        self.assertEqual(len(r.changes.commits), 5)  # 4 commits + 1 merge
        self.assertEqual(len(r.changes.relevant_commits()), 4)
        b_commits = [c for c in r.changes.commits if c.author == "Bilbo Baggins"]
        self.assertEqual(len(b_commits), 4)  # 3 commits + 1 merge
        self.assertEqual(len([c for c in b_commits if c.type == CommitType.RELEVANT]), 3)
        self.assertEqual(len([c for c in b_commits if c.type == CommitType.MERGE]), 1)
        f_commits = [c for c in r.changes.commits if c.author == "Frodo Baggins"]
        self.assertEqual(len(f_commits), 0)  # 0 commits
        s_commits = [c for c in r.changes.commits if c.author == "Samwise Gamgee"]
        self.assertEqual(len(s_commits), 1)  # 1 commits
