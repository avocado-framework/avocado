import json
import unittest
import unittest.mock

from avocado.utils import nvme, process

# ---------------------------------------------------------------------------
# JSON topology fixtures
# ---------------------------------------------------------------------------

# Targeted-controller schema: Name and State reside directly on Path.
_TOPOLOGY_TARGETED = [
    {
        "Subsystems": [
            {
                "Namespaces": [
                    {
                        "NSID": 1,
                        "Paths": [
                            {
                                "Name": "nvme0",
                                "State": "live",
                                "ANAState": "optimized",
                                "Controller": [],
                            }
                        ],
                    }
                ]
            }
        ]
    }
]

# Whole-system schema: Name and State are nested under Controller[].
_TOPOLOGY_WHOLE_SYSTEM = [
    {
        "Subsystems": [
            {
                "Namespaces": [
                    {
                        "NSID": 1,
                        "Paths": [
                            {
                                "ANAState": "optimized",
                                "Controller": [
                                    {"Name": "nvme0", "State": "live"},
                                    {"Name": "nvme3", "State": "live"},
                                ],
                            }
                        ],
                    }
                ]
            }
        ]
    }
]

# Error payload returned by some nvme-cli builds for a targeted query.
_ERROR_PAYLOAD = {"error": "Invalid device name"}


def _make_run_result(stdout_text, exit_status=0):
    """Return a minimal process.CmdResult mock for process.run()."""
    result = process.CmdResult(command="nvme ...", stdout=stdout_text.encode())
    result.exit_status = exit_status
    return result


# ===========================================================================
# _iter_topology_paths() tests
# ===========================================================================


class IterTopologyPathsTest(unittest.TestCase):
    """Tests for _iter_topology_paths() covering both JSON schemas."""

    # --- Guard-clause: non-list input ---

    def test_none_input_yields_nothing(self):
        self.assertEqual(list(nvme._iter_topology_paths(None, 1)), [])

    def test_dict_input_yields_nothing(self):
        self.assertEqual(list(nvme._iter_topology_paths({}, 1)), [])

    def test_empty_list_yields_nothing(self):
        self.assertEqual(list(nvme._iter_topology_paths([], 1)), [])

    # --- Targeted schema (Name/State on Path directly) ---

    def test_targeted_schema_returns_name_state_ana_state(self):
        results = list(nvme._iter_topology_paths(_TOPOLOGY_TARGETED, 1))
        self.assertEqual(len(results), 1)
        name, state, ana_state = results[0]
        self.assertEqual(name, "nvme0")
        self.assertEqual(state, "live")
        self.assertEqual(ana_state, "optimized")

    # --- Whole-system schema (Name/State under Controller[]) ---

    def test_whole_system_schema_yields_one_tuple_per_controller(self):
        results = list(nvme._iter_topology_paths(_TOPOLOGY_WHOLE_SYSTEM, 1))
        self.assertEqual(len(results), 2)
        names = [r[0] for r in results]
        self.assertIn("nvme0", names)
        self.assertIn("nvme3", names)
        # ANAState from the Path is propagated to every Controller entry.
        for _, _, ana_state in results:
            self.assertEqual(ana_state, "optimized")

    # --- NSID filter ---

    def test_nsid_filter_skips_non_matching_namespaces(self):
        """Only paths for the requested NSID are yielded."""
        topology = [
            {
                "Subsystems": [
                    {
                        "Namespaces": [
                            {
                                "NSID": 1,
                                "Paths": [
                                    {
                                        "Name": "nvme0",
                                        "State": "live",
                                        "ANAState": "optimized",
                                        "Controller": [],
                                    }
                                ],
                            },
                            {
                                "NSID": 2,
                                "Paths": [
                                    {
                                        "Name": "nvme0",
                                        "State": "dead",
                                        "ANAState": "non-optimized",
                                        "Controller": [],
                                    }
                                ],
                            },
                        ]
                    }
                ]
            }
        ]
        results_ns1 = list(nvme._iter_topology_paths(topology, 1))
        self.assertEqual(len(results_ns1), 1)
        self.assertEqual(results_ns1[0][1], "live")

        results_ns2 = list(nvme._iter_topology_paths(topology, 2))
        self.assertEqual(len(results_ns2), 1)
        self.assertEqual(results_ns2[0][1], "dead")

    def test_unknown_nsid_yields_nothing(self):
        results = list(nvme._iter_topology_paths(_TOPOLOGY_TARGETED, 99))
        self.assertEqual(results, [])

    # --- Missing keys produce None, not KeyError ---

    def test_missing_name_state_keys_produce_none(self):
        topology = [
            {
                "Subsystems": [
                    {
                        "Namespaces": [
                            {
                                "NSID": 1,
                                "Paths": [{"Controller": []}],
                            }
                        ]
                    }
                ]
            }
        ]
        results = list(nvme._iter_topology_paths(topology, 1))
        self.assertEqual(len(results), 1)
        name, state, ana_state = results[0]
        self.assertIsNone(name)
        self.assertIsNone(state)
        self.assertIsNone(ana_state)


# ===========================================================================
# get_ns_status() tests
# ===========================================================================


class GetNsStatusTest(unittest.TestCase):
    """Tests for the two-stage get_ns_status() function."""

    # --- Primary path succeeds (targeted schema) -------------------------

    @unittest.mock.patch("avocado.utils.nvme.process.run")
    def test_primary_targeted_schema_returns_state(self, mock_run):
        """Primary path with targeted schema returns [State, ANAState],
        no fallback."""
        mock_run.return_value = _make_run_result(json.dumps(_TOPOLOGY_TARGETED))
        result = nvme.get_ns_status("nvme0", 1)
        self.assertEqual(result, ["live", "optimized"])
        self.assertEqual(mock_run.call_count, 1)

    @unittest.mock.patch("avocado.utils.nvme.process.run")
    def test_primary_whole_system_schema_returns_state(self, mock_run):
        """Primary path with Controller[] schema returns correct state."""
        mock_run.return_value = _make_run_result(json.dumps(_TOPOLOGY_WHOLE_SYSTEM))
        result = nvme.get_ns_status("nvme0", 1)
        self.assertEqual(result, ["live", "optimized"])
        self.assertEqual(mock_run.call_count, 1)

    # --- Primary path returns error payload → fallback -------------------

    @unittest.mock.patch("avocado.utils.nvme.process.run")
    def test_error_payload_triggers_fallback(self, mock_run):
        """
        {"error": ...} is valid JSON but not a list, so _iter_topology_paths()
        yields nothing; fallback must be invoked.
        """
        mock_run.side_effect = [
            _make_run_result(json.dumps(_ERROR_PAYLOAD)),
            _make_run_result(json.dumps(_TOPOLOGY_TARGETED)),
        ]
        result = nvme.get_ns_status("nvme0", 1)
        self.assertEqual(result, ["live", "optimized"])
        self.assertEqual(mock_run.call_count, 2)

    # --- Primary path returns invalid JSON → fallback --------------------

    @unittest.mock.patch("avocado.utils.nvme.process.run")
    def test_primary_json_decode_error_triggers_fallback(self, mock_run):
        mock_run.side_effect = [
            _make_run_result("not json at all"),
            _make_run_result(json.dumps(_TOPOLOGY_TARGETED)),
        ]
        result = nvme.get_ns_status("nvme0", 1)
        self.assertEqual(result, ["live", "optimized"])
        self.assertEqual(mock_run.call_count, 2)

    # --- Primary has no match for controller name → fallback -------------

    @unittest.mock.patch("avocado.utils.nvme.process.run")
    def test_primary_controller_name_mismatch_triggers_fallback(self, mock_run):
        """
        Primary topology only contains 'nvme3'; querying for 'nvme0' finds no
        match and must fall through to the whole-system fallback.
        """
        primary_wrong_ctrl = [
            {
                "Subsystems": [
                    {
                        "Namespaces": [
                            {
                                "NSID": 1,
                                "Paths": [
                                    {
                                        "Name": "nvme3",
                                        "State": "live",
                                        "ANAState": "optimized",
                                        "Controller": [],
                                    }
                                ],
                            }
                        ]
                    }
                ]
            }
        ]
        fallback = [
            {
                "Subsystems": [
                    {
                        "Namespaces": [
                            {
                                "NSID": 1,
                                "Paths": [
                                    {
                                        "Name": "nvme0",
                                        "State": "live",
                                        "ANAState": "inaccessible",
                                        "Controller": [],
                                    }
                                ],
                            }
                        ]
                    }
                ]
            }
        ]
        mock_run.side_effect = [
            _make_run_result(json.dumps(primary_wrong_ctrl)),
            _make_run_result(json.dumps(fallback)),
        ]
        result = nvme.get_ns_status("nvme0", 1)
        self.assertEqual(result, ["live", "inaccessible"])
        self.assertEqual(mock_run.call_count, 2)

    # --- Multi-path: nvme0 + nvme3 share a namespace ---------------------

    @unittest.mock.patch("avocado.utils.nvme.process.run")
    def test_multipath_nvme3_found_via_whole_system_fallback(self, mock_run):
        """
        In a multi-path subsystem (nvme0 + nvme3 share NSID 1), querying for
        nvme3 finds its entry in the whole-system fallback topology.
        """
        mock_run.side_effect = [
            _make_run_result(json.dumps(_ERROR_PAYLOAD)),
            _make_run_result(json.dumps(_TOPOLOGY_WHOLE_SYSTEM)),
        ]
        result = nvme.get_ns_status("nvme3", 1)
        self.assertEqual(result, ["live", "optimized"])
        self.assertEqual(mock_run.call_count, 2)

    # --- Both paths fail → empty list ------------------------------------

    @unittest.mock.patch("avocado.utils.nvme.process.run")
    def test_both_paths_invalid_json_returns_empty_list(self, mock_run):
        """If both primary and fallback return unparsable output,
        [] is returned."""
        mock_run.side_effect = [
            _make_run_result("bad"),
            _make_run_result("also bad"),
        ]
        result = nvme.get_ns_status("nvme0", 1)
        self.assertEqual(result, [])

    @unittest.mock.patch("avocado.utils.nvme.process.run")
    def test_nsid_absent_in_fallback_returns_empty_list(self, mock_run):
        """Fallback topology has no matching NSID → empty list returned."""
        no_match = [
            {
                "Subsystems": [
                    {
                        "Namespaces": [
                            {
                                "NSID": 99,
                                "Paths": [
                                    {
                                        "Name": "nvme0",
                                        "State": "live",
                                        "ANAState": "optimized",
                                        "Controller": [],
                                    }
                                ],
                            }
                        ]
                    }
                ]
            }
        ]
        mock_run.side_effect = [
            _make_run_result("bad json"),
            _make_run_result(json.dumps(no_match)),
        ]
        result = nvme.get_ns_status("nvme0", 1)
        self.assertEqual(result, [])

    # --- Command construction checks -------------------------------------

    @unittest.mock.patch("avocado.utils.nvme.process.run")
    def test_primary_command_targets_controller_device(self, mock_run):
        """Primary command must include /dev/<controller_name>."""
        mock_run.return_value = _make_run_result(json.dumps(_TOPOLOGY_TARGETED))
        nvme.get_ns_status("nvme0", 1)
        primary_cmd = mock_run.call_args_list[0][0][0]
        self.assertIn("/dev/nvme0", primary_cmd)
        self.assertIn("show-topology", primary_cmd)

    @unittest.mock.patch("avocado.utils.nvme.process.run")
    def test_fallback_command_omits_device_path(self, mock_run):
        """Fallback (whole-system) command must not include /dev/."""
        mock_run.side_effect = [
            _make_run_result("invalid"),
            _make_run_result(json.dumps(_TOPOLOGY_TARGETED)),
        ]
        nvme.get_ns_status("nvme0", 1)
        fallback_cmd = mock_run.call_args_list[1][0][0]
        self.assertNotIn("/dev/", fallback_cmd)
        self.assertIn("show-topology", fallback_cmd)


if __name__ == "__main__":
    unittest.main()
