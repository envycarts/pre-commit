from __future__ import annotations

import multiprocessing
import os
import random
import re
from typing import Any
from typing import NoReturn
from typing import Sequence

import pre_commit.constants as C
from pre_commit import parse_shebang
from pre_commit.hook import Hook
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output_b
from pre_commit.xargs import xargs

FIXED_RANDOM_SEED = 1542676187

SHIMS_RE = re.compile(r'[/\\]shims[/\\]')


def exe_exists(exe: str) -> bool:
    found = parse_shebang.find_executable(exe)
    if found is None:  # exe exists
        return False

    homedir = os.path.expanduser('~')
    try:
        common: str | None = os.path.commonpath((found, homedir))
    except ValueError:  # on windows, different drives raises ValueError
        common = None

    return (
        # it is not in a /shims/ directory
        not SHIMS_RE.search(found) and
        (
            # the homedir is / (docker, service user, etc.)
            os.path.dirname(homedir) == homedir or
            # the exe is not contained in the home directory
            common != homedir
        )
    )


def run_setup_cmd(prefix: Prefix, cmd: tuple[str, ...], **kwargs: Any) -> None:
    cmd_output_b(*cmd, cwd=prefix.prefix_dir, **kwargs)


def environment_dir(prefix: Prefix, d: str, language_version: str) -> str:
    return prefix.path(f'{d}-{language_version}')


def assert_version_default(binary: str, version: str) -> None:
    if version != C.DEFAULT:
        raise AssertionError(
            f'for now, pre-commit requires system-installed {binary} -- '
            f'you selected `language_version: {version}`',
        )


def assert_no_additional_deps(
        lang: str,
        additional_deps: Sequence[str],
) -> None:
    if additional_deps:
        raise AssertionError(
            f'for now, pre-commit does not support '
            f'additional_dependencies for {lang} -- '
            f'you selected `additional_dependencies: {additional_deps}`',
        )


def basic_get_default_version() -> str:
    return C.DEFAULT


def basic_health_check(prefix: Prefix, language_version: str) -> str | None:
    return None


def no_install(
        prefix: Prefix,
        version: str,
        additional_dependencies: Sequence[str],
) -> NoReturn:
    raise AssertionError('This type is not installable')


def target_concurrency(hook: Hook) -> int:
    if hook.require_serial or 'PRE_COMMIT_NO_CONCURRENCY' in os.environ:
        return 1
    else:
        # Travis appears to have a bunch of CPUs, but we can't use them all.
        if 'TRAVIS' in os.environ:
            return 2
        else:
            try:
                return multiprocessing.cpu_count()
            except NotImplementedError:
                return 1


def _shuffled(seq: Sequence[str]) -> list[str]:
    """Deterministically shuffle"""
    fixed_random = random.Random()
    fixed_random.seed(FIXED_RANDOM_SEED, version=1)

    seq = list(seq)
    fixed_random.shuffle(seq)
    return seq


def run_xargs(
        hook: Hook,
        cmd: tuple[str, ...],
        file_args: Sequence[str],
        **kwargs: Any,
) -> tuple[int, bytes]:
    # Shuffle the files so that they more evenly fill out the xargs partitions,
    # but do it deterministically in case a hook cares about ordering.
    file_args = _shuffled(file_args)
    kwargs['target_concurrency'] = target_concurrency(hook)
    return xargs(cmd, file_args, **kwargs)
