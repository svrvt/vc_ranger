# This is a sample commands.py.  You can add your own commands here.
#
# Please refer to commands_full.py for all the default commands and a complete
# documentation.  Do NOT add them all here, or you may end up with defunct
# commands when upgrading ranger.

# A simple command for demonstration purposes follows.
# -----------------------------------------------------------------------------

from __future__ import (absolute_import, division, print_function)

# You can import any python module as needed.
import os
import re
import subprocess

# You always need to import ranger.api.commands here to get the Command class:
from ranger.api.commands import Command


# Any class that is a subclass of "Command" will be integrated into ranger as a
# command.  Try typing ":my_edit<ENTER>" in ranger!
class my_edit(Command):
    # The so-called doc-string of the class will be visible in the built-in
    # help that is accessible by typing "?c" inside ranger.
    """:my_edit <filename>

    A sample command for demonstration purposes that opens a file in an editor.
    """

    # The execute method is called when you run this command in ranger.
    def execute(self):
        # self.arg(1) is the first (space-separated) argument to the function.
        # This way you can write ":my_edit somefilename<ENTER>".
        if self.arg(1):
            # self.rest(1) contains self.arg(1) and everything that follows
            target_filename = self.rest(1)
        else:
            # self.fm is a ranger.core.filemanager.FileManager object and gives
            # you access to internals of ranger.
            # self.fm.thisfile is a ranger.container.file.File object and is a
            # reference to the currently selected file.
            target_filename = self.fm.thisfile.path

        # This is a generic function to print text in ranger.
        self.fm.notify("Let's edit the file " + target_filename + "!")

        # Using bad=True in fm.notify allows you to print error messages:
        if not os.path.exists(target_filename):
            self.fm.notify("The given file does not exist!", bad=True)
            return

        # This executes a function from ranger.core.acitons, a module with a
        # variety of subroutines that can help you construct commands.
        # Check out the source, or run "pydoc ranger.core.actions" for a list.
        self.fm.edit_file(target_filename)

    # The tab method is called when you press tab, and should return a list of
    # suggestions that the user will tab through.
    # tabnum is 1 for <TAB> and -1 for <S-TAB> by default
    def tab(self, tabnum):
        # This is a generic tab-completion function that iterates through the
        # content of the current directory.
        return self._tab_directory_content()

class recent_directories(Command):
    """
    :recent_directories

    Jump to recent directories using fasd
    """

    def execute(self):
        selector_executable = os.path.join(os.path.dirname(__file__),
                                           'fzf-select-dir')
        fasd_process = self.fm.execute_command(['fasd', '-dl'],
                                               stdout=subprocess.PIPE)
        selector_process = self.fm.execute_command(
            [selector_executable, '--tac'],
            stdin=fasd_process.stdout,
            stdout=subprocess.PIPE,
            universal_newlines=True)
        stdout, _ = selector_process.communicate()
        if selector_process.returncode == 0:
            directory = os.path.abspath(stdout.rstrip('\n'))
            assert os.path.isdir(directory)
            self.fm.execute_command(['fasd', '--add', directory])
            self.fm.cd(directory)


class recent_files(Command):
    """
    :recent_files

    Jump to recent files using fasd
    """

    def execute(self):
        selector_executable = os.path.join(os.path.dirname(__file__),
                                           'fzf-select-file')
        fasd_process = self.fm.execute_command(['fasd', '-fl'],
                                               stdout=subprocess.PIPE)
        selector_process = self.fm.execute_command(
            [selector_executable, '--tac'],
            stdin=fasd_process.stdout,
            stdout=subprocess.PIPE,
            universal_newlines=True)
        stdout, _ = selector_process.communicate()
        if selector_process.returncode == 0:
            file_path = os.path.abspath(stdout.rstrip('\n'))
            assert os.path.isdir(file_path)
            self.fm.execute_command(['fasd', '--add', file_path])
            self.fm.select_file(file_path)


class mkcd(Command):
    """
    :mkcd <dirname>

    Creates a directory with the name <dirname> and enters it.
    """

    def execute(self):

        dirname = os.path.join(self.fm.thisdir.path,
                               os.path.expanduser(self.rest(1)))
        if not os.path.lexists(dirname):
            os.makedirs(dirname)

            match = re.search('^/|^~[^/]*/', dirname)
            if match:
                self.fm.cd(match.group(0))
                dirname = dirname[match.end(0):]

            for match in re.finditer('[^/]+', dirname):
                s = match.group(0)
                if s == '..' or (s.startswith('.') and
                                 not self.fm.settings['show_hidden']):
                    self.fm.cd(s)
                else:
                    ## We force ranger to load content before calling `scout`.
                    self.fm.thisdir.load_content(schedule=False)
                    self.fm.execute_console('scout -ae ^{}$'.format(s))
        else:
            self.fm.notify("file/directory exists!", bad=True)


class fzf_select(Command):
    """
    :fzf_select

    Find a file using fzf.
    """

    def execute(self):
        selector_executable = os.path.join(os.path.dirname(__file__),
                                           'fzf-select-file')
        command = r"find -L . \( -fstype 'dev' -o -fstype 'proc' \) -prune \
                -o -print 2> /dev/null | \
                sed 1d | \
                cut -b3- | \
                {} +m".format(selector_executable)

        fzf = self.fm.execute_command(command,
                                      universal_newlines=True,
                                      stdout=subprocess.PIPE)
        stdout, _ = fzf.communicate()
        if fzf.returncode == 0:
            fzf_file = os.path.abspath(stdout.rstrip('\n'))
            if os.path.isdir(fzf_file):
                self.fm.cd(fzf_file)
            else:
                self.fm.select_file(fzf_file)


class fzf_my_select(Command):
    """
    :fzf_my_select

    Find a file using list-searched-files.
    """

    def execute(self):
        selector_executable = os.path.join(os.path.dirname(__file__),
                                           'fzf-select-file')
        command = r"list-searched-files | {} +m".format(selector_executable)

        fzf = self.fm.execute_command(command,
                                      universal_newlines=True,
                                      stdout=subprocess.PIPE)
        stdout, _ = fzf.communicate()
        if fzf.returncode == 0:
            fzf_file = os.path.abspath(stdout.rstrip('\n'))
            if os.path.isdir(fzf_file):
                self.fm.cd(fzf_file)
            else:
                self.fm.select_file(fzf_file)


class fzf_select_by_line_count(Command):

    def execute(self):
        # directory = self.arg(0)
        # if not directory:
        directory = os.path.relpath(self.fm.thisdir.path)
        command = ['line-count-by-file-fzf', directory]
        fzf = self.fm.execute_command(command,
                                      universal_newlines=True,
                                      stdout=subprocess.PIPE)
        stdout, _ = fzf.communicate()
        if fzf.returncode == 0:
            line = stdout.split('\n')[0]
            # self.fm.notify(line)
            # line is formatted as "<count> <filename>"
            m = re.match(r'\s*\d+\s+(.*)$', line)
            if m:
                # NOTE: Only absolute paths work with select_file for some
                # reason.
                self.fm.select_file(os.path.abspath(m.groups()[0]))


def _split_args_to_batches(args, max_args_len):
    batches = []
    current_batch = []
    current_batch_len = 0
    for arg in args:
        arg_len = len(arg)
        if current_batch_len + arg_len > max_args_len:
            batches.append(current_batch)
            current_batch = []
            current_batch_len = 0
        current_batch.append(arg)
        current_batch_len += arg_len
    batches.append(current_batch)
    assert (sum(len(batch) for batch in batches)) == len(args)
    return batches


class trash_put(Command):
    """
    :trash_put

    Move files to XDG trash.
    """

    def execute(self):
        if self.rest(1):
            args = self.rest(1)
        elif self.fm.thistab.get_selection():
            args = [file.basename for file in self.fm.thistab.get_selection()]
        else:
            args = [self.fm.thisfile.basename]
        args_batches = _split_args_to_batches(args, 100000)
        self.fm.notify(os.getcwd())
        for batch in args_batches:
            self.fm.execute_command(['trash-put'] + batch)
