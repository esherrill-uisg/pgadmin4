##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2025, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

import uuid
from unittest.mock import patch

from pgadmin.browser.server_groups.servers.databases.schemas.tables.tests \
    import utils as tables_utils
from pgadmin.browser.server_groups.servers.databases.schemas.tests import \
    utils as schema_utils
from pgadmin.browser.server_groups.servers.databases.tests import utils as \
    database_utils
from pgadmin.utils.route import BaseTestGenerator
from regression import parent_node_dict
from regression.python_test_utils import test_utils as utils
from . import utils as policy_utils
import sys


class PolicyDeleteTestCase(BaseTestGenerator):
    """This class will delete policy under table node."""
    scenarios = utils.generate_scenarios('delete_policy',
                                         policy_utils.test_cases)

    def setUp(self):
        super().setUp()
        self.db_name = parent_node_dict["database"][-1]["db_name"]
        schema_info = parent_node_dict["schema"][-1]
        self.server_id = schema_info["server_id"]
        self.db_id = schema_info["db_id"]
        db_con = database_utils.connect_database(self, utils.SERVER_GROUP,
                                                 self.server_id, self.db_id)
        if not db_con['data']["connected"]:
            raise Exception("Could not connect to database to delete policy.")
        self.schema_id = schema_info["schema_id"]
        self.schema_name = schema_info["schema_name"]
        schema_response = schema_utils.verify_schemas(self.server,
                                                      self.db_name,
                                                      self.schema_name)
        if not schema_response:
            raise Exception("Could not find the schema to delete policy.")
        self.table_name = "table_column_%s" % (str(uuid.uuid4())[1:8])
        self.table_id = tables_utils.create_table(self.server, self.db_name,
                                                  self.schema_name,
                                                  self.table_name)
        self.policy_name = "test_policy_delete_%s" % (str(uuid.uuid4())[1:8])
        self.policy_id = policy_utils.create_policy(self.server, self.db_name,
                                                    self.schema_name,
                                                    self.table_name,
                                                    self.policy_name)

    def delete_policy(self):
        return self.tester.delete(
            "{0}{1}/{2}/{3}/{4}/{5}/{6}".format(self.url, utils.SERVER_GROUP,
                                                self.server_id, self.db_id,
                                                self.schema_id, self.table_id,
                                                self.policy_id),
            follow_redirects=True
        )

    def runTest(self):
        """This function will delete policy under table node."""
        policy_response = policy_utils.verify_policy(self.server, self.db_name,
                                                     self.policy_name)
        if not policy_response:
            raise Exception("Could not find the policy to delete.")

        if self.is_positive_test:
            if hasattr(self, "invalid_policy_id"):
                self.policy_id = 9999
            response = self.delete_policy()
        else:
            with patch(self.mock_data["function_name"],
                       return_value=eval(self.mock_data["return_value"])):
                response = self.delete_policy()

        self.assertEqual(response.status_code,
                         self.expected_data["status_code"])

    def tearDown(self):
        # Disconnect the database
        database_utils.disconnect_database(self, self.server_id, self.db_id)
