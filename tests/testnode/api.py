#!/bin/env python3

import datetime
import inspect
import time

import yaml

import kubernetes


class NotFound(Exception):
    pass


class RetryWrapper:
    """Generic class for retrying method calls on an object"""

    def __init__(self, object, exception=Exception, timeout=60):
        self.object = object
        self.exception = exception
        self.timeout = timeout

    def __getattribute__(self, name, *args, **kwargs):
        object = super().__getattribute__("object")
        exception = super().__getattribute__("exception")
        timeout = super().__getattribute__("timeout")

        if not hasattr(object, name):
            raise AttributeError(f"No {name} on {type(object)}")
        else:
            attr = getattr(object, name)

            if not inspect.ismethod(attr):
                return attr

            def wrapped(*args, **kwargs):
                deadline = datetime.datetime.now() + datetime.timedelta(seconds=timeout)

                while True:
                    try:
                        result = attr(*args, **kwargs)

                        return result
                    except exception as e:
                        if datetime.datetime.now() >= deadline:
                            raise e
                        time.sleep(1)

            return wrapped


class Kubernetes:
    """Kubernetes api commands"""

    def __init__(self, config):
        """
        Initialize the api
        Config can be provided as a dictionary or a callable that will be evaluated when the
        api is used the first time. If callable is provided the output will be run through
        yaml_safeload to produce the config.
        """

        self._config = config
        self._api = None
        self._api_network = None
        self._timeout_coefficient = 1.0

    def set_timeout_coefficient(self, coefficient):
        self._timeout_coefficient = float(coefficient)

    def _get_deadline(self, timeout):
        deadline = datetime.datetime.now() + datetime.timedelta(
            seconds=timeout * self._timeout_coefficient
        )
        return deadline

    @property
    def api(self):
        if self._api:

            return self._api

        config = kubernetes.client.configuration.Configuration.get_default_copy()
        # config.retries = 60
        local_config = self.config
        kubernetes.config.load_kube_config_from_dict(local_config, client_configuration=config)
        self.api_client = kubernetes.client.ApiClient(configuration=config)
        self._raw_api = kubernetes.client.CoreV1Api(api_client=self.api_client)
        self._api = RetryWrapper(self._raw_api, Exception)

        return self._api

    @property
    def api_network(self):
        if self._api_network:
            return self._api_network

        self.api  # Ensure the core api has been setup
        self._raw_api_network = kubernetes.client.NetworkingV1beta1Api(api_client=self.api_client)
        self._api_network = RetryWrapper(self._raw_api_network, Exception)

        return self._api_network

    @property
    def config(self):
        """Return config"""

        if callable(self._config):
            self._config = yaml.safe_load(self._config())

        return self._config

    def get_raw_api(self, url, timeout=60):
        self.api
        deadline = self._get_deadline(timeout)

        while True:
            try:
                resp = self.api_client.call_api(
                    url,
                    "GET",
                    auth_settings=["BearerToken"],
                    response_type="yaml",
                    _preload_content=False,
                )

                break
            except kubernetes.client.exceptions.ApiException:
                pass

            if datetime.datetime.now() > deadline:
                break
            time.sleep(1)

        return yaml.safe_load(resp[0].data.decode("utf8"))

    def create_from_yaml(self, yaml_file, verbose=False, namespace="default"):
        """Create objcets from yaml input"""

        if not self.api_client:
            self.api  # Accessing the api creates an api_client

        return kubernetes.utils.create_from_yaml(
            k8s_client=self.api_client, yaml_file=yaml_file, verbose=verbose, namespace=namespace
        )

    def get_service_proxy(self, name, namespace, path=None, timeout=30):
        """Return a GET call to a proxied service"""
        deadline = self._get_deadline(timeout)

        while True:
            try:
                if path:
                    response = self.api.connect_get_namespaced_service_proxy(name, namespace, path)
                else:
                    response = self.api.connect_get_namespaced_service_proxy(name, namespace)
                return response
            except kubernetes.client.exceptions.ApiException:
                if datetime.datetime.now() > deadline:
                    raise TimeoutError(
                        f"Timeout waiting for service proxy {name}, response: {response}"
                    )
                time.sleep(1)

    def create_pvc(
        self,
        name,
        namespace,
        storage="1G",
        access=["ReadWriteOnce"],
        storage_class=None,
        wait=False,
    ):
        """Create a PVC"""
        claim = kubernetes.client.V1PersistentVolumeClaim()
        spec = kubernetes.client.V1PersistentVolumeClaimSpec()
        metadata = kubernetes.client.V1ObjectMeta()
        resources = kubernetes.client.V1ResourceRequirements()
        metadata.name = name
        resources.requests = {}
        resources.requests["storage"] = storage
        spec.access_modes = access
        spec.resources = resources

        if storage_class:
            spec.storage_class_name = storage_class
        claim.metadata = metadata
        claim.spec = spec

        if wait:
            self.api.create_namespaced_persistent_volume_claim(namespace, claim)

            return self.wait_pvc_phase(name, namespace)
        else:
            return self.api.create_namespaced_persistent_volume_claim(namespace, claim)

    def delete_pvc(self, name, namespace):
        """Delete a PVC"""

        return self.api.delete_namespaced_persistent_volume_claim(name, namespace)

    def wait_pvc_phase(self, name, namespace, phase="Bound", timeout=60):
        """Wait for a PVC to enter the given phase"""
        deadline = self._get_deadline(timeout)

        while True:
            claim = self.api.read_namespaced_persistent_volume_claim_status(name, namespace)

            if claim.status.phase == phase:
                return claim
            elif datetime.datetime.now() > deadline:
                raise TimeoutError(f"Timeout waiting for {name} to become {phase}")
            time.sleep(0.5)

    def wait_nodes_ready(self, count, timeout=60):
        """Wait for nodes to become ready"""
        deadline = self._get_deadline(timeout)
        nodes = self.api.list_node().items

        while True:
            ready_count = 0

            for node in nodes:
                for condition in node.status.conditions:
                    if condition.type == "Ready" and condition.status == "True":
                        ready_count += 1

            if ready_count >= count:
                return count
            elif datetime.datetime.now() > deadline:
                raise TimeoutError(f"Timeout waiting {ready_count} of {count} Ready")

    def create_namespace(self, namespace):
        """Create a namespace"""

        metadata = kubernetes.client.V1ObjectMeta(name=namespace)
        namespace = kubernetes.client.V1Namespace(metadata=metadata)
        api_response = self.api.create_namespace(namespace)

        return api_response

    def get_service_cluster_ip(self, namespace, name):
        """Get an IP for a service by name"""
        service_list = self.api.list_namespaced_service(namespace)

        if not service_list.items:
            raise NotFound(f"No services in namespace {namespace}")

        for service in service_list.items:
            if service.metadata.name == name:
                return service.spec.cluster_ip

        raise NotFound(f"cluster_ip not found for {name} in {namespace}")

    def get_service_load_balancer_ip(self, namespace, name):
        """Get an LB IP for a service by name"""
        service_list = self.api.list_namespaced_service(namespace)

        if not service_list.items:
            raise NotFound(f"No services in namespace {namespace}")

        for service in service_list.items:
            if service.metadata.name == name:
                try:
                    return service.status.load_balancer.ingress[0].ip
                except TypeError:
                    pass

        raise NotFound(f"load_balancer_ip not found for {name} in {namespace}")

    def wait_load_balancer_ip(self, namespace, name, timeout=60):
        deadline = self._get_deadline(timeout)

        while True:
            try:
                ip = self.get_service_load_balancer_ip(namespace, name)

                if ip:
                    return ip
            except NotFound:
                pass

            if datetime.datetime.now() > deadline:
                raise TimeoutError(f"Timeout waiting for {name} in {namespace}")
            time.sleep(1)

    def get_pods(self, namespace, label=None, field=None):
        """Get pod list"""
        pod_list = self.api.list_namespaced_pod(
            namespace, label_selector=label, field_selector=field
        )

        if not pod_list.items:
            raise NotFound(f"No pods in namespace {namespace} with label {label}")

        return pod_list.items

    def all_containers_ready(self, namespace, label=None, field=None):
        """Check if all containers in all pods are ready"""

        ready = True

        pods = self.api.list_namespaced_pod(namespace, label_selector=label, field_selector=field)

        if not len(pods.items):
            return False

        for pod in pods.items:
            try:
                for container in pod.status.container_statuses:
                    ready = ready & container.ready
            except TypeError:
                return False

        return ready

    def wait_containers_ready(self, namespace, label=None, field=None, timeout=60):
        """Wait up to timeout for all containers to be ready."""
        deadline = self._get_deadline(timeout)

        while True:
            if self.all_containers_ready(namespace, label, field):
                return
            elif datetime.datetime.now() > deadline:
                raise TimeoutError(f"Timeout waiting for containers in {namespace}")
            else:
                time.sleep(1)

    def wait_ingress_ready(self, name, namespace, timeout=60):
        """Wait for an ingress to get an address"""
        deadline = self._get_deadline(timeout)

        while True:
            result = self.api_network.read_namespaced_ingress(name, namespace)

            if result.status.load_balancer.ingress is not None:
                return result.status.load_balancer.ingress
            elif datetime.datetime.now() > deadline:
                raise TimeoutError(f"Timeout waiting for Ingress {name}, result: {result}")
            else:
                time.sleep(1)
