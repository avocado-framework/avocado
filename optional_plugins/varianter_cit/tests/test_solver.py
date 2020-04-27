import unittest

from avocado_varianter_cit.Solver import Solver


class SolverTest(unittest.TestCase):

    """
    Test for compute_constraints function
    """

    def test_compute_constraints_without_secret_constraint(self):
        """
        Test that, function shouldn't change constraints if there isn't any secret constraint

        """
        parameters = [3, 3, 3]
        constraints = {((0, 0), (2, 0)), ((0, 1), (1, 1)), ((1, 0), (2, 0))}
        solver = Solver([], [])
        solver.data = parameters
        solver.constraints = constraints
        solver.read_constraints()
        solver.compute_constraints()
        self.assertEqual(solver.constraints, constraints, "compute_constraints change constraints without secret "
                                                          "constraint")

    def test_compute_constraints_new_constraint_with_more_than_one_value_for_one_parameter(self):
        """
        Test that, function shouldn't change constraints. It founds new constraint,
        but the constraint has one parameter with two values. This means that it isn't secreted constraint.
        """
        parameters = [3, 3, 3]
        constraints = {((0, 0), (1, 0)), ((0, 1), (1, 1)), ((1, 2), (2, 0))}
        solver = Solver([], [])
        solver.data = parameters
        solver.constraints = constraints
        solver.read_constraints()
        solver.compute_constraints()
        self.assertEqual(solver.constraints, constraints, "compute_constraints change constraints without secret "
                                                          "constraint")

    def test_compute_constraints_detect_invalid_constraints(self):
        """
        Test that, function should raise an exception, if there is invalid_constraints
        """
        parameters = [3, 3, 3]
        constraints = {((0, 0),), ((0, 1),), ((0, 2),)}
        solver = Solver([], [])
        solver.data = parameters
        solver.constraints = constraints
        solver.read_constraints()
        self.assertRaises(ValueError, solver.compute_constraints)

    def test_compute_constraints_with_one_secrete_constraint(self):
        """
        Test that, function should find new constraint
        """
        parameters = [3, 3, 3, 3]
        constraints = {((0, 0), (2, 0)), ((0, 1), (1, 1), (2, 0)), ((0, 2), (3, 2))}
        solver = Solver([], [])
        solver.data = parameters
        solver.constraints = constraints
        solver.read_constraints()
        solver.compute_constraints()
        expectation = {((0, 0), (2, 0)), ((0, 1), (1, 1), (2, 0)), ((0, 2), (3, 2)),
                       ((1, 1), (2, 0), (3, 2))}
        self.assertEqual(solver.constraints, expectation, "compute_constraints didn't find secret constraints")

    # Test for simplify_constraints function

    def test_simplify_constraints_constraints_without_simplification(self):
        """
        Test that, function do not delete important constraints
        """
        parameters = [3, 3, 3, 3]
        constraints = {((0, 0), (2, 0)), ((0, 1), (1, 1), (2, 0)), ((0, 2), (3, 2))}
        solver = Solver([], [])
        solver.data = parameters
        solver.constraints = constraints
        solver.read_constraints()
        solver.simplify_constraints()
        self.assertEqual(solver.constraints, constraints, "simplify_constraints deleted some important constraints")

    def test_simplify_constraints_constraints_with_simplification(self):
        """
        Test that, function do not delete important constraints
        """
        parameters = [3, 3, 3, 3]
        constraints = {((0, 0), (2, 0)), ((0, 1), (2, 0), (1, 1)),
                       ((0, 2), (2, 0)), ((2, 0),)}
        solver = Solver([], [])
        solver.data = parameters
        solver.constraints = constraints
        solver.read_constraints()
        solver.simplify_constraints()
        expectation = {((2, 0),)}
        self.assertEqual(solver.constraints, expectation, "simplify_constraints deleted some important constraints")

    # Test of Minimum forbidden tuple algorithm

    def test_solver_without_secrete_constraints(self):
        """
        Test that, solver didn't change constraints if there isn't any secret constraint
        """
        parameters = [3, 3, 3]
        constraints = {((0, 0), (2, 0)), ((0, 1), (1, 1)), ((1, 0), (2, 0))}
        solver = Solver(parameters, constraints)
        self.assertEqual(solver.constraints, constraints, "solver change constraints without secret "
                                                          "constraint")

    def test_solver_constraints_without_simplification(self):
        """
        Test that, solver do not delete important constraints
        """
        parameters = [3, 3, 3, 3]
        constraints = {((0, 0), (2, 0)), ((0, 1), (1, 1), (2, 0)), ((0, 2), (3, 2))}
        solver = Solver(parameters, constraints)
        self.assertEqual(solver.constraints, constraints, "solver deleted some important constraints")

    def test_solver_constraints_with_simplification_and_secrete(self):
        """
        Test that, Minimum forbidden tuple algorithm can find and simplify constraints
        """
        parameters = [3, 3, 3, 3]
        constraints = {((0, 0), (1, 0)), ((0, 0), (1, 2)), ((0, 1), (3, 0)),
                       ((0, 2), (3, 0)), ((1, 1), (3, 0))}
        solver = Solver(parameters, constraints)
        expectation = {((0, 0), (1, 0)), ((0, 0), (1, 2)), ((3, 0),)}
        self.assertEqual(solver.constraints, expectation, "solver can not compute and simplify constraints")


if __name__ == '__main__':
    unittest.main()
