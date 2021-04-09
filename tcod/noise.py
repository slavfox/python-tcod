"""Noise map generators are provided by this module.

The :any:`Noise.sample_mgrid` and :any:`Noise.sample_ogrid` methods perform
much better than multiple calls to :any:`Noise.get_point`.

Example::

    >>> import numpy as np
    >>> import tcod
    >>> noise = tcod.noise.Noise(
    ...     dimensions=2,
    ...     algorithm=tcod.noise.Algorithm.SIMPLEX,
    ...     seed=42,
    ... )
    >>> samples = noise[tcod.noise.grid(shape=(5, 5), scale=0.25, origin=(0, 0))]
    >>> samples  # Samples are a grid of floats between -1.0 and 1.0
    array([[ 0.        , -0.55046356, -0.76072866, -0.7088647 , -0.68165785],
           [-0.27523372, -0.7205134 , -0.74057037, -0.43919194, -0.29195625],
           [-0.40398532, -0.57662135, -0.33160293,  0.12860827,  0.2864191 ],
           [-0.50773406, -0.2643614 ,  0.24446318,  0.6390255 ,  0.5922846 ],
           [-0.64945626, -0.12529983,  0.5346834 ,  0.80402255,  0.52655405]],
          dtype=float32)
    >>> (samples + 1.0) * 0.5  # You can normalize samples to 0.0 - 1.0
    array([[0.5       , 0.22476822, 0.11963567, 0.14556766, 0.15917107],
           [0.36238313, 0.1397433 , 0.12971482, 0.28040403, 0.35402188],
           [0.29800734, 0.21168932, 0.33419853, 0.5643041 , 0.6432096 ],
           [0.24613297, 0.3678193 , 0.6222316 , 0.8195127 , 0.79614234],
           [0.17527187, 0.4373501 , 0.76734173, 0.9020113 , 0.76327705]],
          dtype=float32)
    >>> ((samples + 1.0) * (256 / 2)).astype(np.uint8)  # Or as 8-bit unsigned bytes.
    array([[128,  57,  30,  37,  40],
           [ 92,  35,  33,  71,  90],
           [ 76,  54,  85, 144, 164],
           [ 63,  94, 159, 209, 203],
           [ 44, 111, 196, 230, 195]], dtype=uint8)
"""  # noqa: E501
import enum
import warnings
from typing import Any, Optional, Sequence, Tuple, Union

import numpy as np

import tcod.constants
import tcod.random
from tcod._internal import deprecate
from tcod.loader import ffi, lib

try:
    from numpy.typing import ArrayLike
except ImportError:  # Python < 3.7, Numpy < 1.20
    from typing import Any as ArrayLike


class Algorithm(enum.IntEnum):
    """Libtcod noise algorithms.

    .. versionadded:: 12.2
    """

    PERLIN = 1
    """Perlin noise."""

    SIMPLEX = 2
    """Simplex noise."""

    WAVELET = 4
    """Wavelet noise."""

    def __repr__(self) -> str:
        return f"tcod.noise.Algorithm.{self.name}"


class Implementation(enum.IntEnum):
    """Noise implementations.

    .. versionadded:: 12.2
    """

    SIMPLE = 0
    """Generate plain noise."""

    FBM = 1
    """Fractional Brownian motion.

    https://en.wikipedia.org/wiki/Fractional_Brownian_motion
    """

    TURBULENCE = 2
    """Turbulence noise implementation."""

    def __repr__(self) -> str:
        return f"tcod.noise.Implementation.{self.name}"


def __getattr__(name: str) -> Implementation:
    if name in Implementation.__members__:
        warnings.warn(
            f"'tcod.noise.{name}' is deprecated,"
            f" use 'tcod.noise.Implementation.{name}' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Implementation[name]
    raise AttributeError(f"module {__name__} has no attribute {name}")


class Noise(object):
    """

    The ``hurst`` exponent describes the raggedness of the resultant noise,
    with a higher value leading to a smoother noise.
    Not used with tcod.noise.SIMPLE.

    ``lacunarity`` is a multiplier that determines how fast the noise
    frequency increases for each successive octave.
    Not used with tcod.noise.SIMPLE.

    Args:
        dimensions (int): Must be from 1 to 4.
        algorithm (int): Defaults to :any:`tcod.noise.Algorithm.SIMPLEX`
        implementation (int):
            Defaults to :any:`tcod.noise.Implementation.SIMPLE`
        hurst (float): The hurst exponent.  Should be in the 0.0-1.0 range.
        lacunarity (float): The noise lacunarity.
        octaves (float): The level of detail on fBm and turbulence
                         implementations.
        seed (Optional[Random]): A Random instance, or None.

    Attributes:
        noise_c (CData): A cffi pointer to a TCOD_noise_t object.
    """

    def __init__(
        self,
        dimensions: int,
        algorithm: int = Algorithm.SIMPLEX,
        implementation: int = Implementation.SIMPLE,
        hurst: float = 0.5,
        lacunarity: float = 2.0,
        octaves: float = 4,
        seed: Optional[Union[int, tcod.random.Random]] = None,
    ):
        if not 0 < dimensions <= 4:
            raise ValueError(
                "dimensions must be in range 0 < n <= 4, got %r"
                % (dimensions,)
            )
        self._seed = seed
        self._random = self.__rng_from_seed(seed)
        _random_c = self._random.random_c
        self.noise_c = ffi.gc(
            ffi.cast(
                "struct TCOD_Noise*",
                lib.TCOD_noise_new(dimensions, hurst, lacunarity, _random_c),
            ),
            lib.TCOD_noise_delete,
        )
        self._tdl_noise_c = ffi.new(
            "TDLNoise*", (self.noise_c, dimensions, 0, octaves)
        )
        self.algorithm = algorithm
        self.implementation = implementation  # sanity check

    @staticmethod
    def __rng_from_seed(
        seed: Union[None, int, tcod.random.Random]
    ) -> tcod.random.Random:
        if seed is None or isinstance(seed, int):
            return tcod.random.Random(
                seed=seed, algorithm=tcod.random.MERSENNE_TWISTER
            )
        return seed

    def __repr__(self) -> str:
        parameters = [
            f"dimensions={self.dimensions}",
            f"algorithm={self.algorithm!r}",
            f"implementation={Implementation(self.implementation)!r}",
        ]
        if self.hurst != 0.5:
            parameters.append(f"hurst={self.hurst}")
        if self.lacunarity != 2:
            parameters.append(f"lacunarity={self.lacunarity}")
        if self.octaves != 4:
            parameters.append(f"octaves={self.octaves}")
        if self._seed is not None:
            parameters.append(f"seed={self._seed}")
        return f"tcod.noise.Noise({', '.join(parameters)})"

    @property
    def dimensions(self) -> int:
        return int(self._tdl_noise_c.dimensions)

    @property  # type: ignore
    @deprecate("This is a misspelling of 'dimensions'.")
    def dimentions(self) -> int:
        return self.dimensions

    @property
    def algorithm(self) -> int:
        noise_type = self.noise_c.noise_type
        return Algorithm(noise_type) if noise_type else Algorithm.SIMPLEX

    @algorithm.setter
    def algorithm(self, value: int) -> None:
        lib.TCOD_noise_set_type(self.noise_c, value)

    @property
    def implementation(self) -> int:
        return Implementation(self._tdl_noise_c.implementation)

    @implementation.setter
    def implementation(self, value: int) -> None:
        if not 0 <= value < 3:
            raise ValueError("%r is not a valid implementation. " % (value,))
        self._tdl_noise_c.implementation = value

    @property
    def hurst(self) -> float:
        return float(self.noise_c.H)

    @property
    def lacunarity(self) -> float:
        return float(self.noise_c.lacunarity)

    @property
    def octaves(self) -> float:
        return float(self._tdl_noise_c.octaves)

    @octaves.setter
    def octaves(self, value: float) -> None:
        self._tdl_noise_c.octaves = value

    def get_point(
        self, x: float = 0, y: float = 0, z: float = 0, w: float = 0
    ) -> float:
        """Return the noise value at the (x, y, z, w) point.

        Args:
            x (float): The position on the 1st axis.
            y (float): The position on the 2nd axis.
            z (float): The position on the 3rd axis.
            w (float): The position on the 4th axis.
        """
        return float(lib.NoiseGetSample(self._tdl_noise_c, (x, y, z, w)))

    def __getitem__(self, indexes: Any) -> np.ndarray:
        """Sample a noise map through NumPy indexing.

        This follows NumPy's advanced indexing rules, but allows for floating
        point values.

        .. versionadded:: 11.16
        """
        if not isinstance(indexes, tuple):
            indexes = (indexes,)
        if len(indexes) > self.dimensions:
            raise IndexError(
                "This noise generator has %i dimensions, but was indexed with %i."
                % (self.dimensions, len(indexes))
            )
        indexes = np.broadcast_arrays(*indexes)
        c_input = [ffi.NULL, ffi.NULL, ffi.NULL, ffi.NULL]
        for i, index in enumerate(indexes):
            if index.dtype.type == np.object_:
                raise TypeError("Index arrays can not be of dtype np.object_.")
            indexes[i] = np.ascontiguousarray(index, dtype=np.float32)
            c_input[i] = ffi.from_buffer("float*", indexes[i])

        out = np.empty(indexes[0].shape, dtype=np.float32)
        if self.implementation == Implementation.SIMPLE:
            lib.TCOD_noise_get_vectorized(
                self.noise_c,
                self.algorithm,
                out.size,
                *c_input,
                ffi.from_buffer("float*", out),
            )
        elif self.implementation == Implementation.FBM:
            lib.TCOD_noise_get_fbm_vectorized(
                self.noise_c,
                self.algorithm,
                self.octaves,
                out.size,
                *c_input,
                ffi.from_buffer("float*", out),
            )
        elif self.implementation == Implementation.TURBULENCE:
            lib.TCOD_noise_get_turbulence_vectorized(
                self.noise_c,
                self.algorithm,
                self.octaves,
                out.size,
                *c_input,
                ffi.from_buffer("float*", out),
            )
        else:
            raise TypeError("Unexpected %r" % self.implementation)

        return out

    def sample_mgrid(self, mgrid: ArrayLike) -> np.ndarray:
        """Sample a mesh-grid array and return the result.

        The :any:`sample_ogrid` method performs better as there is a lot of
        overhead when working with large mesh-grids.

        Args:
            mgrid (numpy.ndarray): A mesh-grid array of points to sample.
                A contiguous array of type `numpy.float32` is preferred.

        Returns:
            numpy.ndarray: An array of sampled points.

                This array has the shape: ``mgrid.shape[:-1]``.
                The ``dtype`` is `numpy.float32`.
        """
        mgrid = np.ascontiguousarray(mgrid, np.float32)
        if mgrid.shape[0] != self.dimensions:
            raise ValueError(
                "mgrid.shape[0] must equal self.dimensions, "
                "%r[0] != %r" % (mgrid.shape, self.dimensions)
            )
        out = np.ndarray(mgrid.shape[1:], np.float32)
        if mgrid.shape[1:] != out.shape:
            raise ValueError(
                "mgrid.shape[1:] must equal out.shape, "
                "%r[1:] != %r" % (mgrid.shape, out.shape)
            )
        lib.NoiseSampleMeshGrid(
            self._tdl_noise_c,
            out.size,
            ffi.from_buffer("float*", mgrid),
            ffi.from_buffer("float*", out),
        )
        return out

    def sample_ogrid(self, ogrid: Sequence[ArrayLike]) -> np.ndarray:
        """Sample an open mesh-grid array and return the result.

        Args
            ogrid (Sequence[Sequence[float]]): An open mesh-grid.

        Returns:
            numpy.ndarray: An array of sampled points.

                The ``shape`` is based on the lengths of the open mesh-grid
                arrays.
                The ``dtype`` is `numpy.float32`.
        """
        if len(ogrid) != self.dimensions:
            raise ValueError(
                "len(ogrid) must equal self.dimensions, "
                "%r != %r" % (len(ogrid), self.dimensions)
            )
        ogrids = [np.ascontiguousarray(array, np.float32) for array in ogrid]
        out = np.ndarray([array.size for array in ogrids], np.float32)
        lib.NoiseSampleOpenMeshGrid(
            self._tdl_noise_c,
            len(ogrids),
            out.shape,
            [ffi.from_buffer("float*", array) for array in ogrids],
            ffi.from_buffer("float*", out),
        )
        return out

    def __getstate__(self) -> Any:
        state = self.__dict__.copy()
        if self.dimensions < 4 and self.noise_c.waveletTileData == ffi.NULL:
            # Trigger a side effect of wavelet, so that copies will be synced.
            saved_algo = self.algorithm
            self.algorithm = tcod.constants.NOISE_WAVELET
            self.get_point()
            self.algorithm = saved_algo

        waveletTileData = None
        if self.noise_c.waveletTileData != ffi.NULL:
            waveletTileData = list(
                self.noise_c.waveletTileData[0 : 32 * 32 * 32]
            )
            state["_waveletTileData"] = waveletTileData

        state["noise_c"] = {
            "ndim": self.noise_c.ndim,
            "map": list(self.noise_c.map),
            "buffer": [list(sub_buffer) for sub_buffer in self.noise_c.buffer],
            "H": self.noise_c.H,
            "lacunarity": self.noise_c.lacunarity,
            "exponent": list(self.noise_c.exponent),
            "waveletTileData": waveletTileData,
            "noise_type": self.noise_c.noise_type,
        }
        state["_tdl_noise_c"] = {
            "dimensions": self._tdl_noise_c.dimensions,
            "implementation": self._tdl_noise_c.implementation,
            "octaves": self._tdl_noise_c.octaves,
        }
        return state

    def __setstate__(self, state: Any) -> None:
        if isinstance(state, tuple):  # deprecated format
            return self._setstate_old(state)
        # unpack wavelet tile data if it exists
        if "_waveletTileData" in state:
            state["_waveletTileData"] = ffi.new(
                "float[]", state["_waveletTileData"]
            )
            state["noise_c"]["waveletTileData"] = state["_waveletTileData"]
        else:
            state["noise_c"]["waveletTileData"] = ffi.NULL

        # unpack TCOD_Noise and link to Random instance
        state["noise_c"]["rand"] = state["_random"].random_c
        state["noise_c"] = ffi.new("struct TCOD_Noise*", state["noise_c"])

        # unpack TDLNoise and link to libtcod noise
        state["_tdl_noise_c"]["noise"] = state["noise_c"]
        state["_tdl_noise_c"] = ffi.new("TDLNoise*", state["_tdl_noise_c"])
        self.__dict__.update(state)

    def _setstate_old(self, state: Any) -> None:
        self._random = state[0]
        self.noise_c = ffi.new("struct TCOD_Noise*")
        self.noise_c.ndim = state[3]
        ffi.buffer(self.noise_c.map)[:] = state[4]
        ffi.buffer(self.noise_c.buffer)[:] = state[5]
        self.noise_c.H = state[6]
        self.noise_c.lacunarity = state[7]
        ffi.buffer(self.noise_c.exponent)[:] = state[8]
        if state[9]:
            # high change of this being prematurely garbage collected!
            self.__waveletTileData = ffi.new("float[]", 32 * 32 * 32)
            ffi.buffer(self.__waveletTileData)[:] = state[9]
        self.noise_c.noise_type = state[10]
        self._tdl_noise_c = ffi.new(
            "TDLNoise*", (self.noise_c, self.noise_c.ndim, state[1], state[2])
        )


def grid(
    shape: Tuple[int, ...],
    scale: Union[Tuple[float, ...], float],
    origin: Optional[Tuple[int, ...]] = None,
) -> Tuple[np.ndarray, ...]:
    """A helper function for generating a grid of noise samples.

    `shape` is the shape of the returned mesh grid.  This can be any number of
    dimensions, but :class:`Noise` classes only support up to 4.

    `scale` is the step size of indexes away from `origin`.
    This can be a single float, or it can be a tuple of floats with one float
    for each axis in `shape`.  A lower scale gives smoother transitions
    between noise values.

    `origin` is the first sample of the grid.
    If `None` then the `origin` will be zero on each axis.
    `origin` is not scaled by the `scale` parameter.

    Example::

        >>> noise = tcod.noise.Noise(dimensions=2, seed=42)
        >>> noise[tcod.noise.grid(shape=(5, 5), scale=0.25)]
        array([[ 0.        , -0.55046356, -0.76072866, -0.7088647 , -0.68165785],
               [-0.27523372, -0.7205134 , -0.74057037, -0.43919194, -0.29195625],
               [-0.40398532, -0.57662135, -0.33160293,  0.12860827,  0.2864191 ],
               [-0.50773406, -0.2643614 ,  0.24446318,  0.6390255 ,  0.5922846 ],
               [-0.64945626, -0.12529983,  0.5346834 ,  0.80402255,  0.52655405]],
              dtype=float32)
        >>> noise[tcod.noise.grid(shape=(5, 5), scale=(0.5, 0.25), origin=(1, 1))]
        array([[ 0.52655405, -0.5037453 , -0.81221616, -0.7057655 ,  0.24630858],
               [ 0.25038874, -0.75348294, -0.6379566 , -0.5817767 , -0.02789652],
               [-0.03488023, -0.73630923, -0.12449139, -0.22774395, -0.22243626],
               [-0.18455243, -0.35063767,  0.4495706 ,  0.02399864, -0.42226675],
               [-0.16333057,  0.18149695,  0.7547447 , -0.07006818, -0.6546707 ]],
              dtype=float32)
    """  # noqa: E501
    if isinstance(scale, float):
        scale = (scale,) * len(shape)
    if origin is None:
        origin = (0,) * len(shape)
    if len(shape) != len(scale):
        raise TypeError("shape must have the same length as scale")
    if len(shape) != len(origin):
        raise TypeError("shape must have the same length as origin")
    indexes = (
        np.arange(i_shape) * i_scale + i_origin
        for i_shape, i_scale, i_origin in zip(shape, scale, origin)
    )
    return tuple(np.meshgrid(*indexes, copy=False, sparse=True, indexing="xy"))
