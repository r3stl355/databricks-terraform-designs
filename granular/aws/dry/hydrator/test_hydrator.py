import unittest
import os
from pathlib import Path
import tempfile

from hydrator import TerragruntConfigParser, Block


class TestHydrator(unittest.TestCase):

    def setUp(self):
        self.config = TerragruntConfigParser(Path('./no-file.hcl'), config_str='', required_blocks=[])

    def _config_with_basic_locals(self) -> str:
        return """
        locals {
            sub_object = {
                str_val = "my-string"
                bool_val = true
                num_val = 12
            }
        }"""

    def test_get_env(self):
        key = 'hydrator_test_get_env_key'
        val = 'test_my_env'
        os.environ[key] = val
        is_ok, res = self.config._resolve(f'"${{get_env("{key}")}}"')
        self.assertTrue(is_ok)
        self.assertEqual(res, val)

    def test_get_terragrunt_dir(self):
        is_ok, res = self.config._resolve(f'"${{get_terragrunt_dir()}}"')
        expected = f'{Path(".").absolute().resolve()}'
        self.assertTrue(is_ok)
        self.assertEqual(res, expected)

    def test_parse_config_locals(self):
        config = TerragruntConfigParser(Path('./no-file.hcl'), config_str=self._config_with_basic_locals(), required_blocks=[])
        sub_object = config.get_block(Block.LOCALS).get('sub_object', None)
        self.assertIsNotNone(sub_object)
        self.assertEqual(sub_object['str_val'], 'my-string')
        self.assertTrue(sub_object['bool_val'])

    def test_parse_replace(self):
        config_str = self._config_with_basic_locals().replace('my-string', "my-${replace(\"some-original-value\", \"original\", \"replaced\")}-string")
        config = TerragruntConfigParser(Path('./no-file.hcl'), config_str=config_str, required_blocks=[])
        new_val = config.get_block(Block.LOCALS)['sub_object']['str_val']
        self.assertEqual(new_val, 'my-some-replaced-value-string')

    def test_parse_config_null_local_errors(self):
        config_str = """
        inputs = {
            should_be_null = local.not_there
        }"""
        with self.assertRaises(LookupError):
            config = TerragruntConfigParser(Path('./no-file.hcl'), config_str=config_str, required_blocks=[])

    def test_parse_config_null_local_errors_in_string(self):
        config_str = """
        inputs = {
            should_be_null = "${local.not_there}"
        }"""
        with self.assertRaises(LookupError):
            TerragruntConfigParser(Path('./no-file.hcl'), config_str=config_str, required_blocks=[])

    def test_jsondecode(self):
        json = '{"sub_object": {"str_val": "my-string", "bool_val": true, "num_val": 12}}'
        self.config.get_block(Block.LOCALS)['json'] = json
        is_ok, res = self.config._resolve(f'jsondecode(local.json)')
        self.assertTrue(is_ok)

    def test_file(self):
        val = '{-}'
        fd, path = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'w') as tmp:
                tmp.write(val)
            is_ok, res = self.config._resolve(f'file("{path}")')  
        finally:
            os.remove(path) 

        self.assertTrue(is_ok)
        self.assertEqual(val, res)

    def test_path_relative_to_include(self):
        parent = Path('.').parent.resolve()
        grand_parent = parent.parent
        config = TerragruntConfigParser(Path(f'../../{grand_parent.name}/no-include-file.hcl'), config_str='', required_blocks=[])
        is_ok, res = config._resolve(f'path_relative_to_include()')
        self.assertTrue(is_ok)
        self.assertEqual(str(res), parent.name)

        is_ok, res = config._resolve('"1-${path_relative_to_include()}-2"')
        self.assertTrue(is_ok)
        self.assertEqual(str(res), f'1-{parent.name}-2')

    def test_find_in_parent_folders(self):
        # Find a first file in the parents
        p = str(Path('../').resolve().absolute())
        to_find = None
        while len(p) > 0:
            for f in os.listdir(p):
                f_path = os.path.join(p, f)
                if os.path.isfile(f_path):
                    to_find = (f, f_path)
                    break
            if to_find is not None:
                break
            p = os.path.split(p)[0]
        if to_find is not None:
            is_ok, res = self.config._resolve(f'find_in_parent_folders("{to_find[0]}")')
            self.assertTrue(is_ok)
            self.assertEqual(str(res), to_find[1])

    def test_find_in_parent_folders_stops_at_root(self):
        with self.assertRaises(FileNotFoundError):
            is_ok, res = self.config._resolve(f'find_in_parent_folders("non-existing-file.tmp")')

    def test_use_parsed_include(self):
        config_str = """
        locals {
            from_include = include.backend.remote_state.backend
        }
        include "backend" {
            path = "<backend_file_path_here>"
        }"""

        remote_state = """
        remote_state {
            backend = "s3"
        }
        """
        fd, path = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'w') as tmp:
                tmp.write(remote_state)

            # Use posix path separator, both for Windows and Linux
            path = path.replace(os.sep, '/')
            config = TerragruntConfigParser(Path('./no-file.hcl'), config_str.replace('<backend_file_path_here>', path), required_blocks=[])
        finally:
            os.remove(path)

        self.assertEqual(config.get_block(Block.INCLUDE)['backend']['remote_state']['backend'], 's3')
        self.assertEqual(config.get_block(Block.LOCALS)['from_include'], 's3')

    def test_large_parse(self):
        config_str = """
        terraform {
            source = "../hydrator"
        }

        locals {
            var_file_prefix     = get_env("TF_VAR_var_file_prefix", "")

            var_file            = "variables.json"
            var_file            = "${local.var_file_prefix}variables.json"
            var_file            = get_env("TF_VAR_var_file", "variables.json")
            var_file            = get_env("TF_VAR_var_file", get_env("madeup", "variables.json"))

            # This file is actually used by other parameters below
            var_file            = get_env("TF_VAR_var_file", "${get_env("TF_VAR_var_file", "variables.json")}")

            vars                = jsondecode(file("${local.var_file}"))
            params              = local.vars.params

            obj_str             = local.params.object_str
            obj_from_var        = jsondecode(local.obj_str)
            replaced            = replace(local.obj_from_var.key, "<placeholder>", "~replaced~")
            replaced_obj        = jsondecode(replace(local.obj_str, "<placeholder>", "~replaced_in_object~"))

            merged              = merge(local.params.object, local.replaced_obj)
            merged_twice        = merge(local.params.object, merge(local.params.object, local.replaced_obj))

            not_ready           = "Before-${local.some_val}-b-${local.nested_string.value}-c"
            nested_string       = {
                value = "Nested String Value"
            }
            some_val            = 10.15
            with_local          = "After-${local.some_val}-b-${local.nested_string.value}-c"
            location            = get_terragrunt_dir()
            location_in_str     = "first_val/${get_terragrunt_dir()}/other_val"
            some_file_contents  = file(local.some_file)
            same_file_contents  = file("${local.some_file}")
            some_file           = "${local.var_file}"

            missing_name        = lookup(local.vars.params, "name", "niko-never-found-name")

            object_str          = "{\\"key\\": \\"val from string\\"}"
            object_str_decoded  = jsondecode(local.object_str)
            decode_from_str     = jsondecode("{\\"key\\": \\"string_json_value\\"}")
            object_val          = {"key": "val from object"}

            a_true              = true
            a_false             = false
            null_local          = null
            empty_object        = {}
            empty_list          = []

            list_one            = ["list-one"]
            list_one_val        = local.list_one[0]
            list_three          = ["${local.list_one_val}", "list-two", "list-3"]
        }

        inputs = {
            metastore_params    = local.params
            some_input          = local.some_val
            no_val              = lookup(local.nested_string, "no_name", "no_val_default")
            null_val            = lookup(local.nested_string, "no_name", null)
            empty_object        = lookup(local.nested_string, "no_name", {})
            empty_list          = lookup(local.nested_string, "no_name", [])
        }"""
        var_file_contents = '''{
            "params": {
                "some_var": "some_var_value", 
                "object_str": "{\\"key\\": \\"json_<placeholder>_value\\"}",
                "object": {
                    "key": "default-key",
                    "value": "default-value"
                }
            }
        }'''

        fd_hcl, path_hcl = tempfile.mkstemp()
        fd_var, path_var = tempfile.mkstemp()
        try:
            os.environ['TF_VAR_var_file'] = path_var
            with os.fdopen(fd_hcl, 'w') as tmp:
                tmp.write(config_str)

            with os.fdopen(fd_var, 'w') as tmp:
                tmp.write(var_file_contents)

            config = TerragruntConfigParser(Path(path_hcl))    
        finally:
            os.remove(path_hcl)
            os.remove(path_var)

        self.assertEqual(config.get_block(Block.TERRAFORM)['source'], '../hydrator')
        self.assertEqual(config.get_block(Block.INPUTS)['metastore_params']['some_var'], 'some_var_value')
        self.assertEqual(config.get_block(Block.LOCALS)['var_file'], path_var)
        self.assertEqual(config.get_block(Block.LOCALS)['some_file_contents'], var_file_contents)
        self.assertTrue(isinstance(config.get_block(Block.LOCALS)['some_val'], (int, float, complex)) and not isinstance(config.get_block(Block.LOCALS)['some_val'], bool))
        self.assertEqual(config.get_block(Block.LOCALS)['some_val'], 10.15)
        self.assertTrue(config.get_block(Block.LOCALS)['a_true'])
        self.assertFalse(config.get_block(Block.LOCALS)['a_false'])
        self.assertEqual(config.get_block(Block.INPUTS)['no_val'], 'no_val_default')
        self.assertIsNone(config.get_block(Block.INPUTS)['null_val'])
        self.assertIsNone(config.get_block(Block.LOCALS)['null_local'])
        self.assertEqual(config.get_block(Block.LOCALS)['empty_object'], {})
        self.assertEqual(config.get_block(Block.INPUTS)['empty_object'], {})
        

if __name__ == '__main__':
    unittest.main()