#!/usr/bin/env python3
"""Build two pinned language views with one backend and checked shared assets."""
import os
from pathlib import Path
import shutil
import subprocess

STAGE = Path('/root/headplane-language-20261113')
UPSTREAM = Path('/root/headplane-setup-20261113/source/tale-headplane-6f0764e')
OVERLAY = STAGE / 'overlay'
DEPS = Path('/opt/headplane-zh-source')


def replace(path, old, new):
    text = path.read_text()
    assert old in text, (str(path), old)
    path.write_text(text.replace(old, new, 1))


def command(cwd, name, *args):
    env = dict(os.environ, PATH='/opt/headplane-build/bin:' + os.environ['PATH'], HEADPLANE_VERSION='0.8.2')
    with (STAGE / f'{cwd.name}-{name}.log').open('w') as log:
        subprocess.run(args, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    print(f'{cwd.name}: {name} passed', flush=True)


def source_for(language):
    assert language in {'zh', 'en'}
    target = STAGE / language
    if target.exists():
        assert target.resolve() == STAGE / language
        shutil.rmtree(target)
    shutil.copytree(UPSTREAM, target, ignore=shutil.ignore_patterns('node_modules', 'build', '.react-router', '.git'))
    (target / 'node_modules').symlink_to(DEPS / 'node_modules', target_is_directory=True)
    assert (target / 'pnpm-lock.yaml').read_bytes() == (DEPS / 'pnpm-lock.yaml').read_bytes()
    shutil.copy2(OVERLAY / 'CHANGELOG.md', target / 'CHANGELOG.md')
    for name in ['hp_ssh.wasm', 'wasm_exec.js']:
        shutil.copy2(DEPS / 'public' / name, target / 'public' / name)
    if language == 'zh':
        shutil.copytree(OVERLAY / 'app', target / 'app', dirs_exist_ok=True)
        shutil.copytree(OVERLAY / 'tests', target / 'tests', dirs_exist_ok=True)
    else:
        # Always apply integration changes to fresh original English app sources.
        # Never copy Chinese page text into the English view.
        shutil.copytree(UPSTREAM / 'app', target / 'app', dirs_exist_ok=True)
        shared = ['utils/language.ts', 'utils/ui-language.ts', 'components/language-switcher.tsx',
                  'routes/util/language.ts', 'server/request-listener.ts', 'server/language-view.ts']
        for rel in shared:
            destination = target / 'app' / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(OVERLAY / 'app' / rel, destination)
        replace(target / 'app/utils/ui-language.ts', '= "zh-CN"', '= "en"')
        replace(target / 'app/root.tsx', 'import { getColorScheme } from "./utils/color-scheme";',
                'import { getColorScheme } from "./utils/color-scheme";\nimport { UI_LANGUAGE } from "./utils/ui-language";')
        replace(target / 'app/root.tsx', 'lang="en"', 'lang={UI_LANGUAGE}')
        for rel in ['layout/header.tsx', 'routes/auth/login/page.tsx']:
            replace(target / 'app' / rel, 'import Link from "~/components/link";',
                    'import Link from "~/components/link";\nimport LanguageSwitcher from "~/components/language-switcher";')
        replace(target / 'app/layout/header.tsx', '          <Menu>', '          <LanguageSwitcher />\n          <Menu>')
        replace(target / 'app/layout/header.tsx', 'ml-auto grid shrink-0 grid-cols-2 gap-x-4',
                'ml-auto flex shrink-0 items-center gap-x-2 sm:gap-x-4')
        replace(target / 'app/layout/header.tsx', 'text-2xl font-semibold',
                'hidden text-2xl font-semibold sm:block')
        replace(target / 'app/layout/header.tsx', 'text-sm font-medium md:flex',
                'text-sm font-medium lg:flex')
        replace(target / 'app/layout/header.tsx', 'p-2 md:hidden', 'p-2 lg:hidden')
        replace(target / 'app/routes/auth/login/page.tsx',
                '    <div className="flex h-screen w-screen items-center justify-center">',
                '    <div className="flex h-screen w-screen items-center justify-center">\n      <div className="absolute top-4 right-4"><LanguageSwitcher /></div>')
        replace(target / 'app/routes.ts', 'route("/color-scheme", "routes/util/color-scheme.ts"),',
                'route("/color-scheme", "routes/util/color-scheme.ts"),\n    route("/language", "routes/util/language.ts"),')
        config = (UPSTREAM / 'vite.config.ts').read_text()
        (target / 'vite.config.ts').write_text(config.replace('const PROD_ENTRY = "./app/server/main.ts"',
                                                          'const PROD_ENTRY = "./app/server/language-view.ts"'))
        # Language preference tests are shared; upstream English assertions stay unchanged.
        for name in ['language.test.ts', 'language-action.test.ts']:
            shutil.copy2(OVERLAY / 'tests/unit/settings' / name, target / 'tests/unit/settings' / name)
    return target


def main():
    sources = [source_for(language) for language in ['zh', 'en']]
    for source in sources:
        command(source, 'typecheck', 'pnpm', 'run', 'typecheck')
        command(source, 'lint', 'pnpm', 'run', 'lint')
        command(source, 'unit', 'pnpm', 'run', 'test:unit')
        command(source, 'build', 'pnpm', 'run', 'build')
    context = STAGE / 'image'
    # A clean assembly prevents stale resources from earlier builds.
    if context.exists():
        assert context.resolve() == STAGE / 'image'
        shutil.rmtree(context)
    context.mkdir()
    shutil.copytree(sources[0] / 'build', context / 'build')
    shutil.copytree(sources[1] / 'build/server', context / 'english/server')
    for item in (sources[1] / 'build/client').rglob('*'):
        if not item.is_file():
            continue
        relative = item.relative_to(sources[1] / 'build/client')
        if relative.parts[0] == '.vite':
            continue  # private build metadata is not a runtime resource
        destination = context / 'build/client' / relative
        if destination.exists():
            assert destination.read_bytes() == item.read_bytes(), f'Asset collision: {relative}'
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)
    shutil.copy2(OVERLAY / 'Dockerfile.language', context / 'Dockerfile')
    print('Both language builds passed; shared asset collisions checked.', flush=True)


if __name__ == '__main__':
    main()
