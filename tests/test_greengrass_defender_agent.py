# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from greengrass_defender_agent import agent
from greengrass_defender_agent.config import SAMPLE_INTERVAL_CONFIG_KEY, SAMPLE_INTERVAL_NEW_CONFIG_KEY


def test_set_configuration():
    assert agent.set_configuration({SAMPLE_INTERVAL_CONFIG_KEY: 400})[SAMPLE_INTERVAL_NEW_CONFIG_KEY] == 400
    assert agent.set_configuration({})["sample_interval_secs"] == 300
    assert agent.set_configuration({SAMPLE_INTERVAL_CONFIG_KEY: None})[SAMPLE_INTERVAL_NEW_CONFIG_KEY] == 300
    assert agent.set_configuration({SAMPLE_INTERVAL_CONFIG_KEY: 100})[SAMPLE_INTERVAL_NEW_CONFIG_KEY] == 300
    assert agent.set_configuration({SAMPLE_INTERVAL_CONFIG_KEY: "nan"})[SAMPLE_INTERVAL_NEW_CONFIG_KEY] == 300
