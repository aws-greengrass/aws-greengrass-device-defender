# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from threading import Timer, Thread
from random import randint
from time import sleep

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


def set_configuration_and_publish(ipc_client, configuration, metrics_collector):
    """
    Call publish_metrics() with the new configuration object.

    :param ipc_client: Ipc client
    :param configuration: a dictionary object of configuration
    :param metrics_collector: metrics collector
    """
    new_config = set_configuration(configuration)
    sample_interval_seconds = new_config[config.SAMPLE_INTERVAL_NEW_CONFIG_KEY]
    config.logger.info("Collector running on device: {}".format(config.THING_NAME))
    config.logger.info("Metrics topic: {}".format(config.TOPIC))
    config.logger.info("Sampling interval: {} seconds".format(sample_interval_seconds))
    publish_metrics(ipc_client, new_config, metrics_collector, sample_interval_seconds)


def wait_for_config_changes(ipc_client, metrics_collector):
    """
    Wait for configuration changes.

    :param ipc_client: Ipc client
    :param metrics_collector: metrics collector
    """
    with config.condition:
        config.condition.wait()
        set_configuration_and_publish(ipc_client, ipc_client.get_configuration(), metrics_collector)
    wait_for_config_changes(ipc_client, metrics_collector)


def publish_metrics(ipc_client, config_changed, metrics_collector, sample_interval_seconds):
    """
    Collect and publish metrics.

    :param ipc_client: Ipc client
    :param config_changed: boolean whether the configuration has changed
    :param metrics_collector: metrics collector
    :param sample_interval_seconds: sampling metrics interval in seconds
    """
    try:
        if config_changed and config.SCHEDULED_THREAD is not None:
            config.SCHEDULED_THREAD.cancel()
            config_changed = False

        metric = metrics_collector.collect_metrics()
        config.logger.debug("Publishing metrics: {}".format(metric.to_json_string()))
        ipc_client.publish_to_iot_core(config.TOPIC, metric.to_json_string())

        config.SCHEDULED_THREAD = Timer(
            float(sample_interval_seconds), publish_metrics,
            [ipc_client, config_changed, metrics_collector, sample_interval_seconds]
        )
        config.SCHEDULED_THREAD.start()

    except Exception as e:
        config.logger.error("Error collecting and publishing metrics: {}".format(e))
        raise e


def main():
    # Get the ipc client
    ipc_client = ipc_utils.IPCUtils()

    need_retry = True
    retry_time = config.INITIAL_RETRY_INTERVAL_SECONDS

    while need_retry:
        try:
            ipc_client.connect()
            need_retry = False
        except Exception as e:
            config.logger.exception(
                "Exception occurred during the creation of an IPC client: {}".format(e)
                )
            config.logger.info(
                "Will retry client initialization in {} seconds".format(retry_time)
            )
            sleep(retry_time)
            if retry_time < config.MAX_RETRY_INTERVAL_SECONDS:
                retry_time = retry_time * 2 + randint(0, config.MAX_JITTER_TIME_INTERVAL)
            else:
                retry_time = config.MAX_RETRY_INTERVAL_SECONDS

    # Get initial configuration from the recipe
    configuration = ipc_client.get_configuration()

    # Subscribe to accepted/rejected topics for status report of publish
    ipc_client.subscribe_to_iot_core(config.TOPIC + "/accepted")
    ipc_client.subscribe_to_iot_core(config.TOPIC + "/rejected")

    # Initialize metrics collector
    metrics_collector = collector.Collector(short_metrics_names=False)

    # Start collecting and publishing metrics
    set_configuration_and_publish(ipc_client, configuration, metrics_collector)

    # Subscribe to the subsequent configuration changes
    ipc_client.subscribe_to_config_updates()
    Thread(
        target=wait_for_config_changes,
        args=(ipc_client, metrics_collector),
    ).start()
