import dataclasses
from typing import Optional
from functools import total_ordering


@total_ordering
@dataclasses.dataclass
class SemanticVersion:
    major: int
    minor: int = 0
    patch: int = 0
    revision: Optional[str] = None

    class Invalid(Exception):
        pass

    @classmethod
    def parse(cls, data: str) -> 'SemanticVersion':
        nparts: int = data.count(".") + 1
        assert nparts <= 4
        M, m, p, r = f"{data}.{'.'.join('0' * (4 - nparts))}".rstrip(".").split(".")
        major: int = cls._parse_unit(M, "major", data)
        minor: int = cls._parse_unit(m, "minor", data)
        patch: int = cls._parse_unit(p, "patch", data)
        revision: Optional[str] = None if nparts < 4 else r
        return SemanticVersion(
            major=major,
            minor=minor,
            patch=patch,
            revision=revision,
        )

    def __eq__(self, other):
        if not isinstance(other, (str, SemanticVersion)):
            return False
        if isinstance(other, str):
            try:
                other = SemanticVersion.parse(other)
            except:
                return False
        return self.major == other.major and self.minor == other.minor and self.patch == other.patch and \
               self.revision == other.revision

    def __lt__(self, other):
        if not isinstance(other, (str, SemanticVersion)):
            raise ValueError(f"Cannot compare object of type SemanticVersion with '{other}'")
        if isinstance(other, str):
            try:
                other = SemanticVersion.parse(other)
            except:
                raise ValueError(f"Cannot compare object of type SemanticVersion with string '{other}'")
        a, b = self, other
        return (a.major, a.minor, a.patch, a.revision) < (b.major, b.minor, b.patch, b.revision)

    @classmethod
    def _parse_unit(cls, data: str, unit: str, full: str) -> int:
        try:
            value: int = int(data)
        except ValueError:
            raise SemanticVersion.Invalid(f"Invalid semantic version '{full}'. Cannot parse component "
                                          f"'{unit}' with value '{data}'. Expected a positive integer.")
        if value < 0:
            raise SemanticVersion.Invalid(f"Invalid semantic version '{full}'. Component '{unit}' must be a "
                                          f"positive integer. '{data}' was given instead.")
        return value

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}" + (f".{self.revision}" if self.revision else "")
