import unittest
from unittest.mock import patch, ANY
from sdbot import extract_prompt, ping, load_concatenated_json, render_image


class ExtractPromptTestCase(unittest.TestCase):
    def test_extract_prompt(self):
        self.assertEqual(extract_prompt('Hello @testuser\nThis is a prompt', 'testuser'), 'This is a prompt')
        self.assertEqual(extract_prompt('Hello @testuser This is a prompt\nThis is another line', 'testuser'), 'This is a prompt')
        self.assertEqual(extract_prompt('@testuser This is a prompt\nThis is another line\nThis is the last line', 'testuser'), 'This is a prompt')


class PingTestCase(unittest.TestCase):

    @unittest.mock.patch('requests.get')
    def test_ping(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'status': 'Online'}
        self.assertTrue(ping())
        mock_get.return_value.json.return_value = {'status': 'Rendering'}
        self.assertTrue(ping())
        mock_get.return_value.status_code = 404
        self.assertFalse(ping())
        mock_get.side_effect = Exception
        self.assertFalse(ping())


class LoadConcatenatedJsonTestCase(unittest.TestCase):
    def test_load_concatenated_json(self):
        assert load_concatenated_json('{"a": 1}{"b": 2}') == [{'a': 1}, {'b': 2}]
        assert load_concatenated_json('{"a": 1}{"b": 2}{"c": 3}') == [{'a': 1}, {'b': 2}, {'c': 3}]
        #test empty string
        assert load_concatenated_json('') == []
        #test invalid json
        assert load_concatenated_json('{"a": 1}{"b": 2}{"c": 3') == [{'a': 1}, {'b': 2}]



SD_SERVER_URL = 'http://localhost:8000'
class RenderImageTestCase(unittest.TestCase):

    @unittest.mock.patch('requests.post')
    def test_render_image(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'task': '1234567890'}
        self.assertEqual(render_image('This is a prompt'), '1234567890')






if __name__ == '__main__':
    unittest.main()
