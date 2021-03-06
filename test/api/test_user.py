import os
import uuid
import random
import unittest
import pprint
from langcodes import Language

from google.protobuf.json_format import MessageToDict
from spaceone.core import utils, pygrpc
from spaceone.core.unittest.runner import RichTestRunner


def random_string():
    return uuid.uuid4().hex


class TestUser(unittest.TestCase):
    config = utils.load_yaml_from_file(
        os.environ.get('SPACEONE_TEST_CONFIG_FILE', './config.yml'))

    pp = pprint.PrettyPrinter(indent=4)
    identity_v1 = None
    domain = None
    domain_owner = None
    owner_id = None
    owner_pw = None
    token = None

    @classmethod
    def setUpClass(cls) -> None:
        super(TestUser, cls).setUpClass()
        endpoints = cls.config.get('ENDPOINTS', {})
        cls.identity_v1 = pygrpc.client(endpoint=endpoints.get('identity', {}).get('v1'), version='v1')

        cls._create_domain()
        cls._create_domain_owner()
        cls._issue_owner_token()

    @classmethod
    def tearDownClass(cls) -> None:
        super(TestUser, cls).tearDownClass()
        cls.identity_v1.DomainOwner.delete({
            'domain_id': cls.domain.domain_id,
            'owner_id': cls.owner_id
        })
        print(f'>> delete domain owner: {cls.owner_id}')

        if cls.domain:
            cls.identity_v1.Domain.delete({'domain_id': cls.domain.domain_id})
            print(f'>> delete domain: {cls.domain.name} ({cls.domain.domain_id})')

    @classmethod
    def _create_domain(cls):
        name = utils.random_string()
        params = {
            'name': name,
            'config': {
                'config_key': 'config_value'
            }
        }
        cls.domain = cls.identity_v1.Domain.create(params)

    @classmethod
    def _create_domain_owner(cls):
        cls.owner_id = utils.random_string()[0:10]
        cls.owner_pw = 'qwerty'

        owner = cls.identity_v1.DomainOwner.create({
            'owner_id': cls.owner_id,
            'password': cls.owner_pw,
            'domain_id': cls.domain.domain_id
        })

        cls.domain_owner = owner
        print(f'owner_id: {cls.owner_id}')
        print(f'owner_pw: {cls.owner_pw}')

    @classmethod
    def _issue_owner_token(cls):
        token_params = {
            'credentials': {
                'user_type': 'DOMAIN_OWNER',
                'user_id': cls.owner_id,
                'password': cls.owner_pw
            },
            'domain_id': cls.domain.domain_id
        }

        issue_token = cls.identity_v1.Token.issue(token_params)
        cls.token = issue_token.access_token
        print(f'token: {cls.token}')

    def setUp(self) -> None:
        self.user = None
        self.users = []
        self.policy = None
        self.policies = []
        self.role = None
        self.roles = []

    def tearDown(self) -> None:
        print()
        for user in self.users:
            print(f'[tearDown] Delete User. {user.user_id}')
            self.identity_v1.User.delete(
                {'user_id': user.user_id,
                 'domain_id': self.domain.domain_id},
                metadata=(('token', self.token),)
            )

        for role in self.roles:
            print(f'[tearDown] Delete Role. {role.role_id}')
            self.identity_v1.Role.delete(
                {'role_id': role.role_id,
                 'domain_id': self.domain.domain_id},
                metadata=(('token', self.token),)
            )

        for policy in self.policies:
            print(f'[tearDown] Delete Policy. {policy.policy_id}')
            self.identity_v1.Policy.delete(
                {'policy_id': policy.policy_id,
                 'domain_id': self.domain.domain_id},
                metadata=(('token', self.token),)
            )

    def _print_data(self, message, description=None):
        print()
        if description:
            print(f'[ {description} ]')

        self.pp.pprint(MessageToDict(message, preserving_proto_field_name=True))

    def _test_create_policy(self, permissions):
        params = {
            'name': 'Policy-' + random_string()[0:5],
            'permissions': permissions,
            'domain_id': self.domain.domain_id
        }

        self.policy = self.identity_v1.Policy.create(
            params,
            metadata=(('token', self.token),)
        )

        self.policies.append(self.policy)

    def _test_create_role(self, policies, role_type='PROJECT'):
        params = {
            'name': 'Role-' + random_string()[0:5],
            'role_type': role_type,
            'policies': policies,
            'domain_id': self.domain.domain_id
        }

        self.role = self.identity_v1.Role.create(
            params,
            metadata=(('token', self.token),))

        self.roles.append(self.role)

    def test_create_user(self, user_id=None, name=None):
        lang_code = random.choice(['zh-hans', 'jp', 'ko', 'en', 'es'])
        language = Language.get(lang_code)
        if user_id is None:
            user_id = utils.random_string()[0:10]

        if name is None:
            name = 'Steven' + utils.random_string()[0:5]

        params = {
            'user_id': user_id,
            'password': 'qwerty123',
            'name': name,
            'language': language.__str__(),
            'tags': {'key': 'value'},
            'email': 'Steven' + utils.random_string()[0:5] + '@mz.co.kr',
            'mobile': '+821026671234',
            'group': 'group-id',
            'domain_id': self.domain.domain_id
        }

        user = self.identity_v1.User.create(
            params,
            metadata=(('token', self.token),)
        )
        self.user = user
        self.users.append(user)
        self._print_data(self.user, 'test_create_user')
        self.assertEqual(self.user.name, params['name'])

    def test_create_duplicate_user(self):
        user_id = utils.random_string()[0:10]
        self.test_create_user(user_id=user_id)

        with self.assertRaises(Exception) as e:
            self.test_create_user(user_id=user_id)

        self.assertIn("ERROR_NOT_UNIQUE_KEYS", str(e.exception))

    def test_update_user(self, name=None):
        self.test_create_user()

        if name is None:
            name = 'Steven' + utils.random_string()[0:5]

        params = {
            'user_id': self.user.user_id,
            'name': name,
            'domain_id': self.domain.domain_id
        }
        self.user = self.identity_v1.User.update(
            params,
            metadata=(('token', self.token),)
        )
        self.assertEqual(self.user.name, params['name'])

    def test_update_long_user_name(self):
        self.test_create_user()
        params = {
            'user_id': self.user.user_id,
            'name': 'a' * 129,
            'domain_id': self.domain.domain_id
        }

        with self.assertRaises(Exception):
            self.user = self.identity_v1.User.update(
                params,
                metadata=(('token', self.token),)
            )

    def test_update_not_exists_enum(self):
        self.test_create_user()
        params = {
            'user_id': self.user.user_id,
            'state': 'HELLO',
            'domain_id': self.domain.domain_id
        }

        with self.assertRaises(Exception):
            self.user = self.identity_v1.User.update(
                params,
                metadata=(('token', self.token),)
            )

    def test_delete_non_existing_user(self):
        params = {
            'user_id': 'hello',
            'domain_id': self.domain.domain_id
        }

        with self.assertRaises(Exception):
            self.identity_v1.User.delete(params, self.user.user_id,
                                         metadata=(('token', self.token),))

    def test_update_tags(self):
        self.test_create_user()
        params = {
            'user_id': self.user.user_id,
            'tags': {
                'update_key': 'update_value'
            },
            'domain_id': self.domain.domain_id
        }
        self.user = self.identity_v1.User.update(
            params,
            metadata=(('token', self.token),)
        )

        self.assertEqual(self.user.tags, params['tags'])

    def test_enable_user(self):
        self.test_create_user()
        params = {
            'user_id': self.user.user_id,
            'domain_id': self.domain.domain_id
        }

        user = self.identity_v1.User.enable(
            params,
            metadata=(('token', self.token),)
        )
        self.assertEqual(user.state, 1)

    def test_disable_user(self):
        self.test_create_user()
        params = {
            'user_id': self.user.user_id,
            'domain_id': self.domain.domain_id
        }

        user = self.identity_v1.User.disable(
            params,
            metadata=(('token', self.token),)
        )
        self.assertEqual(user.state, 2)

    def test_enable_user_without_user_id(self):
        self.test_create_user()
        params = {
            'user_id': None,
            'domain_id': self.domain.domain_id
        }
        with self.assertRaises(Exception):
            self.user = self.identity_v1.User.enable(
                params,
                metadata=(('token', self.token),)
            )
        params = {
            'user_id': '',
            'domain_id': self.domain.domain_id
        }
        with self.assertRaises(Exception):
            self.user = self.identity_v1.User.enable(
                params,
                metadata=(('token', self.token),)
            )

    def test_get_user(self):
        self.test_create_user()
        params = {
            'user_id': self.user.user_id,
            'domain_id': self.domain.domain_id
        }
        user = self.identity_v1.User.get(
            params,
            metadata=(('token', self.token),)
        )

        self.assertEqual(user.user_id, params['user_id'])

    def test_get_not_exists_user(self):
        params = {
            'user_id': 'abc',
            'domain_id': self.domain.domain_id
        }
        with self.assertRaises(Exception):
            self.identity_v1.User.get(
                params,
                metadata=(('token', self.token),)
            )

    def test_update_role(self, role_types=['DOMAIN', 'DOMAIN']):
        self.test_create_user()
        self._test_create_policy([
                'identity.Domain.get',
                'identity.Domain.list',
                'identity.Project.*',
                'identity.ProjectGroup.*',
                'identity.User.get',
                'identity.User.update',
            ])
        self._test_create_policy(['inventory.*'])

        self._test_create_role([{
            'policy_type': 'CUSTOM',
            'policy_id': self.policies[0].policy_id}], role_types[0])
        self._test_create_role([{
            'policy_type': 'CUSTOM',
            'policy_id': self.policies[1].policy_id}], role_types[1])

        params = {
            'user_id': self.user.user_id,
            'domain_id': self.domain.domain_id,
            'roles': list(map(lambda role: role.role_id, self.roles))
        }
        self.user = self.identity_v1.User.update_role(
            params,
            metadata=(('token', self.token),)
        )

        self._print_data(self.user, 'test_update_role')
        self.assertEqual(len(self.roles), len(self.user.roles))

    def test_update_domain_and_project_role(self):
        self.test_update_role(['DOMAIN', 'PROJECT'])

    def test_update_system_and_project_role(self):
        with self.assertRaises(Exception):
            self.test_update_role(['SYSTEM', 'PROJECT'])

    def test_delete_role_exist_user(self):
        self.test_update_role(['DOMAIN', 'PROJECT'])

        with self.assertRaises(Exception) as e:
            self.identity_v1.Role.delete(
                {
                    'role_id': self.role.role_id,
                    'domain_id': self.domain.domain_id
                },
                metadata=(('token', self.token),)
            )

        self.assertIn("ERROR_EXIST_RESOURCE", str(e.exception))

    def test_list_user(self):
        self.test_create_user()
        self.test_create_user()
        self.test_create_user()

        params = {
            'domain_id': self.domain.domain_id,
            'query': {
                'filter': [
                    {
                        'k': 'user_id',
                        'v': list(map(lambda user: user.user_id, self.users)),
                        'o': 'in'
                    }
                ]
            }
        }

        response = self.identity_v1.User.list(
            params,
            metadata=(('token', self.token),)
        )
        self.assertEqual(len(self.users), response.total_count)

    def test_list_user_query_filter(self):
        self.test_create_user()
        self.test_create_user()
        self.test_create_user()

        response = self.identity_v1.User.list({
            'group': 'group-id',
            'domain_id': self.domain.domain_id
        }, metadata=(('token', self.token),)
        )
        self.assertEqual(len(self.users), response.total_count)

    def test_list_user_role_id(self):
        self.test_update_role()

        response = self.identity_v1.User.list({
            'role_id': self.role.role_id,
            'domain_id': self.domain.domain_id
        }, metadata=(('token', self.token),)
        )

        self._print_data(response, 'test_list_user_role_id')

        self.assertEqual(len(self.users), response.total_count)

    def test_user_id_must_unique_in_domain(self):
        self.test_create_user('user-id-john')

        with self.assertRaises(Exception):
            self.test_create_user('user-id-john')

    def test_find_user(self):
        token_param = {
            'credentials': {
                'user_type': 'DOMAIN_OWNER',
                'user_id': self.owner_id,
                'password': self.owner_pw
            },
            'domain_id': self.domain.domain_id
        }

        issue_token = self.identity_v1.Token.issue(token_param)
        token = issue_token.access_token

        users = self.identity_v1.User.find(
            {
                'search': {
                    'user_id': 'test_user'
                },
                'domain_id': self.domain.domain_id
            },
            metadata=(('token', token),)
        )
        print(f'users: {users}')

    def test_stat_user(self):
        self.test_list_user()

        params = {
            'domain_id': self.domain.domain_id,
            'query': {
                'aggregate': {
                    'group': {
                        'keys': [{
                            'key': 'user_id',
                            'name': 'Id'
                        }],
                        'fields': [{
                            'operator': 'count',
                            'name': 'Count'
                        }]
                    }
                },
                'sort': {
                    'name': 'Count',
                    'desc': True
                }
            }
        }

        result = self.identity_v1.User.stat(
            params, metadata=(('token', self.token),))

        self._print_data(result, 'test_stat_user')


if __name__ == "__main__":
    unittest.main(testRunner=RichTestRunner)
