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


class UtilsNvmeTest(unittest.TestCase):
    @unittest.mock.patch("os.path.exists", return_value=True)
    def test_get_atomic_write_units(self, _):
        mock_data = {
            "/sys/block/nvme0n1/queue/atomic_write_unit_min_bytes": "4096\n",
            "/sys/block/nvme0n1/queue/atomic_write_unit_max_bytes": "65536\n",
        }

        def mock_open(path, *_args, **_kwargs):
            return unittest.mock.mock_open(read_data=mock_data[path])()

        with unittest.mock.patch("builtins.open", side_effect=mock_open):
            min_val, max_val = nvme.get_atomic_write_units("/dev/nvme0n1")
            self.assertEqual(min_val, 4096)
            self.assertEqual(max_val, 65536)

    @unittest.mock.patch("os.path.exists", return_value=False)
    def test_get_atomic_write_units_not_supported(self, _):
        min_val, max_val = nvme.get_atomic_write_units("/dev/nvme0n1")
        self.assertEqual(min_val, 0)
        self.assertEqual(max_val, 0)

    @unittest.mock.patch("avocado.utils.nvme.get_atomic_write_units")
    def test_find_device_with_atomic_write_explicit_devices(self, mock_get_units):
        mock_get_units.side_effect = [(0, 0), (4096, 65536)]
        dev, min_val, max_val = nvme.find_device_with_atomic_write(
            ["/dev/nvme0n1", "/dev/nvme1n1"]
        )
        self.assertEqual(dev, "/dev/nvme1n1")
        self.assertEqual(min_val, 4096)
        self.assertEqual(max_val, 65536)

    @unittest.mock.patch(
        "avocado.utils.nvme.get_atomic_write_units", return_value=(0, 0)
    )
    @unittest.mock.patch(
        "avocado.utils.process.system_output", return_value=b"/dev/nvme0n1\n"
    )
    def test_find_device_with_atomic_write_none_found(
        self, _mock_sys_out, _mock_get_units
    ):
        dev, min_val, max_val = nvme.find_device_with_atomic_write()
        self.assertIsNone(dev)
        self.assertEqual(min_val, 0)
        self.assertEqual(max_val, 0)

    @unittest.mock.patch("avocado.utils.process.system_output")
    def test_get_free_space_blocks(self, mock_sys_out):
        mock_sys_out.return_value = (
            b"Number  Start    End      Size     Type     File system  Flags\n"
            b"        0.00MiB  1.00MiB  1.00MiB           Free Space\n"
            b" 1      1.00MiB  100MiB   99.0MiB  primary  ext4\n"
            b"        100MiB   200MiB   100MiB            Free Space\n"
        )
        blocks = nvme.get_free_space_blocks("/dev/nvme0n1")
        self.assertEqual(blocks, [(0.0, 1.0, 1.0), (100.0, 200.0, 100.0)])

    @unittest.mock.patch("avocado.utils.process.run")
    @unittest.mock.patch("avocado.utils.process.system_output")
    @unittest.mock.patch(
        "avocado.utils.nvme.get_free_space_blocks",
        return_value=[(100.0, 300.0, 200.0)],
    )
    def test_create_partitions_in_free_space(self, _mock_free, mock_sys_out, mock_run):
        mock_sys_out.side_effect = [
            b"/dev/nvme0n1\n",
            b"/dev/nvme0n1\n/dev/nvme0n1p1\n/dev/nvme0n1p2\n",
        ]
        parts = nvme.create_partitions_in_free_space("/dev/nvme0n1", count=2)
        self.assertEqual(parts, ["/dev/nvme0n1p1", "/dev/nvme0n1p2"])
        expected_calls = [
            unittest.mock.call(
                "parted -s /dev/nvme0n1 mkpart primary 100.0MiB 200.0MiB",
                sudo=True,
            ),
            unittest.mock.call(
                "parted -s /dev/nvme0n1 mkpart primary 200.0MiB 300.0MiB",
                sudo=True,
            ),
            unittest.mock.call("partprobe /dev/nvme0n1", sudo=True, ignore_status=True),
        ]
        mock_run.assert_has_calls(expected_calls)

    @unittest.mock.patch("avocado.utils.nvme.get_free_space_blocks", return_value=[])
    def test_create_partitions_in_free_space_no_space(self, _mock_free):
        with self.assertRaises(nvme.NvmeException):
            nvme.create_partitions_in_free_space("/dev/nvme0n1")

    @unittest.mock.patch("avocado.utils.process.run")
    def test_remove_partitions(self, mock_run):
        nvme.remove_partitions("/dev/nvme0n1", ["/dev/nvme0n1p1", "/dev/nvme0n1p2"])
        expected_calls = [
            unittest.mock.call(
                "parted -s /dev/nvme0n1 rm 1", sudo=True, ignore_status=True
            ),
            unittest.mock.call(
                "parted -s /dev/nvme0n1 rm 2", sudo=True, ignore_status=True
            ),
            unittest.mock.call("partprobe /dev/nvme0n1", sudo=True, ignore_status=True),
        ]
        mock_run.assert_has_calls(expected_calls)


if __name__ == "__main__":
    unittest.main()
