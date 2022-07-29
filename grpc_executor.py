import argparse
import subprocess
import os
import sys
from importlib import import_module
import re
import json
import shutil
from pathlib import Path
from google.protobuf.json_format import Parse
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.json_format import MessageToDict, ParseError

from library.executor.execute import Executor
from library.dbhandler.persist_db import PersistDB
import grpc
import platform
import logging
if os.getenv("app_type") is not None:
    from common import log_generation
    LOG = log_generation.get_logger(os.getenv("app_type"))
else:
    LOGFILE = "grpc_log"
    LOG = logging.getLogger(LOGFILE)
    LOG.setLevel(logging.DEBUG)
    FH = logging.FileHandler(LOGFILE)
    FH.setLevel(logging.DEBUG)
    LOG.addHandler(FH)

PROTOC_COMMAND = "grpc_tools.protoc"


class GrpcModuleGenerator:
    """
    This class is responsible for
    generating proto interface folder
    and package
    """

    def __init__(self, proto_package_name, dependent_proto_package=None):
        self.proto_package_name = proto_package_name
        self.proto_package_name_ = proto_package_name
        self.proto_interface_folder = self.proto_package_name.split('.')[
            0] + "_interface"
        self.create_proto_interface_dir()
        self.generate_grpc_interface_modules()
        self.dependent_proto_package_name = dependent_proto_package
        if self.dependent_proto_package_name is not None:
            generated_files = map(
                self.generate_grpc_interface_modules,
                self.dependent_proto_package_name)
            LOG.debug(f"file is generated {list(generated_files)} ")

    def create_proto_interface_dir(self):
        """
        generates interface folder
        """
        try:
            self.proto_interface_folder = self.proto_package_name.split('.')[
                0] + "_interface"
            if os.path.exists(self.proto_interface_folder):
                shutil.rmtree(self.proto_interface_folder)

            os.mkdir(self.proto_interface_folder)
            LOG.debug(
                f'--- successfully created {self.proto_interface_folder} ---')

        except IOError:
            raise IOError(
                f'--- {self.proto_interface_folder} does not exists ---')

    def generate_grpc_interface_modules(self, package_name=None):
        """
        generate grpc files
        :rtype: object
        """

        if package_name is not None:
            self.proto_package_name = package_name
            LOG.debug(f" proto name {self.proto_package_name} ")

        proc = None
        try:
            if os.getenv("project_path") is not None:
                interface_folder_path = str(
                    os.path.join(
                        os.getenv("project_path"),
                        "testinputs", os.getenv('env_type'),
                        os.getenv("app_type"),
                        "proto_buffer"))
                if platform.system() == 'Windows':
                    proc = subprocess.Popen(
                        "python -m" +
                        " " +
                        PROTOC_COMMAND +
                        " " +
                        "-I =" +
                        interface_folder_path +
                        "   --python_out=" +
                        os.path.join(os.getenv("project_path"),
                                     self.proto_interface_folder) +
                        " --grpc_python_out=" +
                        os.path.join(os.getenv("project_path"),
                                     self.proto_interface_folder) +
                        " " +
                        self.proto_package_name, cwd=os.getenv("project_path"),
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
                else:
                    proc = subprocess.Popen(
                        "python3 -m" +
                        " " +
                        PROTOC_COMMAND +
                        " " +
                        "-I =" +
                        interface_folder_path +
                        "   --python_out=" +
                        os.path.join(os.getenv("project_path"),
                                     self.proto_interface_folder) +
                        " --grpc_python_out=" +
                        os.path.join(os.getenv("project_path"),
                                     self.proto_interface_folder) +
                        " " +
                        self.proto_package_name, cwd=os.getenv("project_path"),
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
                proc.communicate()
            else:
                interface_folder_path = "."
                if platform.system() == 'Windows':
                    proc = subprocess.Popen(
                        "python3 -m" +
                        " " +
                        PROTOC_COMMAND +
                        " " +
                        "-I =" +
                        interface_folder_path +
                        "   --python_out=" +
                        "./" +
                        self.proto_interface_folder +
                        " --grpc_python_out=" +
                        "./" +
                        self.proto_interface_folder +
                        " " +
                        self.proto_package_name, cwd=os.getcwd(),
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
                else:
                    proc = subprocess.Popen(
                        "python3 -m" +
                        " " +
                        PROTOC_COMMAND +
                        " " +
                        "-I =" +
                        interface_folder_path +
                        "   --python_out=" +
                        "./" +
                        self.proto_interface_folder +
                        " --grpc_python_out=" +
                        "./" +
                        self.proto_interface_folder +
                        " " +
                        self.proto_package_name, cwd=os.getcwd(),
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
                proc.communicate()
            if proc.returncode != 0:
                raise Exception("failed to generated grpc files")
            LOG.debug(
                "--- successfully generated *_pb2 and *_pb2_grpc module ---")
        finally:
            proc.terminate()
        sys.path.extend(self.proto_interface_folder)
        Path(
            os.path.join(
                self.proto_interface_folder,
                "__init__.py")).touch()

    def delete_grpc_interface_modules(self):
        """

        """
        try:
            if os.path.exists(self.proto_interface_folder):
                shutil.rmtree(self.proto_interface_folder)
        except IOError:
            raise IOError(
                f'--- {self.proto_interface_folder} does not exists ---')


class GrpcClient(GrpcModuleGenerator):
    """
    Execute grpc request
    """

    def __init__(self, **payload):
        proto_package_name = payload.get("protoPackage")
        dependent_proto_package = payload.get("dependentProtoPackage", None)
        super().__init__(proto_package_name, dependent_proto_package)
        self.payload = payload
        self.return_response = None
        self.pb2_module_name = None
        self.pb2_grpc_module_name = None
        self.grpc_sym_db = _symbol_database.Default()

    def execute_grpc_request(self):
        """
        execute grpc request
        return: None
        """
        pdb_module_name, pdb_grpc_module_name = self.import_grpc_module()
        grpc_channel = self.define_channel_interface()
        service_name, method = self.get_grpc_service_method()
        grpc_input_type, grpc_output_type = self._get_input_from_grpc_service(
            service=service_name,
            method=method)
        self.service_name = service_name
        self.method = method

        def execute():
            stub_property = self.get_stub_property(service_name)
            stub = getattr(pdb_grpc_module_name, stub_property)
            self.return_response = getattr(
                stub(grpc_channel),
                method)(self.create_protobuff_request(grpc_input_type))
            self.return_response = MessageToDict(self.return_response)
            LOG.debug(f'--- server response {self.return_response} --- ')

        try:
            exec(str(execute()))
        except Exception as error:
            raise Exception(f'{error}')

    def create_protobuff_request(self, grpc_input_type=None):
        """
        creates protobuff json input to protobuff message
        :return:
        """
        try:
            grpc_payload = self.payload.get('input')
            protobuff_request = Parse(
                json.dumps(
                    grpc_payload),
                grpc_input_type())
            LOG.debug(f"--- Payload protobuff_request {protobuff_request} ---")
            return protobuff_request
        except ParseError as e:
            LOG.error(f"--- {e} --- ")
            raise ParseError(f'-- {e} --- ')
        except KeyError:
            raise KeyError

    @staticmethod
    def camelize(string, uppercase_first_letter=True):
        """
        converts string to upper case
        params:
        return: str
        """
        if uppercase_first_letter:
            stub_property = re.sub(
                r"(?:^|_)(.)", lambda m: m.group(1).upper(), string)
            LOG.debug(f'--- stub object {stub_property} ---')
            return stub_property
        else:
            stub_property = string[0].lower(
            ) + GrpcClient.camelize(string)[1:]
            LOG.debug(f'--- stub object {stub_property} ---')
            return stub_property

    def get_stub_property(self, service_name):
        """
        get the service name
        :param service_name:
        :return:
        """
        return self.camelize(service_name) + 'Stub'

    def define_channel_interface(self):
        """
        create channel interface for grpc communication
        :param self:
        :param port_number:
        :param ipAddress:
        :return:
        """

        try:
            if self.payload is None:
                hostip = 'localhost'
                port_number = '50051'
            else:
                hostip = self.payload.get('connect').get("host")
                port_number = self.payload.get('connect').get("port")
            server_target = "{}:{}".format(hostip, port_number)
            LOG.debug(
                f"--- host target {server_target} for grpc communication ---")
            grpc_channel = grpc.insecure_channel(
                server_target)
            LOG.debug(f"--- created grpc channel {grpc_channel} ---")
            return grpc_channel
        except KeyError:
            raise KeyError

    def import_grpc_module(self):
        """
        Import generated pb2 and _pb2_grpc file
        """
        try:
            LOG.debug(
                f" my proto interface folder {self.proto_interface_folder}")
            pb2_module_name = pb2_grpc_module_name = None
            for folderName, subfolders, filenames in os.walk(
                    self.proto_interface_folder):
                if not str(filenames).__contains__("cpython") and str(
                        filenames.__contains__("init")):
                    for filename in filenames:
                        if filename.__contains__("grpc"):
                            pb2_grpc_module_name = filename.split('.')[0]
                            with open(os.path.join(self.proto_interface_folder,
                                                   filename), 'r+') as fr:
                                temp_code = fr.read()
                                fr.seek(0)
                                sys_code = "import sys"
                                path_append_code =\
                                    f"sys.path.append('{self.proto_interface_folder}')"  # noqa pylint: disable=unused-import
                                fr.write(sys_code)
                                fr.write('\n')
                                fr.write(path_append_code)
                                fr.write(temp_code)
                                # fr.write(
                                #     re.sub(
                                #         r'(import .+_pb2.*)',
                                #         'from . \\1',
                                #         temp_code))
                                fr.truncate()
                            # pb2_grpc_module_name = import_module(
                            #     "." + pb2_grpc_module_name,
                            #     self.proto_interface_folder)
                        else:
                            pb2_module_name = filename.split('.')[0]
                            with open(os.path.join(self.proto_interface_folder,
                                                   filename), 'r+') as fr:
                                temp_code = fr.read()
                                fr.seek(0)
                                sys_code = "import sys"
                                path_append_code = f"sys.path.append('{self.proto_interface_folder}')"  # noqa pylint: disable=unused-import
                                fr.write(sys_code)
                                fr.write('\n')
                                fr.write(path_append_code)
                                fr.write(temp_code)
                                fr.truncate()
                            # pdb_module_name = import_module(
                            #     "." + pb2_module_name,
                            #     self.proto_interface_folder)
            for folderName, subfolders, filenames in os.walk(
                    self.proto_interface_folder):
                proto_name = self.proto_package_name_.split(".")[0]
                if not str(filenames).__contains__("cpython") and str(
                        filenames.__contains__("init")):
                    for filename in filenames:
                        if filename.__contains__(
                                "grpc") and filename.startswith(proto_name):
                            pb2_grpc_module_name = filename.split('.')[0]
                            pb2_grpc_module_name = import_module(
                                "." + pb2_grpc_module_name,
                                self.proto_interface_folder)
                        elif filename.startswith(proto_name) and not filename.__contains__("grpc"):  # noqa pylint: disable=unused-import
                            pb2_module_name = filename.split('.')[0]
                            pb2_module_name = import_module(
                                "." + pb2_module_name,
                                self.proto_interface_folder)
            return pb2_module_name, pb2_grpc_module_name
        except ImportError:
            raise ImportError
        except FileNotFoundError:
            raise FileNotFoundError

    def get_grpc_service_method(self):
        """
        get service, method from payload
        :param service:
        :return:
        """
        try:
            full_service = self.payload.get("service").split('/')
            service, method = full_service[0], full_service[1]
            LOG.debug(
                f"--- service {service} method {method}"
                f" for grpc communication ---")
            return service, method
        except IndexError:
            raise IndexError("/ not found")
        except KeyError:
            raise KeyError("Key service not found {}".format(self.payload))

    def _get_input_from_grpc_service(self, service, method):
        """
        get the input type, output type of grpc client
        :param service:
        :param method:
        :return:
        """
        full_service_name = "{}.{}".format(service, method)
        try:
            # built-in api FindMethodByName, GetPrototype given by google
            grpc_service = self.grpc_sym_db.pool.FindMethodByName(
                full_service_name)
            input_type = self.grpc_sym_db.GetPrototype(
                grpc_service.input_type)
            output_type = self.grpc_sym_db.GetPrototype(
                grpc_service.output_type)
            LOG.debug(f'--- input_type {input_type} of protobuff ---')
            return input_type, output_type
        except KeyError:
            raise KeyError


class Grpc():
    def __init__(self, payload):
        LOG.debug("--- start grpc execution ---")
        with open(payload, 'r') as fr:
            payload = json.load(fr)
        self.grpcclient = GrpcClient(**payload)

    def grpc_executor(self):
        self.grpcclient.execute_grpc_request()
        self.grpcclient.delete_grpc_interface_modules()
        LOG.debug("--- end grpc execution ---")


def main():
    """

    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-input', type=str,
                        help="input file name",
                        required=True)
    args = parser.parse_args()
    grpc_object = Grpc(args.input)
    grpc_object.grpc_executor()


if __name__ == '__main__':
    main()
