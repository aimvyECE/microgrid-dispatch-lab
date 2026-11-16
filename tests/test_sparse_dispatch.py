"""Regression checks for linear-size assembly, not performance benchmarks."""
import unittest
from unittest.mock import patch

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import isspmatrix_csr

from microgrid import Battery, solve, synthetic_day


class SparseDispatchTests(unittest.TestCase):
    def test_sparse_matrix_has_linear_number_of_coefficients(self):
        # Include the one-interval boundary and a full synthetic week.
        for n in (1, 24, 168):
            with self.subTest(n=n):
                def checked_solver(*args, **kwargs):
                    matrix = kwargs['A_eq']
                    self.assertTrue(isspmatrix_csr(matrix))
                    self.assertEqual(matrix.shape, (2*n+1, 5*n))
                    self.assertEqual(matrix.nnz, 8*n)
                    return linprog(*args, **kwargs)
                with patch('microgrid.linprog', side_effect=checked_solver):
                    result = solve(np.ones(n), np.zeros(n), np.ones(n),
                                   np.zeros(n), Battery(initial_fraction=0))
                self.assertAlmostEqual(result['metrics']['grid_kwh'], n)
                self.assertLess(result['metrics']['maximum_equality_residual'], 1e-8)

    def test_sparse_and_dense_solver_objectives_agree(self):
        # Same LP passed to HiGHS via sparse and dense interfaces. Dispatch
        # itself may differ where multiple schedules share the optimum.
        rng = np.random.default_rng(3821)
        profiles = [synthetic_day()]
        for n in (1, 2, 17):
            profiles.append((rng.uniform(0, 4, n), rng.uniform(0, 3, n),
                             rng.uniform(0, .5, n), rng.uniform(0, .8, n)))
        for inputs in profiles:
            for battery in (Battery(0, 0), Battery(initial_fraction=0), Battery()):
                with self.subTest(n=len(inputs[0]), battery=battery):
                    sparse = solve(*inputs, battery, carbon_price=.2, hours=.5)
                    def dense_solver(*args, **kwargs):
                        kwargs['A_eq'] = kwargs['A_eq'].toarray()
                        return linprog(*args, **kwargs)
                    with patch('microgrid.linprog', side_effect=dense_solver):
                        dense = solve(*inputs, battery, carbon_price=.2, hours=.5)
                    self.assertAlmostEqual(sparse['metrics']['objective_eur'],
                                           dense['metrics']['objective_eur'], places=8)
                    self.assertLess(sparse['metrics']['maximum_equality_residual'], 1e-8)


if __name__ == '__main__':
    unittest.main()
