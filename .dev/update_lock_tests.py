from pathlib import Path
p = Path(__file__).resolve().parent / 'simulator-work/tests/test_sync_v20.py'
s = p.read_text(encoding='utf-8')
start = s.index('    def test_local_preparation')
end = s.index('    def parity', start)
s = s[:start] + '''    def test_local_preparation_verifies_exact_sources_before_writing(self):
        from scripts.prepare_engine import prepare
        contents = Runner().verify_engine()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / 'source', root / 'output'
            (source / 'python').mkdir(parents=True)
            for name, content in contents.items():
                (source / 'python' / name).write_bytes(content)
            prepare(source, destination)
            self.assertEqual({p.name: p.read_bytes() for p in destination.iterdir()}, contents)
            with self.assertRaises(SystemExit):
                prepare(source, destination)
            with (source / 'python/combats.py').open('ab') as stream:
                stream.write(b'\\n# Unvalidated change\\n')
            with self.assertRaises(SystemExit):
                prepare(source, root / 'invalid')
            self.assertFalse((root / 'invalid').exists())

    def test_commit_preparation_uses_verified_git_blobs(self):
        from scripts.prepare_engine import prepare
        contents = Runner().verify_engine()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'backend').mkdir()
            lock = dict(LOCK, source_mode='git')
            (root / 'backend/engine.lock.json').write_text(json.dumps(lock))
            def git_blob(command):
                name = command[-1].removeprefix(LOCK['commit'] + ':python/')
                self.assertEqual(command, ['git', '-C', str(root), 'show',
                                           LOCK['commit'] + ':python/' + name])
                return contents[name]
            with patch('scripts.prepare_engine.ROOT', root):
                with patch('scripts.prepare_engine.subprocess.check_output', side_effect=git_blob):
                    prepare(root, root / 'output')
                self.assertEqual({p.name: p.read_bytes() for p in (root / 'output').iterdir()}, contents)
                with patch('scripts.prepare_engine.subprocess.check_output', return_value=b'altered blob'):
                    with self.assertRaises(SystemExit):
                        prepare(root, root / 'invalid')
                self.assertFalse((root / 'invalid').exists())

''' + s[end:]
p.write_text(s, encoding='utf-8', newline='\n')
