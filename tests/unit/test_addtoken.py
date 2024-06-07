from unittest import mock, TestCase
from add_token import print_short

class test_at(TestCase):
    @mock.patch('builtins.print')
    @mock.patch('add_token.get_network_info', return_value=['10.23.53.54', ['10.23.53.54'], str(32)])
    def test_add_token(self, addtoken, mock_print):
        # self.assertEqual(print_short('t', 'c'), 2)
        print_short('t', 'c')
        mock_print.assert_called_with('microk8s join 10.23.53.54:32/t/c')
