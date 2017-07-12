import sys
import argparse
from prompt_toolkit import prompt
from prompt_toolkit.styles import style_from_dict
from prompt_toolkit.token import Token
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.contrib.completers import WordCompleter

class InteractiveShell:
    def __init__(self, title='Interactive Shell', add_help=True):
        self.title = title
        self.style = style_from_dict({
            Token.Toolbar: '#ffffff bg:#333333',
        })
        if add_help:
            self.commands['help'] = dict(
                help = 'Show this help message',
            )
        self.history = InMemoryHistory()
        self.completer = WordCompleter(sorted(self.commands.keys()))
        self.parser = self._create_parser()

    def _create_parser(self):
        parser = argparse.ArgumentParser(
            prog=self.title, add_help=False,
            usage='{}: Use one of the available commands'.format(self.title))
        subparsers = parser.add_subparsers()
        for name, info in self.commands.items():
            if 'args' not in info:
                info['args'] = []
            parser_x = subparsers.add_parser(name, help=info['help'], usage='{} [-h] {}'.format(
                name, ' '.join((x[0] for x, y in info['args']))
            ))
            for args_def, kwargs_def in info['args']:
                parser_x.add_argument(*args_def, **kwargs_def)
        return parser

    def _get_toolbar(self, cli):
        return [(Token.Toolbar, 'Actions: {}'.format(', '.join(self.commands)))]

    def _process_input(self):
        input_ = prompt('> ', get_bottom_toolbar_tokens=self._get_toolbar,
                        style=self.style, history=self.history,
                        completer=self.completer, complete_while_typing=False)
        input_ = input_.split(' ')
        cmd = input_[0]
        args = input_[1:]
        if cmd == '':
            return
        try:
            args = self.parser.parse_args(input_)
            result = getattr(self, 'cmd_{}'.format(cmd))(args)
            if result:
                print(result)
        except SystemExit:
            pass

    def __call__(self):
        try:
            while True:
                self._process_input()
        except (EOFError, KeyboardInterrupt):
            print('Good bye!')
        except:
            print('{} thrown -> GoodBye!'.format(sys.exc_info()[0].__name__))
            raise

    # --------------------------------------------------------------------------
    # Available commands for the interactive shell
    # --------------------------------------------------------------------------

    def cmd_help(self, args):
        self.parser.print_help()
