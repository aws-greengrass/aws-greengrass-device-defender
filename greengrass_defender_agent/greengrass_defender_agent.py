# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from threading import Timer, Thread

from AWSIoTDeviceDefenderAgentSDK import collector

import config
import ipc_utils


def set_configuration_and_publish(configuration):
    """
    Set up a configuration object given input configuration and apply constraints and defaults.
    Call publish_metrics() with the new configuration object.

    :param configuration: a dictionary object of configuration
    """
    new_config = {}
    if config.SAMPLE_INTERVAL_CONFIG_KEY in configuration:
        sample_interval_seconds = configuration[config.SAMPLE_INTERVAL_CONFIG_KEY]
        if int(sample_interval_seconds) < config.MIN_INTERVAL_SECONDS:
            config.logger.warning(
                "Using minimum sample interval: {}".format(
                    config.MIN_INTERVAL_SECONDS
                )
            )
            new_config[config.SAMPLE_INTERVAL_NEW_CONFIG_KEY] = config.MIN_INTERVAL_SECONDS
        else:
            new_config[config.SAMPLE_INTERVAL_NEW_CONFIG_KEY] = sample_interval_seconds
    else:
        new_config[config.SAMPLE_INTERVAL_NEW_CONFIG_KEY] = config.MIN_INTERVAL_SECONDS
        config.logger.warning(
            "Using default sample interval: {}".format(
                config.MIN_INTERVAL_SECONDS
            )
        )

    publish_metrics(new_config, True)


def wait_for_config_changes():
    """ Wait for configuration changes."""
    with config.condition:
        config.condition.wait()
        set_configuration_and_publish(ipc_utils.IPCUtils().get_configuration())
    wait_for_config_changes()


def publish_metrics(new_config, config_changed):
    """
    Collect and publish metrics.

    :param new_config: a configuration object
    :param config_changed: boolean whether the configuration has changed
    """
    try:
        if config_changed and config.SCHEDULED_THREAD is not None:
            config.SCHEDULED_THREAD.cancel()
            config_changed = False

        topic = config.TOPIC
        sample_interval_seconds = new_config[config.SAMPLE_INTERVAL_NEW_CONFIG_KEY]

        config.logger.info("Collector running on device: {}".format(config.THING_NAME))
        config.logger.info("Metrics topic: {}".format(topic))
        config.logger.info("Sampling interval: {} seconds".format(sample_interval_seconds))

        metrics_collector = collector.Collector(short_metrics_names=False)
        metric = metrics_collector.collect_metrics()
        config.logger.debug("Publishing metrics: {}".format(metric.to_json_string()))
        ipc.publish_to_iot_core(topic, metric.to_json_string())

        config.SCHEDULED_THREAD = Timer(
            float(sample_interval_seconds), publish_metrics, [new_config, config_changed]
        )
        config.SCHEDULED_THREAD.start()

    except Exception as e:
        config.logger.error("Error publishing metrics: {}".format(e))
        exit(1)


ipc = ipc_utils.IPCUtils()

# Subscribe to accepted/rejected topics for status report of publish
ipc.subscribe_to_iot_core(config.TOPIC + "/accepted")
ipc.subscribe_to_iot_core(config.TOPIC + "/rejected")

# Get initial configuration from the recipe
set_configuration_and_publish(ipc.get_configuration())

# Subscribe to the subsequent configuration changes
ipc.subscribe_to_config_updates()
Thread(
    target=wait_for_config_changes,
    args=(),
).start()
