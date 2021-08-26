# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from os import getenv

import awsiot.greengrasscoreipc.client as client
from awscrt.io import (
    ClientBootstrap,
    DefaultHostResolver,
    EventLoopGroup,
    SocketDomain,
    SocketOptions,
)
from awsiot.eventstreamrpc import Connection, LifecycleHandler, MessageAmendment
from awsiot.greengrasscoreipc.model import (
    ConfigurationUpdateEvents,
    GetConfigurationRequest,
    PublishToIoTCoreRequest,
    SubscribeToConfigurationUpdateRequest,
    SubscribeToIoTCoreRequest, IoTCoreMessage
)

from greengrass_defender_agent import config


class IPCUtils:
    def __init__(self):
        self.lifecycle_handler = None
        self.ipc_client = None

    def connect(self):
        elg = EventLoopGroup()
        resolver = DefaultHostResolver(elg)
        bootstrap = ClientBootstrap(elg, resolver)
        socket_options = SocketOptions()
        socket_options.domain = SocketDomain.Local
        amender = MessageAmendment.create_static_authtoken_amender(getenv("SVCUID"))
        hostname = getenv("AWS_GG_NUCLEUS_DOMAIN_SOCKET_FILEPATH_FOR_COMPONENT")
        connection = Connection(
            host_name=hostname,
            port=8033,
            bootstrap=bootstrap,
            socket_options=socket_options,
            connect_message_amender=amender,
        )
        self.lifecycle_handler = LifecycleHandler()
        connect_future = connection.connect(self.lifecycle_handler)
        connect_future.result(config.TIMEOUT)
        self.ipc_client = client.GreengrassCoreIPCClient(connection)
        config.logger.info("Created IPC client...")

    def publish_to_iot_core(self, topic, payload):
        """
        Ipc client creates a request and activates the operation to publish messages to the IoT core
        with a qos type over a topic.

        :param topic: the topic to publish
        :param payload: json string
        """
        try:
            request = PublishToIoTCoreRequest()
            request.topic_name = topic
            request.payload = bytes(payload, "utf-8")
            request.qos = config.QOS_TYPE
            operation = self.ipc_client.new_publish_to_iot_core()
            operation.activate(request)
            future = operation.get_response()
            future.result(config.TIMEOUT)
            config.logger.info("Published to the IoT core...")
        except Exception as e:
            config.logger.error("Exception occurred during publish to {}: {}".format(topic, e))
            raise e

    def subscribe_to_iot_core(self, topic):
        """
        Ipc client creates a request and activates the operation to subscribe to a topic

        :param topic: the topic to subscribe to
        """
        try:
            request = SubscribeToIoTCoreRequest()
            request.topic_name = topic
            request.qos = config.QOS_TYPE
            operation = self.ipc_client.new_subscribe_to_iot_core(SubscribeToIoTCoreHandler(topic))
            future = operation.activate(request)
            future.result(config.TIMEOUT)
            config.logger.info("Subscribed to topic {}".format(topic))
        except Exception as e:
            config.logger.error("Exception occurred during subscribe: {}".format(e))
            raise e

    def get_configuration(self):
        """
        Ipc client creates a request and activates the operation to get the configuration.

        :return: a dictionary object of the component's configuration value.
        """
        try:
            request = GetConfigurationRequest()
            operation = self.ipc_client.new_get_configuration()
            operation.activate(request).result(config.TIMEOUT)
            result = operation.get_response().result(config.TIMEOUT)
            return result.value
        except Exception as e:
            config.logger.error(
                "Exception occurred during fetching the configuration: {}".format(e)
            )
            raise e

    def subscribe_to_config_updates(self):
        """
        Ipc client creates a request and activates the operation to subscribe to the configuration change on
        "SampleIntervalSeconds".
        """
        try:
            subsreq = SubscribeToConfigurationUpdateRequest(key_path=[config.SAMPLE_INTERVAL_CONFIG_KEY])
            subscribe_operation = self.ipc_client.new_subscribe_to_configuration_update(
                ConfigUpdateHandler()
            )
            subscribe_operation.activate(subsreq).result(config.TIMEOUT)
            subscribe_operation.get_response().result(config.TIMEOUT)
        except Exception as e:
            config.logger.error(
                "Exception occurred during subscribing to the configuration updates: {}".format(e)
            )
            raise e


class ConfigUpdateHandler(client.SubscribeToConfigurationUpdateStreamHandler):
    """
    Custom handle of the subscribed configuration events(steam,error and close).
    Due to the SDK limitation, another request from within this callback cannot to be sent.
    Here, it just logs and notifies the thread.
    """

    def on_stream_event(self, event: ConfigurationUpdateEvents) -> None:
        config.logger.info("Configuration updated...")
        with config.condition:
            config.condition.notify()

    def on_stream_error(self, error: Exception) -> bool:
        config.logger.error("Error in config update subscriber - {0}".format(error))
        return False

    def on_stream_closed(self) -> None:
        config.logger.info("Config update subscription stream was closed")


class SubscribeToIoTCoreHandler(client.SubscribeToIoTCoreStreamHandler):
    """
    Custom handle of subscription to IoT Core.
    Due to the SDK limitation, another request from within this callback cannot to be sent.
    Here, it just logs.
    """

    def __init__(self, topic):
        super().__init__()
        self.topic = topic

    def on_stream_event(self, event: IoTCoreMessage) -> None:
        received_message = str(event.message.payload, "utf-8")
        config.logger.debug("Received message from topic {}: {}".format(self.topic, received_message))

    def on_stream_error(self, error: Exception) -> bool:
        config.logger.error("Error in Iot Core subscriber - {0}".format(error))
        return False

    def on_stream_closed(self) -> None:
        config.logger.info("Subscribe to Iot Core stream was closed")
