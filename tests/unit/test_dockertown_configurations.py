import os
import unittest

import yaml

from cpk import CPKProject
from cpk.types import CPKProjectSelfLayer, CPKProjectTemplateLayer, CPKProjectFormatLayer, \
    CPKProjectBaseLayer, CPKProjectStructureLayer, CPKProjectContainersLayer, CPKContainerConfiguration, \
    DockertownContainerConfiguration

TEST_PROJECTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "projects"))


class TestContainersProject(unittest.TestCase):

    @staticmethod
    def get_project(name: str) -> CPKProject:
        return CPKProject(os.path.join(TEST_PROJECTS_DIR, name))

    @staticmethod
    def get_project_layer_raw(name: str, layer: str) -> dict:
        yaml_fpath: str = os.path.join(TEST_PROJECTS_DIR, name, "cpk", f"{layer}.yaml")
        with open(yaml_fpath, "rt") as fin:
            return yaml.safe_load(fin)

    def test_container_configuration_default(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("default").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration()
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_development(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("development").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            mounts=[
                ["./", "${CPK_PROJECT_PATH}"]
            ]
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_ports(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("ports").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            publish=[
                ("8080", "80"),
                ("9090", "90"),
                ("9091", "91", "udp"),
            ]
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_privilege(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("privilege").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            privileged=True
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_nethost(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("nethost").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            networks=["host"]
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_named(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("named").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            name="my_container"
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_workdir(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("workdir").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            workdir="/path/to/workdir"
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_interactive(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("interactive").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            tty=True,
            interactive=True,
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_environment(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("environment").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            envs={
                "MY_ENV_VAR": "foo",
                "MY_OTHER_ENV_VAR": "bar",
            }
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_envfile(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("envfile").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            env_files=[".env"]
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_labels(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("labels").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            labels={
                "com.example.description": "Webapp",
                "com.example.department": "Finance",
                "com.example.label-with-empty-value": "",
            }
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_restart(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("restart").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            restart="always"
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_stopsignal(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("stopsignal").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            stop_signal="SIGKILL"
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_healthcheck(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("healthcheck").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            health_cmd="curl -f http://localhost",
            health_interval=90,
            health_timeout=10,
            health_retries=3,
            health_start_period=40,
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_command(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("command").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            command=["echo", "Hello world!"],
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_tmpfs(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("tmpfs").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            tmpfs=[
                "/tmp",
                "/run",
            ],
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_cgroup_parent(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("cgroup_parent").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            cgroup_parent="cg-parent",
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_cgroupns(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("cgroupns").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            cgroupns="host",
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_hostname(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("hostname").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            hostname="myhostname",
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_ipc(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("ipc").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            ipc="host",
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_macaddress(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("macaddress").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            mac_address="02:42:ac:11:65:43",
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_pid(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("pid").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            pid="host",
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_caps(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("caps").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            cap_add=["SYS_ADMIN"],
            cap_drop=["NET_ADMIN"],
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_devices(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("devices").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            devices=[
                "/dev/ttyUSB0:/dev/ttyUSB0"
            ]
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_sysctls(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("sysctls").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            sysctl={
                "net.core.somaxconn": "1024",
            }
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_dns(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("dns").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            dns=["8.8.8.8"],
            dns_search=["example.com"],
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_domainname(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("domainname").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            domainname="example.com"
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_userns(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("userns").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            userns="host"
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_entrypoint(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("entrypoint").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            entrypoint="/bin/sh -c"
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_security_opt(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("security_opt").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            security_options=["seccomp:unconfined"]
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_extra_hosts(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("extra_hosts").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            add_hosts=[("somehost", "1.1.1.1")]
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_links(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("links").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            link=["db"]
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_init(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("init").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            init=True,
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_isolation(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("isolation").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            isolation="hyperv",
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_logging(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("logging").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            log_driver="syslog",
            log_options=[
                "syslog-address=tcp://",
            ]
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_read_only(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("read_only").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            read_only=True,
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_shm_size(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("shm_size").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            shm_size="64M",
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_stop_grace_period(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("stop_grace_period").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            stop_timeout=90
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_storage_opt(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("storage_opt").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            storage_options=[
                "size=20G",
            ]
        )
        self.assertEqual(cfg1, cfg2)

    def test_container_configuration_user(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        # ---
        cfg1: DockertownContainerConfiguration = layer.get("user").as_dockertown_configuration()
        cfg2: DockertownContainerConfiguration = DockertownContainerConfiguration(
            user="1000:1000",
        )
        self.assertEqual(cfg1, cfg2)



if __name__ == '__main__':
    unittest.main()
