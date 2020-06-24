# The MIT License (MIT)
#
# Copyright (c) 2020 Michael Schroeder
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import json
import os

from google.cloud import bigquery
from google.oauth2 import service_account

BIGQ_QUERY_STRING = """SELECT
  COUNT(*) AS num_downloads,
  file.project AS `lib`,
  details.installer.name AS `installer`
FROM `the-psf.pypi.downloads*`
WHERE
  file.project LIKE 'adafruit-%'
  AND details.installer.name = 'pip'
  AND _TABLE_SUFFIX
    BETWEEN FORMAT_DATE(
      '%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
GROUP BY `lib`, `installer`
ORDER BY `num_downloads` DESC
"""

class PyPIBigQuery:
    """ Class to provide access to the PyPI stats Google BigQuery, provided
        by PPA's Linehaul service.

        Note: requires GCP service account credentials info to be available
        as a JSON-string enrivornment variable 'ADABOT_GOOGLE_AUTH_STRING'.
    """

    def __init__(self):
        creds_info = json.loads(
            os.environ.get("ADABOT_GOOGLE_AUTH_STRING", "")
        )
        credentials = service_account.Credentials.from_service_account_info(
            creds_info
        )
        self._client = bigquery.Client(credentials=credentials)
        self._results = {}

    def query(self):
        """ Initiates a query, waits for the query to finish, and stores
            the results into `self._result` (accessed via ``results`` method).

            :returns: Query job result status as a boolean
        """
        query_job = self._client.query(BIGQ_QUERY_STRING)
        results = query_job.result()

        if results:
            results_to_dict = {}
            for row in results:
                lib = row.get("lib")
                num_dl = int(row.get("num_downloads", 0))
                results_to_dict[lib] = num_dl

            self._results = results_to_dict
            results = True
        else:
            self._results = {}
            results = False

        return results

    @property
    def results(self):
        """ The results of the last query.

            :returns: Dict[str: int] as '{lib_name: downloads}'
        """
        return self._results
