import unittest
from unittest.mock import patch
from mongoengine import connect, disconnect

from spaceone.core.error import *
from spaceone.core.unittest.result import print_data
from spaceone.core.unittest.runner import RichTestRunner
from spaceone.core import config
from spaceone.core.model.mongo_model import MongoModel
from spaceone.core.transaction import Transaction
from spaceone.identity.service.provider_service import ProviderService
from spaceone.identity.model.provider_model import Provider
from spaceone.identity.manager.provider_manager import ProviderManager
from spaceone.identity.info.provider_info import *
from spaceone.identity.info.common_info import StatisticsInfo
from test.factory.provider_factory import ProviderFactory


class TestProviderService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        config.init_conf(package='spaceone.identity')
        connect('test', host='mongomock://localhost')
        cls.transaction = Transaction({
            'service': 'identity',
            'api_class': 'Provider'
        })
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        disconnect()

    @patch.object(MongoModel, 'connect', return_value=None)
    def tearDown(self, *args) -> None:
        print('(tearDown) ==> Delete all providers')
        provider_mgr = ProviderManager()
        provider_vos, total_count = provider_mgr.list_providers()
        provider_vos.delete()

    @patch.object(MongoModel, 'connect', return_value=None)
    def test_create_provider(self, *args):
        params = {
            'provider': 'DK corp',
            'name': 'AWS',
            'template': {
                'service_account': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'account_id': {
                                'title': 'Account ID',
                                'type': 'string'
                            }
                        },
                        'required': ['account_id']
                    }
                }
            },
            'metadata': {
                'view': {
                    'layouts': {
                        'help:service_account:create': {
                            'name': 'Creation Help',
                            'type': 'markdown',
                            'options': {
                                'markdown': {
                                    'en': (
                                        '### Finding Your AWS Account ID\n'
                                        'You can find your account ID in the AWS Management Console, or using the AWS CLI or AWS API.\n'
                                        '#### Finding your account ID (Console)\n'
                                        'In the navigation bar, choose **Support**, and then **Support Center**. '
                                        'Your currently signed-in 12-digit account number (ID) appears in the **Support Center** title bar.'
                                    )
                                }
                            }
                        }
                    }
                }
            },
            'capability': {
                'supported_schema': ['schema-aaa', 'schema-bbb']
            },
            'tags': {
                'key': 'value'
            }
        }

        self.transaction.method = 'create'
        provider_svc = ProviderService(transaction=self.transaction)
        provider_vo = provider_svc.create_provider(params.copy())

        print_data(provider_vo.to_dict(), 'test_create_provider')
        ProviderInfo(provider_vo)

        self.assertIsInstance(provider_vo, Provider)
        self.assertEqual(params['provider'], provider_vo.provider)
        self.assertEqual(params['name'], provider_vo.name)
        self.assertEqual(params['template'], provider_vo.template)
        self.assertEqual(params['metadata'], provider_vo.metadata)
        self.assertEqual(params['capability'], provider_vo.capability)
        self.assertEqual(params['tags'], provider_vo.tags)

    @patch.object(MongoModel, 'connect', return_value=None)
    def test_create_duplicated_provider(self, *args):
        params = {
            'provider': 'duplicated_provider',
            'name': 'Duplicated Provider'
        }

        self.transaction.method = 'create'
        provider_svc = ProviderService(transaction=self.transaction)
        provider_svc.create_provider(params.copy())

        with self.assertRaises(ERROR_NOT_UNIQUE_KEYS) as e:
            provider_svc = ProviderService(transaction=self.transaction)
            provider_svc.create_provider(params.copy())

    @patch.object(MongoModel, 'connect', return_value=None)
    def test_update_provider(self, *args):
        new_provider_vo = ProviderFactory(provider='aws')
        params = {
            'provider': new_provider_vo.provider,
            'name': 'Update AWS',
            'template': {
            },
            'metadata': {
            },
            'tags': {
                'update_key': 'update_value'
            }
        }

        self.transaction.method = 'update'
        provider_svc = ProviderService(transaction=self.transaction)
        provider_vo = provider_svc.update_provider(params.copy())

        print_data(provider_vo.to_dict(), 'test_update_provider')
        ProviderInfo(provider_vo)

        self.assertIsInstance(provider_vo, Provider)
        self.assertEqual(new_provider_vo.provider, provider_vo.provider)
        self.assertEqual(params['name'], provider_vo.name)
        self.assertEqual(params['template'], provider_vo.template)
        self.assertEqual(params['metadata'], provider_vo.metadata)
        self.assertEqual(params['tags'], provider_vo.tags)

    @patch.object(MongoModel, 'connect', return_value=None)
    def test_delete_provider(self, *args):
        new_provider_vo = ProviderFactory()
        params = {
            'provider': new_provider_vo.provider
        }

        self.transaction.method = 'delete'
        provider_svc = ProviderService(transaction=self.transaction)
        result = provider_svc.delete_provider(params)

        self.assertIsNone(result)

    @patch.object(MongoModel, 'connect', return_value=None)
    def test_get_provider(self, *args):
        new_provider_vo = ProviderFactory()
        params = {
            'provider': new_provider_vo.provider
        }

        self.transaction.method = 'get'
        provider_svc = ProviderService(transaction=self.transaction)
        provider_vo = provider_svc.get_provider(params)

        print_data(provider_vo.to_dict(), 'test_get_provider')
        ProviderInfo(provider_vo)

        self.assertIsInstance(provider_vo, Provider)

    @patch.object(MongoModel, 'connect', return_value=None)
    def test_generate_default_provider_by_list_providers_method(self, *args):
        params = {
            'provider': 'aws'
        }

        self.transaction.method = 'list'
        provider_svc = ProviderService(transaction=self.transaction)
        providers_vos, total_count = provider_svc.list_providers(params)

        print_data(providers_vos, 'test_generate_default_provider_by_list_providers_method')
        ProvidersInfo(providers_vos, total_count)

        self.assertEqual(len(providers_vos), 1)
        self.assertIsInstance(providers_vos[0], Provider)
        self.assertEqual(total_count, 1)

    @patch.object(MongoModel, 'connect', return_value=None)
    def test_list_providers_by_provider(self, *args):
        provider_vos = ProviderFactory.build_batch(10)
        list(map(lambda vo: vo.save(), provider_vos))

        params = {
            'provider': provider_vos[0].provider
        }

        self.transaction.method = 'list'
        provider_svc = ProviderService(transaction=self.transaction)
        providers_vos, total_count = provider_svc.list_providers(params)

        ProvidersInfo(providers_vos, total_count)

        self.assertEqual(len(providers_vos), 1)
        self.assertIsInstance(providers_vos[0], Provider)
        self.assertEqual(total_count, 1)

    @patch.object(MongoModel, 'connect', return_value=None)
    def test_list_providers_by_name(self, *args):
        provider_vos = ProviderFactory.build_batch(10)
        list(map(lambda vo: vo.save(), provider_vos))

        params = {
            'name': provider_vos[0].name
        }

        self.transaction.method = 'list'
        provider_svc = ProviderService(transaction=self.transaction)
        providers_vos, total_count = provider_svc.list_providers(params)

        ProvidersInfo(providers_vos, total_count)

        self.assertEqual(len(providers_vos), 1)
        self.assertIsInstance(providers_vos[0], Provider)
        self.assertEqual(total_count, 1)

    @patch.object(MongoModel, 'connect', return_value=None)
    def test_list_providers_by_tag(self, *args):
        ProviderFactory(tags={'tag_key': 'tag_value'})
        provider_vos = ProviderFactory.build_batch(9)
        list(map(lambda vo: vo.save(), provider_vos))

        params = {
            'query': {
                'filter': [{
                    'k': 'tags.tag_key',
                    'v': 'tag_value',
                    'o': 'eq'
                }]
            }
        }

        self.transaction.method = 'list'
        provider_svc = ProviderService(transaction=self.transaction)
        providers_vos, total_count = provider_svc.list_providers(params)

        ProvidersInfo(providers_vos, total_count)

        self.assertEqual(len(providers_vos), 1)
        self.assertIsInstance(providers_vos[0], Provider)
        self.assertEqual(total_count, 1)

    @patch.object(MongoModel, 'connect', return_value=None)
    def test_stat_provider(self, *args):
        provider_vos = ProviderFactory.build_batch(10)
        list(map(lambda vo: vo.save(), provider_vos))

        params = {
            'query': {
                'aggregate': {
                    'group': {
                        'keys': [{
                            'key': 'provider',
                            'name': 'Provider'
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

        self.transaction.method = 'stat'
        provider_svc = ProviderService(transaction=self.transaction)
        values = provider_svc.stat(params)
        StatisticsInfo(values)

        print_data(values, 'test_stat_provider')


if __name__ == "__main__":
    unittest.main(testRunner=RichTestRunner)
