import os
from typing import Union


class CPKException(RuntimeError):

    def __init__(self, msg: str):
        super(RuntimeError, self).__init__(msg)


class NotACPKProjectException(CPKException):

    def __init__(self, path: str):
        super(NotACPKProjectException, self).__init__(
            f"The path '{path}' does not appear to be a CPK project. " +
            (f"The metadata file 'project.cpk' is missing." if os.path.isdir(path) else
             "Path does not exist."))


class InvalidCPKProjectFile(CPKException):

    def __init__(self, path: str, reason: Union[str, None] = None):
        super(InvalidCPKProjectFile, self).__init__(
            f"The path `{path}` contains an invalid CPK project file." + (
                f" Reason: {reason}" if reason else ""
            ))


class CPKProjectSchemaNotSupported(CPKException):

    def __init__(self, schema: str):
        super(CPKProjectSchemaNotSupported, self).__init__(
            f"The project schema used in this project (`{schema}`) is not supported by this "
            f"version of CPK.")


class InvalidCPKTemplate(CPKException):

    def __init__(self, reason: Union[str, None] = None):
        super(InvalidCPKTemplate, self).__init__(
            f"Found an invalid CPK template. Reason: {reason}" if reason else "")


class InvalidCPKTemplateFile(CPKException):

    def __init__(self, path: str, reason: Union[str, None] = None):
        super(InvalidCPKTemplateFile, self).__init__(
            f"The path `{path}` contains an invalid CPK template file." + (
                f" Reason: {reason}" if reason else ""
            ))


class CPKTemplateSchemaNotSupported(CPKException):

    def __init__(self, schema: str):
        super(CPKTemplateSchemaNotSupported, self).__init__(
            f"The template schema used in this project (`{schema}`) is not supported by this "
            f"version of CPK.")


class CPKMissingResourceException(CPKException):

    def __init__(self, resource: str, explanation: str = None):
        exp = "" if explanation is None else f"{explanation}\n"
        super(CPKMissingResourceException, self).__init__(f"{exp}Missing resource: {resource}")


class CPKProjectBuildException(CPKException):

    def __init__(self, reason: Union[str, BaseException]):
        super(CPKProjectBuildException, self).__init__(f"The project failed to build. "
                                                       f"Reason:\n{str(reason)}")


class CPKProjectPushException(CPKException):

    def __init__(self, reason: Union[str, BaseException]):
        super(CPKProjectPushException, self).__init__(f"The project failed to be pushed. "
                                                       f"Reason:\n{str(reason)}")
