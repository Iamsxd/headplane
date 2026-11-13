"""Regression checks for concurrent operator changes and scoped recovery."""
from importlib.machinery import SourceFileLoader
from contextlib import contextmanager, closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

deploy = SourceFileLoader('deploy_casdoor_test', str(Path(__file__).parents[1] / 'deploy-casdoor.py')).load_module()


class OwnerMigration(unittest.TestCase):
    @contextmanager
    def connection(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            yield db

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / 'owner.db'
        self.before = {'id': 'owner-id', 'sub': 'proxy:admin', 'role': 'owner', 'caps': 7, 'headscale_user_id': '1'}
        with self.connection() as db:
            db.execute('CREATE TABLE users (id TEXT PRIMARY KEY, sub TEXT UNIQUE, role TEXT, caps INTEGER, headscale_user_id TEXT)')
            db.execute('CREATE TABLE auth_sessions (id TEXT)')
            db.execute('INSERT INTO users VALUES (?,?,?,?,?)', tuple(self.before.values()))
        (self.root / 'state.json').write_text(json.dumps({'owner': self.before, 'new_subject': 'provider-sub', 'network_identity': {}}))

    def tearDown(self):
        self.temp.cleanup()

    def read(self):
        with self.connection() as db:
            return db.execute('SELECT sub,role,caps,headscale_user_id FROM users WHERE id=?', ('owner-id',)).fetchone()

    def rollback(self):
        with patch.object(deploy, 'ROLLBACK', self.root), patch.object(deploy, 'DB', self.path), patch.object(deploy, 'FILES', {}), patch.object(deploy, 'identity', return_value={}), patch.object(deploy.subprocess, 'run'):
            deploy.rollback()

    def test_rollback_preserves_permissions_and_link_changed_after_cutover(self):
        with self.connection() as db:
            db.execute('UPDATE users SET sub=?,role=?,caps=?,headscale_user_id=?', ('provider-sub', 'admin', 11, '9'))
        self.rollback()
        self.assertEqual(self.read(), ('proxy:admin', 'admin', 11, '9'))

    def test_rollback_refuses_an_unrelated_later_subject_change(self):
        with self.connection() as db:
            db.execute('UPDATE users SET sub=?', ('another-provider',))
        with self.assertRaisesRegex(RuntimeError, 'subject'):
            self.rollback()
        self.assertEqual(self.read()[0], 'another-provider')

    def test_migration_rejects_owner_change_since_preflight(self):
        with self.connection() as db:
            db.execute('UPDATE users SET headscale_user_id=?', ('9',))
        with self.connection() as db:
            with self.assertRaises(RuntimeError):
                deploy.migrate_owner(db, self.before, 'provider-sub')
        self.assertEqual(self.read(), ('proxy:admin', 'owner', 7, '9'))

    def test_migration_changes_only_subject_and_removes_old_sessions(self):
        with self.connection() as db:
            db.execute('INSERT INTO auth_sessions VALUES (?)', ('old-session',))
        with self.connection() as db:
            deploy.migrate_owner(db, self.before, 'provider-sub')
        self.assertEqual(self.read(), ('provider-sub', 'owner', 7, '1'))
        with self.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM auth_sessions').fetchone()[0], 0)

    def test_rollback_is_idempotent_when_owner_subject_is_already_old(self):
        self.rollback()
        self.rollback()
        self.assertEqual(self.read(), ('proxy:admin', 'owner', 7, '1'))


if __name__ == '__main__':
    unittest.main()
