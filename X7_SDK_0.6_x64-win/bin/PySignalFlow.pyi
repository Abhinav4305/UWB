from __future__ import annotations
import typing
__all__: list[str] = ['Break', 'Continue', 'EndOfData', 'EndOfSubgraphData', 'FileError', 'Flow', 'FlowConfigurationError', 'FlowContext', 'FlowLoadError', 'FlowNodeImplNotSupportedError', 'FlowNodeNotSupportedError', 'FlowProcessError', 'FlowSharedMemoryServiceError', 'IDDict', 'Pointed', 'ProcessResult', 'SignalFrameBuffers', 'SubgraphBreak', 'VariantArray', 'signalflow_get_version']
class FileError(Exception):
    pass
class Flow:
    def __init__(self) -> None:
        ...
    def load(self, graph_file: str, **kwargs) -> None:
        ...
    def run(self, graph_file: str = '', cancel_func: typing.Callable[[], bool] = ..., **kwargs) -> None:
        ...
    def set_output_tap(self, callback: typing.Callable[[int, SignalFrame], bool]) -> None:
        ...
    def set_parameters(self, parameter_file: str = '', parameter_string: str = '') -> None:
        ...
class FlowConfigurationError(Exception):
    pass
class FlowContext:
    @property
    def rootdir(self) -> str:
        ...
class FlowLoadError(Exception):
    pass
class FlowNodeImplNotSupportedError(Exception):
    pass
class FlowNodeNotSupportedError(Exception):
    pass
class FlowProcessError(Exception):
    pass
class FlowSharedMemoryServiceError(Exception):
    pass
class IDDict:
    def __bool__(self) -> typing.Any:
        ...
    def __contains__(self, arg0: typing.Any) -> bool:
        ...
    def __delitem__(self, arg0: typing.Any) -> None:
        ...
    def __getitem__(self, arg0: typing.Any) -> typing.Any:
        ...
    def __init__(self, arg0: dict) -> None:
        ...
    def __iter__(self) -> typing.Any:
        ...
    def __repr__(self) -> str:
        ...
    def __setitem__(self, arg0: typing.Any, arg1: typing.Any) -> None:
        ...
class Pointed:
    def __contains__(self, arg0: typing.Any) -> bool:
        ...
    def __delitem__(self, arg0: typing.Any) -> None:
        ...
    def __getattr__(self, arg0: typing.Any) -> typing.Any:
        ...
    def __getitem__(self, arg0: typing.Any) -> typing.Any:
        ...
    def __init__(self, arg0: str, arg1: dict) -> None:
        ...
    def __repr__(self) -> str:
        ...
    def __setattr__(self, arg0: typing.Any, arg1: typing.Any) -> None:
        ...
    def __setitem__(self, arg0: typing.Any, arg1: typing.Any) -> None:
        ...
class ProcessResult:
    """
    Members:
    
      Continue
    
      Break
    
      EndOfData
    
      EndOfSubgraphData
    
      SubgraphBreak
    """
    Break: typing.ClassVar[ProcessResult]  # value = <ProcessResult.Break: 1>
    Continue: typing.ClassVar[ProcessResult]  # value = <ProcessResult.Continue: 0>
    EndOfData: typing.ClassVar[ProcessResult]  # value = <ProcessResult.EndOfData: 2>
    EndOfSubgraphData: typing.ClassVar[ProcessResult]  # value = <ProcessResult.EndOfSubgraphData: 3>
    SubgraphBreak: typing.ClassVar[ProcessResult]  # value = <ProcessResult.SubgraphBreak: 4>
    __members__: typing.ClassVar[dict[str, ProcessResult]]  # value = {'Continue': <ProcessResult.Continue: 0>, 'Break': <ProcessResult.Break: 1>, 'EndOfData': <ProcessResult.EndOfData: 2>, 'EndOfSubgraphData': <ProcessResult.EndOfSubgraphData: 3>, 'SubgraphBreak': <ProcessResult.SubgraphBreak: 4>}
    def __eq__(self, other: typing.Any) -> bool:
        ...
    def __getstate__(self) -> int:
        ...
    def __hash__(self) -> int:
        ...
    def __index__(self) -> int:
        ...
    def __init__(self, value: int) -> None:
        ...
    def __int__(self) -> int:
        ...
    def __ne__(self, other: typing.Any) -> bool:
        ...
    def __repr__(self) -> str:
        ...
    def __setstate__(self, state: int) -> None:
        ...
    def __str__(self) -> str:
        ...
    @property
    def name(self) -> str:
        ...
    @property
    def value(self) -> int:
        ...
class SignalFrameBuffers:
    def __getitem__(self, arg0: int) -> SignalFrame:
        ...
    def __iter__(self) -> SignalFrameBuffers:
        ...
    def __len__(self) -> int:
        ...
    def get_raw(self, arg0: int) -> bytearray:
        ...
class VariantArray:
    pass
def signalflow_get_version() -> tuple[int, int, int]:
    ...
Break: ProcessResult  # value = <ProcessResult.Break: 1>
Continue: ProcessResult  # value = <ProcessResult.Continue: 0>
EndOfData: ProcessResult  # value = <ProcessResult.EndOfData: 2>
EndOfSubgraphData: ProcessResult  # value = <ProcessResult.EndOfSubgraphData: 3>
SubgraphBreak: ProcessResult  # value = <ProcessResult.SubgraphBreak: 4>
__version__: str = '6.11.5'
