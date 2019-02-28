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

import gitinspector.localization as localization
from gitinspector.gitinspector import Runner, FileWriter, filtering, interval, __parse_arguments__


# Test gitinspector over a git repository present in the resources/
# dir, count the changes and the blames and check the metrics.
class BasicRepositoryTest(unittest.TestCase):

    def setUp(self):
        zip_ref = zipfile.ZipFile("tests/resources/basic-repository.zip", 'r')
        zip_ref.extractall("build/tests")
        zip_ref.close()

    def tearDown(self):
        # TODO: We definitely need to rewrite the 'filtering' and the
        # 'interval' modules to be part of the Runner context and NOT
        # BEING GLOBAL! (for our own sake!)...

        filtering.clear()
        interval.__since__ = ""
        interval.__until__ = ""
        shutil.rmtree("build/tests/basic-repository")

    def test_process(self):
       # Set options
        opts = __parse_arguments__(args=['--grading', '--legacy',
                                         '--branch', 'master',
                                         '--file-types', '*.c,*.txt',
                                         '--exclude', 'author:John Doe',
                                         '--silent',
                                         'build/tests/basic-repository'])
        opts.progress = False

        # Launch runner
        r = Runner(opts, None)
        r.process()

        # Check the repositories
        self.assertEqual(len(r.repos), 1)
        self.assertEqual(r.repos[0].name, "basic-repository")
        self.assertTrue(r.repos[0].location.endswith("build/tests/basic-repository"))
        self.assertEqual(r.repos[0].authors(),
                         ['Abraham Lincoln <abe@gov.us>', 'Andrew Johnson <jojo@gov.us>'])

        # Check the commits
        self.assertEqual(len(r.changes.commits), 2)
        authors = sorted(list(map(lambda c: c.author, r.changes.commits)))
        self.assertEqual(authors[0], "Abraham Lincoln")
        self.assertEqual(authors[1], "Andrew Johnson")

        # Check the blames
        self.assertEqual(len(r.blames.blames.keys()), 2)
        blame_keys = sorted(list(r.blames.blames.keys()))
        self.assertEqual(blame_keys[0], (('Abraham Lincoln', 'abe@gov.us'), 'README.txt'))
        self.assertEqual(blame_keys[1], (('Andrew Johnson', 'jojo@gov.us'), 'file.c'))
        self.assertEqual(r.blames.blames[blame_keys[0]].rows, 1) # README.txt is 1 line long
        self.assertEqual(r.blames.blames[blame_keys[1]].rows, 6) # main.c     is 6 lines long

        # Check the metrics
        self.assertEqual(r.metrics.eloc, {}) # Both files are too short, no metrics to report

    def test_output_text(self):
       # Set options
        opts = __parse_arguments__(args=['--grading', '--legacy',
                                         '--file-types', '*.c,*.txt',
                                         '--exclude', 'author:John Doe',
                                         '--format', 'text',
                                         'build/tests/basic-repository'])
        opts.progress = False

        # Launch runner
        localization.init_null()
        file = tempfile.NamedTemporaryFile('w', delete=False)
        r = Runner(opts, FileWriter(file))
        r.process()
        with open(file.name, 'r') as f:
            contents = f.read()
            self.assertTrue("Statistical information" in contents)
            self.assertTrue("The following historical commit" in contents)
            self.assertTrue("Below are the number of rows" in contents)
        os.remove(file.name)

    def test_output_html(self):
        # Set options
        opts = __parse_arguments__(args=['--grading', '--legacy',
                                         '--file-types', '*.c,*.txt',
                                         '--exclude', 'author:John Doe',
                                         '--format', 'html',
                                         'build/tests/basic-repository'])
        opts.progress = False

        # Launch runner
        localization.init_null()
        file = tempfile.NamedTemporaryFile('w', delete=False)
        r = Runner(opts, FileWriter(file))
        r.process()
        with open(file.name, 'r') as f:
            contents = f.read()
            self.assertTrue("Statistical information" in contents)
            self.assertTrue("The following history timeline" in contents)
        os.remove(file.name)

    def test_output_xml(self):
        # Set options
        opts = __parse_arguments__(args=['--grading', '--legacy',
                                         '--file-types', '*.c,*.txt',
                                         '--exclude', 'author:John Doe',
                                         '--format', 'xml',
                                         'build/tests/basic-repository'])
        opts.progress = False

        # Launch runner
        localization.init_null()
        file = tempfile.NamedTemporaryFile('w', delete=False)
        r = Runner(opts, FileWriter(file))
        r.process()
        with open(file.name, 'r') as f:
            contents = f.read()
            self.assertTrue("The following historical commit" in contents)
            self.assertTrue("Below are the number of rows" in contents)
            self.assertTrue("The following history timeline" in contents)
        os.remove(file.name)

    def test_output_json(self):
        # Set options
        opts = __parse_arguments__(args=['--grading', '--legacy',
                                         '--file-types', '*.c,*.txt',
                                         '--exclude', 'author:John Doe',
                                         '--format', 'json',
                                         'build/tests/basic-repository'])
        opts.progress = False

        # Launch runner
        localization.init_null()
        file = tempfile.NamedTemporaryFile('w', delete=False)
        r = Runner(opts, FileWriter(file))
        r.process()
        with open(file.name, 'r') as f:
            contents = f.read()
            self.assertTrue("The following historical commit" in contents)
            self.assertTrue("Below are the number of rows" in contents)
            self.assertTrue("The following history timeline" in contents)
        os.remove(file.name)


# Test gitinspector over a git repository present in the resources/
# dir, count the changes and the blames and check the metrics. These
# tests are a bit different because they add some filters.
class BasicFilteredRepositoryTest(unittest.TestCase):

    def setUp(self):
        zip_ref = zipfile.ZipFile("tests/resources/basic-repository.zip", 'r')
        zip_ref.extractall("build/tests")
        zip_ref.close()

    def tearDown(self):
        # TODO: We definitely need to rewrite the 'filtering' and the
        # 'interval' modules to be part of the Runner context and NOT
        # BEING GLOBAL! (for our own sake!)...

        filtering.clear()
        interval.__since__ = ""
        interval.__until__ = ""
        shutil.rmtree("build/tests/basic-repository")

    def test_process(self):
        # Set options
        opts = __parse_arguments__(args=['--grading', '--legacy',
                                         '--branch', 'master',
                                         '--file-types', '*.c,*.txt',
                                         '--exclude', 'author:Abraham Lincoln,message:README',
                                         '--since', '2001-01-01',
                                         '--until', '2020-01-01',
                                         '--silent',
                                         'build/tests/basic-repository'])
        opts.progress = False

        # Launch runner
        r = Runner(opts, None)
        r.process()

        # Check the repositories
        self.assertEqual(len(r.repos), 1)
        self.assertEqual(r.repos[0].name, "basic-repository")
        self.assertTrue(r.repos[0].location.endswith("build/tests/basic-repository"))
        self.assertEqual(r.repos[0].authors(),
                         ['Abraham Lincoln <abe@gov.us>', 'Andrew Johnson <jojo@gov.us>'])

        # Check the commits
        rel_commits = r.changes.relevant_commits()
        self.assertEqual(len(rel_commits), 1)
        authors = sorted(list(map(lambda c: c.author, rel_commits)))
        self.assertEqual(authors[0], "Andrew Johnson")

        # Check the blames
        self.assertEqual(len(r.blames.blames.keys()), 1)
        blame_keys = sorted(list(r.blames.blames.keys()))
        self.assertEqual(blame_keys[0], (('Andrew Johnson', 'jojo@gov.us'), 'file.c'))
        self.assertEqual(r.blames.blames[blame_keys[0]].rows, 6) # main.c is 6 lines long

        # Check the metrics
        self.assertEqual(r.metrics.eloc, {}) # Both files are too short, no metrics to report

    def test_output_text(self):
        # Set options
        opts = __parse_arguments__(args=['--grading', '--legacy',
                                         '--file-types', '*.c,*.txt',
                                         '--exclude', 'author:Abraham Lincoln',
                                         '--since', '2001-01-01',
                                         '--until', '2020-01-01',
                                         '--format', 'text',
                                         'build/tests/basic-repository'])
        opts.progress = False

        # Launch runner
        localization.init_null()
        file = tempfile.NamedTemporaryFile('w', delete=False)
        r = Runner(opts, FileWriter(file))
        r.process()
        with open(file.name, 'r') as f:
            contents = f.read()
            self.assertTrue("Statistical information" in contents)
            self.assertTrue("The following historical commit" in contents)
            self.assertTrue("Below are the number of rows" in contents)
            self.assertTrue("The following history timeline" in contents)
        os.remove(file.name)

    def test_output_html(self):
        # Set options
        opts = __parse_arguments__(args=['--grading', '--legacy',
                                         '--file-types', '*.c,*.txt',
                                         '--exclude', 'author:Abraham Lincoln',
                                         '--since', '2001-01-01',
                                         '--until', '2020-01-01',
                                         '--format', 'html',
                                         'build/tests/basic-repository'])
        opts.progress = False

        # Launch runner
        localization.init_null()
        file = tempfile.NamedTemporaryFile('w', delete=False)
        r = Runner(opts, FileWriter(file))
        r.process()
        with open(file.name, 'r') as f:
            contents = f.read()
            self.assertTrue("Statistical information" in contents)
            self.assertTrue("The following history timeline" in contents)
        os.remove(file.name)

    def test_output_xml(self):
        # Set options
        opts = __parse_arguments__(args=['--grading', '--legacy',
                                         '--file-types', '*.c,*.txt',
                                         '--exclude', 'author:Abraham Lincoln',
                                         '--since', '2001-01-01',
                                         '--until', '2020-01-01',
                                         '--format', 'xml',
                                         'build/tests/basic-repository'])
        opts.progress = False

        # Launch runner
        localization.init_null()
        file = tempfile.NamedTemporaryFile('w', delete=False)
        r = Runner(opts, FileWriter(file))
        r.process()
        with open(file.name, 'r') as f:
            contents = f.read()
            self.assertTrue("The following historical commit" in contents)
            self.assertTrue("Below are the number of rows" in contents)
            self.assertTrue("The following history timeline" in contents)
        os.remove(file.name)

    def test_output_json(self):
        # Set options
        opts = __parse_arguments__(args=['--grading', '--legacy',
                                         '--file-types', '*.c,*.txt',
                                         '--exclude', 'author:Abraham Lincoln',
                                         '--since', '2001-01-01',
                                         '--until', '2020-01-01',
                                         '--format', 'json',
                                         'build/tests/basic-repository'])
        opts.progress = False

        # Launch runner
        localization.init_null()
        file = tempfile.NamedTemporaryFile('w', delete=False)
        r = Runner(opts, FileWriter(file))
        r.process()
        with open(file.name, 'r') as f:
            contents = f.read()
            self.assertTrue("The following historical commit" in contents)
            self.assertTrue("Below are the number of rows" in contents)
            self.assertTrue("The following history timeline" in contents)
        os.remove(file.name)
