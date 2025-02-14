from __future__ import annotations

import os.path

import pytest

from pre_commit import envcontext
from pre_commit.languages import r
from pre_commit.util import win_exe
from testing.fixtures import make_config_from_repo
from testing.fixtures import make_repo
from tests.repository_test import _get_hook_no_install


def _test_r_parsing(
    tempdir_factory,
    store,
    hook_id,
    expected_hook_expr=(),
    expected_args=(),
    config=None,
):
    repo = make_repo(tempdir_factory, 'r_hooks_repo')
    config = make_config_from_repo(repo)
    hook = _get_hook_no_install(config, store, hook_id)
    ret = r._cmd_from_hook(hook)
    expected_path = os.path.join(hook.prefix.prefix_dir, f'{hook_id}.R')
    expected = (
        'Rscript',
        '--no-save', '--no-restore', '--no-site-file', '--no-environ',
        *(expected_hook_expr or (expected_path,)),
        *expected_args,
    )
    assert ret == expected


def test_r_parsing_file_no_opts_no_args(tempdir_factory, store):
    hook_id = 'parse-file-no-opts-no-args'
    _test_r_parsing(tempdir_factory, store, hook_id)


def test_r_parsing_file_opts_no_args(tempdir_factory, store):
    with pytest.raises(ValueError) as excinfo:
        r._entry_validate(['Rscript', '--no-init', '/path/to/file'])

    msg = excinfo.value.args
    assert msg == (
        'The only valid syntax is `Rscript -e {expr}`',
        'or `Rscript path/to/hook/script`',
    )


def test_r_parsing_file_no_opts_args(tempdir_factory, store):
    hook_id = 'parse-file-no-opts-args'
    expected_args = ['--no-cache']
    _test_r_parsing(
        tempdir_factory, store, hook_id, expected_args=expected_args,
    )


def test_r_parsing_expr_no_opts_no_args1(tempdir_factory, store):
    hook_id = 'parse-expr-no-opts-no-args-1'
    _test_r_parsing(
        tempdir_factory, store, hook_id, expected_hook_expr=('-e', '1+1'),
    )


def test_r_parsing_expr_no_opts_no_args2(tempdir_factory, store):
    with pytest.raises(ValueError) as execinfo:
        r._entry_validate(['Rscript', '-e', '1+1', '-e', 'letters'])
    msg = execinfo.value.args
    assert msg == ('You can supply at most one expression.',)


def test_r_parsing_expr_opts_no_args2(tempdir_factory, store):
    with pytest.raises(ValueError) as execinfo:
        r._entry_validate(
            ['Rscript', '--vanilla', '-e', '1+1', '-e', 'letters'],
        )
    msg = execinfo.value.args
    assert msg == (
        'The only valid syntax is `Rscript -e {expr}`',
        'or `Rscript path/to/hook/script`',
    )


def test_r_parsing_expr_args_in_entry2(tempdir_factory, store):
    with pytest.raises(ValueError) as execinfo:
        r._entry_validate(['Rscript', '-e', 'expr1', '--another-arg'])

    msg = execinfo.value.args
    assert msg == ('You can supply at most one expression.',)


def test_r_parsing_expr_non_Rscirpt(tempdir_factory, store):
    with pytest.raises(ValueError) as execinfo:
        r._entry_validate(['AnotherScript', '-e', '{{}}'])

    msg = execinfo.value.args
    assert msg == ('entry must start with `Rscript`.',)


def test_r_parsing_file_local(tempdir_factory, store):
    config = {
        'repo': 'local',
        'hooks': [{
            'id': 'local-r',
            'name': 'local-r',
            'entry': 'Rscript path/to/script.R',
            'language': 'r',
        }],
    }
    hook = _get_hook_no_install(config, store, 'local-r')
    ret = r._cmd_from_hook(hook)
    assert ret == (
        'Rscript',
        '--no-save', '--no-restore', '--no-site-file', '--no-environ',
        hook.prefix.path('path/to/script.R'),
    )


def test_rscript_exec_relative_to_r_home():
    expected = os.path.join('r_home_dir', 'bin', win_exe('Rscript'))
    with envcontext.envcontext((('R_HOME', 'r_home_dir'),)):
        assert r._rscript_exec() == expected


def test_path_rscript_exec_no_r_home_set():
    with envcontext.envcontext((('R_HOME', envcontext.UNSET),)):
        assert r._rscript_exec() == 'Rscript'
