# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import sys
import os
from threading import Condition

from awsiot.greengrasscoreipc.model import QOS

# Set all the constants
QOS_TYPE = QOS.AT_MOST_ONCE
TIMEOUT = 10
MIN_INTERVAL_SECONDS = 300  # minimum sample interval at which metrics messages can be published
SCHEDULED_THREAD = None
SAMPLE_INTERVAL_CONFIG_KEY = "SampleIntervalSeconds"
SAMPLE_INTERVAL_NEW_CONFIG_KEY = "sample_interval_secs"
THING_NAME = os.environ.get("AWS_IOT_THING_NAME")
TOPIC = "$aws/things/{thing_name}/defender/metrics/json".format(thing_name=THING_NAME)

# Set a condition variable
condition = Condition()

# Get a logger
logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.INFO)
logger.addHandler(handler)
