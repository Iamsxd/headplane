import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('build_language',Path(__file__).parents[1]/'build-language.py')
build=importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class BuildStageSafety(unittest.TestCase):
    def test_existing_language_directory_is_never_removed(self):
        for language in ['zh','en']:
            with self.subTest(language=language),tempfile.TemporaryDirectory() as name:
                stage=Path(name);target=stage/language;target.mkdir();sentinel=target/'unrelated.txt'
                sentinel.write_text('keep')
                error=None
                with patch.object(build,'STAGE',stage),patch.object(build,'UPSTREAM',stage/'missing'):
                    try:build.source_for(language)
                    except Exception as e:error=e
                self.assertTrue(sentinel.exists(),'Build removed a pre-existing directory')
                self.assertIsInstance(error,FileExistsError)

    def test_existing_image_directory_is_never_removed(self):
        with tempfile.TemporaryDirectory() as name:
            stage=Path(name);image=stage/'image';image.mkdir();sentinel=image/'unrelated.txt';sentinel.write_text('keep')
            sources=[]
            for lang in ['prepared-zh','prepared-en']:
                src=stage/lang;(src/'build/server').mkdir(parents=True);(src/'build/client').mkdir();sources.append(src)
            error=None
            with patch.object(build,'STAGE',stage),patch.object(build,'source_for',side_effect=sources),patch.object(build,'command'):
                try:build.main()
                except Exception as e:error=e
            self.assertTrue(sentinel.exists(),'Build removed a pre-existing image directory')
            self.assertIsInstance(error,FileExistsError)


if __name__=='__main__':unittest.main()
