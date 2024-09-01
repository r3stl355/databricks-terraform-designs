import os
from argparse import ArgumentParser
import shutil
from datetime import datetime as dt
import logging
from enum import StrEnum, auto
import re
from pathlib import Path
import json


class Operation(StrEnum):
    INIT = auto()
    PLAN = auto()
    APPLY = auto()
    DESTROY = auto()
    @classmethod
    def _missing_(cls, value):
        value = value.lower()
        for member in cls:
            if member.value == value:
                return member
        return None

class NODE_TYPE(StrEnum):
    LOCALS = auto()
    INPUTS = auto()

CONFIG_FILE = Path('terragrunt.hcl')
RUN_DIR = Path('_hydrator')
SUB_REPLACE = '%|||||'
QUOTE_REPLACE = '`````'
TF_RUN_FORMAT = 'cd _hydrator && terraform {}'
LOG_LEVEL = logging.INFO

def log(msg: str, level=logging.DEBUG):
    if LOG_LEVEL <= level:
        print(f'[{dt.now().strftime("%Y-%m-d %H:%M:%S")}]: {msg}')

class Hydrator:
    def __init__(self, operation: str):
        self.operation = Operation(operation)
        self.source = None
        self.locals = {}
        self.inputs = {}
        self.files = []

    def run(self):
        if self.operation == Operation.DESTROY:
            self._tf_run(self.operation)
        else:
            self._parse_config()._copy()._set_vars()._init(self.operation == Operation.INIT)._tf_run(self.operation)

    def _init(self, no_op=False):
        tf = RUN_DIR / '.terraform'
        if not (no_op or tf.exists()):
            self._tf_run(Operation.INIT)
        return self

    def _reset(self):
        self.source = None
        self.locals = {}
        self.inputs = {}
        self.files = []

    def _tf_run(self, op: Operation):
        os.system(TF_RUN_FORMAT.format(op.name.lower()))

    def _set_vars(self):
        if len(self.inputs) > 0:
           dest = RUN_DIR / 'hydrator.auto.tfvars.json' 
           dest.write_text(json.dumps(self.inputs))
        return self

    def _copy(self):
        if not RUN_DIR.exists():
            log(f"New run, creating '{RUN_DIR}' directory", logging.INFO)
            RUN_DIR.mkdir()

        self.files = []
        tf_dir = Path(self.source)
        for f in tf_dir.glob('*'):
            if f.is_file():
                if f.suffix.lower() in ['.tfstate']:
                    raise FileExistsError(f"'{tf_dir}' directory contains a state file, cannot apply a Terraform template with existing state")
                elif f.suffix.lower() in ['.tf', '.tfvars', '.json']:
                    self.files.append(f)
        if len(self.files) == 0:
            raise RuntimeError(f'Teffaform files not found in {tf_dir.absolute}')

        for f in Path('./').glob('*'):
            if f.is_file():
                if f.suffix.lower() in ['.tfstate']:
                    raise FileExistsError(f"Cannot run a template with an existing state file (found in the current directory)")
                elif any([f.name == fe.name for fe in self.files]):
                    raise FileExistsError(f"File '{f.name}' exists in both local directory and target Terraform template directory")
                elif f.suffix.lower() in ['.tf', '.tfvars', '.json']:
                    self.files.append(f)
        [shutil.copy(f, RUN_DIR) for f in self.files]
        
        # Resolve relative paths in modules
        log(f'Resolving module paths')
        for f in self.files:
            path_in_run = RUN_DIR / f.name
            txt = path_in_run.read_text()
            res = re.findall('module\s*"[^"]+"\s*\{([^}]+|\{[^}]*\})[^}]*(source\s*=\s*"([^"]+)")', txt, re.IGNORECASE | re.MULTILINE)
            if res:
                log(f'In file: {f}')
                for p in res:
                    source_path = (f.parent / p[2]).resolve().absolute()
                    rel_path = os.path.relpath(source_path, RUN_DIR)
                    txt = txt.replace(p[1], f'source = "{rel_path}"')
                    path_in_run.write_text(txt)

        return self
    
    def _parse_config(self):
        self._reset()   

        f = f"./{CONFIG_FILE}"
        if not CONFIG_FILE.exists():
            raise FileNotFoundError(f'{f} is not found')

        config_str = CONFIG_FILE.read_text()
        flags = re.IGNORECASE | re.MULTILINE | re.DOTALL

        # One way to parse HCL is by converting it to JSON
        config = re.subn('\s*#[^\n]*', '', config_str)                          # remove comments
        config = re.subn('\${', SUB_REPLACE, config[0], flags)                  # temporarily mask interpolation (start of)
        config = re.subn('"', QUOTE_REPLACE, config[0], flags)                  # temporarily mask double quotes
        # config = re.subfn('([^\s\n=\$]+)\s*=', ',"{1}":', config[0], flags)      # replace `name =` with `,"name":`
        # config = re.subfn('([^\s\n:{]+)\s*{', ',"{1}": {{', config[0], flags)    # replace `name {` with `,"name": {`
        # config = re.subfn(':\s*([^\s\d"{][^\n$]*)', ': "{1}"', config[0], flags) # wrap simple non-numeric values into double quotes
        config = re.subn('([^\s\n=\$]+)\s*=', ',"\\1":', config[0], flags)      # replace `name =` with `,"name":`
        config = re.subn('([^\s\n:{]+)\s*{', ',"\\1": {', config[0], flags)     # replace `name {` with `,"name": {`
        config = re.subn(':\s*([^\s\d"{][^\n$]*)', ': "\\1"', config[0], flags) # wrap simple non-numeric values into double quotes
        config = re.subn('\s*\n\s*', '', config[0], flags)                      # remove empty space
        config = re.subn('{,', '{', config[0], flags)                           # remove extra commas after `{` (introduced by previous substitutions)
        config = re.subn('^,', '', config[0], flags)                            # remove extra commas at the start of line
        config = re.subn('"\^\^', '"', config[0], flags)                        # remove extra double quotes introduced earlier (from the string start)
        config = re.subn('\^\^"', '"', config[0], flags)                        # remove extra double quotes from string ends
        conf_str = config[0].replace(': "true"', ': true').replace(': "false"', ': false')  # unwrap booleans
        config = json.loads(f"{{{conf_str}}}")

        log(f'Config: {config}')

        tf = config.get('terraform', None)
        if tf is None or tf.get('source', None) is None:
            raise LookupError(f'Reference to source terraform template is not found')
        self.source = tf.get('source').replace(QUOTE_REPLACE, '')

        # Resolve locals
        _ = self._resolve(config.get('locals', None), is_recursive=False)
        log(f'Locals: {self.locals}')

        # Resolve inputs
        _, self.inputs = self._resolve(config.get('inputs', None), node_type=NODE_TYPE.INPUTS, is_recursive=False)
        log(f'Inputs: {self.inputs}')

        return self

    def _resolve(self, value, node_type: NODE_TYPE=NODE_TYPE.LOCALS, is_recursive=False):
        """Return a value with all the locals and functions resolved"""

        if value is None:
            return False, None

        local_must_exist=(node_type != NODE_TYPE.LOCALS)

        if isinstance(value, dict):
            resolved = {}
            to_process = list(value.keys())
            while to_process:
                key = to_process.pop(0)
                is_ok, res = self._resolve(value[key], node_type=node_type, is_recursive=True)
                if is_ok:
                    resolved[key] = res
                    if node_type == NODE_TYPE.LOCALS and not is_recursive:
                        # Store only top level locals
                        self.locals[key] = res
                elif not is_recursive:
                    # Dependency not found, this could only happen to locals, not inputs, put it back to queue but only if it wasn't the last one
                    if len(to_process) > 0:
                        to_process.append(key)
                    else:
                        raise LookupError(f"'Dependency for {value[key]}' not found")
                else:
                    # Must be also part of locals but is deeper in the hierarchy, stop here, this should abandon the full tree traversal
                    return False, None
        
            return True, resolved
        
        if isinstance(value, list):
            resolved = []
            for v in value:
                is_ok, res = self._resolve(v, node_type=node_type, is_recursive=True)
                if is_ok:
                    resolved.append(res)
                else:
                    return False, None
        
            return True, resolved

        elif isinstance(value, str):
            # Just because the value is string here doesn't mean it will be of string type becuase of the way we converted the HCL to JSON,
            # e.g. in `x = jsondecode(...)` is converted to `"x": "jsondecode(...)"` so value will appear as str type here but it is an object
            # Actually, in Python it will be parsed `x: 'jsondecode(...)'` so we can test for it being a string becasue Terraform uses only " for strings
            value = value.replace(QUOTE_REPLACE, '"')
            value = value.replace(SUB_REPLACE, '${')
            log(f'Resolving: {value}')

            if value.startswith('local.'):
                # For now assume this is a single value, not an operation. It can be a nested property lookup
                v = self._get_local(value)
                if v is not None:
                    return True, v
                elif local_must_exist:
                    raise LookupError(f"'{value}' not found in locals")
                else:
                    return False, None
            
            if value.startswith('"') and value.endswith('"'):
                # This is a true string, strip the quotes
                is_ok, res = self._replace_locals(value.strip('"'), local_must_exist=local_must_exist)
                if is_ok:
                    res = self._replace_functions(res)
                return is_ok, res
            
            elif self._is_function(value):
                return self._exec_function(value)
            
            raise RuntimeError(f"Should never get here: {value}")
        
        else:
            # Boolean or number, no need to process
            return True, value

    def _get_local(self, key: str):
        if key.startswith('local.'):
            key = key[len('local.'):]
        lookup = self.locals
        for k in key.split('.'):
            res = lookup.get(k, None)
            if res is None:
                break
            else:
                lookup = res
        return res
        

    def _is_function(self, value: str) -> bool:
        if not value.startswith('"'):
            for func in KNOWN_FUNCTIONS:
                if re.search(f'^{func}\s*\(', value):
                    return True
        return False

    def _replace_locals(self, value_str: str, local_must_exist=False) -> tuple[bool, str]:
        """ Interpolate the string by replacing all the occurrences of references to locals only"""

        # This is a string interpolation so must include `${...}`
        pattern = "(\$\{local.([^\s}]+)\})"
        while True:
            res = re.search(pattern, value_str, re.IGNORECASE)
            if res:
                full_local = res.group(1)
                key = res.group(2)
                v = self._get_local(key)
                if v is not None:
                    value_str = value_str.replace(full_local, str(v), 1)
                    continue
                elif local_must_exist:
                    raise LookupError(f"'{key}' not found in locals")
                return False, None
            break

        return True, value_str

    def _replace_functions(self, value_str: str):
        """ Interpolate the string by replacing all the occurrences of references to functions"""

        # Fancy regexes like `((\$\{)?\d[^"()\{\}/]*\([^()]*(\)*\s*)*)` would be really hard to construct here, e.g. for nested functions, safer to parse by walking along
        while True:
            if '${' in value_str:
                i = value_str.index('${')
            else:
                break

            j = i + 2
            func_str = value_str[j:]
            is_func = self._is_function(func_str)
            if not is_func:
                raise LookupError(f'Unknown function in "{func_str}" at the position {i}')
            
            in_string = False
            while (value_str[j] != '}' or in_string) and j < len(value_str):
                if value_str[j] == '"':
                    in_string = not in_string
                elif in_string and value_str[j] == '{' and value_str[j-1] == '$':
                    ## Nested function, need to solve it first
                    i = j - 1
                    in_string = False
                j += 1

            if j < len(value_str):
                is_ok, res = self._exec_function(value_str[i+2:j].strip())
                if is_ok:
                    value_str = f'{value_str[0:i]}{res}{value_str[j+1:]}'

        return value_str

    def _extract_function(self, value: str) -> str:
        """ Extract the full definition of the function at the start of the given value"""

        log(f'Extracting function from: {value}')

        # Fancy regexes like `'([^{(\s]+)\s*\(([^)]*)(\)*\s*)*'` won't be sufficient here, e.g. for nested functions, safer to parse by walking along
        lookup = re.search(f'(^([^\s\(]+)\s*\()', value)
        if not lookup:
            raise ValueError(f'Invalid function {value}')
        func = lookup.group(2)
        if func not in KNOWN_FUNCTIONS:
            raise ValueError(f'Uknown function {func}')
        
        i = len(lookup.group(1)) - 1
        count = 0
        in_string = False
        while i < len(value) - 1:
            i += 1
            if value[i] == '"':
                in_string = not in_string
                i += 1
                continue
            if in_string:
                continue

            if value[i] == '(':
                count += 1
                continue

            if value[i] == ')':
                if count == 0:
                    return value[0:i+1]
                else:
                    count -= 1

        return value
    
    def _exec_function(self, func_str: str):
        """Execute a given function"""

        lookup = re.search(f'(^([^\s\(]+)\s*\()', func_str)
        if not lookup:
            raise ValueError(f'Invalid function {func_str}')
        func = lookup.group(2)
        if func not in KNOWN_FUNCTIONS:
            raise ValueError(f'Uknown function {func}')

        log(f'Executing: {func_str}')
        
        param_str = func_str[len(lookup.group(1)):-1]
        if len(param_str) == 0:
            # Function without parameters
            return True, KNOWN_FUNCTIONS[func]()
        
        if param_str.count(',') == 0:
            # A single parameter
            is_ok, res = self._resolve(param_str)
            if is_ok:
                return True, KNOWN_FUNCTIONS[func](res)
            return False, None
        
        params = []
        i = 0

        if '${' in param_str:
            param_str = self._replace_functions(param_str)
        while i < len(param_str):
            if param_str[i] == '"':
                j = i + 1
                while j < len(param_str) and param_str[j] != '"':
                    j += 1
                if j < len(param_str):
                    params.append(param_str[i:j+1])
                else:
                    raise RuntimeError(f'Unclosed string in {param_str} from position {i}')
                j += 1
            elif self._is_function(param_str[i:]):
                f = self._extract_function(param_str[i:])
                params.append(f)
                j = i + len(f)
            else:
                raise RuntimeError(f"Should never get here: {param_str}")
            
            while j < len(param_str) and param_str[j] in [' ', ',']:
                j += 1
            i = j

        resolved_params = []
        for p in params:
            is_ok, p_res = self._resolve(p)
            if is_ok:
                resolved_params.append(p_res)
            else:
                return False, None
            
        return True, KNOWN_FUNCTIONS[func](*resolved_params)


def get_env(name: str, default=None) -> str:
    val = os.environ.get(name, default)
    return val

def get_terragrunt_dir() -> str:
    return str(Path(".").absolute())

def file(path: str) -> str:
    p = Path(path.strip(' "'))
    return p.read_text()

def jsondecode(obj: str) -> dict:
    return json.loads(obj)

KNOWN_FUNCTIONS = {
    'get_env': get_env, 
    'file': file, 
    'get_terragrunt_dir': get_terragrunt_dir,
    'jsondecode': jsondecode
    }

def get_args():
    parser = ArgumentParser(
        description='Run terragrunt template without using the Terragrunt'
    )
    parser.add_argument(
        'operation',
        default=Operation.PLAN.name.lower(),
        help=f'Terraform operation to run, one of {[op.name.lower() for op in list(Operation)]}'
    )

    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    hydrator = Hydrator(args.operation)
    hydrator.run()