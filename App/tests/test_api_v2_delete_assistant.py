import unittest
from flask_jwt_extended import create_access_token
from App.main import create_app
from App.database import create_db, db
from App.controllers.student import create_student
from App.controllers.help_desk_assistant import create_help_desk_assistant
from App.models.time_entry import TimeEntry
from App.utils.time_utils import trinidad_now

class DeleteAssistantApiV2Tests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'JWT_SECRET_KEY': 'test-secret-key'
        })
        self.ctx = self.app.app_context()
        self.ctx.push()
        create_db()

        # Create admin user manually (bypassing registration)
        from App.models import User
        admin = User('admin_user', 'password', type='admin')
        db.session.add(admin)
        db.session.commit()
        self.admin_token = create_access_token(identity='admin_user')

        # Create assistant
        create_student('stud1', 'pw', 'BSc', 'Student One')
        create_help_desk_assistant('stud1')
        self.assistant_token = create_access_token(identity='stud1')
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _auth_delete(self, username):
        return self.client.delete(f'/api/v2/admin/assistants/{username}', headers={
            'Authorization': f'Bearer {self.admin_token}',
            'Content-Type': 'application/json'
        })

    def test_delete_assistant_success(self):
        resp = self._auth_delete('stud1')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['username'], 'stud1')

    def test_delete_nonexistent(self):
        resp = self._auth_delete('ghost')
        self.assertEqual(resp.status_code, 404)

    def test_delete_block_active_time_entry(self):
        # recreate assistant (already exists) add active time entry
        entry = TimeEntry(username='stud1', clock_in=trinidad_now(), status='active')
        db.session.add(entry)
        db.session.commit()
        resp = self._auth_delete('stud1')
        self.assertEqual(resp.status_code, 409)
        data = resp.get_json()
        self.assertFalse(data['success'])

    def test_delete_admin_forbidden(self):
        resp = self._auth_delete('admin_user')
        self.assertEqual(resp.status_code, 400)

if __name__ == '__main__':
    unittest.main()
