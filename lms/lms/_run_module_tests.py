"""Run one test module without frappe's app-wide discovery.

Scratch helper: `bench run-tests` globs every test file in the app before it
honours --module, and an unrelated broken module aborts the run.
"""

import unittest

import frappe


def execute(module: str = None):
	module = module or frappe.form_dict.get("module")
	frappe.flags.in_test = True
	suite = unittest.TestLoader().loadTestsFromName(module)
	result = unittest.TextTestRunner(verbosity=2).run(suite)
	print(f"\nRESULT ran={result.testsRun} failures={len(result.failures)} errors={len(result.errors)}")
