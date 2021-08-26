# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from threading import Timer, Thread

from AWSIoTDeviceDefenderAgentSDK import collector
from greengrass_defender_agent import config
from greengrass_defender_agent import ipc_utils


def set_configuration(configuration):
    """
    Set up a configuration object given input configuration and apply constraints and defaults.

    :param configuration: a dictionary object of configuration
    """
    new_config = {}
    if config.SAMPLE_INTERVAL_CONFIG_KEY in configuration:
        try:
            sample_interval_seconds = int(configuration[config.SAMPLE_INTERVAL_CONFIG_KEY])
        except (ValueError, TypeError):
            config.logger.warning(
                "Invalid sample interval. Using default sample interval: {}".format(
                    config.MIN_INTERVAL_SECONDS
                )
            )
            sample_interval_seconds = config.MIN_INTERVAL_SECONDS
        if sample_interval_seconds < config.MIN_INTERVAL_SECONDS:
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

    return new_config


def set_configuration_and_publish(ipc_client, configuration):
    """
    Call publish_metrics() with the new configuration object.

    :param ipc_client: Ipc client
    :param configuration: a dictionary object of configuration
    """
    publish_metrics(ipc_client, set_configuration(configuration), True)


def wait_for_config_changes(ipc_client):
    """
    Wait for configuration changes.

    :param ipc_client: Ipc client
    """
    with config.condition:
        config.condition.wait()
        set_configuration_and_publish(ipc_client, ipc_client.get_configuration())
    wait_for_config_changes(ipc_client)


def publish_metrics(ipc_client, new_config, config_changed):
    """
    Collect and publish metrics.

    :param ipc_client: Ipc client
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
        ipc_client.publish_to_iot_core(topic, metric.to_json_string())

        config.SCHEDULED_THREAD = Timer(
            float(sample_interval_seconds), publish_metrics, [ipc_client, new_config, config_changed]
        )
        config.SCHEDULED_THREAD.start()

    except Exception as e:
        config.logger.error("Error collecting and publishing metrics: {}".format(e))
        raise e


def main():
    # Get the ipc client
    ipc_client = ipc_utils.IPCUtils()
    try:
        ipc_client.connect()
    except Exception as e:
        config.logger.error(
            "Exception occurred during the creation of an IPC client: {}".format(e)
        )
        exit(1)

    # Get initial configuration from the recipe
    configuration = ipc_client.get_configuration()

    # Subscribe to accepted/rejected topics for status report of publish
    ipc_client.subscribe_to_iot_core(config.TOPIC + "/accepted")
    ipc_client.subscribe_to_iot_core(config.TOPIC + "/rejected")

    # Start collecting and publishing metrics
    set_configuration_and_publish(ipc_client, configuration)

    # Subscribe to the subsequent configuration changes
    ipc_client.subscribe_to_config_updates()
    Thread(
        target=wait_for_config_changes,
        args=(ipc_client,),
    ).start()
