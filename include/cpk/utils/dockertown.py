import re
from typing import List, Dict, Any, Tuple, Callable

import cpk
from cpk.models.docker.compose import Service, Volumes, Ports, Cgroup

from pytimeparse.timeparse import timeparse

# parse duration strings
duration = lambda s: timeparse(s) if isinstance(s, str) else s

# dict to list of key-value pairs
dict2list = lambda d: [f"{k}={v}" for k, v in d.items()]
# list of key-value pairs to dict
list2dict = lambda t: dict([t.split("=", maxsplit=1) for t in t])
# dict to list of key-value tuples
dict2ltuple = lambda d: [(k, v) for k, v in d.items()]

# list or dict to list of key-value pairs
listdict2list = lambda ld: ld if isinstance(ld, list) else dict2list(ld)

# list or dict to list of key-value tuples
listdict2ltuple = lambda ld: ld if isinstance(ld, list) else dict2ltuple(ld)

# list or dict to dict
listdict2dict = lambda ld: ld if isinstance(ld, dict) else list2dict(ld)

# string or list to list
strlist2list = lambda sl: sl if isinstance(sl, list) else [sl]

# string or list to string
strlist2str = lambda sl: sl if isinstance(sl, str) else " ".join(sl)

# passthrough function with
passthrough = lambda v: v


# mapping from docker-compose to dockertown
mapping: Dict[str, Tuple[str, Callable[[Any], Any]] | List[Tuple[str, Callable[[Any], Any]]]] = {
    # docker-compose -> dockertown :  [] -> dockertown
    "command":          ("command", passthrough),
    "extra_hosts":      ("add_hosts", listdict2ltuple),
    "cap_add":          ("cap_add", passthrough),
    "cap_drop":         ("cap_drop", passthrough),
    "cgroup":           ("cgroupns", lambda cg: cg.name if isinstance(cg, Cgroup) else None),
    "cgroup_parent":    ("cgroup_parent", passthrough),
    "devices":          ("devices", passthrough),
    "dns":              ("dns", passthrough),
    "dns_search":       ("dns_search", passthrough),
    "domainname":       ("domainname", passthrough),
    "entrypoint":       ("entrypoint", strlist2str),
    "environment":      ("envs", listdict2dict),
    "env_file":         ("env_files", passthrough),
    "expose":           ("expose", passthrough),
    "healthcheck":      [
        ("health_cmd", lambda h: strlist2str(h.test)),
        ("health_interval", lambda h: duration(h.interval)),
        ("health_retries", lambda h: h.retries),
        ("health_start_period", lambda h: duration(h.start_period)),
        ("health_timeout", lambda h: duration(h.timeout)),
    ],
    "hostname":         ("hostname", passthrough),
    "init":             ("init", passthrough),
    "stdin_open":       ("interactive", passthrough),
    "ipc":              ("ipc", passthrough),
    "isolation":        ("isolation", passthrough),
    "labels":           ("labels", listdict2dict),
    "links":            ("link", passthrough),
    "logging":          [
        ("log_driver", lambda lg: lg.driver),
        ("log_options", lambda lg: listdict2list(lg.options))
    ],
    "network_mode":     ("networks", lambda n: [n]),
    "mac_address":      ("mac_address", passthrough),
    "container_name":   ("name", passthrough),
    "pid":              ("pid", passthrough),
    "privileged":       ("privileged", passthrough),
    "read_only":        ("read_only", passthrough),
    "restart":          ("restart", passthrough),
    "security_opt":     ("security_options", passthrough),
    "shm_size":         ("shm_size", passthrough),
    "stop_signal":      ("stop_signal", passthrough),
    "stop_grace_period": ("stop_timeout", duration),
    "storage_opt":      ("storage_options", listdict2list),
    "sysctls":          ("sysctl", listdict2dict),
    "tmpfs":            ("tmpfs", passthrough),
    "tty":              ("tty", passthrough),
    "user":             ("user", passthrough),
    "userns_mode":      ("userns", passthrough),
    "working_dir":      ("workdir", passthrough),

    # TODO: needs custom parsing
    # "networks":            "networks"
    # "networks.*.aliases":  "network_aliases"
    # "ulimits":             "ulimit"

}


def populate_dockertown_configuration_from_docker_compose_service(
        cfg: 'cpk.DockertownContainerConfiguration', service: Service):

    """
    Arguments accepted by dockertown.ContainerCLI.run:

        compose (v3 format)     ->          dockertown

        command: pass                       command: List[str] = [],
        extra_hosts: List[str]              add_hosts: List[Tuple[str, str]] = [],
TODO:          - NOT SUPPORTED                     blkio_weight: Optional[int] = None,

TODO:          - NOT SUPPORTED                     blkio_weight_device: List[str] = [],

        cap_add: pass                       cap_add: List[str] = [],
        cap_drop: pass                      cap_drop: List[str] = [],
        cgroup_parent: pass                 cgroup_parent: Optional[str] = None,
        cgroup: Enum                        cgroupns: Optional[str] = None,
          NOT SUPPORTED                     cidfile: Optional[ValidPath] = None,
TODO:          - NOT SUPPORTED                     cpu_period: Optional[int] = None,

          TO BE IMPLEMENTED                 cpu_quota: Optional[int] = None,
          TO BE IMPLEMENTED                 cpu_rt_period: Optional[int] = None,
          TO BE IMPLEMENTED                 cpu_rt_runtime: Optional[int] = None,
          TO BE IMPLEMENTED                 cpu_shares: Optional[int] = None,
          TO BE IMPLEMENTED                 cpus: Optional[float] = None,
          TO BE IMPLEMENTED                 cpuset_cpus: Optional[List[int]] = None,
          TO BE IMPLEMENTED                 cpuset_mems: Optional[List[int]] = None,
          NOT SUPPORTED                     detach: bool = False,
        devices: pass                       devices: List[str] = [],
TODO:          - NOT SUPPORTED                     device_cgroup_rules: List[str] = [],

TODO:          - NOT SUPPORTED                     device_read_bps: List[str] = [],

TODO:          - NOT SUPPORTED                     device_read_iops: List[str] = [],

TODO:          - NOT SUPPORTED                     device_write_bps: List[str] = [],

TODO:          - NOT SUPPORTED                     device_write_iops: List[str] = [],

          NOT SUPPORTED                     content_trust: bool = False,
        dns: pass                           dns: List[str] = [],
TODO:          - NOT SUPPORTED                     dns_options: List[str] = [],

        dns_search: pass                    dns_search: List[str] = [],
        domainname: pass                    domainname: Optional[str] = None,
        entrypoint: Union[str, List[str]]   entrypoint: Optional[str] = None,
        environment: pass                   envs: Dict[str, str] = {},
        env_file: Union[str, List[str]]     env_files: Union[ValidPath, List[ValidPath]] = [],
        expose: List[str]                   expose: Union[int, List[int]] = [],
          NOT SUPPORTED                     gpus: Union[int, str, None] = None,
TODO:          - NOT SUPPORTED                     groups_add: List[str] = [],

          NOT NEEDED                        healthcheck: bool = True,
        healthcheck.test: str | List[str]   health_cmd: Optional[str] = None,
        healthcheck.interval: Duration      health_interval: Union[None, int, timedelta] = None,
        healthcheck.retries: int            health_retries: Optional[int] = None,
        healthcheck.start_period: Duration  health_start_period: Union[None, int, timedelta] = None,
        healthcheck.timeout: Duration       health_timeout: Union[None, int, timedelta] = None,
        hostname: pass                      hostname: Optional[str] = None,
        init: pass                          init: bool = False,
        stdin_open: pass                    interactive: bool = False,
          NOT SUPPORTED                     ip: Optional[str] = None,
          NOT SUPPORTED                     ip6: Optional[str] = None,
        ipc: pass                           ipc: Optional[str] = None,
        isolation: pass                     isolation: Optional[str] = None,
          NOT SUPPORTED                     kernel_memory: Union[int, str, None] = None,
        labels: List[str] | Dict[str, str]  labels: Dict[str, str] = {},
          NOT SUPPORTED                     label_files: List[ValidPath] = [],
        links: List[str]                    link: List[ValidContainer] = [],
          NOT SUPPORTED                     link_local_ip: List[str] = [],
        logging.driver: pass                log_driver: Optional[str] = None,
        logging.options: dict               log_options: List[str] = [],
        mac_address: pass                   mac_address: Optional[str] = None,
          NOT SUPPORTED                     memory: Union[int, str, None] = None,
          NOT SUPPORTED                     memory_reservation: Union[int, str, None] = None,
TODO:          - NOT SUPPORTED                   memory_swap: Union[int, str, None] = None,

TODO:          - NOT SUPPORTED                   memory_swappiness: Optional[int] = None,

        volumes[type=bind]: dict            mounts: List[List[str]] = [],
        container_name: pass                name: Optional[str] = None,
        networks: List[str]                 networks: List[network_cli_wrapper.ValidNetwork] = [],
        networks.<name>.aliases: List[str]  network_aliases: List[str] = [],
        network_mode: str                   networks: List[network_cli_wrapper.ValidNetwork] = [],
TODO:          - NOT SUPPORTED                   oom_kill: bool = True,

TODO:          - NOT SUPPORTED                   oom_score_adj: Optional[int] = None,

        pid: pass                           pid: Optional[str] = None,
          DEPRECATED                        pids_limit: Optional[int] = None,
TODO:          - NOT SUPPORTED                   platform: Optional[str] = None,

        privileged: pass                    privileged: bool = False,
        ports: List[dict]                   publish: List[ValidPortMapping] = [],
          NOT SUPPORTED                     publish_all: bool = False,
TODO:          - NOT SUPPORTED                     pull: str = "missing",

        read_only: pass                     read_only: bool = False,
        restart: pass                       restart: Optional[str] = None,
          NOT SUPPORTED                     remove: bool = False,
TODO:          - NOT SUPPORTED                     runtime: Optional[str] = None,

        security_opt: pass                  security_options: List[str] = [],
        shm_size: str                       shm_size: Union[int, str, None] = None,
          NOT SUPPORTED                     sig_proxy: bool = True,
        stop_signal: pass                   stop_signal: Optional[str] = None,
        stop_grace_period: Duration         stop_timeout: Optional[int] = None,
        storage_opt: Dict[str, str]         storage_options: List[str] = [],
          NOT SUPPORTED                     stream: bool = False,
        sysctls: List[str]                  sysctl: Dict[str, str] = {},
        tmpfs: List[str]                    tmpfs: List[ValidPath] = [],
        tty: pass                           tty: bool = False,
        ulimits: Dict[str, int | dict]      ulimit: List[str] = [], format: <type>=<soft limit>[:<hard limit>]
        user: pass                          user: Optional[str] = None,
        userns_mode: pass                   userns: Optional[str] = None,
TODO:          - NOT SUPPORTED                     uts: Optional[str] = None,

          TO BE IMPLEMENTED                 volumes: Optional[List[volume_cli_wrapper.VolumeDefinition]] = [],
          NOT SUPPORTED                     volume_driver: Optional[str] = None,
          NOT SUPPORTED                     volumes_from: List[ValidContainer] = [],
        working_dir: str                    workdir: Optional[ValidPath] = None,

    """
    # parse simple fields using mapping
    for compose_field, dockertown_fields in mapping.items():
        if not isinstance(dockertown_fields, list):
            dockertown_fields = [dockertown_fields]
        for (dockertown_field, parser) in dockertown_fields:
            value = getattr(service, compose_field)
            if value is not None:
                cfg.set(dockertown_field, parser(value))
    # parse volumes
    unnamed: int = 0
    is_named_volume: Callable[[str], bool] = lambda v: re.match("^[a-zA-Z0-9_]+$", v) is not None
    for volume in (service.volumes or []):
        if isinstance(volume, str):
            parts = volume.split(":")
            if len(parts) == 1:
                # only destination is specified, docker-compose would create a named volume
                name: str = f"unnamed_{unnamed}"
                cfg.add_named_volume(name, Volumes(
                    type="bind",
                    target=parts[0]
                ))
                unnamed += 1
            elif len(parts) == 2:
                source = parts[0]
                if is_named_volume(source):
                    # named volume
                    name: str = source
                    cfg.add_named_volume(name, Volumes(
                        type="bind",
                        target=parts[1]
                    ))
                else:
                    # bind volume
                    cfg.volumes.append((source, parts[1]))
            elif len(parts) == 3:
                source = parts[0]
                if is_named_volume(source):
                    # named volume
                    name: str = source
                    cfg.add_named_volume(name, Volumes(
                        type="bind",
                        target=parts[1],
                        read_only=parts[2] == "ro"
                    ))
                else:
                    # bind volume
                    cfg.volumes.append((source, parts[1], parts[2]))
        else:
            if volume.type == "bind":
                extras = []
                if volume.read_only:
                    extras.append("ro")
                cfg.volumes.append((volume.source, volume.target, *extras))
            else:
                # named volume
                name: str = volume.source
                cfg.add_named_volume(name, Volumes(
                    type="bind",
                    target=volume.target,
                    read_only=volume.read_only
                ))
    # parse ports
    for port in (service.ports or []):
        if isinstance(port, str):
            # noinspection PyTypeChecker
            ports_def: Tuple[str, str] | Tuple[str, str, str] = tuple(port.replace("/", ":").split(":"))
            cfg.publish.append(ports_def)
        elif isinstance(port, Ports):
            extras = []
            if port.protocol is not None:
                extras.append(port.protocol)
            # noinspection PyTypeChecker
            ports_def: Tuple[str, str] | Tuple[str, str, str] = tuple([port.target, port.published] + extras)
            cfg.publish.append(ports_def)
