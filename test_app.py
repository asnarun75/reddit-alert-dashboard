import unittest
from unittest.mock import patch, MagicMock
import os
import datetime
import pandas as pd

# Set environment variables for testing before importing app
os.environ['MYSQL_HOST'] = 'testhost'
os.environ['MYSQL_USER'] = 'testuser'
os.environ['MYSQL_PASSWORD'] = 'testpassword'
os.environ['MYSQL_DATABASE'] = 'testdb'

# It's important that app is imported after env vars are set,
# and after dummy files/dirs it might interact with at import time are ready.
import app as flask_app  # Renamed to avoid conflict with app variable in test methods

class TestAppBehavior(unittest.TestCase):

    def setUp(self):
        flask_app.app.config['TESTING'] = True
        flask_app.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for easier testing
        self.client = flask_app.app.test_client()

        # Ensure static directory exists, as plt.savefig might try to write to it
        if not os.path.exists('static'):
            os.makedirs('static')

    # Sample data to be returned by fetchall
    sample_db_records = [
        {'id': 1, 'timestamp': datetime.datetime(2023, 1, 1, 10, 0, 0), 'matched_keyword': 'meditation', 'sentiment': 'positive', 'subreddit': 'r/mindfulness'},
        {'id': 2, 'timestamp': datetime.datetime(2023, 1, 2, 11, 0, 0), 'matched_keyword': 'yoga', 'sentiment': 'neutral', 'subreddit': 'r/yoga'},
    ]

    @patch('app.plt.savefig') # Mock savefig to prevent actual file saving
    @patch('app.mysql.connector.connect')
    @patch('app.render_template')
    def test_valid_dates(self, mock_render_template, mock_connect, mock_savefig):
        print("Running test_valid_dates")
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = self.sample_db_records

        response = self.client.post('/', data={
            'start_date': '2023-01-01',
            'end_date': '2023-01-07'
        })
        self.assertEqual(response.status_code, 200)
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        self.assertEqual(args[0], 'results.html')
        self.assertTrue('data' in kwargs)
        self.assertIsInstance(kwargs['data'], pd.DataFrame)
        self.assertFalse(kwargs['data'].empty)
        self.assertEqual(kwargs['heatmap'], 'static/heatmap.png')

        # Check if get_data was called with correct dates by inspecting cursor.execute
        mock_cursor.execute.assert_called_once()
        query_args = mock_cursor.execute.call_args[0][1]
        self.assertEqual(query_args[0], "2023-01-01 00:00:00")
        self.assertEqual(query_args[1], "2023-01-07 23:59:59")
        print("test_valid_dates finished")

    @patch('app.plt.savefig')
    @patch('app.mysql.connector.connect')
    @patch('app.render_template')
    def test_empty_dates_defaults(self, mock_render_template, mock_connect, mock_savefig):
        print("Running test_empty_dates_defaults")
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = self.sample_db_records

        response = self.client.post('/', data={
            'start_date': '',
            'end_date': ''
        })
        self.assertEqual(response.status_code, 200)
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        self.assertEqual(args[0], 'results.html')
        self.assertTrue('data' in kwargs)
        self.assertIsInstance(kwargs['data'], pd.DataFrame)

        # Check if get_data was called with default dates
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        seven_days_ago_str = (datetime.date.today() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')

        mock_cursor.execute.assert_called_once()
        query_args = mock_cursor.execute.call_args[0][1]
        self.assertEqual(query_args[0], f"{seven_days_ago_str} 00:00:00")
        self.assertEqual(query_args[1], f"{today_str} 23:59:59")
        print("test_empty_dates_defaults finished")

    @patch('app.render_template')
    def test_invalid_start_date_format(self, mock_render_template):
        print("Running test_invalid_start_date_format")
        response = self.client.post('/', data={
            'start_date': '2023/01/01', # Invalid format
            'end_date': '2023-01-07'
        })
        self.assertEqual(response.status_code, 200) # Renders index, so 200
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        self.assertEqual(args[0], 'index.html')
        self.assertEqual(kwargs['error_message'], "Invalid date format. Please use YYYY-MM-DD.")
        self.assertTrue('today' in kwargs)
        self.assertTrue('default_start' in kwargs)
        print("test_invalid_start_date_format finished")

    @patch('app.render_template')
    def test_invalid_end_date_format(self, mock_render_template):
        print("Running test_invalid_end_date_format")
        response = self.client.post('/', data={
            'start_date': '2023-01-01',
            'end_date': '31-01-2023' # Invalid format
        })
        self.assertEqual(response.status_code, 200)
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        self.assertEqual(args[0], 'index.html')
        self.assertEqual(kwargs['error_message'], "Invalid date format. Please use YYYY-MM-DD.")
        print("test_invalid_end_date_format finished")

    @patch('app.render_template')
    def test_valid_start_invalid_end_date(self, mock_render_template):
        print("Running test_valid_start_invalid_end_date")
        response = self.client.post('/', data={
            'start_date': '2023-01-01',
            'end_date': 'invalid-date'
        })
        self.assertEqual(response.status_code, 200)
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        self.assertEqual(args[0], 'index.html')
        self.assertEqual(kwargs['error_message'], "Invalid date format. Please use YYYY-MM-DD.")
        print("test_valid_start_invalid_end_date finished")

    @patch('app.render_template')
    def test_initial_get_request(self, mock_render_template):
        print("Running test_initial_get_request")
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        mock_render_template.assert_called_once()
        args, kwargs = mock_render_template.call_args
        self.assertEqual(args[0], 'index.html')
        self.assertTrue('today' in kwargs)
        self.assertTrue('default_start' in kwargs)
        self.assertNotIn('error_message', kwargs)
        print("test_initial_get_request finished")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

# To run these tests from shell:
# Ensure MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE are set in the environment
# python -m unittest test_app.py
#
# Note: The print statements are for visibility during the agent's execution,
# they would typically be removed in a final test script.
# The unittest.main call is modified for programmatic execution.
# The actual app.py uses matplotlib.use('Agg') which is good for non-GUI backend.
# The tests also mock plt.savefig to avoid actual file operations for figures.
# Flask's render_template is mocked to inspect its arguments without actual rendering.
# The mock for mysql.connector.connect simulates the database interaction.
# The setup also ensures 'static' dir exists, though plt.savefig is mocked,
# it's a good practice if other parts of app might use it.
# Added WTF_CSRF_ENABLED = False for tests that POST form data.
# Corrected the import of app to flask_app to avoid name collision.
# Added print statements at start/end of each test for clarity in logs.
