# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import sys
import os
from threading import Condition

from awsiot.greengrasscoreipc.model import QOS

# Set all the constants
QOS_TYPE = QOS.AT_MOST_ONCE
IPC_CONNECT_TIMEOUT = 120
TIMEOUT = 10
MIN_INTERVAL_SECONDS = 300  # minimum sample interval at which metrics messages can be published
SCHEDULED_THREAD = None
IS_SHUTTING_DOWN = False
SAMPLE_INTERVAL_CONFIG_KEY = "SampleIntervalSeconds"
PUBLISH_RETRY_CONFIG_KEY = "GG_DD_PUB_RETRY_COUNT"
MIN_PUBLISH_RETRY = 0
DEFAULT_CONNECT_AND_PUBLISH_RETRY = 5
MAX_PUBLISH_RETRY = 72 # About 12 hours of max retry can be configured from customer side
SAMPLE_INTERVAL_NEW_CONFIG_KEY = "sample_interval_secs"
THING_NAME = os.environ.get("AWS_IOT_THING_NAME")
TOPIC = "$aws/things/{thing_name}/defender/metrics/json".format(thing_name=THING_NAME)
INITIAL_RETRY_INTERVAL_SECONDS = 5
MAX_RETRY_INTERVAL_SECONDS = 600  # 10 minutes
MAX_JITTER_TIME_INTERVAL_SECONDS = 30

# Set a condition variable
condition = Condition()

# Get a logger
logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.INFO)
logger.addHandler(handler)
