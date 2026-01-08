import numpy as np

from simulation.core.spacecraft import Spacecraft


def test_set_quaternion_accepts_int_array_and_normalizes():
    sc = Spacecraft()

    # Int array previously caused in-place division casting error
    sc.set_quaternion(np.array([1, 0, 0, 0], dtype=int))

    q = sc.attitude_state.quaternion
    assert q.dtype.kind == "f"
    assert np.isclose(np.linalg.norm(q), 1.0)
