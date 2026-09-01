"""Task-owned typed view of TIDMAD's opaque dataset-profile topology."""

from __future__ import annotations

from string import Formatter
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
)

from execute_tools.dataset_config import DatasetProfile, resolve_dataset_profile

_PATTERN_PROBE_INDEX = 7
_TOPOLOGY_SECTIONS = ("dataset", "channels", "encoding")


class TidmadDatasetGeometry(BaseModel):
    """TIDMAD file naming and time-series decomposition geometry."""

    model_config = ConfigDict(frozen=True)

    psd_segment_length: int = Field(gt=0)
    segments_per_file: int = Field(gt=0)
    num_files: int = Field(gt=0)
    sampling_frequency: float = Field(gt=0)
    training_file_pattern: str
    validation_file_pattern: str

    @field_validator("training_file_pattern", "validation_file_pattern")
    @classmethod
    def validate_file_index_pattern(cls, value: str, info: ValidationInfo) -> str:
        """Require an integer ``file_index`` replacement in each pattern."""
        try:
            fields = [name for _, name, _, _ in Formatter().parse(value)]
        except ValueError as exc:
            raise ValueError(
                f"{info.field_name} is not a valid format string: {exc}"
            ) from exc
        bases = {name.split("[")[0].split(".")[0] for name in fields if name}
        if "file_index" not in bases:
            raise ValueError(
                f"{info.field_name} must contain a {{file_index}} replacement field"
            )
        try:
            value.format(file_index=_PATTERN_PROBE_INDEX)
        except Exception as exc:
            raise ValueError(
                f"{info.field_name} does not format with an integer file index: {exc}"
            ) from exc
        return value

    def training_file_name(self, file_index: int) -> str:
        return self.training_file_pattern.format(file_index=file_index)

    def validation_file_name(self, file_index: int) -> str:
        return self.validation_file_pattern.format(file_index=file_index)

    def valid_segmentation_sizes(self, lo: int = 100, hi: int = 100_000) -> list[int]:
        """Return sorted divisors of the PSD segment length in ``[lo, hi]``."""
        divisors: set[int] = set()
        candidate = 1
        while candidate * candidate <= self.psd_segment_length:
            if self.psd_segment_length % candidate == 0:
                paired = self.psd_segment_length // candidate
                if lo <= candidate <= hi:
                    divisors.add(candidate)
                if lo <= paired <= hi:
                    divisors.add(paired)
            candidate += 1
        return sorted(divisors)


class TidmadChannelIdentity(BaseModel):
    """Input and target HDF5 channel identities."""

    model_config = ConfigDict(frozen=True)

    input_channel: str
    target_channel: str

    @field_validator("target_channel")
    @classmethod
    def require_distinct_target(cls, value: str, info: ValidationInfo) -> str:
        if value == info.data.get("input_channel"):
            raise ValueError("target_channel must differ from input_channel")
        return value


class TidmadValueEncoding(BaseModel):
    """Stored ADC representation and shifted model alphabet."""

    model_config = ConfigDict(frozen=True)

    storage_dtype: str
    compute_dtype: str
    value_offset: int
    num_classes: int = Field(gt=0)

    @field_validator("num_classes")
    @classmethod
    def require_alphabet_to_cover_shifted_values(
        cls, value: int, info: ValidationInfo
    ) -> int:
        widths = {"int8": (-128, 127), "uint8": (0, 255), "int16": (-32768, 32767)}
        bounds = widths.get(info.data.get("storage_dtype"))
        offset = info.data.get("value_offset")
        if bounds is None or offset is None:
            return value
        lo, hi = bounds
        if lo + offset < 0 or hi + offset >= value:
            raise ValueError(
                "num_classes does not cover the shifted stored-value range"
            )
        return value


class TidmadTopology(BaseModel):
    """Validated TIDMAD interpretation of a generic opaque topology payload."""

    model_config = ConfigDict(frozen=True)

    dataset: TidmadDatasetGeometry
    channels: TidmadChannelIdentity
    encoding: TidmadValueEncoding


def declares_tidmad_topology(profile: DatasetProfile) -> bool:
    """Whether every required TIDMAD topology section is present."""
    return all(section in profile.topology for section in _TOPOLOGY_SECTIONS)


def tidmad_topology(profile: DatasetProfile) -> TidmadTopology:
    """Decode a generic dataset profile using the task-owned TIDMAD schema."""
    missing = [
        section for section in _TOPOLOGY_SECTIONS if section not in profile.topology
    ]
    if missing:
        raise ValueError(
            f"dataset profile has no complete TIDMAD topology; missing {missing}, "
            f"available keys are {sorted(profile.topology)}"
        )
    try:
        return TidmadTopology.model_validate(
            {section: profile.topology[section] for section in _TOPOLOGY_SECTIONS}
        )
    except ValidationError as exc:
        raise ValueError(
            f"dataset profile does not satisfy the TIDMAD topology: {exc}"
        ) from exc


def resolve_tidmad_topology() -> TidmadTopology:
    """Decode the currently bound generic profile as TIDMAD topology."""
    return tidmad_topology(resolve_dataset_profile())
