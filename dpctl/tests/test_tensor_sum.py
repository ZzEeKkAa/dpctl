#                       Data Parallel Control (dpctl)
#
#  Copyright 2020-2023 Intel Corporation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import pytest

import dpctl.tensor as dpt
import dpctl.utils as du
from dpctl.tests.helper import get_queue_or_skip, skip_if_dtype_not_supported

_all_dtypes = [
    "?",
    "i1",
    "u1",
    "i2",
    "u2",
    "i4",
    "u4",
    "i8",
    "u8",
    "f2",
    "f4",
    "f8",
    "c8",
    "c16",
]


@pytest.mark.parametrize("arg_dtype", _all_dtypes)
def test_sum_arg_dtype_default_output_dtype_matrix(arg_dtype):
    q = get_queue_or_skip()
    skip_if_dtype_not_supported(arg_dtype, q)

    m = dpt.ones(100, dtype=arg_dtype)
    r = dpt.sum(m)

    assert isinstance(r, dpt.usm_ndarray)
    if m.dtype.kind == "i":
        assert r.dtype.kind == "i"
    elif m.dtype.kind == "u":
        assert r.dtype.kind == "u"
    elif m.dtype.kind == "f":
        assert r.dtype.kind == "f"
    elif m.dtype.kind == "c":
        assert r.dtype.kind == "c"
    assert dpt.all(r == 100)

    m = dpt.ones(200, dtype=arg_dtype)[:1:-2]
    r = dpt.sum(m)
    assert dpt.all(r == 99)


@pytest.mark.parametrize("arg_dtype", _all_dtypes)
@pytest.mark.parametrize("out_dtype", _all_dtypes[1:])
def test_sum_arg_out_dtype_matrix(arg_dtype, out_dtype):
    q = get_queue_or_skip()
    skip_if_dtype_not_supported(arg_dtype, q)
    skip_if_dtype_not_supported(out_dtype, q)

    m = dpt.ones(100, dtype=arg_dtype)
    r = dpt.sum(m, dtype=out_dtype)

    assert isinstance(r, dpt.usm_ndarray)
    assert r.dtype == dpt.dtype(out_dtype)
    assert dpt.all(r == 100)


def test_sum_empty():
    get_queue_or_skip()
    x = dpt.empty((0,), dtype="u1")
    y = dpt.sum(x)
    assert y.shape == tuple()
    assert int(y) == 0


def test_sum_axis():
    get_queue_or_skip()

    m = dpt.ones((3, 4, 5, 6, 7), dtype="i4")
    s = dpt.sum(m, axis=(1, 2, -1))

    assert isinstance(s, dpt.usm_ndarray)
    assert s.shape == (3, 6)
    assert dpt.all(s == dpt.asarray(4 * 5 * 7, dtype="i4"))


def test_sum_keepdims():
    get_queue_or_skip()

    m = dpt.ones((3, 4, 5, 6, 7), dtype="i4")
    s = dpt.sum(m, axis=(1, 2, -1), keepdims=True)

    assert isinstance(s, dpt.usm_ndarray)
    assert s.shape == (3, 1, 1, 6, 1)
    assert dpt.all(s == dpt.asarray(4 * 5 * 7, dtype=s.dtype))


def test_sum_scalar():
    get_queue_or_skip()

    m = dpt.ones(())
    s = dpt.sum(m)

    assert isinstance(s, dpt.usm_ndarray)
    assert m.sycl_queue == s.sycl_queue
    assert s.shape == ()
    assert s == dpt.full((), 1)


@pytest.mark.parametrize("arg_dtype", _all_dtypes)
@pytest.mark.parametrize("out_dtype", _all_dtypes[1:])
def test_sum_arg_out_dtype_scalar(arg_dtype, out_dtype):
    q = get_queue_or_skip()
    skip_if_dtype_not_supported(arg_dtype, q)
    skip_if_dtype_not_supported(out_dtype, q)

    m = dpt.ones((), dtype=arg_dtype)
    r = dpt.sum(m, dtype=out_dtype)

    assert isinstance(r, dpt.usm_ndarray)
    assert r.dtype == dpt.dtype(out_dtype)
    assert r == 1


def test_sum_keepdims_zero_size():
    """See gh-1293"""
    get_queue_or_skip()
    n = 10
    a = dpt.ones((n, 0, n))

    s1 = dpt.sum(a, keepdims=True)
    assert s1.shape == (1, 1, 1)

    s2 = dpt.sum(a, axis=(0, 1), keepdims=True)
    assert s2.shape == (1, 1, n)

    s3 = dpt.sum(a, axis=(1, 2), keepdims=True)
    assert s3.shape == (n, 1, 1)

    s4 = dpt.sum(a, axis=(0, 2), keepdims=True)
    assert s4.shape == (1, 0, 1)

    a0 = a[0]
    s5 = dpt.sum(a0, keepdims=True)
    assert s5.shape == (1, 1)


@pytest.mark.parametrize("arg_dtype", ["i8", "f4", "c8"])
@pytest.mark.parametrize("n", [1023, 1024, 1025])
def test_largish_reduction(arg_dtype, n):
    q = get_queue_or_skip()
    skip_if_dtype_not_supported(arg_dtype, q)

    m = 5
    x = dpt.ones((m, n, m), dtype=arg_dtype)

    y1 = dpt.sum(x, axis=(0, 1))
    y2 = dpt.sum(x, axis=(1, 2))

    assert dpt.all(dpt.equal(y1, y2))
    assert dpt.all(dpt.equal(y1, n * m))


def test_axis0_bug():
    "gh-1391"
    get_queue_or_skip()

    sh = (1, 2, 3)
    a = dpt.arange(sh[0] * sh[1] * sh[2], dtype="i4")
    a = dpt.reshape(a, sh)
    aT = dpt.permute_dims(a, (2, 1, 0))

    s = dpt.sum(aT, axis=2)
    expected = dpt.asarray([[0, 3], [1, 4], [2, 5]])

    assert dpt.all(s == expected)


@pytest.mark.parametrize("arg_dtype", _all_dtypes[1:])
def test_prod_arg_dtype_default_output_dtype_matrix(arg_dtype):
    q = get_queue_or_skip()
    skip_if_dtype_not_supported(arg_dtype, q)

    m = dpt.ones(100, dtype=arg_dtype)
    r = dpt.prod(m)

    assert isinstance(r, dpt.usm_ndarray)
    if m.dtype.kind == "i":
        assert r.dtype.kind == "i"
    elif m.dtype.kind == "u":
        assert r.dtype.kind == "u"
    elif m.dtype.kind == "f":
        assert r.dtype.kind == "f"
    elif m.dtype.kind == "c":
        assert r.dtype.kind == "c"
    assert dpt.all(r == 1)

    if dpt.isdtype(m.dtype, "unsigned integer"):
        m = dpt.tile(dpt.arange(1, 3, dtype=arg_dtype), 10)[:1:-2]
        r = dpt.prod(m)
        assert dpt.all(r == dpt.asarray(512, dtype=r.dtype))
    else:
        m = dpt.full(200, -1, dtype=arg_dtype)[:1:-2]
        r = dpt.prod(m)
        assert dpt.all(r == dpt.asarray(-1, dtype=r.dtype))


def test_prod_empty():
    get_queue_or_skip()
    x = dpt.empty((0,), dtype="u1")
    y = dpt.prod(x)
    assert y.shape == tuple()
    assert int(y) == 1


def test_prod_axis():
    get_queue_or_skip()

    m = dpt.ones((3, 4, 5, 6, 7), dtype="i4")
    s = dpt.prod(m, axis=(1, 2, -1))

    assert isinstance(s, dpt.usm_ndarray)
    assert s.shape == (3, 6)
    assert dpt.all(s == dpt.asarray(1, dtype="i4"))


@pytest.mark.parametrize("arg_dtype", _all_dtypes)
@pytest.mark.parametrize("out_dtype", _all_dtypes[1:])
def test_prod_arg_out_dtype_matrix(arg_dtype, out_dtype):
    q = get_queue_or_skip()
    skip_if_dtype_not_supported(arg_dtype, q)
    skip_if_dtype_not_supported(out_dtype, q)

    out_dtype = dpt.dtype(out_dtype)
    arg_dtype = dpt.dtype(arg_dtype)
    if dpt.isdtype(out_dtype, "complex floating") and du._is_gen9(
        q.sycl_device
    ):
        pytest.skip(
            "Product reduction for complex output are known "
            "to fail for Gen9 with 2024.0 compiler"
        )

    m = dpt.ones(100, dtype=arg_dtype)
    r = dpt.prod(m, dtype=out_dtype)

    assert isinstance(r, dpt.usm_ndarray)
    assert r.dtype == dpt.dtype(out_dtype)
    assert dpt.all(r == 1)
